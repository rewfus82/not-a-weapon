"""Evaluate Forge resolvers on the held-out Sonnet bake (data/bake/*-pre30: never trained on), against the fallback.

  python -m forge.evaluate                                   # the shipped models/forge
  python -m forge.evaluate runs/forge-mechanics hybrid:runs/forge-mechanics+runs/forge-writer [--seeds 3] [--n 8]

Per gold combo x depth x seed:
  - shippability: nonwords (oov), foreign item mentions, names copied from training; for a single sample (n=1)
    and after best-of-n selection (what would actually be frozen into the library)
  - legality / firing / resolves through clamp.apply
  - closeness to Sonnet's composition (effect-kind / kind@target / trigger Jaccard, same derived category)
  - depth ladder (effects per reading) and latency
"""
import argparse
import json
import statistics
import time

from forge import quiet
from forge.grammar import DIRECT, FIRING
from forge.mechanics import DEPTH_TIER, DEPTHS, ROOT
from forge.sampling import combo_seed
from forge.shippable import HARD, Checker
from forge.train_mechanics import build_from_slots
from forge.writer import load_resolver
from resolver.clamp import apply as clamp_apply, derive_category
from resolver.contract import GadgetDraft, Tier
from resolver.fallback import resolve as fallback_resolve
from resolver.validate import repair


def sig(d):
    return [(s.trigger.value, [(e.kind.value, e.target.value) for e in s.effects]) for s in d.stages]


def sets(d):
    return ({e.kind.value for s in d.stages for e in s.effects},
            {f"{e.kind.value}@{e.target.value}" for s in d.stages for e in s.effects},
            {s.trigger.value for s in d.stages})


def jac(a, b):
    return len(a & b) / len(a | b) if a | b else 1.0


def score(d, gold, build, tier):
    legal = sig(repair(d, build)) == sig(d)
    fires = any(s.trigger.value in FIRING.get(build.delivery.value, DIRECT) for s in d.stages)
    cat = clamp_apply(d, build, tier).category.value
    k, p, t = sets(d)
    gk = [sets(g) for g in gold]
    gcat = {derive_category(clamp_apply(g, build, tier).draft).value for g in gold}
    return {"legal": legal, "fires": fires, "kind_j": max(jac(k, x[0]) for x in gk),
            "pair_j": max(jac(p, x[1]) for x in gk), "trig_j": max(jac(t, x[2]) for x in gk),
            "same_category": cat in gcat, "n_fx": sum(len(s.effects) for s in d.stages)}


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*", help="model specs (default: the shipped models/forge)")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--max-items", type=int, default=0, help="limit gold combos (smoke tests)")
    a = ap.parse_args()
    quiet()
    sel = {c["combo_id"]: c["slots"] for c in json.loads((ROOT / "data/bake/combos-pre30.json").read_text())["combos"]}
    gold = []
    for line in (ROOT / "data/bake/scaffolds-pre30.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["status"] == "resolved":
            gold.append((r["combo_id"], build_from_slots(sel[r["combo_id"]]),
                         {dp: [GadgetDraft.model_validate(x) for x in r["scaffolds"][dp]] for dp in DEPTHS}))
    if a.max_items:
        gold = gold[:a.max_items]
    label = lambda r: f"forge:{str(r).rstrip('/').split('/')[-1]}" if r and not str(r).startswith("hybrid:") \
        else "forge:hybrid"  # noqa: E731
    models = {label(r): load_resolver(r) for r in (a.runs or [None])}
    checker = next(iter(models.values())).checker
    rows = {"sonnet 2nd draft": [], "fallback": [], **{n: [] for n in models}}
    ship = {n: {"n1": [], "best": [], "tries": []} for n in models}
    foreign = {"sonnet 2nd draft": [], "fallback": []}
    lat = {n: [] for n in models}
    for cid, build, gd in gold:
        for di, depth in enumerate(DEPTHS):
            tier = Tier(DEPTH_TIER[depth])
            g = gd[depth]
            if len(g) > 1:
                rows["sonnet 2nd draft"].append({**score(g[1], g[:1], build, tier), "depth": di})
                foreign["sonnet 2nd draft"].append("foreign" in checker.issues(g[1], build))
            fb = fallback_resolve(build, tier)
            rows["fallback"].append({**score(fb, g, build, tier), "depth": di})
            foreign["fallback"].append("foreign" in checker.issues(fb, build))
            for name, m in models.items():
                for s in range(a.seeds):
                    t0 = time.perf_counter()
                    d = m.resolve(build, tier.value, seed=combo_seed([cid, depth, str(s)]), n=a.n)
                    lat[name].append((time.perf_counter() - t0) * 1000)
                    rows[name].append({**score(d, g, build, tier), "depth": di})
                    ship[name]["n1"].append(m.first_issues)
                    ship[name]["best"].append(m.last_issues)
                    ship[name]["tries"].append(m.last_tries)
    systems = list(rows)
    w = 34
    print(f"held-out: {len(gold)} combos x 3 depths (game repo pre30 Sonnet bake); models: {a.seeds} seeds, best-of-{a.n}\n")
    print(f"{'':{w}}" + "".join(f"{n:>24}" for n in systems))

    def line(label, fn, fmt="{:.0%}"):
        print(f"{label:{w}}" + "".join(f"{fn(n):>24}" for n in systems))

    na = lambda f: (lambda n: f(n) if n in models else "-")  # noqa: E731
    print("-- shippability (lower is better)")
    for k in HARD:
        line(f"single sample: {k}", na(lambda n, k=k: f"{mean([k in x for x in ship[n]['n1']]):.0%}"))
    line("single sample: any hard issue", na(lambda n: f"{mean([any(k in x for k in HARD) for x in ship[n]['n1']]):.0%}"))
    line(f"best-of-{a.n}: any hard issue", na(lambda n: f"{mean([any(k in x for k in HARD) for x in ship[n]['best']]):.0%}"))
    line(f"best-of-{a.n}: mean candidates tried", na(lambda n: f"{mean(ship[n]['tries']):.1f}"))
    line("names a foreign item (all systems)", lambda n: f"{mean([('foreign' in x) for x in ship[n]['best']]):.0%}"
         if n in models else f"{mean(foreign[n]):.0%}")
    print("-- mechanics")
    for label, k, kind in [("legal (no repair needed)", "legal", "%"), ("has a firing trigger", "fires", "%"),
                           ("effect-kind overlap w/ Sonnet", "kind_j", "j"), ("kind@target overlap", "pair_j", "j"),
                           ("trigger overlap", "trig_j", "j"), ("same category as Sonnet", "same_category", "%")]:
        line(label, lambda n, k=k, kind=kind: (f"{mean([r[k] for r in rows[n]]):.0%}" if kind == "%"
                                               else f"{mean([r[k] for r in rows[n]]):.2f}"))
    line("effects/reading SHALLOW-MED-DEEP", lambda n: "-".join(
        f"{mean([r['n_fx'] for r in rows[n] if r['depth'] == di]):.1f}" for di in range(3)))
    print()
    for n in models:
        print(f"{n}: latency per resolve (best-of-{a.n}, 1 CPU thread, PyTorch eager): median "
              f"{statistics.median(lat[n]):.0f} ms, p90 {sorted(lat[n])[int(0.9 * len(lat[n]))]:.0f} ms")


if __name__ == "__main__":
    main()
