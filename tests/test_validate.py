from resolver.contract import (
    Delivery, Effect, EffectKind, GadgetDraft, Role, Stage, Target, Tier, Trigger,
)
from resolver.items import BaseUse, Build, CATALOG, Item
from resolver.validate import repair
from resolver import clamp


def _draft(*stages: Stage) -> GadgetDraft:
    return GadgetDraft(name="t", description="", logic="", stages=list(stages))


def _fx(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=5.0):
    return Effect(kind=kind, target=target, amount=amount)


_SELF_KIT = Build(delivery_item=CATALOG["first-aid kit"])  # SELF chassis, not protective
_BAT = Build(delivery_item=CATALOG["baseball bat"])        # non-SELF chassis

# the reactive rule is exercised with a fabricated worn-vest fixture so these
# tests stay independent of catalog contents (since the 2026-07-19 editorial
# pass, the firefighter turnout coat carries SELF + protective in the catalog)
_VEST = Item("test vest", roles=frozenset({Role.MECHANISM}), verb="wear",
             tags=frozenset({"protective"}), delivery=Delivery.SELF,
             base_use=BaseUse(Delivery.SELF, EffectKind.SHIELD))
_VEST_KIT = Build(delivery_item=_VEST)


def test_non_self_chassis_passes_through_untouched():
    # lifedrain on a bat: DAMAGE@STRUCK + HEAL@SELF on one ON_HIT stage is intended
    d = _draft(Stage(trigger=Trigger.ON_HIT, effects=[
        _fx(), _fx(kind=EffectKind.HEAL, target=Target.SELF)]))
    out = repair(d, _BAT)
    assert out.model_dump() == d.model_dump()


def test_self_kit_retriggers_on_impact_to_on_use():
    d = _draft(Stage(trigger=Trigger.ON_IMPACT, effects=[_fx()]))
    assert repair(d, _SELF_KIT).stages[0].trigger is Trigger.ON_USE


def test_self_kit_retriggers_on_trigger_to_on_use():
    d = _draft(Stage(trigger=Trigger.ON_TRIGGER, effects=[_fx()]))
    assert repair(d, _SELF_KIT).stages[0].trigger is Trigger.ON_USE


def test_self_kit_retriggers_on_block_to_on_use():
    d = _draft(Stage(trigger=Trigger.ON_BLOCK, effects=[_fx()]))
    assert repair(d, _SELF_KIT).stages[0].trigger is Trigger.ON_USE


def test_self_kit_on_hit_without_protective_chassis_becomes_on_use_targeting_self():
    d = _draft(Stage(trigger=Trigger.ON_HIT, effects=[_fx()]))
    out = repair(d, _SELF_KIT)
    assert out.stages[0].trigger is Trigger.ON_USE
    assert out.stages[0].effects[0].target is Target.SELF


def test_protective_self_kit_keeps_reactive_on_hit_and_mixed_targets():
    # retaliation: when you get hit, shield yourself AND bite back at the striker
    d = _draft(Stage(trigger=Trigger.ON_HIT, effects=[
        _fx(kind=EffectKind.SHIELD, target=Target.SELF),
        _fx(kind=EffectKind.DAMAGE, target=Target.STRUCK)]))
    out = repair(d, _VEST_KIT)
    assert out.stages[0].trigger is Trigger.ON_HIT
    assert [e.target for e in out.stages[0].effects] == [Target.SELF, Target.STRUCK]


def test_self_kit_on_use_effects_are_retargeted_to_self():
    d = _draft(Stage(trigger=Trigger.ON_USE, effects=[_fx(target=Target.STRUCK)]))
    assert repair(d, _SELF_KIT).stages[0].effects[0].target is Target.SELF


def test_self_kit_on_expire_effects_are_retargeted_to_self():
    d = _draft(Stage(trigger=Trigger.ON_EXPIRE, effects=[_fx(target=Target.STRUCK)]))
    assert repair(d, _SELF_KIT).stages[0].effects[0].target is Target.SELF


def test_self_kit_on_kill_keeps_trigger_but_retargets_to_self():
    # the reward reading: the target is dead, the payoff lands on you
    d = _draft(Stage(trigger=Trigger.ON_KILL, effects=[
        _fx(kind=EffectKind.SPEED, target=Target.STRUCK)]))
    out = repair(d, _SELF_KIT)
    assert out.stages[0].trigger is Trigger.ON_KILL
    assert out.stages[0].effects[0].target is Target.SELF


def test_clamp_apply_runs_repair_before_derivation():
    d = _draft(Stage(trigger=Trigger.ON_TRIGGER, effects=[_fx(amount=4.0)]))
    resolved = clamp.apply(d, _SELF_KIT, Tier.DUD)
    assert resolved.draft.stages[0].trigger is Trigger.ON_USE
