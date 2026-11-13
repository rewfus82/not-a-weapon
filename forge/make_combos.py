"""Select a new round of training combos with the repo's own bake selector (e.g. after a catalog wave).

  python -m forge.make_combos --round round1 --shards 20 --per-shard 100 --seed 20261201

Uses resolver.bake.select.select_combos (coverage of every catalog item + shape/coherence strata), drops the held-out
gold set (data/bake/combos-pre30.json) and every combo already in data/forge/combos-*.json, then writes
  data/forge/combos-<round>.json                      combo ids + slots (commit this)
  runs/forge-teacher/<round>/prompts_XX.jsonl        the exact bake user message per combo, for the teacher
A teacher (any LLM, following data/forge/WRITER_GUIDE.md) answers each prompt with a ScaffoldSet line; check shards with
forge.validate_data, then append them to data/forge/scaffolds-<round>.jsonl and retrain.
"""
import argparse
import json

from forge.mechanics import ROOT
from resolver.bake.run import render_bake_message
from resolver.bake.schema import combo_id, contract_fingerprint
from resolver.bake.select import select_combos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shards", type=int, default=20)
    ap.add_argument("--per-shard", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261111)
    ap.add_argument("--round", default="round1")
    a = ap.parse_args()
    need = a.shards * a.per_shard
    gold = {c["combo_id"] for c in json.loads((ROOT / "data/bake/combos-pre30.json").read_text())["combos"]}
    for f in (ROOT / "data/forge").glob("combos-*.json"):  # never re-ask the teacher for a combo we already have
        gold |= {c["combo_id"] for c in json.loads(f.read_text())["combos"]}
    builds = [b for b in select_combos(n=need + len(gold) + 50, seed=a.seed) if combo_id(b) not in gold][:need]
    assert len(builds) == need, f"only {len(builds)} combos selected"
    out = ROOT / "runs/forge-teacher" / a.round
    out.mkdir(parents=True, exist_ok=True)
    combos = [{"combo_id": combo_id(b), "slots": {slot: (it.name if it else None) for slot, it in b.slots()},
               "form": b.delivery.value} for b in builds]
    (ROOT / f"data/forge/combos-{a.round}.json").write_text(json.dumps({"combos": combos}, indent=0))
    for s in range(a.shards):
        rows = [{**c, "prompt": render_bake_message(b)}
                for c, b in zip(combos[s * a.per_shard:(s + 1) * a.per_shard], builds[s * a.per_shard:(s + 1) * a.per_shard])]
        (out / f"prompts_{s:02d}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    shapes = {}
    for b in builds:
        k = sum(1 for _, it in b.slots() if it)
        shapes[k] = shapes.get(k, 0) + 1
    items = {}
    for b in builds:
        for _, it in b.slots():
            if it:
                items[it.name] = items.get(it.name, 0) + 1
    print(f"{need} combos -> {a.shards} shards in {out}; held out {len(gold)} gold combos; "
          f"contract {contract_fingerprint()[:12]}")
    print(f"items per combo: {dict(sorted(shapes.items()))}; item appearances min/max: "
          f"{min(items.values())}/{max(items.values())} over {len(items)} items")


if __name__ == "__main__":
    main()
