"""The deterministic resolver — the offline fallback (and the LLM's floor).

This is the chassis + payload composition the whole redesign is about:

  - the DELIVERY-slot item decides the chassis (its natural `shape`), so the
    player's declared intent picks the form instead of a flat tag-vote guessing;
  - the DAMAGE / UTILITY items become the ordered trigger stage — damage keeps
    its harm, utility is stripped to its non-damage behavior;
  - the MODIFIER item twists the whole thing (homing, added element, speed);
  - a placement's `fit` grades it, and the awakening's mismatch policy decides
    whether an off-nature placement is normalized away, penalized, or rewarded.

The LLM resolver (Phase 2) produces the SAME `Gadget` schema; this stays as the
no-key fallback and the thing the LLM output is clamped against.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .grammar import Build, Placement
from .items import Item
from .lucidity import Awakening, MismatchPolicy
from .schema import Category, Delivery, Effect, EffectKind, Gadget, Stage, Trigger

# fit below this = an off-nature placement, subject to the mismatch policy
MISMATCH_FIT = 0.35

# --- item mechanics (keyed by id; kept out of items.py so perception vs.
#     mechanics stay separate — a test guarantees parity with the catalog) ------

# the chassis an item becomes when it sits in the DELIVERY slot
SHAPE: dict[str, Delivery] = {
    "bear_trap": Delivery.PLACED,
    "beehive": Delivery.LOBBED,
    "fireworks": Delivery.PROJECTILE,
    "dry_ice": Delivery.LOBBED,
    "mop": Delivery.MELEE,
    "gasoline": Delivery.LOBBED,
    "salami": Delivery.MELEE,
    "dish_soap": Delivery.CONE,
    "handgun": Delivery.PROJECTILE,
    "pencil": Delivery.MELEE,
    "m16": Delivery.PROJECTILE,
    "grenade": Delivery.LOBBED,
    "chainsaw": Delivery.MELEE,
    "magnet": Delivery.AURA,
    "co2_canister": Delivery.CONE,
    "leaf_blower": Delivery.CONE,
    "potato": Delivery.PROJECTILE,
    "spaghetti": Delivery.CONE,
    "feathers": Delivery.CONE,
    "boombox": Delivery.DECOY,
    "nerf_gun": Delivery.PROJECTILE,
    "anchovies": Delivery.PROJECTILE,
    "ketchup": Delivery.CONE,
    "pixie_stix": Delivery.CONE,
    "boomerang": Delivery.RETURN,
    "fishing_rod": Delivery.RETURN,
    "pringles": Delivery.PROJECTILE,
    "vacuum": Delivery.AURA,
    "backpack": Delivery.AURA,
    "wire_hanger": Delivery.PROJECTILE,
    "zip_ties": Delivery.PLACED,
    "kitchen_knife": Delivery.MELEE,
    "frying_pan": Delivery.MELEE,
    "rolling_pin": Delivery.MELEE,
    "cheese_grater": Delivery.MELEE,
    "meat_cleaver": Delivery.MELEE,
    "hot_sauce": Delivery.CONE,
    "oven_cleaner": Delivery.CONE,
    "nail_gun": Delivery.PROJECTILE,
    "power_drill": Delivery.MELEE,
    "propane_tank": Delivery.LOBBED,
    "car_battery": Delivery.PLACED,
    "crowbar": Delivery.MELEE,
    "screwdriver": Delivery.MELEE,
    "weed_whacker": Delivery.MELEE,
    "slingshot": Delivery.PROJECTILE,
    "water_gun": Delivery.CONE,
    "super_ball": Delivery.PROJECTILE,
    "marbles": Delivery.PLACED,
    "yo_yo": Delivery.RETURN,
    "battery_acid": Delivery.LOBBED,
    "bug_spray": Delivery.CONE,
    "glow_sticks": Delivery.DECOY,
    "helium_tank": Delivery.CONE,
    "glue": Delivery.LOBBED,
    "duct_tape": Delivery.PLACED,
    "brick": Delivery.LOBBED,
    "mousetrap": Delivery.PLACED,
    "fire_extinguisher": Delivery.CONE,
    "spray_paint": Delivery.CONE,
    "laser_pointer": Delivery.BEAM,
    "taser": Delivery.BEAM,
    "ice_pack": Delivery.LOBBED,
    "jumper_cables": Delivery.BEAM,
    "bandages": Delivery.SELF,
    "caffeine_pills": Delivery.SELF,
    "trash_can_lid": Delivery.SELF,
    "tripod": Delivery.TURRET,
    "raw_meat": Delivery.DECOY,
    # --- new game item set (parity with scripts/item_db.gd archetypes) ---
    "motor_oil": Delivery.PUDDLE,
    "fertilizer": Delivery.LOBBED,
    "pitchfork": Delivery.MELEE,
    "barbed_wire": Delivery.CALTROPS,
    "hornet_nest": Delivery.PROJECTILE,
    "skillet": Delivery.MELEE,
    "cooking_grease": Delivery.PUDDLE,
    "drain_cleaner": Delivery.PUDDLE,
    "mason_jar": Delivery.LOBBED,
    "nails": Delivery.CALTROPS,
    "pvc_pipe": Delivery.PROJECTILE,
    "garage_spring": Delivery.PROJECTILE,
    "sledgehammer": Delivery.MELEE,
    "bleach": Delivery.PUDDLE,
    "road_flare": Delivery.LOBBED,
    "air_horn": Delivery.DECOY,
    "energy_drink": Delivery.SELF,
    "first_aid": Delivery.SELF,
    "painkillers": Delivery.SELF,
    "shop_vac": Delivery.AURA,
    "chain": Delivery.MELEE,
    "bullets": Delivery.PROJECTILE,
    "shells": Delivery.PROJECTILE,
    "arrows": Delivery.PROJECTILE,
    "bolts": Delivery.PROJECTILE,
    "gas_canister": Delivery.CONE,
    "rockets": Delivery.LOBBED,
    "energy_cell": Delivery.BEAM,
}

# effects an item brings as a PAYLOAD (damage/utility), priority order
BRINGS: dict[str, tuple[EffectKind, ...]] = {
    "bear_trap": (EffectKind.SNARE, EffectKind.DAMAGE),
    "beehive": (EffectKind.SPAWN, EffectKind.DAMAGE),
    "fireworks": (EffectKind.KNOCKBACK, EffectKind.BURN),
    "dry_ice": (EffectKind.FREEZE, EffectKind.SLOW),
    "mop": (EffectKind.SNARE, EffectKind.SLOW),
    "gasoline": (EffectKind.BURN,),
    "salami": (EffectKind.DAMAGE, EffectKind.KNOCKBACK),
    "dish_soap": (EffectKind.SLOW, EffectKind.SNARE),
    "handgun": (EffectKind.DAMAGE,),
    "pencil": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "m16": (EffectKind.DAMAGE, EffectKind.PIERCE),
    "grenade": (EffectKind.EXPLODE, EffectKind.DAMAGE),
    "chainsaw": (EffectKind.DAMAGE, EffectKind.PIERCE),
    "magnet": (EffectKind.COLLECT,),
    "co2_canister": (EffectKind.KNOCKBACK,),
    "leaf_blower": (EffectKind.KNOCKBACK,),
    "potato": (EffectKind.DAMAGE,),
    "spaghetti": (EffectKind.SLOW, EffectKind.SNARE),
    "feathers": (EffectKind.SLOW,),
    "boombox": (),
    "nerf_gun": (EffectKind.KNOCKBACK,),
    "anchovies": (EffectKind.DAMAGE,),
    "ketchup": (EffectKind.SLOW,),
    "pixie_stix": (),
    "boomerang": (EffectKind.DAMAGE,),
    "fishing_rod": (EffectKind.COLLECT,),
    "pringles": (EffectKind.PIERCE,),
    "vacuum": (EffectKind.COLLECT,),
    "backpack": (EffectKind.COLLECT,),
    "wire_hanger": (EffectKind.DAMAGE,),
    "zip_ties": (EffectKind.SNARE,),
    "kitchen_knife": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "frying_pan": (EffectKind.KNOCKBACK, EffectKind.DAMAGE),
    "rolling_pin": (EffectKind.KNOCKBACK, EffectKind.DAMAGE),
    "cheese_grater": (EffectKind.DAMAGE, EffectKind.PIERCE),
    "meat_cleaver": (EffectKind.DAMAGE, EffectKind.PIERCE),
    "hot_sauce": (EffectKind.BURN,),
    "oven_cleaner": (EffectKind.BURN, EffectKind.DAMAGE),
    "nail_gun": (EffectKind.DAMAGE, EffectKind.PIERCE),
    "power_drill": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "propane_tank": (EffectKind.EXPLODE, EffectKind.BURN),
    "car_battery": (EffectKind.CHAIN, EffectKind.BURN),
    "crowbar": (EffectKind.DAMAGE, EffectKind.KNOCKBACK),
    "screwdriver": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "weed_whacker": (EffectKind.DAMAGE, EffectKind.PIERCE),
    "slingshot": (EffectKind.DAMAGE,),
    "water_gun": (EffectKind.KNOCKBACK,),
    "super_ball": (EffectKind.KNOCKBACK,),
    "marbles": (EffectKind.SLOW,),
    "yo_yo": (EffectKind.DAMAGE,),
    "battery_acid": (EffectKind.BURN, EffectKind.DAMAGE),
    "bug_spray": (EffectKind.BURN,),
    "glow_sticks": (),
    "helium_tank": (EffectKind.KNOCKBACK,),
    "glue": (EffectKind.SNARE, EffectKind.SLOW),
    "duct_tape": (EffectKind.SNARE,),
    "brick": (EffectKind.DAMAGE, EffectKind.KNOCKBACK),
    "mousetrap": (EffectKind.SNARE, EffectKind.DAMAGE),
    "fire_extinguisher": (EffectKind.FREEZE, EffectKind.KNOCKBACK),
    "spray_paint": (EffectKind.BURN,),
    "laser_pointer": (EffectKind.DAMAGE,),
    "taser": (EffectKind.SNARE, EffectKind.CHAIN),
    "ice_pack": (EffectKind.FREEZE, EffectKind.SLOW),
    "jumper_cables": (EffectKind.CHAIN, EffectKind.BURN),
    "bandages": (EffectKind.HEAL,),
    "caffeine_pills": (EffectKind.SPEED,),
    "trash_can_lid": (EffectKind.SHIELD,),
    "tripod": (),
    "raw_meat": (),
    # --- new game item set ---
    "motor_oil": (EffectKind.SLOW, EffectKind.BURN),
    "fertilizer": (EffectKind.EXPLODE, EffectKind.DAMAGE),
    "pitchfork": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "barbed_wire": (EffectKind.SNARE, EffectKind.DAMAGE),
    "hornet_nest": (EffectKind.SPAWN, EffectKind.DAMAGE),
    "skillet": (EffectKind.KNOCKBACK, EffectKind.DAMAGE),
    "cooking_grease": (EffectKind.SLOW, EffectKind.BURN),
    "drain_cleaner": (EffectKind.BURN, EffectKind.DAMAGE),
    "mason_jar": (),
    "nails": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "pvc_pipe": (EffectKind.PIERCE,),
    "garage_spring": (EffectKind.KNOCKBACK,),
    "sledgehammer": (EffectKind.KNOCKBACK, EffectKind.DAMAGE),
    "bleach": (EffectKind.BURN, EffectKind.DAMAGE),
    "road_flare": (EffectKind.BURN,),
    "air_horn": (),
    "energy_drink": (EffectKind.SPEED,),
    "first_aid": (EffectKind.HEAL,),
    "painkillers": (EffectKind.HEAL,),
    "shop_vac": (EffectKind.COLLECT,),
    "chain": (EffectKind.DAMAGE, EffectKind.KNOCKBACK),
    "bullets": (EffectKind.DAMAGE,),
    "shells": (EffectKind.DAMAGE, EffectKind.KNOCKBACK),
    "arrows": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "bolts": (EffectKind.PIERCE, EffectKind.DAMAGE),
    "gas_canister": (EffectKind.BURN,),
    "rockets": (EffectKind.EXPLODE, EffectKind.DAMAGE),
    "energy_cell": (EffectKind.CHAIN, EffectKind.BURN),
}


@dataclass(frozen=True)
class Mod:
    """How an item behaves in the MODIFIER slot: a twist on the whole gadget."""

    homing: bool = False
    speed_mult: float = 1.0
    add: tuple[EffectKind, ...] = ()


MODIFIERS: dict[str, Mod] = {
    "magnet": Mod(homing=True),
    "co2_canister": Mod(speed_mult=1.4, add=(EffectKind.FREEZE,)),
    "gasoline": Mod(add=(EffectKind.BURN,)),
    "dry_ice": Mod(add=(EffectKind.FREEZE,)),
    "pencil": Mod(add=(EffectKind.PIERCE,)),
    "dish_soap": Mod(add=(EffectKind.SLOW,)),
    "feathers": Mod(add=(EffectKind.SLOW,)),
    "spaghetti": Mod(add=(EffectKind.SNARE,)),
    "potato": Mod(),  # a suppressor: changes character, adds no effect
    "beehive": Mod(add=(EffectKind.SPAWN,)),
    "fireworks": Mod(add=(EffectKind.KNOCKBACK,)),
    "pringles": Mod(add=(EffectKind.PIERCE,)),      # a barrel / scope
    "hot_sauce": Mod(add=(EffectKind.BURN,)),
    "oven_cleaner": Mod(add=(EffectKind.BURN,)),
    "car_battery": Mod(add=(EffectKind.CHAIN,)),
    "propane_tank": Mod(add=(EffectKind.EXPLODE,)),
    "ice_pack": Mod(add=(EffectKind.FREEZE,)),
    "fire_extinguisher": Mod(add=(EffectKind.FREEZE,)),
    "jumper_cables": Mod(add=(EffectKind.CHAIN,)),
    "taser": Mod(add=(EffectKind.CHAIN,)),
    "glue": Mod(add=(EffectKind.SNARE,)),
    "duct_tape": Mod(add=(EffectKind.SNARE,)),
    "zip_ties": Mod(add=(EffectKind.SNARE,)),
    "ketchup": Mod(add=(EffectKind.SLOW,)),
    "marbles": Mod(add=(EffectKind.SLOW,)),
    "helium_tank": Mod(speed_mult=1.4),             # propellant, like CO2
    "caffeine_pills": Mod(add=(EffectKind.SPEED,)),
    "battery_acid": Mod(add=(EffectKind.BURN,)),
    "bug_spray": Mod(add=(EffectKind.BURN,)),
    "spray_paint": Mod(add=(EffectKind.BURN,)),
    "pixie_stix": Mod(add=(EffectKind.SPEED,)),     # sugar rush
}

# default tuning per primitive (the deterministic floor; the LLM can vary these)
_MAG: dict[EffectKind, dict] = {
    EffectKind.DAMAGE: {"amount": 12.0},
    EffectKind.SNARE: {"duration": 2.2},
    EffectKind.SLOW: {"amount": 55.0, "duration": 3.0},
    EffectKind.KNOCKBACK: {"amount": 240.0},
    EffectKind.BURN: {"amount": 5.0, "duration": 3.0},
    EffectKind.FREEZE: {"duration": 2.0},
    EffectKind.EXPLODE: {"amount": 16.0, "radius": 90.0},
    EffectKind.SPAWN: {"count": 4},
    EffectKind.PIERCE: {"count": 2},
    EffectKind.CHAIN: {"amount": 8.0, "radius": 110.0, "count": 3},
    EffectKind.COLLECT: {"radius": 180.0},
    EffectKind.HEAL: {"amount": 40.0},
    EffectKind.SHIELD: {"amount": 40.0},
    EffectKind.SPEED: {"amount": 1.6, "duration": 6.0},
}

# effects that mean "this can actually hurt something"
_LETHAL = {EffectKind.DAMAGE, EffectKind.EXPLODE, EffectKind.BURN,
           EffectKind.SPAWN, EffectKind.CHAIN}
# effects a UTILITY placement is allowed to keep (non-damage behaviors)
_CONTROL = {EffectKind.SNARE, EffectKind.SLOW, EffectKind.KNOCKBACK,
            EffectKind.FREEZE, EffectKind.COLLECT, EffectKind.SPAWN}

_CHASSIS_WORD: dict[Delivery, str] = {
    Delivery.PROJECTILE: "Gun", Delivery.LOBBED: "Bomb", Delivery.PLACED: "Trap",
    Delivery.CONE: "Sprayer", Delivery.BEAM: "Lance", Delivery.MELEE: "Basher",
    Delivery.RETURN: "Boomerang", Delivery.AURA: "Field", Delivery.SELF: "Kit",
    Delivery.TURRET: "Turret", Delivery.DECOY: "Decoy",
    Delivery.CALTROPS: "Scatter", Delivery.PUDDLE: "Slick",
}

_CHASSIS_TRIGGER: dict[Delivery, Trigger] = {
    Delivery.PLACED: Trigger.ON_TRIGGER,
    Delivery.LOBBED: Trigger.ON_EXPIRE,
    Delivery.CALTROPS: Trigger.ON_EXPIRE,
    Delivery.PUDDLE: Trigger.ON_EXPIRE,
    Delivery.SELF: Trigger.ON_USE,
    Delivery.TURRET: Trigger.ON_USE,
    Delivery.DECOY: Trigger.ON_USE,
    Delivery.AURA: Trigger.ON_USE,
}


def _mk(kind: EffectKind, scale: float = 1.0) -> Effect:
    m = _MAG.get(kind, {})
    amount = float(m.get("amount", 0.0)) * scale
    count = m.get("count", 0)
    count = max(1, round(count * scale)) if count else 0
    return Effect(kind=kind, amount=amount,
                  duration=float(m.get("duration", 0.0)),
                  radius=float(m.get("radius", 0.0)), count=count)


def _contribution(p: Placement, policy: MismatchPolicy) -> tuple[bool, float]:
    """Given a placement's fit + the era policy, decide (include?, magnitude scale)."""
    if p.fit >= MISMATCH_FIT:
        return True, 1.0
    if policy is MismatchPolicy.NORMALIZE:
        return False, 0.0          # the simulation quietly discards the anomaly
    if policy is MismatchPolicy.PENALIZE:
        return True, 0.5           # it works, but weak and janky
    return True, 1.1               # LUCID: breaking the rule is rewarded


