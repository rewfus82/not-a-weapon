"""The junk catalog as ASSOCIATION CLOUDS with reveal tiers.

An item is not a tag list — it is a small cloud of the things a player *thinks*
when they see it, each tagged with the insight TIER at which it becomes legible.
Asleep (tier 0) a mop is "just a filthy mop, junk"; as you wake up, "soaks up
liquid" and "stringy strands that tangle" surface — and THAT is what makes
combos start seeming obvious. The resolver is only ever shown the associations
visible at the player's current insight, so results can never cite a trait the
player can't yet see.

`fit` is the old tag system, repurposed: not a gate on which slot an item may go
in, but a soft 0..1 signal of how NATURALLY it plays that role. Off-nature
placements are always allowed; they just resolve weaker/jokier (see lucidity).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

SLOTS: tuple[str, ...] = ("delivery", "damage", "utility", "modifier")


@dataclass(frozen=True)
class Assoc:
    """One thing a player associates with an item, gated by insight tier."""

    text: str
    tier: int  # 0 = visible even asleep; higher = needs more insight


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    associations: tuple[Assoc, ...]
    fit: Mapping[str, float]  # slot -> 0..1 natural fit
    color: str = "#b0b0b0"

    def visible(self, insight: int) -> tuple[Assoc, ...]:
        """Associations legible at this insight level (tier <= insight)."""
        return tuple(a for a in self.associations if a.tier <= insight)

    def visible_text(self, insight: int) -> list[str]:
        return [a.text for a in self.visible(insight)]

    def hidden_count(self, insight: int) -> int:
        """How many associations are still redacted (drives the '▓▓▓' teaser)."""
        return sum(1 for a in self.associations if a.tier > insight)

    def fit_for(self, slot: str) -> float:
        return float(self.fit.get(slot, 0.0))


# (id, name, [(text, tier), ...], {slot: fit}, color)
_RAW: list[tuple] = [
    ("bear_trap", "Bear Trap",
     [("rusty steel jaws", 0), ("snaps shut on whatever steps in", 0),
      ("you hide it on the ground", 1), ("holds the catch in place", 2)],
     {"delivery": 0.9, "utility": 0.5, "damage": 0.4, "modifier": 0.1}, "#8f9196"),

    ("beehive", "Beehive",
     [("a papery lump, buzzing", 0), ("full of furious bees", 1),
      ("do not disturb — they swarm", 2), ("the swarm chases warm bodies", 3)],
     {"damage": 0.7, "utility": 0.6, "delivery": 0.3, "modifier": 0.2}, "#cca659"),

    ("fireworks", "Fireworks",
     [("a bundle of festive tubes", 0), ("bang and a bright flash", 1),
      ("startles everything nearby", 2), ("launches on a gout of sparks", 2)],
     {"utility": 0.8, "delivery": 0.5, "damage": 0.4, "modifier": 0.3}, "#e64d66"),

    ("dry_ice", "Dry Ice",
     [("a smoking block, painfully cold", 0), ("freezes what it touches", 1),
      ("hisses out a creeping fog", 2), ("frostbite in a brick", 3)],
     {"modifier": 0.8, "utility": 0.4, "damage": 0.2}, "#a6d8f2"),

    ("mop", "Mop",
     [("a filthy mop, junk", 0), ("soaks up liquid", 1),
      ("stringy strands that tangle", 2), ("a long handle you can swing", 2)],
     {"delivery": 0.6, "utility": 0.4, "modifier": 0.3, "damage": 0.2}, "#c0a06a"),

    ("gasoline", "Jerry Can of Gas",
     [("a sloshing red can, reeking", 0), ("one spark and it goes up", 1),
      ("soaks into anything porous", 2), ("fuel — it makes fire spread", 2)],
     {"modifier": 0.7, "damage": 0.5, "utility": 0.3, "delivery": 0.1}, "#ccb333"),

    ("salami", "Salami",
     [("a greasy cured sausage", 0), ("dense and floppy, like a club", 1),
      ("a hollow-ish tube of meat", 2), ("smells irresistible to the hungry", 3)],
     {"delivery": 0.4, "modifier": 0.3, "utility": 0.3, "damage": 0.2}, "#a44a3f"),

    ("dish_soap", "Dish Soap",
     [("a bottle of slippery suds", 0), ("makes everything slick", 1),
      ("stings and blinds the eyes", 2), ("degreases — nothing keeps its footing", 2)],
     {"utility": 0.6, "modifier": 0.5, "delivery": 0.2, "damage": 0.1}, "#4fb0e6"),

    ("handgun", "Handgun",
     [("a compact pistol", 0), ("fires a lethal round", 0),
      ("loud bark and muzzle flash", 1), ("kicks back hard", 2)],
     {"damage": 0.9, "delivery": 0.8, "utility": 0.3, "modifier": 0.2}, "#6a6a70"),

    ("pencil", "Pencil",
     [("a chewed no. 2 pencil", 0), ("sharp point — it can stab", 1),
      ("graphite conducts a little", 2), ("snaps into splinters", 2)],
     {"modifier": 0.5, "damage": 0.3, "delivery": 0.3, "utility": 0.2}, "#e0c341"),

    ("m16", "M16 Rifle",
     [("a real military rifle", 0), ("spits bullets fast", 0),
      ("magazine-fed, full-auto", 1)],
     {"damage": 0.9, "delivery": 0.9, "utility": 0.2, "modifier": 0.1}, "#73737f"),

    ("grenade", "Frag Grenade",
     [("a heavy iron egg", 0), ("pull the pin and throw", 0),
      ("bursts into shrapnel", 1), ("you lob it and run", 1)],
     {"damage": 0.7, "delivery": 0.6, "modifier": 0.4, "utility": 0.3}, "#66724d"),

    ("chainsaw", "Chainsaw",
     [("a roaring toothed blade", 0), ("cuts through anything", 0),
      ("you have to get close", 1), ("horror-movie loud", 2)],
     {"damage": 0.9, "delivery": 0.7, "modifier": 0.3, "utility": 0.2}, "#e6662f"),

    ("magnet", "Horseshoe Magnet",
     [("a red horseshoe magnet", 0), ("pulls metal toward it", 1),
      ("an invisible tugging field", 2), ("makes things seek each other", 3)],
     {"modifier": 0.8, "utility": 0.6, "delivery": 0.3, "damage": 0.1}, "#d94040"),

    ("co2_canister", "CO2 Canister",
     [("a small pressurized cylinder", 0), ("a propellant — it blasts things out", 1),
      ("vents freezing cold", 2), ("raw pressure looking for a nozzle", 2)],
     {"modifier": 0.8, "delivery": 0.5, "utility": 0.3, "damage": 0.2}, "#bfc7cc"),

    ("leaf_blower", "Leaf Blower",
     [("a loud yard tool", 0), ("blasts a cone of air", 1),
      ("shoves everything away", 2), ("a gale from a nozzle", 2)],
     {"delivery": 0.9, "utility": 0.5, "modifier": 0.3, "damage": 0.2}, "#4da64d"),

    ("potato", "Potato",
     [("a lumpy spud", 0), ("dense and starchy", 1),
      ("jam it on a barrel — a movie silencer", 2), ("the classic spud-gun ammo", 2)],
     {"modifier": 0.6, "damage": 0.3, "delivery": 0.3, "utility": 0.3}, "#bf9966"),

    ("spaghetti", "Plate of Spaghetti",
     [("a cold plate of noodles", 0), ("long sticky strands", 1),
      ("tangles everything up", 2), ("a gooey, gluey mess", 2)],
     {"utility": 0.6, "modifier": 0.5, "damage": 0.3, "delivery": 0.3}, "#e6cc4d"),

    ("feathers", "Handful of Feathers",
     [("a puff of loose feathers", 0), ("light — they float and drift", 1),
      ("tickle, harmless", 1), ("drag on the air, slowing", 2)],
     {"utility": 0.4, "modifier": 0.4, "delivery": 0.2, "damage": 0.1}, "#f2f2f2"),

    ("boombox", "Boombox",
     [("a battered stereo", 0), ("blares loud music", 1),
      ("everything turns to look", 2), ("draws a crowd to it", 2)],
     {"utility": 0.8, "delivery": 0.6, "modifier": 0.2, "damage": 0.1}, "#d94d8c"),
]


def build_catalog() -> dict[str, Item]:
    catalog: dict[str, Item] = {}
    for iid, name, assocs, fit, color in _RAW:
        item = Item(
            id=iid,
            name=name,
            associations=tuple(Assoc(t, tier) for t, tier in assocs),
            fit=dict(fit),
            color=color,
        )
        catalog[iid] = item
    return catalog


CATALOG: dict[str, Item] = build_catalog()
