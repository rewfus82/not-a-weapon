# Design — Item Catalog & Behavior-First Weapon Taxonomy

*Date: 2026-07-12. Reimagines the resolver item catalog around **intuitive MacGyvering** and adopts a **behavior-first, three-layer weapon model**. Supersedes Pieces 1–2 (tag taxonomy, catalog) of `2026-07-11-sensible-vs-absurd-routing-design.md`; that doc's Piece 3 (coherence score) and handoff rule still stand and consume this catalog. Also records the extraction/blueprint mechanics settled alongside it, to be applied to `GAME_IDENTITY.md`.*

## The thesis correction

The earlier catalog leaned on verb-less novelty props (rubber duck, garden gnome, silly string, can of anchovies, bag of flour). They are *funny nouns*, not *combinable objects* — a garden gnome has no verb the sim can wield. The reimagining fixes the source of absurdity:

> **Every item carries a clear functional verb. The absurdity lives in *combining* them, not in the items being jokes.**

You could never duct-tape a blender, a banana, a fire extinguisher, and a car battery into a weapon in reality — you'd get a smashed banana and a sad blender. But the *simulation* composes their verbs: extinguisher **cone-blasts**, blender **blends-and-spits**, banana **is gooey goo**, battery **electrifies** → the **Bananarama Ultra 5000**, a cone of electrified sticky banana goo. The impossibility of the physical assembly is the whole joke; the sim is what makes the verbs cohere.

This keeps the two-quadrant design (`2026-07-11` routing doc): grounded combos resolve deterministically; the sim-magic frontier (impossible results at high tiers) is the LLM's quadrant. The item is always a sensible object; **how far reality bends is a function of tier/risk** (§7).

## The three-layer behavior model

A weapon is composed on three orthogonal layers. This is the game-design lens: organize by **how the weapon behaves in play**, not by the real-world mechanism that launches it (a flamethrower, an acid-sprayer, and a fire-hose are one *behavior* — continuous stream — in three costumes; you balance the behavior once).

```
weapon = BASE DELIVERY behaviour  ×  BEHAVIOURAL OVERLAY(s)  ×  EFFECT / damage type
```

- **Base delivery behaviour** — how it moves through space. Maps to the contract `Delivery` enum: Ballistic (`HITSCAN`/fast `PROJECTILE`), Spread (`SPRAY` cone), Stream (`SPRAY`/`BEAM` sustained), Arc (`LOBBED`), Thrown (`THROWN`), Beam (`BEAM`), Melee (`SWING`/`THRUST`/`SLAM`/`WHIP`/`GUARD`), Placed (`PLACED`), Self/mobility (`SELF`/`DASH`).
- **Behavioural overlay** — how it behaves *on top of* the base, the way real ammo types layer on a gun (AP / explosive / homing). In-contract today via effect kinds: **Explosive** (`EXPLODE`), **Chain** (`CHAIN`), **Piercing** (`PIERCE`). **Parked** (not in the contract yet — a deliberate future capability decision, never model-reachable): **Seeking** (homing) and **Physics** (bounce / drill / ricochet / boomerang).
- **Effect / damage type** — what it does on contact. Maps to `EffectKind`: Burn, Corrode(as `BURN`/`DAMAGE`), Freeze, Shock(as `CHAIN`/`DAMAGE`), Snare, plus base `DAMAGE`/`KNOCKBACK`/`STAGGER`/etc. "Toxic gas" is an *emergent* effect (chlorine + ammonia) the composer derives, not an item property.

**Why the split matters mechanically:** the same three items rerolled at a higher tier can pick up an overlay they lacked at low tier — Bananarama at COMMON is blender-stream + banana-snare; at LEGENDARY it also gains the car-battery **chain** overlay and a seeking arc. "Reality bends more the deeper you go" becomes a tunable knob (which overlays unlock at which tier), not just flavor.

## How items feed the layers

Each item declares the **role(s)** it can play; the resolver slots it into the matching layer. Items may span layers (that overlap is the composability).

| Item role | Feeds which layer | Examples |
|---|---|---|
| **Mechanism** | base delivery behaviour | blender→stream, potato cannon→arc, nail gun→ballistic, crowbar→melee |
| **Modifier / energizer** | behavioural overlay (+ effect transform) | car battery→chain+shock, propane tank→explosive, thermite→burn |
| **Substance** | effect / damage type (needs a delivery to come out) | gasoline→burn, chlorine→corrode, wet cement→snare |

## The item model (schema)

Extend `resolver/items.py` `Item` with the fields the three layers need:

```
Item:
  name: str
  roles: set[Role]              # {MECHANISM, MODIFIER, SUBSTANCE} — which layers it can feed
  verb: str                    # the one-word functional verb (flavor + composer hint)
  tags: list[str]              # affinity tags (interaction-bearing; see taxonomy)
  delivery: Delivery | None    # base delivery FORM, only for MECHANISM items
  caliber: str | None          # firearms + real ammo only (match gates coherence)
  flags: set[Flag]             # {WIELDABLE, FIREARM, AMMUNITION, LOADABLE, BASE_WEAPON}
```