@dataclass
class _Assembly:
    order: list[EffectKind] = field(default_factory=list)
    by_kind: dict[EffectKind, Effect] = field(default_factory=dict)

    def add(self, kind: EffectKind, scale: float) -> None:
        e = _mk(kind, scale)
        if kind in self.by_kind:
            cur = self.by_kind[kind]
            cur.amount += e.amount
            cur.count = max(cur.count, e.count)
            cur.duration = max(cur.duration, e.duration)
            cur.radius = max(cur.radius, e.radius)
        else:
            self.by_kind[kind] = e
            self.order.append(kind)

    def effects(self) -> list[Effect]:
        return [self.by_kind[k] for k in self.order]


def deterministic_resolve(build: Build, awakening: Awakening) -> Gadget:
    """Compose a Gadget from a filled slot grid, with no network / no LLM."""
    policy = awakening.mismatch_policy()

    # 1) chassis from the delivery slot (declared intent), else improvised.
    delivery_item: Item | None = build.delivery
    chassis = SHAPE.get(delivery_item.id, Delivery.PROJECTILE) if delivery_item else Delivery.PROJECTILE
    trigger = _CHASSIS_TRIGGER.get(chassis, Trigger.ON_HIT)

    asm = _Assembly()

    # 2) the chassis item's own nature contributes first (a trap snaps, etc.)
    if delivery_item is not None:
        inc, scale = _contribution(Placement("delivery", delivery_item, delivery_item.fit_for("delivery")), policy)
        if inc:
            for k in BRINGS.get(delivery_item.id, ()):
                asm.add(k, scale * 0.6)  # the frame contributes lightly

    # 3) utility (non-damage behavior) comes before damage in the sequence
    if build.utility is not None:
        inc, scale = _contribution(Placement("utility", build.utility, build.utility.fit_for("utility")), policy)
        if inc:
            for k in BRINGS.get(build.utility.id, ()):
                if k in _CONTROL:            # utility is stripped to non-damage
                    asm.add(k, scale)

    # 4) damage (the business end)
    if build.damage is not None:
        inc, scale = _contribution(Placement("damage", build.damage, build.damage.fit_for("damage")), policy)
        if inc:
            brings = BRINGS.get(build.damage.id, ())
            for k in brings:
                asm.add(k, scale)
            if not any(k in _LETHAL for k in brings):
                asm.add(EffectKind.DAMAGE, scale)  # something in the damage slot should try to hurt

    # 5) modifier twist
    homing = False
    speed_mult = 1.0
    if build.modifier is not None:
        inc, scale = _contribution(Placement("modifier", build.modifier, build.modifier.fit_for("modifier")), policy)
        if inc:
            mod = MODIFIERS.get(build.modifier.id, Mod())
            homing = mod.homing
            speed_mult = mod.speed_mult
            for k in mod.add:
                asm.add(k, scale)

    effects = asm.effects()

    # 6) categorize + harmlessness
    armed = any(e.kind in _LETHAL for e in effects)
    harmless = not armed
    category = _categorize(build, effects, chassis, harmless)
    if harmless:
        for e in effects:
            if e.kind is EffectKind.DAMAGE:
                e.amount = min(e.amount, 1.0)

    if not effects:
        # nothing survived (e.g. an all-junk build normalized to nothing)
        category = Category.DUD

    stages = [Stage(trigger=trigger, effects=effects)] if effects else []

    g = Gadget(
        name=_name(build, chassis),
        category=category,
        chassis=chassis,
        stages=stages,
        description=_describe(chassis, category, harmless),
        logic=_logic(build, chassis),
        harmless=harmless,
        homing=homing,
        projectile_speed=min(700.0 * speed_mult, 1400.0),
        params=(_boomerang_params(build) if chassis is Delivery.RETURN else {}),
        color=(delivery_item.color if delivery_item else "#b0b0b0"),
    )
    return g


