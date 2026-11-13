"""The writer: flan-t5-small fine-tuned on the game's GadgetDraft format, decoded under the shared Grammar; and
Hybrid, the shipped resolver (mechanics from forge.mechanics, name + description from this writer).

Why: the from-scratch mechanics model composes closest to Sonnet but its text has nonwords and foreign items; a
pretrained model brings English and world knowledge. Same output token language as forge.mechanics (structure
tokens added to T5's vocab), same grammar (100% legal + firing), same best-of-N shippability filter. In the hybrid
the writer reads the mechanics model's stages as forced decoder input and writes only the name + description.

  python -m forge.writer train --out runs/forge-writer     # defaults = the shipped recipe (~1 h on an M2)
"""
import argparse
import json
import math
import random
import re
import time
from pathlib import Path

import torch

from forge.mechanics import DEPTHS, MAX_COUNT, REP, ROOT, SCALE_TO, TIER_DEPTH, bucket, delex_slots, display, slot_names
from forge.grammar import SLOT_TOKENS, STRUCT_TOKENS, TEXT_TOKENS, Grammar
from forge.shippable import Checker, best_of, build_lexicon, has_idiom

ADDED = STRUCT_TOKENS + SLOT_TOKENS + TEXT_TOKENS
_BUCKET_WORDS = ["zero", "tiny", "very small", "small", "low", "moderate", "medium", "high", "very high", "huge",
                 "enormous"]
_NUM = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight"]


def phrase(tok):
    """Natural-language seed for initialising an added token's embedding."""
    if tok in ("<stage>", "<fx>", "<name>", "<desc>"):
        return {"<stage>": "stage", "<fx>": "effect", "<name>": "name", "<desc>": "description"}[tok]
    body = tok[1:-1]
    if body.startswith(("trig:", "k:", "t:")):
        v = body.split(":", 1)[1]
        return {"STRUCK": "target", "SELF": "self"}.get(v, v.lower().replace("_", " "))
    if body.startswith("b"):
        return _BUCKET_WORDS[int(body[1:])]
    if body.startswith("c"):
        return _NUM[int(body[1:])]
    if body.startswith("i"):
        return ["first item", "second item", "third item", "fourth item"][int(body[1:])]
    return body


def src_text(build, depth):
    parts = [f"form {build.delivery.value}", f"depth {depth}"]
    for slot, it in build.slots():
        parts.append(f"{slot}: {it.name} ({it.describe()})" if it else f"{slot}: empty")
    return ". ".join(parts)


