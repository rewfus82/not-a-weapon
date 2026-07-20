# Item-Cloud Editorial Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four new catalog items (firefighter turnout coat, battery boombox, cooler of raw steaks, case of energy drinks) and one non-fire hook line to each of the six real-ammo association clouds, with all prose passing a user editorial checkpoint before landing in `resolver/items.py`.

**Architecture:** Pure content change inside the existing `Item` catalog plus test-pin updates. No resolver code changes: the turnout coat activates the dormant ON_HIT self-kit path through the *existing* `resolver/validate.py` protective-tag check; all four items use existing enum values and existing taxonomy tags. `contract_fingerprint` hashes only the enum vocabularies, so the committed pre30 scaffolds and the HELD pilot selection are unaffected.

**Tech Stack:** Python 3 dataclasses, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-19-item-cloud-editorial-pass-design.md`

## Global Constraints

- **No live API calls anywhere in this pass.** Do not run `python -m resolver.bake run` or `dedup`; the 300-combo pilot stays HELD. Live validation of the new items rides with the next bake wave.
- **The enums are the capability contract — never widen them** (`resolver/contract.py`). Never widen the tag taxonomy (`resolver/interactions.py`) either — all four items use existing tags.
- **NEVER introspect why a call was refused. Log rates only. No stop reasons, exception text, or failure classification in records or console output.** (Standing AUP rule; no live calls happen here, but the rule binds any code touched.)
- **Task 1's user editorial checkpoint is a hard gate.** No prose lands in `resolver/items.py` until the user has red-penned the review document. The prose in Tasks 2–3 below is the *draft*; if the user amended any line at the checkpoint, use the amended text verbatim instead. Item mechanics (roles/delivery/tags/base_use/verb) are locked by the spec and are NOT at the checkpoint's discretion.
- Branch `main` only; **no remote — do not push, do not add one**.
- Never stage wholesale: `git add` only the explicitly named files in each commit step. Untracked files (`data/bake/combos-pilot.json`, `hello.md`, `docs/CAPABILITY_CONTRACT_v0.md`, the 2026-07-10 docs) are intentional — leave them alone.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Cloud conventions (2026-07-12 spec, inherited): 3–5 lines for normal items, ordered obvious → non-obvious → chainable-last; lines embody the item's tags and verb; no digits outside the item name/caliber; no enum vocabulary; real register.
- Engine-agnostic: zero engine references in `resolver/`.
- Suite baseline: `python -m pytest -q` → **340 passed** before this plan; **348 passed** after Task 3 (parametrized tests grow with the catalog).

---

### Task 1: Draft review document + user editorial checkpoint

**Files:**
- Create: `<session scratchpad>/cloud-editorial-review.md` (scratchpad only — NOT committed, never `git add`ed)

**Interfaces:**
- Produces: the approved prose for Tasks 2 and 3. Every association line and hook line in those tasks is a draft until this checkpoint approves or amends it.

**This task is user-interactive and must run inline (never in a subagent), regardless of which execution mode drives the rest of the plan.**

- [ ] **Step 1: Write the review document to the scratchpad**

Write exactly this content (it is the full draft — four item clouds + six ammo hooks):

```markdown
# Item-Cloud Editorial Pass — prose for red-pen review

Mechanics (roles/tags/delivery/base use) are locked by the approved spec;
only the prose below is up for edit. Conventions: 3–5 lines, obvious →
non-obvious → chainable-last, no digits, no schema words, real register.

## New item clouds

### firefighter turnout coat  (worn; protective; shrug-off)
1. a firefighter's turnout coat, scorched but intact
2. heat that would blister bare skin just warms it through
3. heavy canvas and reflective stripes turn a glancing hit into a shove
4. wearing it, your own fire is just weather

### battery boombox  (placed; loud; blast)
1. a battered boombox that runs on fat batteries
2. cranked to full, it's a wall of sound you can carry
3. set playing in an empty room, it makes that room the interesting one
4. whatever hunts by ear goes to the music, not to you

### cooler of raw steaks  (substance; slippery; bait)
1. a cooler of raw steaks, past cold and starting to turn
2. the smell carries further than you'd like
3. underfoot the fat is slick as soap
4. a trail of it leads anything hungry exactly where you want it standing

### case of energy drinks  (drunk; stimulant + liquid; chug)
1. a case of neon energy drinks, warm and shaken
2. two cans in, your hands move before your thoughts finish
3. the shakes show up later and bill you for the speed
4. spilled, they leave a sticky sheet that loves a live wire

