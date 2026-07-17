"""Deterministic legality repair: the model proposes, code disposes.

Repairs drafts against the code-owned trigger/target legality table for the
chassis in hand — repairs, never rejects, so the keyless path cannot fail.
Only a SELF chassis (a worn/used kit) constrains composition at v1; on every
other chassis all (kind, target) combinations are intended compositions
(lifedrain, the healing gun, self-costs). Semantics on a self-kit: ON_HIT =
"when you get hit" (needs a chassis that can absorb a hit — the `protective`
tag); ON_KILL = "when you down something while this is active" (the payoff
lands on you). The protective rule ships defined-but-dormant: the only
protective catalog item today (riot shield) locks GUARD.
"""
from __future__ import annotations

import copy

from resolver.contract import Delivery, GadgetDraft, Target, Trigger
from resolver.items import Build

# Nothing is thrown, placed, or blocked-with on a self-kit.
_SELF_ILLEGAL: frozenset[Trigger] = frozenset({
    Trigger.ON_IMPACT, Trigger.ON_TRIGGER, Trigger.ON_BLOCK,
})
# Stages whose effects can only land on the wielder.
_RETARGET_SELF: frozenset[Trigger] = frozenset({
    Trigger.ON_USE, Trigger.ON_EXPIRE, Trigger.ON_KILL,
})


def repair(draft: GadgetDraft, build: Build) -> GadgetDraft:
    if build.delivery is not Delivery.SELF:
        return copy.deepcopy(draft)
    protective = "protective" in build.delivery_item.tags
    out = copy.deepcopy(draft)
    for stage in out.stages:
        if stage.trigger in _SELF_ILLEGAL:
            stage.trigger = Trigger.ON_USE
        elif stage.trigger is Trigger.ON_HIT and not protective:
            stage.trigger = Trigger.ON_USE
        if stage.trigger in _RETARGET_SELF:
            for effect in stage.effects:
                effect.target = Target.SELF
    return out
