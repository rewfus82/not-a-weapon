# Association Clouds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author association clouds for all 60 catalog items in `resolver/items.py` so the LLM path stops starving, then validate them live with risk-class probe builds.

**Architecture:** Pure data authoring into the existing `Item.associations` field (`tuple[str, ...]`) — no schema change, `describe()` untouched. Four authoring batches by catalog layer, each pinned by parametrized shape tests. Probe builds are wired at the harness layer (`PROBE_BUILDS`), never into `DEFAULT_BUILDS`. Live validation runs after a hard user-review gate.

**Tech Stack:** Python 3.12, pytest, existing resolver harness (`python -m resolver.harness`).

**Spec:** `docs/superpowers/specs/2026-07-12-association-clouds-design.md` — read it first. The clouds below are the authored deliverable; transcribe them **verbatim** (they were written to satisfy the spec's register, ordering, and no-digits rules — do not "improve" them).

## Global Constraints

- Only knowledge/currency persist; enums are the capability contract — this plan touches **no** enums, schema, `clamp.py`, router thresholds, or system-prompt rules (one *exemplar* text block is refreshed, no rule text changes).
- Deterministic path must stay fully functional with no API key at every commit.
- `python -m pytest -q` green at **every** commit (currently 95 passing).
- Associations: ordered obvious → non-obvious → chainable; junk 3–5 lines; guns (FIREARM flag) 2–3; ammo (AMMUNITION flag) 1–2; **no digits** except an item's own caliber/name; no magnitudes in words either ("heavy", never "fifty-pound"); real register throughout — cartoon register is applied ONLY in Task 7's repair loop, per-item, on live refusal evidence.
- **Never ask any model why it refused.** Refusals are a normal fallback outcome: log the rate, repair by ablation (Task 7). This is a standing AUP lesson — violating it has flagged sessions before.
- Commits: conventional messages, one per task (Task 7 may commit per repair). `git add` ONLY the files named in the task. End commit messages with your standard `Co-Authored-By` trailer.
- Append a one-line status per completed task to `.superpowers/sdd/progress.md` under a new `## Plan: 2026-07-12-association-clouds` heading.
- Windows: run live harness commands with `PYTHONUTF8=1` and redirect output to a UTF-8 file (em-dashes mojibake the console).

---

### Task 1: Shape tests + Batch 1 — ranged mechanisms & guns (16 items)

**Files:**
- Create: `tests/test_associations.py`
- Modify: `resolver/items.py` (the 16 `Item(...)` entries listed below)

**Interfaces:**
- Consumes: `resolver.items.CATALOG`, `resolver.contract.Flag`.
- Produces: `tests/test_associations.py` with `BATCH_RANGED: tuple[str, ...]` and helper `_assert_cloud(name: str) -> None`; Tasks 2–4 add `BATCH_CONTACT`, `BATCH_MODIFIERS`, `BATCH_SUBSTANCES` tuples and reuse `_assert_cloud` unchanged.

- [ ] **Step 1: Write the failing shape tests**

Create `tests/test_associations.py`:

```python
"""Mechanical invariants for the association clouds. Prose quality is gated
by user review (spec: 2026-07-12-association-clouds-design.md), not tests.
"""
import re

import pytest

from resolver.contract import Flag
from resolver.items import CATALOG

# Batch tuples are appended per authoring task; Task 4 asserts they
# partition the whole catalog.
BATCH_RANGED: tuple[str, ...] = (
    "m16 rifle", ".22 pistol", "9mm pistol", "revolver",
    ".30-06 hunting rifle", "pump shotgun",
    "nail gun", "fire extinguisher", "pressure washer", "blender",
    "garden hose", "potato cannon", "roman candle", "glass bottle",
    "cinder block", "salvaged laser cutter",
)


def _expected_line_range(item) -> tuple[int, int]:
    if Flag.FIREARM in item.flags:
        return (2, 3)
    if Flag.AMMUNITION in item.flags:
        return (1, 2)
    return (3, 5)


def _assert_cloud(name: str) -> None:
    item = CATALOG[name]
    lo, hi = _expected_line_range(item)
    n = len(item.associations)
    assert lo <= n <= hi, f"{name}: {n} lines, expected {lo}-{hi}"
    for line in item.associations:
        stripped = line.replace(item.name, "")
        if item.caliber:
            stripped = stripped.replace(item.caliber, "")
        assert not re.search(r"\d", stripped), f"{name}: digits in {line!r}"


@pytest.mark.parametrize("name", BATCH_RANGED)
def test_ranged_batch_cloud_shape(name):
    _assert_cloud(name)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_associations.py -q`
Expected: 16 FAILs, each `"...: 0 lines, expected ..."` (no item has associations yet).

- [ ] **Step 3: Author Batch 1 in `resolver/items.py`**

Add an `associations=(...)` keyword to each of these 16 existing `Item(...)` entries. Place it right after the name argument for readability (it's a keyword; call-site position is free). Worked example of the placement for the first item — apply the same pattern to all:

```python
    Item("m16 rifle",
         associations=(
             "a military service rifle",
             "fires 5.56 on full auto; does exactly what a rifle does",
         ),
         roles=frozenset({M}), verb="fire-auto",
         tags=frozenset(), delivery=Delivery.HITSCAN, caliber="5.56", flags=_GUN),
```

The clouds, verbatim (guns are deliberately dry — that's the spec, not laziness):

```python
# m16 rifle
associations=(
    "a military service rifle",
    "fires 5.56 on full auto; does exactly what a rifle does",
),
# .22 pistol
associations=(
    "a small-bore .22 target pistol",
    "quiet, light, and exactly as boring as it looks",
),
# 9mm pistol  (spec exemplar — verbatim)
associations=(
    "a standard 9mm sidearm",
    "does exactly what a pistol does; nothing clever about it",
),
# revolver
associations=(
    "a .357 six-shooter",
    "heavy trigger, big noise, no surprises",
),
# .30-06 hunting rifle
associations=(
    "a bolt-action .30-06 hunting rifle",
    "slow, deliberate, and accurate at long range",
),
# pump shotgun
associations=(
    "a pump-action 12ga shotgun",
    "wide, loud, and short-ranged; exactly what it looks like",
),
# nail gun
associations=(
    "a construction tool that spits framing nails",
    "meant to be pressed against wood, but the safety tip is long gone",
    "each nail flies flat and pins whatever it hits",
    "whatever coats the nails goes wherever the nails go",
),
# fire extinguisher
associations=(
    "a red steel bottle under serious pressure",
    "vents a freezing white cone that blankets everything in front of it",
    "the blast shoves lightweight things backward and kills open flames",
    "empty, it's still a heavy steel club — and punctured, it takes off like a rocket",
),
# pressure washer
associations=(
    "a motor that turns a garden trickle into a cutting jet",
    "the stream hits hard enough to strip paint and peel bark",
    "knocks light things over and pushes heavy things back",
    "whatever you feed the intake comes out the nozzle at paint-stripping speed",
),
# blender  (spec exemplar — verbatim)
associations=(
    "a pitcher of whirling blades on a motor base",
    "chews anything dropped in into a slurry",
    "the lid never holds — run it open and it slings its contents out in a cone",
    "whatever you feed it comes out the top as a fine flying spray",
),
# garden hose
associations=(
    "a long rubber hose that sprays wherever you point it",
    "soaks the ground into mud and puddles",
    "kink it and let go for a single hard spurt",
    "a wet floor plus anything electrical is everyone's problem at once",
),
# potato cannon
associations=(
    "a length of pipe that lobs whatever fits down the barrel",
    "a puff of propellant sends the payload in a high arc",
    "doesn't care what the payload is, only that it fits",
    "load something that splashes, shatters, or burns and it delivers that downrange",
),
# roman candle
associations=(
    "a cardboard tube that spits burning stars one at a time",
    "each star pops loud and glows bright enough to read by",
    "the stars keep burning wherever they land",
    "every star is a flying ignition source for anything flammable it touches",
),
# glass bottle
associations=(
    "an empty glass bottle, ready to be filled",
    "shatters on the first hard knock into a burst of sharp shards",
    "holds a pour of whatever liquid you have on hand",
    "thrown full, it breaks on impact and splashes its contents over everything nearby",
),
# cinder block
associations=(
    "a two-handed slab of concrete",
    "everything it lands on stays landed on",
    "awkward to throw far, devastating to drop close",
    "crushes brittle things flat and pins whatever it doesn't crush",
),
# salvaged laser cutter
associations=(
    "an industrial cutting head pulled off its gantry, trigger wired by hand",
    "projects a thin line of light that scorches a seam across whatever it crosses",
    "steady hands turn it into a slow knife at a distance",
    "anything flammable along the line starts smoking before the beam even finishes passing",
),
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass (95 existing + 16 new parametrized). Nothing else asserts on these items' `describe()`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_associations.py resolver/items.py
git commit -m "feat: association clouds - ranged mechanisms and dry-lined guns (batch 1/4)"
```

---

### Task 2: Batch 2 — contact & mobility mechanisms (15 items)

**Files:**
- Modify: `tests/test_associations.py` (add `BATCH_CONTACT` + test)
- Modify: `resolver/items.py` (15 entries)
- Modify: `tests/test_prompt.py:22-23` (the `"clobber"` assertion — see Step 1; it breaks the moment the bat gets a cloud, because `describe()` stops emitting the verb)

**Interfaces:**
- Consumes: `_assert_cloud` from Task 1 (same file).
- Produces: `BATCH_CONTACT: tuple[str, ...]`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_associations.py`, add below `BATCH_RANGED`:

```python
BATCH_CONTACT: tuple[str, ...] = (
    "crowbar", "sledgehammer", "fire axe", "machete", "screwdriver",
    "baseball bat", "power drill", "angle grinder", "chainsaw",
    "weed whacker", "riot shield", "bear trap", "leaf blower",
    "adrenaline shot", "first-aid kit",
)


@pytest.mark.parametrize("name", BATCH_CONTACT)
def test_contact_batch_cloud_shape(name):
    _assert_cloud(name)
```

In `tests/test_prompt.py`, replace the last two lines of
`test_render_user_message_includes_slots_associations_delivery_and_tier`:

```python
    # at least one descriptor from the delivery item is injected
    assert "clobber" in msg
```

with:

```python
    # at least one descriptor from the delivery item's cloud is injected
    assert "swing weight" in msg
```

- [ ] **Step 2: Run to verify both fail**

Run: `python -m pytest tests/test_associations.py tests/test_prompt.py -q`
Expected: 15 FAILs (`0 lines`) + 1 FAIL (`"swing weight" not in msg` — bat still describes as verb+tags).

- [ ] **Step 3: Author Batch 2 in `resolver/items.py`**

Same `associations=(...)` placement pattern as Task 1. Verbatim:

```python
# crowbar
associations=(
    "a bent steel bar with a flattened claw",
    "swings mean and pries meaner",
    "finds the gap in anything — doors, crates, armor plates",
    "wedged into a seam, it turns your whole body weight into leverage",
),
# sledgehammer
associations=(
    "a slab of steel on a long handle",
    "too slow to swing twice, too heavy to need to",
    "the follow-through carries into walls, floors, and whatever's behind the target",
    "one full swing turns brittle things into gravel",
),
# fire axe
associations=(
    "a heavy axe head on a long haft, made for cutting through doors",
    "bites deep and sticks where it lands",
    "the spike on the back punches holes the blade can't",
    "momentum does the work — whatever it hits, it hits committed",
),
# machete
associations=(
    "a long flat blade made for clearing brush",
    "light enough to swing all day, fast enough to swing twice",
    "slices in arcs rather than chops",
    "whatever's smeared on the blade ends up in every cut",
),
# screwdriver
associations=(
    "a palm-sized steel spike with a handle",
    "goes exactly where you push it, no farther",
    "punches through sheet metal if you lean in",
    "jammed into a moving part, it stops the whole machine",
),
# baseball bat   ("swing weight" in line 1 is pinned by tests/test_prompt.py)
associations=(
    "a solid wooden bat with real swing weight",
    "the sweet spot sends things flying instead of just breaking them",
    "flexes a hair on impact and gives the hit a spring",
    "anything small and hard becomes a line drive if you can toss it up first",
),
# power drill
associations=(
    "a cordless drill with a fresh bit",
    "chews through wood, plastic, and thin steel",
    "the torque wrenches your wrist if the bit binds",
    "pressed against anything, it doesn't stop at the surface",
),
# angle grinder
associations=(
    "a spinning abrasive disc on a motor",
    "throws a rooster tail of sparks off bare metal",
    "doesn't cut so much as eat its way through",
    "the spark stream is an ignition source you can aim",
),
# chainsaw
associations=(
    "a motorized chain of cutting teeth",
    "announces itself from a block away",
    "pulls itself into the cut once it bites",
    "the noise alone empties a room before the blade arrives",
),
# weed whacker
associations=(
    "a spinning line on the end of a long shaft",
    "stings and shreds anything soft inside a wide arc",
    "keeps threats at a full pole's length",
    "swap the trimmer line for wire or chain and the sting becomes a bite",
),
# riot shield
associations=(
    "a clear polymer wall with a handle",
    "turns anything thrown or swung at you",
    "leaning in, it's a pushing weapon in its own right",
    "whatever splashes against the front stays on the front — not on you",
),
# bear trap
associations=(
    "a spring-loaded steel jaw staked to the ground",
    "waits under leaves or trash until something steps in",
    "snaps shut hard enough to hold what it catches",
    "anything lured, herded, or knocked onto it does the work for you",
),
# leaf blower
associations=(
    "a backpack motor that throws a hard lane of wind",
    "shoves loose junk, dust, and mist wherever it points",
    "braced against your own body, the recoil is a push you can ride",
    "anything drifting in the air — spray, smoke, sparks — rides the wind lane downrange",
),
# adrenaline shot
associations=(
    "a spring-loaded autoinjector of pure hurry",
    "your legs stop asking questions for a little while",
    "pain arrives later, all at once, with interest",
    "everything else you're carrying gets used faster while it lasts",
),
# first-aid kit
associations=(
    "gauze, splints, and stims in a plastic clamshell",
    "closes wounds well enough to keep moving",
    "works on the move if you don't mind the stitching",
    "buys back the mistakes the rest of this loadout will cause",
),
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass (the prompt test now finds "swing weight" via the bat's cloud).

- [ ] **Step 5: Commit**

```bash
git add tests/test_associations.py tests/test_prompt.py resolver/items.py
git commit -m "feat: association clouds - contact and mobility mechanisms (batch 2/4)"
```

---

### Task 3: Batch 3 — modifiers/energizers (6 items) + system-prompt exemplar refresh

**Files:**
- Modify: `tests/test_associations.py` (add `BATCH_MODIFIERS` + test)
- Modify: `resolver/items.py` (6 entries)
- Modify: `resolver/prompts/system_prompt.txt` (Example block only — the bat+battery exemplar now shows the OLD verb+tags `describe()` format and cites properties ("blunt", "springy") the model will no longer see stated)
- Modify: `docs/RESOLVER_PROMPT_v0.md` (mirrors the prompt verbatim — apply the identical Example-block edit; locate it with `grep -n "Objects as they arrive" docs/RESOLVER_PROMPT_v0.md`)

**Interfaces:**
- Consumes: `_assert_cloud` from Task 1.
- Produces: `BATCH_MODIFIERS: tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

In `tests/test_associations.py`:

```python
BATCH_MODIFIERS: tuple[str, ...] = (
    "propane tank", "fertilizer", "car battery", "jumper cables",
    "defibrillator", "taser",
)


@pytest.mark.parametrize("name", BATCH_MODIFIERS)
def test_modifier_batch_cloud_shape(name):
    _assert_cloud(name)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_associations.py -q`
Expected: 6 FAILs (`0 lines`).

- [ ] **Step 3: Author Batch 3 in `resolver/items.py`**

The car battery cloud is the OLD catalog's proven cloud, reused verbatim (it never drove a refusal across every live run — do not reword it).

```python
# propane tank
associations=(
    "a squat steel tank of liquid propane under pressure",
    "hisses out a heavier-than-air cloud when the valve cracks",
    "the tank itself flies when ruptured",
    "a leaking cloud finds every spark in the room the hard way",
),
# fertilizer
associations=(
    "a heavy sack of pellet fertilizer",
    "grows crops on the label, wears a hazard diamond on the back",
    "burns fast and mean once something sets it off",
    "packed in with anything else that burns, the burn becomes a blast",
),
# car battery   (old catalog's proven cloud — verbatim)
associations=(
    "dead-weight heavy",
    "holds a charge that arcs across a gap",
    "leaks corrosive acid",
    "a hard enough knock cracks the case and spills the acid",
),
# jumper cables
associations=(
    "a pair of thick copper clamps on long insulated leads",
    "the clamps bite onto anything and hold",
    "bridge them to a live source and the far ends carry the charge",
    "anything conductive they're clipped to becomes part of the circuit",
),
# defibrillator
associations=(
    "a portable unit with two paddles and one job",
    "builds a charge with a rising whine, then dumps it all at once",
    "the jolt clenches every muscle it crosses",
    "delivered through anything conductive — rails, puddles, chain link — it travels",
),
# taser
associations=(
    "a palm-sized stunner with a crackling arc between two prongs",
    "the arc snaps and pops even before it touches anything",
    "a touch locks up whatever muscle it finds",
    "held against metal or wet ground, the crackle keeps traveling",
),
```

- [ ] **Step 4: Refresh the exemplar in `resolver/prompts/system_prompt.txt`**

Replace the line beginning `Example. Objects as they arrive to you:` with:

```
Example. Objects as they arrive to you: delivery = baseball bat — a solid wooden bat with real swing weight, the sweet spot sends things flying instead of just breaking them, flexes a hair on impact and gives the hit a spring, anything small and hard becomes a line drive if you can toss it up first. modifier = car battery — dead-weight heavy, holds a charge that arcs across a gap, leaks corrosive acid, a hard enough knock cracks the case and spills the acid. Target DUD:
```

Then in the LEGENDARY exemplar a few lines below, replace the `logic:` line (which cites "blunt" and "springy" — properties no longer stated) with:

```
  logic: "The bat has real swing weight and a spring in the flex: real force behind a real rebound. The battery is dead-weight, leaks acid, and holds a charge that arcs: leaking terminals coat the barrel and carry a jolt into whatever it hits. The impact burns and shocks together, the dead weight rides the springy rebound and sends them flying, and what's left over arcs to whoever's standing closest."
```

Leave the DUD exemplar and everything else untouched. Apply the **identical** two replacements in `docs/RESOLVER_PROMPT_v0.md`.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass (`tests/test_prompt.py` checks length + banned jargon words only; neither edit trips it — verify).

- [ ] **Step 6: Commit**

```bash
git add tests/test_associations.py resolver/items.py resolver/prompts/system_prompt.txt docs/RESOLVER_PROMPT_v0.md
git commit -m "feat: association clouds - modifiers; refresh bat+battery exemplar to cloud format (batch 3/4)"
```

---

### Task 4: Batch 4 — substances, ammo, feeders (23 items) + full-catalog coverage

**Files:**
- Modify: `tests/test_associations.py` (add `BATCH_SUBSTANCES` + test + two coverage tests)
- Modify: `resolver/items.py` (23 entries + module docstring)

**Interfaces:**
- Consumes: `_assert_cloud`, the three earlier batch tuples.
- Produces: `BATCH_SUBSTANCES: tuple[str, ...]`; after this task every `CATALOG` item has a cloud.

- [ ] **Step 1: Write the failing tests**

In `tests/test_associations.py`:

```python
BATCH_SUBSTANCES: tuple[str, ...] = (
    "gasoline", "motor oil", "thermite", "road flare", "hairspray",
    "pool chlorine", "ammonia cleaner", "bleach", "liquid nitrogen",
    "dry ice", "wet cement", "expanding foam", "overripe produce",
    ".22 rounds", "9mm rounds", ".357 rounds", "5.56 rounds",
    "12-gauge shells", ".30-06 rounds",
    "box of nails", "ball bearings", "marbles", "bag of gravel",
)


@pytest.mark.parametrize("name", BATCH_SUBSTANCES)
def test_substance_batch_cloud_shape(name):
    _assert_cloud(name)


def test_every_item_has_a_cloud():
    for item in CATALOG.values():
        assert item.associations, f"{item.name} has no associations"


def test_batches_cover_the_whole_catalog():
    covered = set(BATCH_RANGED) | set(BATCH_CONTACT) | set(BATCH_MODIFIERS) | set(BATCH_SUBSTANCES)
    assert covered == set(CATALOG)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_associations.py -q`
Expected: 23 parametrized FAILs + `test_every_item_has_a_cloud` FAIL. `test_batches_cover_the_whole_catalog` should already PASS (16+15+6+23 = 60) — if it fails, a batch tuple has a typo'd item name; fix the tuple, not the catalog.

- [ ] **Step 3: Author Batch 4 in `resolver/items.py`**

Real ammo is deliberately near-silent, and the corrosive clouds deliberately name hazards at hazard-label level without naming reaction partners — keep it that way.

```python
# gasoline
associations=(
    "a can of gasoline, sloshing and sharp-smelling",
    "splashes wide, soaks in, and stays",
    "the fumes catch before the liquid does",
    "one spark anywhere on the spill claims the whole spill",
),
# motor oil   (spec exemplar — verbatim)
associations=(
    "slick, viscous, impossible to get traction on",
    "clings in a dark film to whatever it coats",
    "flammable once something gets it hot enough",
    "poured across a floor it turns the whole stretch into a skating rink",
),
# thermite
associations=(
    "a jar of dull grey powder that looks like nothing",
    "nearly impossible to light — and nearly impossible to put out once lit",
    "burns hot enough to eat through steel plate",
    "poured onto a surface first, it turns any ignition into a cutting charge",
),
# road flare
associations=(
    "a stick that strikes to a furious red flame",
    "burns wet or dry, wind be damned",
    "bright enough to blind night eyes and mark positions",
    "an open flame you can hold, plant, or throw at anything that wants lighting",
),
# hairspray   (last line is the old aerosol can's proven line — verbatim)
associations=(
    "a can of hairspray under pressure",
    "sprays a fine sticky mist that hangs in the air",
    "the propellant is flammable",
    "a mist plus a spark becomes a gout of flame",
),
# pool chlorine
associations=(
    "a tub of pool-shock granules with a bleachy reek",
    "eats color, fabric, and skin given time",
    "the dust alone stings eyes and throats",
    "given something to react with, the granules boil into stinging fog",
),
# ammonia cleaner
associations=(
    "a jug of ammonia cleaner that clears your sinuses from across the room",
    "the fumes sting eyes shut and chase people out of small spaces",
    "slicks and strips whatever it's poured over",
    "in a closed room the fumes do more work than the liquid",
),
# bleach
associations=(
    "a jug of household bleach",
    "ruins everything it splashes — cloth, color, skin",
    "the smell alone announces it",
    "an open pan of it makes a room hostile to stay in",
),
# liquid nitrogen
associations=(
    "a steel dewar of liquid so cold it smokes",
    "a splash freezes surfaces white on contact",
    "what it soaks turns brittle as glass",
    "frozen brittle, things that used to bend now shatter",
),
# dry ice
associations=(
    "a block of dry ice, smoking in open air",
    "burns bare skin with cold instead of heat",
    "sublimates into a heavy ground-hugging fog",
    "dropped in water it fogs a whole corridor in moments",
),
# wet cement
associations=(
    "a bucket of wet cement, heavy and slopping",
    "clings to boots and drags every step",
    "sets hard on its own schedule, and nothing renegotiates",
    "whatever's standing in it when it cures is furniture now",
),
# expanding foam
associations=(
    "a can of gap-filler foam",
    "a thin bead swells to a fat, sticky loaf",
    "cures from tacky to rock in place",
    "sprayed into a mechanism or a doorway, it becomes the new mechanism",
),
# overripe produce
associations=(
    "a crate of produce past its best days",
    "bursts into slick pulp at the slightest violence",
    "the pulp is half slip, half glue",
    "anything driven through it comes out wearing it",
),
# .22 rounds
associations=(
    "a box of .22 rounds",
    "inert until a matching firearm feeds them",
),
# 9mm rounds
associations=(
    "a box of 9mm rounds",
    "inert until a matching firearm feeds them",
),
# .357 rounds
associations=(
    "a box of .357 rounds",
    "inert until a matching revolver feeds them",
),
# 5.56 rounds
associations=(
    "a box of 5.56 rounds",
    "inert until a matching rifle feeds them",
),
# 12-gauge shells
associations=(
    "a box of 12-gauge shells",
    "inert until a matching shotgun feeds them",
),
# .30-06 rounds
associations=(
    "a box of .30-06 rounds",
    "inert until a matching rifle feeds them",
),
# box of nails
associations=(
    "a hardware-store box of loose nails",
    "each one is a small sharp problem for whoever's downrange",
    "they tumble and scatter rather than fly true",
    "fired or flung in a handful, they turn one hit into many small punctures",
),
# ball bearings
associations=(
    "a tin of dense steel spheres",
    "heavier than they look; they hit like thrown weights",
    "spilled underfoot, they take feet out from under people",
    "launched in a spread they dent everything in a cone",
),
# marbles
associations=(
    "a bag of glass marbles",
    "roll forever on any hard floor",
    "underfoot they're a slapstick disaster",
    "scattered ahead of a chase, they end the chase",
),
# bag of gravel
associations=(
    "a heavy bag of loose gravel",
    "flung, it's a wave of stinging grit",
    "spread thin, it makes every step loud and unsure",
    "loaded into anything that launches, it becomes a wide, ugly cone",
),
```

- [ ] **Step 4: Update the `resolver/items.py` module docstring**

Append to the existing docstring (keep everything already there):

```
Association-cloud conventions (spec: 2026-07-12-association-clouds-design.md):
ordered obvious -> non-obvious -> chainable; lines embody the item's tags and
verb, never contradict them; no digits or magnitudes (caliber names excepted);
real register — cartoon register is a per-item repair applied only on live
refusal evidence, never pre-emptively. Shape is pinned by tests/test_associations.py.
```

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass. Every catalog item now has a cloud.

- [ ] **Step 6: Commit**

```bash
git add tests/test_associations.py resolver/items.py
git commit -m "feat: association clouds - substances, ammo, feeders; full catalog covered (batch 4/4)"
```

---

### Task 5: Probe builds at the harness layer

**Files:**
- Modify: `resolver/harness.py` (add `PROBE_BUILDS`/`ALL_BUILDS`; swap three `DEFAULT_BUILDS` lookups)
- Modify: `tests/test_harness.py` (add tests; follow the file's existing conventions)

**Interfaces:**
- Consumes: `resolver.items.CATALOG`, `Build`, `DEFAULT_BUILDS`; existing `run()`, `routing_summary()`, `main()`.
- Produces: `resolver.harness.PROBE_BUILDS: dict[str, Build]` and `resolver.harness.ALL_BUILDS: dict[str, Build]` (Task 7 runs probes by these keys). `run()` and `routing_summary()` signatures unchanged.

- [ ] **Step 1: Write the failing tests**

In `tests/test_harness.py` add (adapt imports to the file's existing style):

```python
from resolver.fallback import resolve as fallback_resolve
from resolver.harness import ALL_BUILDS, PROBE_BUILDS, run
from resolver.items import DEFAULT_BUILDS


def test_probe_builds_cover_the_risk_classes():
    assert set(PROBE_BUILDS) == {
        "probe_incendiary", "probe_corrosive", "probe_whimsical",
        "probe_electric", "probe_gun", "probe_trap",
    }
    assert not set(PROBE_BUILDS) & set(DEFAULT_BUILDS)
    assert ALL_BUILDS == {**DEFAULT_BUILDS, **PROBE_BUILDS}


def test_probe_build_runs_on_the_deterministic_path():
    results = run(fallback_resolve, ["probe_incendiary"], repeats=1)
    assert results and all(r.build_key == "probe_incendiary" for r in results)
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_harness.py -q`
Expected: ImportError — `PROBE_BUILDS`/`ALL_BUILDS` don't exist.

- [ ] **Step 3: Implement in `resolver/harness.py`**

Change the items import to include `CATALOG`:

```python
from resolver.items import CATALOG, DEFAULT_BUILDS, Build
```

Below the import block add:

```python
# Throwaway validation builds covering the refusal-risk classes (spec:
# 2026-07-12-association-clouds-design.md). Harness-layer fixtures only;
# deliberately NOT in DEFAULT_BUILDS.
PROBE_BUILDS: dict[str, Build] = {
    "probe_incendiary": Build(
        delivery_item=CATALOG["potato cannon"],
        damage_item=CATALOG["gasoline"],
        utility_item=CATALOG["road flare"],
    ),
    "probe_corrosive": Build(
        delivery_item=CATALOG["pressure washer"],
        damage_item=CATALOG["pool chlorine"],
    ),
    "probe_whimsical": Build(
        delivery_item=CATALOG["blender"],
        damage_item=CATALOG["marbles"],
        utility_item=CATALOG["expanding foam"],
    ),
    "probe_electric": Build(
        delivery_item=CATALOG["weed whacker"],
        modifier_item=CATALOG["jumper cables"],
    ),
    "probe_gun": Build(
        delivery_item=CATALOG["9mm pistol"],
        damage_item=CATALOG["9mm rounds"],
    ),
    "probe_trap": Build(
        delivery_item=CATALOG["bear trap"],
        utility_item=CATALOG["motor oil"],
    ),
}

ALL_BUILDS: dict[str, Build] = {**DEFAULT_BUILDS, **PROBE_BUILDS}
```

Then swap exactly three lookups from `DEFAULT_BUILDS` to `ALL_BUILDS`:
- `run()`: `build = ALL_BUILDS[key]`
- `routing_summary()`: `build = ALL_BUILDS[result.build_key]`
- `main()` argparse: `choices=list(ALL_BUILDS)` — but keep the no-flag default as `build_keys = args.builds or list(DEFAULT_BUILDS)` (a plain `python -m resolver.harness` run must NOT silently include probes).

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: CLI smoke test (deterministic, no API key needed)**

Run: `python -m resolver.harness --fallback --build probe_trap --repeats 1`
Expected: renders a spread for `probe_trap` across the six tiers, plus fallback/routing summary lines. Exit 0.

- [ ] **Step 6: Commit**

```bash
git add tests/test_harness.py resolver/harness.py
git commit -m "feat: harness probe builds for association-cloud validation"
```

---

### Task 6: HARD GATE — user reviews all 60 clouds

No live API call happens before this gate closes. Blandness is cheap to fix as text, expensive to discover in live output.

**Files:**
- Create: `docs/superpowers/review/2026-07-12-association-clouds-review.md` (review artifact; committed so the review has a stable object)
- Possibly modify: `resolver/items.py` (user edits)

- [ ] **Step 1: Generate the review artifact**

Write a script-free dump using Python:

```bash
python -c "
from resolver.items import CATALOG
lines = ['# Association clouds - review copy (generated from resolver/items.py)', '']
for item in CATALOG.values():
    lines.append(f'## {item.name}')
    lines.extend(f'- {a}' for a in item.associations)
    lines.append('')
open('docs/superpowers/review/2026-07-12-association-clouds-review.md', 'w', encoding='utf-8').write('\n'.join(lines))
" 
```

(Create the `docs/superpowers/review/` directory first if it doesn't exist.)

- [ ] **Step 2: STOP — present to the user**

Tell the user the review file path and ask for editorial read-through of all 60 clouds. **Do not proceed to Task 7 without explicit approval.** This is the spec's quality gate.

- [ ] **Step 3: Apply any user edits**

Apply requested edits to `resolver/items.py` (and regenerate the review file so the two match). Run `python -m pytest -q` — must stay green (edits must respect the shape rules; if the user's wording genuinely needs to break one, surface the conflict rather than silently bending the test).

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/review/2026-07-12-association-clouds-review.md resolver/items.py
git commit -m "docs: association-cloud review copy; apply user editorial pass"
```

(If the user made no edits, commit just the review file.)

---

### Task 7: Live validation + ablation repair loop

Requires `ANTHROPIC_API_KEY` in the environment. If it is missing, STOP and ask the user — do not fake or skip validation.

**Files:**
- Create: run outputs under the session scratchpad (NOT the repo; they are throwaway)
- Possibly modify: `resolver/items.py` (targeted register repairs only)
- Modify: `.superpowers/sdd/progress.md` (results), `docs/HANDOFF.md` (task outcome)

- [ ] **Step 1: Run the six probes live**

For each key in `probe_incendiary probe_corrosive probe_whimsical probe_electric probe_gun probe_trap` (bash; 12 calls per build = 6 tiers + 2 extra repeats × 3 high tiers; 72 calls total):

```bash
PYTHONUTF8=1 python -m resolver.harness --build <key> --repeats 3 > "$SCRATCHPAD/<key>.txt" 2>&1
```

Default flags already give the proven retry ladder (`--attempts 3`, escalation to opus-4-8 on the final attempt).

- [ ] **Step 2: Read each output file and tally**

For each build record: fallback count (the `render_fallback_summary` line) and an eyeball verdict on dud→god spread + within-tier variety at RARE/EPIC/LEGENDARY.

Acceptance per spec: **~0% fallback per build** (a single transport-error fallback in 72 calls is tolerable; a repeated-refusal build is not) and a real spread on every build.

- [ ] **Step 3: Repair loop (only for builds with repeated refusals)**

For each refusing build, identify the implicated item **by ablation only**:
1. Re-run the build with one item swapped for a neutral same-role stand-in (e.g. swap the suspect substance for `wet cement`), `--repeats 3`.
2. The item whose removal drops the refusals is implicated. **Never ask any model to explain or categorize a refusal** — rate only.
3. Rewrite ONLY the implicated item's cloud in cartoon register — change the *register*, keep every mechanism hook (precedent: the old box fan kept "aim it down a hall and its wind ferries along whatever's floating — mist, dust, sparks" while going fully cartoon in tone). Keep the shape rules; `python -m pytest -q` stays green.
4. Re-run ONLY the affected build live. Repeat once more if needed; if a build still refuses after two register passes, STOP and surface to the user (deterministic-lean is an acceptable documented outcome — see the fan+duck history).
5. Commit each repair separately:

```bash
git add resolver/items.py
git commit -m "fix: cartoon register for <item> (live refusal evidence, ablated)"
```

Also regenerate and commit the Task 6 review file so it matches the repaired catalog.

- [ ] **Step 4: Record results**

Append to `.superpowers/sdd/progress.md` under the plan heading: per-build fallback tallies (before/after any repairs), which items (if any) were cartoon-repaired, and the spread verdict. Update `docs/HANDOFF.md`: mark the association-clouds task done, note repairs, and point the next session at the remaining follow-up queue.

- [ ] **Step 5: Final suite + commit**

Run: `python -m pytest -q` — all green.

```bash
git add docs/HANDOFF.md
git commit -m "docs: association clouds validated live; handoff updated"
```

---

## Self-review notes (already applied)

- Spec coverage: scope/conventions → Tasks 1–4; docstring consistency rule → Task 4 Step 4; probe builds + "not in DEFAULT_BUILDS" → Task 5; user review gate → Task 6; validation, acceptance, ablation repair, ledger → Task 7; exemplar staleness ripple → Task 3; `test_prompt.py` "clobber" ripple → Task 2.
- Every cloud line was digit-scanned against the Task 1 test rule (calibers only, strippable via `item.caliber`/`item.name`).
- Counts: 16 + 15 + 6 + 23 = 60 = `len(CATALOG)`; junk 48 at 4 lines, guns 6 at 2, ammo 6 at 2.
