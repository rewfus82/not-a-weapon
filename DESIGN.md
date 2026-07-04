# This Is Not A Weapon — Design & Direction

> The canonical statement of what this game *is*. If a decision conflicts with this
> doc, either the decision is wrong or this doc needs an explicit, dated update.

> **MAJOR REVISION — 2026-07-03.** The vision was refined and sharpened. Key changes
> from prior versions of this doc: (1) the game is now framed as a **real zombie-survival
> shooter** whose weapons are genuinely useful — the absurd junk-combining is a *glitch
> layer* the player unlocks by "waking up," **not** the only path to a usable item.
> (2) Perspective is now **isometric** (top-down is retired). (3) The loop is a
> **day/night cycle with stealth/detection**, not zombie waves. (4) Crafting is split:
> **limited field crafting** (reload, obvious add-ons) vs **full AI building only at
> workbenches**. (5) A concrete **item taxonomy** (real guns, ammo, thrown, melee,
> add-ons, junk) and a **lucidity ladder** that ties story → mechanic. Art/assets are
> a deliberately deferred conversation.

> **MAJOR REVISION — 2026-07-04. Open-world pivot.** The endpoint expanded from a
> run-based roguelite to an **open-world survival game** — Project Zomboid scale: a
> county with a large town and a couple of hamlets — **starting with a single
> procedurally-generated town.** The world is now a **code grid** (cells →
> grass/road/sidewalk/wall/floor/door/cornfield; `_gen_town()` in `main.gd`) with real
> collision, drawn as graybox tiles, **reusing every proven system** — this is the real
> scalable world layer (a county is just a bigger grid + streaming). **Phases 0–2 are
> DONE; Phase 3 (the world) is in progress** (procgen town + collision landed; interiors,
> zombie-wall-collision, entity-scaling next). New dev workflow: a **capture harness**
> (`tools/capture.ps1`) screenshots a frame + captures the console so the agent can
> self-verify Godot changes instead of relying only on F5s. **The isometric decision
> (§8) is REOPENED** — the top-down grid is proving a cheap, good fit for an open world;
> iso for a county is a large art commitment we'd want to justify. Scope reality: this is
> a much bigger, longer build than the roguelite — eyes open.

---

## 1. What this game is (one paragraph)

An **open-world, atmospheric zombie-survival game** set in the decaying rural American
Midwest — you explore a town (growing toward a whole county) and try to survive. On the
surface it plays straight: you have real guns, ammo, melee, and thrown weapons, and you
survive a **day/night cycle** in a dark, lived-in world where light and sound draw the
horde. (Perspective is currently top-down; iso is reopened — see §8.) Underneath, the
world is a **simulation** and you don't know it. As you survive, you slowly **wake up**
(the *lucidity* progression), and the simulation's rules start to bend — first you notice
any bullet fits any gun, then you can jam junk into a gun and it fires, then you can
bolt weird objects onto weapons for glitched effects, and finally you can build weapons,
tools, traps, and armor out of almost anything. The title is the twist: everything
becomes a weapon once you realize none of it is real.

## 2. Story & premise

You're a survivor of the fall — you lived the collapse of society and the rise of the
horde, and you're grinding through the first weeks in the Midwest wasteland. You do
**not** know you are inside a simulation. The game *is* a competent survival-horror
shooter for a while.

The awakening is discovered through desperation and glitches, in this order — this
progression is the emotional arc **and** the mechanical unlock ladder:

1. **"All bullets fit all guns."** Out of the right ammo, you try the wrong ammo — and
   it works. The first crack: the sim's rules are looser than reality's.
2. **"I can reload with… anything?"** Truly desperate, you shove non-ammo junk into a
   gun — and it fires, with strange effects. Junk-as-ammo.
3. **"Parts change the gun."** A weapon breaks; you try to repair/augment it with
   something absurd (the canonical example: a **mop**), and the sim glitches — the
   weapon now carries an effect derived from the object.