## Ammo hook lines (one added per cloud; the two dry lines stay)

- .22 rounds — spilled by the boxful, they're brass gravel — loud and treacherous underfoot
- 9mm rounds — one round wedged in a track or hinge stops the whole mechanism cold
- .357 rounds — heavy for their size; a sock-load of them swings like a blackjack
- 5.56 rounds — rattled in a steel can, they pass for gunfire from a street away
- 12-gauge shells — cut open, each shell spills a palmful of shot for anything that needs pellets
- .30-06 rounds — a full box is a dense brass brick — ballast, doorstop, counterweight
```

- [ ] **Step 2: Present the document to the user and wait for the red-pen (HARD GATE)**

Show the full text in the conversation (don't just name the file) and ask the user to approve or amend each cloud and each hook line. Do not proceed to Task 2 until the user has responded. Record any amendments — the amended text replaces the corresponding draft lines in Tasks 2 and 3 verbatim.

---

### Task 2: Land the six ammo hook lines (TDD)

**Files:**
- Modify: `resolver/items.py:587-628` (the six real-ammo `Item` entries)
- Test: `tests/test_associations.py:49-54` (`_expected_line_range`)

**Interfaces:**
- Consumes: approved hook-line text from Task 1.
- Produces: six 3-line ammo clouds; `_expected_line_range` returns `(2, 3)` for `Flag.AMMUNITION`.

Note on step order: the range change `(1, 2) → (2, 3)` is a *widening*, so editing the test first cannot go red. Instead we add the lines first to prove the existing pin catches the change (red), then widen the pin (green).

- [ ] **Step 1: Add one hook line to each real-ammo cloud in `resolver/items.py`**

Each edit appends one line as the *last* line of the cloud (chainable-last ordering). Exact edits (use Task-1-approved text if amended):

`.22 rounds` — replace:
```python
             "a box of .22 rounds",
             "inert until a matching firearm feeds them",
         ),
```
with:
```python
             "a box of .22 rounds",
             "inert until a matching firearm feeds them",
             "spilled by the boxful, they're brass gravel — loud and treacherous underfoot",
         ),
```

`9mm rounds` — replace:
```python
             "a box of 9mm rounds",
             "inert until a matching firearm feeds them",
         ),
```
with:
```python
             "a box of 9mm rounds",
             "inert until a matching firearm feeds them",
             "one round wedged in a track or hinge stops the whole mechanism cold",
         ),
```

`.357 rounds` — replace:
```python
             "a box of .357 rounds",
             "inert until a matching revolver feeds them",
         ),
```
with:
```python
             "a box of .357 rounds",
             "inert until a matching revolver feeds them",
             "heavy for their size; a sock-load of them swings like a blackjack",
         ),
```

`5.56 rounds` — replace:
```python
             "a box of 5.56 rounds",
             "inert until a matching rifle feeds them",
         ),
```
with:
```python
             "a box of 5.56 rounds",
             "inert until a matching rifle feeds them",
             "rattled in a steel can, they pass for gunfire from a street away",
         ),
```

`12-gauge shells` — replace:
```python
             "a box of 12-gauge shells",
             "inert until a matching shotgun feeds them",
         ),
```
with:
```python
             "a box of 12-gauge shells",
             "inert until a matching shotgun feeds them",
             "cut open, each shell spills a palmful of shot for anything that needs pellets",
         ),
```

`.30-06 rounds` — replace:
```python
             "a box of .30-06 rounds",
             "inert until a matching rifle feeds them",
         ),
```
with:
```python
             "a box of .30-06 rounds",
             "inert until a matching rifle feeds them",
             "a full box is a dense brass brick — ballast, doorstop, counterweight",
         ),
```

(No digits in any hook line once the item name and caliber are stripped — the digit test checks exactly this.)

- [ ] **Step 2: Run the association tests to verify the pin catches the change (red)**

Run: `python -m pytest tests/test_associations.py -q`
Expected: 6 FAILED — one per ammo item, message like `.22 rounds: 3 lines, expected 1-2`.

- [ ] **Step 3: Widen the ammo line-range pin**

In `tests/test_associations.py`, replace:
```python
    if Flag.AMMUNITION in item.flags:
        return (1, 2)
```
with:
```python
    if Flag.AMMUNITION in item.flags:
        return (2, 3)
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: **340 passed** (no test-count change; the six clouds now sit at 3 lines inside the widened range).

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py tests/test_associations.py
git commit -m "feat: ammo hook lines - one non-fire improvisation per real-ammo cloud