- `WIELDABLE` — usable raw as a weapon (guns, melee).
- `BASE_WEAPON` — the only junk that yields a **materials-free base-item blueprint**, retrieved at the armory (see mechanics below). Firearms; the "which melee count" line is a parked question.
- `FIREARM` + `caliber` — a gun; needs matching `AMMUNITION` caliber for high coherence.
- `AMMUNITION` (caliber-matched) vs `LOADABLE` (small+numerous improvised ammo) — the two ammo classes; a gun's coherence axis runs *matching caliber (sensible)* → *loadable junk (absurd)*.

## Reconciled tag taxonomy

The reimagining changed which tags have carriers. Dropped (no carrier survives): `buoyant`, `decoy`, `swarm` (their items — rubber duck, gnome, crickets, anchovies — were cut). Added: `container` (holds a payload → Molotov/grenade chassis). Result is **~24 interaction-bearing tags** plus the weapon-system flags/`caliber` field above:

- **Physical / impact (6):** `sharp, blunt, heavy, long-reach, springy, brittle`
- **Substance / state (9):** `flammable, ignition, corrosive, cold, liquid, slippery, sticky, pressurized-gas, powder`
- **Energy / field (4):** `electrical, wind, loud, light-source`
- **Structural / dispersal (2):** `container, scatter`
- **Self / support (3):** `restorative, stimulant, protective`

Principle unchanged from Fork 1: **every tag is interaction-bearing, not flavor** — each drives an effect or param via the known-interaction table. `explode` is expressed as the Explosive *overlay*, driven by items tagged for it (propane tank, fertilizer), not a standalone tag.

**Parked contract question:** `Seeking`/`Physics` overlays and a `PULL`/`COLLECT` effect have no contract token; adding them is a deliberate vocabulary event (economics doc §7), not a casual widening.

## The catalog — 53 items, cut by behaviour

### Layer 1 — Base delivery behaviour (Mechanism)

**Ballistic** *(fast, flat)* — `.22 pistol` (HITSCAN, firearm·.22), `9mm pistol` (HITSCAN, firearm·9mm), `revolver` (HITSCAN, firearm·.357), `M16 rifle` (HITSCAN, firearm·5.56), `.30-06 hunting rifle` (HITSCAN, firearm·.30-06), `nail gun` (PROJECTILE; also piercing)
**Spread** *(cone of many)* — `pump shotgun` (SPRAY, firearm·12ga)
**Stream** *(continuous cone/jet)* — `fire extinguisher` (SPRAY), `pressure washer` (BEAM), `blender` (SPRAY, spit), `leaf blower` (SPRAY/DASH), `garden hose` (SPRAY)
**Arc** *(lobbed, indirect)* — `potato cannon` (LOBBED), `roman candle` (LOBBED)
**Thrown** *(single-arc object)* — `glass bottle` (THROWN, container), `cinder block` (THROWN)
**Beam** *(instant sustained line)* — `salvaged laser cutter` (BEAM)
**Melee** *(contact)* — `crowbar` (SWING), `sledgehammer` (SLAM), `fire axe` (SWING), `machete` (SWING), `screwdriver` (THRUST), `baseball bat` (SWING), `power drill` (THRUST, bore), `angle grinder` (SWING), `chainsaw` (SWING), `weed whacker` (WHIP), `riot shield` (GUARD)
**Placed** — `bear trap` (PLACED)
**Self / mobility** — `leaf blower` (DASH), `adrenaline shot` (SELF), `first-aid kit` (SELF)

### Layer 2 — Behavioural overlays (Modifier)

**Explosive** — `propane tank`, `fertilizer (AN)`, `roman candle`
**Chain** — `car battery`, `jumper cables`, `defibrillator`
**Piercing** — sharp munitions (`nails`, AP rounds)
**Parked** — Seeking, Physics (bounce/drill/ricochet) — items ready (`power drill`→drill, a superball core→bounce) but held pending the contract decision.

### Layer 3 — Effect / damage type (Substance)

**Burn** — `gasoline (jerry can)`, `motor oil`, `thermite`, `road flare`, `hairspray`
**Corrode** — `pool chlorine`, `ammonia cleaner`, `bleach`
**Freeze** — `liquid nitrogen`, `dry ice`, `fire extinguisher` (CO₂)
**Shock** — `car battery`, `defibrillator`, `taser`
**Snare / immobilize** — `wet cement`, `expanding foam`, `overripe produce (banana)`
**Toxic gas** *(emergent)* — chlorine + ammonia

### Feeders

