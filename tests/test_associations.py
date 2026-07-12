"""Mechanical invariants for the association clouds. Prose quality is gated
by user review (spec: 2026-07-12-association-clouds-design.md), not tests.
"""
import re

import pytest

from resolver.contract import Flag
from resolver.items import CATALOG

# Batch tuples are appended per authoring task; Task 4 asserts they
# partition the whole catalog.
BATCH_RANGED: tuple[str, ...] = (
    "m16 rifle", ".22 pistol", "9mm pistol", "revolver",
    ".30-06 hunting rifle", "pump shotgun",
    "nail gun", "fire extinguisher", "pressure washer", "blender",
    "garden hose", "potato cannon", "roman candle", "glass bottle",
    "cinder block", "salvaged laser cutter",
)


BATCH_CONTACT: tuple[str, ...] = (
    "crowbar", "sledgehammer", "fire axe", "machete", "screwdriver",
    "baseball bat", "power drill", "angle grinder", "chainsaw",
    "weed whacker", "riot shield", "bear trap", "leaf blower",
    "adrenaline shot", "first-aid kit",
)


BATCH_MODIFIERS: tuple[str, ...] = (
    "propane tank", "fertilizer", "car battery", "jumper cables",
    "defibrillator", "taser",
)


def _expected_line_range(item) -> tuple[int, int]:
    if Flag.FIREARM in item.flags:
        return (2, 3)
    if Flag.AMMUNITION in item.flags:
        return (1, 2)
    return (3, 5)


def _assert_cloud(name: str) -> None:
    item = CATALOG[name]
    lo, hi = _expected_line_range(item)
    n = len(item.associations)
    assert lo <= n <= hi, f"{name}: {n} lines, expected {lo}-{hi}"
    for line in item.associations:
        stripped = line.replace(item.name, "")
        if item.caliber:
            stripped = stripped.replace(item.caliber, "")
        assert not re.search(r"\d", stripped), f"{name}: digits in {line!r}"


@pytest.mark.parametrize("name", BATCH_RANGED)
def test_ranged_batch_cloud_shape(name):
    _assert_cloud(name)


@pytest.mark.parametrize("name", BATCH_CONTACT)
def test_contact_batch_cloud_shape(name):
    _assert_cloud(name)


@pytest.mark.parametrize("name", BATCH_MODIFIERS)
def test_modifier_batch_cloud_shape(name):
    _assert_cloud(name)
