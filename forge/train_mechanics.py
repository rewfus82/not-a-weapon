"""Train the mechanics model on teacher ScaffoldSets (data/forge/scaffolds-*.jsonl).

  python -m forge.train_mechanics --out runs/forge-mechanics      # defaults = the shipped recipe (~13 min on an M2)
"""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from forge.mechanics import (BOS, DEPTHS, PAD, ROOT, SPECIALS, GameCodec, ItemVectors, delex_slots, generate,
                             slot_names)
from forge.model import Forge, n_params
from forge.text import train_tokenizer

DATA = ROOT / "data/forge"


def is_val(combo_id, pct=5):
    return int(hashlib.md5(combo_id.encode()).hexdigest(), 16) % 100 < pct


def batches(pairs, bs, shuffle, device):
    """pairs: (src_ids, tgt_ids, feat_rows). Yields src, tgt_in, tgt_out, feat."""
    order = list(range(len(pairs)))
    if shuffle:
        random.shuffle(order)
    for i in range(0, len(order), bs):
        chunk = [pairs[j] for j in order[i:i + bs]]
        S = max(len(p[0]) for p in chunk)
        T = max(len(p[1]) for p in chunk) + 1
        src = torch.full((len(chunk), S), PAD, dtype=torch.long)
        tin = torch.full((len(chunk), T - 1), PAD, dtype=torch.long)
        tout = torch.full((len(chunk), T - 1), PAD, dtype=torch.long)
        feat = torch.zeros((len(chunk), S, chunk[0][2].shape[1]))
        for k, (s, t, f) in enumerate(chunk):
            src[k, :len(s)] = torch.tensor(s)
            seq = [BOS] + t
            tin[k, :len(seq) - 1] = torch.tensor(seq[:-1])
            tout[k, :len(seq) - 1] = torch.tensor(seq[1:])
            feat[k, :len(s)] = torch.from_numpy(f)
        yield src.to(device), tin.to(device), tout.to(device), feat.to(device)


def weighted_ce(logits, tout, plan_lo, plan_hi, plan_weight, smoothing):
    """Token cross-entropy with the structure ("plan") tokens up-weighted."""
    ce = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), tout.reshape(-1), ignore_index=PAD,
                         label_smoothing=smoothing, reduction="none")
    w = torch.ones_like(tout, dtype=torch.float)
    w[(tout >= plan_lo) & (tout <= plan_hi)] = plan_weight
    w[tout == PAD] = 0.0
    return (ce * w.reshape(-1)).sum() / w.sum()


