"""The slot grid — the player's DECLARED intent.

Instead of dumping items in a pot and hoping the resolver guesses which is the
chassis, the player places each item in a role:

  delivery : the mechanism / how it's used   (required — something must carry it)
  damage   : the business end                (optional — empty => not a weapon)
  utility  : a non-damage behavior           (optional)
  modifier : a twist on the whole thing      (optional)

The slot an item sits in is an instruction to the resolver, and it OVERRIDES the
item's default reading (a beehive in `damage` is the killing swarm; in `utility`
it's area denial). `fit` grades how natural the placement is, never whether it's
allowed.
"""

from __future__ import annotations

from dataclasses import dataclass

from .items import SLOTS, Item


@dataclass(frozen=True)
class Placement:
    slot: str
    item: Item
    fit: float  # 0..1: how naturally this item plays this slot


@dataclass(frozen=True)
class Build:
    delivery: Item | None = None
    damage: Item | None = None
    utility: Item | None = None
    modifier: Item | None = None

    def slot(self, name: str) -> Item | None:
        if name not in SLOTS:
            raise KeyError(f"unknown slot {name!r}")
        return getattr(self, name)

    def placements(self) -> list[Placement]:
        out: list[Placement] = []
        for name in SLOTS:
            item = getattr(self, name)
            if item is not None:
                out.append(Placement(name, item, item.fit_for(name)))
        return out

    def is_empty(self) -> bool:
        return all(getattr(self, name) is None for name in SLOTS)

    def coherence(self) -> float:
        """Average fit of the filled slots (0..1). High = a 'sensible' build."""
        ps = self.placements()
        if not ps:
            return 0.0
        return sum(p.fit for p in ps) / len(ps)


def validate_build(build: Build) -> list[str]:
    """Return a list of human-readable problems; empty list == buildable.

    All four slots are ALWAYS open. The awakening ramps how much a placement can
    be BENT (mismatch policy), not which roles exist — so the only structural
    requirements are: something on the bench, and a delivery to carry it.
    """
    problems: list[str] = []
    if build.is_empty():
        problems.append("the bench is empty")
        return problems
    if build.delivery is None:
        problems.append("no delivery: something has to carry the build")
    return problems
