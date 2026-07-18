import pytest

from resolver.contract import (
    Category, Delivery, Effect, EffectKind, GadgetDraft, Stage, Target, Tier,
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


def test_total_cost_sums_weighted_fields():
    d = _draft(
        Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=10),
        Effect(kind=EffectKind.SNARE, target=Target.STRUCK, duration=2.0),
        Effect(kind=EffectKind.PIERCE, target=Target.STRUCK, count=2),
    )
    expected = (10 * clamp.W_AMOUNT[EffectKind.DAMAGE]
                + 2.0 * clamp.W_DURATION + 2 * clamp.W_COUNT)
    assert clamp.total_cost(d) == pytest.approx(expected)


def test_over_budget_is_scaled_down_to_the_cap():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=1000))
    out = clamp.clamp_magnitudes(d, Tier.LEGENDARY)
    cap = clamp.TIER_BUDGET[Tier.LEGENDARY] * clamp.OVER_BUDGET_FACTOR
    assert clamp.total_cost(out) <= cap + 1e-6
    assert clamp.total_cost(out) == cap  # scaled exactly to the ceiling


def test_dud_over_budget_scales_down_hard():
    d = _draft(Effect(kind=EffectKind.KNOCKBACK, target=Target.STRUCK, amount=120))
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    cap = clamp.TIER_BUDGET[Tier.DUD] * clamp.OVER_BUDGET_FACTOR
    assert clamp.total_cost(out) == cap


def test_tiny_nonzero_draft_is_raised_to_the_floor():
    d = _draft(Effect(kind=EffectKind.STAGGER, target=Target.STRUCK, amount=0.2))
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    assert clamp.total_cost(out) == clamp.DUD_FLOOR


def test_empty_draft_is_left_alone():
    d = GadgetDraft(name="t", description="", logic="", stages=[])
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    assert clamp.total_cost(out) == 0


def test_harmless_true_when_only_control_and_lure():
    d = _draft(Effect(kind=EffectKind.SNARE, target=Target.STRUCK, amount=1), Effect(kind=EffectKind.LURE, target=Target.STRUCK, amount=1))
    assert clamp.derive_harmless(d) is True


def test_harmless_false_when_any_damage_family():
    d = _draft(Effect(kind=EffectKind.BURN, target=Target.STRUCK, amount=1))
    assert clamp.derive_harmless(d) is False


def test_category_weapon_for_lethal():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=5))
    assert clamp.derive_category(d) is Category.WEAPON


def test_category_control_for_control_only():
    d = _draft(Effect(kind=EffectKind.SNARE, target=Target.STRUCK, amount=1))
    assert clamp.derive_category(d) is Category.CONTROL


def test_category_support_for_self_only():
    d = _draft(Effect(kind=EffectKind.HEAL, target=Target.SELF, amount=1))
    assert clamp.derive_category(d) is Category.SUPPORT


def test_category_utility_for_lure_only():
    d = _draft(Effect(kind=EffectKind.LURE, target=Target.STRUCK, amount=1))
    assert clamp.derive_category(d) is Category.UTILITY


def test_category_dud_for_empty():
    d = GadgetDraft(name="t", description="", logic="", stages=[])
    assert clamp.derive_category(d) is Category.DUD


def test_apply_assembles_code_owned_fields_from_build():
    build = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
    d = _draft(Effect(kind=EffectKind.BURN, target=Target.STRUCK, amount=14), Effect(kind=EffectKind.KNOCKBACK, target=Target.STRUCK, amount=120))
    rg = clamp.apply(d, build, Tier.LEGENDARY)
    assert rg.delivery is Delivery.SWING
    assert rg.color == "grey"
    assert rg.tier is Tier.LEGENDARY
    assert rg.category is Category.WEAPON
    assert rg.harmless is False
    assert set(rg.params) == {"reach", "arc", "commit", "sweep_targets"}


def test_fill_budget_scales_up_preserving_ratios():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=30), Effect(kind=EffectKind.BURN, target=Target.STRUCK, amount=10))
    out = clamp.fill_budget(d, Tier.LEGENDARY)  # budget 120, ratios 3:1
    amounts = [e.amount for s in out.stages for e in s.effects]
    assert amounts == [pytest.approx(90.0), pytest.approx(30.0)]


