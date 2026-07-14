"""Base-use resolution: the solo action an item performs with no craft.

Magnitudes are code-owned and fixed at the floor: every solo use is a
DUD-strength single behavior, strictly below any crafted tier's budget
(the zero-risk act of picking something up never competes with crafting).
Armed payloads (inert until ignited) resolve as a two-stage patch using
existing triggers — no new vocabulary.
"""
from __future__ import annotations

from resolver.clamp import apply as clamp_apply
from resolver.contract import (
    Delivery, Effect, GadgetDraft, ResolvedGadget, Stage, Tier, Trigger,
)
from resolver.fallback import _TIER_SEED
from resolver.items import Build, Item

BASE_USE_TIER: Tier = Tier.DUD
_SOLO_SEED: float = _TIER_SEED[BASE_USE_TIER]

_TRIGGER_BY_DELIVERY: dict[Delivery, Trigger] = {
    Delivery.PLACED: Trigger.ON_TRIGGER,
    Delivery.SELF: Trigger.ON_USE,
    Delivery.DASH: Trigger.ON_USE,
}


def solo_draft(item: Item) -> GadgetDraft:
    bu = item.base_use
    if bu is None:
        raise ValueError(f"{item.name!r} has no base use")
    effect = Effect(kind=bu.effect, amount=_SOLO_SEED, note="base use")
    if bu.armed:
        stages = [
            Stage(trigger=Trigger.ON_IMPACT, effects=[], note="burst"),
            Stage(trigger=Trigger.ON_TRIGGER, effects=[effect], note="armed patch"),
        ]
    else:
        trigger = _TRIGGER_BY_DELIVERY.get(bu.delivery, Trigger.ON_HIT)
        stages = [Stage(trigger=trigger, effects=[effect], note="base use")]
    return GadgetDraft(
        name=item.name.title(),
        description=f"{item.name}, used as found.",
        logic=f"Base use: {bu.delivery.value} -> {bu.effect.value}.",
        stages=stages,
    )


def resolve_solo(item: Item) -> ResolvedGadget:
    return clamp_apply(solo_draft(item), Build(delivery_item=item), BASE_USE_TIER)
