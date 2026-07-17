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
    Category, EffectKind, GadgetDraft, ResolvedGadget, Target, Tier,
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


def total_magnitude(draft: GadgetDraft) -> float:
    return sum(e.amount for stage in draft.stages for e in stage.effects)


def _scale(draft: GadgetDraft, factor: float) -> GadgetDraft:
    out = copy.deepcopy(draft)
    for stage in out.stages:
        for e in stage.effects:
            e.amount *= factor
    return out


def clamp_magnitudes(draft: GadgetDraft, tier: Tier) -> GadgetDraft:
    total = total_magnitude(draft)
    if total == 0:
        return copy.deepcopy(draft)
    cap = TIER_BUDGET[tier] * OVER_BUDGET_FACTOR
    if total > cap:
        return _scale(draft, cap / total)
    if total < DUD_FLOOR:
        return _scale(draft, DUD_FLOOR / total)
    return copy.deepcopy(draft)


def fill_budget(draft: GadgetDraft, tier: Tier) -> GadgetDraft:
    """Scale a draft so its total magnitude lands exactly on the tier budget,
    preserving the composition's proportions. The LLM path calls this on
    parsed drafts (models free-hand magnitudes); the deterministic composer
    already fills the budget by construction. Zero-total drafts (pure
    duration-carried control) pass through — there are no proportions to
    scale. Never called from `apply` — solo stays pathetic.
    """
    total = total_magnitude(draft)
    if total == 0:
        return copy.deepcopy(draft)
    return _scale(draft, TIER_BUDGET[tier] / total)


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
