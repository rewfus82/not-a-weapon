# Design — Junk Base Uses: Items Are Objects First, Ingredients Second

*Date: 2026-07-13. Gives every catalog item a **base use** — the solo action it performs the moment you pick it up, before any crafting. Renames containerized substances, swaps one item, adds one, and removes the "must bring a chassis" restriction. Extends `2026-07-12-item-catalog-and-behavior-taxonomy-design.md` (the three-layer model and 24-tag taxonomy stand unchanged). The association clouds (`2026-07-12-association-clouds-design.md`) get a follow-up pass after this lands — renamed and new items need cloud updates; the paused live cloud validation resumes after that.*

## The thesis correction

The catalog modeled items as crafting *ingredients* first and forgot they are usable *objects* first. The taser exposed it: flagged `WIELDABLE` but `delivery=None`, so it literally could not be used on its own. That was systemic, not a one-off — substances had no way out of your hands without a mechanism, and the composer refused any build lacking a delivery chassis.

> **Every item does something the moment you pick it up. That solo action is the item's whole point; crafting combines those base behaviors into something bigger.**

### The governing rule

**An item's solo use = its verb = what it contributes to a craft.** One behavior, expressed three ways. An item cannot do one thing solo and something unrelated in a craft; the solo use honestly telegraphs the ingredient. This doubles as a catalog sanity check: if an item's solo use can't line up with what it adds to a craft, the item is muddled and needs fixing (this is what killed the blender — see below).

**Why it matters:** the base use *teaches crafting*. Zap someone with the taser → you've learned "taser = shock" → you already know a taser makes anything you build with it shock. No manual, no tooltip tree — the game reveals how to craft by letting you use the parts first.

### Named refinements to the rule (settled in brainstorm)

1. **Primary-effect solo, exotic tags via crafting.** A multi-tag item's solo use expresses its verb's *primary* effect; the exotic tags are what crafting unlocks. The baseball bat solo-clobbers (blunt DAMAGE); its `springy` line-drive LAUNCH is a craft contribution. Bonus: solo use against *loose environment objects* still shows the deeper lesson for free (whack a bottle across the room → the bat moves payloads).
2. **The ammo exception.** Items with the `AMMUNITION` flag (the six caliber-matched boxes) have **no base use** — they are honestly inert until a matching firearm feeds them, and that inertness is itself the telegraph. This is the only class exempt from the universal rule. Improvised feeders (`LOADABLE`) are *not* exempt; scattering them is their honest solo action.
3. **The common-knowledge carve-out.** When an item's craft contribution is common cultural knowledge, the solo use doesn't have to re-teach it. The car battery solo is a heavy thing you hurl (blunt DAMAGE) — everyone already knows batteries = electricity, so `electrify` needs no solo demonstration.
4. **Common sense governs throwability.** Containers burst when thrown; a steel propane tank does not. The defibrillator and taser are used, not thrown.

## Decisions locked (with the earlier session)

- **Substances are containerized → everything containerized is throwable.** You don't find a puddle of gasoline; you find a jerrycan. Throwing the container = burst + payload disperses (the Molotov move, no build needed). Items are renamed to show the container.
- **The old "improvise a delivery" idea is dropped entirely.** Throw-the-container covers the "nothing to launch it with" case.
- **Recon-only items stay out of scope** (surveillance is a game system, not a resolver gadget).
- **Concealment is presentation, not a mechanic.** The fire extinguisher cloud and dry ice fog have no `EffectKind` token and get none: the mechanical effect uses existing tokens (FREEZE/SLOW via the `cold` tag), and the fog is renderer visuals only. Concealment-as-mechanic can become a deliberate capability event later if playtests demand it. **No enum widens for this design.**
- **Base-use power sits at the floor.** A base use is always weaker than the cheapest craft using that item; magnitudes are fixed and code-owned, never rolled. Every taser zaps identically for every player, always (invariant 2), and picking things up — the zero-risk act — never competes with crafting (invariant 3).
- **No pre-made mines or traps beyond the placed items below.** Mines are what *crafting* makes (bear trap + gasoline; airhorn + propane + flare). The Placed expansion comes from the composer routing payloads into PLACED chassis, not from a shelf of finished mines — pre-made mines would undercut the junk→weapon thesis.

