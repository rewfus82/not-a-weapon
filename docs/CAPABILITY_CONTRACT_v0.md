# Capability Contract — v0

The vocabulary the resolver composes over, and the wall the renderer must implement. **The model may only emit these tokens** — it can never ask for something the renderer can't build. Creativity lives in *composing* these freely (which primitives, in what sequence, on what triggers), not in inventing new ones.

Rule (from the POC, still true): **never add a token until the renderer can both execute AND present it.** The enums are the capability contract.

This is v0 — generous enough that free composition feels bottomless, flagged for what the vertical slice actually implements. Not final; expect churn once the renderer is real.

---

## Delivery — the chassis (how the weapon reaches the world)

One per weapon. Locked in code from the delivery-slot item, not chosen freely by the model (POC lesson: delivery item fixes the form).

**Ranged / thrown**
- `HITSCAN` — instant-hit line. Guns, the pitiful .22, rifles. *(slice)*
- `PROJECTILE` — travels, dodgeable. Bolts, arrows, slow rounds. *(slice)*
- `LOBBED` — arcs, lands, detonates on impact/timer. Grenades, thrown jars.
- `BEAM` — continuous sustained line. Laser, flamethrower, stream.
- `THROWN` — discrete thrown object, single arc. Knife, axe, boomerang (returns via param).
- `SPRAY` — short-range cone spread. Shotgun, extinguisher, gout.
- `PLACED` — deployed into world, fires later on trigger. Mines, traps, deployables.

**Melee (co-equal — full breadth)**
- `SWING` — wide horizontal arc, hits multiple in front. Sword, bat, baton. *(slice)*
- `THRUST` — narrow forward stab, reach, single target. Spear, rapier.
- `SLAM` — overhead/downward, AoE on impact point. Hammer, maul.
- `WHIP` — long flexible reach, wide low-commit arc. Chain, whip, mop-strands.
- `GUARD` — defensive chassis: block/bash/parry, enables `ON_BLOCK`. Shield, plank.

**Self / mobility**
- `SELF` — affects the wielder, no target. Buffs, heals. *(slice — needed for non-weapon results)*
- `DASH` — movement-as-delivery. Lunge, blink, leap.

---

## EffectKind — the primitive payloads (what happens)

A stage carries one or more. Composition over these is where the surprise lives.

**Damage family**
- `DAMAGE` — direct hit.
- `BURN` — damage over time (fire, acid, corrosion).
- `EXPLODE` — burst AoE at a point.
- `PIERCE` — penetrate / ignore armor / pass through.
- `CHAIN` — arcs to nearby targets (lightning, ricochet).

**Control family** (physics chaos = your mischief spikes — lean in here)
- `KNOCKBACK` — physical shove. *(slice — core feel)*
- `LAUNCH` — send target airborne (juggle).
- `STAGGER` — brief interrupt / hitstun.
- `SNARE` — root in place.
- `SLOW` — movement debuff.
- `FREEZE` — hard lock, longer than snare.

**Self family**
- `HEAL` — restore.
- `SHIELD` — absorb.
- `SPEED` — mobility buff.

**Zany / utility** (the flavor that makes it *your* game)
- `SUMMON` — release homing sub-things (the bee swarm).
- `LURE` — bait: pull machines/enemies to a spot (great vs the hunters, on-theme).

Control family (`KNOCKBACK/LAUNCH/STAGGER/SNARE/SLOW/FREEZE`), self family, and `LURE` are **non-lethal** — a weapon built only from these is `CONTROL`/`SUPPORT`/`UTILITY`, not `WEAPON` (category is derived, see below).

---

## Trigger — when a stage fires

Richer than the POC's 4, because sequencing is a primary creative surface.
- `ON_USE` — on activation (self-buffs, the swing/shot itself). *(slice)*
- `ON_HIT` — on connecting with a target. *(slice)*
- `ON_IMPACT` — when a projectile/lob lands on world/surface.
- `ON_TRIGGER` — a placed thing set off by proximity.
- `ON_EXPIRE` — timeout / duration end / lob detonation.
- `ON_KILL` — when it downs a target (combo/chain-reaction enabler).
- `ON_BLOCK` — when a `GUARD` parry/block succeeds.

This is what lets "swing → ON_HIT: stagger → ON_KILL: summon swarm" exist as a sequence. The staged structure is the POC's; keep it.

---

## Category — derived, never trusted (code re-computes it)

Role, not form (delivery already encodes melee vs ranged).
- `WEAPON` — armed, lethal.
- `CONTROL` — non-lethal, disrupts (snare/knockback/etc.).
- `SUPPORT` — self/ally buffs (heal/shield/speed).
- `MOBILITY` — movement-focused.
- `UTILITY` — non-combat use (lure, etc.).
- `TRINKET` — harmless, minor.
- `DUD` — the low tail of the rarity roll; barely does anything.

---

## Gadget schema (the output shape)

```
Gadget:
  name: str
  category: Category            # DERIVED by code, not trusted
  tier: Tier                    # rarity tier; code assigns/clamps to budget (§6/§9)
  delivery: Delivery            # locked in code from the delivery item
  stages: list[Stage]           # ordered
  description: str              # flavor
  logic: str                    # the "aha" — how each item was read
  harmless: bool                # DERIVED, re-computed from effects
  params: dict[str, float]      # per-delivery tuning (see families below)
  color: str                    # set by code from delivery item (POC lesson)

Stage:
  trigger: Trigger
  effects: list[Effect]
  note: str

Effect:
  kind: EffectKind
  amount: float
  duration: float
  radius: float
  count: int
  note: str
```

**Params by delivery family** (the renderer expects these keys):
- Ranged (`HITSCAN/PROJECTILE/LOBBED/BEAM/THROWN/SPRAY`): `range`, `projectile_speed`, `spread`, `homing`, and for `THROWN` boomerangs `return_arc`.
- Melee (`SWING/THRUST/SLAM/WHIP`): `reach`, `arc` (degrees), `commit` (swing wind-up/recovery — the feel knob), `sweep_targets`.
- `GUARD`: `block_arc`, `parry_window`.
- Self/mobility (`SELF/DASH`): `distance`, `self_duration`.

---

## Ownership line — model vs code (§6, §8, §9)

- **Model owns:** meaning, name, `logic`, and *composition* — which effects, in what sequence, on which triggers, the interpretation of *these specific items*. This is the creative surface.
- **Code owns:** `delivery` (locked from item), `color`, `tier`/budget assignment, all caps/floors on magnitudes, `harmless` and `category` (re-derived), and the ~10–15% over-budget cap. Model proposes; code disposes on anything touching fairness or feasibility.

Static + RNG boosters act on the build-time roll within these code-owned limits (§6).

---

## v0 open questions (don't pretend these are settled)

1. **Melee param model.** `reach/arc/commit` is a guess; real melee feel may need more (hit-pause, cancel windows). Will churn once melee is prototyped — and per §9, feel values are play-tuned, not modeled.
2. **Is `tier` an input or output of resolution?** Does the model target a tier (compose to a budget it's told), or does code assign tier after scoring the composition? Leaning toward: code sets the budget, model composes within it, best-of-N spreads the *quality within* that budget. Needs confirming against the prompt experiment.
3. **`DASH` / `LAUNCH`** — delivery vs effect overlap (mobility as chassis vs as payload). Fine for v0; resolve when the renderer forces it.
4. Slice implements only the `(slice)`-flagged tokens; the rest are contract ceiling, not slice scope.
