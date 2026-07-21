import json
import threading
import urllib.request

import pytest

from resolver import fallback, serve
from resolver.bake.schema import contract_fingerprint
from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS


def test_catalog_payload_lists_items_tiers_and_delivery_forms():
    payload = serve.catalog_payload()
    names = {item["name"] for item in payload["items"]}
    assert {"baseball bat", "m16 rifle", "industrial fan", "jerrycan of gasoline"} <= names
    by_name = {item["name"]: item for item in payload["items"]}
    assert by_name["baseball bat"]["delivery"] == "SWING"  # delivery-capable -> its form
    assert by_name["jerrycan of gasoline"]["delivery"] is None         # payload-only
    assert by_name["baseball bat"]["associations"]         # describe() carried through
    assert "LEGENDARY" in payload["tiers"] and "DUD" in payload["tiers"]


def test_build_from_request_assembles_slots():
    build = serve.build_from_request(
        {"delivery": "baseball bat", "modifier": "car battery", "damage": None, "utility": None}
    )
    assert build.delivery_item.name == "baseball bat"
    assert build.modifier_item.name == "car battery"
    assert build.damage_item is None and build.utility_item is None


def test_build_from_request_accepts_substance_chassis():
    build = serve.build_from_request({"delivery": "jerrycan of gasoline"})
    assert build.delivery_item.name == "jerrycan of gasoline"


def test_build_from_request_rejects_ammo_in_delivery_slot():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": ".22 rounds"})


def test_build_from_request_requires_a_delivery_item():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": None, "damage": "5.56 rounds"})


def test_build_from_request_rejects_unknown_item():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": "baseball bat", "damage": "moon rock"})


def test_gadget_to_dict_shape():
    build = DEFAULT_BUILDS["broom_bat"]
    resolved = serve._resolve_once(fallback.resolve, build, Tier.RARE)[1]
    d = serve.gadget_to_dict(resolved, source="llm")
    assert d["source"] == "llm"
    assert d["tier"] == "RARE"
    assert d["name"] and "category" in d and "harmless" in d
    assert d["delivery"] == "SWING"
    assert d["stages"] and "kind" in d["stages"][0]["effects"][0]


def test_roll_returns_n_results_tagged_llm_when_resolver_succeeds():
    build = DEFAULT_BUILDS["broom_bat"]
    results = serve.roll(fallback.resolve, build, Tier.EPIC, 3)
    assert len(results) == 3
    assert all(r["source"] == "llm" for r in results)          # primary resolver succeeded
    assert all(r["stages"] for r in results)


def test_roll_tags_fallback_when_the_resolver_refuses():
    def always_refuse(build, tier):
        raise RuntimeError("refused")

    build = DEFAULT_BUILDS["swamp_cooler"]
    results = serve.roll(always_refuse, build, Tier.LEGENDARY, 1)
    assert results[0]["source"] == "fallback"
    assert results[0]["stages"]                                # a valid instance, not a hole


def test_catalog_payload_exposes_chassis_eligibility_and_solo_cards():
    payload = serve.catalog_payload()
    by_name = {item["name"]: item for item in payload["items"]}

    jerrycan = by_name["jerrycan of gasoline"]
    assert jerrycan["chassis"] is True
    assert jerrycan["mechanism"] is False
    assert jerrycan["form"] == "THROWN"
    solo = jerrycan["solo"]
    assert solo["source"] == "solo" and solo["tier"] == "DUD"
    assert [s["trigger"] for s in solo["stages"]] == ["ON_IMPACT", "ON_TRIGGER"]

    ammo = by_name[".22 rounds"]
    assert ammo["chassis"] is False and ammo["mechanism"] is False
    assert ammo["solo"] is None and ammo["form"] is None

    crowbar = by_name["crowbar"]
    assert crowbar["mechanism"] is True and crowbar["form"] == "SWING"
    assert [s["trigger"] for s in crowbar["solo"]["stages"]] == ["ON_HIT"]


def test_catalog_payload_is_json_serializable():
    json.dumps(serve.catalog_payload())


def test_roll_runs_slots_concurrently():
    # a resolver that blocks until all n calls have started can only finish
    # if roll() runs its slots in parallel — sequential execution deadlocks
    # (the barrier would time out and every slot would fall back)
    barrier = threading.Barrier(3, timeout=5)

    def blocking(build, tier):
        barrier.wait()
        return fallback.resolve(build, tier)

    results = serve.roll(blocking, DEFAULT_BUILDS["broom_bat"], Tier.EPIC, 3)
    assert len(results) == 3
    assert all(r["source"] == "llm" for r in results)


def test_roll_tags_only_the_failing_slot_as_fallback():
    lock = threading.Lock()
    calls = []

    def flaky(build, tier):
        with lock:
            calls.append(1)
            fail = len(calls) == 2
        if fail:
            raise RuntimeError("refused")
        return fallback.resolve(build, tier)

    results = serve.roll(flaky, DEFAULT_BUILDS["broom_bat"], Tier.EPIC, 3)
    assert len(results) == 3
    assert sum(1 for r in results if r["source"] == "fallback") == 1
    assert all(r["stages"] for r in results)


def _serve_on_free_port():
    """A real PlayServer on an OS-assigned port, fallback resolver, daemon thread."""
    server = serve.PlayServer(("127.0.0.1", 0), serve.PlayHandler,
                              fallback.resolve, "fallback (free)")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_contract_endpoint_serves_the_enum_fingerprint():
    server, base = _serve_on_free_port()
    try:
        with urllib.request.urlopen(base + "/api/contract") as resp:
            payload = json.loads(resp.read())
        assert payload == {"fingerprint": contract_fingerprint()}
    finally:
        server.shutdown()
        server.server_close()
