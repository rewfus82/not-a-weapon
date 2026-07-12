"""The tag taxonomy + the known-interaction tables. This is half the system:
the composer can only be as clever as these tables, and the coherence scorer
reads the same wiring to decide whether a build's items interact. Numbers live
in the composer/clamp; here we own only *which effect a tag interaction yields*.
v0, code-owned, expected to churn.
"""
from __future__ import annotations

from itertools import combinations

from resolver.contract import EffectKind

TAXONOMY: frozenset[str] = frozenset({
    # physical / impact
    "sharp", "blunt", "heavy", "long-reach", "springy", "brittle",
    # substance / state
    "flammable", "ignition", "corrosive", "cold", "liquid", "slippery",
    "sticky", "pressurized-gas", "powder",
    # energy / field
    "electrical", "wind", "loud", "light-source",
    # structural / dispersal
    "container", "scatter",
    # self / support
    "restorative", "stimulant", "protective",
})

# A lone tag's baseline effect (used when no pair interaction covers it).
SINGLE_TAG_EFFECTS: dict[str, EffectKind] = {
    "sharp": EffectKind.PIERCE,
    "blunt": EffectKind.DAMAGE,
    "heavy": EffectKind.KNOCKBACK,
    "springy": EffectKind.LAUNCH,
    "corrosive": EffectKind.BURN,
    "cold": EffectKind.FREEZE,
    "electrical": EffectKind.CHAIN,
    "sticky": EffectKind.SNARE,
    "slippery": EffectKind.SLOW,
    "flammable": EffectKind.BURN,
    "loud": EffectKind.LURE,
    "light-source": EffectKind.LURE,
    "wind": EffectKind.KNOCKBACK,
    "restorative": EffectKind.HEAL,
    "stimulant": EffectKind.SPEED,
    "protective": EffectKind.SHIELD,
}

# Emergent effect when two tags meet (checked before singles).
PAIR_EFFECTS: dict[frozenset[str], EffectKind] = {
    frozenset({"flammable", "ignition"}): EffectKind.BURN,
    frozenset({"flammable", "electrical"}): EffectKind.BURN,
    frozenset({"pressurized-gas", "ignition"}): EffectKind.EXPLODE,
    frozenset({"powder", "ignition"}): EffectKind.EXPLODE,
    frozenset({"corrosive", "liquid"}): EffectKind.BURN,
    frozenset({"electrical", "liquid"}): EffectKind.CHAIN,
    frozenset({"liquid", "cold"}): EffectKind.FREEZE,
    frozenset({"sticky", "liquid"}): EffectKind.SNARE,
}


def tags_interact(a: frozenset[str], b: frozenset[str]) -> bool:
    if a & b:
        return True
    for x in a:
        for y in b:
            if frozenset({x, y}) in PAIR_EFFECTS:
                return True
    return False


def effects_for(tags: frozenset[str]) -> list[EffectKind]:
    effects: list[EffectKind] = []
    seen: set[EffectKind] = set()
    covered: set[str] = set()
    for pair in combinations(sorted(tags), 2):
        key = frozenset(pair)
        if key in PAIR_EFFECTS:
            effect = PAIR_EFFECTS[key]
            if effect not in seen:
                effects.append(effect)
                seen.add(effect)
            covered |= key
    for tag in sorted(tags - covered):
        if tag in SINGLE_TAG_EFFECTS:
            effect = SINGLE_TAG_EFFECTS[tag]
            if effect not in seen:
                effects.append(effect)
                seen.add(effect)
    return effects
