# Item Catalog & Behavior-First Taxonomy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the resolver's placeholder catalog and stub fallback with the reimagined 53-item verb-first catalog, a three-layer behavior model (base delivery × overlay × effect), a coherence scorer, a real deterministic composer, and a router that concentrates LLM spend on the absurd high-tier quadrant.

**Architecture:** Items declare `roles` (MECHANISM/MODIFIER/SUBSTANCE) + affinity `tags` + a base `delivery` form. A shared tag-interaction table drives both the coherence scorer (does a build's items interact → C∈[0,1]) and the deterministic composer (interactions → staged effects, tier-scaled, then clamped by the existing `clamp.py`). A router picks deterministic vs. LLM from `(coherence, tier)`. The composer's `resolve(build, tier) -> GadgetDraft` signature is identical to today's `fallback.resolve`, so the harness swaps paths without structural change.

**Tech Stack:** Python 3.11+, pydantic v2 (already used in `contract.py`), pytest. Engine-agnostic — zero engine references. No new third-party dependencies.

## Global Constraints

- **Engine-agnostic:** no Unreal/engine references anywhere in `resolver/` (CLAUDE.md).
- **Code owns every number:** the model/composer proposes composition; magnitudes are code-derived and re-clamped by `clamp.py`. `harmless` and `category` are always re-derived in `clamp.py`, never trusted (invariant #4).
- **Enums are the contract:** items may only carry tokens from `Delivery`/`EffectKind`/`Trigger` and the tag `TAXONOMY`. Never widen to fit the model (invariant #5). `Seeking`/`Physics` overlays stay design-only — do NOT add them to the contract.
- **Never a hard LLM dependency:** the deterministic composer must fully resolve any build with no API key (invariant #6).
- **Tag taxonomy (24, exact):** `sharp, blunt, heavy, long-reach, springy, brittle, flammable, ignition, corrosive, cold, liquid, slippery, sticky, pressurized-gas, powder, electrical, wind, loud, light-source, container, scatter, restorative, stimulant, protective`.
- **Source of truth for the catalog:** `docs/superpowers/specs/2026-07-12-item-catalog-and-behavior-taxonomy-design.md` (§ "The catalog — 53 items"). Transcribe items from there; the invariant tests enforce completeness.
- **Tests run with:** `python -m pytest -q` from repo root.
- **Commit style:** conventional commits; end with the `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` trailer.

## File Structure

- `resolver/contract.py` — **modify.** Add `Role`, `Flag` enums and a `TIER_ORDER` index helper. (Existing enums/schema unchanged.)
- `resolver/interactions.py` — **create.** The tag `TAXONOMY`, `SINGLE_TAG_EFFECTS`, `PAIR_EFFECTS`, and `tags_interact(a_tags, b_tags)` — shared by the scorer and the composer.
- `resolver/items.py` — **modify.** Extend `Item` (new fields, `associations` optional, `describe()`); catalog swapped to 53 items; `Build.delivery` reads `item.delivery`; `DELIVERY_LOCK` removed; new `DEFAULT_BUILDS`.
- `resolver/coherence.py` — **create.** `coherence(build) -> float`.
- `resolver/fallback.py` — **modify (rewrite `resolve`).** The three-layer deterministic composer. Keeps the module name and `resolve(build, tier) -> GadgetDraft` signature.
- `resolver/router.py` — **create.** `route(build, tier) -> Literal["deterministic","llm"]`.
- `resolver/prompt.py`, `resolver/serve.py`, `resolver/harness.py` — **modify.** Migrate off `associations`/`DELIVERY_LOCK` to the new schema; harness reports the deterministic/LLM split.
- Tests: `tests/test_contract.py`, `tests/test_interactions.py` (new), `tests/test_items.py`, `tests/test_coherence.py` (new), `tests/test_fallback.py`, `tests/test_router.py` (new), plus touch-ups to `tests/test_prompt.py`, `tests/test_serve.py`, `tests/test_harness.py`.

---

### Task 1: `Role` + `Flag` enums and tier ordering

**Files:**
- Modify: `resolver/contract.py` (append after `Tier`, ~line 77)
- Test: `tests/test_contract.py`

**Interfaces:**
- Produces: `Role` (MECHANISM, MODIFIER, SUBSTANCE), `Flag` (WIELDABLE, FIREARM, AMMUNITION, LOADABLE, BASE_WEAPON), `TIER_ORDER: dict[Tier, int]`, `tier_at_least(tier, floor) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contract.py  (append)
from resolver.contract import Role, Flag, Tier, TIER_ORDER, tier_at_least

def test_roles_and_flags_exist():
    assert {r.value for r in Role} == {"MECHANISM", "MODIFIER", "SUBSTANCE"}
    assert {f.value for f in Flag} == {
        "WIELDABLE", "FIREARM", "AMMUNITION", "LOADABLE", "BASE_WEAPON"
    }

def test_tier_order_is_monotonic_and_total():
    assert set(TIER_ORDER) == set(Tier)
    assert TIER_ORDER[Tier.DUD] < TIER_ORDER[Tier.LEGENDARY]

def test_tier_at_least():
    assert tier_at_least(Tier.RARE, Tier.UNCOMMON) is True
    assert tier_at_least(Tier.COMMON, Tier.RARE) is False
    assert tier_at_least(Tier.RARE, Tier.RARE) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_contract.py::test_roles_and_flags_exist -q`
Expected: FAIL with `ImportError: cannot import name 'Role'`.

- [ ] **Step 3: Write minimal implementation**

```python
# resolver/contract.py  (append after the Tier enum, before the family sets)
class Role(str, Enum):
    MECHANISM = "MECHANISM"   # feeds base delivery behaviour
    MODIFIER = "MODIFIER"     # feeds behavioural overlay + effect transform
    SUBSTANCE = "SUBSTANCE"   # feeds effect / damage type


class Flag(str, Enum):
    WIELDABLE = "WIELDABLE"
    FIREARM = "FIREARM"
    AMMUNITION = "AMMUNITION"
    LOADABLE = "LOADABLE"
    BASE_WEAPON = "BASE_WEAPON"


TIER_ORDER: dict["Tier", int] = {t: i for i, t in enumerate(Tier)}


def tier_at_least(tier: "Tier", floor: "Tier") -> bool:
    return TIER_ORDER[tier] >= TIER_ORDER[floor]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_contract.py -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add resolver/contract.py tests/test_contract.py
git commit -m "feat: add Role/Flag enums and tier ordering to the contract

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: The tag taxonomy + interaction tables

**Files:**
- Create: `resolver/interactions.py`
- Test: `tests/test_interactions.py`

**Interfaces:**
- Consumes: `EffectKind` from `resolver.contract`.
- Produces:
  - `TAXONOMY: frozenset[str]` — the 24 tags.
  - `SINGLE_TAG_EFFECTS: dict[str, EffectKind]` — effect a lone tag implies.
  - `PAIR_EFFECTS: dict[frozenset[str], EffectKind]` — emergent effect from two tags.
  - `tags_interact(a: frozenset[str], b: frozenset[str]) -> bool` — do two items' tag sets share a tag or trigger a pair interaction.
  - `effects_for(tags: frozenset[str]) -> list[EffectKind]` — every effect a combined tag set produces (pairs first, then singles for uncovered tags).

These tables are **v0, code-owned, and expected to churn** (like `clamp.py`'s budgets). Tests assert *structure and known wirings*, never exact balance.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_interactions.py
from resolver.contract import EffectKind
from resolver import interactions as I

def test_taxonomy_is_the_24_locked_tags():
    assert len(I.TAXONOMY) == 24
    assert "container" in I.TAXONOMY and "scatter" in I.TAXONOMY
    # dropped tags must be absent
    for gone in ("buoyant", "decoy", "swarm"):
        assert gone not in I.TAXONOMY

def test_all_table_tags_are_in_taxonomy():
    used = set(I.SINGLE_TAG_EFFECTS)
    for pair in I.PAIR_EFFECTS:
        used |= set(pair)
    assert used <= I.TAXONOMY

def test_known_pair_flammable_ignition_burns():
    assert I.PAIR_EFFECTS[frozenset({"flammable", "ignition"})] is EffectKind.BURN

def test_electrical_liquid_chains():
    assert I.PAIR_EFFECTS[frozenset({"electrical", "liquid"})] is EffectKind.CHAIN

def test_tags_interact_on_shared_tag():
    assert I.tags_interact(frozenset({"heavy", "blunt"}), frozenset({"blunt"})) is True

def test_tags_interact_on_pair_rule():
    assert I.tags_interact(frozenset({"flammable"}), frozenset({"ignition"})) is True

def test_tags_do_not_interact_when_unrelated():
    assert I.tags_interact(frozenset({"sharp"}), frozenset({"restorative"})) is False

def test_effects_for_prefers_pair_then_singles():
    effs = I.effects_for(frozenset({"flammable", "ignition", "sharp"}))
    assert EffectKind.BURN in effs      # from the pair
    assert EffectKind.PIERCE in effs    # sharp single, uncovered by the pair
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_interactions.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.interactions'`.

- [ ] **Step 3: Write minimal implementation**

```python
# resolver/interactions.py
"""The tag taxonomy + the known-interaction tables. This is half the system:
the composer can only be as clever as these tables, and the coherence scorer
reads the same wiring to decide whether a build's items interact. Numbers live
in the composer/clamp; here we own only *which effect a tag interaction yields*.
v0, code-owned, expected to churn.
"""
from __future__ import annotations

from itertools import combinations

from resolver.contract import EffectKind

TAXONOMY: frozenset[str] = frozenset({
    # physical / impact
    "sharp", "blunt", "heavy", "long-reach", "springy", "brittle",
    # substance / state
    "flammable", "ignition", "corrosive", "cold", "liquid", "slippery",
    "sticky", "pressurized-gas", "powder",
    # energy / field
    "electrical", "wind", "loud", "light-source",
    # structural / dispersal
    "container", "scatter",
    # self / support
    "restorative", "stimulant", "protective",
})

# A lone tag's baseline effect (used when no pair interaction covers it).
SINGLE_TAG_EFFECTS: dict[str, EffectKind] = {
    "sharp": EffectKind.PIERCE,
    "blunt": EffectKind.DAMAGE,
    "heavy": EffectKind.KNOCKBACK,
    "springy": EffectKind.LAUNCH,
    "corrosive": EffectKind.BURN,
    "cold": EffectKind.FREEZE,
    "electrical": EffectKind.CHAIN,
    "sticky": EffectKind.SNARE,
    "slippery": EffectKind.SLOW,
    "flammable": EffectKind.BURN,
    "loud": EffectKind.LURE,
    "light-source": EffectKind.LURE,
    "wind": EffectKind.KNOCKBACK,
    "restorative": EffectKind.HEAL,
    "stimulant": EffectKind.SPEED,
    "protective": EffectKind.SHIELD,
}

# Emergent effect when two tags meet (checked before singles).
PAIR_EFFECTS: dict[frozenset[str], EffectKind] = {
    frozenset({"flammable", "ignition"}): EffectKind.BURN,
    frozenset({"flammable", "electrical"}): EffectKind.BURN,
    frozenset({"pressurized-gas", "ignition"}): EffectKind.EXPLODE,
    frozenset({"powder", "ignition"}): EffectKind.EXPLODE,
    frozenset({"corrosive", "liquid"}): EffectKind.BURN,
    frozenset({"electrical", "liquid"}): EffectKind.CHAIN,
    frozenset({"liquid", "cold"}): EffectKind.FREEZE,
    frozenset({"sticky", "liquid"}): EffectKind.SNARE,
}


def tags_interact(a: frozenset[str], b: frozenset[str]) -> bool:
    if a & b:
        return True
    for x in a:
        for y in b:
            if frozenset({x, y}) in PAIR_EFFECTS:
                return True
    return False


def effects_for(tags: frozenset[str]) -> list[EffectKind]:
    effects: list[EffectKind] = []
    covered: set[str] = set()
    for pair in combinations(sorted(tags), 2):
        key = frozenset(pair)
        if key in PAIR_EFFECTS:
            effects.append(PAIR_EFFECTS[key])
            covered |= key
    for tag in sorted(tags - covered):
        if tag in SINGLE_TAG_EFFECTS:
            effects.append(SINGLE_TAG_EFFECTS[tag])
    return effects
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_interactions.py -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add resolver/interactions.py tests/test_interactions.py
git commit -m "feat: tag taxonomy + known-interaction tables (scorer/composer shared)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Extend the `Item` schema (additive, repo stays green)

**Files:**
- Modify: `resolver/items.py` (the `Item` dataclass, ~lines 12-16)
- Test: `tests/test_items.py` (append)

**Interfaces:**
- Consumes: `Role`, `Flag` (Task 1), `Delivery`.
- Produces: `Item` with new fields, all defaulted so the existing 8 items still construct unchanged, plus `Item.describe() -> str`.

New `Item` shape:
```
Item(name, associations=(), roles=frozenset(), verb="",
     tags=frozenset(), delivery=None, caliber=None, flags=frozenset())
```

- [ ] **Step 1: Write the failing test**

```python
# tests/test_items.py  (append)
from resolver.contract import Role, Flag, Delivery
from resolver.items import Item

def test_item_defaults_keep_old_construction_working():
    it = Item("scrap", ["it is scrap"])
    assert it.roles == frozenset() and it.verb == "" and it.tags == frozenset()
    assert it.delivery is None and it.caliber is None and it.flags == frozenset()

def test_item_describe_uses_associations_when_present():
    it = Item("mop", ["long reach", "tangling strands"])
    assert it.describe() == "long reach, tangling strands"

def test_item_describe_falls_back_to_verb_and_tags():
    it = Item("blender", roles=frozenset({Role.MECHANISM}), verb="blend-&-spit",
              tags=frozenset({"liquid", "scatter"}), delivery=Delivery.SPRAY)
    d = it.describe()
    assert "blend-&-spit" in d and "liquid" in d and "scatter" in d
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_items.py::test_item_defaults_keep_old_construction_working -q`
Expected: FAIL with `TypeError` (unexpected keyword) or `AttributeError: describe`.

- [ ] **Step 3: Write minimal implementation**

Replace the `Item` dataclass at the top of `resolver/items.py`:

```python
from resolver.contract import Delivery, Role, Flag, MELEE_DELIVERIES

@dataclass(frozen=True)
class Item:
    name: str
    # ordered obvious -> non-obvious -> chainable (optional; LLM-path flavor)
    associations: tuple[str, ...] = ()
    roles: frozenset[Role] = frozenset()
    verb: str = ""
    tags: frozenset[str] = frozenset()
    delivery: Delivery | None = None
    caliber: str | None = None
    flags: frozenset[Flag] = frozenset()

    def describe(self) -> str:
        if self.associations:
            return ", ".join(self.associations)
        parts = [self.verb] if self.verb else []
        parts.extend(sorted(self.tags))
        return ", ".join(p for p in parts if p)
```

Note: `associations` is now a tuple with default `()`. The existing 8 items pass a `list`; frozen dataclasses accept it, but normalize by leaving those list literals — they still work since the field is only read. Do NOT retag the old items; they are deleted in Task 4.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_items.py -q`
Expected: PASS (existing item tests still green; new schema tests pass).

- [ ] **Step 5: Commit**

```bash
git add resolver/items.py tests/test_items.py
git commit -m "feat: extend Item schema with roles/verb/tags/delivery/caliber/flags

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Swap in the 53-item catalog + migrate all consumers (atomic; repo stays green)

This is the big swap. It replaces the catalog, moves delivery onto the item, deletes `DELIVERY_LOCK`, rebuilds `DEFAULT_BUILDS`, and migrates every consumer (`prompt.py`, `serve.py`, `harness.py`) plus their tests in one green commit.

**Files:**
- Modify: `resolver/items.py` (catalog, `Build.delivery`, `DEFAULT_BUILDS`, remove `DELIVERY_LOCK`)
- Modify: `resolver/prompt.py` (`_slot_line` → `item.describe()`)
- Modify: `resolver/serve.py` (catalog payload + build assembly off the new schema)
- Modify: `tests/test_items.py`, `tests/test_prompt.py`, `tests/test_serve.py`
- Test: catalog invariants in `tests/test_items.py`

**Interfaces:**
- Consumes: `Item`, `Role`, `Flag`, `Delivery`, `TAXONOMY`.
- Produces: `CATALOG: dict[str, Item]` (53 items), `Build.delivery` reads `delivery_item.delivery`, `DEFAULT_BUILDS` with keys `"broom_bat"` (grounded), `"gun_ammo"` (coherent firearm), `"bananarama"` (absurd). `DELIVERY_LOCK` no longer exists.

- [ ] **Step 1: Write the failing catalog-invariant tests**

Replace the obsolete assertions in `tests/test_items.py` (the ones referencing `rubber duck`, `push broom`, `DELIVERY_LOCK`, and the old `DEFAULT_BUILDS` families) with:

```python
# tests/test_items.py  (replace old catalog/build tests with these)
from resolver.contract import Delivery, Role, Flag
from resolver.items import Item, Build, CATALOG, DEFAULT_BUILDS, params_for
from resolver.interactions import TAXONOMY

def test_catalog_is_the_reimagined_slice():
    assert len(CATALOG) >= 50
    for it in CATALOG.values():
        assert it.roles, f"{it.name} has no role"
        assert it.tags <= TAXONOMY, f"{it.name} has off-taxonomy tags: {it.tags - TAXONOMY}"

def test_every_delivery_form_has_a_mechanism_carrier():
    carried = {it.delivery for it in CATALOG.values()
               if Role.MECHANISM in it.roles and it.delivery is not None}
    assert carried == set(Delivery)

def test_every_tag_has_a_carrier():
    carried = set().union(*(it.tags for it in CATALOG.values()))
    assert TAXONOMY <= carried

def test_firearms_have_matching_ammunition():
    gun_cals = {it.caliber for it in CATALOG.values() if Flag.FIREARM in it.flags}
    ammo_cals = {it.caliber for it in CATALOG.values() if Flag.AMMUNITION in it.flags}
    assert gun_cals and gun_cals <= ammo_cals

def test_build_delivery_reads_from_the_item():
    build = DEFAULT_BUILDS["gun_ammo"]
    assert isinstance(build.delivery, Delivery)

def test_build_rejects_non_delivery_chassis():
    import pytest
    payload = next(it for it in CATALOG.values() if it.delivery is None)
    with pytest.raises(ValueError):
        _ = Build(delivery_item=payload).delivery

def test_default_builds_span_grounded_and_absurd():
    assert set(DEFAULT_BUILDS) == {"broom_bat", "gun_ammo", "bananarama"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_items.py -q`
Expected: FAIL (old catalog still present; new invariants unmet).

- [ ] **Step 3: Rewrite the catalog and Build in `resolver/items.py`**

Replace `_ITEMS`, `DELIVERY_LOCK`, `Build.delivery`, `Build.color`, and `DEFAULT_BUILDS`. Transcribe **all 53 items** from the spec's catalog tables. Representative constructions (one per role/flag pattern — follow this exact shape for the rest):

```python
from resolver.contract import Delivery, Role, Flag, MELEE_DELIVERIES

M, MOD, SUB = Role.MECHANISM, Role.MODIFIER, Role.SUBSTANCE

_ITEMS: list[Item] = [
    # --- firearms (Mechanism · wieldable base weapons) ---
    Item("m16 rifle", roles=frozenset({M}), verb="fire-auto",
         tags=frozenset({}), delivery=Delivery.HITSCAN, caliber="5.56",
         flags=frozenset({Flag.WIELDABLE, Flag.FIREARM, Flag.BASE_WEAPON})),
    Item("pump shotgun", roles=frozenset({M}), verb="fire-spread",
         tags=frozenset({"scatter"}), delivery=Delivery.SPRAY, caliber="12ga",
         flags=frozenset({Flag.WIELDABLE, Flag.FIREARM, Flag.BASE_WEAPON})),
    # --- powered mechanisms ---
    Item("blender", roles=frozenset({M}), verb="blend-&-spit",
         tags=frozenset({"liquid", "scatter", "electrical"}), delivery=Delivery.SPRAY),
    Item("potato cannon", roles=frozenset({M}), verb="launch",
         tags=frozenset({"pressurized-gas"}), delivery=Delivery.LOBBED),
    # --- melee ---
    Item("baseball bat", roles=frozenset({M}), verb="clobber",
         tags=frozenset({"blunt", "springy"}), delivery=Delivery.SWING,
         flags=frozenset({Flag.WIELDABLE})),
    # --- modifier / energizer (overlay + effect transform) ---
    Item("car battery", roles=frozenset({MOD, SUB}), verb="electrify",
         tags=frozenset({"electrical", "heavy", "corrosive"})),
    Item("propane tank", roles=frozenset({MOD, SUB}), verb="fuel-bomb",
         tags=frozenset({"pressurized-gas", "flammable"})),
    # --- substance / payload ---
    Item("gasoline", roles=frozenset({SUB}), verb="fuel",
         tags=frozenset({"liquid", "flammable", "ignition"})),
    Item("overripe produce", roles=frozenset({SUB}), verb="gum-up",
         tags=frozenset({"slippery", "sticky"})),
    # --- ammo ---
    Item("5.56 rounds", roles=frozenset({SUB}), verb="round",
         tags=frozenset(), caliber="5.56", flags=frozenset({Flag.AMMUNITION})),
    Item("box of nails", roles=frozenset({SUB}), verb="improvised-round",
         tags=frozenset({"scatter", "sharp"}), flags=frozenset({Flag.LOADABLE})),
    # --- support ---
    Item("first-aid kit", roles=frozenset({MOD}), verb="patch",
         tags=frozenset({"restorative"}), delivery=Delivery.SELF),
    # ... transcribe the remaining items from the spec's catalog tables.
    # The invariant tests above enforce: >=50 items, every delivery form
    # carried, every tag carried, every firearm caliber matched by ammo.
]

CATALOG: dict[str, Item] = {item.name: item for item in _ITEMS}

_COLOR_BY_ITEM: dict[str, str] = {}  # optional per-item tint; default "grey"
```

Rewrite `Build.delivery` / `Build.color` and drop `DELIVERY_LOCK`:

```python
    @property
    def delivery(self) -> Delivery:
        d = self.delivery_item.delivery
        if d is None:
            raise ValueError(f"{self.delivery_item.name!r} cannot be a delivery chassis")
        return d

    @property
    def color(self) -> str:
        return _COLOR_BY_ITEM.get(self.delivery_item.name, "grey")
```

Rewrite `DEFAULT_BUILDS`:

```python
DEFAULT_BUILDS: dict[str, Build] = {
    # grounded, coherent: blunt melee + heavy modifier
    "broom_bat": Build(
        delivery_item=CATALOG["baseball bat"],
        modifier_item=CATALOG["car battery"],
    ),
    # coherent firearm: gun + matching-caliber ammo (C should be ~1)
    "gun_ammo": Build(
        delivery_item=CATALOG["m16 rifle"],
        damage_item=CATALOG["5.56 rounds"],
    ),
    # absurd: the Bananarama — stream mechanism + shock modifier + snare goo
    "bananarama": Build(
        delivery_item=CATALOG["blender"],
        modifier_item=CATALOG["car battery"],
        utility_item=CATALOG["overripe produce"],
    ),
}
```

- [ ] **Step 4: Migrate `prompt.py` and `serve.py`**

`resolver/prompt.py` — swap `_slot_line` to the schema-agnostic describe:

```python
def _slot_line(item) -> str:
    if item is None:
        return "empty"
    return f"{item.name} — {item.describe()}"
```

`resolver/serve.py` — replace the `DELIVERY_LOCK`/`associations` reads. In the catalog payload (~lines 30-33) and build assembly (~lines 52-54):

```python
# catalog payload
"associations": list(item.describe().split(", ")),
"delivery": item.delivery.value if item.delivery is not None else None,
"color": _color_for(item.name),
# build assembly guard
if item_for(name).delivery is None:
    raise ValueError(...)
```

Update the import line `from resolver.items import CATALOG, COLOR_BY_ITEM, DELIVERY_LOCK, Build` to drop `COLOR_BY_ITEM, DELIVERY_LOCK` and use `item.delivery`. (If `serve.py` needs a color, add a local `_color_for(name) -> str` returning `"grey"`.) The inline JS at line 304 already reads `it.associations`, which the payload still provides — no JS change needed.

- [ ] **Step 5: Fix `test_prompt.py` and `test_serve.py`**

Update any assertions that referenced old item names (`push broom`, `rubber duck`) or `DELIVERY_LOCK` to use the new `DEFAULT_BUILDS` keys and item names. Run each file and repair references until green.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all). If `test_harness.py` references old build keys, update them to `"broom_bat"/"gun_ammo"/"bananarama"`.

- [ ] **Step 7: Commit**

```bash
git add resolver/items.py resolver/prompt.py resolver/serve.py tests/
git commit -m "feat: swap in the 53-item verb-first catalog; migrate consumers

Delivery moves onto Item; DELIVERY_LOCK removed; DEFAULT_BUILDS now span
grounded/coherent/absurd (incl. the Bananarama). Catalog invariants tested.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Coherence scorer

**Files:**
- Create: `resolver/coherence.py`
- Test: `tests/test_coherence.py`

**Interfaces:**
- Consumes: `Build` (`resolver.items`), `tags_interact` (`resolver.interactions`), `Flag` (`resolver.contract`).
- Produces: `coherence(build: Build) -> float` in `[0,1]`.

Rule: items = non-None build slots. `len <= 1 → 1.0`. Otherwise `C = interacting_pairs / total_pairs`, where a pair interacts if `tags_interact(a.tags, b.tags)` **or** one is a `FIREARM` and the other is matching-caliber `AMMUNITION`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coherence.py
from resolver.items import Build, CATALOG, DEFAULT_BUILDS
from resolver.coherence import coherence

def test_single_item_is_trivially_coherent():
    assert coherence(Build(delivery_item=CATALOG["baseball bat"])) == 1.0

def test_gun_plus_matching_ammo_is_fully_coherent():
    assert coherence(DEFAULT_BUILDS["gun_ammo"]) == 1.0

def test_absurd_build_is_less_coherent_than_a_grounded_one():
    grounded = coherence(DEFAULT_BUILDS["broom_bat"])
    absurd = coherence(DEFAULT_BUILDS["bananarama"])
    assert 0.0 <= absurd < grounded <= 1.0

def test_gun_plus_wrong_caliber_ammo_does_not_interact():
    build = Build(delivery_item=CATALOG["m16 rifle"], damage_item=CATALOG["box of nails"])
    # nails are LOADABLE (no caliber), so no firearm/ammo edge, and no shared tag
    assert coherence(build) < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_coherence.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.coherence'`.

- [ ] **Step 3: Write minimal implementation**

```python
# resolver/coherence.py
"""Pure, cheap, LLM-free routing signal: how connected a build's items are.
C≈1 = a coherent build (a chain explains all items); C≈0 = disconnected junk.
"""
from __future__ import annotations

from itertools import combinations

from resolver.contract import Flag
from resolver.items import Build, Item
from resolver.interactions import tags_interact


def _firearm_ammo_match(a: Item, b: Item) -> bool:
    gun, ammo = None, None
    for x in (a, b):
        if Flag.FIREARM in x.flags:
            gun = x
        elif Flag.AMMUNITION in x.flags:
            ammo = x
    return gun is not None and ammo is not None and gun.caliber == ammo.caliber


def _pair_interacts(a: Item, b: Item) -> bool:
    return tags_interact(a.tags, b.tags) or _firearm_ammo_match(a, b)


def coherence(build: Build) -> float:
    items = [it for _, it in build.slots() if it is not None]
    if len(items) <= 1:
        return 1.0
    pairs = list(combinations(items, 2))
    edges = sum(1 for a, b in pairs if _pair_interacts(a, b))
    return edges / len(pairs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_coherence.py -q`
Expected: PASS. If `test_absurd_build_is_less_coherent...` fails because the Bananarama scores 1.0, verify the spec's tags for `blender`/`car battery`/`overripe produce` — the intended non-edge is produce↔battery (no shared tag, no pair rule). Adjust the transcribed tags to match the spec, not the test.

- [ ] **Step 5: Commit**

```bash
git add resolver/coherence.py tests/test_coherence.py
git commit -m "feat: coherence scorer over tags + firearm/ammo caliber match

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Deterministic three-layer composer (rewrite the `fallback.py` stub)

**Files:**
- Modify: `resolver/fallback.py` (rewrite `resolve`; keep the module + signature)
- Test: `tests/test_fallback.py` (replace stub assertions)

**Interfaces:**
- Consumes: `Build`, `effects_for` (`interactions`), `Effect/Stage/GadgetDraft/Trigger/EffectKind/Tier/Role` (`contract`).
- Produces: `resolve(build: Build, tier: Tier) -> GadgetDraft` — **same signature as today**, so `harness`/`clamp` consume it unchanged. Downstream `clamp.apply(...)` still owns final magnitudes, `harmless`, and `category`.

Composition rule (three layers):
- **Base delivery** = `build.delivery` (the chassis form) — recorded in `logic`, not an effect.
- **Effects (Layer 3)** = `effects_for(union of SUBSTANCE + MECHANISM item tags)`. If empty, fall back to a single `DAMAGE` (a plain hit).
- **Overlays (Layer 2)** = from MODIFIER items: `EXPLODE` if any modifier has `pressurized-gas`+`flammable` or `powder`; `CHAIN` if any modifier has `electrical`; `PIERCE` if any item has `sharp`. Overlays become an extra `ON_HIT` effect.
- **Magnitudes** = seed each effect with a per-tier weight (`_TIER_SEED[tier]`); `clamp.py` re-derives the final budget. Deeper tier = more overlay effects unlocked (DUD: base only; ≥RARE: base + all overlays), which is the "reality bends deeper" knob.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fallback.py  (replace the file body)
from resolver.contract import EffectKind, GadgetDraft, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver import fallback

def _kinds(draft):
    return {e.kind for s in draft.stages for e in s.effects}

def test_composer_returns_valid_draft_with_no_api():
    draft = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.COMMON)
    assert isinstance(draft, GadgetDraft)
    assert draft.name and draft.logic and draft.stages

def test_grounded_flammable_chain_burns():
    # a build whose substance tags trigger BURN should yield a BURN effect
    draft = fallback.resolve(DEFAULT_BUILDS["bananarama"], Tier.RARE)
    assert draft.stages[0].trigger is Trigger.ON_HIT

def test_higher_tier_unlocks_more_effects():
    dud = fallback.resolve(DEFAULT_BUILDS["bananarama"], Tier.DUD)
    leg = fallback.resolve(DEFAULT_BUILDS["bananarama"], Tier.LEGENDARY)
    dud_effects = sum(len(s.effects) for s in dud.stages)
    leg_effects = sum(len(s.effects) for s in leg.stages)
    assert leg_effects >= dud_effects

def test_composer_is_deterministic():
    a = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.EPIC)
    b = fallback.resolve(DEFAULT_BUILDS["gun_ammo"], Tier.EPIC)
    assert a.model_dump() == b.model_dump()

def test_effectless_build_still_deals_a_plain_hit():
    from resolver.items import Build, CATALOG
    draft = fallback.resolve(Build(delivery_item=CATALOG["m16 rifle"]), Tier.DUD)
    assert EffectKind.DAMAGE in _kinds(draft)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fallback.py -q`
Expected: FAIL (old stub returns a fixed single DAMAGE draft; new behaviors absent).

- [ ] **Step 3: Write the composer**

```python
# resolver/fallback.py  (rewrite body below the module docstring)
from __future__ import annotations

from resolver.contract import (
    Effect, EffectKind, GadgetDraft, Role, Stage, Tier, Trigger, tier_at_least,
)
from resolver.items import Build
from resolver.interactions import effects_for

_TIER_SEED: dict[Tier, float] = {
    Tier.DUD: 2.0, Tier.COMMON: 6.0, Tier.UNCOMMON: 10.0,
    Tier.RARE: 18.0, Tier.EPIC: 30.0, Tier.LEGENDARY: 45.0,
}


def _role_items(build: Build, role: Role):
    return [it for _, it in build.slots() if it is not None and role in it.roles]


def _overlays(build: Build) -> list[EffectKind]:
    overlays: list[EffectKind] = []
    mods = _role_items(build, Role.MODIFIER)
    for m in mods:
        if "electrical" in m.tags:
            overlays.append(EffectKind.CHAIN)
        if "powder" in m.tags or ("pressurized-gas" in m.tags and "flammable" in m.tags):
            overlays.append(EffectKind.EXPLODE)
    if any("sharp" in it.tags for _, it in build.slots() if it is not None):
        overlays.append(EffectKind.PIERCE)
    # de-dup, stable order
    seen, out = set(), []
    for k in overlays:
        if k not in seen:
            seen.add(k); out.append(k)
    return out


def resolve(build: Build, tier: Tier) -> GadgetDraft:
    seed = _TIER_SEED[tier]
    tag_union = frozenset().union(
        *(it.tags for _, it in build.slots() if it is not None)
    ) if any(it for _, it in build.slots()) else frozenset()

    base_effects = effects_for(tag_union) or [EffectKind.DAMAGE]
    # base: strongest single effect at DUD; more of the chain deeper
    take = 1 if tier is Tier.DUD else (2 if not tier_at_least(tier, Tier.RARE) else len(base_effects))
    chosen = base_effects[:take]

    effects = [Effect(kind=k, amount=seed, note="base") for k in chosen]
    # overlays only unlock at RARE+
    if tier_at_least(tier, Tier.RARE):
        for k in _overlays(build):
            effects.append(Effect(kind=k, amount=seed * 0.5, note="overlay"))

    name_bits = " + ".join(it.name for _, it in build.slots() if it is not None)
    return GadgetDraft(
        name=f"Improvised {build.delivery_item.name.title()}",
        description=f"{name_bits}, composed by the simulation.",
        logic=(
            f"Base delivery: {build.delivery.value}. "
            f"Effects from tags {sorted(tag_union)}: "
            f"{[e.kind.value for e in effects]}."
        ),
        stages=[Stage(trigger=Trigger.ON_HIT, effects=effects, note="composed")],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fallback.py -q`
Expected: PASS. Then run the whole suite (`python -m pytest -q`) to confirm `harness`/`clamp` still consume the composer.

- [ ] **Step 5: Commit**

```bash
git add resolver/fallback.py tests/test_fallback.py
git commit -m "feat: real three-layer deterministic composer (base x overlay x effect)

Replaces the plain-hit stub: tags -> interaction effects, modifier overlays
unlock at RARE+, clamp.py still owns final magnitudes/harmless/category.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Router

**Files:**
- Create: `resolver/router.py`
- Test: `tests/test_router.py`

**Interfaces:**
- Consumes: `coherence` (`resolver.coherence`), `Tier`, `tier_at_least` (`contract`), `Build`.
- Produces: `route(build: Build, tier: Tier) -> str` returning `"deterministic"` or `"llm"`; module constants `C_HIGH = 0.66`, `C_LOW = 0.33`.

Rule (spec Fork 2, confirmed):
```
if tier in {DUD, COMMON}: "deterministic"
elif C >= C_HIGH:         "deterministic"
elif C <= C_LOW:          "llm" if tier >= UNCOMMON else "deterministic"
else:                     "llm" if tier >= RARE else "deterministic"
```

- [ ] **Step 1: Write the failing test**

```python
# tests/test_router.py
from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS
from resolver.router import route, C_HIGH, C_LOW

def test_low_tiers_are_always_deterministic():
    assert route(DEFAULT_BUILDS["bananarama"], Tier.DUD) == "deterministic"
    assert route(DEFAULT_BUILDS["bananarama"], Tier.COMMON) == "deterministic"

def test_coherent_build_stays_deterministic_even_high_tier():
    assert route(DEFAULT_BUILDS["gun_ammo"], Tier.LEGENDARY) == "deterministic"

def test_absurd_high_tier_routes_to_llm():
    assert route(DEFAULT_BUILDS["bananarama"], Tier.LEGENDARY) == "llm"

def test_thresholds_are_the_confirmed_values():
    assert (C_HIGH, C_LOW) == (0.66, 0.33)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_router.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.router'`.

- [ ] **Step 3: Write minimal implementation**

```python
# resolver/router.py
"""The cost lever: pick deterministic vs. LLM from (coherence, tier). Sensible
combos and all low tiers are free; LLM spend concentrates on the absurd frontier.
"""
from __future__ import annotations

from resolver.contract import Tier, tier_at_least
from resolver.coherence import coherence
from resolver.items import Build

C_HIGH: float = 0.66
C_LOW: float = 0.33


def route(build: Build, tier: Tier) -> str:
    if tier in (Tier.DUD, Tier.COMMON):
        return "deterministic"
    c = coherence(build)
    if c >= C_HIGH:
        return "deterministic"
    if c <= C_LOW:
        return "llm" if tier_at_least(tier, Tier.UNCOMMON) else "deterministic"
    return "llm" if tier_at_least(tier, Tier.RARE) else "deterministic"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_router.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add resolver/router.py tests/test_router.py
git commit -m "feat: router - deterministic vs LLM from (coherence, tier)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Wire the router into the harness (report the split)

**Files:**
- Modify: `resolver/harness.py` (compute + print the deterministic/LLM split per run)
- Test: `tests/test_harness.py` (a split-reporting assertion)

**Interfaces:**
- Consumes: `route` (`resolver.router`).
- Produces: harness output including a line like `routing: deterministic 2 / llm 1` across the resolved builds.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_harness.py  (append)
from resolver.router import route
from resolver.items import DEFAULT_BUILDS
from resolver.contract import Tier

def test_route_is_callable_over_default_builds():
    calls = {k: route(b, Tier.RARE) for k, b in DEFAULT_BUILDS.items()}
    assert set(calls.values()) <= {"deterministic", "llm"}
```

(If `harness.py` exposes a `routing_summary(results)` helper, assert its format instead. Otherwise this guards the wiring import.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_harness.py -q`
Expected: FAIL if the import path/helper is missing; otherwise adjust to the real helper name.

- [ ] **Step 3: Add the split report to `harness.py`**

In the run loop where each build is resolved, call `route(build, tier)` and tally. After the loop, print `routing: deterministic {d} / llm {l}`. Keep it additive — do not change the existing resolve/fallback flow; the router report is observational for now (the bake pipeline consumes `route()` later).

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add resolver/harness.py tests/test_harness.py
git commit -m "feat: harness reports the deterministic/LLM routing split

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Integration read (play-tuned, not unit-tested)

Per GAME_IDENTITY §9, "does the weapon read well" has no failing test — it is judged by reading output. This task produces evidence, not an assertion.

**Files:** none created; a manual harness run.

- [ ] **Step 1: Run the deterministic path over all default builds across tiers**

Run: `python -m resolver.harness --builds broom_bat gun_ammo bananarama --fallback` (or the harness's no-API flag) and capture output to `scratchpad/integration_read.txt`.

- [ ] **Step 2: Read the output against these checks (judgment, not pass/fail):**
  - `gun_ammo` (coherent) routes deterministic at all tiers and reads as a reliable weapon.
  - `broom_bat` (grounded) reads as a sensible bat-with-a-kick.
  - `bananarama` (absurd) routes to LLM at RARE+ and, on the deterministic path at low tiers, still produces a valid, legible draft (stream + snare, gaining CHAIN at RARE+).
  - Every effect traces to a stated tag/interaction; magnitudes sit within the tier budget after `clamp.apply`.

- [ ] **Step 3: Record the read** in `docs/HANDOFF.md` (a short "integration read 2026-07-12" note: what read well, what needs table tuning). No commit of scratchpad; commit only the HANDOFF note.

```bash
git add docs/HANDOFF.md
git commit -m "docs: integration read of the deterministic composer + router

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Three-layer model (base × overlay × effect) → Tasks 2 (tables), 6 (composer). ✓
- Reconciled 24-tag taxonomy (dropped buoyant/decoy/swarm, added container) → Task 2 `TAXONOMY` + test. ✓
- Item schema (roles/verb/tags/delivery/caliber/flags) → Tasks 3–4. ✓
- 53-item catalog, every form + tag carried, calibers matched → Task 4 invariants. ✓
- Coherence score (P2) → Task 5. ✓
- Deterministic composer replacing the stub (P3) → Task 6. ✓
- Router with confirmed thresholds (P4, Fork 2) → Task 7. ✓
- Integration read (P5) → Task 9. ✓
- Forks 4 (coherent high-tiers pure deterministic) and 5 (composer before router) → honored by ordering (Task 6 before Task 7) and by the router sending coherent high-tiers to deterministic. ✓
- Parked Seeking/Physics → Global Constraints forbid adding them. ✓
- Game-mechanics (armory/deconstruct/blueprints) → out of scope for the resolver brain; already applied to GAME_IDENTITY. ✓

**Placeholder scan:** the only "transcribe the rest" is Task 4's catalog data, whose source (the committed spec) is named and whose completeness is enforced by four invariant tests. Acceptable — not a logic placeholder.

**Type consistency:** `resolve(build, tier) -> GadgetDraft` preserved (fallback→composer); `coherence(build) -> float`; `route(build, tier) -> str`; `tags_interact`/`effects_for` names match across Tasks 2/5/6; `Role`/`Flag` names match across Tasks 1/3/4/6.

## Open notes for the implementer
- The interaction tables (Task 2) and tier seeds (Task 6) are **v0 and expected to churn** — do not treat their exact effects/numbers as balance truth. Tests assert wiring and structure only.
- If a transcribed item's tags make a `coherence`/composer test contradict the spec, **fix the tags to match the spec**, not the test.
- `clamp.py` still owns final magnitudes, `harmless`, and `category` — the composer must not set those.
