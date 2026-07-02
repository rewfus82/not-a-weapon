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

    # --- the rest of the in-game junk drawer (parity with scripts/item_db.gd) ---
    ("nerf_gun", "Nerf Blaster",
     [("a kid's toy blaster", 0), ("fires soft foam darts", 0),
      ("harmless bright plastic", 1), ("rapid-fire pew-pew", 2)],
     {"delivery": 0.8, "damage": 0.3, "utility": 0.3, "modifier": 0.2}, "#f28c26"),
    ("anchovies", "Can of Anchovies",
     [("a reeking little tin", 0), ("tiny salty fish in oily brine", 1),
      ("smells revolting", 2), ("bait that draws hungry things", 3)],
     {"utility": 0.5, "modifier": 0.4, "damage": 0.3, "delivery": 0.3}, "#8c6640"),
    ("ketchup", "Ketchup Bottle",
     [("a squeezy red bottle", 0), ("goopy sauce that squirts everywhere", 1),
      ("looks unsettlingly like blood", 2), ("a sticky mess underfoot", 2)],
     {"modifier": 0.5, "utility": 0.5, "delivery": 0.3, "damage": 0.2}, "#cc2626"),
    ("pixie_stix", "Pixie Stix",
     [("a paper straw of colored dust", 0), ("pure sugar", 1),
      ("a hyperactive sugar rush", 2), ("pops in a candy cloud", 2)],
     {"modifier": 0.5, "utility": 0.4, "damage": 0.1}, "#f28ccc"),
    ("boomerang", "Boomerang",
     [("a curved throwing stick", 0), ("you throw it and it comes back", 0),
      ("whirls through the air", 1), ("cuts coming and going", 2)],
     {"delivery": 0.8, "modifier": 0.5, "damage": 0.3}, "#b38c4d"),
    ("fishing_rod", "Fishing Rod",
     [("a long flexible pole", 0), ("casts a line way out", 1),
      ("hooks and reels the catch back", 2), ("drags things toward you", 2)],
     {"delivery": 0.7, "modifier": 0.5, "utility": 0.5}, "#80996f"),
    ("pringles", "Pringles Can",
     [("a cardboard snack tube", 0), ("pops when you crack it open", 1),
      ("a perfect hollow barrel", 2), ("a tube to aim things down", 2)],
     {"modifier": 0.6, "delivery": 0.5, "utility": 0.3}, "#cc3333"),
    ("vacuum", "Shop Vacuum",
     [("a hose and a roaring motor", 0), ("sucks everything in", 1),
      ("loud and hungry", 2), ("hoovers it all up", 2)],
     {"delivery": 0.7, "utility": 0.7, "modifier": 0.3}, "#4d8ccc"),
    ("backpack", "Backpack",
     [("a roomy fabric pack", 0), ("holds more than it should", 1),
      ("straps and pockets", 2), ("a place to stash the haul", 2)],
     {"modifier": 0.6, "utility": 0.5, "delivery": 0.2}, "#59994d"),
    ("wire_hanger", "Wire Hanger",
     [("a bent metal hanger", 0), ("springy and pokey", 1),
      ("unfolds into a frame", 2), ("a makeshift launcher armature", 3)],
     {"delivery": 0.5, "modifier": 0.4, "damage": 0.2}, "#9a9ea6"),
    ("zip_ties", "Zip Ties",
     [("a handful of plastic straps", 0), ("cinch tight and don't let go", 1),
      ("bind anything together", 2), ("a one-way ratchet", 2)],
     {"modifier": 0.6, "utility": 0.5, "damage": 0.1}, "#333336"),
    ("kitchen_knife", "Kitchen Knife",
     [("a sharp kitchen blade", 0), ("stabs and slices", 0), ("keen steel edge", 1)],
     {"damage": 0.8, "delivery": 0.6, "modifier": 0.3}, "#b3b8c7"),
    ("frying_pan", "Frying Pan",
     [("a heavy flat pan", 0), ("a satisfying BONK", 1), ("blunt and metal", 1)],
     {"delivery": 0.7, "damage": 0.6, "modifier": 0.3}, "#404047"),
    ("rolling_pin", "Rolling Pin",
     [("a wooden rolling pin", 0), ("a solid two-handed whack", 1), ("a blunt bludgeon", 2)],
     {"delivery": 0.7, "damage": 0.5, "modifier": 0.2}, "#c79e6b"),
    ("cheese_grater", "Cheese Grater",
     [("a box of little blades", 0), ("shreds whatever you drag across it", 1),
      ("rows of grabby holes", 2)],
     {"damage": 0.7, "delivery": 0.5, "modifier": 0.4}, "#b3b3bd"),
    ("meat_cleaver", "Meat Cleaver",
     [("a heavy square blade", 0), ("chops clean through", 0), ("a butcher's tool", 1)],
     {"damage": 0.8, "delivery": 0.6}, "#b8b8c7"),
    ("hot_sauce", "Hot Sauce",
     [("a little bottle of fire", 0), ("blistering spicy", 1), ("burns on contact", 2)],
     {"modifier": 0.6, "damage": 0.4, "utility": 0.3}, "#cc1a0d"),
    ("oven_cleaner", "Oven Cleaner",
     [("an aerosol can of chemicals", 0), ("caustic spray that eats grime", 1),
      ("a burning chemical mist", 2)],
     {"delivery": 0.6, "damage": 0.5, "modifier": 0.5}, "#e6f266"),
    ("nail_gun", "Nail Gun",
     [("a pneumatic nailer", 0), ("fires nails fast and deep", 0), ("a magazine of steel spikes", 1)],
     {"damage": 0.9, "delivery": 0.9, "modifier": 0.1}, "#80735c"),
    ("power_drill", "Power Drill",
     [("a whirring power drill", 0), ("bores through anything", 1), ("a spinning bit", 2)],
     {"damage": 0.7, "delivery": 0.6, "modifier": 0.4}, "#d98c1a"),
    ("propane_tank", "Propane Tank",
     [("a heavy steel cylinder", 0), ("pressurized fuel", 1),
      ("goes up in a fireball", 1), ("a BBQ bomb", 2)],
     {"damage": 0.7, "delivery": 0.6, "modifier": 0.5}, "#d9802f"),
    ("car_battery", "Car Battery",
     [("a heavy lead box", 0), ("twelve volts of jolt", 1),
      ("acid sloshing inside", 2), ("jump-starts a dead engine", 2)],
     {"modifier": 0.7, "damage": 0.5, "delivery": 0.3}, "#33333f"),
    ("crowbar", "Crowbar",
     [("a heavy iron bar", 0), ("pry, smash, swing", 1), ("brutal and blunt", 1)],
     {"delivery": 0.7, "damage": 0.7, "modifier": 0.2}, "#8c2626"),
    ("screwdriver", "Screwdriver",
     [("a pointed steel driver", 0), ("jabs and punctures", 1), ("a stabby handle", 2)],
     {"damage": 0.6, "delivery": 0.5, "modifier": 0.3}, "#cc3333"),
    ("weed_whacker", "Weed Whacker",
     [("a spinning cord trimmer", 0), ("shreds anything in reach", 1), ("a whirling blur", 2)],
     {"damage": 0.8, "delivery": 0.7, "modifier": 0.3}, "#4db340"),
    ("slingshot", "Slingshot",
     [("a forked stick with a band", 0), ("snaps small things downrange", 1), ("springy and quick", 2)],
     {"delivery": 0.8, "damage": 0.3, "modifier": 0.3}, "#99734d"),
    ("water_gun", "Water Gun",
     [("a bright plastic squirter", 0), ("shoots a stream of water", 1), ("harmless and drippy", 2)],
     {"delivery": 0.7, "utility": 0.4, "damage": 0.1}, "#3399e6"),
    ("super_ball", "Super Ball",
     [("a dense rubber ball", 0), ("bounces off everything wildly", 1), ("ricochets around a room", 2)],
     {"modifier": 0.5, "delivery": 0.5, "damage": 0.3}, "#e64d99"),
    ("marbles", "Bag of Marbles",
     [("a sack of glass spheres", 0), ("scatter across the floor", 1), ("you slip and wipe out on them", 2)],
     {"utility": 0.6, "modifier": 0.5, "delivery": 0.4, "damage": 0.3}, "#6699cc"),
    ("yo_yo", "Yo-Yo",
     [("a spinning yo-yo", 0), ("flies out and snaps back", 1), ("whirls on its string", 2)],
     {"delivery": 0.7, "modifier": 0.4, "damage": 0.3}, "#d93340"),
    ("battery_acid", "Battery Acid",
     [("a jar of corrosive fluid", 0), ("eats through metal", 1), ("hisses and smokes", 2)],
     {"damage": 0.6, "modifier": 0.6, "delivery": 0.3}, "#b3e633"),
    ("bug_spray", "Bug Spray",
     [("an aerosol can of poison", 0), ("a toxic mist", 1),
      ("flammable propellant", 2), ("a makeshift flame jet", 3)],
     {"delivery": 0.6, "damage": 0.4, "modifier": 0.5}, "#4db34d"),
    ("glow_sticks", "Glow Sticks",
     [("snap-and-glow light sticks", 0), ("an eerie chemical glow", 1), ("draws the eye in the dark", 2)],
     {"utility": 0.5, "modifier": 0.3, "damage": 0.1}, "#66f280"),
    ("helium_tank", "Helium Tank",
     [("a tank of pressurized gas", 0), ("lighter than air", 1), ("a propellant that lifts and blasts", 2)],
     {"modifier": 0.7, "delivery": 0.4, "utility": 0.3}, "#d9d9e6"),
    ("glue", "Bottle of Glue",
     [("a bottle of white glue", 0), ("sticks fast to everything", 1), ("gums up whatever it touches", 2)],
     {"modifier": 0.6, "utility": 0.6, "damage": 0.1}, "#e6e6cc"),
    ("duct_tape", "Duct Tape",
     [("a roll of silver tape", 0), ("fixes and binds anything", 1),
      ("the universal solution", 2), ("holds contraptions together", 2)],
     {"modifier": 0.7, "utility": 0.5, "damage": 0.1}, "#999a9c"),
    ("brick", "Brick",
     [("a solid clay brick", 0), ("heavy and blunt", 1), ("a satisfying thunk", 2)],
     {"damage": 0.6, "delivery": 0.5, "modifier": 0.3}, "#994d40"),
    ("mousetrap", "Mousetrap",
     [("a little spring-loaded trap", 0), ("snaps shut on contact", 1), ("set it and wait", 2)],
     {"delivery": 0.7, "utility": 0.4, "damage": 0.3}, "#b39980"),
    ("fire_extinguisher", "Fire Extinguisher",
     [("a red pressurized cylinder", 0), ("blasts a freezing white cloud", 1), ("a shoving jet of cold", 2)],
     {"delivery": 0.8, "utility": 0.5, "modifier": 0.5}, "#cc3333"),
    ("spray_paint", "Spray Paint",
     [("a rattling aerosol can", 0), ("hisses a colored mist", 1),
      ("flammable propellant", 2), ("a paint-flame jet", 3)],
     {"delivery": 0.6, "modifier": 0.5, "damage": 0.3}, "#3349d9"),
    ("laser_pointer", "Laser Pointer",
     [("a little laser pen", 0), ("a thin bright dot", 1), ("a line that marks a target", 2)],
     {"delivery": 0.7, "modifier": 0.5, "damage": 0.2}, "#e63333"),
    ("taser", "Taser",
     [("a crackling stun gun", 0), ("a high-voltage jolt", 1),
      ("locks muscles stiff", 2), ("arcs between two probes", 2)],
     {"delivery": 0.6, "damage": 0.5, "modifier": 0.5}, "#f2e64d"),
    ("ice_pack", "Ice Pack",
     [("a squishy cold gel pack", 0), ("numbing freezing cold", 1), ("frostbite on contact", 2)],
     {"modifier": 0.7, "damage": 0.3, "utility": 0.4}, "#a6d9f2"),
    ("jumper_cables", "Jumper Cables",
     [("a pair of clamp cables", 0), ("carry raw electricity", 1),
      ("arc and spark", 2), ("chain a jolt between things", 2)],
     {"modifier": 0.7, "damage": 0.5, "delivery": 0.4}, "#d93333"),
    ("bandages", "Bandages",
     [("a roll of gauze", 0), ("patch up wounds", 1), ("stop the bleeding", 2)],
     {"utility": 0.6, "modifier": 0.5, "delivery": 0.5}, "#f2f2ed"),
    ("caffeine_pills", "Caffeine Pills",
     [("a bottle of pep pills", 0), ("a jittery energy jolt", 1), ("makes you fast and reckless", 2)],
     {"modifier": 0.6, "utility": 0.5, "delivery": 0.4}, "#d98c4d"),
    ("trash_can_lid", "Trash Can Lid",
     [("a dented metal lid", 0), ("a makeshift shield", 1), ("blocks and bashes", 2)],
     {"delivery": 0.5, "modifier": 0.5, "utility": 0.5}, "#73737f"),
    ("tripod", "Camera Tripod",
     [("a folding three-legged stand", 0), ("plants firmly on the ground", 1), ("a mount for something bigger", 2)],
     {"delivery": 0.8, "modifier": 0.5}, "#4d4d54"),
    ("raw_meat", "Slab of Raw Meat",
     [("a dripping slab of meat", 0), ("every predator wants it", 1),
      ("irresistible bait", 2), ("dangle it and they come", 2)],
     {"delivery": 0.7, "utility": 0.6, "damage": 0.1}, "#cc4d4d"),
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
