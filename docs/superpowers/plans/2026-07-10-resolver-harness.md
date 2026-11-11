# Resolver Test Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an engine-agnostic Python harness that runs invented junk builds through a resolver (LLM + deterministic fallback) across all six rarity tiers, applies a code-owned clamp, and prints a human-readable spread proving whether the resolver produces a genuine dud→god range.

**Architecture:** Pure-Python package `resolver/` with one responsibility per module: `contract` (enums + Pydantic schema), `items` (junk catalog + builds + delivery lock), `clamp` (code-owned balance), `prompt` (hardened system prompt + user-message renderer), `fallback` (deterministic resolver), `llm` (structured-output resolver with an injectable client), `render` (human-readable output), `harness` (CLI). The model emits only model-owned fields (`GadgetDraft`); code assembles the full `ResolvedGadget` and re-derives everything touching fairness.

**Tech Stack:** Python 3.11+, Pydantic v2 (schema), the `anthropic` SDK (`client.messages.parse` structured output), pytest (tests). No engine/Unreal references anywhere.

## Global Constraints

- **Python 3.11+**, Pydantic v2, `anthropic` SDK, pytest. `requires-python = ">=3.11"`.
- **Tier is an input** told to the model per call — the model never self-assigns tier.
- **Code owns** `delivery` (locked from the delivery item), `color`, `tier` budget, all magnitude clamps, `harmless`, `category`. The model owns `name`, `logic`, `description`, and the staged `effects` composition only.
- **The enums are the wall.** The model-facing `GadgetDraft` contains only model-owned fields; `EffectKind`/`Trigger` inside stages are enums, so structured output cannot emit an off-contract token.
- **A deterministic fallback must exist** and produce a valid (boring) result with **no API key**. Never a hard LLM dependency.
- **Engine-agnostic**: zero Unreal/engine references in the Python.
- **Default model** `claude-sonnet-5`, overridable via `RESOLVER_MODEL` env var. Do **not** set `temperature`/`top_p`/`top_k` (current Sonnet rejects non-default sampling params; adaptive thinking is on by default).
- **Git note:** this repo is not yet a git repository, and the repo's rule is "don't commit unless asked." Task 1 runs `git init` so the plan's per-task commit checkpoints work; those commits stay local. If the user does not want a local repo, skip every `git commit` step — the code still works.
- **Commands** are shown as `python -m pytest ...`. On this machine the shell is PowerShell; the Bash tool is also available. Either runs these commands verbatim.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `resolver/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `resolver` package and a working `python -m pytest` invocation.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "resolver"
version = "0.0.0"
description = "Junk-to-weapon resolver test harness (engine-agnostic brain)"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.6",
    "anthropic>=0.69",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["resolver"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create the package and test packages**

Create `resolver/__init__.py` with a single line:

```python
"""Engine-agnostic junk-to-weapon resolver test harness."""
```

Create `tests/__init__.py` as an empty file (zero bytes).

- [ ] **Step 3: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
*.egg-info/
```

- [ ] **Step 4: Write a smoke test**

Create `tests/test_smoke.py`:

```python
import resolver


def test_package_imports():
    assert resolver.__doc__ is not None
```

- [ ] **Step 5: Install dev dependencies and run the smoke test**

Run:
```
python -m pip install -e ".[dev]"
python -m pytest tests/test_smoke.py -v
```
Expected: `1 passed`.

- [ ] **Step 6: Initialize git and commit**

```
git init
git add pyproject.toml resolver/__init__.py tests/__init__.py tests/test_smoke.py .gitignore
git commit -m "chore: scaffold resolver harness package"
```

---

### Task 2: Capability contract — enums + Pydantic schema

**Files:**
- Create: `resolver/contract.py`
- Test: `tests/test_contract.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Enums `Delivery`, `EffectKind`, `Trigger`, `Category`, `Tier` (all `str, Enum`).
  - Pydantic models `Effect(kind: EffectKind, amount: float=0, duration: float=0, radius: float=0, count: int=0, note: str="")`, `Stage(trigger: Trigger, effects: list[Effect], note: str="")`, `GadgetDraft(name: str, description: str, logic: str, stages: list[Stage])`.
  - Dataclass `ResolvedGadget(draft: GadgetDraft, delivery: Delivery, tier: Tier, category: Category, harmless: bool, color: str, params: dict[str, float])`.
  - Constant frozensets `MELEE_DELIVERIES`, `LETHAL_KINDS`, `CONTROL_KINDS`, `SELF_KINDS`, `UTILITY_KINDS`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_contract.py`:

```python
import pytest
from pydantic import ValidationError

from resolver.contract import (
    Delivery, EffectKind, Trigger, Category, Tier,
    Effect, Stage, GadgetDraft, ResolvedGadget,
    LETHAL_KINDS, CONTROL_KINDS, SELF_KINDS, UTILITY_KINDS, MELEE_DELIVERIES,
)


def test_enums_cover_the_contract_vocabulary():
    assert {d.value for d in Delivery} == {
        "HITSCAN", "PROJECTILE", "LOBBED", "BEAM", "THROWN", "SPRAY", "PLACED",
        "SWING", "THRUST", "SLAM", "WHIP", "GUARD", "SELF", "DASH",
    }
    assert {e.value for e in EffectKind} == {
        "DAMAGE", "BURN", "EXPLODE", "PIERCE", "CHAIN",
        "KNOCKBACK", "LAUNCH", "STAGGER", "SNARE", "SLOW", "FREEZE",
        "HEAL", "SHIELD", "SPEED", "SUMMON", "LURE",
    }
    assert {t.value for t in Trigger} == {
        "ON_USE", "ON_HIT", "ON_IMPACT", "ON_TRIGGER", "ON_EXPIRE", "ON_KILL", "ON_BLOCK",
    }
    assert {t.value for t in Tier} == {
        "DUD", "COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY",
    }


def test_gadget_draft_exposes_only_model_owned_fields():
    # The model may NOT emit delivery, tier, category, harmless, color, params.
    assert set(GadgetDraft.model_fields) == {"name", "description", "logic", "stages"}


def test_valid_draft_round_trips():
    draft = GadgetDraft(
        name="Last Call",
        description="A broom with a grudge.",
        logic="bristles hold the oil; the sweep flings it.",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.BURN, amount=14, duration=3)])],
    )
    assert draft.stages[0].effects[0].kind is EffectKind.BURN


def test_schema_rejects_off_contract_effect_kind():
    with pytest.raises(ValidationError):
        Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind="TELEPORT", amount=1)])


def test_schema_rejects_off_contract_trigger():
    with pytest.raises(ValidationError):
        Stage(trigger="ON_SNEEZE", effects=[])


def test_family_sets_partition_the_effect_kinds():
    families = LETHAL_KINDS | CONTROL_KINDS | SELF_KINDS | UTILITY_KINDS
    assert families == set(EffectKind)
    assert EffectKind.SUMMON in LETHAL_KINDS  # a summoned swarm can hurt -> lethal
    assert Delivery.SWING in MELEE_DELIVERIES


def test_resolved_gadget_carries_code_owned_fields():
    draft = GadgetDraft(name="x", description="", logic="", stages=[])
    rg = ResolvedGadget(
        draft=draft, delivery=Delivery.SWING, tier=Tier.DUD,
        category=Category.DUD, harmless=True, color="amber", params={},
    )
    assert rg.delivery is Delivery.SWING and rg.harmless is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_contract.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.contract'`.

