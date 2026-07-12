from resolver.items import Build, CATALOG, DEFAULT_BUILDS
from resolver.coherence import coherence

def test_single_item_is_trivially_coherent():
    assert coherence(Build(delivery_item=CATALOG["baseball bat"])) == 1.0

def test_gun_plus_matching_ammo_is_fully_coherent():
    assert coherence(DEFAULT_BUILDS["gun_ammo"]) == 1.0

def test_absurd_build_is_less_coherent_than_a_grounded_one():
    grounded = coherence(DEFAULT_BUILDS["broom_bat"])
    absurd = coherence(DEFAULT_BUILDS["bananarama"])
    assert 0.0 <= absurd < grounded <= 1.0

def test_gun_plus_wrong_caliber_ammo_does_not_interact():
    build = Build(delivery_item=CATALOG["m16 rifle"], damage_item=CATALOG["box of nails"])
    # nails are LOADABLE (no caliber), so no firearm/ammo edge, and no shared tag
    assert coherence(build) < 1.0
