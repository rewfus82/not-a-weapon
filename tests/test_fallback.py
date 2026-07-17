import pytest

from resolver.clamp import TIER_BUDGET, apply as clamp_apply

from resolver.contract import EffectKind, GadgetDraft, Target, Tier, Trigger
from resolver.items import DEFAULT_BUILDS, Build, CATALOG
from resolver import fallback

def _kinds(draft):
    return {e.kind for s in draft.stages for e in s.effects}

def test_composer_returns_valid_draft_with_no_api():
    draft = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.COMMON)
    assert isinstance(draft, GadgetDraft)
    assert draft.name and draft.logic and draft.stages

def test_swamp_cooler_yields_its_tag_derived_effects():
    # corrosive+liquid -> BURN, electrical+liquid -> CHAIN; RARE takes the full chain
    draft = fallback.resolve(DEFAULT_BUILDS["swamp_cooler"], Tier.RARE)
    assert draft.stages[0].trigger is Trigger.ON_HIT
    assert EffectKind.BURN in _kinds(draft)
    assert EffectKind.CHAIN in _kinds(draft)

def test_no_duplicate_effect_kinds_within_a_stage():
    # car battery's electrical overlay (CHAIN) must not duplicate the
    # electrical+liquid base CHAIN already in the chain
    draft = fallback.resolve(DEFAULT_BUILDS["swamp_cooler"], Tier.RARE)
    for stage in draft.stages:
        kinds = [e.kind for e in stage.effects]
        assert len(kinds) == len(set(kinds))

def test_higher_tier_unlocks_more_effects():
    dud = fallback.resolve(DEFAULT_BUILDS["swamp_cooler"], Tier.DUD)
    leg = fallback.resolve(DEFAULT_BUILDS["swamp_cooler"], Tier.LEGENDARY)
    dud_effects = sum(len(s.effects) for s in dud.stages)
    leg_effects = sum(len(s.effects) for s in leg.stages)
    # wiring, not balance: DUD takes exactly one, LEGENDARY takes the full chain
    assert leg_effects > dud_effects

def test_overlay_gated_behind_rare():
    # base = [BURN] (flammable single; pressurized-gas+flammable is no pair rule);
    # overlay = EXPLODE from the propane tank MODIFIER — distinct from base
    build = Build(delivery_item=CATALOG["t-shirt cannon"],
                  modifier_item=CATALOG["propane tank"])
    for tier in (Tier.DUD, Tier.COMMON, Tier.UNCOMMON):
        assert EffectKind.EXPLODE not in _kinds(fallback.resolve(build, tier))
    for tier in (Tier.RARE, Tier.EPIC, Tier.LEGENDARY):
        assert EffectKind.EXPLODE in _kinds(fallback.resolve(build, tier))

def test_composer_is_deterministic():
    a = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.EPIC)
    b = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.EPIC)
    assert a.model_dump() == b.model_dump()

def test_effectless_build_still_deals_a_plain_hit():
    draft = fallback.resolve(Build(delivery_item=CATALOG["m16 rifle"]), Tier.DUD)
    assert EffectKind.DAMAGE in _kinds(draft)

def test_substance_chassis_composes_a_thrown_burst():
    draft = fallback.resolve(Build(delivery_item=CATALOG["bucket of wet cement"]), Tier.COMMON)
    assert draft.stages[0].trigger is Trigger.ON_IMPACT
    assert EffectKind.SNARE in _kinds(draft)


def test_armed_chassis_composes_the_two_stage_patch():
    draft = fallback.resolve(Build(delivery_item=CATALOG["jerrycan of gasoline"]), Tier.COMMON)
    assert [s.trigger for s in draft.stages] == [Trigger.ON_IMPACT, Trigger.ON_TRIGGER]
    assert draft.stages[0].effects == []


def test_mechanism_chassis_keeps_on_hit():
    draft = fallback.resolve(DEFAULT_BUILDS["broom_bat"], Tier.COMMON)
    assert draft.stages[0].trigger is Trigger.ON_HIT


def test_every_build_fills_the_tier_budget_exactly():
    # §6: same power total within a tier, whatever the item/effect count
    builds = {
        **DEFAULT_BUILDS,
        "lone_gun": Build(delivery_item=CATALOG["9mm pistol"]),
        "lone_jerrycan": Build(delivery_item=CATALOG["jerrycan of gasoline"]),
        "overlay_build": Build(delivery_item=CATALOG["t-shirt cannon"],
                               modifier_item=CATALOG["propane tank"]),
    }
    for key, build in builds.items():
        for tier in Tier:
            draft = fallback.resolve(build, tier)
            total = sum(e.amount for s in draft.stages for e in s.effects)
            assert total == pytest.approx(TIER_BUDGET[tier]), (key, tier.value)


def test_overlay_rides_at_half_a_base_share():
    # cannon+propane at LEGENDARY: base [BURN] w=1, overlay [EXPLODE] w=0.5
    build = Build(delivery_item=CATALOG["t-shirt cannon"],
                  modifier_item=CATALOG["propane tank"])
    draft = fallback.resolve(build, Tier.LEGENDARY)
    amounts = {e.note: e.amount for s in draft.stages for e in s.effects}
    assert amounts["overlay"] == pytest.approx(amounts["base"] / 2)


def test_self_kit_chassis_composes_an_on_use_self_stage():
    draft = fallback.resolve(Build(delivery_item=CATALOG["first-aid kit"]), Tier.COMMON)
    assert [s.trigger for s in draft.stages] == [Trigger.ON_USE]
    assert all(e.target is Target.SELF for s in draft.stages for e in s.effects)


def test_composer_effects_carry_code_authored_targets():
    draft = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.COMMON)
    assert all(e.target is Target.STRUCK for s in draft.stages for e in s.effects)


def test_deterministic_path_never_trips_the_clamp_cap():
    # budget < budget*1.12, so the clamp must pass composed drafts through
    # untouched — the over-budget headroom is booster-only again
    for build in DEFAULT_BUILDS.values():
        for tier in Tier:
            draft = fallback.resolve(build, tier)
            resolved = clamp_apply(draft, build, tier)
            before = sum(e.amount for s in draft.stages for e in s.effects)
            after = sum(e.amount for s in resolved.draft.stages for e in s.effects)
            assert after == pytest.approx(before)
