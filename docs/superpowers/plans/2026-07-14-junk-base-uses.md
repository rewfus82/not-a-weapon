# Junk Base Uses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every catalog item gains a solo base use (delivery + effect + armed flag) consistent with its verb/tags; containerized substances are renamed and throwable; the blender becomes the industrial fan; the airhorn joins; any non-ammo item can be a delivery chassis; solo uses resolve at the DUD floor through the existing clamp.

**Architecture:** A `BaseUse` value object on `Item` (separate from the mechanism `delivery` field), a full 61-item enumeration pinned by tests, a `Build.delivery` fallback through `base_use.delivery`, a new `resolver/solo.py` for floor-tier solo resolution, and a small stage-shape extension in `fallback.py` for thrown-burst / armed-patch chassis. No enum changes anywhere.

**Tech Stack:** Python 3.13, dataclasses, pydantic (existing contract models), pytest.

**Spec:** `docs/superpowers/specs/2026-07-13-junk-base-use-design.md`

## Global Constraints

- **Never widen the enums** (`Delivery`, `EffectKind`, `Trigger`, `Category`, `Tier`, `Role`, `Flag` in `resolver/contract.py`). Zero contract changes in this plan.
- **Code owns every number.** Solo magnitudes come from the existing clamp at `Tier.DUD`; never rolled, never model-supplied.
- **Engine-agnostic:** zero engine references in `resolver/`.
- **Keep the suite green at every commit.** Baseline is 95 tests; each task adds or updates tests and must end green.
- Run tests with: `python -m pytest -q` from the repo root.
- Commit per task, conventional messages, ending with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Do NOT touch `docs/HANDOFF.md` (has uncommitted user edits), `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`, or the 2026-07-10 plan/spec files.
- Association-cloud *content* for renamed items is a separate queued pass. This plan only keeps cloud *shape* tests green (new items get real but placeholder-status clouds; renamed items keep their existing clouds verbatim).

---

### Task 1: Container renames (15 items)

Pure rename refactor: the item names change; associations, tags, verbs, roles stay byte-identical. Update every reference in code and tests, then rename in the catalog.

**Files:**
- Modify: `resolver/items.py` (15 `Item("...")` name strings + 1 `DEFAULT_BUILDS` reference)
- Modify: `resolver/harness.py` (5 `CATALOG[...]` keys in `PROBE_BUILDS`)
- Modify: `tests/test_associations.py` (batch tuples)
- Modify: `tests/test_serve.py` (name literals)

**Interfaces:**
- Produces: the 15 new catalog keys used by every later task, exactly:

| Old name | New name |
|---|---|
| `gasoline` | `jerrycan of gasoline` |
| `motor oil` | `jug of motor oil` |
| `thermite` | `jar of thermite` |
| `fertilizer` | `sack of fertilizer` |
| `bleach` | `jug of bleach` |
| `ammonia cleaner` | `jug of ammonia cleaner` |
| `pool chlorine` | `tub of pool chlorine` |
| `liquid nitrogen` | `dewar of liquid nitrogen` |
| `wet cement` | `bucket of wet cement` |
| `overripe produce` | `crate of overripe produce` |
| `expanding foam` | `can of expanding foam` |
| `hairspray` | `can of hairspray` |
| `dry ice` | `block of dry ice` |
| `marbles` | `bag of marbles` |
| `ball bearings` | `tin of ball bearings` |

- [ ] **Step 1: Update the test name lists (failing first)**

In `tests/test_associations.py`, apply the table to the batch tuples. `BATCH_MODIFIERS` gains the fertilizer rename:

```python
BATCH_MODIFIERS: tuple[str, ...] = (
    "propane tank", "sack of fertilizer", "car battery", "jumper cables",
    "defibrillator", "taser",
)
```

In `BATCH_SUBSTANCES`, replace the renamed entries in place (order preserved):

```python
BATCH_SUBSTANCES: tuple[str, ...] = (
    "jerrycan of gasoline", "jug of motor oil", "jar of thermite",
    "road flare", "can of hairspray",
    "tub of pool chlorine", "jug of ammonia cleaner", "jug of bleach",
    "dewar of liquid nitrogen",
    "block of dry ice", "bucket of wet cement", "can of expanding foam",
    "crate of overripe produce",
    ".22 rounds", "9mm rounds", ".357 rounds", "5.56 rounds",
    "12-gauge shells", ".30-06 rounds",
    "box of nails", "tin of ball bearings", "bag of marbles", "bag of gravel",
)
```

In `tests/test_serve.py`, update the two `gasoline` literals:

