"""Validate a shard of teacher-written ScaffoldSets against the game repo's own schema and code.

  python -m forge.validate_data runs/forge-teacher/round1/shard_03.jsonl [--final]

Checks: the repo's pydantic ScaffoldSet (enums, required targets), its legality repair must be a no-op
(write legal trigger/target combos, don't rely on repair), clamp.apply must resolve at the depth's tier,
plus length/variety rules. Exit 0 = no errors; warnings never fail.
"""
import collections
import json
import math
import re
import sys
from pathlib import Path

from forge.mechanics import DEPTH_TIER, DEPTHS
from resolver.bake.schema import ScaffoldSet
from resolver.bake.select import load_selection  # noqa: F401
from resolver.clamp import apply as clamp_apply
from resolver.contract import EffectKind, Tier
from resolver.items import CATALOG, Build
from resolver.validate import repair

MECHANIC_WORDS = {k.value.lower() for k in EffectKind} | {"launcher", "projectile", "hitscan"}
DAMAGE_KINDS = {"DAMAGE", "BURN", "EXPLODE", "SUMMON"}
# Triggers the game's renderer actually fires per delivery form (game/Source/NotAWeapon/NAWGadget*.cpp).
# Every reading needs at least one stage on one of these, or the player gets a dead gadget.
_DIRECT = {"ON_USE", "ON_HIT", "ON_IMPACT"}
FIRING = {"PLACED": {"ON_TRIGGER"}, "GUARD": {"ON_USE", "ON_BLOCK"}, "SELF": {"ON_USE", "ON_HIT"},
          "DASH": {"ON_USE", "ON_HIT"}}


def build_of(slots):
    item = lambda k: CATALOG[slots[k]] if slots.get(k) else None  # noqa: E731
    return Build(delivery_item=CATALOG[slots["delivery"]], damage_item=item("damage"),
                 utility_item=item("utility"), modifier_item=item("modifier"))