- [ ] **Step 3: Write the implementation**

Create `resolver/contract.py`:

```python
"""The capability contract in code: enums (the wall) + the output schema.

Mirrors docs/CAPABILITY_CONTRACT_v0.md. The enums are the single source of
truth; structured output constrains the model to exactly these tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel


class Delivery(str, Enum):
    HITSCAN = "HITSCAN"
    PROJECTILE = "PROJECTILE"
    LOBBED = "LOBBED"
    BEAM = "BEAM"
    THROWN = "THROWN"
    SPRAY = "SPRAY"
    PLACED = "PLACED"
    SWING = "SWING"
    THRUST = "THRUST"
    SLAM = "SLAM"
    WHIP = "WHIP"
    GUARD = "GUARD"
    SELF = "SELF"
    DASH = "DASH"


class EffectKind(str, Enum):
    DAMAGE = "DAMAGE"
    BURN = "BURN"
    EXPLODE = "EXPLODE"
    PIERCE = "PIERCE"
    CHAIN = "CHAIN"
    KNOCKBACK = "KNOCKBACK"
    LAUNCH = "LAUNCH"
    STAGGER = "STAGGER"
    SNARE = "SNARE"
    SLOW = "SLOW"
    FREEZE = "FREEZE"
    HEAL = "HEAL"
    SHIELD = "SHIELD"
    SPEED = "SPEED"
    SUMMON = "SUMMON"
    LURE = "LURE"


class Trigger(str, Enum):
    ON_USE = "ON_USE"
    ON_HIT = "ON_HIT"
    ON_IMPACT = "ON_IMPACT"
    ON_TRIGGER = "ON_TRIGGER"
    ON_EXPIRE = "ON_EXPIRE"
    ON_KILL = "ON_KILL"
    ON_BLOCK = "ON_BLOCK"


class Category(str, Enum):
    WEAPON = "WEAPON"
    CONTROL = "CONTROL"
    SUPPORT = "SUPPORT"
    MOBILITY = "MOBILITY"
    UTILITY = "UTILITY"
    TRINKET = "TRINKET"
    DUD = "DUD"


class Tier(str, Enum):
    DUD = "DUD"
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


# --- family sets (code knowledge, used by the clamp + params) ---
# SUMMON is treated as lethal: a summoned swarm deals damage.
LETHAL_KINDS: frozenset[EffectKind] = frozenset({
    EffectKind.DAMAGE, EffectKind.BURN, EffectKind.EXPLODE,
    EffectKind.PIERCE, EffectKind.CHAIN, EffectKind.SUMMON,
})
CONTROL_KINDS: frozenset[EffectKind] = frozenset({
    EffectKind.KNOCKBACK, EffectKind.LAUNCH, EffectKind.STAGGER,
    EffectKind.SNARE, EffectKind.SLOW, EffectKind.FREEZE,
})
SELF_KINDS: frozenset[EffectKind] = frozenset({
    EffectKind.HEAL, EffectKind.SHIELD, EffectKind.SPEED,
})
UTILITY_KINDS: frozenset[EffectKind] = frozenset({EffectKind.LURE})

MELEE_DELIVERIES: frozenset[Delivery] = frozenset({
    Delivery.SWING, Delivery.THRUST, Delivery.SLAM, Delivery.WHIP,
})


# --- output schema ---
class Effect(BaseModel):
    kind: EffectKind
    amount: float = 0.0
    duration: float = 0.0
    radius: float = 0.0
    count: int = 0
    note: str = ""


class Stage(BaseModel):
    trigger: Trigger
    effects: list[Effect]
    note: str = ""


class GadgetDraft(BaseModel):
    """Model-facing output. ONLY model-owned fields live here."""
    name: str
    description: str
    logic: str
    stages: list[Stage]


@dataclass
class ResolvedGadget:
    """Code-assembled final artifact. Code owns everything but `draft`."""
    draft: GadgetDraft
    delivery: Delivery
    tier: Tier
    category: Category
    harmless: bool
    color: str
    params: dict[str, float] = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_contract.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add resolver/contract.py tests/test_contract.py
git commit -m "feat: capability contract enums and output schema"
```

---

### Task 3: Item catalog, builds, delivery lock, params

**Files:**
- Create: `resolver/items.py`
- Test: `tests/test_items.py`

**Interfaces:**
- Consumes: `resolver.contract` (`Delivery`, `MELEE_DELIVERIES`).
- Produces:
  - `@dataclass Item(name: str, associations: list[str])`.
  - `@dataclass Build(delivery_item: Item, damage_item: Item|None=None, utility_item: Item|None=None, modifier_item: Item|None=None)` with read-only properties `delivery -> Delivery` and `color -> str`, and method `slots() -> list[tuple[str, Item|None]]` returning `[("delivery", item), ("damage", item_or_None), ("utility", ...), ("modifier", ...)]`.
  - `CATALOG: dict[str, Item]` (~8 items).
  - `DELIVERY_LOCK: dict[str, Delivery]` (delivery-capable items only).
  - `COLOR_BY_ITEM: dict[str, str]`.
  - `DEFAULT_BUILDS: dict[str, Build]` (keys: `"broom+oil"`, `"aerosol+candles"`, `"fan+duck"`).
  - `params_for(delivery: Delivery) -> dict[str, float]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_items.py`:

```python
import pytest

from resolver.contract import Delivery
from resolver.items import (
    Item, Build, CATALOG, DELIVERY_LOCK, DEFAULT_BUILDS, params_for,
)


def test_catalog_has_rich_association_clouds():
    assert len(CATALOG) >= 8
    for item in CATALOG.values():
        assert len(item.associations) >= 3  # obvious -> non-obvious -> chainable


def test_build_locks_delivery_from_the_delivery_item():
    build = Build(delivery_item=CATALOG["push broom"], utility_item=CATALOG["spilled fry oil"])
    assert build.delivery is Delivery.SWING


def test_build_color_comes_from_delivery_item():
    build = Build(delivery_item=CATALOG["push broom"])
    assert build.color == "amber"


def test_build_rejects_non_delivery_item_in_delivery_slot():
    with pytest.raises(ValueError):
        _ = Build(delivery_item=CATALOG["rubber duck"]).delivery


def test_build_slots_lists_all_four_in_order():
    build = Build(delivery_item=CATALOG["push broom"], utility_item=CATALOG["spilled fry oil"])
    labels = [label for label, _ in build.slots()]
    assert labels == ["delivery", "damage", "utility", "modifier"]


def test_default_builds_cover_three_delivery_families():
    deliveries = {b.delivery for b in DEFAULT_BUILDS.values()}
    assert deliveries == {Delivery.SWING, Delivery.SPRAY, Delivery.PLACED}


def test_params_for_melee_and_ranged_families():
    melee = params_for(Delivery.SWING)
    assert set(melee) == {"reach", "arc", "commit", "sweep_targets"}
    ranged = params_for(Delivery.SPRAY)
    assert set(ranged) == {"range", "projectile_speed", "spread", "homing"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_items.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.items'`.

- [ ] **Step 3: Write the implementation**

Create `resolver/items.py`:

