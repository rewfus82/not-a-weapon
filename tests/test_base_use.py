"""Pins the base-use enumeration (spec: 2026-07-13-junk-base-use-design.md)
and mechanically enforces the governing rule: an item's solo effect must be
derivable from its own tags, be the firearm default, or sit on the CLOSED
judgment-call list below. Adding to that list is a deliberate act.
"""
import pytest

from resolver.contract import Delivery, EffectKind, Flag
from resolver.interactions import effects_for
from resolver.items import CATALOG

D, E = Delivery, EffectKind

# name -> (base delivery, base effect, armed) | None (AMMUNITION only)
EXPECTED: dict[str, tuple[Delivery, EffectKind, bool] | None] = {
    # melee
    "crowbar": (D.SWING, E.DAMAGE, False),
    "sledgehammer": (D.SLAM, E.DAMAGE, False),
    "fire axe": (D.SWING, E.PIERCE, False),
    "machete": (D.SWING, E.PIERCE, False),
    "screwdriver": (D.THRUST, E.PIERCE, False),
    "baseball bat": (D.SWING, E.DAMAGE, False),
    "power drill": (D.THRUST, E.PIERCE, False),
    "angle grinder": (D.SWING, E.PIERCE, False),
    "chainsaw": (D.SWING, E.PIERCE, False),
    "weed whacker": (D.WHIP, E.DAMAGE, False),
    "riot shield": (D.GUARD, E.SHIELD, False),
    "nail gun": (D.PROJECTILE, E.PIERCE, False),
    # guns
    "m16 rifle": (D.HITSCAN, E.DAMAGE, False),
    ".22 pistol": (D.HITSCAN, E.DAMAGE, False),
    "9mm pistol": (D.HITSCAN, E.DAMAGE, False),
    "revolver": (D.HITSCAN, E.DAMAGE, False),
    ".30-06 hunting rifle": (D.HITSCAN, E.DAMAGE, False),
    "pump shotgun": (D.SPRAY, E.DAMAGE, False),
    # real ammo: the named exception — no base use
    ".22 rounds": None,
    "9mm rounds": None,
    ".357 rounds": None,
    "5.56 rounds": None,
    "12-gauge shells": None,
    ".30-06 rounds": None,
    # ranged mechanisms
    "fire extinguisher": (D.SPRAY, E.FREEZE, False),
    "pressure washer": (D.BEAM, E.KNOCKBACK, False),
    "garden hose": (D.SPRAY, E.KNOCKBACK, False),
    "roman candle": (D.LOBBED, E.BURN, False),
    "salvaged laser cutter": (D.BEAM, E.BURN, False),
    "glass bottle": (D.THROWN, E.PIERCE, False),
    "cinder block": (D.THROWN, E.DAMAGE, False),
    "t-shirt cannon": (D.LOBBED, E.STAGGER, False),
    "industrial fan": (D.PLACED, E.KNOCKBACK, False),
    # placed & scatter
    "bear trap": (D.PLACED, E.SNARE, False),
    "airhorn": (D.PLACED, E.LURE, False),
    "box of nails": (D.PLACED, E.PIERCE, False),
    "tin of ball bearings": (D.THROWN, E.DAMAGE, False),
    "bag of marbles": (D.PLACED, E.SLOW, False),
    "bag of gravel": (D.THROWN, E.DAMAGE, False),
    # self-use & electrical
    "leaf blower": (D.DASH, E.KNOCKBACK, False),
    "adrenaline shot": (D.SELF, E.SPEED, False),
    "first-aid kit": (D.SELF, E.HEAL, False),
    "taser": (D.THRUST, E.STAGGER, False),
    "defibrillator": (D.THRUST, E.DAMAGE, False),
    "jumper cables": (D.THRUST, E.SNARE, False),
    "car battery": (D.THROWN, E.DAMAGE, False),
    # containers & substances
    "jerrycan of gasoline": (D.THROWN, E.BURN, True),
    "jar of thermite": (D.THROWN, E.BURN, True),
    "sack of fertilizer": (D.THROWN, E.BURN, True),
    "jug of motor oil": (D.THROWN, E.SLOW, False),
    "jug of bleach": (D.THROWN, E.BURN, False),
    "jug of ammonia cleaner": (D.THROWN, E.BURN, False),
    "tub of pool chlorine": (D.THROWN, E.BURN, False),
    "dewar of liquid nitrogen": (D.THROWN, E.FREEZE, False),
    "bucket of wet cement": (D.THROWN, E.SNARE, False),
    "crate of overripe produce": (D.THROWN, E.SLOW, False),
    "can of expanding foam": (D.SPRAY, E.SNARE, False),
    "can of hairspray": (D.SPRAY, E.SNARE, False),
    "block of dry ice": (D.PLACED, E.FREEZE, False),
    "road flare": (D.THROWN, E.BURN, False),
    "propane tank": (D.THROWN, E.DAMAGE, False),
}