4. **"I can build anything from anything."** Full freeform combining — weapons, tools,
   traps, armor — assembled from seemingly useless things.

Each step is a higher **lucidity** rating. The grim world is the simulation; the glitch
visuals are **reality cracking through** as you grow lucid (kept subtle so it doesn't
overpower the horror tone).

## 3. The lucidity ladder — story = unlock ladder

Lucidity (a.k.a. "awakening", 0 → high) gates **what crafting is possible**. It is the
progression system. It does **not** unlock recipes; it unlocks *how far the rules bend*.

| Lucidity | The realization | What it unlocks mechanically |
|---|---|---|
| **Asleep** | It's a normal apocalypse | Straight shooter: guns take their "correct" ammo, melee/thrown work as expected |
| **Tier 1** | Any bullet fits any gun | **Universal ammo** — any ammo type loads any gun |
| **Tier 2** | Reload with anything | **Junk-as-ammo** — non-ammo junk becomes rounds, with quirks |
| **Tier 3** | Parts change weapons | **Augment/add-ons** — attach objects to weapons for glitched effects |
| **Tier 4** | Build anything from anything | **Freeform combine** — full AI-driven building of weapons/tools/traps/armor |

Design rule: **items are useful WITHOUT modification.** A gun shoots, a bat hits, a
flare lights. Combining is the *bonus glitch layer*, never the price of admission to a
working item. (This is the big correction from earlier drafts, where "most combos are
not weapons" made base items feel useless.)

## 4. Crafting model — where each tier happens

Crafting ability is split by **context**, gated by lucidity:

- **Field crafting (anywhere, non-debug):** limited, fast, no AI calls.
  - Reload a gun (matching ammo → universal ammo → junk-as-ammo, as lucidity rises).
  - Attach **obvious** add-ons (scope, silencer, extended mag, bump stock).
  - This is the moment-to-moment survival crafting. Cheap, deterministic.
- **Workbench crafting (at workbenches scattered on the map):** the deep layer.
  - Full **freeform building** — the AI combine brain (Tier 4). Weapons, tools, traps,
    armor from arbitrary junk. This is where the expensive/creative resolution lives.
  - Workbenches are places you seek out — a survival-crafting beat, and a natural home
    for the pause-screen build UI.
- **Debug mode:** everything unlocked, all items stocked, for testing.

Non-negotiable: **never a hard AI dependency at ship** — field crafting and a
deterministic fallback keep the game fully playable with no key / no server.

## 5. Item taxonomy (starter list — not comprehensive)

Items must be **useful unmodified**. The starting kit is a **loaded handgun + a handful
of bullets**; the first thing you scavenge for is more bullets.

**Projectile weapons:** handgun (start), SMG, shotgun, automatic rifle, crossbow,
compound bow, sniper rifle, flamethrower, grenade launcher, sentry turret, rocket
launcher, railgun, beam-style weapon, energy weapon.

**Ammo:** bullets (the universal conceit — first glitch), shells, arrows, bolts, gas
canisters, grenades, rockets, energy cells.

**Thrown weapons/tools:** grenades, flares (light), smoke grenades, flashbangs,
boomerangs, yo-yos, throwing stars, molotov cocktails.

**Melee weapons:** bats, chainsaws, swords, brass knuckles, lightsaber, knives,
nunchucks.

**Add-ons (legit weapon mods):** scopes, bump stocks, extended magazines, silencers, …

**Junk (glitch fuel):** mundane objects that — once lucid — augment weapons or become
craft ingredients. Useful mainly via the glitch layer, by design. **Seed set of 32
below** (a *starting* set, not a ceiling — sized for *coverage* of the engine's ~14
effect primitives + light/sound + flight modifiers, at ≥2 intuitive sources each, spread
across 8 Midwest scavenge clusters). Adding more later is just a data row; only a
brand-new *primitive* touches the capability contract. Each item is annotated with its
real-world read → what the AI can build with it.

*🔧 Garage & Truck* — Motor Oil (slick, flammable → slow/oil-slick, fire) · Jerry Can of
Gasoline (accelerant → fire, explode) · Car Battery (12V + acid → electric/chain,
caustic) · Jumper Cables (conducts → chain-lightning, reach)

*🌾 Barn & Field* — Bag of Fertilizer (ammonium nitrate → big explode) · Pitchfork (long
tines → pierce, reach, damage) · Barbed Wire (snags → snare, area damage) · Hornet Nest
(furious swarm → spawn/homing swarm)

*🍳 Kitchen & House* — Cast Iron Skillet (heavy, flat → blunt damage, shield/block) ·
Cooking Grease (slippery, flammable → slow, fire) · Drain Cleaner (lye → acid burn,
poison) · Mason Jar (sealed vessel → lobbed container / holds a payload)

*🪚 Shed & Hardware* — Box of Nails (shrapnel → pierce, scatter/spread, damage) · PVC Pipe
(hollow tube → barrel: range/speed + pierce) · Propane Tank (pressurized → explode, cold
vent/freeze) · Garage-Door Spring (stored force → knockback, launch/return, bounce) ·
Sledgehammer (mass → huge blunt damage, knockback)

*🧪 Cleaning & Chemical* — Aerosol Bug Spray (jet + flammable → cone spray, fire, poison) ·
Fire Extinguisher (CO₂ blast → freeze, knockback cone, smoke) · Bleach/Ammonia (toxic
fumes → poison cloud, caustic)

*⛽ Gas Station & Store* — Road Flare (burns bright → fire, light lure/ward) · Glow Sticks
(cold light → light marker, decoy) · Air Horn (piercing noise → sound lure/decoy, stun) ·
Energy Drink (caffeine → speed/buff, self)

*💊 Medicine & Home* — First Aid Kit (patch up → heal, bandage-shield) · Duct Tape (binds
anything → snare, patch/heal, the universal "attach" modifier) · Painkillers (numb →
heal-over-time / pain-ignore buff)

*📦 Odds & Ends* — Horseshoe Magnet (attracts metal → homing, loot-collect) · Shop Vac
(suction → collect/loot vacuum, aura) · Handful of Feathers (floaty → flight modifier:
slower, wider arc, drift) · Chain (heavy links → swing damage, snare, "chain" pun) ·
Brick (dense → thrown/blunt damage, knockback)

*Known thin spot:* spawn/swarm has only one strong source (Hornet Nest) — add a second
later (e.g. a jar of fire ants). Flight-modifier coverage is deliberately rich (feathers,
spring, PVC, magnet, nails, duct tape) because the boomerang delivery-profile blueprint
keys off exactly those.

### Use / delivery archetypes (the delivery model) — locked 2026-07-03

The set of distinct **delivery mechanisms** the engine renders and the AI picks a chassis
from. Two weapons share an archetype if the code path is the same with different numbers.
The **key separation:** an item's *delivery* (how output reaches the world) is distinct
from its *payload* (the effects it carries) — e.g. a rocket is `Projectile + EXPLODE
payload`, not its own archetype. This is why "how it's launched" and "what it does on
arrival" are modeled independently. An item's **standalone (wielded-alone) use ≠ its
combine contribution** — a box of nails thrown = caltrops; combined into a launcher =
spread shot.

**🔫 Ranged** — *Projectile* (discrete shots; spread param = shotgun; **rocket = projectile
+ explode payload + "munition" render flag**: slow visible shot, trail, big boom) ·
*Beam* (hitscan line / continuous — railgun, laser, arc) · *Spray* (close cone stream —
flamethrower, extinguisher, bug spray)

**🎯 Thrown** — *Lob-impact* (detonates/shatters on land — grenade, molotov, mason jar;
**grenade launcher = lob + explode payload**) · *Scatter/caltrops* 🆕 (bursts into a ground
hazard field — nails, glass) · *Pour* 🆕 (liquid puddle: slick/flammable/caustic — oil,
gas, bleach) · *Return* (arcs out and back — boomerang, yo-yo)

**🔨 Melee** — *Swing* (arc — bat, sword, sledgehammer, skillet) · *Thrust* 🆕 (straight jab
with reach — spear, pitchfork, brass knuckles/punch, screwdriver) · *Grind* ⚠️ (hold for
continuous contact damage while moving; **reach varies** — chainsaw long, drill short)

**📦 Placeable** — *Trap/Mine* (proximity trigger — bear trap, landmine) · *Turret*
(auto-fires — sentry) · *Barricade* 🆕 (physical blocker / soaks hits) · *Decoy* (draws
enemies — boombox, raw meat) · *Beacon* 🆕 (placed light/sound; feeds the day-night
attraction system — dropped flare, glow stick, lantern)

**🧍 Self / Utility** — *Use-on-self* (heal/buff — first aid, energy drink, painkillers) ·
*Field/Aura* (passive while held — shop vac vacuum, magnet pull, lantern light)

**🔧 Modifier** — *Inert* (no standalone use; only alters another item in a combine —
feathers, scope, silencer, ext-mag)

**Not delivery archetypes:** **armor & shields are worn** (ARMOR equipment slot, not a
"use"); active blocking is deferred / folded into armor. Legend: 🆕 = new engine behavior
to build, ⚠️ = partial today. New behaviors implied: scatter/caltrops, pour/puddle,
barricade, beacon, thrust-melee, grind-melee, munition render flag.

Open modeling questions for the revamp (see §11): the exact tag/stat vocabulary, whether
the Godot item list mirrors the Python `combine/items.py` "association clouds" or the two
unify, and killing the vestigial `slots`/`affordance` fields that nothing currently reads.

## 6. Gameplay loop — day/night + stealth (NO waves)

Retire the wave system. The clock is a **day/night cycle**.

- **Day:** zombies retreat to darkness/interiors, lethargic, low threat. This is your
  window to scavenge, explore, reach workbenches, and craft.
- **Night:** zombies emerge, stronger, and **actively hunt**. Getting caught out at night
  is the core danger.
- **Attraction:** zombies are drawn to **light and sound** (your flashlight, gunfire,
  a running generator). Stealth is a real option.
- **Detection:** a zombie must be **alerted** to your presence before it chases. Break
  line-of-contact for a few seconds and it **disengages** and wanders off.

The darkness system already built (ambient/flashlight/fog driven by one value) becomes
the day/night clock, instead of tracking wave progress.

## 7. The world — open-world town → county (grid architecture)

**Endpoint:** an explorable open world — a Midwest **county** with a large town and a
couple of hamlets, rural connective tissue, cornfields. **We start with one town** and
grow outward; a county is the same architecture at larger scale.

**Architecture (built, graybox):** the world is a **code grid** — a 2-D array of cell
types (grass / road / sidewalk / wall / floor / door / cornfield), **procedurally
generated** into a town (`_gen_town()`): a cornfield ring, a street grid dividing blocks,
buildings stamped into clear lots (wall perimeter + floor + a doorway), scavenge sites
scattered onto buildings. Drawn as graybox tiles, **view-culled** around the camera so it
stays cheap as the world grows. Real **collision** (walls are solid; player slides along
them). This deliberately avoids Godot's TileSet/scene machinery for now — a grid + a
generator + draw + collision in code, which is testable via the capture harness and
scales to a county (bigger grid + streaming).

**Landed:** grid world, procgen town, roads/blocks/buildings/doors, cornfield edges,
player wall collision, camera-centered draw culling.

**Still to build (Phase 3):**
- **Zombies respect walls — DONE.** Per-axis collision: they stack on the outer walls
  and only breach through the door (verified). Blocked chasers now wall-follow around a
  building instead of dead-sticking; full nav/pathing (A*) deferred to entity-scaling.
- **Interiors** — enter through doors (DONE), walk-in scavenge loot (DONE), and **roof-fade
  reveal DONE**: buildings are opaque roofed blocks that hide the interior + any horde
  inside; the roof fades open for the building you're standing in (verified). Remaining:
  loot *containers* + workbenches placed inside (vs auto-loot / TAB-anywhere today).
- **Entity scaling** — simulate only what's near the player (active radius) + pooling, so
  the town can grow toward a county without dying.
- **Density & texture** — DONE: denser building lattice + dirt/weed ground patches, and
  item icons via alias map, doors that face the nearest road, and solid trees (treeline
  by the corn, sparse in town; block movement + shots). Remaining: more building types
  and the other props (cars, fences, poles).
- **Workbench placement** in the world (the Tier-4 build is currently anywhere via TAB).

## 8. Presentation

- **Isometric viewpoint — REOPENED (2026-07-04).** We're currently building **top-down**
  on the grid world, and it's proving a cheap, readable fit for an open world. Iso for a
  county is a heavy art commitment (iso tilesets + 8-directional characters). Decide iso
  vs. top-down as part of the art talk; don't assume iso anymore.
- **Not** the current cartoony/chunky player & zombie look — art direction is a
  deferred conversation, but the target is grittier/grounded.
- **Weapons/tools render in the player's hands** — you can see what you're wielding.
- **Full UI/HUD revamp** — the current graybox HUD is throwaway.
- Art & assets are a **separate, later conversation** — do not block systems work on them.

## 9. Setting — rural / small-town Midwest America (preserved)

Deliberately **NOT** generic zombie apocalypse. Specific, eerie, lived-in Americana decay:
grain elevators, Casey's-style gas stations with flickering signs, trailer parks, farm
supply stores, small-town main streets, abandoned big-box husks, **cornfields that hide
hordes**, **tornado sirens** as the night/alert motif, rusted pickups, county
fairgrounds. This supplies the props, the dread, and the audio identity.

## 10. The combine brain (preserved, re-scoped)

The combine "brain" is an **engine-agnostic, fully-tested Python package** (`combine/`),
so it survives any engine migration; the game engine is a **thin renderer** that must
faithfully show what the brain builds (distinct deliveries, staged effects). Re-scoped:
the brain now powers **Tier-4 workbench building**, not every interaction. Essentials
still hold — slot grid (delivery/damage/utility/modifier) as declared intent; output =
chassis + ordered stages in a fixed **capability-contract** vocabulary the engine can
render; LLM resolver primary + deterministic fallback; `COMBINE_MODEL` env (Haiku dev /
Sonnet ceiling). See the `combine/` package and memory notes.

**Capability-contract — delivery params (blueprint DONE):** the contract now models both a
weapon's *payload* (effects) **and** its *delivery behavior* via a per-gadget `params`
dict. Boomerang is the fully-worked example (arc/range/return-speed — read by the engine,
set by every resolver, emittable + clamped by the AI, bent by modifiers). The pattern
templates out to other deliveries (trap arm-time, turret fire-rate) by adding keys.

## 11. Open questions / to be fleshed out

- World: interior reveal model **resolved — roof-fade** (opaque roofs, fade open on enter);
  streaming for county scale still open — see §7.
- Iso vs top-down (§8) — reopened; decide in the art talk.
- How lucidity is *earned* (survival time? story beats? specific glitch triggers?). Currently
  debug-only (`[` / `]`); no in-game earn mechanic yet.
- Armor: slot system exists (hand + armor); armor items/effects TBD.
- *(Resolved: item model unified — Godot `item_db.gd` tags + Python `combine/items.py`
  association clouds kept additively in sync; vestigial `slots`/`affordance` dropped.)*

## 11b. Backlog — deferred tweaks (not blocking; revisit when convenient)

- **Ammo → shot damage/effects tuning pass.** Loaded ammo "works but the effects/damage
  is off" (noted 2026-07-03). `Resolver.ammo_profile()` was built for the old junk-only
  model and maps awkwardly onto "this is the actual round the gun fires now": light junk
  (feathers) → `dmg_mult 0` = zero damage; base gun damage × profile can read weak/strong;
  loaded ammo's effect (pierce/explode) should read clearly. Target: bullets punchy, arrows
  pierce, rockets boom, junk weird-but-not-zero. Also decide what cross-loading ammo into an
  *improvised* weapon (caltrops/puddle thrower) should do.

## 12. Roadmap / phased plan  (status: 2026-07-04)

Systems first; art/iso is its own later phase so it never blocks gameplay.

- **Phase 0 — Item taxonomy. ✅ DONE.** Hybrid item model (category + declared archetype +
  tags + associations), 32 junk + 7 ammo, delivery-archetype taxonomy locked.
- **Phase 1 — Crafting + lucidity T1–4. ✅ DONE.** Reload ladder (universal ammo →
  junk-as-ammo), primitive build menu + attachment slots, lucidity-gated bench, AI BUILD
  synced to the new items, boomerang delivery-profile blueprint.
- **Phase 2 — Day/night + stealth loop. ✅ DONE.** Day/night clock, flashlight toggle,
  waves retired, continuous night-scaled spawning, zombie detection AI
  (wander/alert/chase, light+sound, disengage), day-lethargy/night-hunting.
- **Phase 3 — The world (open-world town → county). 🔨 IN PROGRESS.** Landed: grid world +
  procgen town + collision + edge-culling. Left: zombies-respect-walls + pathing,
  interiors, entity scaling, density/props, workbench placement. See §7.
- **Phase 4 — Presentation overhaul. ⬜ NOT STARTED.** Art direction, in-hand weapons, full
  UI/HUD revamp, and the **iso-vs-top-down decision** (§8). Gated behind the art talk.

The endpoint (open-world survival) makes Phase 3 the long pole — it's the "build the real
game" phase, and it's content/world-authoring heavy (procedural generation is the lever).

## 13. Current state (2026-07-04)

Playable top-down graybox, Phases 0–2 done + Phase 3 underway. **Combine:** hybrid item
model, primitive build menu (BUILD/ATTACH/LOAD) + attachment slots, workbench AI (Tier-4)
wired to the Python brain, lucidity ladder gating field crafting + the bench, boomerang
delivery-profile blueprint (per-delivery `params`). **Loop:** day/night clock + flashlight
toggle, no waves, continuous night-scaled spawning, zombie detection AI (wander/alert/
chase, drawn to light + gunfire, disengage on lost contact). **World:** procgen town on a
code grid — roads/blocks/buildings/doors/cornfields, player wall collision, camera-culled
draw. **Combat:** RUINER juice, caltrops/puddle ground hazards, real 2D lighting/fog.
**Python `combine/` brain** tested (pytest 73/73). **Dev loop:** `tools/capture.ps1`
gives the agent eyes (screenshot + console). Everything is graybox-skinned — art is Phase 4.

## 14. Guiding principles

- **Items are useful unmodified.** Combining is the glitch bonus, not the cost of a working item.
- **Story = mechanic.** The awakening/lucidity ladder *is* the crafting-unlock ladder.
- **Readability beats realism.** If you can't tell what a thing is at a glance in the dark, it's wrong.
- **The dark is the aesthetic.** Show little, imply much; light what matters.
- **Systems over assets.** Don't block gameplay systems on art; art is a later phase.
- **The brain is portable.** Keep combine logic engine-agnostic; the renderer is swappable.
- **Never a hard AI dependency at ship.** Field crafting + deterministic fallback keep it fun keyless.
