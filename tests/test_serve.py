import pytest

from resolver import fallback, serve
from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS


def test_catalog_payload_lists_items_tiers_and_delivery_forms():
    payload = serve.catalog_payload()
    names = {item["name"] for item in payload["items"]}
    assert {"push broom", "box fan", "rubber duck", "birthday candles"} <= names
    by_name = {item["name"]: item for item in payload["items"]}
    assert by_name["box fan"]["delivery"] == "PLACED"      # delivery-capable -> its form
    assert by_name["rubber duck"]["delivery"] is None      # payload-only
    assert by_name["push broom"]["associations"]           # associations carried through
    assert "LEGENDARY" in payload["tiers"] and "DUD" in payload["tiers"]


def test_build_from_request_assembles_slots():
    build = serve.build_from_request(
        {"delivery": "push broom", "utility": "spilled fry oil", "damage": None, "modifier": None}
    )
    assert build.delivery_item.name == "push broom"
    assert build.utility_item.name == "spilled fry oil"
    assert build.damage_item is None and build.modifier_item is None


def test_build_from_request_rejects_non_delivery_item_in_delivery_slot():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": "rubber duck"})


def test_build_from_request_requires_a_delivery_item():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": None, "damage": "birthday candles"})


def test_build_from_request_rejects_unknown_item():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": "push broom", "damage": "moon rock"})


def test_gadget_to_dict_shape():
    build = DEFAULT_BUILDS["broom+oil"]
    resolved = serve._resolve_once(fallback.resolve, build, Tier.RARE)[1]
    d = serve.gadget_to_dict(resolved, source="llm")
    assert d["source"] == "llm"
    assert d["tier"] == "RARE"
    assert d["name"] and "category" in d and "harmless" in d
    assert d["delivery"] == "SWING"
    assert d["stages"] and "kind" in d["stages"][0]["effects"][0]


def test_roll_returns_n_results_tagged_llm_when_resolver_succeeds():
    build = DEFAULT_BUILDS["broom+oil"]
    results = serve.roll(fallback.resolve, build, Tier.EPIC, 3)
    assert len(results) == 3
    assert all(r["source"] == "llm" for r in results)          # primary resolver succeeded
    assert all(r["stages"] for r in results)


def test_roll_tags_fallback_when_the_resolver_refuses():
    def always_refuse(build, tier):
        raise RuntimeError("refused")

    build = DEFAULT_BUILDS["fan+duck"]
    results = serve.roll(always_refuse, build, Tier.LEGENDARY, 1)
    assert results[0]["source"] == "fallback"
    assert results[0]["stages"]                                # a valid instance, not a hole
