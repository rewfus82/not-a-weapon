from resolver.contract import EffectKind, GadgetDraft, Tier, Trigger
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
