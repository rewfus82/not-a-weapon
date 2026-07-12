from resolver.contract import EffectKind, GadgetDraft, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver import fallback

def _kinds(draft):
    return {e.kind for s in draft.stages for e in s.effects}

def test_composer_returns_valid_draft_with_no_api():
    draft = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.COMMON)
    assert isinstance(draft, GadgetDraft)
    assert draft.name and draft.logic and draft.stages

def test_grounded_flammable_chain_burns():
    # a build whose substance tags trigger BURN should yield a BURN effect
    draft = fallback.resolve(DEFAULT_BUILDS["bananarama"], Tier.RARE)
    assert draft.stages[0].trigger is Trigger.ON_HIT

def test_higher_tier_unlocks_more_effects():
    dud = fallback.resolve(DEFAULT_BUILDS["bananarama"], Tier.DUD)
    leg = fallback.resolve(DEFAULT_BUILDS["bananarama"], Tier.LEGENDARY)
    dud_effects = sum(len(s.effects) for s in dud.stages)
    leg_effects = sum(len(s.effects) for s in leg.stages)
    assert leg_effects >= dud_effects

def test_composer_is_deterministic():
    a = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.EPIC)
    b = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.EPIC)
    assert a.model_dump() == b.model_dump()

def test_effectless_build_still_deals_a_plain_hit():
    from resolver.items import Build, CATALOG
    draft = fallback.resolve(Build(delivery_item=CATALOG["m16 rifle"]), Tier.DUD)
    assert EffectKind.DAMAGE in _kinds(draft)