```python
"""Invented junk catalog with tiered association clouds, build assembly, and
the delivery-lock map. The association clouds are half the system: the model
can only be as clever as the associations fed to it.
"""
from __future__ import annotations

from dataclasses import dataclass

from resolver.contract import Delivery, MELEE_DELIVERIES


@dataclass(frozen=True)
class Item:
    name: str
    # ordered obvious -> non-obvious -> chainable-consequence
    associations: list[str]


_ITEMS: list[Item] = [
    Item("push broom", [
        "a long, swingable handle with reach",
        "stiff bristles that soak up and hold liquid",
        "sweeps wide across the floor in one motion",
        "drag the bristles fast enough and whatever they hold gets flung in an arc",
    ]),
    Item("mop", [
        "long reach on a pole",
        "loose strands that tangle and snag",
        "the strands drink and hold liquid",
        "a soaked mop-head flung fast sheds its load in a spray",
    ]),
    Item("spilled fry oil", [
        "greasy and slippery underfoot",
        "flammable once it is hot enough",
        "clings to and coats whatever it touches",
        "a slick left on the ground drops anyone who crosses it",
    ]),
    Item("birthday candles", [
        "many tiny open flames",
        "drip hot wax as they burn",
        "the trick kind relight themselves after being blown out",
        "packed together they are a fistful of little ignition sources",
    ]),
    Item("aerosol can", [
        "sprays a fine pressurized mist",
        "the propellant is flammable",
        "the can bursts if it gets too hot",
        "a mist plus a spark becomes a gout of flame",
    ]),
    Item("car battery", [
        "dead-weight heavy",
        "holds a charge that arcs across a gap",
        "leaks corrosive acid",
        "a hard enough knock cracks the case and spills the acid",
    ]),
    Item("rubber duck", [
        "buoyant and harmless-looking",
        "squeaks loudly when squeezed",
        "an obvious decoy nobody takes seriously",
        "its squeak draws attention to wherever you leave it",
    ]),
    Item("box fan", [
        "pushes a steady wall of air",
        "spinning blades behind a thin grille",
        "shoves light objects across the floor",
        "aimed down a hall it can carry mist, dust, or heat with the airflow",
    ]),
]

CATALOG: dict[str, Item] = {item.name: item for item in _ITEMS}

# Only delivery-capable items appear here; the delivery item fixes the form.
DELIVERY_LOCK: dict[str, Delivery] = {
    "push broom": Delivery.SWING,
    "mop": Delivery.SWING,
    "aerosol can": Delivery.SPRAY,
    "box fan": Delivery.PLACED,
    "car battery": Delivery.THROWN,
}

COLOR_BY_ITEM: dict[str, str] = {
    "push broom": "amber",
    "mop": "grey",
    "aerosol can": "hiss-white",
    "box fan": "dust-grey",
    "car battery": "acid-green",
}


@dataclass
class Build:
    delivery_item: Item
    damage_item: Item | None = None
    utility_item: Item | None = None
    modifier_item: Item | None = None

    @property
    def delivery(self) -> Delivery:
        try:
            return DELIVERY_LOCK[self.delivery_item.name]
        except KeyError as exc:
            raise ValueError(
                f"{self.delivery_item.name!r} cannot be a delivery chassis"
            ) from exc

    @property
    def color(self) -> str:
        return COLOR_BY_ITEM.get(self.delivery_item.name, "grey")

    def slots(self) -> list[tuple[str, Item | None]]:
        return [
            ("delivery", self.delivery_item),
            ("damage", self.damage_item),
            ("utility", self.utility_item),
            ("modifier", self.modifier_item),
        ]


DEFAULT_BUILDS: dict[str, Build] = {
    # melee: the prompt's hero example (cross-check against the doc samples)
    "broom+oil": Build(
        delivery_item=CATALOG["push broom"],
        utility_item=CATALOG["spilled fry oil"],
    ),
    # ranged/spray: flammable interaction
    "aerosol+candles": Build(
        delivery_item=CATALOG["aerosol can"],
        damage_item=CATALOG["birthday candles"],
    ),
    # not-a-weapon: forces the CONTROL/UTILITY/harmless path
    "fan+duck": Build(
        delivery_item=CATALOG["box fan"],
        utility_item=CATALOG["rubber duck"],
    ),
}


def params_for(delivery: Delivery) -> dict[str, float]:
    """Per-delivery-family renderer params (v0 stubs; feel-tuned later)."""
    if delivery in MELEE_DELIVERIES:
        return {"reach": 150.0, "arc": 90.0, "commit": 0.4, "sweep_targets": 2.0}
    if delivery is Delivery.GUARD:
        return {"block_arc": 120.0, "parry_window": 0.3}
    if delivery in (Delivery.SELF, Delivery.DASH):
        return {"distance": 300.0, "self_duration": 3.0}
    # ranged / thrown / placed / spray / beam / hitscan / projectile / lobbed
    return {"range": 800.0, "projectile_speed": 1200.0, "spread": 10.0, "homing": 0.0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_items.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add resolver/items.py tests/test_items.py
git commit -m "feat: junk catalog, build assembly, delivery lock, params"
```

---

### Task 4: The clamp — code-owned balance (TDD this hard)

**Files:**
- Create: `resolver/clamp.py`
- Test: `tests/test_clamp.py`

**Interfaces:**
- Consumes: `resolver.contract` (all enums, `Effect`, `Stage`, `GadgetDraft`, `ResolvedGadget`, family sets), `resolver.items` (`Build`, `params_for`).
- Produces:
  - `TIER_BUDGET: dict[Tier, float]`, `OVER_BUDGET_FACTOR: float = 1.12`, `DUD_FLOOR: float = 1.0`.
  - `total_magnitude(draft: GadgetDraft) -> float` (sum of all `effect.amount`).
  - `clamp_magnitudes(draft: GadgetDraft, tier: Tier) -> GadgetDraft` (proportional scale to the tier's `budget * OVER_BUDGET_FACTOR` ceiling; scale up to `DUD_FLOOR` when nonzero-but-tiny; returns a new draft).
  - `derive_harmless(draft: GadgetDraft) -> bool`.
  - `derive_category(draft: GadgetDraft) -> Category`.
  - `apply(draft: GadgetDraft, build: Build, tier: Tier) -> ResolvedGadget`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_clamp.py`:

```python
from resolver.contract import (
    Category, Delivery, Effect, EffectKind, GadgetDraft, Stage, Tier,
)
from resolver.items import Build, CATALOG
from resolver import clamp


def _draft(*effects: Effect) -> GadgetDraft:
    return GadgetDraft(
        name="t", description="", logic="",
        stages=[Stage(trigger=Trigger_ON_HIT(), effects=list(effects))],
    )


def Trigger_ON_HIT():
    from resolver.contract import Trigger
    return Trigger.ON_HIT


def test_total_magnitude_sums_amounts():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=10), Effect(kind=EffectKind.BURN, amount=5))
    assert clamp.total_magnitude(d) == 15


def test_over_budget_is_scaled_down_to_the_cap():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=1000))
    out = clamp.clamp_magnitudes(d, Tier.LEGENDARY)
    cap = clamp.TIER_BUDGET[Tier.LEGENDARY] * clamp.OVER_BUDGET_FACTOR
    assert clamp.total_magnitude(out) <= cap + 1e-6
    assert clamp.total_magnitude(out) == cap  # scaled exactly to the ceiling


def test_dud_over_budget_scales_down_hard():
    d = _draft(Effect(kind=EffectKind.KNOCKBACK, amount=120))
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    cap = clamp.TIER_BUDGET[Tier.DUD] * clamp.OVER_BUDGET_FACTOR
    assert clamp.total_magnitude(out) == cap


