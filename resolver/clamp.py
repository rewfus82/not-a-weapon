"""The deterministic clamp: code owns balance.

Re-derives `harmless` and `category` from the effects the model actually
produced (never trusted from the model) and enforces a per-tier magnitude
budget with the ~10-15% over-budget cap from GAME_IDENTITY §6. The tier
budget numbers are v0 placeholders owned by code; they will churn once the
renderer is real. The job here is to prove the model->code ownership split
works end to end, not to finalize balance.
"""
from __future__ import annotations

import copy

from resolver.contract import (
    Category, Effect, EffectKind, GadgetDraft, ResolvedGadget, Target, Tier,
    LETHAL_KINDS, CONTROL_KINDS, SELF_KINDS, UTILITY_KINDS,
)
from resolver.items import Build, params_for
from resolver.validate import repair

TIER_BUDGET: dict[Tier, float] = {
    Tier.DUD: 6.0,
    Tier.COMMON: 16.0,
    Tier.UNCOMMON: 28.0,
    Tier.RARE: 48.0,
    Tier.EPIC: 80.0,
    Tier.LEGENDARY: 120.0,
}
OVER_BUDGET_FACTOR: float = 1.12  # the ~10-15% over-budget cap
DUD_FLOOR: float = 1.0            # a DUD is pathetic, never literally nothing

# Exchange rates: what one unit of each field costs against the tier budget.
# Structure now, values later — deliberately crude placeholders (> 0 is the
# point: duration and count can no longer ride free on a full damage budget).
# Tuning any of these is a deterministic re-clamp, never a re-bake. W_AMOUNT
# is per-kind so the self-family rate (heal-80 vs damage-80) is a named knob.
W_AMOUNT: dict[EffectKind, float] = {k: 1.0 for k in EffectKind}
W_DURATION: float = 2.0
W_RADIUS: float = 0.5
W_COUNT: float = 3.0


def effect_cost(effect: Effect) -> float:
    return (effect.amount * W_AMOUNT[effect.kind]
            + effect.duration * W_DURATION
            + effect.radius * W_RADIUS
            + effect.count * W_COUNT)


def total_cost(draft: GadgetDraft) -> float:
    return sum(effect_cost(e) for stage in draft.stages for e in stage.effects)


def _scale(draft: GadgetDraft, factor: float) -> GadgetDraft:
    out = copy.deepcopy(draft)
    for stage in out.stages:
        for e in stage.effects:
            e.amount *= factor
            e.duration *= factor
            e.radius *= factor
    return out


def _count_cost(draft: GadgetDraft) -> float:
    return sum(e.count * W_COUNT for stage in draft.stages for e in stage.effects)


def _fit(draft: GadgetDraft, target_total: float) -> GadgetDraft:
    """Scale so total_cost lands on target_total: the float fields share one
    factor (proportions preserved); counts are integers with fixed cost and
    only floor-scale down when their cost alone exceeds the target (small
    under-budget residue from the integer floor is acceptable)."""
    out = copy.deepcopy(draft)
    counts = _count_cost(out)
    if counts > target_total:
        factor = target_total / counts
        for stage in out.stages:
            for e in stage.effects:
                e.count = int(e.count * factor)
        counts = _count_cost(out)
    floats = total_cost(out) - counts
    if floats <= 0:
        return out
    return _scale(out, (target_total - counts) / floats)


def clamp_magnitudes(draft: GadgetDraft, tier: Tier) -> GadgetDraft:
    total = total_cost(draft)
    if total == 0:
        return copy.deepcopy(draft)
    cap = TIER_BUDGET[tier] * OVER_BUDGET_FACTOR
    if total > cap:
        return _fit(draft, cap)
    if total < DUD_FLOOR:
        return _fit(draft, DUD_FLOOR)
    return copy.deepcopy(draft)


def fill_budget(draft: GadgetDraft, tier: Tier) -> GadgetDraft:
    """Scale a draft so its weighted cost lands exactly on the tier budget,
    preserving the composition's proportions. The LLM path calls this on
    parsed drafts (models free-hand magnitudes); the deterministic composer
    already fills the budget by construction. Zero-cost drafts pass through —
    there are no proportions to scale. Never called from `apply` — solo
    stays pathetic.
    """
    total = total_cost(draft)
    if total == 0:
        return copy.deepcopy(draft)
    return _fit(draft, TIER_BUDGET[tier])


def fit_cost(draft: GadgetDraft, target_total: float) -> GadgetDraft:
    """Public fit for offline tooling (the bake deriver): scale the draft so
    its weighted cost lands on target_total. Zero-cost drafts pass through —
    there are no proportions to scale."""
    if total_cost(draft) == 0:
        return copy.deepcopy(draft)
    return _fit(draft, target_total)


def _pairs(draft: GadgetDraft) -> set[tuple[EffectKind, Target]]:
    return {(e.kind, e.target) for stage in draft.stages for e in stage.effects}


def derive_harmless(draft: GadgetDraft) -> bool:
    """Harmless = can't hurt others: no lethal kind aimed at STRUCK.
    Hurting yourself is a cost, not a threat."""
    return not any(k in LETHAL_KINDS and t is Target.STRUCK for k, t in _pairs(draft))


def derive_category(draft: GadgetDraft) -> Category:
    pairs = _pairs(draft)
    if not pairs:
        return Category.DUD
    if any(k in LETHAL_KINDS and t is Target.STRUCK for k, t in pairs):
        return Category.WEAPON
    if any(k in CONTROL_KINDS and t is Target.STRUCK for k, t in pairs):
        return Category.CONTROL
    if any(k in SELF_KINDS or (t is Target.SELF and k not in UTILITY_KINDS)
           for k, t in pairs):
        return Category.SUPPORT
    if any(k in UTILITY_KINDS for k, _ in pairs):
        return Category.UTILITY
    return Category.TRINKET


def apply(draft: GadgetDraft, build: Build, tier: Tier) -> ResolvedGadget:
    clamped = clamp_magnitudes(repair(draft, build), tier)
    return ResolvedGadget(
        draft=clamped,
        delivery=build.delivery,
        tier=tier,
        category=derive_category(clamped),
        harmless=derive_harmless(clamped),
        color=build.color,
        params=params_for(build.delivery),
    )