# Boomerang (RETURN) flight tuning — the delivery-profile blueprint (DESIGN.md §10).
# Defaults mirror main.gd's BOOMERANG_* constants; the modifier item bends the arc.
def _boomerang_params(build: Build) -> dict[str, float]:
    rng, curve, rspeed = 300.0, 260.0, 600.0
    mod = build.modifier
    if mod is not None:
        if mod.id in ("feathers",):                        # floaty: wide, slow loop
            curve, rspeed, rng = curve * 1.6, rspeed * 0.75, rng * 1.1
        elif mod.id in ("co2_canister", "garage_spring", "helium_tank"):  # propellant/spring
            rspeed, curve = rspeed * 1.4, curve * 0.7
        elif mod.id in ("brick", "car_battery", "propane_tank"):          # heavy: short, snappy
            rng, curve = rng * 0.8, curve * 0.7
    return {"range": rng, "curve": curve, "return_speed": rspeed}


def resolve(build: Build, awakening: Awakening, client: object | None = None,
            strict: bool = False) -> Gadget:
    """Public entry. With a client, the LLM composes; without one, the
    deterministic floor does. Both return a clamped Gadget in the same schema.

    A combine must never hard-crash: if the LLM path fails (network, a malformed
    or schema-violating response), it falls back to the deterministic floor.
    Pass strict=True to surface the raw failure instead (used by the eval harness).
    """
    if client is None:
        return deterministic_resolve(build, awakening)
    from .llm import llm_resolve  # local import: anthropic is an optional dep
    try:
        return clamp_gadget(llm_resolve(build, awakening, client))
    except Exception:
        if strict:
            raise
        return deterministic_resolve(build, awakening)