def test_tiny_nonzero_draft_is_raised_to_the_floor():
    d = _draft(Effect(kind=EffectKind.STAGGER, amount=0.2))
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    assert clamp.total_magnitude(out) == clamp.DUD_FLOOR


def test_empty_draft_is_left_alone():
    d = GadgetDraft(name="t", description="", logic="", stages=[])
    out = clamp.clamp_magnitudes(d, Tier.DUD)
    assert clamp.total_magnitude(out) == 0


def test_harmless_true_when_only_control_and_lure():
    d = _draft(Effect(kind=EffectKind.SNARE, amount=1), Effect(kind=EffectKind.LURE, amount=1))
    assert clamp.derive_harmless(d) is True


def test_harmless_false_when_any_damage_family():
    d = _draft(Effect(kind=EffectKind.BURN, amount=1))
    assert clamp.derive_harmless(d) is False


def test_category_weapon_for_lethal():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=5))
    assert clamp.derive_category(d) is Category.WEAPON


def test_category_control_for_control_only():
    d = _draft(Effect(kind=EffectKind.SNARE, amount=1))
    assert clamp.derive_category(d) is Category.CONTROL


def test_category_support_for_self_only():
    d = _draft(Effect(kind=EffectKind.HEAL, amount=1))
    assert clamp.derive_category(d) is Category.SUPPORT


def test_category_utility_for_lure_only():
    d = _draft(Effect(kind=EffectKind.LURE, amount=1))
    assert clamp.derive_category(d) is Category.UTILITY


def test_category_dud_for_empty():
    d = GadgetDraft(name="t", description="", logic="", stages=[])
    assert clamp.derive_category(d) is Category.DUD