Partially reverses the 2026-07-12 ammo-dryness decision on pre30 evidence
(cook-off convergence). Inert-until-fed framing stays; hooks are non-fire.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Land the four new items (TDD)

**Files:**
- Modify: `tests/test_items.py:9` (catalog size pin 61 → 65)
- Modify: `tests/test_associations.py:22-46` (batch tuples)
- Modify: `tests/test_base_use.py:15-106` (`EXPECTED` + `JUDGMENT_CALLS`)
- Modify: `tests/test_validate.py:20-21` (stale dormancy comment — comment only)
- Modify: `resolver/items.py` (three insertion points, given below)

**Interfaces:**
- Consumes: approved cloud text from Task 1; `Item`/`BaseUse` dataclasses and the `M, SUB` role aliases already defined in `resolver/items.py:53`.
- Produces: `CATALOG` with 65 items, including the catalog's first SELF+`protective` item (activates the ON_HIT self-kit path in `resolver/validate.py` with zero code change).

- [ ] **Step 1: Update the test pins to expect the four new items (red)**

**`tests/test_items.py`** — replace:
```python
    assert len(CATALOG) == 61
```
with:
```python
    assert len(CATALOG) == 65
```

**`tests/test_associations.py`** — replace:
```python
    "adrenaline shot", "first-aid kit",
)
```
with:
```python
    "adrenaline shot", "first-aid kit",
    "firefighter turnout coat", "battery boombox",
)
```
and replace:
```python
    "box of nails", "tin of ball bearings", "bag of marbles", "bag of gravel",
)
```
with:
```python
    "box of nails", "tin of ball bearings", "bag of marbles", "bag of gravel",
    "cooler of raw steaks", "case of energy drinks",
)
```

**`tests/test_base_use.py`** — replace:
```python
    "road flare": (D.THROWN, E.BURN, False),
    "propane tank": (D.THROWN, E.DAMAGE, False),
}
```
with:
```python
    "road flare": (D.THROWN, E.BURN, False),
    "propane tank": (D.THROWN, E.DAMAGE, False),
    # 2026-07-19 editorial pass
    "firefighter turnout coat": (D.SELF, E.SHIELD, False),
    "battery boombox": (D.PLACED, E.LURE, False),
    "cooler of raw steaks": (D.PLACED, E.LURE, False),
    "case of energy drinks": (D.SELF, E.SPEED, False),
}
```
and replace:
```python
    "propane tank": E.DAMAGE,          # refinement 4: steel doesn't burst when thrown
}
```
with:
```python
    "propane tank": E.DAMAGE,          # refinement 4: steel doesn't burst when thrown
    "cooler of raw steaks": E.LURE,    # the meat is bait; 'slippery' slick is the byproduct
}
```
(The steaks are a judgment call on purpose: `slippery` derives SLOW, but the base use is the lure — the governing-rule test requires the entry.)

**`tests/test_validate.py`** — replace:
```python
# the dormant gate: no catalog SELF item is protective yet (riot shield locks
# GUARD), so the reactive rule is exercised with a fabricated worn-vest fixture
```
with:
```python
# the reactive rule is exercised with a fabricated worn-vest fixture so these
# tests stay independent of catalog contents (since the 2026-07-19 editorial
# pass, the firefighter turnout coat carries SELF + protective in the catalog)
```

- [ ] **Step 2: Run the suite to verify the pins fail (red)**

Run: `python -m pytest tests/test_items.py tests/test_associations.py tests/test_base_use.py -q`
Expected: FAILURES —
- `test_catalog_is_the_reimagined_slice`: `61 == 65` assertion fails
- `test_batches_cover_the_whole_catalog`: covered set ≠ catalog
- 4 × `test_contact_batch_cloud_shape`/`test_substance_batch_cloud_shape`: `KeyError` on the new names
- `test_expected_covers_the_catalog_exactly`: `set(EXPECTED) != set(CATALOG)`
- 4 × `test_base_use_matches_the_spec[...]`: `KeyError` on the new names
- `test_governing_rule_effect_is_derivable_or_adjudicated`: `set(JUDGMENT_CALLS) <= set(CATALOG)` fails (steaks entry precedes the item)

- [ ] **Step 3: Add the four items to `resolver/items.py` (green)**

Three insertions, keeping section layering. Use Task-1-approved prose verbatim if amended.

