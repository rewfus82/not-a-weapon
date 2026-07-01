"""The slot grid: placements, fit-based coherence, and lucidity-gated validation."""

from __future__ import annotations

from combine.grammar import Build, validate_build
from combine.items import CATALOG


def _b(**slots) -> Build:
    return Build(**{k: CATALOG[v] for k, v in slots.items()})


def test_empty_build_is_empty():
    assert Build().is_empty()
    assert not _b(delivery="bear_trap").is_empty()


def test_placements_report_slot_and_fit():
    build = _b(delivery="bear_trap", damage="beehive")
    by_slot = {p.slot: p for p in build.placements()}
    assert set(by_slot) == {"delivery", "damage"}
    assert by_slot["delivery"].fit == CATALOG["bear_trap"].fit_for("delivery")


def test_coherence_rewards_natural_placement():
    # bear trap as delivery + beehive as damage = a sensible build
    good = _b(delivery="bear_trap", damage="beehive")
    # salami as delivery + dish soap as damage = nonsense
    silly = _b(delivery="salami", damage="dish_soap")
    assert good.coherence() > silly.coherence()


def test_coherence_empty_is_zero():
    assert Build().coherence() == 0.0


def test_validate_flags_missing_delivery():
    build = _b(damage="beehive")  # no delivery
    problems = validate_build(build)
    assert any("delivery" in p for p in problems)


def test_all_slots_are_always_open():
    # a full four-slot build validates with no gating — slots are never locked
    build = _b(delivery="bear_trap", damage="beehive",
               utility="fireworks", modifier="dry_ice")
    assert validate_build(build) == []


def test_flagship_build_is_coherent():
    build = _b(delivery="bear_trap", damage="beehive",
               utility="fireworks", modifier="dry_ice")
    # every item is in a slot it naturally fits reasonably well
    assert build.coherence() > 0.5
