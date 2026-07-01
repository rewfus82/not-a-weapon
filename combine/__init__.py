"""Engine-agnostic combine brain for 'This Is Not A Weapon'.

The whole point of this package: keep the *thinking* (what junk becomes) in a
portable, fully-tested layer, and leave the *rendering* (pixels) to whatever
engine consumes its output. Godot is one consumer today; it won't be the last.
"""

from __future__ import annotations

from .grammar import Build, Placement, validate_build
from .items import CATALOG, SLOTS, Assoc, Item, build_catalog
from .lucidity import Awakening, Era, MismatchPolicy
from .schema import Category, Delivery, Effect, EffectKind, Gadget, Stage, Trigger

__all__ = [
    "Assoc",
    "Awakening",
    "Build",
    "CATALOG",
    "Category",
    "Delivery",
    "Effect",
    "EffectKind",
    "Era",
    "Gadget",
    "Item",
    "MismatchPolicy",
    "Placement",
    "SLOTS",
    "Stage",
    "Trigger",
    "build_catalog",
    "validate_build",
]