# --- shared safety net: keep any Gadget (LLM or not) inside sane numbers ------

# per-effect caps so a hallucinated "damage 99999" can't reach the engine
_CAPS: dict[EffectKind, dict] = {
    EffectKind.DAMAGE: {"amount": 60.0},
    EffectKind.EXPLODE: {"amount": 60.0, "radius": 220.0},
    EffectKind.KNOCKBACK: {"amount": 500.0},
    EffectKind.BURN: {"amount": 20.0, "duration": 8.0},
    EffectKind.SLOW: {"amount": 90.0, "duration": 8.0},
    EffectKind.SNARE: {"duration": 6.0},
    EffectKind.FREEZE: {"duration": 6.0},
    EffectKind.SPAWN: {"count": 10},
    EffectKind.PIERCE: {"count": 8},
    EffectKind.CHAIN: {"amount": 30.0, "radius": 200.0, "count": 8},
    EffectKind.COLLECT: {"radius": 300.0},
    EffectKind.HEAL: {"amount": 80.0},
    EffectKind.SHIELD: {"amount": 80.0},
    EffectKind.SPEED: {"amount": 2.5, "duration": 12.0},
}


# minimum values so a present effect can't be imperceptible (the model sometimes
# fat-fingers a knockback of 8 or a slow with no duration). Only floors the field
# that DRIVES each effect (slow/snare/freeze are duration-driven, not amount).
_FLOORS: dict[EffectKind, dict] = {
    EffectKind.DAMAGE: {"amount": 4.0},
    EffectKind.KNOCKBACK: {"amount": 80.0},
    EffectKind.EXPLODE: {"amount": 10.0, "radius": 60.0},
    EffectKind.BURN: {"amount": 2.0, "duration": 2.0},
    EffectKind.SLOW: {"duration": 1.5},
    EffectKind.SNARE: {"duration": 1.0},
    EffectKind.FREEZE: {"duration": 1.0},
    EffectKind.CHAIN: {"amount": 4.0, "radius": 90.0, "count": 2},
    EffectKind.SPAWN: {"count": 1},
    EffectKind.COLLECT: {"radius": 120.0},
}