def test_apply_assembles_code_owned_fields_from_build():
    build = Build(delivery_item=CATALOG["push broom"], utility_item=CATALOG["spilled fry oil"])
    d = _draft(Effect(kind=EffectKind.BURN, amount=14), Effect(kind=EffectKind.KNOCKBACK, amount=120))
    rg = clamp.apply(d, build, Tier.LEGENDARY)
    assert rg.delivery is Delivery.SWING
    assert rg.color == "amber"
    assert rg.tier is Tier.LEGENDARY
    assert rg.category is Category.WEAPON
    assert rg.harmless is False
    assert set(rg.params) == {"reach", "arc", "commit", "sweep_targets"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_clamp.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.clamp'`.

- [ ] **Step 3: Write the implementation**

Create `resolver/clamp.py`:

```python
"""The deterministic clamp: code owns balance.

Re-derives `harmless` and `category` from the effects the model actually
produced (never trusted from the model) and enforces a per-tier magnitude
budget with the ~10-15% over-budget cap from GAME_IDENTITY §6. The tier
budget numbers are v0 placeholders owned by code; they will churn once the
renderer is real. The job here is to prove the model->code ownership split
works end to end, not to finalize balance.
"""
from __future__ import annotations

import copy

from resolver.contract import (
    Category, GadgetDraft, ResolvedGadget, Tier,
    LETHAL_KINDS, CONTROL_KINDS, SELF_KINDS, UTILITY_KINDS,
)
from resolver.items import Build, params_for

TIER_BUDGET: dict[Tier, float] = {
    Tier.DUD: 6.0,
    Tier.COMMON: 16.0,
    Tier.UNCOMMON: 28.0,
    Tier.RARE: 48.0,
    Tier.EPIC: 80.0,
    Tier.LEGENDARY: 120.0,
}
OVER_BUDGET_FACTOR: float = 1.12  # the ~10-15% over-budget cap
DUD_FLOOR: float = 1.0            # a DUD is pathetic, never literally nothing


def total_magnitude(draft: GadgetDraft) -> float:
    return sum(e.amount for stage in draft.stages for e in stage.effects)


def _scale(draft: GadgetDraft, factor: float) -> GadgetDraft:
    out = copy.deepcopy(draft)
    for stage in out.stages:
        for e in stage.effects:
            e.amount *= factor
    return out


def clamp_magnitudes(draft: GadgetDraft, tier: Tier) -> GadgetDraft:
    total = total_magnitude(draft)
    if total == 0:
        return copy.deepcopy(draft)
    cap = TIER_BUDGET[tier] * OVER_BUDGET_FACTOR
    if total > cap:
        return _scale(draft, cap / total)
    if total < DUD_FLOOR:
        return _scale(draft, DUD_FLOOR / total)
    return copy.deepcopy(draft)


def _kinds(draft: GadgetDraft) -> set:
    return {e.kind for stage in draft.stages for e in stage.effects}


def derive_harmless(draft: GadgetDraft) -> bool:
    return not (_kinds(draft) & LETHAL_KINDS)


def derive_category(draft: GadgetDraft) -> Category:
    kinds = _kinds(draft)
    if not kinds:
        return Category.DUD
    if kinds & LETHAL_KINDS:
        return Category.WEAPON
    if kinds & CONTROL_KINDS:
        return Category.CONTROL
    if kinds & SELF_KINDS:
        return Category.SUPPORT
    if kinds & UTILITY_KINDS:
        return Category.UTILITY
    return Category.TRINKET


def apply(draft: GadgetDraft, build: Build, tier: Tier) -> ResolvedGadget:
    clamped = clamp_magnitudes(draft, tier)
    return ResolvedGadget(
        draft=clamped,
        delivery=build.delivery,
        tier=tier,
        category=derive_category(clamped),
        harmless=derive_harmless(clamped),
        color=build.color,
        params=params_for(build.delivery),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_clamp.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add resolver/clamp.py tests/test_clamp.py
git commit -m "feat: deterministic clamp (budget, harmless, category)"
```

---

### Task 5: Hardened prompt file + user-message renderer

**Files:**
- Create: `resolver/prompts/system_prompt.txt`
- Create: `resolver/prompt.py`
- Modify: `docs/RESOLVER_PROMPT_v0.md` (replace the `## SYSTEM PROMPT` body with the hardened text so the doc mirrors the runtime file)
- Test: `tests/test_prompt.py`

**Interfaces:**
- Consumes: `resolver.contract` (`Tier`), `resolver.items` (`Build`).
- Produces:
  - `SYSTEM_PROMPT: str` (loaded from `resolver/prompts/system_prompt.txt`).
  - `render_user_message(build: Build, tier: Tier) -> str`.

- [ ] **Step 1: Create the hardened prompt file**

Create `resolver/prompts/system_prompt.txt` with this exact content (jargon-free; scrubs "diver / jack-in / signature / the simulation"; keeps only fiction that is behavioral instruction):

```
You are an engine that decides what a jury-rigged contraption does. Someone has jammed a few ordinary objects together and is trying to make a weapon or gadget out of them. Your job is to decide what that combination becomes: read the objects honestly, then let their real properties collide into something the maker did not quite expect.

Treat this as a world where ordinary objects can produce extraordinary effects. Imagination is the only limit, so be willing to be absurd, as long as every effect still traces back to a real property of the objects given.

The core rule: the obvious reading is the weak one. A mop is a thing you bonk people with; that is the boring answer, and boring is a low-tier result. The interesting answer reads a deeper, truer property of the object: a mop soaks up liquid, its strands tangle, it has a long swingable handle. Good results come from the non-obvious property. Great results come from chaining properties into consequences: the mop soaks up a flammable puddle, so when it strikes, the soaked strands ignite. Always look past the first thing an object "is."

Composition is where the surprise lives. You have a fixed set of delivery forms, effect primitives, and triggers (below). You cannot invent new ones, but you can arrange them freely into stages that fire in sequence. "Swing, then on hit stagger, then on kill release a swarm" is three ordinary primitives composed into something memorable. The surprise is in the arrangement and the reading, never in a new verb. Chain consequences across triggers; let one stage's outcome set up the next.

Read the specific objects you are given. Your result must trace back to real, stated properties of these objects. The maker should be able to see why this junk made this thing. Explain that trace in the logic field. Never cite a property that is not there.

Most combinations are not weapons, and that is honest. Junk that cannot hurt anyone becomes a control tool, a support item, a utility, or a trinket, not a weapon with a damage number bolted on. Do not force lethality. A thing that snares and lures is a control tool; describe it as one. Be truthful about what the effects actually are.

Coherence rule: effects that assume damage (PIERCE, CHAIN, EXPLODE as a killing burst) only belong on something that also deals damage. Do not attach a piercing rider to a heal.

The vocabulary. Pick effects by behavior, not vibe.
- Delivery (the form; this is LOCKED and given to you, do not change it): the delivery-slot object fixes the form. You compose within that form.
- Effects: damage family (DAMAGE, BURN, EXPLODE, PIERCE, CHAIN); control family (KNOCKBACK, LAUNCH, STAGGER, SNARE, SLOW, FREEZE); self family (HEAL, SHIELD, SPEED); other (SUMMON, LURE).
- Triggers: ON_USE, ON_HIT, ON_IMPACT, ON_TRIGGER, ON_EXPIRE, ON_KILL, ON_BLOCK.

The tier you are composing for. You will be told a target tier. The tier is your ambition and budget: how inventive and interconnected this result should be. Compose honestly to the tier; do not exceed it, do not phone it in below it.
- DUD: the junk barely cooperates. One weak effect, the obvious-or-failed reading, minimal. Slightly pathetic but not broken.
- COMMON: functional. One clear effect, one clean reading. Does its job, no surprises.
- UNCOMMON: a second beat. Two effects or a two-stage sequence; one mildly clever reading.
- RARE: a genuine interaction. The objects' properties combine; a non-obvious reading drives it; stages set each other up.
- EPIC: inventive and interconnected. Multi-stage, a reading the maker would not have guessed, effects that feed each other.
- LEGENDARY: inspired. It feels discovered, not assembled: the objects' properties chain into a consequence that is genuinely surprising and a little unhinged, while still tracing honestly back to what the junk actually is. This is the top roll. Earn it.

Same objects at DUD and at LEGENDARY should feel like the same junk seen by a sleeping mind versus a lucid one: not different objects, different depth of reading.

Naming. Give it a name a person would grin at. No mechanic-words in the name (not "Snare Launcher"; call it something with character). The name sells the fantasy; the logic field explains the trick.

Output. Fill the structured schema: name, stages (each with a trigger and effects, each effect with amount / duration / radius / count and a short note), description (flavor), and logic (the trace: how you read each object). Keep magnitudes in sane ranges. The delivery form, tier, category, and whether it is harmless are decided by code, not by you; focus on the reading and the composition.

Example. Objects: delivery = push broom (a long swingable handle; stiff bristles that soak up and hold liquid; sweeps wide), utility = spilled fry oil (slippery; flammable; clings and coats). Target DUD:
  name: "Damp Sweep"
  logic: "A broom is a broom. The oil just makes it slippery and awkward. The maker waves a wet broom around."
  stages: ON_HIT -> STAGGER (amount 1, duration 0.4, note "a clumsy shove, barely a stumble")
  description: "It is a broom. It is wet. Swing it and hope."

Same objects. Target LEGENDARY:
  name: "Last Call"
  logic: "The broom's bristles drink the fry oil and hold it. The long handle gives a wide sweep. Oil-soaked bristles dragged fast enough heat and fling burning grease in an arc, and the slick it leaves underfoot drops anything that follows."
  stages:
    ON_HIT -> BURN (amount 14, duration 3, note "flung searing grease coats the target"), KNOCKBACK (amount 120, note "the wide sweep shoves them back into the slick")
    ON_EXPIRE -> SLOW (amount 0.5, duration 4, radius 200, note "the oil pooled underfoot; anyone crossing it skates")
  description: "A janitor's broom that learned to hold a grudge and a grease fire."

The LEGENDARY version reads bristles-hold-liquid and long-handle-wide-arc and oil-is-flammable-and-slippery, then chains them. The DUD read none of that. That gap is the spread.
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_prompt.py`:

```python
from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS
from resolver.prompt import SYSTEM_PROMPT, render_user_message


def test_system_prompt_is_loaded_and_jargon_free():
    assert len(SYSTEM_PROMPT) > 500
    lowered = SYSTEM_PROMPT.lower()
    for banned in ("diver", "jack-in", "jack in", "signature", "the simulation"):
        assert banned not in lowered


def test_render_user_message_includes_slots_associations_delivery_and_tier():
    build = DEFAULT_BUILDS["broom+oil"]
    msg = render_user_message(build, Tier.RARE)
    assert "delivery:" in msg and "push broom" in msg
    assert "utility:" in msg and "spilled fry oil" in msg
    assert "damage:" in msg and "empty" in msg  # unfilled slot shows "empty"
    assert "LOCKED DELIVERY FORM: SWING" in msg
    assert "TARGET TIER: RARE" in msg
    # at least one association from the delivery item is injected
    assert "bristles" in msg
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_prompt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.prompt'`.

- [ ] **Step 4: Write the implementation**

Create `resolver/prompt.py`:

```python
"""Loads the hardened, jargon-free system prompt and renders the per-build
user message. The prompt is data (a text file), not code, so it can be
iterated between test runs without touching Python.
"""
from __future__ import annotations

from pathlib import Path

from resolver.contract import Tier
from resolver.items import Build

_PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"
SYSTEM_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8").strip()

_TEMPLATE = """BUILD
  delivery: {delivery}
  damage:   {damage}
  utility:  {utility}
  modifier: {modifier}

LOCKED DELIVERY FORM: {form}
TARGET TIER: {tier}

Resolve this build to the target tier. Trace every effect back to a stated
property of the specific objects above. Compose within the locked delivery form."""


def _slot_line(item) -> str:
    if item is None:
        return "empty"
    return f"{item.name} — {', '.join(item.associations)}"


def render_user_message(build: Build, tier: Tier) -> str:
    slots = dict(build.slots())
    return _TEMPLATE.format(
        delivery=_slot_line(slots["delivery"]),
        damage=_slot_line(slots["damage"]),
        utility=_slot_line(slots["utility"]),
        modifier=_slot_line(slots["modifier"]),
        form=build.delivery.value,
        tier=tier.value,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_prompt.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Mirror the hardened prompt into the design doc**

Open `docs/RESOLVER_PROMPT_v0.md`. Replace the prose under the `## SYSTEM PROMPT` heading (down to but not including `## USER MESSAGE (template)`) with the exact text of `resolver/prompts/system_prompt.txt`, so the doc reflects the shipped prompt. Leave the rest of the doc (the user-message template section and the notes) intact. Add a one-line note directly under `## SYSTEM PROMPT`:

```markdown
> Runtime source of truth: `resolver/prompts/system_prompt.txt`. This section mirrors it.
```

- [ ] **Step 7: Commit**

```
git add resolver/prompts/system_prompt.txt resolver/prompt.py tests/test_prompt.py docs/RESOLVER_PROMPT_v0.md
git commit -m "feat: hardened jargon-free system prompt and user-message renderer"
```

---

### Task 6: Deterministic fallback resolver

**Files:**
- Create: `resolver/fallback.py`
- Test: `tests/test_fallback.py`

**Interfaces:**
- Consumes: `resolver.contract` (`Effect`, `EffectKind`, `GadgetDraft`, `Stage`, `Tier`, `Trigger`), `resolver.items` (`Build`).
- Produces: `resolve(build: Build, tier: Tier) -> GadgetDraft` — deterministic, no API. Signature is interchangeable with the LLM resolver's `resolve`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fallback.py`:

```python
from resolver.contract import EffectKind, GadgetDraft, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver import fallback


def test_fallback_returns_a_valid_draft_with_no_api():
    draft = fallback.resolve(DEFAULT_BUILDS["broom+oil"], Tier.COMMON)
    assert isinstance(draft, GadgetDraft)
    assert draft.name
    assert draft.logic
    assert len(draft.stages) == 1
    assert draft.stages[0].trigger is Trigger.ON_HIT
    assert draft.stages[0].effects[0].kind is EffectKind.DAMAGE


def test_fallback_is_deterministic():
    a = fallback.resolve(DEFAULT_BUILDS["aerosol+candles"], Tier.EPIC)
    b = fallback.resolve(DEFAULT_BUILDS["aerosol+candles"], Tier.EPIC)
    assert a.model_dump() == b.model_dump()


def test_fallback_scales_amount_with_tier():
    dud = fallback.resolve(DEFAULT_BUILDS["broom+oil"], Tier.DUD)
    leg = fallback.resolve(DEFAULT_BUILDS["broom+oil"], Tier.LEGENDARY)
    assert leg.stages[0].effects[0].amount > dud.stages[0].effects[0].amount
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fallback.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.fallback'`.

- [ ] **Step 3: Write the implementation**

Create `resolver/fallback.py`:

```python
"""Deterministic fallback resolver: keeps the whole pipeline functional with
no API key. Produces a valid but deliberately boring draft (the obvious
reading, one effect, scaled to the tier). Its signature matches the LLM
resolver's `resolve`, so the harness can swap them freely.
"""
from __future__ import annotations

from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Tier, Trigger
from resolver.items import Build

# A crude per-tier amount so the fallback still shows a dud->god shape.
_TIER_AMOUNT: dict[Tier, float] = {
    Tier.DUD: 2.0,
    Tier.COMMON: 6.0,
    Tier.UNCOMMON: 10.0,
    Tier.RARE: 18.0,
    Tier.EPIC: 30.0,
    Tier.LEGENDARY: 45.0,
}


def resolve(build: Build, tier: Tier) -> GadgetDraft:
    delivery_item = build.delivery_item
    amount = _TIER_AMOUNT[tier]
    return GadgetDraft(
        name=f"Improvised {delivery_item.name.title()}",
        description=f"A {delivery_item.name} swung in anger. It works, barely.",
        logic=(
            f"The obvious reading: {delivery_item.name} — "
            f"{delivery_item.associations[0]}. Nothing clever, just the first thing it is."
        ),
        stages=[
            Stage(
                trigger=Trigger.ON_HIT,
                effects=[Effect(kind=EffectKind.DAMAGE, amount=amount, note="a plain hit")],
                note="the obvious reading",
            )
        ],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fallback.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add resolver/fallback.py tests/test_fallback.py
git commit -m "feat: deterministic fallback resolver (no API dependency)"
```

---

### Task 7: LLM resolver (structured output, injectable client)

**Files:**
- Create: `resolver/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `resolver.contract` (`GadgetDraft`), `resolver.prompt` (`SYSTEM_PROMPT`, `render_user_message`), `resolver.items` (`Build`), `resolver.contract` (`Tier`).
- Produces: `class LLMResolver` with `__init__(self, client, model: str)` and `resolve(self, build: Build, tier: Tier) -> GadgetDraft`. `client` is any object exposing `messages.parse(...)` (the real `anthropic.Anthropic()` or a fake).

- [ ] **Step 1: Write the failing test (fake client — no tokens spent)**

Create `tests/test_llm.py`:

```python
from types import SimpleNamespace

from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Tier, Trigger
from resolver.items import DEFAULT_BUILDS
from resolver.llm import LLMResolver
from resolver.prompt import SYSTEM_PROMPT


class FakeMessages:
    def __init__(self, canned):
        self.canned = canned
        self.captured = None

    def parse(self, **kwargs):
        self.captured = kwargs
        return SimpleNamespace(parsed_output=self.canned)


class FakeClient:
    def __init__(self, canned):
        self.messages = FakeMessages(canned)


def _canned_draft():
    return GadgetDraft(
        name="Fake", description="", logic="",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.DAMAGE, amount=1)])],
    )


