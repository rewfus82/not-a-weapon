"""CLI: python -m resolver.bake <select|run|dedup|report>.

Offline tooling beside the runtime resolvers, never the hot path. select and
report run keyless; run and dedup need a live key and exit loudly without
one — never a silent spend. Windows live runs need PYTHONUTF8=1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from resolver.bake.dedup import dedup_wave, load_registry, save_registry
from resolver.bake.report import wave_report
from resolver.bake.run import load_records, run_wave, write_records
from resolver.bake.select import load_selection, select_combos, write_selection
from resolver.harness import DEFAULT_ESCALATE_MODEL, DEFAULT_MODEL, build_model_list

DATA = Path("data/bake")


def _client_or_none():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic  # lazy: keyless commands need no SDK auth

    return anthropic.Anthropic()


def _add_ladder_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--escalate-model", default=DEFAULT_ESCALATE_MODEL)


def _ladder(args: argparse.Namespace) -> list[str]:
    escalate = None if args.escalate_model.lower() == "none" else args.escalate_model
    return build_model_list(args.model, args.attempts, escalate)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="resolver.bake",
                                     description="Offline bake pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_select = sub.add_parser("select", help="write the reviewable combo selection")
    p_select.add_argument("--n", type=int, default=300)
    p_select.add_argument("--seed", type=int, default=20260717)
    p_select.add_argument("--out", default=str(DATA / "combos-pilot.json"))

    p_run = sub.add_parser("run", help="bake scaffolds for the selection (spends money)")
    p_run.add_argument("--combos", default=str(DATA / "combos-pilot.json"))
    p_run.add_argument("--out", default=str(DATA / "scaffolds.jsonl"))
    p_run.add_argument("--retry-unresolved", action="store_true")
    _add_ladder_args(p_run)

    p_dedup = sub.add_parser("dedup", help="post-wave global rename pass")
    p_dedup.add_argument("--scaffolds", default=str(DATA / "scaffolds.jsonl"))
    p_dedup.add_argument("--names", default=str(DATA / "names.json"))
    p_dedup.add_argument("--events-out", default=str(DATA / "reports" / "rename-events.json"))
    _add_ladder_args(p_dedup)

    p_report = sub.add_parser("report", help="per-wave stats report (offline)")
    p_report.add_argument("--scaffolds", default=str(DATA / "scaffolds.jsonl"))
    p_report.add_argument("--combos", default=str(DATA / "combos-pilot.json"))
    p_report.add_argument("--renames", default=str(DATA / "reports" / "rename-events.json"))
    p_report.add_argument("--wave", default="wave1")
    p_report.add_argument("--out", default="")

    args = parser.parse_args(argv)

    if args.command == "select":
        builds = select_combos(args.n, args.seed)
        write_selection(builds, Path(args.out), args.seed)
        print(f"selected {len(builds)} combos (seed {args.seed}) -> {args.out}")
        print("review the file before running the bake - money moves on `run`.")
        return 0

    if args.command == "run":
        client = _client_or_none()
        if client is None:
            print("ANTHROPIC_API_KEY not set - `run` spends money and needs a live key.")
            return 1
        builds = load_selection(Path(args.combos))
        stats = run_wave(client, _ladder(args), builds, Path(args.out),
                         retry_unresolved=args.retry_unresolved)
        print("rates: " + ", ".join(f"{k} {v}" for k, v in stats.items()))
        return 0

    if args.command == "dedup":
        client = _client_or_none()
        if client is None:
            print("ANTHROPIC_API_KEY not set - `dedup` renames via the live ladder.")
            return 1
        path = Path(args.scaffolds)
        records = list(load_records(path).values())
        registry = load_registry(Path(args.names))
        events = dedup_wave(records, registry, client, _ladder(args))
        write_records(path, {r.combo_id: r for r in records})
        save_registry(Path(args.names), registry)
        events_path = Path(args.events_out)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
        suffixed = sum(1 for e in events if e["outcome"] == "suffixed")
        print(f"renames: {len(events)} (suffixed: {suffixed}) -> {args.events_out}")
        return 0

    # report
    records = list(load_records(Path(args.scaffolds)).values())
    builds = load_selection(Path(args.combos))
    renames_path = Path(args.renames)
    events = (json.loads(renames_path.read_text(encoding="utf-8"))
              if renames_path.exists() else [])
    md = wave_report(records, builds, events, args.wave)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"report -> {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
