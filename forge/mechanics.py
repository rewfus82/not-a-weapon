"""The mechanics model: a slotted Build + target depth -> the stages/effects/relative weights of a GadgetDraft.

A ~10M-parameter encoder-decoder trained from scratch. It also writes a name + description, but in the shipped
hybrid (forge.writer.Hybrid) only its mechanics are kept and the T5 writer authors the text.
Interface matches the game's resolvers: Mechanics(run).resolve(build, tier) -> GadgetDraft with fill_budget applied
(like resolver.llm.LLMResolver); serve.py then runs clamp.apply, so code still owns every number.

Source:  <form:SPRAY> <depth:MEDIUM> <slot:delivery> <it:fire extinguisher> <slot:damage> <empty> ...
         (+ a Model2Vec vector of each item's association cloud on its item token)
Target:  <stage> <trig:ON_HIT> <fx> <k:DAMAGE> <t:STRUCK> <b6> <b0> <b0> <c0> <fx> ... <stage> ...
         <name> Overtime <desc> A slugger's <i0> wired to a dying <i3> ... <eos>
Magnitudes are relative: floats are scaled so the largest is 32, then bucketed by powers of two.
"""
import json
import re
from pathlib import Path

import numpy as np
import torch

from resolver.clamp import fill_budget
from resolver.contract import Delivery, Effect, EffectKind, GadgetDraft, Stage, Target, Tier, Trigger
from resolver.items import CATALOG, Build

from forge.text import relex

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models/forge"  # mechanics/ + writer/ (python -m forge.fetch)
SLOTS = ("delivery", "damage", "utility", "modifier")
DEPTHS = ("SHALLOW", "MEDIUM", "DEEP")
TIER_DEPTH = {"DUD": "SHALLOW", "COMMON": "SHALLOW", "UNCOMMON": "MEDIUM", "RARE": "MEDIUM",
              "EPIC": "DEEP", "LEGENDARY": "DEEP"}
DEPTH_TIER = {"SHALLOW": "COMMON", "MEDIUM": "RARE", "DEEP": "LEGENDARY"}  # tier used to clamp a teacher reading
EDGES = [0.5, 1, 2, 4, 8, 16, 32, 64, 128]          # bucket k (1..9) = (EDGES[k-2], EDGES[k-1]]; b10 > 128
REP = [0.0, 0.35, 0.75, 1.5, 3, 6, 12, 24, 48, 96, 180]
SCALE_TO = 32.0
MAX_STAGES, MAX_FX, MAX_COUNT = 4, 4, 8
_DIRECT = {"ON_USE", "ON_HIT", "ON_IMPACT"}
FIRING = {"PLACED": {"ON_TRIGGER"}, "GUARD": {"ON_USE", "ON_BLOCK"}, "SELF": {"ON_USE", "ON_HIT"},
          "DASH": {"ON_USE", "ON_HIT"}}
SELF_ILLEGAL = {"ON_IMPACT", "ON_TRIGGER", "ON_BLOCK"}
SELF_TARGET_ONLY = {"ON_USE", "ON_EXPIRE", "ON_KILL"}

BASE = ["<pad>", "<unk>", "<bos>", "<eos>", "<name>", "<desc>", "<empty>"]
FORM_T = [f"<form:{d.value}>" for d in Delivery]
DEPTH_T = [f"<depth:{d}>" for d in DEPTHS]
SLOT_T = [f"<slot:{s}>" for s in SLOTS]
ITEM_T = [f"<it:{n}>" for n in sorted(CATALOG)] + ["<it:?>"]
STRUCT = (["<stage>", "<fx>"] + [f"<trig:{t.value}>" for t in Trigger] + [f"<k:{k.value}>" for k in EffectKind]
          + [f"<t:{t.value}>" for t in Target] + [f"<b{i}>" for i in range(len(REP))]
          + [f"<c{i}>" for i in range(MAX_COUNT + 1)])
ISLOT_T = [f"<i{k}>" for k in range(len(SLOTS))]
SPECIALS = BASE + FORM_T + DEPTH_T + SLOT_T + ITEM_T + STRUCT + ISLOT_T
PAD, UNK, BOS, EOS, NAME, DESC, EMPTY = range(7)


def bucket(v):
    if v <= 0:
        return 0
    for k, e in enumerate(EDGES, 1):
        if v <= e:
            return k
    return len(REP) - 1


def item_text(name):
    it = CATALOG.get(name)
    return f"{name}: {it.describe()}" if it else name