class T5GameCodec:
    def __init__(self, tok):
        self.tok = tok
        self.id = {t: tok.convert_tokens_to_ids(t) for t in ADDED}
        self.inv = {v: k for k, v in self.id.items()}
        self.eos = tok.eos_token_id
        self.vocab = len(tok)
        self.text_mask = torch.zeros(self.vocab, dtype=torch.bool)
        first_extra = tok.convert_tokens_to_ids("<extra_id_99>")  # sentinels + added tokens sit above the pieces
        self.text_mask[3:first_extra] = True  # skip pad/eos/unk

    def text(self, s):
        return self.tok(s, add_special_tokens=False).input_ids

    def tgt(self, d, names):
        floats = [v for s in d["stages"] for e in s["effects"] for v in (e["amount"], e["duration"], e["radius"])]
        scale = SCALE_TO / max(floats) if floats and max(floats) > 0 else 1.0
        I, out = self.id, []  # noqa: E741
        for s in d["stages"]:
            out += [I["<stage>"], I[f"<trig:{s['trigger']}>"]]
            for e in s["effects"]:
                out += [I["<fx>"], I[f"<k:{e['kind']}>"], I[f"<t:{e['target']}>"]]
                out += [I[f"<b{bucket(e[f] * scale)}>"] for f in ("amount", "duration", "radius")]
                out.append(I[f"<c{min(MAX_COUNT, int(e['count']))}>"])
        desc = delex_slots(d["description"], names)
        return out + [I["<name>"]] + self.text(d["name"]) + [I["<desc>"]] + self.text(desc) + [self.eos]

    def to_draft(self, ids, names):
        from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger
        from forge.text import relex
        I, inv, stages, i = self.id, self.inv, [], 0  # noqa: E741
        while i < len(ids) and ids[i] == I["<stage>"]:
            trig = inv[ids[i + 1]][6:-1]
            i += 2
            effects = []
            while i < len(ids) and ids[i] == I["<fx>"]:
                kind, tgt = inv[ids[i + 1]][3:-1], inv[ids[i + 2]][3:-1]
                vals = [REP[int(inv[ids[i + j]][2:-1])] for j in (3, 4, 5)]
                effects.append(Effect(kind=EffectKind(kind), target=Target(tgt), amount=vals[0], duration=vals[1],
                                      radius=vals[2], count=int(inv[ids[i + 6]][2:-1]), note=""))
                i += 7
            stages.append(Stage(trigger=Trigger(trig), effects=effects, note=""))
        rest = ids[i:]
        nm, ds = I["<name>"], I["<desc>"]
        name_ids = rest[rest.index(nm) + 1:rest.index(ds)] if ds in rest else rest[1:]
        desc_ids = rest[rest.index(ds) + 1:] if ds in rest else []
        if self.eos in desc_ids:
            desc_ids = desc_ids[:desc_ids.index(self.eos)]
        desc = self.tok.decode(desc_ids, skip_special_tokens=False).strip()
        desc = re.sub(r"\s*(<i\d>)\s*", r" \1 ", desc).strip()
        desc = re.sub(r"(<i\d>) (?=['’,.;:!?)\-])", r"\1", desc)
        desc = re.sub(r"\s{2,}", " ", desc)
        return GadgetDraft(name=self.tok.decode(name_ids, skip_special_tokens=True).strip(),
                           description=relex(desc, [display(n) for n in names]), logic="", stages=stages)


def struct_tokens(draft):
    """A GadgetDraft's stages as structure-token strings (same scaling/bucketing as training targets)."""
    floats = [v for s in draft.stages for e in s.effects for v in (e.amount, e.duration, e.radius)]
    scale = SCALE_TO / max(floats) if floats and max(floats) > 0 else 1.0
    out = []
    for s in draft.stages:
        out += ["<stage>", f"<trig:{s.trigger.value}>"]
        for e in s.effects:
            out += ["<fx>", f"<k:{e.kind.value}>", f"<t:{e.target.value}>"]
            out += [f"<b{bucket(v * scale)}>" for v in (e.amount, e.duration, e.radius)]
            out.append(f"<c{min(MAX_COUNT, e.count)}>")
    return out


@torch.no_grad()
def t5_generate(model, codec, build, depth, seed=None, temperature=0.9, min_p=0.1, forced=None):
    """forced: optional structure-token strings to force (hybrid mode: another model's mechanics, T5's text)."""
    from forge.sampling import pick as _pick
    enc_in = codec.tok(src_text(build, depth), return_tensors="pt", truncation=True, max_length=512)
    enc_out = model.get_encoder()(**enc_in)
    g = Grammar(codec.id, codec.eos, codec.text_mask, build)
    gen = torch.Generator().manual_seed(seed) if seed is not None else None
    dec = torch.tensor([[model.config.decoder_start_token_id]])
    past, out = None, []
    forced_ids = [codec.id[t] for t in (forced or [])]
    for _ in range(220):
        res = model(encoder_outputs=enc_out, attention_mask=enc_in.attention_mask, decoder_input_ids=dec,
                    past_key_values=past, use_cache=True)
        past = res.past_key_values
        allowed = g.allowed(out)
        if len(out) < len(forced_ids):
            tok = forced_ids[len(out)]
            assert allowed[tok], "forced structure violates the grammar"
        elif int(allowed.sum()) == 1:
            tok = int(allowed.nonzero()[0])
        else:
            tok = _pick(res.logits[0, -1].float()[:codec.vocab], allowed, gen, temperature, min_p)
        out.append(tok)
        dec = torch.tensor([[tok]])
        if tok == codec.eos:
            break
    return codec.to_draft(out, slot_names(build))


