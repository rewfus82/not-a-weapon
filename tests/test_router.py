from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS
from resolver.router import route, C_HIGH, C_LOW


def test_low_tiers_are_always_deterministic():
    assert route(DEFAULT_BUILDS["swamp_cooler"], Tier.DUD) == "deterministic"
    assert route(DEFAULT_BUILDS["swamp_cooler"], Tier.COMMON) == "deterministic"


def test_coherent_build_stays_deterministic_even_high_tier():
    assert route(DEFAULT_BUILDS["gun_ammo"], Tier.LEGENDARY) == "deterministic"


def test_absurd_high_tier_routes_to_llm():
    assert route(DEFAULT_BUILDS["swamp_cooler"], Tier.LEGENDARY) == "llm"


def test_middle_band_leans_deterministic_until_rare():
    # swamp_cooler sits in the middle coherence band (C ~0.67); the middle band
    # leans deterministic until RARE, unlike the low band which flips at UNCOMMON.
    assert route(DEFAULT_BUILDS["swamp_cooler"], Tier.UNCOMMON) == "deterministic"
    assert route(DEFAULT_BUILDS["swamp_cooler"], Tier.RARE) == "llm"


def test_thresholds_are_the_adjudicated_values():
    # Spec says C_HIGH ~0.66; adjudicated to 0.67 so a 2/3-coherent build lands in the middle band.
    assert (C_HIGH, C_LOW) == (0.67, 0.33)