def test_resolver_returns_the_parsed_draft():
    client = FakeClient(_canned_draft())
    resolver = LLMResolver(client, model="claude-sonnet-5")
    out = resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    assert out.name == "Fake"


def test_resolver_wires_the_call_correctly():
    client = FakeClient(_canned_draft())
    resolver = LLMResolver(client, model="claude-sonnet-5")
    resolver.resolve(DEFAULT_BUILDS["broom+oil"], Tier.RARE)
    call = client.messages.captured
    assert call["model"] == "claude-sonnet-5"
    assert call["system"] == SYSTEM_PROMPT
    assert call["output_format"] is GadgetDraft
    assert "TARGET TIER: RARE" in call["messages"][0]["content"]
    # no sampling params — current Sonnet rejects non-default temperature/top_p/top_k
    assert "temperature" not in call and "top_p" not in call and "top_k" not in call
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.llm'`.

- [ ] **Step 3: Write the implementation**

Create `resolver/llm.py`:

```python
"""LLM resolver: proposes the creative composition via structured output.

The Anthropic client is injected so the harness can use a real client at
runtime and a fake client in tests (creativity itself is not unit-testable;
this is a contract test of the wiring). This is offline/frontier generation,
never a runtime hot path.
"""
from __future__ import annotations

from resolver.contract import GadgetDraft, Tier
from resolver.items import Build
from resolver.prompt import SYSTEM_PROMPT, render_user_message


class LLMResolver:
    def __init__(self, client, model: str) -> None:
        self.client = client
        self.model = model

    def resolve(self, build: Build, tier: Tier) -> GadgetDraft:
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": render_user_message(build, tier)}],
            output_format=GadgetDraft,
        )
        return response.parsed_output
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_llm.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add resolver/llm.py tests/test_llm.py
git commit -m "feat: LLM resolver with injectable client (structured output)"
```

---

### Task 8: Human-readable renderer

**Files:**
- Create: `resolver/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `resolver.contract` (`ResolvedGadget`).
- Produces:
  - `@dataclass RunResult(build_key: str, resolved: ResolvedGadget, run_index: int, run_total: int)`.
  - `render_run(results: list[RunResult]) -> str` — groups by `build_key` in first-seen order, prints a build header (delivery + color) then, per result, tier + category + harmless + the name/logic/staged effects.

- [ ] **Step 1: Write the failing test**

Create `tests/test_render.py`:

```python
from resolver.contract import (
    Category, Delivery, Effect, EffectKind, GadgetDraft, ResolvedGadget, Stage, Tier, Trigger,
)
from resolver.render import RunResult, render_run