def build_from_names(names):
    """Positional craft, like serve.build_from_items: names[0] is the delivery chassis."""
    slots = dict.fromkeys(SLOTS)
    for slot, n in zip(SLOTS, names):
        slots[slot] = CATALOG[n]
    return Build(delivery_item=slots["delivery"], damage_item=slots["damage"],
                 utility_item=slots["utility"], modifier_item=slots["modifier"])


def slot_names(build):
    return [it.name if it else None for _, it in build.slots()]


def delex_slots(text, names):
    """Replace every alias of each present item with its slot token <iK> (longest alias first)."""
    from forge.shippable import ALIASES
    pairs = [(a, k) for k, n in enumerate(names) if n for a in set(ALIASES.get(n, []) + [n])]
    for a, k in sorted(pairs, key=lambda p: (-len(p[0]), p[1])):
        text = re.sub(r"(?<![\w<-])" + re.escape(a) + r"(?![\w>-])", f"<i{k}>", text, flags=re.IGNORECASE)
    return text


def display(name):
    """Short natural surface form used when re-inserting a slot (first alias), e.g. 'jerrycan'."""
    from forge.shippable import ALIASES
    return ALIASES.get(name, [name])[0] if name else "something"


class ItemVectors:
    """Model2Vec vectors of each catalog item's association cloud (precomputed table, shipped with the model)."""

    def __init__(self, path=None):
        self.table = {}
        if path and Path(path).exists():
            z = np.load(path, allow_pickle=False)
            self.table = dict(zip(z["names"].tolist(), z["vecs"]))

    def ensure(self, names):
        missing = sorted({n for n in names if n and n not in self.table})
        if missing:
            from forge.text import ItemEmbedder
            vecs = ItemEmbedder()._model().encode([item_text(n) for n in missing])
            self.table.update(zip(missing, vecs))

    def __getitem__(self, name):
        return self.table[name]

    def save(self, path):
        names = sorted(self.table)
        np.savez(path, names=np.array(names), vecs=np.stack([self.table[n] for n in names]).astype("float32"))


class GameCodec:
    def __init__(self, tok):
        self.tok = tok
        self.id = {s: tok.token_to_id(s) for s in SPECIALS}
        assert all(self.id[s] == i for i, s in enumerate(SPECIALS)), "tokenizer special ids out of order"
        self.n_special = len(SPECIALS)
        self.struct_lo, self.struct_hi = self.id[STRUCT[0]], self.id[STRUCT[-1]]
        g = lambda prefix: [self.id[s] for s in SPECIALS if s.startswith(prefix)]  # noqa: E731
        self.trig_ids, self.kind_ids, self.tgt_ids = g("<trig:"), g("<k:"), g("<t:")
        self.b_ids, self.c_ids, self.islot_ids = g("<b"), g("<c"), [self.id[s] for s in ISLOT_T]

    def text(self, s):
        return self.tok.encode(s, add_special_tokens=False).ids

    def src(self, build, depth, vectors):
        names = slot_names(build)
        ids = [self.id[f"<form:{build.delivery.value}>"], self.id[f"<depth:{depth}>"]]
        feat_rows = [None, None]
        for slot, n in zip(SLOTS, names):
            ids.append(self.id[f"<slot:{slot}>"])
            feat_rows.append(None)
            ids.append(self.id.get(f"<it:{n}>", self.id["<it:?>"]) if n else EMPTY)
            feat_rows.append(n)
        vectors.ensure(names)
        dim = len(next(iter(vectors.table.values())))
        feat = np.stack([vectors[n] if n else np.zeros(dim, "float32") for n in feat_rows]).astype("float32")
        return ids, feat

    def tgt(self, draft, names):
        floats = [v for s in draft["stages"] for e in s["effects"] for v in (e["amount"], e["duration"], e["radius"])]
        scale = SCALE_TO / max(floats) if floats and max(floats) > 0 else 1.0
        out = []
        for s in draft["stages"]:
            out += [self.id["<stage>"], self.id[f"<trig:{s['trigger']}>"]]
            for e in s["effects"]:
                out += [self.id["<fx>"], self.id[f"<k:{e['kind']}>"], self.id[f"<t:{e['target']}>"]]
                out += [self.id[f"<b{bucket(e[f] * scale)}>"] for f in ("amount", "duration", "radius")]
                out.append(self.id[f"<c{min(MAX_COUNT, int(e['count']))}>"])
        desc = delex_slots(draft["description"], names)
        return out + [NAME] + self.text(draft["name"]) + [DESC] + self.text(desc) + [EOS]

    def to_draft(self, ids, names):
        inv = {v: k for k, v in self.id.items()}
        stages, i = [], 0
        while i < len(ids) and ids[i] == self.id["<stage>"]:
            trig = inv[ids[i + 1]].split(":")[1][:-1]
            i += 2
            effects = []
            while i < len(ids) and ids[i] == self.id["<fx>"]:
                kind, tgt = inv[ids[i + 1]][3:-1], inv[ids[i + 2]][3:-1]
                vals = [REP[int(inv[ids[i + j]][2:-1])] for j in (3, 4, 5)]
                count = int(inv[ids[i + 6]][2:-1])
                effects.append(Effect(kind=EffectKind(kind), target=Target(tgt), amount=vals[0], duration=vals[1],
                                      radius=vals[2], count=count, note=""))
                i += 7
            stages.append(Stage(trigger=Trigger(trig), effects=effects, note=""))
        rest = ids[i:]
        name_ids = rest[1:rest.index(DESC)] if DESC in rest else rest[1:]
        desc_ids = rest[rest.index(DESC) + 1:] if DESC in rest else []
        if EOS in desc_ids:
            desc_ids = desc_ids[:desc_ids.index(EOS)]
        desc = self.tok.decode(desc_ids, skip_special_tokens=False).strip()
        desc = re.sub(r"(<i\d>) (?=['’,.;:!?)\-])", r"\1", desc)
        filled = [display(n) for n in names]
        return GadgetDraft(name=self.tok.decode(name_ids).strip(), description=relex(desc, filled), logic="",
                           stages=stages)