class Writer:
    """Resolver with the game repo's interface: resolve(build, tier) -> GadgetDraft (fill_budget applied)."""

    def __init__(self, run, threads=1):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from resolver.bake.schema import contract_fingerprint
        run = Path(run)
        torch.set_num_threads(threads)
        self.tok = AutoTokenizer.from_pretrained(run)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(run).eval()
        self.codec = T5GameCodec(self.tok)
        self.meta = json.loads((run / "t5_meta.json").read_text())
        if self.meta["contract_fingerprint"] != contract_fingerprint():
            raise RuntimeError("model was trained against a different capability contract - retrain it")
        self.checker = Checker(json.loads((run / "lexicon.json").read_text()))
        self.last_issues, self.last_tries = {}, 0
        self.ck = {"epoch": self.meta["epoch"]}

    def draft(self, build, depth, seed=None, temperature=0.9, min_p=0.1):
        return t5_generate(self.model, self.codec, build, depth, seed=seed, temperature=temperature, min_p=min_p)

    def resolve(self, build, tier, seed=None, n=8):
        from resolver.bake.schema import combo_id
        from resolver.clamp import fill_budget
        from resolver.contract import Tier
        from forge.sampling import combo_seed
        tier = Tier(tier)
        base = seed if seed is not None else combo_seed([combo_id(build), tier.value])
        draft, self.last_issues, self.last_tries, self.first_issues = best_of(
            n, lambda i: self.draft(build, TIER_DEPTH[tier.value], seed=base + i), build, self.checker)
        return fill_budget(draft, tier)


class Hybrid:
    """Mechanics from the tiny model (closest to Sonnet's compositions), name + description from T5 (fluent,
    grounded), written for exactly those mechanics. Spec string: 'hybrid:<tiny run>+<t5 run>'."""

    def __init__(self, tiny_run, t5_run):
        from forge.mechanics import Mechanics
        self.tiny, self.t5 = Mechanics(tiny_run), Writer(t5_run)
        self.checker = self.t5.checker
        self.last_issues, self.last_tries, self.first_issues = {}, 0, {}
        self.ck = {"epoch": f"{self.tiny.ck['epoch']}+{self.t5.meta['epoch']}"}

    def draft(self, build, depth, seed=None):
        plan = self.tiny.draft(build, depth, seed=seed)
        return t5_generate(self.t5.model, self.t5.codec, build, depth, seed=seed, forced=struct_tokens(plan))

    def resolve(self, build, tier, seed=None, n=8):
        from resolver.bake.schema import combo_id
        from resolver.clamp import fill_budget
        from resolver.contract import Tier
        from forge.sampling import combo_seed
        tier = Tier(tier)
        base = seed if seed is not None else combo_seed([combo_id(build), tier.value])
        draft, self.last_issues, self.last_tries, self.first_issues = best_of(
            n, lambda i: self.draft(build, TIER_DEPTH[tier.value], seed=base + i), build, self.checker)
        return fill_budget(draft, tier)


def load_resolver(run=None):
    """The shipped Hybrid from models/forge (run=None, or a dir holding mechanics/ + writer/), a Hybrid from
    'hybrid:<mechanics run>+<writer run>', or a single Writer / Mechanics run dir."""
    from forge.mechanics import MODELS
    run = MODELS if run is None else run
    if str(run).startswith("hybrid:"):
        tiny, t5 = str(run)[len("hybrid:"):].split("+")
        return Hybrid(tiny, t5)
    if (Path(run) / "mechanics").is_dir() and (Path(run) / "writer").is_dir():
        return Hybrid(Path(run) / "mechanics", Path(run) / "writer")
    if not Path(run).exists():
        raise FileNotFoundError(f"no Forge model at {run} - run: python -m forge.fetch")
    if (Path(run) / "t5_meta.json").exists():
        return Writer(run)
    from forge.mechanics import Mechanics
    return Mechanics(run)


