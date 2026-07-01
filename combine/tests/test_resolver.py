"""The deterministic resolver: chassis from the delivery slot, payloads as an
ordered stage, and the lucidity eras — including the flagship acceptance case."""

from __future__ import annotations

import pytest

from combine.grammar import Build
from combine.items import CATALOG
from combine.lucidity import Awakening
from combine.resolver import BRINGS, MODIFIERS, SHAPE, deterministic_resolve
from combine.schema import Category, Delivery, EffectKind

LUCID = Awakening(1.0)
ASLEEP = Awakening(0.1)


def _b(**slots) -> Build:
    return Build(**{k: CATALOG[v] for k, v in slots.items()})


# --- table/catalog parity: adding an item can't silently miss mechanics -------

def test_every_catalog_item_has_shape_and_brings():
    for iid in CATALOG:
        assert iid in SHAPE, f"{iid} missing a SHAPE (delivery form)"
        assert iid in BRINGS, f"{iid} missing a BRINGS entry"


def test_modifier_ids_are_real_items():
    for iid in MODIFIERS:
        assert iid in CATALOG


# --- the core promise: the delivery slot decides the chassis ------------------

def test_delivery_slot_sets_the_chassis():
    # this is the whole fix: the bear trap (delivery) makes it a PLACED trap,
    # NOT a lobbed bomb, even though fireworks (explosive-ish) is in the build.
    g = deterministic_resolve(
        _b(delivery="bear_trap", damage="beehive", utility="fireworks", modifier="dry_ice"),
        LUCID,
    )
    assert g.chassis is Delivery.PLACED


def test_flagship_build_reads_as_trap_startle_swarm_freeze():
    g = deterministic_resolve(
        _b(delivery="bear_trap", damage="beehive", utility="fireworks", modifier="dry_ice"),
        LUCID,
    )
    kinds = [e.kind for e in g.all_effects()]
    assert EffectKind.SNARE in kinds       # the trap snaps
    assert EffectKind.KNOCKBACK in kinds   # fireworks startle
    assert EffectKind.SPAWN in kinds       # the bees pour out
    assert EffectKind.FREEZE in kinds      # dry ice: the swarm stings cold
    # ordering: snare (trap) precedes the swarm (payload) precedes the modifier twist
    assert kinds.index(EffectKind.SNARE) < kinds.index(EffectKind.SPAWN)
    assert kinds.index(EffectKind.SPAWN) < kinds.index(EffectKind.FREEZE)
    assert g.category is Category.WEAPON


def test_leaf_blower_is_a_cone_not_a_projectile():
    g = deterministic_resolve(_b(delivery="leaf_blower", damage="handgun"), LUCID)
    assert g.chassis is Delivery.CONE


# --- utility is stripped to non-damage ---------------------------------------

def test_utility_slot_drops_raw_damage():
    # fireworks BRINGS (knockback, burn); in utility, burn (damage-over-time) is
    # dropped and only the startle (knockback) remains.
    g = deterministic_resolve(_b(delivery="handgun", utility="fireworks"), LUCID)
    kinds = {e.kind for e in g.all_effects()}
    assert EffectKind.KNOCKBACK in kinds
    assert EffectKind.BURN not in kinds


# --- empty damage slot => not a weapon (the theme enforces itself) ------------

def test_no_damage_slot_is_not_a_weapon():
    g = deterministic_resolve(_b(delivery="mop", utility="magnet"), LUCID)
    assert g.category is not Category.WEAPON
    assert g.harmless


# --- the modifier twists the whole thing -------------------------------------

def test_magnet_modifier_makes_it_homing():
    g = deterministic_resolve(_b(delivery="handgun", damage="handgun", modifier="magnet"), LUCID)
    assert g.homing


def test_co2_modifier_boosts_projectile_speed():
    base = deterministic_resolve(_b(delivery="handgun", damage="handgun"), LUCID)
    mod = deterministic_resolve(_b(delivery="handgun", damage="handgun", modifier="co2_canister"), LUCID)
    assert mod.projectile_speed > base.projectile_speed


# --- the lucidity ramp: same mismatch, three meanings ------------------------

def _salami_build() -> Build:
    # every item off-nature: salami/delivery, dish_soap/damage, handgun/utility, pencil/modifier
    return _b(delivery="salami", damage="dish_soap", utility="handgun", modifier="pencil")


def test_asleep_normalizes_off_nature_placements_away():
    # dish_soap in damage (fit 0.1) is far below the mismatch threshold, so an
    # ASLEEP simulation quietly discards it — you get a plain salami club.
    g = deterministic_resolve(_salami_build(), ASLEEP)
    # salami (delivery, fit 0.4) survives and sets a melee chassis
    assert g.chassis is Delivery.MELEE
    kinds = {e.kind for e in g.all_effects()}
    # the soap's slip/blind never makes it in while asleep
    assert EffectKind.SLOW not in kinds
    # but the salami's own club nature (it's the chassis) still lands
    assert EffectKind.KNOCKBACK in kinds


def test_lucid_lets_the_absurd_build_go_through():
    g = deterministic_resolve(_salami_build(), Awakening(1.0))
    kinds = {e.kind for e in g.all_effects()}
    # awake, the off-nature placements are honored: soap slips, the gun scatters
    assert EffectKind.SLOW in kinds
    assert EffectKind.KNOCKBACK in kinds


def test_penalize_era_is_weaker_than_reward_era():
    build = _b(delivery="salami", damage="dish_soap")  # dish_soap off-nature in damage
    mid = deterministic_resolve(build, Awakening(0.5))
    hi = deterministic_resolve(build, Awakening(0.9))
    mid_slow = next(e.amount for e in mid.all_effects() if e.kind is EffectKind.SLOW)
    hi_slow = next(e.amount for e in hi.all_effects() if e.kind is EffectKind.SLOW)
    assert mid_slow < hi_slow


# --- mop + gasoline across insight (the reveal-driven 'obvious' case) ---------

def test_mop_gasoline_makes_a_burning_melee_when_awake():
    # mop (delivery -> melee swing) + gasoline (damage -> burn): a flaming mop.
    g = deterministic_resolve(_b(delivery="mop", damage="gasoline"), LUCID)
    assert g.chassis is Delivery.MELEE
    assert EffectKind.BURN in {e.kind for e in g.all_effects()}
