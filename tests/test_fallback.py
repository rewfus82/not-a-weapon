from resolver.contract import EffectKind, GadgetDraft, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver import fallback


def test_fallback_returns_a_valid_draft_with_no_api():
    draft = fallback.resolve(DEFAULT_BUILDS["broom+oil"], Tier.COMMON)
    assert isinstance(draft, GadgetDraft)
    assert draft.name
    assert draft.logic
    assert len(draft.stages) == 1
    assert draft.stages[0].trigger is Trigger.ON_HIT
    assert draft.stages[0].effects[0].kind is EffectKind.DAMAGE


def test_fallback_is_deterministic():
    a = fallback.resolve(DEFAULT_BUILDS["aerosol+candles"], Tier.EPIC)
    b = fallback.resolve(DEFAULT_BUILDS["aerosol+candles"], Tier.EPIC)
    assert a.model_dump() == b.model_dump()


def test_fallback_scales_amount_with_tier():
    dud = fallback.resolve(DEFAULT_BUILDS["broom+oil"], Tier.DUD)
    leg = fallback.resolve(DEFAULT_BUILDS["broom+oil"], Tier.LEGENDARY)
    assert leg.stages[0].effects[0].amount > dud.stages[0].effects[0].amount