```python
    assert {"baseball bat", "m16 rifle", "blender", "jerrycan of gasoline"} <= names
```
```python
    assert by_name["jerrycan of gasoline"]["delivery"] is None  # payload-only
```
```python
        serve.build_from_request({"delivery": "jerrycan of gasoline"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_associations.py tests/test_serve.py -q`
Expected: FAIL with `KeyError` on the new names (catalog still has old names).

- [ ] **Step 3: Rename in the catalog and harness**

In `resolver/items.py`, change only the first argument of each affected `Item(...)` per the table (e.g. `Item("gasoline",` → `Item("jerrycan of gasoline",`). Associations and all other fields stay untouched. Then update the `DEFAULT_BUILDS` reference:

```python
        utility_item=CATALOG["crate of overripe produce"],
```

In `resolver/harness.py` `PROBE_BUILDS`, update the five keys:

```python
        damage_item=CATALOG["jerrycan of gasoline"],
```
```python
        damage_item=CATALOG["tub of pool chlorine"],
```
```python
        damage_item=CATALOG["bag of marbles"],
        utility_item=CATALOG["can of expanding foam"],
```
```python
        utility_item=CATALOG["jug of motor oil"],
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: 95 passed.

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py resolver/harness.py tests/test_associations.py tests/test_serve.py
git commit -m "refactor: rename containerized substances to show the container

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Blender → industrial fan; bananarama → swamp_cooler

The blender fails the governing rule (no honest solo use) and is replaced by the industrial fan, a PLACED wind mechanism. The `bananarama` exemplar build referenced the blender; its replacement must stay in the **middle coherence band (C = 2/3)** or the router tests change meaning. Verified against `interactions.py`: fan{wind, electrical} + car battery{electrical, heavy, corrosive} + garden hose{liquid} has edges fan–battery (shared `electrical`) and battery–hose (`electrical`+`liquid` pair), no fan–hose edge → C = 2/3, same band as before. (Fan + battery + produce would be C = 1/3 and silently change the router's test coverage — do not use it.)

**Files:**
- Modify: `resolver/items.py` (swap the Item; rebuild the exemplar)
- Modify: `resolver/harness.py` (`probe_whimsical` chassis)
- Modify: `tests/test_associations.py` (BATCH_RANGED)
- Modify: `tests/test_items.py`, `tests/test_fallback.py`, `tests/test_router.py`, `tests/test_coherence.py`, `tests/test_harness.py`, `tests/test_llm.py`, `tests/test_serve.py` (key/name updates)

**Interfaces:**
- Produces: catalog key `"industrial fan"` (roles `{MECHANISM}`, verb `"blow"`, tags `{"wind", "electrical"}`, `delivery=Delivery.PLACED`); `DEFAULT_BUILDS["swamp_cooler"]` replacing `"bananarama"`.

- [ ] **Step 1: Update tests (failing first)**

`tests/test_associations.py` — in `BATCH_RANGED`, replace `"blender"` with `"industrial fan"`.

`tests/test_items.py` — update the default-builds set:

```python
def test_default_builds_span_grounded_and_absurd():
    assert set(DEFAULT_BUILDS) == {"broom_bat", "gun_ammo", "swamp_cooler"}
```

(The local `Item("blender", ...)` in `test_item_describe_falls_back_to_verb_and_tags` constructs its own item and is unaffected — leave it.)

`tests/test_serve.py` — replace `"blender"` with `"industrial fan"` in the payload-names assertion.

`tests/test_router.py`, `tests/test_coherence.py`, `tests/test_harness.py`, `tests/test_llm.py`, `tests/test_serve.py` — replace every `DEFAULT_BUILDS["bananarama"]` / `"bananarama"` build-key string with `"swamp_cooler"`, and update comments that say "bananarama" to "swamp_cooler". The router band comments stay true (C is still 2/3).

`tests/test_fallback.py` — the swamp_cooler tag union is `{wind, electrical, heavy, corrosive, liquid}` → base chain `[BURN, CHAIN, KNOCKBACK]` (pairs `corrosive+liquid`→BURN, `electrical+liquid`→CHAIN; singles `heavy`/`wind`→KNOCKBACK deduped). Replace the two bananarama-specific tests and update the other two key references:

```python
def test_swamp_cooler_yields_its_tag_derived_effects():
    # corrosive+liquid -> BURN, electrical+liquid -> CHAIN; RARE takes the full chain
    draft = fallback.resolve(DEFAULT_BUILDS["swamp_cooler"], Tier.RARE)
    assert draft.stages[0].trigger is Trigger.ON_HIT
    assert EffectKind.BURN in _kinds(draft)
    assert EffectKind.CHAIN in _kinds(draft)