def load_examples(data=DATA):
    """(combo_id, build, depth, draft-dict) for every reading in data/forge/scaffolds-*.jsonl (combo slots come from
    the matching combos-*.json); skips anything that fails to parse."""
    combos = {}
    for f in sorted(Path(data).glob("combos-*.json")):
        for c in json.loads(f.read_text())["combos"]:
            combos[c["combo_id"]] = c["slots"]
    out, bad = [], 0
    for f in sorted(Path(data).glob("scaffolds-*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                build = build_from_slots(combos[r["combo_id"]])
                for d in DEPTHS:
                    out.append((r["combo_id"], build, d, r["scaffolds"][d]))
            except Exception:
                bad += 1
    return out, bad


def build_from_slots(slots):
    from resolver.items import CATALOG, Build
    it = lambda k: CATALOG[slots[k]] if slots.get(k) else None  # noqa: E731
    return Build(delivery_item=CATALOG[slots["delivery"]], damage_item=it("damage"),
                 utility_item=it("utility"), modifier_item=it("modifier"))


def demo_builds():
    """The held-out gold combos (the game repo's pre30 Sonnet bake): never trained on."""
    sel = json.loads((ROOT / "data/bake/combos-pre30.json").read_text())["combos"]
    return [(c["combo_id"], build_from_slots(c["slots"])) for c in sel]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA), help="dir with combos-*.json + scaffolds-*.jsonl")
    ap.add_argument("--out", default=str(ROOT / "runs/forge-mechanics"))
    ap.add_argument("--vocab", type=int, default=3000)
    ap.add_argument("--d", type=int, default=256)
    ap.add_argument("--heads", type=int, default=4)
    ap.add_argument("--enc", type=int, default=4)
    ap.add_argument("--dec", type=int, default=5)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--lr", type=float, default=7e-4)
    ap.add_argument("--wd", type=float, default=0.05)
    ap.add_argument("--smoothing", type=float, default=0.1)
    ap.add_argument("--plan-weight", type=float, default=2.0)
    ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
    ap.add_argument("--seed", type=int, default=2)
    a = ap.parse_args()
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    ex, bad = load_examples(a.data)
    train_e = [e for e in ex if not is_val(e[0])]
    val_e = [e for e in ex if is_val(e[0])]
    print(f"{len(ex)} examples from {len(ex) // 3} combos ({bad} bad lines); train {len(train_e)} / val {len(val_e)}")

    texts = []
    for _, b, _, d in train_e:
        texts += [d["name"], delex_slots(d["description"], slot_names(b))]
    tok = train_tokenizer(texts, a.vocab, out / "tokenizer.json", specials=SPECIALS)
    codec = GameCodec(tok)
    vectors = ItemVectors()
    from resolver.items import CATALOG
    vectors.ensure(sorted(CATALOG))
    vectors.save(out / "item_vectors.npz")

    def encode(e):
        _, b, depth, d = e
        ids, feat = codec.src(b, depth, vectors)
        return ids, codec.tgt(d, slot_names(b)), feat

    train_p, val_p = [encode(e) for e in train_e], [encode(e) for e in val_e]
    print(f"tokenizer {tok.get_vocab_size()} tokens; target tokens mean {sum(len(p[1]) for p in train_p) / len(train_p):.1f}, "
          f"max {max(len(p[1]) for p in train_p + val_p)}")
    from forge.shippable import build_lexicon
    (out / "lexicon.json").write_text(json.dumps(build_lexicon(
        [d["description"] for _, _, _, d in train_e] + [d["name"] for _, _, _, d in train_e],
        [d["name"] for _, _, _, d in train_e])))
    from resolver.bake.schema import contract_fingerprint
    (out / "meta.json").write_text(json.dumps({"contract_fingerprint": contract_fingerprint(),
                                               "examples": len(train_p)}, indent=1))

    model = Forge(tok.get_vocab_size(), d=a.d, heads=a.heads, enc_layers=a.enc, dec_layers=a.dec,
                  dropout=a.dropout, feat_dim=train_p[0][2].shape[1], max_pos=256).to(a.device)
    print(f"model: {n_params(model) / 1e6:.2f}M params on {a.device}")
    decay = [p for p in model.parameters() if p.dim() >= 2]
    no_decay = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": a.wd}, {"params": no_decay, "weight_decay": 0.0}],
                            lr=a.lr, betas=(0.9, 0.98))
    total = a.epochs * math.ceil(len(train_p) / a.bs)
    warmup = min(400, total // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warmup) * (0.02 + 0.98 * 0.5 * (1 + math.cos(math.pi * min(1.0, s / total)))))
    lo, hi = codec.struct_lo, codec.struct_hi
    demos = demo_builds()[:3]
    best, bad_epochs, log = float("inf"), 0, []
    for ep in range(1, a.epochs + 1):
        model.train()
        t0, tl, tn = time.time(), 0.0, 0
        for src, tin, tout, feat in batches(train_p, a.bs, True, a.device):
            loss = weighted_ce(model(src, tin, feat), tout, lo, hi, a.plan_weight, a.smoothing)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            tl, tn = tl + loss.item(), tn + 1
        model.eval()
        vw, vn = 0.0, 0
        with torch.no_grad():
            for src, tin, tout, feat in batches(val_p, 128, False, a.device):
                vw += weighted_ce(model(src, tin, feat), tout, lo, hi, a.plan_weight, 0.0).item() * len(src)
                vn += len(src)
        vloss = vw / max(vn, 1)
        log.append({"epoch": ep, "train": tl / tn, "val": vloss, "sec": time.time() - t0})
        print(f"ep {ep:3d}  train {tl / tn:.3f}  val {vloss:.3f}  {time.time() - t0:.1f}s", flush=True)
        if vloss < best:
            best, bad_epochs = vloss, 0
            torch.save({"model": model.state_dict(), "config": model.config, "args": vars(a), "epoch": ep,
                        "val_loss": vloss}, out / "best.pt")
        else:
            bad_epochs += 1
        if ep % 10 == 0 or ep == 1:
            for cid, b in demos:
                d = generate(model, codec, b, "DEEP", vectors)
                kinds = " | ".join(f"{s.trigger.value}: " + ",".join(f"{e.kind.value}@{e.target.value}" for e in s.effects)
                                   for s in d.stages)
                print(f"   {cid} -> {d.name!r} [{kinds}] {d.description}")
        if bad_epochs >= a.patience:
            print(f"early stop at epoch {ep} (best val {best:.3f})")
            break
    (out / "train_log.json").write_text(json.dumps(log, indent=1))
    print(f"best val {best:.3f} -> {out / 'best.pt'}")


if __name__ == "__main__":
    main()
