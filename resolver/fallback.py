"""Deterministic fallback resolver: keeps the whole pipeline functional with
no API key. Produces a valid but deliberately boring draft (the obvious
reading, one effect, scaled to the tier). Its signature matches the LLM
resolver's `resolve`, so the harness can swap them freely.
"""
from __future__ import annotations

from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Tier, Trigger
from resolver.items import Build

# A crude per-tier amount so the fallback still shows a dud->god shape.
_TIER_AMOUNT: dict[Tier, float] = {
    Tier.DUD: 2.0,
    Tier.COMMON: 6.0,
    Tier.UNCOMMON: 10.0,
    Tier.RARE: 18.0,
    Tier.EPIC: 30.0,
    Tier.LEGENDARY: 45.0,
}


def resolve(build: Build, tier: Tier) -> GadgetDraft:
    delivery_item = build.delivery_item
    amount = _TIER_AMOUNT[tier]
    return GadgetDraft(
        name=f"Improvised {delivery_item.name.title()}",
        description=f"A {delivery_item.name} swung in anger. It works, barely.",
        logic=(
            f"The obvious reading: {delivery_item.name} — "
            f"{delivery_item.associations[0]}. Nothing clever, just the first thing it is."
        ),
        stages=[
            Stage(
                trigger=Trigger.ON_HIT,
                effects=[Effect(kind=EffectKind.DAMAGE, amount=amount, note="a plain hit")],
                note="the obvious reading",
            )
        ],
    )