def test_no_duplicate_effect_kinds_within_a_stage():
    # car battery's electrical overlay (CHAIN) must not duplicate the
    # electrical+liquid base CHAIN already in the chain
    draft = fallback.resolve(DEFAULT_BUILDS["swamp_cooler"], Tier.RARE)
    for stage in draft.stages:
        kinds = [e.kind for e in stage.effects]
        assert len(kinds) == len(set(kinds))
```

(`test_higher_tier_unlocks_more_effects` keeps its logic; just swap the key.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest -q`
Expected: FAIL — `KeyError: 'industrial fan'` / `KeyError: 'swamp_cooler'`.

- [ ] **Step 3: Swap the item and rebuild the exemplar**

In `resolver/items.py`, replace the entire `Item("blender", ...)` block (Stream section) with:

```python
    Item("industrial fan",
         associations=(
             "a man-high drum fan on a rolling frame",
             "kicks out a steady lane of wind that shoves loose junk downrange",
             "planted in a doorway, nothing light gets through against the airflow",
             "anything airborne — mist, powder, fog, sparks — rides the lane to the far end",
         ),
         roles=frozenset({M}), verb="blow",
         tags=frozenset({"wind", "electrical"}), delivery=Delivery.PLACED),
```

Replace the `"bananarama"` entry in `DEFAULT_BUILDS`:

```python
    # absurd: the Swamp Cooler — placed wind lane + shock modifier + water feed
    "swamp_cooler": Build(
        delivery_item=CATALOG["industrial fan"],
        modifier_item=CATALOG["car battery"],
        utility_item=CATALOG["garden hose"],
    ),
```

In `resolver/harness.py`, update `probe_whimsical`:

```python
    "probe_whimsical": Build(
        delivery_item=CATALOG["industrial fan"],
        damage_item=CATALOG["bag of marbles"],
        utility_item=CATALOG["can of expanding foam"],
    ),
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: 95 passed. (`test_every_delivery_form_has_a_mechanism_carrier` still holds: SPRAY keeps extinguisher/hose/shotgun carriers; PLACED now has bear trap + fan.)

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py resolver/harness.py tests/
git commit -m "feat: industrial fan replaces blender; swamp_cooler exemplar (C=2/3 preserved)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Add the airhorn

**Files:**
- Modify: `resolver/items.py` (new Item in the Placed section)
- Modify: `tests/test_associations.py` (BATCH_CONTACT)
- Modify: `tests/test_items.py` (catalog count pinned to 61)

**Interfaces:**
- Produces: catalog key `"airhorn"` (roles `{MECHANISM}`, verb `"blare"`, tags `{"loud"}`, `delivery=Delivery.PLACED`).

- [ ] **Step 1: Update tests (failing first)**

`tests/test_associations.py` — append `"airhorn"` to `BATCH_CONTACT` (after `"bear trap"`).

`tests/test_items.py` — pin the count in the catalog test:

```python
def test_catalog_is_the_reimagined_slice():
    assert len(CATALOG) == 61
    for it in CATALOG.values():
        assert it.roles, f"{it.name} has no role"
        assert it.tags <= TAXONOMY, f"{it.name} has off-taxonomy tags: {it.tags - TAXONOMY}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_items.py tests/test_associations.py -q`
Expected: FAIL — catalog has 60 items; `KeyError: 'airhorn'`.

- [ ] **Step 3: Add the item**

In `resolver/items.py`, in the `Placed` section directly after the bear trap:

```python
    Item("airhorn",
         associations=(
             "a pocket air canister with a trumpet that makes ears ring",
             "one blast turns every head on the block",
             "wedge the button down and it screams until the can dies",
             "set it where you aren't, and everything comes running to where you aren't",
         ),
         roles=frozenset({M}), verb="blare",
         tags=frozenset({"loud"}), delivery=Delivery.PLACED),
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all passing (count test now green at 61).

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py tests/test_associations.py tests/test_items.py
git commit -m "feat: airhorn — placed noise decoy (PLACED + loud -> LURE)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `BaseUse` + the full 61-item enumeration + consistency tests

The heart of the design. `BaseUse` is a frozen value object on `Item`; a new test module pins the full enumeration and mechanically enforces the governing rule (solo effect derivable from the item's own tags via `effects_for`, or FIREARM→DAMAGE, or a **closed** judgment-call allowlist).

**Files:**
- Modify: `resolver/items.py` (BaseUse dataclass, `base_use` field, 55 per-item values)
- Test: `tests/test_base_use.py` (new)

**Interfaces:**
- Consumes: `effects_for(tags)` from `resolver/interactions.py` (existing).
- Produces: `BaseUse(delivery: Delivery, effect: EffectKind, armed: bool = False)` and `Item.base_use: BaseUse | None` — consumed by Tasks 5–7.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_base_use.py`:

```python
"""Pins the base-use enumeration (spec: 2026-07-13-junk-base-use-design.md)
and mechanically enforces the governing rule: an item's solo effect must be
derivable from its own tags, be the firearm default, or sit on the CLOSED
judgment-call list below. Adding to that list is a deliberate act.
"""
import pytest

from resolver.contract import Delivery, EffectKind, Flag
from resolver.interactions import effects_for
from resolver.items import CATALOG

D, E = Delivery, EffectKind

# name -> (base delivery, base effect, armed) | None (AMMUNITION only)
EXPECTED: dict[str, tuple[Delivery, EffectKind, bool] | None] = {
    # melee
    "crowbar": (D.SWING, E.DAMAGE, False),
    "sledgehammer": (D.SLAM, E.DAMAGE, False),
    "fire axe": (D.SWING, E.PIERCE, False),
    "machete": (D.SWING, E.PIERCE, False),
    "screwdriver": (D.THRUST, E.PIERCE, False),
    "baseball bat": (D.SWING, E.DAMAGE, False),
    "power drill": (D.THRUST, E.PIERCE, False),
    "angle grinder": (D.SWING, E.PIERCE, False),
    "chainsaw": (D.SWING, E.PIERCE, False),
    "weed whacker": (D.WHIP, E.DAMAGE, False),
    "riot shield": (D.GUARD, E.SHIELD, False),
    "nail gun": (D.PROJECTILE, E.PIERCE, False),
    # guns
    "m16 rifle": (D.HITSCAN, E.DAMAGE, False),
    ".22 pistol": (D.HITSCAN, E.DAMAGE, False),
    "9mm pistol": (D.HITSCAN, E.DAMAGE, False),
    "revolver": (D.HITSCAN, E.DAMAGE, False),
    ".30-06 hunting rifle": (D.HITSCAN, E.DAMAGE, False),
    "pump shotgun": (D.SPRAY, E.DAMAGE, False),
    # real ammo: the named exception — no base use
    ".22 rounds": None,
    "9mm rounds": None,
    ".357 rounds": None,
    "5.56 rounds": None,
    "12-gauge shells": None,
    ".30-06 rounds": None,
    # ranged mechanisms
    "fire extinguisher": (D.SPRAY, E.FREEZE, False),
    "pressure washer": (D.BEAM, E.KNOCKBACK, False),
    "garden hose": (D.SPRAY, E.KNOCKBACK, False),
    "roman candle": (D.LOBBED, E.BURN, False),
    "salvaged laser cutter": (D.BEAM, E.BURN, False),
    "glass bottle": (D.THROWN, E.PIERCE, False),
    "cinder block": (D.THROWN, E.DAMAGE, False),
    "t-shirt cannon": (D.LOBBED, E.STAGGER, False),
    "industrial fan": (D.PLACED, E.KNOCKBACK, False),
    # placed & scatter
    "bear trap": (D.PLACED, E.SNARE, False),
    "airhorn": (D.PLACED, E.LURE, False),
    "box of nails": (D.PLACED, E.PIERCE, False),
    "tin of ball bearings": (D.THROWN, E.DAMAGE, False),
    "bag of marbles": (D.PLACED, E.SLOW, False),
    "bag of gravel": (D.THROWN, E.DAMAGE, False),
    # self-use & electrical
    "leaf blower": (D.DASH, E.KNOCKBACK, False),
    "adrenaline shot": (D.SELF, E.SPEED, False),
    "first-aid kit": (D.SELF, E.HEAL, False),
    "taser": (D.THRUST, E.STAGGER, False),
    "defibrillator": (D.THRUST, E.DAMAGE, False),
    "jumper cables": (D.THRUST, E.SNARE, False),
    "car battery": (D.THROWN, E.DAMAGE, False),
    # containers & substances
    "jerrycan of gasoline": (D.THROWN, E.BURN, True),
    "jar of thermite": (D.THROWN, E.BURN, True),
    "sack of fertilizer": (D.THROWN, E.BURN, True),
    "jug of motor oil": (D.THROWN, E.SLOW, False),
    "jug of bleach": (D.THROWN, E.BURN, False),
    "jug of ammonia cleaner": (D.THROWN, E.BURN, False),
    "tub of pool chlorine": (D.THROWN, E.BURN, False),
    "dewar of liquid nitrogen": (D.THROWN, E.FREEZE, False),
    "bucket of wet cement": (D.THROWN, E.SNARE, False),
    "crate of overripe produce": (D.THROWN, E.SLOW, False),
    "can of expanding foam": (D.SPRAY, E.SNARE, False),
    "can of hairspray": (D.SPRAY, E.SNARE, False),
    "block of dry ice": (D.PLACED, E.FREEZE, False),
    "road flare": (D.THROWN, E.BURN, False),
    "propane tank": (D.THROWN, E.DAMAGE, False),
}

# CLOSED allowlist: items whose solo effect is a documented judgment call,
# not tag-derivable. Each entry names its justification.
JUDGMENT_CALLS: dict[str, EffectKind] = {
    "weed whacker": E.DAMAGE,          # 'long-reach' has no single-tag effect
    "pressure washer": E.KNOCKBACK,    # 'liquid' unmapped; the jet shoves
    "garden hose": E.KNOCKBACK,        # 'liquid' unmapped; weak push + soak
    "salvaged laser cutter": E.BURN,   # 'light-source'->LURE is wrong for a cutter
    "glass bottle": E.PIERCE,          # 'brittle' unmapped; shard burst
    "t-shirt cannon": E.STAGGER,       # empty-launcher near-dud pop
    "bear trap": E.SNARE,              # holding is the point, not the PIERCE bite
    "tin of ball bearings": E.DAMAGE,  # thrown weights, not knockback
    "bag of gravel": E.DAMAGE,         # 'scatter' unmapped; stinging wave
    "taser": E.STAGGER,                # solo locks muscles; CHAIN is craft behavior
    "defibrillator": E.DAMAGE,         # one big timed dump
    "jumper cables": E.SNARE,          # the clamps bite and hold
    "car battery": E.DAMAGE,           # refinement 3: common-knowledge carve-out
    "can of hairspray": E.SNARE,       # sticky mist lives in associations, not tags
    "jar of thermite": E.BURN,         # burns through steel; tag pair says EXPLODE
    "sack of fertilizer": E.BURN,      # fast mean burn; tag pair says EXPLODE
    "propane tank": E.DAMAGE,          # refinement 4: steel doesn't burst when thrown
}


def test_expected_covers_the_catalog_exactly():
    assert set(EXPECTED) == set(CATALOG)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_base_use_matches_the_spec(name):
    item, exp = CATALOG[name], EXPECTED[name]
    if exp is None:
        assert Flag.AMMUNITION in item.flags, f"{name}: only ammo may lack a base use"
        assert item.base_use is None
        return
    bu = item.base_use
    assert bu is not None, f"{name} has no base use"
    assert (bu.delivery, bu.effect, bu.armed) == exp


def test_governing_rule_effect_is_derivable_or_adjudicated():
    for item in CATALOG.values():
        bu = item.base_use
        if bu is None:
            continue
        if item.name in JUDGMENT_CALLS:
            assert bu.effect is JUDGMENT_CALLS[item.name], item.name
        elif Flag.FIREARM in item.flags:
            assert bu.effect is EffectKind.DAMAGE, item.name
        else:
            assert bu.effect in effects_for(item.tags), (
                f"{item.name}: {bu.effect} not derivable from {sorted(item.tags)}"
            )


def test_mechanism_base_delivery_matches_its_craft_form():
    # the crowbar swings both ways: solo form == the FORM it locks in a craft
    for item in CATALOG.values():
        if item.base_use is not None and item.delivery is not None:
            assert item.base_use.delivery is item.delivery, item.name


def test_armed_is_exactly_the_ignition_gated_payloads():
    armed = {it.name for it in CATALOG.values() if it.base_use and it.base_use.armed}
    assert armed == {"jerrycan of gasoline", "jar of thermite", "sack of fertilizer"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_base_use.py -q`