## The base-use enumeration (all 61 items)

Base effect tokens come from the item's verb/tags via `SINGLE_TAG_EFFECTS` unless marked as a judgment call. All magnitudes are floor-tier (weak); "patch" = a ground area left by a burst.

### Melee (12) — swing/thrust it; delivery already on the item

| Item | Solo action | Base effect |
|---|---|---|
| crowbar | swing | blunt DAMAGE |
| sledgehammer | slam | DAMAGE + heavy KNOCKBACK |
| fire axe | chop | PIERCE |
| machete | slash | PIERCE |
| screwdriver | stab | PIERCE |
| baseball bat | clobber | blunt DAMAGE (LAUNCH stays in-craft; refinement 1's exemplar) |
| power drill | bore | PIERCE |
| angle grinder | grind | PIERCE |
| chainsaw | saw | PIERCE (loud — enemies hear it) |
| weed whacker | whip at reach | DAMAGE, long reach |
| riot shield | block/shove | SHIELD |
| nail gun | fire nails | PIERCE (it's a ranged tool) |

### Guns & ammo (12)

Guns: base use = fire (needs matching ammo); unchanged, already work. Real ammo (six boxes): **no base use** (refinement 2). Improvised feeders are under Placed & scatter below.

### Ranged mechanisms (9)

| Item | Solo action | Base effect |
|---|---|---|
| fire extinguisher | short cold cone-blast | weak FREEZE (via `cold`); fog = visuals only |
| pressure washer | hard water jet | weak KNOCKBACK |
| garden hose | spray water | weak KNOCKBACK; soaks ground (wet-floor synergy is the craft lesson) |
| roman candle | spit burning stars | weak BURN |
| salvaged laser cutter | scorch a line | weak BURN |
| glass bottle | throw → shatters | weak PIERCE (shard burst); empty telegraphs "fill me" |
| cinder block | hurl / drop | blunt DAMAGE, heavy |
| t-shirt cannon | fire → a t-shirt flops out | ~harmless pop (tiny STAGGER at most) |
| **industrial fan** (new; replaces blender) | plant it → steady wind lane | weak KNOCKBACK, continuous |

**The empty-launcher class:** the t-shirt cannon (and formerly the blender) are payload movers whose solo use is comically weak *because the whole item is a delivery mechanism* — firing it empty is the honest telegraph. Real firearms are strict (won't fire without matching caliber); junk launchers are permissive and silly. That split is intentional register.

**Blender → industrial fan.** The blender failed the governing rule ("run it open at arm's length" is not an honest solo use — the rule working as a sanity check). The industrial fan replaces it: everyone knows what a fan does on sight. Delivery **PLACED** (not SPRAY): set down, it's an area-denial emitter — solo a wind lane (weak KNOCKBACK, continuous), in-craft a *dispersal emitter* that feeds its payload into the airstream (fan + dry ice = fog corridor; fan + pool chlorine = gas lane; fan + gravel = stinging grit blast). Distinct from the leaf blower (mobile, rideable recoil) and the t-shirt cannon (single lob). Tags `wind`, `electrical`; verb `blow`; roles `{MECHANISM}`.

### Placed & scatter (6)

| Item | Solo action | Base effect |
|---|---|---|
| bear trap | place it, it waits | SNARE on step-in (holding is the point; the bite is flavor) |
| industrial fan | (above) | — |
| **airhorn** (new) | wedge the button down, walk away | PLACED LURE (enemies investigate) |
| box of nails | pour a caltrop patch | weak PIERCE on step-in |
| tin of ball bearings (renamed) | hurl a dense handful | weak DAMAGE |
| bag of marbles (renamed) | scatter underfoot | SLOW patch |
| bag of gravel | fling a wave of grit | weak DAMAGE, wide stinging cone |

The four feeders all teach "I turn one hit into many," but no two teach it identically: nails deny ground with punctures, marbles deny ground with slipping, bearings and gravel are thrown — one dense, one wide.

**Airhorn** (addition): tags `loud` (→ LURE per `SINGLE_TAG_EFFECTS`); verb `blare`; roles `{MECHANISM}`; delivery `PLACED`. In-craft it is the noise-decoy component for lure builds — the catalog's first pure-utility placed item.

### Self-use & electrical (7)

| Item | Solo action | Base effect |
|---|---|---|
| leaf blower | wind lane; brace and ride the recoil | weak KNOCKBACK + DASH move |
| adrenaline shot | jab yourself | short weak SPEED |
| first-aid kit | patch yourself | weak HEAL |
| taser | quick press → zap | weak STAGGER, fast recovery; **gains `delivery=THRUST` (fixes the latent bug)** |
| defibrillator | charge with a rising whine, then dump | weak DAMAGE + STAGGER, slow wind-up |
| jumper cables | clamp onto a target — they bite and hold | weak SNARE ("attach things to the circuit") |
| car battery | hurl it | blunt heavy DAMAGE (refinement 3's exemplar) |

The four electrical items each teach a different lesson: taser = fast lock-up, defib = one big timed dump, cables = attachment/conduction, battery = the power source (taught by common knowledge, not by solo use).

### Containers & substances (15)

**The patch mechanic:** a thrown container bursts and leaves a patch whose effect comes from the payload's tag. Payloads inert until ignited leave an **armed patch**: no immediate effect; any ignition triggers it. Expressed with existing tokens as a two-stage build — `ON_IMPACT` (burst, no effect) + `ON_TRIGGER` (payload effect). **No new enums.**

| Item (new name) | Solo action | Patch effect |
|---|---|---|
| jerrycan of gasoline | throw → burst | armed: BURN when ignited |
| jar of thermite | throw → powder scatter | armed: big BURN when ignited ("nearly impossible to light" is the lesson) |
| sack of fertilizer | throw → pellet scatter | armed: BURN when ignited, weaker than thermite |
| jug of motor oil | throw → slick | SLOW immediately; also ignitable |
| jug of bleach | throw → splash | weak BURN (corrosive) |
| jug of ammonia cleaner | throw → splash + fumes | weak BURN (corrosive) |
| tub of pool chlorine | throw → stinging dust burst | weak BURN (corrosive) |
| dewar of liquid nitrogen | throw → burst | weak FREEZE patch |
| bucket of wet cement | throw → glop | weak SNARE (sticky) |
| crate of overripe produce | throw → pulp splash | weak SLOW (slick pulp) |
| can of expanding foam | spray a blob, it cures | weak SNARE |
| can of hairspray | spritz a mist | near-dud sticky mist; real life is as flamethrower fuel in crafts |
| block of dry ice | drop/place it (not thrown-burst — honest to the object) | weak FREEZE patch + fog (visuals only) |
| road flare | strike it — hold or throw | weak BURN; the walking ignition source that triggers armed patches |
| propane tank | heave it — steel doesn't burst (refinement 4) | blunt heavy DAMAGE; "flies when ruptured" stays craft/emergent |

**The road flare is the keystone teacher.** Throw a jerrycan (nothing happens) → toss a flare at the spill (everything happens). A two-item, zero-craft interaction that teaches the combination system in the first ten minutes.

## The item model (schema)

`Item` gains a `base_use` field, **separate from** the existing `delivery` (which keeps meaning "the FORM this mechanism locks in a craft"):

```
BaseUse:
  delivery: Delivery      # THRUST for taser, THROWN for jerrycan, PLACED for marbles...
  effect: EffectKind      # the one lesson: STAGGER, SNARE, FREEZE...
  armed: bool = False     # True = patch inert until ignition (gasoline, thermite, fertilizer)

Item.base_use: BaseUse | None   # None ONLY for AMMUNITION-flagged items
```

For mechanisms, `base_use.delivery` and `delivery` usually coincide (the crowbar swings both ways); for substances they deliberately diverge (base = THROWN burst; craft role = payload, `delivery=None`). Overloading one field would have recreated the taser bug in mirror image.

`base_use.effect` is a **single token** — one behavior, one lesson. Where an enumeration row lists a secondary effect (sledgehammer's knockback, defib's stagger, leaf blower's dash), the first token is `base_use.effect`; the secondary arrives through the delivery form or code-owned params at implementation's discretion, never a second BaseUse effect.

**The consistency test enforces the governing rule mechanically:** a unit test pins all 61 items and asserts each item's `base_use.effect` is derivable from its verb/tags (in `SINGLE_TAG_EFFECTS` of its tags), or is one of the explicitly enumerated judgment calls — each carrying a comment naming which refinement justifies it. Known judgment calls going in: car battery (refinement 3), t-shirt cannon (empty-launcher near-dud), garden hose and pressure washer (`liquid` is unmapped in `SINGLE_TAG_EFFECTS`; KNOCKBACK from the verb), glass bottle (`brittle` unmapped; PIERCE from shattering), hairspray (near-dud mist; SNARE-ish stickiness is in its associations, not its tags). The judgment-call list is closed in the test — adding to it is a deliberate act, not a default.

## Numbers

Code owns all of them (invariant 4). Base-use magnitudes are produced by running the solo item through the **existing clamp at a fixed floor tier** — never rolled, identical for every player. Rebalance = re-clamp, never re-authoring.

## Composer changes

- The `ValueError` in `Build.delivery` ("cannot be a delivery chassis") is removed: any non-ammo item can be a chassis, resolving through `base_use.delivery`. Throw-the-container is the universal fallback build.
- The deterministic composer learns one new shape: substance-as-chassis → thrown patch build (two-stage armed patch where the payload requires ignition).
- `DEFAULT_BUILDS["bananarama"]` referenced the blender; it gets rebuilt as a fan-based exemplar (exact recipe settled at implementation — an absurd fan + modifier + substance build).

## Catalog changes summary

- **Renames (15):** jerrycan of gasoline, jug of motor oil, jar of thermite, sack of fertilizer, jug of bleach, jug of ammonia cleaner, tub of pool chlorine, dewar of liquid nitrogen, bucket of wet cement, crate of overripe produce, can of expanding foam, can of hairspray, block of dry ice, bag of marbles, tin of ball bearings. (Names now uniformly show the container across everything scatterable/throwable; road flare, propane tank, bag of gravel, box of nails already do.)
- **Swap (1):** blender → industrial fan.
- **Addition (1):** airhorn.
- **Total: 61 items** (60 − 1 + 2).
- Association clouds for renamed/swapped/new items are the **queued follow-up pass**, not this design; the live cloud validation stays paused until that pass.

## Out of scope

Recon/surveillance items; concealment as a mechanic (presentation only); pre-made mine/trap items; any enum widening; renderer work; `_TIER_SEED` tuning (play-tuned, separately queued).

## Testing

TDD applies (this is all brain code): the 61-item consistency test above; base-use resolution through the clamp at floor tier (fixed outputs, property: below the cheapest craft using the same item); ammo-exception shape test; armed-patch stage structure; `Build.delivery` fallback path; catalog shape tests updated for renames/swap/addition (the association-shape tests in `tests/test_associations.py` will need the renamed keys; new items get placeholder clouds within the existing shape rules until the cloud pass). Keep all 95 existing tests green, updating only where names changed.