def train(a):
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    from resolver.bake.schema import contract_fingerprint
    from forge.train_mechanics import is_val, load_examples
    random.seed(0)
    torch.manual_seed(0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ex, bad = load_examples()
    if a.max_train:
        ex = ex[:a.max_train]
    train_e = [e for e in ex if not is_val(e[0])]
    val_e = [e for e in ex if is_val(e[0])]
    print(f"{len(ex)} examples ({bad} bad); train {len(train_e)} / val {len(val_e)}")
    resume = a.resume and (out / "t5_meta.json").exists()
    tok = AutoTokenizer.from_pretrained(out if resume else a.base)
    if not resume:
        tok.add_tokens(ADDED, special_tokens=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(out if resume else a.base)
    start_ep = json.loads((out / "t5_meta.json").read_text())["epoch"] if resume else 0
    prev_best = json.loads((out / "t5_meta.json").read_text())["val_loss"] if resume else float("inf")
    if resume:
        print(f"resuming from {out} (epoch {start_ep}, val {prev_best:.3f})")
    # transformers 5.x loads flan-t5 with config.tie_word_embeddings=True while the checkpoint's lm_head is untied;
    # resize_token_embeddings() would then re-tie lm_head to the (10x larger) input embeddings and wreck the output
    # layer (initial loss ~400 instead of ~10). Untie for the resize, then restore the flag, which this version also
    # uses to apply T5's d_model**-0.5 output rescale. Verified: base translation loss unchanged (0.605).
    def probe():  # base-model sanity: a fixed translation pair's loss must not change across the resize
        ptok = AutoTokenizer.from_pretrained(a.base)
        x = ptok(["translate English to German: The house is wonderful."], return_tensors="pt")
        y = ptok(["Das Haus ist wunderbar."], return_tensors="pt").input_ids
        with torch.no_grad():
            return model.eval()(**x, labels=y).loss.item()

    if not resume:
        before = probe()
        model.config.tie_word_embeddings = False
        model.resize_token_embeddings(len(tok), mean_resizing=False)
        model.config.tie_word_embeddings = True
    with torch.no_grad():  # new input rows: meaning of their words; new output rows: the average output row (neutral)
        emb, head = model.get_input_embeddings().weight, model.get_output_embeddings().weight
        n_old = tok.convert_tokens_to_ids("<extra_id_99>") + 1
        head_mean = head[:n_old].mean(0)
        for t in ADDED if not resume else []:
            ids = tok(phrase(t), add_special_tokens=False).input_ids
            tid = tok.convert_tokens_to_ids(t)
            emb[tid] = emb[ids].mean(0)
            head[tid] = head_mean
        assert head.data_ptr() != emb.data_ptr(), "lm_head must stay untied"
    if not resume:  # measured after the new rows are initialised (random rows would steal probability mass)
        after = probe()
        print(f"resize sanity: base translation loss {before:.3f} -> {after:.3f}")
        if abs(after - before) > 0.05:
            raise SystemExit("ABORT: resizing changed the base model's behaviour (embedding tying bug?)")
    if a.grad_ckpt:
        model.gradient_checkpointing_enable()
        model.config.use_cache = False
    model.to(a.device)
    codec = T5GameCodec(tok)

    def enc(e):
        _, b, depth, d = e
        return src_text(b, depth), codec.tgt(d, slot_names(b)), has_idiom(d["description"])

    tr, va = [enc(e) for e in train_e], [enc(e) for e in val_e]
    print(f"target tokens mean {sum(len(t) for _, t, _ in tr) / len(tr):.1f}, max {max(len(t) for _, t, _ in tr + va)}; "
          f"objective={a.objective}; idiom examples {sum(f for *_, f in tr) / len(tr):.0%} (text weight {a.idiom_weight})")
    if not resume:
        (out / "lexicon.json").write_text(json.dumps(build_lexicon(
            [d["description"] for *_, d in train_e] + [d["name"] for *_, d in train_e], [d["name"] for *_, d in train_e])))

    name_id = codec.id["<name>"]

    def batch(chunk, train=True):
        """Explicit decoder inputs (structure tokens are always *read*), plus a per-token loss weight:
        objective 'text' scores only <name> onward; idiom-bearing examples get idiom_weight on their text."""
        x = tok([s for s, _, _ in chunk], padding=True, pad_to_multiple_of=32, truncation=True, max_length=512,
                return_tensors="pt")
        T = -(-max(len(t) for _, t, _ in chunk) // 16) * 16
        full = torch.full((len(chunk), T), tok.pad_token_id, dtype=torch.long)
        w = torch.zeros((len(chunk), T))
        for k, (_, t, idiom) in enumerate(chunk):
            full[k, :len(t)] = torch.tensor(t)
            n0 = t.index(name_id)
            if a.objective == "full":
                w[k, :n0] = 1.0
            w[k, n0:len(t)] = a.idiom_weight if (train and idiom) else 1.0
        dec = model._shift_right(full)
        return (x.input_ids.to(a.device), x.attention_mask.to(a.device), dec.to(a.device), full.to(a.device),
                w.to(a.device))

    def weighted_loss(ids, att, dec, full, w):
        logits = model(input_ids=ids, attention_mask=att, decoder_input_ids=dec).logits
        ce = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]).float(), full.reshape(-1),
                                               reduction="none").view_as(w)
        return (ce * w).sum() / w.sum(), w.sum()

    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
    steps = a.epochs * math.ceil(len(tr) / a.bs)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (100 if resume else 300))
                                              * max(0.1, 1 - 0.9 * s / steps))
    best, bad_ep = prev_best, 0
    for ep in range(start_ep + 1, start_ep + a.epochs + 1):
        model.train()
        random.shuffle(tr)
        t0, tl, tn = time.time(), 0.0, 0
        for i in range(0, len(tr), a.bs):
            loss, _ = weighted_loss(*batch(tr[i:i + a.bs]))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tl, tn = tl + loss.item(), tn + 1
            if tn % 100 == 0:
                print(f"   step {tn}: {(time.time() - t0) / tn:.2f} s/step", flush=True)
                if a.device == "mps":
                    torch.mps.empty_cache()
        model.eval()
        vl, vn = 0.0, 0
        with torch.no_grad():
            for i in range(0, len(va), 32):
                vloss_b, n = weighted_loss(*batch(va[i:i + 32], train=False))
                vl, vn = vl + vloss_b.item() * n.item(), vn + n.item()
        vloss = vl / vn
        print(f"ep {ep:2d}  train {tl / tn:.3f}  val {vloss:.3f}  {time.time() - t0:.0f}s", flush=True)
        if vloss < best:
            best, bad_ep = vloss, 0
            model.config.use_cache = True
            model.save_pretrained(out)
            model.config.use_cache = not a.grad_ckpt
            tok.save_pretrained(out)
            (out / "t5_meta.json").write_text(json.dumps({"base": a.base, "epoch": ep, "val_loss": vloss,
                                                          "objective": a.objective,
                                                          "contract_fingerprint": contract_fingerprint()}))
        else:
            bad_ep += 1
            if bad_ep >= a.patience:
                print(f"early stop at epoch {ep}")
                break
    print(f"best val {best:.3f} -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train"])
    ap.add_argument("--base", default="google/flan-t5-small")
    ap.add_argument("--out", default=str(ROOT / "runs/forge-writer"))
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--resume", action="store_true", help="continue from the checkpoint in --out")
    ap.add_argument("--objective", choices=["full", "text"], default="text",
                    help="full: learn structure + text; text: hybrid writer, loss on name+description only")
    ap.add_argument("--idiom-weight", type=float, default=0.3, help="text-loss weight for idiom-bearing examples")
    ap.add_argument("--max-train", type=int, default=0, help="limit examples (smoke tests)")
    ap.add_argument("--grad-ckpt", action="store_true", help="gradient checkpointing (much less memory, ~30%% slower)")
    train(ap.parse_args())