Expected: FAIL — `Item` has no attribute `base_use` (AttributeError/ImportError).

- [ ] **Step 3: Add `BaseUse` and the field**

In `resolver/items.py`, extend the contract import and add the dataclass above `Item`:

```python
from resolver.contract import Delivery, EffectKind, Role, Flag, MELEE_DELIVERIES
```

```python
@dataclass(frozen=True)
class BaseUse:
    """The solo action an item performs with no craft: one delivery, one
    effect — the same behavior it contributes to a craft (the governing
    rule). `armed=True` marks a payload inert until ignited (its patch
    fires on ON_TRIGGER, not on impact)."""
    delivery: Delivery
    effect: EffectKind
    armed: bool = False
```

Add the field to `Item` (after `flags`):

```python
    base_use: BaseUse | None = None
```

- [ ] **Step 4: Author all 55 base uses**

Add `base_use=BaseUse(...)` to every non-ammo `Item(...)` in `_ITEMS`, copying (delivery, effect, armed) exactly from the `EXPECTED` table in Step 1. Pattern (taser shown — this is also the latent-bug fix, via `base_use`, NOT via `Item.delivery`, which stays `None` because the taser is not a craft mechanism):

```python
    Item("taser",
         associations=(
             "a palm-sized stunner with a crackling arc between two prongs",
             "the arc snaps and pops even before it touches anything",
             "a touch locks up whatever muscle it finds",
             "held against metal or wet ground, the crackle keeps traveling",
         ),
         roles=frozenset({MOD, SUB}), verb="stun",
         tags=frozenset({"electrical"}), flags=frozenset({WIELD}),
         base_use=BaseUse(Delivery.THRUST, EffectKind.STAGGER)),
```

