"""CLI harness: runs builds across all six tiers (with repeats at the high
tiers), applies the code-owned clamp, and prints the spread. Runs live with
an API key; degrades to the deterministic fallback with none. This is an
offline generation harness, not a runtime path.
"""
from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from itertools import groupby

from resolver.clamp import apply as clamp_apply
from resolver.contract import GadgetDraft, Tier
from resolver.fallback import resolve as fallback_resolve
from resolver.items import DEFAULT_BUILDS, Build
from resolver.render import RunResult, render_fallback_summary, render_run

ResolverFn = Callable[[Build, Tier], GadgetDraft]

TIERS: list[Tier] = [Tier.DUD, Tier.COMMON, Tier.UNCOMMON, Tier.RARE, Tier.EPIC, Tier.LEGENDARY]
REPEAT_TIERS: list[Tier] = [Tier.RARE, Tier.EPIC, Tier.LEGENDARY]

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_ESCALATE_MODEL = "claude-opus-4-8"


def build_model_list(primary: str, attempts: int, escalate: str | None) -> list[str]:
    """The ordered attempt list for one slot. `attempts` is the total call
    budget; escalation replaces the final attempt (never adds beyond budget).
    e.g. ("sonnet", 3, "opus") -> [sonnet, sonnet, opus]; escalate None or ==
    primary -> [sonnet]*attempts; attempts 1 -> [sonnet] (no room to escalate).
    """
    attempts = max(1, attempts)
    if escalate and escalate != primary and attempts >= 2:
        return [primary] * (attempts - 1) + [escalate]
    return [primary] * attempts


def _label_models(models: list[str]) -> str:
    parts = []
    for model, grp in groupby(models):
        n = sum(1 for _ in grp)
        parts.append(f"{model} x{n}" if n > 1 else model)
    return " -> ".join(parts)


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
                source, reason = "llm", None
            except Exception as exc:
                # A refusal or transport error is a normal, expected outcome for a
                # fraction of builds. Fall back to the deterministic resolver (always
                # a valid instance) and record the slot. We never classify *why*.
                draft = fallback_resolve(build, tier)
                source = "fallback"
                reason = f"{type(exc).__name__}: {exc}"
            resolved = clamp_apply(draft, build, tier)
            results.append(RunResult(key, resolved, counters[tier], totals[tier], source, reason))
    return results


def _build_resolver(
    use_fallback: bool, model: str, attempts: int, escalate: str | None
) -> tuple[ResolverFn, str]:
    if use_fallback or not os.environ.get("ANTHROPIC_API_KEY"):
        return fallback_resolve, "deterministic fallback (no API)"
    import anthropic  # imported lazily so the fallback path needs no SDK auth

    from resolver.llm import LLMResolver

    models = build_model_list(model, attempts, escalate)
    return LLMResolver(anthropic.Anthropic(), models).resolve, f"live LLM ({_label_models(models)})"


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
    parser.add_argument("--attempts", type=int, default=3,
                        help="live LLM attempts per slot before the deterministic fallback (default 3)")
    parser.add_argument("--escalate-model", default=DEFAULT_ESCALATE_MODEL,
                        help="model for the final attempt; 'none' disables escalation "
                             f"(default {DEFAULT_ESCALATE_MODEL})")
    args = parser.parse_args(argv)

    build_keys = args.builds or list(DEFAULT_BUILDS)
    escalate = None if args.escalate_model.lower() == "none" else args.escalate_model
    resolver_fn, label = _build_resolver(args.fallback, args.model, args.attempts, escalate)

    print(f"resolver: {label}")
    print(f"builds:   {', '.join(build_keys)}")
    print(f"repeats:  {args.repeats} per high tier")

    results = run(resolver_fn, build_keys, args.repeats)
    print(render_run(results))
    print()
    print(render_fallback_summary(results))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
