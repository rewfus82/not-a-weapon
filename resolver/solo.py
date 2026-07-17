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
    default_target,
)
from resolver.fallback import substance_stages
from resolver.items import Build, Item

BASE_USE_TIER: Tier = Tier.DUD
_SOLO_AMOUNT: float = 2.0  # code-owned; a bare item is pathetic, below even a DUD craft

_TRIGGER_BY_DELIVERY: dict[Delivery, Trigger] = {
    Delivery.PLACED: Trigger.ON_TRIGGER,
    Delivery.SELF: Trigger.ON_USE,
    Delivery.DASH: Trigger.ON_USE,
}


def solo_draft(item: Item) -> GadgetDraft:
    bu = item.base_use
    if bu is None:
        raise ValueError(f"{item.name!r} has no base use")
    effect = Effect(kind=bu.effect, target=default_target(bu.effect), amount=_SOLO_AMOUNT, note="base use")
    # thrown mechanisms (Item.delivery set) keep ON_HIT; a delivery-less thrown
    # substance bursts where it lands, same shape as the crafted chassis path.
    # `bu.armed or` keeps the patch shape even for a hypothetical non-THROWN armed item.
    if bu.armed or (item.delivery is None and bu.delivery is Delivery.THROWN):
        stages = substance_stages([effect], bu.armed)
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
