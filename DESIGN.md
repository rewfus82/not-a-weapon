# This Is Not A Weapon — Design & Direction

> The canonical statement of what this game *is*. If a decision conflicts with this
> doc, either the decision is wrong or this doc needs an explicit, dated update.

## Elevator pitch

A **dark, high-angle, atmospheric top-down survival-shooter** set in the decaying
rural American Midwest. You scavenge junk through a shadow-drenched, lived-in world
lit mostly by your flashlight, and **combine that junk into weapons, tools, and
gadgets** — most combinations are *not* weapons, and that's the point. Calm, tense
exploration is punctuated by frantic swarms. Underneath it all: you are an entity
slowly realizing this grim world is a **simulation**, and as you wake up, its rules
loosen and reality glitches.

The combine mechanic is the identity. Everything else exists to make combining junk
feel meaningful, legible, and dangerous.

## Setting — rural / small-town Midwest America

Deliberately **NOT** generic zombie apocalypse. Specific, eerie, lived-in Americana
decay:

- Grain elevators looming in the dark
- Casey's-style gas stations, flickering signs
- Trailer parks, farm supply stores, small-town main streets
- Abandoned Walmarts / big-box husks
- **Cornfields that hide hordes** (they're fine… until the stalks start moving)
- **Tornado sirens** as the swarm-warning motif
- Rusted pickup trucks, county fairgrounds

This setting supplies the props (world detail), the dread, and the audio identity.

## Aesthetic & feel — the reference board

Each axis is anchored to a game that nails it:

| Axis | Reference | What we take |
|---|---|---|
| **Camera / movement** | Project Zomboid | High angle, grounded, realistic scale, excellent environmental readability |
| **Lighting / atmosphere** | Darkwood | Line-of-sight **vision & darkness as a mechanic**; the flashlight is precious; fog; you only see what you light; oppressive dread |
| **World detail** | The Ascent | Dense clutter, lots of props, dynamic lighting, rich particles — everything feels *lived-in* |
| **Combat feel** | RUINER | Snappy movement, chunky impacts, sparks / casings / gore, loud visual feedback |
| **Enemy density** | Brotato | Hundreds of enemies, constant pressure, **simple readable silhouettes — readability always beats realism** |
| **Overall pacing** | Helldivers | Calm exploration punctuated by frantic swarms; explosions are genuinely dangerous |

The tension between "grounded/detailed" and "simple/readable" resolves as: **a dense,
grounded, dark WORLD + simple readable ENEMY silhouettes, with LIGHTING telling you
what matters.** Lit = important. The rest is dread in shadow.

## The key unlock — why this is achievable

This direction **dissolves the art-breadth trap** (a junk-combine game needs hundreds
of item concepts; we can't hand-draw all of it). The richness comes from **lighting +
darkness + density + particles + juice** — systems and shaders, which are buildable —
**not** bespoke per-asset art:

- Enemies are simple silhouettes (Brotato) → no detailed enemy art needed.
- Most of the world is hidden in shadow (Darkwood) → less has to look good.
- Impact comes from sparks/feedback (RUINER) → juice, not art.
- Environmental richness comes from prop density + dynamic light (The Ascent).

Free CC0/CC-BY assets (Kenney sprites/tiles, game-icons item icons) work fine under
dramatic lighting. AI-generated art is a *later* force-multiplier, never a dependency.

## Perspective — top-down, NOT true isometric

We build the **feel** of both PZ and Darkwood with a **steep, atmospheric top-down**
view. True isometric (Project Zomboid's projection) is explicitly **rejected** for now:
it needs isometric tiles *and* 8-directional animated iso characters/zombies, which
re-opens the art-breadth trap hard. Darkwood itself is top-down and achieves all the
dread without iso. Camera height + lighting sell the "grounded" weight; readability
wins. (Revisit only if we ever commit to an iso-art pipeline.)

## Narrative / tone

You're an unaware entity inside a **simulated reality** (matrix-like). The core verb —
combining junk to "see what happens" — feels like exploiting a glitch. As your grasp
on reality shatters, the simulation's rules loosen. The grim Midwest world **is** the
simulation; the **glitch effects are reality cracking through** as you grow lucid
(kept subtle so it doesn't fight the survival-horror tone). This ties art → narrative →
mechanic: the **lucidity/awakening meter** drives both what you can build (rules
loosening) and how much reality glitches.

## Core loop & mechanics

- **Scavenge** junk from the dark, lived-in world (calm, tense, flashlight-limited).
- **Combine** junk at a workbench into gadgets (weapons / tools / control / duds).
- **Survive** frantic swarms (Helldivers pacing; cornfields/darkness hide them).
- Escalate; the simulation loosens; combines get more absurd; you die and restart.

Progression is **lucidity** (waking up) — it unlocks how much you can bend the rules
and how absurd/rewarding off-nature combinations become; NOT unlocking recipes.

## The combine system — the identity (already built)

The "brain" is an **engine-agnostic, fully-tested Python package** (`combine/`), so it
survives any engine migration. See `combine/` and the memory notes. Essentials:

- **Slot grid** = declared intent: `delivery` (the chassis/how it's used, required),
  `damage`, `utility` (non-damage behavior), `modifier` (a twist). The slot overrides
  an item's default reading.
- **Association clouds + reveal tiers**: items are vivid associations the player *sees*
  progressively as they wake up; the resolver only ever sees what the player can see.
- **Output = chassis + ordered stages + free flavor**, spelled in a fixed vocabulary of
  engine-renderable primitives (the capability contract). Finite letters, infinite words.
- **LLM resolver (primary) + deterministic fallback**, same schema. All slots always
  open; the lucidity ramp changes how much a placement can be *bent*, not which roles
  exist. Model: `COMBINE_MODEL` env (Haiku default for dev/cost; Sonnet for the ceiling
  / a future shipped catalog).
- **Not-a-weapon is enforced**: empty damage slot ⇒ a tool, not a weapon.

The engine (Godot for now) is a **thin renderer** that must faithfully show what the
brain builds (distinct deliveries, staged effects) — this fidelity is a top priority.

## Build / craft UX

A **dedicated build screen that PAUSES the game**: big labeled slots you **drag items
into** (delivery / damage / utility / modifier), a result/preview, and a clear read of
what you made and *why*. Later, gate it behind **finding or building a workbench**
(survival-crafting). Interacting with the combine mechanic must feel *good* — it's the
core verb.

## Roadmap / priorities

1. **Atmosphere + combat-feel CORE (in progress):** darkness / flashlight vision,
   dynamic lighting, chunky RUINER-style particle combat. This single pass fixes the
   "boring map," most of the "juice," and the "combat feels weak" problems at once.
2. **Then** revisit the issue list below.
3. Later: density (hundreds of enemies), day/night or scavenge→swarm pacing, the
   dedicated build screen, real Midwest environment/props, audio (tornado sirens!),
   and the lucidity ramp surfacing in-game.

## Known issues to address (Ryan's list, 2026-07-02)

1. The map is a boring green square with labeled boxes — needs a dark, dense, lived-in
   Midwest space (lighting does most of the work).
2. The loop is boring; **builds take too long** so you flee instead of fight — retune pacing.
3. Effects suck — **everything shoots balls**; deliveries/effects aren't visually distinct.
4. The AI builder must be **reflected accurately in-game** — e.g., a boomerang should
   arc out and **return** by default; distinct deliveries must render distinctly.
5. **Over-homing bug**: many items heat-seek when they shouldn't (prime suspect: spawned
   sub-projectiles hardcoded to home via `or sub` in `main.gd:_make_proj`).
6. Juice sucks — go **fully off graybox** (textured particles, real FX).
7. Bench UX is bad; also a **pause bug** (re-pausing re-inserts the last bench item).

## Guiding principles

- **Readability beats realism.** If you can't tell what a thing is at a glance in the
  dark, it's wrong.
- **The dark is the aesthetic.** Show little, imply much; light what matters.
- **Systems over assets.** Lighting, particles, density, and juice carry the look.
- **The combine is the game.** Every system serves making junk-combining meaningful,
  legible, and dangerous. Most combos are not weapons — protect that.
- **The brain is portable.** Keep combine logic engine-agnostic; the renderer is swappable.
- **Never a hard AI dependency at ship.** BYOK/offline-catalog; the game must be fun keyless.