def _resolved(name, tier, category, harmless):
    draft = GadgetDraft(
        name=name, description="flavor", logic="the trace",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[Effect(kind=EffectKind.BURN, amount=14, duration=3, note="grease")])],
    )
    return ResolvedGadget(
        draft=draft, delivery=Delivery.SWING, tier=tier,
        category=category, harmless=harmless, color="amber", params={},
    )


def test_render_groups_by_build_and_shows_both_axes():
    results = [
        RunResult("broom+oil", _resolved("Damp Sweep", Tier.DUD, Category.WEAPON, False), 1, 1),
        RunResult("broom+oil", _resolved("Last Call", Tier.LEGENDARY, Category.WEAPON, False), 1, 3),
        RunResult("broom+oil", _resolved("Second Round", Tier.LEGENDARY, Category.WEAPON, False), 2, 3),
    ]
    out = render_run(results)
    assert "broom+oil" in out
    assert "SWING" in out and "amber" in out
    assert "DUD" in out and "LEGENDARY" in out       # depth across tiers
    assert "Damp Sweep" in out and "Last Call" in out
    assert "the trace" in out                        # logic is shown
    assert "BURN" in out                             # staged effect is shown
    assert "[run 2/3]" in out                        # variety-within-tier instances labelled


def test_render_prints_build_header_once_per_build():
    results = [
        RunResult("broom+oil", _resolved("A", Tier.DUD, Category.WEAPON, False), 1, 1),
        RunResult("broom+oil", _resolved("B", Tier.COMMON, Category.WEAPON, False), 1, 1),
    ]
    out = render_run(results)
    assert out.count("BUILD: broom+oil") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'resolver.render'`.

- [ ] **Step 3: Write the implementation**

Create `resolver/render.py`:

```python
"""Human-readable output. Groups by build, then tier, so a person can eyeball
depth across tiers and variety within a tier in one scroll (not raw JSON).
"""
from __future__ import annotations

from dataclasses import dataclass

from resolver.contract import ResolvedGadget

_BAR = "=" * 60


@dataclass
class RunResult:
    build_key: str
    resolved: ResolvedGadget
    run_index: int
    run_total: int


def _render_effect(effect) -> str:
    bits = [effect.kind.value, f"a={effect.amount:g}"]
    if effect.duration:
        bits.append(f"d={effect.duration:g}")
    if effect.radius:
        bits.append(f"r={effect.radius:g}")
    if effect.count:
        bits.append(f"n={effect.count}")
    line = " ".join(bits)
    if effect.note:
        line += f'  "{effect.note}"'
    return line


def _render_one(result: RunResult) -> str:
    rg = result.resolved
    lines = [
        f"--- {rg.tier.value} ---  ({rg.category.value}, harmless={rg.harmless})  "
        f"[run {result.run_index}/{result.run_total}]",
        f"  name:  {rg.draft.name}",
        f"  logic: {rg.draft.logic}",
        "  stages:",
    ]
    for stage in rg.draft.stages:
        lines.append(f"    {stage.trigger.value}:")
        for effect in stage.effects:
            lines.append(f"      {_render_effect(effect)}")
    return "\n".join(lines)


def render_run(results: list[RunResult]) -> str:
    out: list[str] = []
    seen: set[str] = set()
    for result in results:
        key = result.build_key
        if key not in seen:
            seen.add(key)
            rg = result.resolved
            out.append("")
            out.append(_BAR)
            out.append(f"BUILD: {key}   [delivery: {rg.delivery.value}, color: {rg.color}]")
            out.append(_BAR)
        out.append("")
        out.append(_render_one(result))
    return "\n".join(out).strip() + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_render.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add resolver/render.py tests/test_render.py
git commit -m "feat: human-readable spread renderer"
```

---

### Task 9: CLI harness (wires it together, degrades gracefully)

**Files:**
- Create: `resolver/harness.py`
- Test: `tests/test_harness.py`

**Interfaces:**
- Consumes: `resolver.contract` (`Tier`), `resolver.items` (`DEFAULT_BUILDS`), `resolver.clamp` (`apply`), `resolver.fallback` (`resolve`), `resolver.llm` (`LLMResolver`), `resolver.render` (`RunResult`, `render_run`).
- Produces:
  - `TIERS: list[Tier]`, `REPEAT_TIERS: list[Tier]`.
  - `tier_schedule(repeats: int) -> list[Tier]` — every tier once, plus `repeats-1` extra runs of each RARE/EPIC/LEGENDARY tier.
  - `run(resolver_fn, build_keys: list[str], repeats: int) -> list[RunResult]` — `resolver_fn` is any `callable(build, tier) -> GadgetDraft`.
  - `main(argv: list[str] | None = None) -> int` — argparse CLI; selects LLM vs fallback resolver and prints the spread.

- [ ] **Step 1: Write the failing test (drives the fallback path — no key needed)**

Create `tests/test_harness.py`:

```python
from resolver.contract import Tier
from resolver import fallback, harness


def test_tier_schedule_repeats_only_the_high_tiers():
    schedule = harness.tier_schedule(repeats=3)
    assert schedule.count(Tier.DUD) == 1
    assert schedule.count(Tier.COMMON) == 1
    assert schedule.count(Tier.UNCOMMON) == 1
    assert schedule.count(Tier.RARE) == 3
    assert schedule.count(Tier.EPIC) == 3
    assert schedule.count(Tier.LEGENDARY) == 3


def test_run_produces_one_result_per_scheduled_tier_per_build():
    results = harness.run(fallback.resolve, build_keys=["broom+oil"], repeats=3)
    # 3 singles (DUD/COMMON/UNCOMMON) + 3*3 high-tier = 12
    assert len(results) == 12
    assert all(r.build_key == "broom+oil" for r in results)
    # high-tier instances are labelled 1..3
    leg = [r for r in results if r.resolved.tier is Tier.LEGENDARY]
    assert sorted(r.run_index for r in leg) == [1, 2, 3]
    assert all(r.run_total == 3 for r in leg)


