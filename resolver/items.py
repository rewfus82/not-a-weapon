"""The junk catalog, behaviour-first. Every item carries a functional verb; the
absurdity lives in *combining* verbs, not in the items being jokes. Each item
declares the layer(s) it can feed (roles), affinity tags (interaction-bearing;
see resolver.interactions.TAXONOMY), and — for mechanisms — the base delivery
FORM it locks. Guns + real ammo share a `caliber` so a matching pair reads as
coherent. See docs/superpowers/specs/2026-07-12-item-catalog-and-behavior-taxonomy-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from resolver.contract import Delivery, Role, Flag, MELEE_DELIVERIES


@dataclass(frozen=True)
class Item:
    name: str
    # ordered obvious -> non-obvious -> chainable (optional; LLM-path flavor)
    associations: tuple[str, ...] = ()
    roles: frozenset[Role] = frozenset()
    verb: str = ""
    tags: frozenset[str] = frozenset()
    delivery: Delivery | None = None
    caliber: str | None = None
    flags: frozenset[Flag] = frozenset()

    def describe(self) -> str:
        if self.associations:
            return ", ".join(self.associations)
        parts = [self.verb] if self.verb else []
        parts.extend(sorted(self.tags))
        return ", ".join(p for p in parts if p)


M, MOD, SUB = Role.MECHANISM, Role.MODIFIER, Role.SUBSTANCE
WIELD, FIRE, AMMO, LOAD, BASE = (
    Flag.WIELDABLE, Flag.FIREARM, Flag.AMMUNITION, Flag.LOADABLE, Flag.BASE_WEAPON,
)
_GUN = frozenset({WIELD, FIRE, BASE})
_MELEE = frozenset({WIELD})


_ITEMS: list[Item] = [
    # ---- Layer 1 · Mechanism · Ballistic (fast, flat) ----
    Item("m16 rifle", roles=frozenset({M}), verb="fire-auto",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber="5.56", flags=_GUN),
    Item(".22 pistol", roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber=".22", flags=_GUN),
    Item("9mm pistol", roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber="9mm", flags=_GUN),
    Item("revolver", roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber=".357", flags=_GUN),
    Item(".30-06 hunting rifle", roles=frozenset({M}), verb="fire",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber=".30-06", flags=_GUN),
    Item("nail gun", roles=frozenset({M}), verb="drive-nails",
         tags=frozenset({"sharp"}), delivery=Delivery.PROJECTILE, flags=_MELEE),

    # ---- Layer 1 · Mechanism · Spread (cone of many) ----
    Item("pump shotgun", roles=frozenset({M}), verb="fire-spread",
         tags=frozenset({"scatter"}), delivery=Delivery.SPRAY, caliber="12ga", flags=_GUN),

    # ---- Layer 1 · Mechanism · Stream (continuous cone/jet) ----
    Item("fire extinguisher", roles=frozenset({M}), verb="cone-blast",
         tags=frozenset({"pressurized-gas", "cold"}), delivery=Delivery.SPRAY),
    Item("pressure washer", roles=frozenset({M}), verb="jet",
         tags=frozenset({"liquid"}), delivery=Delivery.BEAM),
    Item("blender", roles=frozenset({M}), verb="blend-&-spit",
         tags=frozenset({"liquid", "scatter", "electrical"}), delivery=Delivery.SPRAY),
    Item("garden hose", roles=frozenset({M}), verb="spray-water",
         tags=frozenset({"liquid"}), delivery=Delivery.SPRAY),

    # ---- Layer 1 · Mechanism · Arc (lobbed, indirect) ----
    Item("potato cannon", roles=frozenset({M}), verb="launch",
         tags=frozenset({"pressurized-gas"}), delivery=Delivery.LOBBED),
    Item("roman candle", roles=frozenset({M, MOD}), verb="lob-sparks",
         tags=frozenset({"flammable", "ignition", "light-source", "loud"}),
         delivery=Delivery.LOBBED),

    # ---- Layer 1 · Mechanism · Thrown (single-arc object) ----
    Item("glass bottle", roles=frozenset({M}), verb="smash",
         tags=frozenset({"brittle", "container"}), delivery=Delivery.THROWN),
    Item("cinder block", roles=frozenset({M}), verb="hurl",
         tags=frozenset({"heavy", "blunt"}), delivery=Delivery.THROWN),

    # ---- Layer 1 · Mechanism · Beam (instant sustained line) ----
    Item("salvaged laser cutter", roles=frozenset({M}), verb="cut",
         tags=frozenset({"light-source"}), delivery=Delivery.BEAM),

    # ---- Layer 1 · Mechanism · Melee (contact) ----
    Item("crowbar", roles=frozenset({M}), verb="pry-&-swing",
         tags=frozenset({"blunt"}), delivery=Delivery.SWING, flags=_MELEE),
    Item("sledgehammer", roles=frozenset({M}), verb="smash",
         tags=frozenset({"blunt", "heavy"}), delivery=Delivery.SLAM, flags=_MELEE),
    Item("fire axe", roles=frozenset({M}), verb="chop",
         tags=frozenset({"sharp"}), delivery=Delivery.SWING, flags=_MELEE),
    Item("machete", roles=frozenset({M}), verb="slash",
         tags=frozenset({"sharp"}), delivery=Delivery.SWING, flags=_MELEE),
    Item("screwdriver", roles=frozenset({M}), verb="stab",
         tags=frozenset({"sharp"}), delivery=Delivery.THRUST, flags=_MELEE),
    Item("baseball bat", roles=frozenset({M}), verb="clobber",
         tags=frozenset({"blunt", "springy"}), delivery=Delivery.SWING, flags=_MELEE),
    Item("power drill", roles=frozenset({M}), verb="bore",
         tags=frozenset({"sharp"}), delivery=Delivery.THRUST, flags=_MELEE),
    Item("angle grinder", roles=frozenset({M}), verb="grind",
         tags=frozenset({"sharp"}), delivery=Delivery.SWING, flags=_MELEE),
    Item("chainsaw", roles=frozenset({M}), verb="saw",
         tags=frozenset({"sharp", "loud"}), delivery=Delivery.SWING, flags=_MELEE),
    Item("weed whacker", roles=frozenset({M}), verb="whip",
         tags=frozenset({"long-reach"}), delivery=Delivery.WHIP, flags=_MELEE),
    Item("riot shield", roles=frozenset({M}), verb="block",
         tags=frozenset({"protective"}), delivery=Delivery.GUARD, flags=_MELEE),

    # ---- Layer 1 · Mechanism · Placed ----
    Item("bear trap", roles=frozenset({M}), verb="snap",
         tags=frozenset({"sharp"}), delivery=Delivery.PLACED),

    # ---- Layer 1 · Mechanism · Self / mobility ----
    Item("leaf blower", roles=frozenset({M}), verb="gust",
         tags=frozenset({"wind"}), delivery=Delivery.DASH),
    Item("adrenaline shot", roles=frozenset({M, SUB}), verb="inject",
         tags=frozenset({"stimulant"}), delivery=Delivery.SELF),
    Item("first-aid kit", roles=frozenset({MOD}), verb="patch",
         tags=frozenset({"restorative"}), delivery=Delivery.SELF),

    # ---- Layer 2 · Modifier / energizer (overlay + effect transform) ----
    Item("propane tank", roles=frozenset({MOD, SUB}), verb="fuel-bomb",
         tags=frozenset({"pressurized-gas", "flammable"})),
    Item("fertilizer", roles=frozenset({MOD, SUB}), verb="detonate",
         tags=frozenset({"powder", "ignition"})),
    Item("car battery", roles=frozenset({MOD, SUB}), verb="electrify",
         tags=frozenset({"electrical", "heavy", "corrosive"})),
    Item("jumper cables", roles=frozenset({MOD}), verb="jolt",
         tags=frozenset({"electrical"})),
    Item("defibrillator", roles=frozenset({MOD, SUB}), verb="shock",
         tags=frozenset({"electrical"})),
    Item("taser", roles=frozenset({MOD, SUB}), verb="stun",
         tags=frozenset({"electrical"}), flags=frozenset({WIELD})),

    # ---- Layer 3 · Substance / payload (needs a delivery to come out) ----
    Item("gasoline", roles=frozenset({SUB}), verb="fuel",
         tags=frozenset({"liquid", "flammable", "ignition"})),
    Item("motor oil", roles=frozenset({SUB}), verb="slick",
         tags=frozenset({"liquid", "flammable", "slippery"})),
    Item("thermite", roles=frozenset({SUB}), verb="burn-through",
         tags=frozenset({"powder", "ignition"})),
    Item("road flare", roles=frozenset({SUB}), verb="ignite",
         tags=frozenset({"ignition", "light-source", "flammable"})),
    Item("hairspray", roles=frozenset({SUB}), verb="spritz",
         tags=frozenset({"flammable", "pressurized-gas"})),
    Item("pool chlorine", roles=frozenset({SUB}), verb="corrode",
         tags=frozenset({"corrosive", "powder"})),
    Item("ammonia cleaner", roles=frozenset({SUB}), verb="fume",
         tags=frozenset({"corrosive", "liquid"})),
    Item("bleach", roles=frozenset({SUB}), verb="bleach",
         tags=frozenset({"corrosive", "liquid"})),
    Item("liquid nitrogen", roles=frozenset({SUB}), verb="freeze",
         tags=frozenset({"cold", "liquid"})),
    Item("dry ice", roles=frozenset({SUB}), verb="chill",
         tags=frozenset({"cold"})),
    Item("wet cement", roles=frozenset({SUB}), verb="set",
         tags=frozenset({"sticky", "liquid"})),
    Item("expanding foam", roles=frozenset({SUB}), verb="foam",
         tags=frozenset({"sticky"})),
    Item("overripe produce", roles=frozenset({SUB}), verb="gum-up",
         tags=frozenset({"slippery", "sticky"})),

    # ---- Feeders · Ammo — real (AMMUNITION · caliber-matched) ----
    Item(".22 rounds", roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber=".22", flags=frozenset({AMMO})),
    Item("9mm rounds", roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber="9mm", flags=frozenset({AMMO})),
    Item(".357 rounds", roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber=".357", flags=frozenset({AMMO})),
    Item("5.56 rounds", roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber="5.56", flags=frozenset({AMMO})),
    Item("12-gauge shells", roles=frozenset({SUB}), verb="shell",
         tags=frozenset({"scatter"}), caliber="12ga", flags=frozenset({AMMO})),
    Item(".30-06 rounds", roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber=".30-06", flags=frozenset({AMMO})),

    # ---- Feeders · Ammo — improvised (LOADABLE, small + numerous) ----
    Item("box of nails", roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "sharp"}), flags=frozenset({LOAD})),
    Item("ball bearings", roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "heavy"}), flags=frozenset({LOAD})),
    Item("marbles", roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "slippery"}), flags=frozenset({LOAD})),
    Item("bag of gravel", roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter"}), flags=frozenset({LOAD})),
]

CATALOG: dict[str, Item] = {item.name: item for item in _ITEMS}

# Optional per-item tint for the playground; unknown items default to "grey".
_COLOR_BY_ITEM: dict[str, str] = {}


@dataclass
class Build:
    delivery_item: Item
    damage_item: Item | None = None
    utility_item: Item | None = None
    modifier_item: Item | None = None

    @property
    def delivery(self) -> Delivery:
        d = self.delivery_item.delivery
        if d is None:
            raise ValueError(f"{self.delivery_item.name!r} cannot be a delivery chassis")
        return d

    @property
    def color(self) -> str:
        return _COLOR_BY_ITEM.get(self.delivery_item.name, "grey")

    def slots(self) -> list[tuple[str, Item | None]]:
        return [
            ("delivery", self.delivery_item),
            ("damage", self.damage_item),
            ("utility", self.utility_item),
            ("modifier", self.modifier_item),
        ]


DEFAULT_BUILDS: dict[str, Build] = {
    # grounded, coherent: blunt melee + heavy shock modifier
    "broom_bat": Build(
        delivery_item=CATALOG["baseball bat"],
        modifier_item=CATALOG["car battery"],
    ),
    # coherent firearm: gun + matching-caliber ammo (C should be ~1)
    "gun_ammo": Build(
        delivery_item=CATALOG["m16 rifle"],
        damage_item=CATALOG["5.56 rounds"],
    ),
    # absurd: the Bananarama — stream mechanism + shock modifier + snare goo
    "bananarama": Build(
        delivery_item=CATALOG["blender"],
        modifier_item=CATALOG["car battery"],
        utility_item=CATALOG["overripe produce"],
    ),
}


def params_for(delivery: Delivery) -> dict[str, float]:
    """Per-delivery-family renderer params (v0 stubs; feel-tuned later)."""
    if delivery in MELEE_DELIVERIES:
        return {"reach": 150.0, "arc": 90.0, "commit": 0.4, "sweep_targets": 2.0}
    if delivery is Delivery.GUARD:
        return {"block_arc": 120.0, "parry_window": 0.3}
    if delivery in (Delivery.SELF, Delivery.DASH):
        return {"distance": 300.0, "self_duration": 3.0}
    # ranged / thrown / placed / spray / beam / hitscan / projectile / lobbed
    return {"range": 800.0, "projectile_speed": 1200.0, "spread": 10.0, "homing": 0.0}