@torch.no_grad()
def generate(model, codec, build, depth, vectors, seed=None, temperature=0.9, min_p=0.1, max_name=12, max_desc=64):
    """Grammar-constrained decoding (forge.grammar): every output parses, is legal for the chassis, and fires."""
    from forge.sampling import pick as _pick
    from forge.grammar import Grammar
    device = next(model.parameters()).device
    vocab = model.config["vocab"]
    ids, feat = codec.src(build, depth, vectors)
    mem, mask = model.encode(torch.tensor([ids], device=device), torch.from_numpy(feat)[None].to(device))
    gen = torch.Generator().manual_seed(seed) if seed is not None else None
    text_mask = torch.zeros(vocab, dtype=torch.bool)
    text_mask[codec.n_special:] = True
    g = Grammar(codec.id, EOS, text_mask, build, max_name=max_name, max_desc=max_desc)
    out = []
    for _ in range(model.config["max_pos"] - 2):
        allowed = g.allowed(out)
        if int(allowed.sum()) == 1:
            tok = int(allowed.nonzero()[0])
        else:
            logits = model.decode(torch.tensor([[BOS] + out], device=device), mem, mask)[0, -1].float().cpu()
            tok = _pick(logits, allowed, gen, temperature, min_p)
        out.append(tok)
        if tok == EOS:
            break
    return codec.to_draft(out, slot_names(build))


class Mechanics:
    """Resolver for the game repo: resolve(build, tier) -> GadgetDraft (fill_budget applied, like LLMResolver)."""

    def __init__(self, run, threads=1):
        from forge.text import load_tokenizer
        from forge.model import Forge
        run = Path(run)
        torch.set_num_threads(threads)
        self.ck = torch.load(run / "best.pt", map_location="cpu", weights_only=True)  # tensors + plain values only
        self.model = Forge(**self.ck["config"]).eval()
        self.model.load_state_dict(self.ck["model"])
        self.codec = GameCodec(load_tokenizer(run / "tokenizer.json", SPECIALS))
        self.vectors = ItemVectors(run / "item_vectors.npz")
        meta = json.loads((run / "meta.json").read_text())
        from forge.shippable import Checker
        self.checker = Checker(json.loads((run / "lexicon.json").read_text()))
        self.last_issues, self.last_tries = {}, 0
        from resolver.bake.schema import contract_fingerprint
        if meta["contract_fingerprint"] != contract_fingerprint():
            raise RuntimeError("model was trained against a different capability contract - retrain it")

    def draft(self, build, depth, seed=None, temperature=0.9, min_p=0.1):
        return generate(self.model, self.codec, build, depth, self.vectors, seed=seed, temperature=temperature,
                        min_p=min_p)

    def resolve(self, build, tier, seed=None, n=8):
        """Best-of-n: sample up to n candidates (deterministic seeds per combo+tier), keep the first shippable one."""
        from forge.shippable import best_of
        from resolver.bake.schema import combo_id
        from forge.sampling import combo_seed
        tier = Tier(tier)
        depth = TIER_DEPTH[tier.value]
        base = seed if seed is not None else combo_seed([combo_id(build), tier.value])
        draft, self.last_issues, self.last_tries, self.first_issues = best_of(
            n, lambda i: self.draft(build, depth, seed=base + i), build, self.checker)
        return fill_budget(draft, tier)
