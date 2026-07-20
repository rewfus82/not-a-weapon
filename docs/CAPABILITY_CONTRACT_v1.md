# Capability Contract — v1

The vocabulary the resolver composes over, and the wall the renderer must implement. **The model may only emit these tokens** — it can never ask for something the renderer can't build. Creativity lives in *composing* these freely (which primitives, in what sequence, on what triggers, at which target), not in inventing new ones.

Rule (from the POC, still true): **never add a token until the renderer can both execute AND present it.** The enums are the capability contract.

v1 = v0 tightened against the 2026-07-16 playtest evidence (see `docs/superpowers/specs/2026-07-16-contract-v1-design.md`): every effect declares who it hits, derivation keys on (kind, target), self-kit trigger semantics are law, and duration/radius/count cost budget. No enum family gained a token except `Target`, which is a validation axis (who an existing effect applies to — the renderer already had to know), not a renderer capability.

---

## Delivery — the chassis (how the weapon reaches the world)

Unchanged from v0. One per weapon, locked in code from the delivery-slot item.

Ranged/thrown: `HITSCAN`, `PROJECTILE`, `LOBBED`, `BEAM`, `THROWN`, `SPRAY`, `PLACED`.
Melee: `SWING`, `THRUST`, `SLAM`, `WHIP`, `GUARD` (enables `ON_BLOCK`).
Self/mobility: `SELF` (a kit worn or used on yourself — see trigger semantics below), `DASH`.

## EffectKind — the primitive payloads (what happens)

Unchanged from v0.

Damage family (lethal): `DAMAGE`, `BURN`, `EXPLODE`, `PIERCE`, `CHAIN` (+ `SUMMON` counts lethal).
Control family: `KNOCKBACK`, `LAUNCH`, `STAGGER`, `SNARE`, `SLOW`, `FREEZE`.
Self family: `HEAL`, `SHIELD`, `SPEED`.
Utility: `LURE`. (`SUMMON` lives here in flavor, in the damage family in law.)

## Target — who the effect applies to (NEW in v1)

- `STRUCK` — whatever the effect connects with: the thing hit, snared, or dosed.
- `SELF` — the wielder.

Required on **every** effect; there is no default (a baked scaffold can never contain a "whatever the default was that week" absence). Composition, not new tokens, expresses the interesting cases:

- Lifedrain = `DAMAGE@STRUCK + HEAL@SELF` on one stage — a weapon that feeds its user.
- The healing gun = `HEAL@STRUCK` — a dose fired into whatever the shot touches.
- A self-cost = `DAMAGE@SELF` riding a benefit — the adrenaline crash.

## Trigger — when a stage fires

Tokens unchanged from v0: `ON_USE`, `ON_HIT`, `ON_IMPACT`, `ON_TRIGGER`, `ON_EXPIRE`, `ON_KILL`, `ON_BLOCK`.

**Self-kit semantics (SELF chassis), enforced by deterministic repair (`resolver/validate.py`) — repaired, never rejected:**

| Rule | Repair |
| --- | --- |
| `ON_USE`, `ON_EXPIRE`, `ON_KILL` always legal | — |
| `ON_HIT` means "when *you* get hit" — legal only if the chassis item carries the `protective` tag | retrigger stage to `ON_USE` |
| `ON_IMPACT`, `ON_TRIGGER`, `ON_BLOCK` illegal (nothing is thrown, placed, or blocked-with) | retrigger stage to `ON_USE` |
| Effects in `ON_USE`/`ON_EXPIRE` stages target `SELF` | retarget to `SELF` |
| Effects in a legal reactive `ON_HIT` stage may target either (`STRUCK` = whoever hit you — retaliation) | — |
| Effects in `ON_KILL` stages target `SELF` (the reward reading; the target is dead) | retarget to `SELF` |

`ON_KILL` on a self-kit = "when you down something while this is active." The protective rule is live: the riot shield locks a GUARD chassis, while the firefighter turnout coat (worn, SELF) activates the ON_HIT self-kit path.

**Non-SELF chassis: every (kind, target) combination is legal.** Lifedrain, the healing gun, and self-costs are intended compositions.

## Category & harmless — derived, never trusted (code re-computes both)

`harmless` = no lethal kind targeting `STRUCK`. Harmless means *can't hurt others*; hurting yourself is a cost, not a threat.

`derive_category` walks in priority order over the (kind, target) pairs present:

1. no effects → `DUD`
2. any lethal kind @`STRUCK` → `WEAPON`
3. any control kind @`STRUCK` → `CONTROL`
4. any self-family kind (either target) **or** any non-`LURE` kind @`SELF` → `SUPPORT`
5. any `LURE` → `UTILITY`
6. else → `TRINKET`

Accepted edge (documented, not special-cased): a build whose only effect is `DAMAGE@SELF` derives `SUPPORT`.

## Budget — weighted cost (NEW in v1)

Every effect field costs budget; raw amount-sum is dead:

```
cost(effect) = amount   * W_AMOUNT[kind]     # per-kind table, all 1.0 at v1
             + duration * W_DURATION
             + radius   * W_RADIUS
             + count    * W_COUNT
```

Weights live beside `TIER_BUDGET` in `resolver/clamp.py` — one tuning location, code-owned; values are deliberately crude placeholders until the renderer exists. Tuning them is a deterministic re-clamp, never a re-bake. Normalization scales the float fields by one shared factor (proportions preserved); counts are integers with fixed cost and floor-scale down only when count cost alone exceeds the budget. `target` does not affect cost at v1 (a self-cost *discount* is renderer-era tuning). Solo base-use stays pinned at 2.0 and is never budget-filled.

## Gadget schema (the output shape)

```
Effect:
  kind: EffectKind
  target: Target                # REQUIRED — who it applies to
  amount: float  (>= 0)
  duration: float
  radius: float
  count: int
  note: str

Stage:
  trigger: Trigger
  effects: list[Effect]
  note: str

GadgetDraft (model-facing):     name, description, logic, stages
ResolvedGadget (code-assembled): draft + delivery, tier, category, harmless, color, params
```

Params-by-delivery-family tables are unchanged from v0 (`resolver/items.py:params_for`).

## Ownership line — model vs code

- **Model owns:** meaning, name, `logic`, composition — which effects, sequence, triggers, targets, the interpretation of *these specific items*.
- **Code owns:** `delivery` (locked from item), `color`, tier/budget and all weights, caps/floors, legality repair, `harmless` and `category` (re-derived from (kind, target)), the ~10-15% over-budget cap. Model proposes; code disposes.

## v1 open questions

1. `LURE@SELF` (a taunt) stays legal on non-SELF chassis — maximally permissive where no invariant is at stake; revisit on live abuse.
2. Weight *values* are placeholders; play-tuned renderer-era, `TIER_BUDGET`-family knobs.
3. v0's open questions 1/3/4 (melee params, DASH/LAUNCH overlap, slice scope) carry forward unchanged.