Armed example (jerrycan):

```python
         base_use=BaseUse(Delivery.THROWN, EffectKind.BURN, armed=True)),
```

The six ammo items get no `base_use` (default `None`).

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: all passing, including the 65+ new parametrized assertions.

- [ ] **Step 6: Commit**

```bash
git add resolver/items.py tests/test_base_use.py
git commit -m "feat: BaseUse — every item's solo action, pinned for all 61 items

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `Build.delivery` falls back through `base_use`; serve follows

Removes the "must bring a chassis" restriction: any non-ammo item can be a delivery chassis. The ValueError survives only for true no-use items (ammo).

**Files:**
- Modify: `resolver/items.py` (`Build.delivery` property)
- Modify: `resolver/serve.py` (`build_from_request` guard)
- Modify: `tests/test_items.py`, `tests/test_serve.py`

**Interfaces:**
- Consumes: `Item.base_use` (Task 4).
- Produces: `Build.delivery` resolving for substance chassis (e.g. jerrycan → `Delivery.THROWN`) — consumed by Tasks 6–7.

- [ ] **Step 1: Update/add tests (failing first)**

`tests/test_items.py` — replace `test_build_rejects_non_delivery_chassis` with:

```python
def test_build_rejects_only_baseless_chassis():
    # ammo is the one class with no base use — still not a chassis
    ammo = CATALOG[".22 rounds"]
    with pytest.raises(ValueError):
        _ = Build(delivery_item=ammo).delivery


def test_substance_chassis_resolves_via_base_use():
    # throw-the-container: the universal fallback build
    build = Build(delivery_item=CATALOG["jerrycan of gasoline"])
    assert build.delivery is Delivery.THROWN
```

`tests/test_serve.py` — replace `test_build_from_request_rejects_non_delivery_item_in_delivery_slot` with:

```python
def test_build_from_request_accepts_substance_chassis():
    build = serve.build_from_request({"delivery": "jerrycan of gasoline"})
    assert build.delivery_item.name == "jerrycan of gasoline"


