"""Pure, cheap, LLM-free routing signal: how connected a build's items are.
C≈1 = a coherent build (a chain explains all items); C≈0 = disconnected junk.
"""
from __future__ import annotations

from itertools import combinations

from resolver.contract import Flag
from resolver.items import Build, Item
from resolver.interactions import tags_interact


def _firearm_ammo_match(a: Item, b: Item) -> bool:
    gun, ammo = None, None
    for x in (a, b):
        if Flag.FIREARM in x.flags:
            gun = x
        elif Flag.AMMUNITION in x.flags:
            ammo = x
    return gun is not None and ammo is not None and gun.caliber == ammo.caliber


def _pair_interacts(a: Item, b: Item) -> bool:
    return tags_interact(a.tags, b.tags) or _firearm_ammo_match(a, b)


def coherence(build: Build) -> float:
    items = [it for _, it in build.slots() if it is not None]
    if len(items) <= 1:
        return 1.0
    pairs = list(combinations(items, 2))
    edges = sum(1 for a, b in pairs if _pair_interacts(a, b))
    return edges / len(pairs)
