import pytest

from resolver.clamp import TIER_BUDGET, OVER_BUDGET_FACTOR
from resolver.contract import Category, Delivery, EffectKind, Flag, Target, Tier, Trigger
from resolver.items import CATALOG, Build
from resolver import fallback, solo


def test_taser_solo_zap_is_a_thrust_stagger():
    r = solo.resolve_solo(CATALOG["taser"])
    assert r.delivery is Delivery.THRUST
    kinds = {e.kind for s in r.draft.stages for e in s.effects}
    assert kinds == {EffectKind.STAGGER}
    assert r.tier is Tier.DUD


def test_armed_jerrycan_is_a_two_stage_patch():
    r = solo.resolve_solo(CATALOG["jerrycan of gasoline"])
    assert [s.trigger for s in r.draft.stages] == [Trigger.ON_IMPACT, Trigger.ON_TRIGGER]
    assert r.draft.stages[0].effects == []
    assert {e.kind for e in r.draft.stages[1].effects} == {EffectKind.BURN}


def test_placed_solo_triggers_on_step_in():
    r = solo.resolve_solo(CATALOG["bag of marbles"])
    assert r.draft.stages[0].trigger is Trigger.ON_TRIGGER
    assert r.delivery is Delivery.PLACED


def test_self_solo_uses_on_use_and_stays_support():
    r = solo.resolve_solo(CATALOG["first-aid kit"])
    assert r.draft.stages[0].trigger is Trigger.ON_USE
    assert r.harmless is True and r.category is Category.SUPPORT


def test_every_base_use_resolves_at_the_floor():
    # fixed magnitudes at the DUD floor: never zero, never past the DUD cap,
    # always below the cheapest real craft budget (COMMON)
    cap = TIER_BUDGET[Tier.DUD] * OVER_BUDGET_FACTOR
    for item in CATALOG.values():
        if Flag.AMMUNITION in item.flags:
            continue
        r = solo.resolve_solo(item)
        total = sum(e.amount for s in r.draft.stages for e in s.effects)
        assert 0 < total <= cap, item.name
        assert total < TIER_BUDGET[Tier.COMMON], item.name


def test_solo_is_deterministic():
    a = solo.resolve_solo(CATALOG["crowbar"])
    b = solo.resolve_solo(CATALOG["crowbar"])
    assert a.draft.model_dump() == b.draft.model_dump()


def test_ammo_has_no_solo_use():
    with pytest.raises(ValueError):
        solo.solo_draft(CATALOG[".22 rounds"])


def test_thrown_container_solo_bursts_on_impact():
    # same shape as the crafted path: the thrown jug bursts where it lands
    r = solo.resolve_solo(CATALOG["jug of motor oil"])
    assert r.draft.stages[0].trigger is Trigger.ON_IMPACT
    assert r.delivery is Delivery.THROWN


def test_solo_self_item_targets_the_user():
    r = solo.resolve_solo(CATALOG["first-aid kit"])
    effects = [e for s in r.draft.stages for e in s.effects]
    assert effects and all(e.target is Target.SELF for e in effects)


def test_solo_weighted_cost_stays_pathetic():
    from resolver import clamp
    r = solo.resolve_solo(CATALOG["crowbar"])
    assert clamp.total_cost(r.draft) == pytest.approx(2.0)  # _SOLO_AMOUNT, never filled


def test_solo_stays_below_even_a_dud_craft():
    # bare pickup never competes with crafting, even at the floor:
    # solo is a pinned 2.0; a DUD craft fills the DUD budget (6.0)
    r = solo.resolve_solo(CATALOG["crowbar"])
    solo_total = sum(e.amount for s in r.draft.stages for e in s.effects)
    craft = fallback.resolve(Build(delivery_item=CATALOG["crowbar"]), Tier.DUD)
    craft_total = sum(e.amount for s in craft.stages for e in s.effects)
    assert solo_total < craft_total