def stage_sig(draft):
    return [(s.trigger.value, [(e.kind.value, e.target.value) for e in s.effects]) for s in draft.stages]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = Path(sys.argv[1]).resolve()
    final = "--final" in sys.argv
    combos = {}
    for line in Path(str(path).replace("/crafts/", "/combos/")).read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            combos[c["combo_id"]] = c
    errors, warnings, seen = [], [], set()
    names, descs = collections.Counter(), collections.Counter()
    n_ok = 0
    for ln, line in enumerate(path.read_text().splitlines() if path.exists() else [], 1):
        if not line.strip():
            continue
        before = len(errors)

        def err(m):
            errors.append(f"line {ln}: {m}")

        def warn(m):
            warnings.append(f"line {ln}: {m}")

        try:
            r = json.loads(line)
        except json.JSONDecodeError as e:
            err(f"invalid JSON ({e})")
            continue
        if not isinstance(r, dict) or sorted(r) != ["combo_id", "scaffolds"]:
            err("keys must be exactly ['combo_id', 'scaffolds']")
            continue
        cid = r["combo_id"]
        if cid not in combos:
            err(f"unknown combo_id {cid!r}")
            continue
        if cid in seen:
            err(f"duplicate combo_id {cid}")
            continue
        seen.add(cid)
        sc = r["scaffolds"]
        if not isinstance(sc, dict) or sorted(sc) != sorted(DEPTHS):
            err(f"{cid}: scaffolds must have exactly the keys {list(DEPTHS)}")
            continue
        try:
            ss = ScaffoldSet.model_validate({"shallow": sc["SHALLOW"], "medium": sc["MEDIUM"], "deep": sc["DEEP"]})
        except Exception as e:  # pydantic ValidationError
            msg = str(e).replace("\n", " | ")
            err(f"{cid}: schema error: {msg[:300]}")
            continue
        build = build_of(combos[cid]["slots"])
        drafts = {"SHALLOW": ss.shallow, "MEDIUM": ss.medium, "DEEP": ss.deep}
        seen_names = set()
        for depth, d in drafts.items():
            tag = f"{cid} {depth}"
            if not 1 <= len(d.stages) <= 4:
                err(f"{tag}: 1-4 stages required (got {len(d.stages)})")
            for s in d.stages:
                if not 1 <= len(s.effects) <= 4:
                    err(f"{tag}: each stage needs 1-4 effects (got {len(s.effects)})")
                for e in s.effects:
                    vals = (e.amount, e.duration, e.radius)
                    if any(not math.isfinite(v) or v < 0 or v > 1000 for v in vals) or not 0 <= e.count <= 8:
                        err(f"{tag}: magnitudes must be finite, 0..1000, count 0..8 ({e.kind.value})")
            firing = FIRING.get(build.delivery.value, _DIRECT)
            if not any(s.trigger.value in firing for s in d.stages):
                err(f"{tag}: dead gadget - a {build.delivery.value} chassis needs at least one stage on "
                    f"{sorted(firing)}")
            if stage_sig(repair(d, build)) != stage_sig(d):
                err(f"{tag}: illegal trigger/target for the {build.delivery.value} chassis (repair would change "
                    f"it) - see 'Trigger semantics' in data/forge/WRITER_GUIDE.md")
            try:
                clamp_apply(d, build, Tier(DEPTH_TIER[depth]))
            except Exception as e:
                err(f"{tag}: does not resolve through clamp.apply ({type(e).__name__}: {e})")
            nw = d.name.split()
            if not d.name.strip() or len(nw) > 5 or len(d.name) > 40:
                err(f"{tag}: name must be 1-5 words, <=40 chars: {d.name!r}")
            if d.name.lower() in seen_names:
                err(f"{tag}: the three readings need different names ({d.name!r})")
            seen_names.add(d.name.lower())
            if set(re.findall(r"[a-z]+", d.name.lower())) & MECHANIC_WORDS:
                warn(f"{tag}: mechanic word in name {d.name!r} (prompt says give it character instead)")
            dw = len(d.description.split())
            if not 8 <= dw <= 40 or "\n" in d.description:
                err(f"{tag}: description must be one line of 8-40 words (got {dw})")
            lw = len(d.logic.split())
            if not 5 <= lw <= 45:
                err(f"{tag}: logic must be a short trace of 5-45 words (got {lw})")
            kinds = {e.kind.value for s in d.stages for e in s.effects}
            if kinds & {"PIERCE", "CHAIN"} and not kinds & DAMAGE_KINDS:
                warn(f"{tag}: PIERCE/CHAIN without a damage effect (coherence rule)")
            names[d.name.lower()] += 1
            descs[d.description.strip().lower()] += 1
        n_eff = {k: sum(len(s.effects) for s in v.stages) + len(v.stages) - 1 for k, v in drafts.items()}
        if n_eff["SHALLOW"] > n_eff["DEEP"]:
            warn(f"{cid}: SHALLOW is more complex than DEEP")
        if len(errors) == before:
            n_ok += 1
    total = sum(names.values()) or 1
    dups = {n: c for n, c in names.items() if c > 1}
    if sum(c - 1 for c in dups.values()) / total > 0.03:
        errors.append(f"too many duplicate names (>3%): {sorted(dups.items(), key=lambda x: -x[1])[:8]}")
    if [d for d, c in descs.items() if c > 1]:
        errors.append("duplicate descriptions found")
    missing = [c for c in combos if c not in seen]
    print(f"{path}: {len(seen)}/{len(combos)} combos written, {n_ok} fully valid, {len(errors)} errors, "
          f"{len(warnings)} warnings, {len(missing)} missing")
    if final and missing:
        errors.append(f"{len(missing)} combos missing, first: {missing[:3]}")
    for e in (errors if "--all" in sys.argv else errors[:40]):
        print("ERROR", e)
    for w in warnings[:12]:
        print("WARN ", w)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
