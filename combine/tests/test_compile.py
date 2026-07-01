"""Lowering to the engine dict: only contract-legal primitives come out."""

from __future__ import annotations

import json

from combine.compile import _DELIVERY_ENUM, _EFFECT_CONST, to_engine
from combine.grammar import Build
from combine.items import CATALOG
from combine.lucidity import Awakening
from combine.resolver import deterministic_resolve
from combine.schema import EffectKind

# the engine const strings gadget.gd actually defines
_ENGINE_EFFECT_CONSTS = {
    "damage", "slow", "snare", "knockback", "explode", "burn", "pierce",
    "spawn", "collect", "freeze", "chain", "heal", "shield", "speed_buff",
}
_ENGINE_DELIVERIES = {
    "PROJECTILE", "MELEE", "LOBBED", "AURA", "PLACED", "CONE", "BEAM",
    "RETURN", "SELF", "TURRET", "DECOY",
}


def _b(**slots) -> Build:
    return Build(**{k: CATALOG[v] for k, v in slots.items()})


def test_effect_const_map_covers_every_effect_kind():
    for kind in EffectKind:
        assert kind in _EFFECT_CONST
        assert _EFFECT_CONST[kind] in _ENGINE_EFFECT_CONSTS


def test_speed_is_renamed_to_engine_const():
    assert _EFFECT_CONST[EffectKind.SPEED] == "speed_buff"


def test_lowering_emits_only_contract_legal_tokens():
    g = deterministic_resolve(
        _b(delivery="bear_trap", damage="beehive", utility="fireworks", modifier="dry_ice"),
        Awakening(1.0),
    )
    dto = to_engine(g)
    assert dto["delivery"] in _ENGINE_DELIVERIES
    for e in dto["effects"]:
        assert e["kind"] in _ENGINE_EFFECT_CONSTS


def test_lowering_is_json_serializable():
    g = deterministic_resolve(_b(delivery="handgun", damage="handgun", modifier="magnet"), Awakening(1.0))
    dto = to_engine(g)
    # must survive an HTTPRequest / file round-trip to Godot unchanged
    assert json.loads(json.dumps(dto)) == dto
    assert dto["homing"] is True


def test_every_delivery_enum_maps():
    from combine.schema import Delivery
    for d in Delivery:
        assert d in _DELIVERY_ENUM
        assert _DELIVERY_ENUM[d] in _ENGINE_DELIVERIES
