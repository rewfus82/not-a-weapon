"""Invented junk catalog with tiered association clouds, build assembly, and
the delivery-lock map. The association clouds are half the system: the model
can only be as clever as the associations fed to it.
"""
from __future__ import annotations

from dataclasses import dataclass

from resolver.contract import Delivery, MELEE_DELIVERIES


@dataclass(frozen=True)
class Item:
    name: str
    # ordered obvious -> non-obvious -> chainable-consequence
    associations: list[str]


_ITEMS: list[Item] = [
    Item("push broom", [
        "a long, swingable handle with reach",
        "stiff bristles that soak up and hold liquid",
        "sweeps wide across the floor in one motion",
        "drag the bristles fast enough and whatever they hold gets flung in an arc",
    ]),
    Item("mop", [
        "long reach on a pole",
        "loose strands that tangle and snag",
        "the strands drink and hold liquid",
        "a soaked mop-head flung fast sheds its load in a spray",
    ]),
    Item("spilled fry oil", [
        "greasy and slippery underfoot",
        "flammable once it is hot enough",
        "clings to and coats whatever it touches",
        "a slick left on the ground drops anyone who crosses it",
    ]),
    Item("birthday candles", [
        "many tiny open flames",
        "drip hot wax as they burn",
        "the trick kind relight themselves after being blown out",
        "packed together they are a fistful of little ignition sources",
    ]),
    Item("aerosol can", [
        "sprays a fine pressurized mist",
        "the propellant is flammable",
        "the can bursts if it gets too hot",
        "a mist plus a spark becomes a gout of flame",
    ]),
    Item("car battery", [
        "dead-weight heavy",
        "holds a charge that arcs across a gap",
        "leaks corrosive acid",
        "a hard enough knock cracks the case and spills the acid",
    ]),
    Item("rubber duck", [
        "buoyant and harmless-looking",
        "squeaks loudly when squeezed",
        "an obvious decoy nobody takes seriously",
        "its squeak draws attention to wherever you leave it",
    ]),
    Item("box fan", [
        "pushes a steady wall of air",
        "spinning blades behind a thin grille",
        "shoves light objects across the floor",
        "aimed down a hall it can carry mist, dust, or heat with the airflow",
    ]),
]

CATALOG: dict[str, Item] = {item.name: item for item in _ITEMS}

# Only delivery-capable items appear here; the delivery item fixes the form.
DELIVERY_LOCK: dict[str, Delivery] = {
    "push broom": Delivery.SWING,
    "mop": Delivery.SWING,
    "aerosol can": Delivery.SPRAY,
    "box fan": Delivery.PLACED,
    "car battery": Delivery.THROWN,
}

COLOR_BY_ITEM: dict[str, str] = {
    "push broom": "amber",
    "mop": "grey",
    "aerosol can": "hiss-white",
    "box fan": "dust-grey",
    "car battery": "acid-green",
}


@dataclass
class Build:
    delivery_item: Item
    damage_item: Item | None = None
    utility_item: Item | None = None
    modifier_item: Item | None = None

    @property
    def delivery(self) -> Delivery:
        try:
            return DELIVERY_LOCK[self.delivery_item.name]
        except KeyError as exc:
            raise ValueError(
                f"{self.delivery_item.name!r} cannot be a delivery chassis"
            ) from exc

    @property
    def color(self) -> str:
        return COLOR_BY_ITEM.get(self.delivery_item.name, "grey")

    def slots(self) -> list[tuple[str, Item | None]]:
        return [
            ("delivery", self.delivery_item),
            ("damage", self.damage_item),
            ("utility", self.utility_item),
            ("modifier", self.modifier_item),
        ]


DEFAULT_BUILDS: dict[str, Build] = {
    # melee: the prompt's hero example (cross-check against the doc samples)
    "broom+oil": Build(
        delivery_item=CATALOG["push broom"],
        utility_item=CATALOG["spilled fry oil"],
    ),
    # ranged/spray: flammable interaction
    "aerosol+candles": Build(
        delivery_item=CATALOG["aerosol can"],
        damage_item=CATALOG["birthday candles"],
    ),
    # not-a-weapon: forces the CONTROL/UTILITY/harmless path
    "fan+duck": Build(
        delivery_item=CATALOG["box fan"],
        utility_item=CATALOG["rubber duck"],
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