# CLOSED allowlist: items whose solo effect is a documented judgment call,
# not tag-derivable. Each entry names its justification.
JUDGMENT_CALLS: dict[str, EffectKind] = {
    "weed whacker": E.DAMAGE,          # 'long-reach' has no single-tag effect
    "pressure washer": E.KNOCKBACK,    # 'liquid' unmapped; the jet shoves
    "garden hose": E.KNOCKBACK,        # 'liquid' unmapped; weak push + soak
    "salvaged laser cutter": E.BURN,   # 'light-source'->LURE is wrong for a cutter
    "glass bottle": E.PIERCE,          # 'brittle' unmapped; shard burst
    "t-shirt cannon": E.STAGGER,       # empty-launcher near-dud pop
    "bear trap": E.SNARE,              # holding is the point, not the PIERCE bite
    "tin of ball bearings": E.DAMAGE,  # thrown weights, not knockback
    "bag of gravel": E.DAMAGE,         # 'scatter' unmapped; stinging wave
    "taser": E.STAGGER,                # solo locks muscles; CHAIN is craft behavior
    "defibrillator": E.DAMAGE,         # one big timed dump
    "jumper cables": E.SNARE,          # the clamps bite and hold
    "car battery": E.DAMAGE,           # refinement 3: common-knowledge carve-out
    "can of hairspray": E.SNARE,       # sticky mist lives in associations, not tags
    "jar of thermite": E.BURN,         # burns through steel; tag pair says EXPLODE
    "sack of fertilizer": E.BURN,      # fast mean burn; tag pair says EXPLODE
    "propane tank": E.DAMAGE,          # refinement 4: steel doesn't burst when thrown
}


def test_expected_covers_the_catalog_exactly():
    assert set(EXPECTED) == set(CATALOG)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_base_use_matches_the_spec(name):
    item, exp = CATALOG[name], EXPECTED[name]
    if exp is None:
        assert Flag.AMMUNITION in item.flags, f"{name}: only ammo may lack a base use"
        assert item.base_use is None
        return
    bu = item.base_use
    assert bu is not None, f"{name} has no base use"
    assert (bu.delivery, bu.effect, bu.armed) == exp


def test_governing_rule_effect_is_derivable_or_adjudicated():
    for item in CATALOG.values():
        bu = item.base_use
        if bu is None:
            continue
        if item.name in JUDGMENT_CALLS:
            assert bu.effect is JUDGMENT_CALLS[item.name], item.name
        elif Flag.FIREARM in item.flags:
            assert bu.effect is EffectKind.DAMAGE, item.name
        else:
            assert bu.effect in effects_for(item.tags), (
                f"{item.name}: {bu.effect} not derivable from {sorted(item.tags)}"
            )


def test_mechanism_base_delivery_matches_its_craft_form():
    # the crowbar swings both ways: solo form == the FORM it locks in a craft
    for item in CATALOG.values():
        if item.base_use is not None and item.delivery is not None:
            assert item.base_use.delivery is item.delivery, item.name


def test_armed_is_exactly_the_ignition_gated_payloads():
    armed = {it.name for it in CATALOG.values() if it.base_use and it.base_use.armed}
    assert armed == {"jerrycan of gasoline", "jar of thermite", "sack of fertilizer"}
