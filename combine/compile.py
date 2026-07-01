"""Lower a Gadget (chassis + stages) into the flat structure the engine runs.

This is the concrete 'AI output → engine executes it' bridge. `main.gd`'s Gadget
today is a single delivery + a flat effects list; this flattens our staged form
into exactly that, and maps our vocabulary onto the engine's const strings. Any
future engine just needs to consume this same dict.
"""

from __future__ import annotations

from .schema import Delivery, EffectKind, Gadget

# our EffectKind value -> the const string gadget.gd uses (mostly identical)
_EFFECT_CONST: dict[EffectKind, str] = {
    EffectKind.DAMAGE: "damage",
    EffectKind.SLOW: "slow",
    EffectKind.SNARE: "snare",
    EffectKind.KNOCKBACK: "knockback",
    EffectKind.EXPLODE: "explode",
    EffectKind.BURN: "burn",
    EffectKind.PIERCE: "pierce",
    EffectKind.SPAWN: "spawn",
    EffectKind.COLLECT: "collect",
    EffectKind.FREEZE: "freeze",
    EffectKind.CHAIN: "chain",
    EffectKind.HEAL: "heal",
    EffectKind.SHIELD: "shield",
    EffectKind.SPEED: "speed_buff",   # the one rename: gadget.gd SPEED := "speed_buff"
}

# delivery -> the engine's Gadget.Delivery enum NAME (uppercased in GDScript)
_DELIVERY_ENUM: dict[Delivery, str] = {
    Delivery.PROJECTILE: "PROJECTILE",
    Delivery.MELEE: "MELEE",
    Delivery.LOBBED: "LOBBED",
    Delivery.AURA: "AURA",
    Delivery.PLACED: "PLACED",
    Delivery.CONE: "CONE",
    Delivery.BEAM: "BEAM",
    Delivery.RETURN: "RETURN",
    Delivery.SELF: "SELF",
    Delivery.TURRET: "TURRET",
    Delivery.DECOY: "DECOY",
}


def to_engine(gadget: Gadget) -> dict:
    """Flatten a Gadget into the engine-consumable dict (JSON-safe)."""
    effects = []
    for e in gadget.all_effects():
        effects.append({
            "kind": _EFFECT_CONST[e.kind],
            "amount": e.amount,
            "duration": e.duration,
            "radius": e.radius,
            "count": e.count,
        })
    return {
        "name": gadget.name,
        "description": gadget.description,
        "category": gadget.category.value,
        "delivery": _DELIVERY_ENUM[gadget.chassis],
        "effects": effects,
        "homing": gadget.homing,
        "harmless": gadget.harmless,
        "projectile_speed": gadget.projectile_speed,
        "color": gadget.color,
    }
