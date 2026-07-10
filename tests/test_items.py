import pytest

from resolver.contract import Delivery
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
