"""CLI harness: runs builds across all six tiers (with repeats at the high
tiers), applies the code-owned clamp, and prints the spread. Runs live with
an API key; degrades to the deterministic fallback with none. This is an
offline generation harness, not a runtime path.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable

from resolver.clamp import apply as clamp_apply
from resolver.contract import GadgetDraft, Tier
from resolver.fallback import resolve as fallback_resolve
from resolver.items import DEFAULT_BUILDS, Build
from resolver.render import RunResult, render_run

ResolverFn = Callable[[Build, Tier], GadgetDraft]

TIERS: list[Tier] = [Tier.DUD, Tier.COMMON, Tier.UNCOMMON, Tier.RARE, Tier.EPIC, Tier.LEGENDARY]
REPEAT_TIERS: list[Tier] = [Tier.RARE, Tier.EPIC, Tier.LEGENDARY]

DEFAULT_MODEL = "claude-sonnet-5"


def tier_schedule(repeats: int) -> list[Tier]:
    schedule = list(TIERS)
    for tier in REPEAT_TIERS:
        schedule += [tier] * (repeats - 1)
    return schedule


def run(resolver_fn: ResolverFn, build_keys: list[str], repeats: int) -> list[RunResult]:
    results: list[RunResult] = []
    schedule = tier_schedule(repeats)
    totals: dict[Tier, int] = {t: schedule.count(t) for t in set(schedule)}
    for key in build_keys:
        build = DEFAULT_BUILDS[key]
        # per-tier instance counter so high-tier runs are labelled 1..repeats
        counters: dict[Tier, int] = {}
        for tier in schedule:
            counters[tier] = counters.get(tier, 0) + 1
            try:
                draft = resolver_fn(build, tier)
            except Exception as exc:  # one bad call must not abort the whole run
                # Record the failure as a visible slot (empty stages -> DUD) so
                # the spread still shows which (build, tier) failed and why,
                # rather than losing the other 40+ results.
                draft = GadgetDraft(
                    name="[resolution failed]",
                    description="",
                    logic=f"{type(exc).__name__}: {exc}",
                    stages=[],
                )
            resolved = clamp_apply(draft, build, tier)
            results.append(RunResult(key, resolved, counters[tier], totals[tier]))
    return results


def _build_resolver(use_fallback: bool, model: str) -> tuple[ResolverFn, str]:
    if use_fallback or not os.environ.get("ANTHROPIC_API_KEY"):
        return fallback_resolve, "deterministic fallback (no API)"
    import anthropic  # imported lazily so the fallback path needs no SDK auth

    from resolver.llm import LLMResolver

    return LLMResolver(anthropic.Anthropic(), model).resolve, f"live LLM ({model})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolver dud->god spread harness.")
    parser.add_argument("--build", action="append", dest="builds",
                        choices=list(DEFAULT_BUILDS), help="build key (repeatable; default all)")
    parser.add_argument("--repeats", type=int, default=3,
                        help="runs per high tier (RARE/EPIC/LEGENDARY); default 3")
    parser.add_argument("--model", default=os.environ.get("RESOLVER_MODEL", DEFAULT_MODEL),
                        help="model id (env RESOLVER_MODEL; default claude-sonnet-5)")
    parser.add_argument("--fallback", action="store_true",
                        help="force the deterministic fallback even if a key is set")
    args = parser.parse_args(argv)

    build_keys = args.builds or list(DEFAULT_BUILDS)
    resolver_fn, label = _build_resolver(args.fallback, args.model)

    print(f"resolver: {label}")
    print(f"builds:   {', '.join(build_keys)}")
    print(f"repeats:  {args.repeats} per high tier")

    results = run(resolver_fn, build_keys, args.repeats)
    print(render_run(results))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
