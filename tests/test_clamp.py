from resolver.contract import (
    Category, Delivery, Effect, EffectKind, GadgetDraft, Stage, Tier,
)
from resolver.items import Build, CATALOG
from resolver import clamp


def _draft(*effects: Effect) -> GadgetDraft:
    return GadgetDraft(
        name="t", description="", logic="",
        stages=[Stage(trigger=Trigger_ON_HIT(), effects=list(effects))],
    )


def Trigger_ON_HIT():
    from resolver.contract import Trigger
    return Trigger.ON_HIT


def test_total_magnitude_sums_amounts():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=10), Effect(kind=EffectKind.BURN, amount=5))
    assert clamp.total_magnitude(d) == 15


def test_over_budget_is_scaled_down_to_the_cap():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=1000))
    out = clamp.clamp_magnitudes(d, Tier.LEGENDARY)
    cap = clamp.TIER_BUDGET[Tier.LEGENDARY] * clamp.OVER_BUDGET_FACTOR
    assert clamp.total_magnitude(out) <= cap + 1e-6
    assert clamp.total_magnitude(out) == cap  # scaled exactly to the ceiling


def test_dud_over_budget_scales_down_hard():
    d = _draft(Effect(kind=EffectKind.KNOCKBACK, amount=120))
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    cap = clamp.TIER_BUDGET[Tier.DUD] * clamp.OVER_BUDGET_FACTOR
    assert clamp.total_magnitude(out) == cap


def test_tiny_nonzero_draft_is_raised_to_the_floor():
    d = _draft(Effect(kind=EffectKind.STAGGER, amount=0.2))
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    assert clamp.total_magnitude(out) == clamp.DUD_FLOOR


def test_empty_draft_is_left_alone():
    d = GadgetDraft(name="t", description="", logic="", stages=[])
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    assert clamp.total_magnitude(out) == 0


def test_harmless_true_when_only_control_and_lure():
    d = _draft(Effect(kind=EffectKind.SNARE, amount=1), Effect(kind=EffectKind.LURE, amount=1))
    assert clamp.derive_harmless(d) is True


def test_harmless_false_when_any_damage_family():
    d = _draft(Effect(kind=EffectKind.BURN, amount=1))
    assert clamp.derive_harmless(d) is False


def test_category_weapon_for_lethal():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=5))
    assert clamp.derive_category(d) is Category.WEAPON


def test_category_control_for_control_only():
    d = _draft(Effect(kind=EffectKind.SNARE, amount=1))
    assert clamp.derive_category(d) is Category.CONTROL


def test_category_support_for_self_only():
    d = _draft(Effect(kind=EffectKind.HEAL, amount=1))
    assert clamp.derive_category(d) is Category.SUPPORT


def test_category_utility_for_lure_only():
    d = _draft(Effect(kind=EffectKind.LURE, amount=1))
    assert clamp.derive_category(d) is Category.UTILITY


def test_category_dud_for_empty():
    d = GadgetDraft(name="t", description="", logic="", stages=[])
    assert clamp.derive_category(d) is Category.DUD


def test_apply_assembles_code_owned_fields_from_build():
    build = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
    d = _draft(Effect(kind=EffectKind.BURN, amount=14), Effect(kind=EffectKind.KNOCKBACK, amount=120))
    rg = clamp.apply(d, build, Tier.LEGENDARY)
    assert rg.delivery is Delivery.SWING
    assert rg.color == "grey"
    assert rg.tier is Tier.LEGENDARY
    assert rg.category is Category.WEAPON
    assert rg.harmless is False
    assert set(rg.params) == {"reach", "arc", "commit", "sweep_targets"}