def clamp_gadget(g: Gadget) -> Gadget:
    """Clamp every effect field into its [floor, cap] band and re-assert harmlessness."""
    for e in g.all_effects():
        caps = _CAPS.get(e.kind, {})
        floors = _FLOORS.get(e.kind, {})
        if "amount" in caps:
            e.amount = min(e.amount, caps["amount"])
        if "duration" in caps:
            e.duration = min(e.duration, caps["duration"])
        if "radius" in caps:
            e.radius = min(e.radius, caps["radius"])
        if "count" in caps:
            e.count = min(e.count, caps["count"])
        if "amount" in floors:
            e.amount = max(e.amount, floors["amount"])
        if "duration" in floors:
            e.duration = max(e.duration, floors["duration"])
        if "radius" in floors:
            e.radius = max(e.radius, floors["radius"])
        if "count" in floors:
            e.count = max(e.count, floors["count"])
    # keep delivery params inside sane bands too (a hallucinated range=99999 can't ship)
    for key, (lo, hi) in _PARAM_BANDS.items():
        if key in g.params:
            g.params[key] = max(lo, min(hi, g.params[key]))
    # harmlessness is DERIVED, not trusted: something with no damaging effect can't
    # be a weapon, and something that hurts isn't harmless — whatever the model said.
    g.harmless = not any(e.kind in _LETHAL for e in g.all_effects())
    if g.harmless and g.category is Category.WEAPON:
        controls = any(e.kind in {EffectKind.SNARE, EffectKind.SLOW, EffectKind.KNOCKBACK, EffectKind.FREEZE}
                       for e in g.all_effects())
        g.category = Category.CONTROL if controls else Category.TRINKET
    return g