def test_fill_budget_scales_down_to_budget_not_cap():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=500))
    out = clamp.fill_budget(d, Tier.LEGENDARY)
    assert clamp.total_cost(out) == pytest.approx(clamp.TIER_BUDGET[Tier.LEGENDARY])


def test_fill_budget_passes_zero_total_through():
    d = _draft(Effect(kind=EffectKind.SNARE, target=Target.STRUCK, amount=0))
    out = clamp.fill_budget(d, Tier.LEGENDARY)
    assert clamp.total_cost(out) == 0


def test_fill_budget_works_at_the_dud_floor():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=1))
    out = clamp.fill_budget(d, Tier.DUD)
    assert clamp.total_cost(out) == pytest.approx(6.0)


# --- derivation matrix on (kind, target) — spec §6, playtest fixtures pinned ---

def test_lethal_at_self_only_is_support_and_harmless():
    # accepted edge: a pure self-cost derives SUPPORT; it can't hurt others
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.SELF, amount=5))
    assert clamp.derive_category(d) is Category.SUPPORT
    assert clamp.derive_harmless(d) is True


def test_control_at_self_only_is_support():
    d = _draft(Effect(kind=EffectKind.SLOW, target=Target.SELF, amount=5))
    assert clamp.derive_category(d) is Category.SUPPORT


def test_adrenaline_crash_kit_is_support_and_harmless():
    # playtest fixture: HEAL+SPEED with a self-inflicted crash, however written
    d = _draft(
        Effect(kind=EffectKind.HEAL, target=Target.SELF, amount=10),
        Effect(kind=EffectKind.SPEED, target=Target.SELF, amount=10),
        Effect(kind=EffectKind.DAMAGE, target=Target.SELF, amount=5),
    )
    assert clamp.derive_category(d) is Category.SUPPORT
    assert clamp.derive_harmless(d) is True


def test_dosing_nail_heal_at_struck_is_support_and_harmless():
    # playtest fixture: the healing gun — heals whatever it shoots
    d = _draft(Effect(kind=EffectKind.HEAL, target=Target.STRUCK, amount=10))
    assert clamp.derive_category(d) is Category.SUPPORT
    assert clamp.derive_harmless(d) is True


def test_lifedrain_is_a_weapon_and_not_harmless():
    # playtest fixture: the self-heal doesn't launder the damage
    d = _draft(
        Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=10),
        Effect(kind=EffectKind.HEAL, target=Target.SELF, amount=10),
    )
    assert clamp.derive_category(d) is Category.WEAPON
    assert clamp.derive_harmless(d) is False


def test_lure_at_self_is_still_utility():
    # LURE is the one kind rule 4 ignores at SELF — bait is utility either way
    d = _draft(Effect(kind=EffectKind.LURE, target=Target.SELF, amount=1))
    assert clamp.derive_category(d) is Category.UTILITY


def test_duration_only_effect_consumes_budget():
    # the free-rider exploit: a 2.5s snare next to a full damage budget must
    # now cost — fill_budget lands the weighted total exactly on the budget
    d = _draft(
        Effect(kind=EffectKind.SNARE, target=Target.STRUCK, duration=2.5),
        Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=50),
    )
    out = clamp.fill_budget(d, Tier.RARE)  # budget 48; cost before = 2.5*2 + 50 = 55
    assert clamp.total_cost(out) == pytest.approx(clamp.TIER_BUDGET[Tier.RARE])
    snare = out.stages[0].effects[0]
    assert snare.duration == pytest.approx(2.5 * 48.0 / 55.0)  # scaled, not free


def test_count_overflow_floor_scales_counts_first():
    # count cost alone (10 * W_COUNT = 30) exceeds the DUD budget (6):
    # counts floor-scale down deterministically; small residue is acceptable
    d = _draft(Effect(kind=EffectKind.PIERCE, target=Target.STRUCK, count=10))
    out = clamp.fill_budget(d, Tier.DUD)
    e = out.stages[0].effects[0]
    assert e.count == 2  # int(10 * 6/30)
    assert clamp.total_cost(out) <= clamp.TIER_BUDGET[Tier.DUD] + 1e-9


def test_fit_cost_lands_on_the_target_and_passes_zero_through():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=10))
    assert clamp.total_cost(clamp.fit_cost(d, 30.0)) == pytest.approx(30.0)
    empty = _draft()
    assert clamp.total_cost(clamp.fit_cost(empty, 30.0)) == 0.0