**Insertion A — after `airhorn` (Layer 1 · Mechanism · Placed).** Anchor: the airhorn entry's closing lines at `resolver/items.py:356-358`:
```python
         roles=frozenset({M}), verb="blare",
         tags=frozenset({"loud"}), delivery=Delivery.PLACED,
         base_use=BaseUse(Delivery.PLACED, EffectKind.LURE)),
```
Insert immediately after:
```python
    Item("battery boombox",
         associations=(
             "a battered boombox that runs on fat batteries",
             "cranked to full, it's a wall of sound you can carry",
             "set playing in an empty room, it makes that room the interesting one",
             "whatever hunts by ear goes to the music, not to you",
         ),
         roles=frozenset({M}), verb="blast",
         tags=frozenset({"loud"}), delivery=Delivery.PLACED,
         base_use=BaseUse(Delivery.PLACED, EffectKind.LURE)),
```

**Insertion B — after `first-aid kit` (Layer 1 · Mechanism · Self / mobility).** Anchor: the first-aid kit entry's closing line at `resolver/items.py:390`:
```python
         base_use=BaseUse(Delivery.SELF, EffectKind.HEAL)),
```
Insert immediately after (both items, in this order):
```python
    Item("firefighter turnout coat",
         associations=(
             "a firefighter's turnout coat, scorched but intact",
             "heat that would blister bare skin just warms it through",
             "heavy canvas and reflective stripes turn a glancing hit into a shove",
             "wearing it, your own fire is just weather",
         ),
         roles=frozenset({M}), verb="shrug-off",
         tags=frozenset({"protective"}), delivery=Delivery.SELF,
         base_use=BaseUse(Delivery.SELF, EffectKind.SHIELD)),
    Item("case of energy drinks",
         associations=(
             "a case of neon energy drinks, warm and shaken",
             "two cans in, your hands move before your thoughts finish",
             "the shakes show up later and bill you for the speed",
             "spilled, they leave a sticky sheet that loves a live wire",
         ),
         roles=frozenset({M, SUB}), verb="chug",
         tags=frozenset({"stimulant", "liquid"}), delivery=Delivery.SELF,
         base_use=BaseUse(Delivery.SELF, EffectKind.SPEED)),
```

**Insertion C — after `crate of overripe produce` (end of the substances layer, just before the real-ammo section).** Anchor: the crate entry's closing lines at `resolver/items.py:582-584`:
```python
         roles=frozenset({SUB}), verb="gum-up",
         tags=frozenset({"slippery", "sticky"}),
         base_use=BaseUse(Delivery.THROWN, EffectKind.SLOW)),
```
Insert immediately after:
```python
    Item("cooler of raw steaks",
         associations=(
             "a cooler of raw steaks, past cold and starting to turn",
             "the smell carries further than you'd like",
             "underfoot the fat is slick as soap",
             "a trail of it leads anything hungry exactly where you want it standing",
         ),
         roles=frozenset({SUB}), verb="bait",
         tags=frozenset({"slippery"}),
         base_use=BaseUse(Delivery.PLACED, EffectKind.LURE)),
```

Notes for the implementer:
- No `flags`, no `caliber` on any of the four; `armed` stays default `False`.
- The steaks have **no** `delivery=` — they are a substance whose base use supplies PLACED (mirrors the improvised-ammo pattern); `test_mechanism_base_delivery_matches_its_craft_form` only checks items where `delivery` is set.
- All tags already exist in the taxonomy (`protective`, `loud`, `slippery`, `stimulant`, `liquid`) — do NOT touch `resolver/interactions.py`.

- [ ] **Step 4: Run the full suite (green)**

Run: `python -m pytest -q`
Expected: **348 passed** (340 baseline + 4 new `test_base_use_matches_the_spec` params + 4 new cloud-shape params). Zero failures — in particular `test_bake_select.py::test_every_catalog_item_is_covered` passes untouched (selection has a per-item coverage loop) and `test_solo.py` passes untouched (all four items carry a base use).

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py tests/test_items.py tests/test_associations.py tests/test_base_use.py tests/test_validate.py
git commit -m "feat: 4 new catalog items - turnout coat, boombox, steaks, energy drinks

Turnout coat (SELF + protective) wakes the dormant ON_HIT self-kit path with
zero resolver changes; boombox + steaks feed pure-LURE (UTILITY), coat +
drinks feed SUPPORT. Catalog 61 -> 65. No enum or taxonomy changes.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Not in this plan (per spec)

The 300-combo pilot (HELD), any live API call, prompt/contract changes, combo-selection changes, the full-catalog cloud re-read, ON_KILL rider filler, name-style dedup, further catalog expansion. `data/bake/combos-pilot.json` is untouched and stays uncommitted.
