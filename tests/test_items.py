import pytest

from resolver.contract import Delivery, Role, Flag
from resolver.items import (
    Item, Build, CATALOG, DELIVERY_LOCK, DEFAULT_BUILDS, params_for,
)


def test_catalog_has_rich_association_clouds():
    assert len(CATALOG) >= 8
    for item in CATALOG.values():
        assert len(item.associations) >= 3  # obvious -> non-obvious -> chainable


def test_build_locks_delivery_from_the_delivery_item():
    build = Build(delivery_item=CATALOG["push broom"], utility_item=CATALOG["spilled fry oil"])
    assert build.delivery is Delivery.SWING


def test_build_color_comes_from_delivery_item():
    build = Build(delivery_item=CATALOG["push broom"])
    assert build.color == "amber"


def test_build_rejects_non_delivery_item_in_delivery_slot():
    with pytest.raises(ValueError):
        _ = Build(delivery_item=CATALOG["rubber duck"]).delivery


def test_build_slots_lists_all_four_in_order():
    build = Build(delivery_item=CATALOG["push broom"], utility_item=CATALOG["spilled fry oil"])
    labels = [label for label, _ in build.slots()]
    assert labels == ["delivery", "damage", "utility", "modifier"]


def test_default_builds_cover_three_delivery_families():
    deliveries = {b.delivery for b in DEFAULT_BUILDS.values()}
    assert deliveries == {Delivery.SWING, Delivery.SPRAY, Delivery.PLACED}


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
