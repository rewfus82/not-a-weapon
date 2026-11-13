import json
import threading
import urllib.error
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


def test_build_from_items_maps_positionally():
    build = serve.build_from_items(["bucket of wet cement", "jerrycan of gasoline"])
    assert build.delivery_item.name == "bucket of wet cement"
    assert build.damage_item.name == "jerrycan of gasoline"
    assert build.utility_item is None and build.modifier_item is None


def test_build_from_items_rejects_bad_requests():
    with pytest.raises(ValueError):
        serve.build_from_items([])
    with pytest.raises(ValueError):
        serve.build_from_items(["a", "b", "c", "d", "e"])
    with pytest.raises(ValueError):
        serve.build_from_items(["definitely not junk"])


def test_craft_resolves_once_and_reports_an_honest_source():
    payload = {"items": ["cooler of raw steaks"], "tier_target": "COMMON"}
    gadget = serve.craft(fallback.resolve, payload)
    # a keyless server's resolver_fn IS the fallback: never claim a live source
    assert gadget["source"] == "fallback"
    assert gadget["tier"] == "COMMON"
    # the wire contract the C++ mirror parses — pin the exact key sets
    assert set(gadget) == {"source", "name", "description", "logic", "tier",
                           "category", "harmless", "delivery", "color", "stages"}
    for stage in gadget["stages"]:
        assert set(stage) == {"trigger", "note", "effects"}
        for effect in stage["effects"]:
            assert set(effect) == {"kind", "target", "amount", "duration",
                                   "radius", "count", "note"}
    # Task 1's fix, observed on the wire: a PLACED chassis fires ON_TRIGGER
    assert gadget["delivery"] == "PLACED"
    assert [s["trigger"] for s in gadget["stages"]] == ["ON_TRIGGER"]


def test_craft_accepts_and_ignores_a_seed():
    payload = {"items": ["bucket of wet cement"], "tier_target": "COMMON", "seed": 7}
    assert serve.craft(fallback.resolve, payload)["source"] == "fallback"


def test_craft_endpoint_end_to_end_fallback():
    server, base = _serve_on_free_port()
    try:
        body = json.dumps({"items": ["bucket of wet cement", "jerrycan of gasoline"],
                           "tier_target": "RARE"}).encode("utf-8")
        req = urllib.request.Request(base + "/craft", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            gadget = json.loads(resp.read())
        assert gadget["source"] == "fallback"
        assert gadget["tier"] == "RARE"
        assert gadget["stages"] and all(s["effects"] for s in gadget["stages"])
    finally:
        server.shutdown()
        server.server_close()


def test_craft_endpoint_rejects_unknown_items_with_400():
    server, base = _serve_on_free_port()
    try:
        body = json.dumps({"items": ["not junk"], "tier_target": "COMMON"}).encode("utf-8")
        req = urllib.request.Request(base + "/craft", data=body,
                                     headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req)
        assert excinfo.value.code == 400
        assert "error" in json.loads(excinfo.value.read())
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------- local Forge resolver (optional extra)


class _LabelledResolver:
    """Stands in for forge.resolver.ForgeResolver: a resolver_fn that names its own source."""
    source = "forge"
    label = "FORGE (local model, epoch test)"

    def __init__(self, *args, **kwargs):
        self.calls = 0

    def __call__(self, build, tier):
        self.calls += 1
        return fallback.resolve(build, tier)


def test_craft_and_roll_report_the_resolvers_own_source():
    resolver = _LabelledResolver()
    gadget = serve.craft(resolver, {"items": ["baseball bat", "car battery"], "tier_target": "RARE"})
    assert gadget["source"] == "forge"
    results = serve.roll(resolver, DEFAULT_BUILDS["broom_bat"], Tier.EPIC, 2)
    assert [r["source"] for r in results] == ["forge", "forge"]


def test_a_failing_labelled_resolver_still_degrades_to_fallback():
    class Broken(_LabelledResolver):
        def __call__(self, build, tier):
            raise RuntimeError("model missing")

    gadget = serve.craft(Broken(), {"items": ["baseball bat"], "tier_target": "COMMON"})
    assert gadget["source"] == "fallback"


def test_make_resolver_forge_needs_no_key_and_loads_lazily(monkeypatch):
    import sys
    import types
    fake = types.ModuleType("forge.resolver")
    fake.ForgeResolver = _LabelledResolver
    monkeypatch.setitem(sys.modules, "forge.resolver", fake)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resolver_fn, label = serve._make_resolver(False, "unused", 3, None, forge="models/forge")
    assert isinstance(resolver_fn, _LabelledResolver)
    assert label.startswith("FORGE")


def test_play_server_does_not_reverse_resolve_its_host(monkeypatch):
    # http.server's default server_bind calls socket.getfqdn, which can stall ~30 s on macOS
    import socket

    def boom(*args):
        raise AssertionError("getfqdn called")

    monkeypatch.setattr(socket, "getfqdn", boom)
    server = serve.PlayServer(("127.0.0.1", 0), serve.PlayHandler, fallback.resolve, "fallback (free)")
    server.server_close()


def test_playground_page_knows_forge_mode_and_badge():
    assert "/^FORGE/" in serve.PAGE
    assert "g.source === 'forge'" in serve.PAGE
