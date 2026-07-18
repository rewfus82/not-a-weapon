"""derive_instance: the pure scaffold->instance function.

Same (draft, build, tier, seed) -> byte-identical ResolvedGadget, forever.
The scaffold is the stored truth; instances are always computed, never
stored mutated. Rebalance = edit the clamp tables and re-run this over the
frozen library — re-clamp, never re-bake. Game-side, the acquisition roll
picks (scaffold alternate, tier, seed) and extraction freezes the triple:
acquisition random, combat deterministic, by construction.
"""
from __future__ import annotations

import random

from resolver.bake.schema import Depth
from resolver.clamp import (
    DUD_FLOOR, OVER_BUDGET_FACTOR, TIER_BUDGET,
    derive_category, derive_harmless, fit_cost,
)
from resolver.contract import GadgetDraft, ResolvedGadget, Tier
from resolver.items import Build, params_for
from resolver.validate import repair

# Adjacent tiers share a composition at different budgets.
DEPTH_TIERS: dict[Depth, tuple[Tier, Tier]] = {
    Depth.SHALLOW: (Tier.DUD, Tier.COMMON),
    Depth.MEDIUM: (Tier.UNCOMMON, Tier.RARE),
    Depth.DEEP: (Tier.EPIC, Tier.LEGENDARY),
}

# Placeholder values, renderer-era tuning (same rule as W_DURATION):
JITTER = 0.10      # per-effect float perturbation — the intra-tier variance
BUDGET_LOW = 0.90  # bottom of the seeded budget band; top is OVER_BUDGET_FACTOR


def derive_instance(draft: GadgetDraft, build: Build, tier: Tier, seed: int) -> ResolvedGadget:
    rng = random.Random(seed)
    out = repair(draft, build)  # deep-copies; the input is never mutated
    for stage in out.stages:
        for effect in stage.effects:
            effect.amount *= rng.uniform(1 - JITTER, 1 + JITTER)
            effect.duration *= rng.uniform(1 - JITTER, 1 + JITTER)
            effect.radius *= rng.uniform(1 - JITTER, 1 + JITTER)
    point = TIER_BUDGET[tier] * rng.uniform(BUDGET_LOW, OVER_BUDGET_FACTOR)
    out = fit_cost(out, max(DUD_FLOOR, point))
    return ResolvedGadget(
        draft=out,
        delivery=build.delivery,
        tier=tier,
        category=derive_category(out),
        harmless=derive_harmless(out),
        color=build.color,
        params=params_for(build.delivery),
    )
