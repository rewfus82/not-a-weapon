"""The capability contract in code: enums (the wall) + the output schema.

Mirrors docs/CAPABILITY_CONTRACT_v0.md. The enums are the single source of
truth; structured output constrains the model to exactly these tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field


class Delivery(str, Enum):
    HITSCAN = "HITSCAN"
    PROJECTILE = "PROJECTILE"
    LOBBED = "LOBBED"
    BEAM = "BEAM"
    THROWN = "THROWN"
    SPRAY = "SPRAY"
    PLACED = "PLACED"
    SWING = "SWING"
    THRUST = "THRUST"
    SLAM = "SLAM"
    WHIP = "WHIP"
    GUARD = "GUARD"
    SELF = "SELF"
    DASH = "DASH"


class EffectKind(str, Enum):
    DAMAGE = "DAMAGE"
    BURN = "BURN"
    EXPLODE = "EXPLODE"
    PIERCE = "PIERCE"
    CHAIN = "CHAIN"
    KNOCKBACK = "KNOCKBACK"
    LAUNCH = "LAUNCH"
    STAGGER = "STAGGER"
    SNARE = "SNARE"
    SLOW = "SLOW"
    FREEZE = "FREEZE"
    HEAL = "HEAL"
    SHIELD = "SHIELD"
    SPEED = "SPEED"
    SUMMON = "SUMMON"
    LURE = "LURE"


class Trigger(str, Enum):
    ON_USE = "ON_USE"
    ON_HIT = "ON_HIT"
    ON_IMPACT = "ON_IMPACT"
    ON_TRIGGER = "ON_TRIGGER"
    ON_EXPIRE = "ON_EXPIRE"
    ON_KILL = "ON_KILL"
    ON_BLOCK = "ON_BLOCK"


class Target(str, Enum):
    SELF = "SELF"      # applies to the wielder
    STRUCK = "STRUCK"  # applies to whatever the effect connects with


class Category(str, Enum):
    WEAPON = "WEAPON"
    CONTROL = "CONTROL"
    SUPPORT = "SUPPORT"
    MOBILITY = "MOBILITY"
    UTILITY = "UTILITY"
    TRINKET = "TRINKET"
    DUD = "DUD"


class Tier(str, Enum):
    DUD = "DUD"
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class Role(str, Enum):
    MECHANISM = "MECHANISM"   # feeds base delivery behaviour
    MODIFIER = "MODIFIER"     # feeds behavioural overlay + effect transform
    SUBSTANCE = "SUBSTANCE"   # feeds effect / damage type


class Flag(str, Enum):
    WIELDABLE = "WIELDABLE"
    FIREARM = "FIREARM"
    AMMUNITION = "AMMUNITION"
    LOADABLE = "LOADABLE"
    BASE_WEAPON = "BASE_WEAPON"


TIER_ORDER: dict["Tier", int] = {t: i for i, t in enumerate(Tier)}


def tier_at_least(tier: "Tier", floor: "Tier") -> bool:
    return TIER_ORDER[tier] >= TIER_ORDER[floor]


# --- family sets (code knowledge, used by the clamp + params) ---
# SUMMON is treated as lethal: a summoned swarm deals damage.
LETHAL_KINDS: frozenset[EffectKind] = frozenset({
    EffectKind.DAMAGE, EffectKind.BURN, EffectKind.EXPLODE,
    EffectKind.PIERCE, EffectKind.CHAIN, EffectKind.SUMMON,
})
CONTROL_KINDS: frozenset[EffectKind] = frozenset({
    EffectKind.KNOCKBACK, EffectKind.LAUNCH, EffectKind.STAGGER,
    EffectKind.SNARE, EffectKind.SLOW, EffectKind.FREEZE,
})
SELF_KINDS: frozenset[EffectKind] = frozenset({
    EffectKind.HEAL, EffectKind.SHIELD, EffectKind.SPEED,
})
UTILITY_KINDS: frozenset[EffectKind] = frozenset({EffectKind.LURE})

def default_target(kind: EffectKind) -> Target:
    """Code-authored default for the deterministic paths: self-family
    effects apply to the wielder; everything else applies to what it
    connects with (a LURE is bait thrown at a spot, not worn)."""
    return Target.SELF if kind in SELF_KINDS else Target.STRUCK


MELEE_DELIVERIES: frozenset[Delivery] = frozenset({
    Delivery.SWING, Delivery.THRUST, Delivery.SLAM, Delivery.WHIP,
})


# --- output schema ---
class Effect(BaseModel):
    kind: EffectKind
    target: Target  # required: the model must declare who it hits on every effect
    amount: float = Field(0.0, ge=0)
    duration: float = 0.0
    radius: float = 0.0
    count: int = 0
    note: str = ""


class Stage(BaseModel):
    trigger: Trigger
    effects: list[Effect]
    note: str = ""


class GadgetDraft(BaseModel):
    """Model-facing output. ONLY model-owned fields live here."""
    name: str
    description: str
    logic: str
    stages: list[Stage]


@dataclass
class ResolvedGadget:
    """Code-assembled final artifact. Code owns everything but `draft`."""
    draft: GadgetDraft
    delivery: Delivery
    tier: Tier
    category: Category
    harmless: bool
    color: str
    params: dict[str, float] = field(default_factory=dict)
