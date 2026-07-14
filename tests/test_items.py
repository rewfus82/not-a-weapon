import pytest

from resolver.contract import Delivery, Role, Flag
from resolver.items import Item, Build, CATALOG, DEFAULT_BUILDS, params_for
from resolver.interactions import TAXONOMY


def test_catalog_is_the_reimagined_slice():
    assert len(CATALOG) >= 50
    for it in CATALOG.values():
        assert it.roles, f"{it.name} has no role"
        assert it.tags <= TAXONOMY, f"{it.name} has off-taxonomy tags: {it.tags - TAXONOMY}"


def test_every_delivery_form_has_a_mechanism_carrier():
    carried = {it.delivery for it in CATALOG.values()
               if Role.MECHANISM in it.roles and it.delivery is not None}
    assert carried == set(Delivery)


def test_every_tag_has_a_carrier():
    carried = set().union(*(it.tags for it in CATALOG.values()))
    assert TAXONOMY <= carried


def test_firearms_have_matching_ammunition():
    gun_cals = {it.caliber for it in CATALOG.values() if Flag.FIREARM in it.flags}
    ammo_cals = {it.caliber for it in CATALOG.values() if Flag.AMMUNITION in it.flags}
    assert gun_cals and gun_cals <= ammo_cals


def test_build_delivery_reads_from_the_item():
    build = DEFAULT_BUILDS["gun_ammo"]
    assert isinstance(build.delivery, Delivery)


def test_build_rejects_non_delivery_chassis():
    payload = next(it for it in CATALOG.values() if it.delivery is None)
    with pytest.raises(ValueError):
        _ = Build(delivery_item=payload).delivery


def test_default_builds_span_grounded_and_absurd():
    assert set(DEFAULT_BUILDS) == {"broom_bat", "gun_ammo", "swamp_cooler"}


def test_build_slots_lists_all_four_in_order():
    build = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
    labels = [label for label, _ in build.slots()]
    assert labels == ["delivery", "damage", "utility", "modifier"]


def test_params_for_melee_and_ranged_families():
    melee = params_for(Delivery.SWING)
    assert set(melee) == {"reach", "arc", "commit", "sweep_targets"}
    ranged = params_for(Delivery.SPRAY)
    assert set(ranged) == {"range", "projectile_speed", "spread", "homing"}


def test_item_defaults_keep_old_construction_working():
    it = Item("scrap", ["it is scrap"])
    assert it.roles == frozenset() and it.verb == "" and it.tags == frozenset()
    assert it.delivery is None and it.caliber is None and it.flags == frozenset()


def test_item_describe_uses_associations_when_present():
    it = Item("mop", ["long reach", "tangling strands"])
    assert it.describe() == "long reach, tangling strands"


def test_item_describe_falls_back_to_verb_and_tags():
    it = Item("blender", roles=frozenset({Role.MECHANISM}), verb="blend-&-spit",
              tags=frozenset({"liquid", "scatter"}), delivery=Delivery.SPRAY)
    d = it.describe()
    assert "blend-&-spit" in d and "liquid" in d and "scatter" in d


def test_baseball_bat_carries_heavy_for_the_broom_bat_edge():
    # 'heavy' deviates from the plan's representative construction on purpose:
    # the spec doesn't enumerate melee tags, and coherence ordering requires
    # bat<->car-battery to interact via the shared 'heavy' tag (see Task 5 review).
    assert {"blunt", "heavy", "springy"} <= CATALOG["baseball bat"].tags