def test_main_runs_the_fallback_path_and_prints(capsys):
    exit_code = harness.main(["--fallback", "--build", "broom+oil", "--repeats", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "BUILD: broom+oil" in out
    assert "deterministic fallback" in out.lower()
    assert "LEGENDARY" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_harness.py -v`
Expected: FAIL with `AttributeError`/`ImportError` (no `harness` members yet).

- [ ] **Step 3: Write the implementation**

Create `resolver/harness.py`:

```python
"""CLI harness: runs builds across all six tiers (with repeats at the high
tiers), applies the code-owned clamp, and prints the spread. Runs live with
an API key; degrades to the deterministic fallback with none. This is an
offline generation harness, not a runtime path.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable

from resolver.clamp import apply as clamp_apply
from resolver.contract import GadgetDraft, Tier
from resolver.fallback import resolve as fallback_resolve
from resolver.items import DEFAULT_BUILDS, Build
from resolver.render import RunResult, render_run

ResolverFn = Callable[[Build, Tier], GadgetDraft]

TIERS: list[Tier] = [Tier.DUD, Tier.COMMON, Tier.UNCOMMON, Tier.RARE, Tier.EPIC, Tier.LEGENDARY]
REPEAT_TIERS: list[Tier] = [Tier.RARE, Tier.EPIC, Tier.LEGENDARY]

DEFAULT_MODEL = "claude-sonnet-5"


def tier_schedule(repeats: int) -> list[Tier]:
    schedule = list(TIERS)
    for tier in REPEAT_TIERS:
        schedule += [tier] * (repeats - 1)
    return schedule


def run(resolver_fn: ResolverFn, build_keys: list[str], repeats: int) -> list[RunResult]:
    results: list[RunResult] = []
    schedule = tier_schedule(repeats)
    for key in build_keys:
        build = DEFAULT_BUILDS[key]
        # per-tier instance counter so high-tier runs are labelled 1..repeats
        counters: dict[Tier, int] = {}
        totals: dict[Tier, int] = {t: schedule.count(t) for t in set(schedule)}
        for tier in schedule:
            counters[tier] = counters.get(tier, 0) + 1
            draft = resolver_fn(build, tier)
            resolved = clamp_apply(draft, build, tier)
            results.append(RunResult(key, resolved, counters[tier], totals[tier]))
    return results


def _build_resolver(use_fallback: bool, model: str) -> tuple[ResolverFn, str]:
    if use_fallback or not os.environ.get("ANTHROPIC_API_KEY"):
        return fallback_resolve, "deterministic fallback (no API)"
    import anthropic  # imported lazily so the fallback path needs no SDK auth

    from resolver.llm import LLMResolver

    return LLMResolver(anthropic.Anthropic(), model).resolve, f"live LLM ({model})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolver dud->god spread harness.")
    parser.add_argument("--build", action="append", dest="builds",
                        choices=list(DEFAULT_BUILDS), help="build key (repeatable; default all)")
    parser.add_argument("--repeats", type=int, default=3,
                        help="runs per high tier (RARE/EPIC/LEGENDARY); default 3")
    parser.add_argument("--model", default=os.environ.get("RESOLVER_MODEL", DEFAULT_MODEL),
                        help="model id (env RESOLVER_MODEL; default claude-sonnet-5)")
    parser.add_argument("--fallback", action="store_true",
                        help="force the deterministic fallback even if a key is set")
    args = parser.parse_args(argv)

    build_keys = args.builds or list(DEFAULT_BUILDS)
    resolver_fn, label = _build_resolver(args.fallback, args.model)

    print(f"resolver: {label}")
    print(f"builds:   {', '.join(build_keys)}")
    print(f"repeats:  {args.repeats} per high tier")

    results = run(resolver_fn, build_keys, args.repeats)
    print(render_run(results))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_harness.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: every test across all modules PASS.

- [ ] **Step 6: Smoke-run the CLI on the fallback path (no key)**

Run: `python -m resolver.harness --fallback --build broom+oil --repeats 2`
Expected: prints `resolver: deterministic fallback (no API)` and a grouped spread for `broom+oil` across all six tiers.

- [ ] **Step 7: Commit**

```
git add resolver/harness.py tests/test_harness.py
git commit -m "feat: CLI harness (live LLM + fallback, tier schedule)"
```

---

### Task 10: Live spread run (the actual experiment)

**Files:** none (produces console output / notes only).

**Interfaces:**
- Consumes: the whole harness.
- Produces: the empirical answer to "does the prompt produce range?" plus notes on where a cold model gets confused (feeds prompt iteration).

- [ ] **Step 1: Confirm the key is available**

Run: `python -c "import os; print('key set' if os.environ.get('ANTHROPIC_API_KEY') else 'NO KEY')"`
Expected: `key set`. (If not, the user sets `ANTHROPIC_API_KEY` in the environment, or runs `ant auth login`.)

- [ ] **Step 2: Run the full live spread (3 builds, ~45 calls, default Sonnet)**

Run: `python -m resolver.harness`
Expected: `resolver: live LLM (claude-sonnet-5)`, then all three default builds rendered across all six tiers with 3× at RARE/EPIC/LEGENDARY.

- [ ] **Step 3: Read the two axes and record the verdict**

Read the output and answer, in a short note back to the user:
- **Depth across tiers:** are DUD→LEGENDARY genuinely different *depths of reading*, not just bigger numbers?
- **Variety within a tier:** do the 3× RARE/EPIC/LEGENDARY instances differ in *character* (horizontal), not just wording?
- **Blandness check:** does it read the *non-obvious* property, or default to "bonk"? If bland at high tiers, the few-shot examples aren't strong enough — add more, weirder ones to `resolver/prompts/system_prompt.txt` and re-run.
- **Cold-model confusion:** note any place the model misread the task (jargon it still trips on, slots it ignored). Patch `system_prompt.txt` with *task-relevant* context only (never game lore) and re-run.

- [ ] **Step 4: Surface, don't silently decide, the open question**

If tier *headroom* appears to vary by combination (a tube/spray ladder taller than a sword ladder — GAME_IDENTITY §6 note), **flag it to the user** rather than baking an assumption into the harness.

- [ ] **Step 5 (optional): Commit any prompt tuning**

If `system_prompt.txt` was edited during Step 3, re-mirror it into `docs/RESOLVER_PROMPT_v0.md` (as in Task 5 Step 6) and commit:

```
git add resolver/prompts/system_prompt.txt docs/RESOLVER_PROMPT_v0.md
git commit -m "chore: tune resolver prompt from first cold-model outputs"
```

---

## Self-Review

**Spec coverage** (spec §-by-§ → task):
- §1 goal / §2 non-goals → Task 10 (the experiment); scope held throughout.
- §3 constraints → Global Constraints + enforced in Tasks 2 (schema wall), 4 (code owns balance), 7 (tier is input, no sampling params), 9 (fallback path, offline).
- §4 module layout → Tasks 2–9 (one module each) + Task 1 (scaffold).
- §5 contract & schema → Task 2 (incl. `GadgetDraft` model-only fields, `ResolvedGadget`).
- §6 ownership split / data flow → Task 4 `apply` + Task 9 `run`.
- §7 clamp (budget, over-budget cap, DUD floor, harmless, category) → Task 4.
- §8 item catalog (~8 items, rich clouds, delivery lock) → Task 3.
- §9 default run (3 builds, tiers + repeats, model env var) → Tasks 3 (builds) + 9 (schedule, model).
- §10 prompt hardening (jargon scrub, first-do, keep few-shots) → Task 5 + Task 10 Step 3.
- §11 LLM resolver (parse, injectable client, default Sonnet) → Task 7 + Task 9.
- §12 fallback → Task 6.
- §13 CLI (graceful degrade, flags, grouped output) → Task 9.
- §14 testing (TDD clamp/schema/items; contract-test LLM w/ fake) → Tasks 2,3,4,7 tests.
- §15 acceptance criteria → satisfied across Tasks 6/7/9 (degrade, wall, model swap) + Task 10 (legible axes).
- §16 open questions → Task 10 Steps 3–4 (surface, don't decide).
- §17 after-this → out of scope, noted.

**Placeholder scan:** no "TBD/TODO/handle edge cases/similar to Task N". Every code step shows complete code; every command shows expected output. The tier-budget *values* are intentional v0 placeholders (spec §16) with concrete numbers given, not gaps.

**Type consistency:** `GadgetDraft` fields `{name, description, logic, stages}` are identical in Tasks 2/5/6/7. `resolve(build, tier) -> GadgetDraft` signature matches across Task 6 (fallback) and Task 7 (`LLMResolver.resolve`) so Task 9's `ResolverFn` alias holds. `clamp.apply(draft, build, tier)` used consistently in Tasks 4 and 9. `RunResult(build_key, resolved, run_index, run_total)` defined in Task 8 and constructed in Task 9. `params_for`/`Build.delivery`/`Build.color` defined in Task 3 and consumed in Task 4. Family sets defined in Task 2 and consumed in Task 4.