**Ammo — real** *(load ballistic/spread/arc; AMMUNITION·caliber)* — `.22 rounds`, `12-gauge shells`, `5.56 rounds`, `.30-06 rounds`
**Ammo — improvised** *(LOADABLE, small+numerous)* — `box of nails/screws` (scatter, sharp), `ball bearings` (scatter, heavy), `marbles` (scatter, slippery), `bag of gravel` (scatter)

*(Delivery-form coverage: every `Delivery` enum token has ≥1 carrier. Every tag has ≥1 carrier. Both quadrants — grounded and sim-magic — are exercised.)*

## Game-mechanics decisions (apply to GAME_IDENTITY as §5/§11/§124–131 refinements)

Settled in the same conversation; recorded here so they aren't lost, to be written into the canon doc as **intentional, additive refinements** (not a rewrite):

1. **Guns are junk** — uncrafted base items like everything else, but `WIELDABLE` (usable raw) and valid crafting inputs. They anchor the *coherent* end of the routing axis (real gun + matching ammo → C≈1 → deterministic, reliable).
2. **Base-weapon blueprints spawn materials-free, but are gated.** A base-weapon blueprint requires reaching an in-run **armory construct** (the Matrix "Guns. Lots of guns." rack) — exposed travel, no free spawn at the safe opening — and costs a finite **loadout slot**. This resolves the §5 collision: you carry *knowledge of a location + schematic*, not power; the M16-vs-.22 base gap becomes *earned* (slot cost + risky detour), not free.
3. **Two blueprint kinds coexist.** *Base-item blueprints* (guns; materials-free, retrieved at the armory, inbound) and canon *combination blueprints* (§131 recipe for a junk combo; still requires finding the parts, learned via deconstruct, outbound).
4. **Deconstruct-to-learn, at a cost.** Crafted items extract as **currency** by default. To bank the **blueprint** instead, take the item to an in-run **deconstruct spot** and *destroy* it — forfeiting both its combat use for the extraction fight *and* its currency. Three-way tension per crafted weapon: **keep firepower / bank currency / learn recipe** — pick one, under fire. Sharpens §124–125.
5. **Loadout copies of an unlosable master.** Loaded blueprints are *copies* of the permanent codex master (which lives outside the sim). Deleting a loaded copy in-run costs nothing permanent — **except** a blueprint *acquired this run and not yet extracted*, which has no outside master and is lost if dropped or if you die (§47). This is what gives the "go in full vs. leave slots open" decision real stakes. Refines §130–131: the *master* is unlosable; the *loaded copy* is a disposable projection.

## Routing integration (from the 2026-07-11 doc; forks resolved)

The coherence score and handoff rule are unchanged and consume this catalog. Recommended resolutions for the three open routing forks (confirm at review):

- **Fork 2 — thresholds:** `C_HIGH = 0.66`, `C_LOW = 0.33`; middle band leans deterministic until `RARE`. Start cheap; let playtest push LLM spend up only where it delights.
- **Fork 4 — coherent high-tiers:** pure deterministic, no LLM polish for v1 (a coherent LEGENDARY is the sensible chain scaled up). Optional polish is a cheap future wave.
- **Fork 5 — sequencing:** richen the deterministic composer (P3) **before** the router; do not ship the stub behind the router. It's the hard dependency and does triple duty (fallback / instant-craft / scaffold filler).

## Open / parked

- **Seeking + Physics overlays** — promote to first-class contract tokens, or leave design-only? (Deliberate vocabulary decision; parked by user.)
- **`PULL`/`COLLECT` effect** — still absent; revisit if a field/gravity mechanic is wanted.
- **Which melee count as `BASE_WEAPON`** (armory-retrievable) vs. found junk — proposed: manufactured weapons only (firearms; maybe knife/machete), so the armory doesn't swallow the catalog and weaken scavenging.

## Phasing (to writing-plans)

- **P1 — Item schema + catalog.** Extend `Item` (roles, verb, delivery, caliber, flags); enter the 53 items. *(TDD: schema, catalog invariants — every item tagged, every delivery form carried, tags from the taxonomy, calibers match between guns and real ammo.)*
- **P2 — Coherence scorer** (from 2026-07-11 Piece 3) over the new tags + known-interaction table. *(TDD: gun+matching-ammo≈1, junk-junk≈0, known pairs wired.)*
- **P3 — Deterministic composer v1** — the three-layer composer: tags/roles → base delivery × overlays × effect, tier-scaled, clamped. Replaces the `fallback.py` stub. *(TDD: coherent build yields the sensible chain; magnitudes fit the tier budget.)*
- **P4 — Router** — `route(build, tier)` per the handoff rule; wire into the harness; report the deterministic/LLM split. *(TDD: the rule table.)*
- **P5 — Integration read** — mixed sensible+absurd build set; confirm grounded→deterministic reads well and absurd→LLM still delights (Bananarama). *(Play-tuned, GAME_IDENTITY §9.)*