# sane bands for the delivery-behavior params (boomerang blueprint)
_PARAM_BANDS: dict[str, tuple[float, float]] = {
    "range": (80.0, 600.0),
    "curve": (0.0, 800.0),
    "return_speed": (200.0, 1200.0),
}


# --- flavor (deterministic + legible; the LLM makes it witty) ----------------

def _categorize(build: Build, effects: list[Effect], chassis: Delivery, harmless: bool) -> Category:
    kinds = {e.kind for e in effects}
    if kinds & {EffectKind.HEAL, EffectKind.SHIELD, EffectKind.SPEED}:
        return Category.SUPPORT
    if not effects:
        return Category.DUD
    if harmless:
        if kinds & {EffectKind.SNARE, EffectKind.SLOW, EffectKind.KNOCKBACK, EffectKind.FREEZE}:
            return Category.CONTROL
        if EffectKind.COLLECT in kinds:
            return Category.UTILITY
        return Category.TRINKET
    # armed, but if the player never filled the damage slot it's control-first
    if build.damage is None and (kinds & {EffectKind.SNARE, EffectKind.SLOW, EffectKind.FREEZE}) \
            and not (kinds & {EffectKind.DAMAGE, EffectKind.EXPLODE}):
        return Category.CONTROL
    return Category.WEAPON


def _name(build: Build, chassis: Delivery) -> str:
    base_item = build.damage or build.delivery or build.utility or build.modifier
    base = base_item.name.split()[-1] if base_item else "Improvised"
    return f"{base} {_CHASSIS_WORD[chassis]}"


def _describe(chassis: Delivery, category: Category, harmless: bool) -> str:
    if harmless:
        return "It works. It is not a weapon. It is barely an opinion."
    word = _CHASSIS_WORD[chassis].lower()
    return f"A {word} that does what its parts imply - no more, no less."


def _logic(build: Build, chassis: Delivery) -> str:
    bits = [f"delivery={build.delivery.id} -> {chassis.value} chassis"] if build.delivery else ["improvised chassis"]
    if build.damage is not None:
        bits.append(f"damage={build.damage.id}")
    if build.utility is not None:
        bits.append(f"utility={build.utility.id} (non-damage)")
    if build.modifier is not None:
        bits.append(f"modifier={build.modifier.id} (twist)")
    return "; ".join(bits)