def test_build_from_request_rejects_ammo_in_delivery_slot():
    with pytest.raises(ValueError):
        serve.build_from_request({"delivery": ".22 rounds"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_items.py tests/test_serve.py -q`
Expected: FAIL — jerrycan chassis raises ValueError from the old property/guard.

- [ ] **Step 3: Implement the fallback**

`resolver/items.py` — replace the `Build.delivery` property:

```python
    @property
    def delivery(self) -> Delivery:
        d = self.delivery_item.delivery
        if d is not None:
            return d
        bu = self.delivery_item.base_use
        if bu is None:
            raise ValueError(f"{self.delivery_item.name!r} cannot be a delivery chassis")
        return bu.delivery
```

`resolver/serve.py` — replace the guard in `build_from_request`:

```python
    if delivery_item.delivery is None and delivery_item.base_use is None:
        raise ValueError(f"{delivery_item.name!r} cannot be a delivery chassis")
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py resolver/serve.py tests/test_items.py tests/test_serve.py
git commit -m "feat: any non-ammo item can be a delivery chassis via its base use

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: `resolver/solo.py` — floor-tier solo resolution

Solo uses resolve through the existing clamp at `Tier.DUD`: fixed, code-owned, never rolled, strictly below crafted budgets.

**Files:**
- Create: `resolver/solo.py`
- Test: `tests/test_solo.py` (new)

**Interfaces:**
- Consumes: `Item.base_use` (Task 4), `Build.delivery` fallback (Task 5), `clamp.apply`, `fallback._TIER_SEED`.
- Produces: `solo_draft(item: Item) -> GadgetDraft`, `resolve_solo(item: Item) -> ResolvedGadget`, `BASE_USE_TIER: Tier`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_solo.py`:

```python
import pytest

from resolver.clamp import TIER_BUDGET, OVER_BUDGET_FACTOR
from resolver.contract import Category, Delivery, EffectKind, Flag, Tier, Trigger
from resolver.items import CATALOG
from resolver import solo


def test_taser_solo_zap_is_a_thrust_stagger():
    r = solo.resolve_solo(CATALOG["taser"])
    assert r.delivery is Delivery.THRUST
    kinds = {e.kind for s in r.draft.stages for e in s.effects}
    assert kinds == {EffectKind.STAGGER}
    assert r.tier is Tier.DUD


def test_armed_jerrycan_is_a_two_stage_patch():
    r = solo.resolve_solo(CATALOG["jerrycan of gasoline"])
    assert [s.trigger for s in r.draft.stages] == [Trigger.ON_IMPACT, Trigger.ON_TRIGGER]
    assert r.draft.stages[0].effects == []
    assert {e.kind for e in r.draft.stages[1].effects} == {EffectKind.BURN}


def test_placed_solo_triggers_on_step_in():
    r = solo.resolve_solo(CATALOG["bag of marbles"])
    assert r.draft.stages[0].trigger is Trigger.ON_TRIGGER
    assert r.delivery is Delivery.PLACED


def test_self_solo_uses_on_use_and_stays_support():
    r = solo.resolve_solo(CATALOG["first-aid kit"])
    assert r.draft.stages[0].trigger is Trigger.ON_USE
    assert r.harmless is True and r.category is Category.SUPPORT


def test_every_base_use_resolves_at_the_floor():
    # fixed magnitudes at the DUD floor: never zero, never past the DUD cap,
    # always below the cheapest real craft budget (COMMON)
    cap = TIER_BUDGET[Tier.DUD] * OVER_BUDGET_FACTOR
    for item in CATALOG.values():
        if Flag.AMMUNITION in item.flags:
            continue
        r = solo.resolve_solo(item)
        total = sum(e.amount for s in r.draft.stages for e in s.effects)
        assert 0 < total <= cap, item.name
        assert total < TIER_BUDGET[Tier.COMMON], item.name


def test_solo_is_deterministic():
    a = solo.resolve_solo(CATALOG["crowbar"])
    b = solo.resolve_solo(CATALOG["crowbar"])
    assert a.draft.model_dump() == b.draft.model_dump()


def test_ammo_has_no_solo_use():
    with pytest.raises(ValueError):
        solo.solo_draft(CATALOG[".22 rounds"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_solo.py -q`
Expected: FAIL — `ModuleNotFoundError: resolver.solo`.

- [ ] **Step 3: Implement the module**

Create `resolver/solo.py`:

```python
"""Base-use resolution: the solo action an item performs with no craft.

Magnitudes are code-owned and fixed at the floor: every solo use is a
DUD-strength single behavior, strictly below any crafted tier's budget
(the zero-risk act of picking something up never competes with crafting).
Armed payloads (inert until ignited) resolve as a two-stage patch using
existing triggers — no new vocabulary.
"""
from __future__ import annotations

from resolver.clamp import apply as clamp_apply
from resolver.contract import (
    Delivery, Effect, GadgetDraft, ResolvedGadget, Stage, Tier, Trigger,
)
from resolver.fallback import _TIER_SEED
from resolver.items import Build, Item

BASE_USE_TIER: Tier = Tier.DUD
_SOLO_SEED: float = _TIER_SEED[BASE_USE_TIER]

_TRIGGER_BY_DELIVERY: dict[Delivery, Trigger] = {
    Delivery.PLACED: Trigger.ON_TRIGGER,
    Delivery.SELF: Trigger.ON_USE,
    Delivery.DASH: Trigger.ON_USE,
}


def solo_draft(item: Item) -> GadgetDraft:
    bu = item.base_use
    if bu is None:
        raise ValueError(f"{item.name!r} has no base use")
    effect = Effect(kind=bu.effect, amount=_SOLO_SEED, note="base use")
    if bu.armed:
        stages = [
            Stage(trigger=Trigger.ON_IMPACT, effects=[], note="burst"),
            Stage(trigger=Trigger.ON_TRIGGER, effects=[effect], note="armed patch"),
        ]
    else:
        trigger = _TRIGGER_BY_DELIVERY.get(bu.delivery, Trigger.ON_HIT)
        stages = [Stage(trigger=trigger, effects=[effect], note="base use")]
    return GadgetDraft(
        name=item.name.title(),
        description=f"{item.name}, used as found.",
        logic=f"Base use: {bu.delivery.value} -> {bu.effect.value}.",
        stages=stages,
    )


def resolve_solo(item: Item) -> ResolvedGadget:
    return clamp_apply(solo_draft(item), Build(delivery_item=item), BASE_USE_TIER)
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all passing.

- [ ] **Step 5: Commit**

```bash
git add resolver/solo.py tests/test_solo.py
git commit -m "feat: solo resolution — base uses clamp at the DUD floor

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Fallback composer learns the thrown-burst / armed-patch chassis shapes

Crafted builds whose chassis resolves via `base_use` (substance containers) get burst-shaped stages: `ON_IMPACT` for immediate payloads, the two-stage armed patch for ignition-gated ones. Mechanism chassis keep today's `ON_HIT` shape. (Deliberately simple: armed-ness comes from the chassis alone; "the flare in the build self-ignites the patch" is future LLM-path nuance, not composer logic.)

**Files:**
- Modify: `resolver/fallback.py`
- Modify: `tests/test_fallback.py`

**Interfaces:**
- Consumes: `Item.base_use`, `Build.delivery` fallback.
- Produces: unchanged signature `resolve(build, tier) -> GadgetDraft`; new stage shapes for substance chassis.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_fallback.py`:

```python
def test_substance_chassis_composes_a_thrown_burst():
    draft = fallback.resolve(Build(delivery_item=CATALOG["bucket of wet cement"]), Tier.COMMON)
    assert draft.stages[0].trigger is Trigger.ON_IMPACT
    assert EffectKind.SNARE in _kinds(draft)


def test_armed_chassis_composes_the_two_stage_patch():
    draft = fallback.resolve(Build(delivery_item=CATALOG["jerrycan of gasoline"]), Tier.COMMON)
    assert [s.trigger for s in draft.stages] == [Trigger.ON_IMPACT, Trigger.ON_TRIGGER]
    assert draft.stages[0].effects == []


def test_mechanism_chassis_keeps_on_hit():
    draft = fallback.resolve(DEFAULT_BUILDS["broom_bat"], Tier.COMMON)
    assert draft.stages[0].trigger is Trigger.ON_HIT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fallback.py -q`
Expected: the two new substance-chassis tests FAIL (stages are `ON_HIT` today); `test_mechanism_chassis_keeps_on_hit` passes.

- [ ] **Step 3: Implement the stage shapes**

In `resolver/fallback.py`, add after `_overlays`:

```python
def _stages_for(build: Build, effects: list[Effect]) -> list[Stage]:
    """Mechanism chassis hit (ON_HIT); a substance chassis is a thrown
    container that bursts (ON_IMPACT) — armed payloads burst inert and
    fire on ignition (ON_TRIGGER)."""
    chassis = build.delivery_item
    if chassis.delivery is None and chassis.base_use is not None:
        if chassis.base_use.armed:
            return [
                Stage(trigger=Trigger.ON_IMPACT, effects=[], note="burst"),
                Stage(trigger=Trigger.ON_TRIGGER, effects=effects, note="armed patch"),
            ]
        return [Stage(trigger=Trigger.ON_IMPACT, effects=effects, note="burst")]
    return [Stage(trigger=Trigger.ON_HIT, effects=effects, note="composed")]
```

In `resolve`, replace the final `stages=[...]` line:

```python
        stages=_stages_for(build, effects),
```

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: all passing (the swamp_cooler ON_HIT assertion still holds — its chassis is a mechanism).

- [ ] **Step 5: Commit**

```bash
git add resolver/fallback.py tests/test_fallback.py
git commit -m "feat: composer burst/armed-patch shapes for substance chassis

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: End-to-end verification

No new code. Prove the whole pipeline runs with no API key and the catalog reads correctly through the consumers.

- [ ] **Step 1: Full suite**

Run: `python -m pytest -q`
Expected: all green (baseline 95 + the new base-use/solo/fallback/items tests; roughly 170 collected with the 61-item parametrization).

- [ ] **Step 2: Deterministic harness smoke run**

Run (PowerShell): `$env:PYTHONUTF8 = '1'; python -m resolver.harness --fallback --build swamp_cooler --build probe_whimsical --repeats 1`
Expected: renders both builds across all six tiers via the deterministic fallback, no exceptions, no API key needed. Eyeball: swamp_cooler shows BURN/CHAIN/KNOCKBACK at RARE+.

- [ ] **Step 3: Verify a thrown-container build end to end**

Run (PowerShell): `$env:PYTHONUTF8 = '1'; python -c "from resolver.contract import Tier; from resolver.items import CATALOG, Build; from resolver import fallback; from resolver.clamp import apply; b = Build(delivery_item=CATALOG['jerrycan of gasoline']); r = apply(fallback.resolve(b, Tier.COMMON), b, Tier.COMMON); print(r.delivery, r.category, r.harmless, [s.trigger for s in r.draft.stages])"`
Expected output: `Delivery.THROWN Category.WEAPON False [<Trigger.ON_IMPACT...>, <Trigger.ON_TRIGGER...>]`

- [ ] **Step 4: Report**

No commit (nothing changed). Report the final test count and paste the harness tier-spread snippet for the swamp_cooler into the task notes for the user's eyeball check.
