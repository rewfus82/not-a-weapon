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
        "a big goofy handle you can swing with real reach",
        "stiff bristles that slurp up and cling onto any liquid",
        "sweeps in one wide dramatic arc across the floor",
        "swing it fast and the bristles fling whatever they soaked up in a spray",
    ]),
    Item("mop", [
        "a floppy pole with silly long reach",
        "loose stringy strands that tangle and snag onto things",
        "those strands gulp up liquid and hold a big sloppy load",
        "whip it around and the soaked strands sling their load everywhere",
    ]),
    Item("spilled fry oil", [
        "a greasy puddle that sends cartoon feet flying out from under",
        "gets hot and bursts into big whooshy cartoon flames",
        "gloops onto and coats anything it splats against",
        "leaves a banana-peel slick that drops whoever skates across it",
    ]),
    Item("birthday candles", [
        "a fistful of tiny wobbling party flames",
        "dribble goofy hot wax blobs as they burn",
        "the trick kind pop back alight the instant you puff them out",
        "bunched together they're a silly little bouquet of flames",
    ]),
    Item("aerosol can", [
        "hisses out a big dramatic cloud on cue",
        "that cloud loves to catch into a cartoon whoosh of flame",
        "shake it up and it gets over-excited, ready to pop like a gag prop",
        "point it at anything and it makes a whole scene",
    ]),
    Item("car battery", [
        "a heavy clunky brick you can hurl",
        "crackles with cartoon zap-electricity across a gap",
        "sloshing with green fizzy goo inside",
        "give it a good whack and the case cracks, glugging goo everywhere",
    ]),
    Item("rubber duck", [
        "bobbing, wide-eyed, and utterly harmless-looking",
        "lets out a loud indignant SQUEAK when squeezed",
        "the world's most obvious decoy, taken seriously by no one",
        "its squeak yanks every eye toward wherever you plop it",
    ]),
    Item("box fan", [
        "blasts out a steady whooshing wall of wind",
        "whirring cartoon blades buzzing behind a flimsy grille",
        "strong enough to shove light junk skittering across the floor",
        "aim it down a hall and its wind ferries along whatever's floating — mist, dust, sparks",
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
