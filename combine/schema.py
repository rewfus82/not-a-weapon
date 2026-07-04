"""The combine OUTPUT contract — engine-agnostic.

Everything the resolver (deterministic OR LLM) may emit lives here, and *only*
what an engine can actually execute. This is the capability contract in one
place: the `Delivery` and `EffectKind` enums mirror what `scripts/main.gd` runs
today. A resolver that stays inside these types can be rendered by Godot now and
by whatever we migrate to later.

Shape: a Gadget is a CHASSIS (how it's delivered) + an ordered list of STAGES
(what happens, and when), each stage carrying primitive EFFECTS. That structure
is what lets "bear trap -> on trigger: snare, then startle, then swarm" exist,
instead of a flat unordered bag stapled to one delivery.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Delivery(str, Enum):
    """How the gadget reaches the world. Mirrors Gadget.Delivery in main.gd."""

    PROJECTILE = "projectile"
    MELEE = "melee"
    LOBBED = "lobbed"
    AURA = "aura"
    PLACED = "placed"
    CONE = "cone"
    BEAM = "beam"
    RETURN = "return"
    SELF = "self"
    TURRET = "turret"
    DECOY = "decoy"
    CALTROPS = "caltrops"   # thrown -> scatter into a ground hazard field
    PUDDLE = "puddle"       # thrown -> a liquid ground zone (slick/flammable/caustic)


class EffectKind(str, Enum):
    """A primitive the engine knows how to apply. Mirrors the consts in gadget.gd."""

    DAMAGE = "damage"
    SLOW = "slow"
    SNARE = "snare"
    KNOCKBACK = "knockback"
    EXPLODE = "explode"
    BURN = "burn"
    PIERCE = "pierce"
    SPAWN = "spawn"
    COLLECT = "collect"
    FREEZE = "freeze"
    CHAIN = "chain"
    HEAL = "heal"
    SHIELD = "shield"
    SPEED = "speed"


class Trigger(str, Enum):
    """When a stage fires within the gadget's lifecycle."""

    ON_USE = "on_use"          # the player activates it (buffs, deploys, swings)
    ON_HIT = "on_hit"          # the delivery connects with an enemy
    ON_TRIGGER = "on_trigger"  # a placed thing is set off by a nearby enemy
    ON_EXPIRE = "on_expire"    # timeout / lobbed detonation on landing


class Category(str, Enum):
    WEAPON = "weapon"
    CONTROL = "control"
    SUPPORT = "support"
    UTILITY = "utility"
    MOBILITY = "mobility"
    TRINKET = "trinket"
    DUD = "dud"


class Effect(BaseModel):
    """One primitive effect with its tuning. `note` is free flavor (unbounded)."""

    kind: EffectKind
    amount: float = 0.0
    duration: float = 0.0
    radius: float = 0.0
    count: int = 0
    note: str = ""


class Stage(BaseModel):
    """A step in the trigger sequence: 'when this happens, do these effects'."""

    trigger: Trigger = Trigger.ON_HIT
    effects: list[Effect] = Field(default_factory=list)
    note: str = ""


class Gadget(BaseModel):
    """The resolved contraption. chassis + ordered stages + free flavor."""

    name: str
    category: Category
    chassis: Delivery
    stages: list[Stage] = Field(default_factory=list)
    description: str = ""
    logic: str = ""            # the 'aha': how each slot was read
    harmless: bool = False
    homing: bool = False
    projectile_speed: float = Field(default=700.0, ge=0.0, le=1400.0)
    color: str = "#b0b0b0"

    @model_validator(mode="after")
    def _stages_present_unless_dud(self) -> "Gadget":
        if self.category is not Category.DUD and not self.stages:
            raise ValueError("a non-DUD gadget must have at least one stage")
        return self

    def all_effects(self) -> list[Effect]:
        return [e for s in self.stages for e in s.effects]

    def has(self, kind: EffectKind) -> bool:
        return any(e.kind is kind for e in self.all_effects())


class GadgetDraft(BaseModel):
    """What the LLM fills — the creative fields only.

    `color` is deliberately EXCLUDED: the model treats a free-text color field as a
    creative outlet, emitting hex grids that blow the token budget and corrupt the
    JSON (dropping `stages`). Color is not a creative decision — code sets it from
    the delivery item via `to_gadget()`.
    """

    name: str
    category: Category
    chassis: Delivery
    stages: list[Stage] = Field(default_factory=list)
    description: str = ""
    logic: str = ""
    harmless: bool = False
    homing: bool = False
    projectile_speed: float = Field(default=700.0, ge=0.0, le=1400.0)

    @model_validator(mode="after")
    def _stages_present_unless_dud(self) -> "GadgetDraft":
        if self.category is not Category.DUD and not self.stages:
            raise ValueError("a non-DUD gadget must have at least one stage")
        return self

    def to_gadget(self, color: str = "#b0b0b0") -> Gadget:
        return Gadget(**self.model_dump(), color=color)
