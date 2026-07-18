# Bake Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline bake pipeline (`resolver/bake/`) that generates depth-scaffold libraries per item-combo via LLM structured output, derives instances deterministically at read time, and proves itself with a real-dollar pilot over ~300 combos.

**Architecture:** New `resolver/bake/` subpackage beside (never inside) the runtime resolvers. One structured-output call per combo returns a `ScaffoldSet` (three `GadgetDraft` readings: shallow/medium/deep); records append to a git-tracked JSONL; `derive_instance` is a pure seeded function that turns (scaffold, build, tier, seed) into a byte-identical `ResolvedGadget` forever. Name uniqueness is a post-wave pass against a persistent global registry. Spec: `docs/superpowers/specs/2026-07-17-bake-pipeline-design.md`.

**Tech Stack:** Python ≥3.11, pydantic ≥2.6, anthropic ≥0.69 (structured output via `client.messages.parse(..., output_format=Model)`), pytest.

## Global Constraints

Every task's requirements implicitly include all of these.

- **The enums are the capability contract — never widen them.** The bake composes over contract v1 tokens only (`resolver/contract.py`).
- **Code owns every number.** Scaffold magnitudes are relative weights; `harmless`/`category` are always re-derived (`clamp.derive_harmless`/`derive_category`); the deriver produces every real magnitude.
- **Repair, never reject** (`resolver.validate.repair`). **Never a hard LLM dependency:** `select`, `derive`, `report` run keyless; `run`/`dedup` fail loud with a clear message when `ANTHROPIC_API_KEY` is absent — never a silent spend, never a crash mid-wave that loses data.
- **NEVER introspect why a call was refused.** Log rates only. Bake records and console output must not contain stop reasons, exception text, or any classification of a failure. (Standing AUP rule — a prior session was flagged for asking a model to categorize a refusal.)
- **Engine-agnostic:** zero engine references anywhere in `resolver/`.
- **No sampling params** on `messages.parse` calls (current Sonnet rejects non-default `temperature`/`top_p`/`top_k`).
- Windows live runs need `PYTHONUTF8=1`.
- Git: branch `main` only; **no remote — never push, never add one**. Conventional commits, one per task, ending with the trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. `git add` ONLY the files named in the task — the working tree holds intentionally-uncommitted files (`docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`, ten 2026-07-10 docs) that must never be staged.
- Baseline before Task 1: `python -m pytest -q` → 279 passed.
- Ladder default everywhere: `claude-sonnet-5` ×2 → `claude-opus-4-8` (reuse `resolver.harness.build_model_list`).
- Placeholder *values* (jitter width, budget band, top-up threshold, prices) are named constants; tuning them is renderer-era and out of scope — structure now, values later.

## File Structure

```
resolver/bake/__init__.py        # empty package marker
resolver/bake/schema.py          # Depth, ScaffoldSet, BakeRecord, combo_id, contract_fingerprint
resolver/bake/derive.py          # derive_instance + DEPTH_TIERS (pure)
resolver/bake/select.py          # PINNED_BUILDS + deterministic stratified selection
resolver/bake/run.py             # bake prompt loading, ladder calls, resumable JSONL, width + top-up
resolver/bake/dedup.py           # normalize, registry, collision detection, rename pass
resolver/bake/report.py          # per-wave markdown report + instance_seed
resolver/bake/__main__.py        # CLI: python -m resolver.bake <select|run|dedup|report>
resolver/prompts/bake_prompt.txt # depth-scaffold system prompt (data, not code)
resolver/clamp.py                # + fit_cost (public alias for _fit)
resolver/prompt.py               # _slot_line promoted to slot_line (public)
pyproject.toml                   # packages += resolver.bake
tests/test_bake_schema.py
tests/test_bake_derive.py
tests/test_bake_select.py
tests/test_bake_run.py
tests/test_bake_dedup.py
tests/test_bake_report.py
tests/test_bake_cli.py
data/bake/                       # created by the live pilot (Task 8), git-tracked
```

Two spec deviations, both forced by reality (surface them in the final summary):

1. The spec pins "fan+duck", but the rubber duck left the catalog in the 2026-07-12 rewrite — the build cannot be constructed. Its successor `probe_whimsical` (industrial fan + bag of marbles + expanding foam) is already among the six pinned probes. fan+duck is dropped.
2. The 9/9-refused build's powder item was never recorded (HANDOFF says "a powder item"). The plan pins a named reconstruction: extinguisher + roman candle + fan + **sack of fertilizer** (powder + ignition — the most refusal-prone powder). The pin's purpose is a refusal hot-spot, not archival fidelity.

---

### Task 1: Bake schema (`schema.py`)

**Files:**
- Create: `resolver/bake/__init__.py`
- Create: `resolver/bake/schema.py`
- Modify: `pyproject.toml` (packages list)
- Test: `tests/test_bake_schema.py`

**Interfaces:**
- Consumes: `resolver.contract` (`Delivery`, `EffectKind`, `Trigger`, `Target`, `GadgetDraft`), `resolver.items.Build`.
- Produces: `Depth(str, Enum)` with `SHALLOW`/`MEDIUM`/`DEEP`; `ScaffoldSet(BaseModel)` with fields `shallow`/`medium`/`deep: GadgetDraft`; `BakeRecord(BaseModel)`; `combo_id(build: Build) -> str`; `contract_fingerprint() -> str`; `CONTRACT_VERSION = "v1"`. Later tasks import all of these from `resolver.bake.schema`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bake_schema.py`:

```python
from resolver.bake.schema import (
    CONTRACT_VERSION, BakeRecord, Depth, ScaffoldSet,
    combo_id, contract_fingerprint, _fingerprint,
)
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger
from resolver.items import CATALOG, Build


def _draft(name="Fake"):
    return GadgetDraft(
        name=name, description="d", logic="l",
        stages=[Stage(trigger=Trigger.ON_HIT, effects=[
            Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=2.0),
        ])],
    )


def test_combo_id_canonical_format():
    build = Build(delivery_item=CATALOG["baseball bat"],
                  modifier_item=CATALOG["car battery"])
    assert combo_id(build) == "d:baseball bat|dmg:-|u:-|m:car battery"


def test_combo_id_is_role_sensitive():
    a = Build(delivery_item=CATALOG["baseball bat"], damage_item=CATALOG["car battery"])
    b = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
    assert combo_id(a) != combo_id(b)


def test_fingerprint_is_stable_and_hex():
    fp = contract_fingerprint()
    assert fp == contract_fingerprint()
    assert len(fp) == 64 and int(fp, 16) >= 0


def test_fingerprint_changes_when_vocabulary_changes():
    base = {"delivery": ["SWING"], "effect": ["DAMAGE"], "trigger": ["ON_HIT"], "target": ["STRUCK"]}
    widened = {**base, "effect": ["DAMAGE", "TELEPORT"]}
    assert _fingerprint(base) != _fingerprint(widened)


def test_fingerprint_ignores_token_order():
    a = {"delivery": ["SWING", "SLAM"], "effect": [], "trigger": [], "target": []}
    b = {"delivery": ["SLAM", "SWING"], "effect": [], "trigger": [], "target": []}
    assert _fingerprint(a) == _fingerprint(b)


def test_scaffold_set_has_one_draft_per_depth():
    s = ScaffoldSet(shallow=_draft("a"), medium=_draft("b"), deep=_draft("c"))
    assert [s.shallow.name, s.medium.name, s.deep.name] == ["a", "b", "c"]


def test_bake_record_round_trips_through_json():
    record = BakeRecord(
        combo_id="d:baseball bat|dmg:-|u:-|m:car battery",
        status="resolved",
        contract_fingerprint=contract_fingerprint(),
        model="claude-sonnet-5",
        baked_at="2026-07-17T00:00:00+00:00",
        usage={"input_tokens": 100, "output_tokens": 200},
        scaffolds={Depth.SHALLOW: [_draft()], Depth.MEDIUM: [_draft()], Depth.DEEP: [_draft()]},
    )
    line = record.model_dump_json()
    assert BakeRecord.model_validate_json(line) == record
    assert record.contract_version == CONTRACT_VERSION == "v1"


def test_unresolved_record_defaults_to_empty_scaffolds():
    record = BakeRecord(combo_id="x", status="unresolved",
                        contract_fingerprint=contract_fingerprint(), baked_at="t")
    assert record.scaffolds == {} and record.model is None and record.usage == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_schema.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolver.bake'`

- [ ] **Step 3: Implement**

Create empty `resolver/bake/__init__.py`.

In `pyproject.toml` change:

```toml
[tool.setuptools]
packages = ["resolver", "resolver.bake"]
```

Create `resolver/bake/schema.py`:

```python
"""Bake schema: what one bake call returns and what the library stores.

The scaffold body reuses GadgetDraft: fit/fill rescales every draft, so the
numbers a model emits are formally *relative weights* — "no magnitudes" is
enforced by the deriver (derive.py), not the schema. Depth is the bake-side
instruction axis; tiers are derived per depth band at read time.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from resolver.contract import Delivery, EffectKind, GadgetDraft, Target, Trigger
from resolver.items import Build

CONTRACT_VERSION = "v1"


class Depth(str, Enum):
    SHALLOW = "SHALLOW"  # the DUD/COMMON reading
    MEDIUM = "MEDIUM"    # the workmanlike reading — UNCOMMON/RARE
    DEEP = "DEEP"        # chained, reactive — EPIC/LEGENDARY


class ScaffoldSet(BaseModel):
    """Model-facing structured output: named fields, not a list, so "exactly
    one scaffold per depth" holds by construction."""
    shallow: GadgetDraft
    medium: GadgetDraft
    deep: GadgetDraft


class BakeRecord(BaseModel):
    combo_id: str
    status: Literal["resolved", "unresolved"]
    contract_version: str = CONTRACT_VERSION
    contract_fingerprint: str
    model: str | None = None  # the ladder model that produced the base set
    baked_at: str = ""        # ISO timestamp, UTC
    usage: dict[str, int] = Field(default_factory=dict)
    scaffolds: dict[Depth, list[GadgetDraft]] = Field(default_factory=dict)


_EMPTY = "-"


def combo_id(build: Build) -> str:
    """Canonical, role-sensitive id: same items in different slots are
    different combos, matching Build."""
    slots = dict(build.slots())

    def name(key: str) -> str:
        item = slots[key]
        return item.name if item is not None else _EMPTY

    return (f"d:{name('delivery')}|dmg:{name('damage')}"
            f"|u:{name('utility')}|m:{name('modifier')}")


def _fingerprint(families: dict[str, list[str]]) -> str:
    payload = json.dumps({k: sorted(v) for k, v in sorted(families.items())})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def contract_fingerprint() -> str:
    """Stable hash of the enum vocabulary the scaffolds were baked against.
    A mismatch on read means deterministic re-validation through repair —
    never a re-bake."""
    return _fingerprint({
        "delivery": [d.value for d in Delivery],
        "effect": [k.value for k in EffectKind],
        "trigger": [t.value for t in Trigger],
        "target": [t.value for t in Target],
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_schema.py -q` then `python -m pytest -q`
Expected: new file PASS; full suite green (279 + 8 new).

- [ ] **Step 5: Commit**

```bash
git add resolver/bake/__init__.py resolver/bake/schema.py pyproject.toml tests/test_bake_schema.py
git commit -m "feat: bake schema - ScaffoldSet, BakeRecord, combo_id, contract fingerprint

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Instance derivation (`derive.py`) + `clamp.fit_cost`

**Files:**
- Create: `resolver/bake/derive.py`
- Modify: `resolver/clamp.py` (add `fit_cost` right after `fill_budget`)
- Test: `tests/test_bake_derive.py`, `tests/test_clamp.py` (one addition)

**Interfaces:**
- Consumes: `Depth` (Task 1); `resolver.clamp` (`TIER_BUDGET`, `OVER_BUDGET_FACTOR`, `DUD_FLOOR`, `total_cost`, `derive_category`, `derive_harmless`, new `fit_cost`); `resolver.validate.repair`; `resolver.items` (`Build`, `params_for`).
- Produces: `derive_instance(draft: GadgetDraft, build: Build, tier: Tier, seed: int) -> ResolvedGadget`; `DEPTH_TIERS: dict[Depth, tuple[Tier, Tier]]`; constants `JITTER = 0.10`, `BUDGET_LOW = 0.90`. `fit_cost(draft: GadgetDraft, target_total: float) -> GadgetDraft` in `resolver.clamp`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bake_derive.py`:

```python
import pytest

from resolver.bake.derive import BUDGET_LOW, DEPTH_TIERS, JITTER, derive_instance
from resolver.bake.schema import Depth
from resolver.clamp import OVER_BUDGET_FACTOR, TIER_BUDGET, total_cost
from resolver.contract import (
    Category, Effect, EffectKind, GadgetDraft, Stage, Target, Tier, Trigger,
)
from resolver.items import CATALOG, Build

BUILD = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])


def _scaffold():
    # float-only, two stages: proportions are what the scaffold carries
    return GadgetDraft(
        name="Scaffold", description="d", logic="l",
        stages=[
            Stage(trigger=Trigger.ON_HIT, effects=[
                Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=3.0),
                Effect(kind=EffectKind.KNOCKBACK, target=Target.STRUCK, amount=1.0, duration=1.0),
            ]),
            Stage(trigger=Trigger.ON_KILL, effects=[
                Effect(kind=EffectKind.HEAL, target=Target.SELF, amount=1.0),
            ]),
        ],
    )


def test_depth_bands_cover_all_six_tiers_exactly_once():
    assert DEPTH_TIERS == {
        Depth.SHALLOW: (Tier.DUD, Tier.COMMON),
        Depth.MEDIUM: (Tier.UNCOMMON, Tier.RARE),
        Depth.DEEP: (Tier.EPIC, Tier.LEGENDARY),
    }


def test_same_seed_gives_identical_instance():
    a = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=42)
    b = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=42)
    assert a.draft.model_dump() == b.draft.model_dump()
    assert (a.tier, a.category, a.harmless) == (b.tier, b.category, b.harmless)


def test_different_seeds_give_different_magnitudes():
    a = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=1)
    b = derive_instance(_scaffold(), BUILD, Tier.RARE, seed=2)
    assert a.draft.model_dump() != b.draft.model_dump()


@pytest.mark.parametrize("tier", list(Tier))
def test_cost_lands_in_the_seeded_band_at_every_tier(tier):
    for seed in range(10):
        out = derive_instance(_scaffold(), BUILD, tier, seed=seed)
        total = total_cost(out.draft)
        assert total <= TIER_BUDGET[tier] * OVER_BUDGET_FACTOR + 1e-9
        assert total >= TIER_BUDGET[tier] * BUDGET_LOW - 1e-9


def test_count_heavy_scaffold_never_exceeds_the_cap():
    draft = GadgetDraft(name="Counts", description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_HIT, effects=[
            Effect(kind=EffectKind.CHAIN, target=Target.STRUCK, amount=1.0, count=100),
        ]),
    ])
    out = derive_instance(draft, BUILD, Tier.DUD, seed=0)
    assert total_cost(out.draft) <= TIER_BUDGET[Tier.DUD] * OVER_BUDGET_FACTOR + 1e-9


def test_self_chassis_scaffold_is_repaired():
    kit = Build(delivery_item=CATALOG["adrenaline shot"])
    draft = GadgetDraft(name="Kit", description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_IMPACT, effects=[
            Effect(kind=EffectKind.SPEED, target=Target.STRUCK, amount=2.0),
        ]),
    ])
    out = derive_instance(draft, kit, Tier.COMMON, seed=7)
    assert out.draft.stages[0].trigger is Trigger.ON_USE
    assert all(e.target is Target.SELF for s in out.draft.stages for e in s.effects)


def test_zero_cost_scaffold_passes_through():
    draft = GadgetDraft(name="Empty", description="d", logic="l", stages=[])
    out = derive_instance(draft, BUILD, Tier.LEGENDARY, seed=3)
    assert out.draft.stages == [] and out.category is Category.DUD


def test_input_draft_is_never_mutated():
    draft = _scaffold()
    before = draft.model_dump()
    derive_instance(draft, BUILD, Tier.EPIC, seed=9)
    assert draft.model_dump() == before


def test_jitter_stays_inside_its_band():
    # after fit, per-effect *proportions* deviate from the scaffold's by at
    # most the jitter ratio ((1+J)/(1-J)); a plain rescale would keep them exact
    scaffold = _scaffold()
    out = derive_instance(scaffold, BUILD, Tier.RARE, seed=11)
    base = scaffold.stages[0].effects
    got = out.draft.stages[0].effects
    ratio = (got[0].amount / got[1].amount) / (base[0].amount / base[1].amount)
    band = (1 + JITTER) / (1 - JITTER)
    assert 1 / band - 1e-9 <= ratio <= band + 1e-9
```

Append to `tests/test_clamp.py` (it already imports `pytest`, `Effect`, `EffectKind`, `Target`, and `clamp`, and defines `_draft(*effects)`):

```python
def test_fit_cost_lands_on_the_target_and_passes_zero_through():
    d = _draft(Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=10))
    assert clamp.total_cost(clamp.fit_cost(d, 30.0)) == pytest.approx(30.0)
    empty = _draft()
    assert clamp.total_cost(clamp.fit_cost(empty, 30.0)) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_derive.py tests/test_clamp.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolver.bake.derive'` and `ImportError: cannot import name 'fit_cost'`

- [ ] **Step 3: Implement**

In `resolver/clamp.py`, directly after `fill_budget`:

```python
def fit_cost(draft: GadgetDraft, target_total: float) -> GadgetDraft:
    """Public fit for offline tooling (the bake deriver): scale the draft so
    its weighted cost lands on target_total. Zero-cost drafts pass through —
    there are no proportions to scale."""
    if total_cost(draft) == 0:
        return copy.deepcopy(draft)
    return _fit(draft, target_total)
```

Create `resolver/bake/derive.py`:

```python
"""derive_instance: the pure scaffold->instance function.

Same (draft, build, tier, seed) -> byte-identical ResolvedGadget, forever.
The scaffold is the stored truth; instances are always computed, never
stored mutated. Rebalance = edit the clamp tables and re-run this over the
frozen library — re-clamp, never re-bake. Game-side, the acquisition roll
picks (scaffold alternate, tier, seed) and extraction freezes the triple:
acquisition random, combat deterministic, by construction.
"""
from __future__ import annotations

import random

from resolver.bake.schema import Depth
from resolver.clamp import (
    DUD_FLOOR, OVER_BUDGET_FACTOR, TIER_BUDGET,
    derive_category, derive_harmless, fit_cost,
)
from resolver.contract import GadgetDraft, ResolvedGadget, Tier
from resolver.items import Build, params_for
from resolver.validate import repair

# Adjacent tiers share a composition at different budgets.
DEPTH_TIERS: dict[Depth, tuple[Tier, Tier]] = {
    Depth.SHALLOW: (Tier.DUD, Tier.COMMON),
    Depth.MEDIUM: (Tier.UNCOMMON, Tier.RARE),
    Depth.DEEP: (Tier.EPIC, Tier.LEGENDARY),
}

# Placeholder values, renderer-era tuning (same rule as W_DURATION):
JITTER = 0.10      # per-effect float perturbation — the intra-tier variance
BUDGET_LOW = 0.90  # bottom of the seeded budget band; top is OVER_BUDGET_FACTOR


def derive_instance(draft: GadgetDraft, build: Build, tier: Tier, seed: int) -> ResolvedGadget:
    rng = random.Random(seed)
    out = repair(draft, build)  # deep-copies; the input is never mutated
    for stage in out.stages:
        for effect in stage.effects:
            effect.amount *= rng.uniform(1 - JITTER, 1 + JITTER)
            effect.duration *= rng.uniform(1 - JITTER, 1 + JITTER)
            effect.radius *= rng.uniform(1 - JITTER, 1 + JITTER)
    point = TIER_BUDGET[tier] * rng.uniform(BUDGET_LOW, OVER_BUDGET_FACTOR)
    out = fit_cost(out, max(DUD_FLOOR, point))
    return ResolvedGadget(
        draft=out,
        delivery=build.delivery,
        tier=tier,
        category=derive_category(out),
        harmless=derive_harmless(out),
        color=build.color,
        params=params_for(build.delivery),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_derive.py tests/test_clamp.py -q` then `python -m pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add resolver/bake/derive.py resolver/clamp.py tests/test_bake_derive.py tests/test_clamp.py
git commit -m "feat: derive_instance - pure seeded scaffold->instance derivation

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Combo selection (`select.py`)

**Files:**
- Create: `resolver/bake/select.py`
- Test: `tests/test_bake_select.py`

**Interfaces:**
- Consumes: `combo_id` (Task 1); `resolver.harness.PROBE_BUILDS`; `resolver.coherence.coherence`; `resolver.router` (`C_LOW`, `C_HIGH`); `resolver.items` (`CATALOG`, `Build`, `Item`).
- Produces: `PINNED_BUILDS: dict[str, Build]` (7 entries); `chassis_eligible(item: Item) -> bool`; `select_combos(n: int = 300, seed: int = 20260717) -> list[Build]`; `write_selection(builds: list[Build], path: Path, seed: int) -> None`; `load_selection(path: Path) -> dict[str, Build]` (combo_id → Build, insertion-ordered). Tasks 7–8 call all four.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bake_select.py`:

```python
from resolver.bake.schema import combo_id
from resolver.bake.select import (
    PINNED_BUILDS, chassis_eligible, load_selection, select_combos, write_selection,
)
from resolver.harness import PROBE_BUILDS
from resolver.items import CATALOG

N, SEED = 120, 1


def _ids(builds):
    return [combo_id(b) for b in builds]


def test_selection_is_deterministic_for_a_seed():
    assert _ids(select_combos(N, SEED)) == _ids(select_combos(N, SEED))
    assert _ids(select_combos(N, SEED)) != _ids(select_combos(N, SEED + 1))


def test_selection_size_and_uniqueness():
    ids = _ids(select_combos(N, SEED))
    assert len(ids) == N == len(set(ids))


def test_all_pinned_builds_are_selected():
    assert set(PROBE_BUILDS) <= set(PINNED_BUILDS)
    assert "pinned_extinguisher" in PINNED_BUILDS
    selected = set(_ids(select_combos(N, SEED)))
    assert {combo_id(b) for b in PINNED_BUILDS.values()} <= selected


def test_every_catalog_item_is_covered():
    covered = set()
    for build in select_combos(N, SEED):
        covered |= {item.name for _, item in build.slots() if item is not None}
    assert covered == set(CATALOG)


def test_every_delivery_slot_is_chassis_eligible():
    for build in select_combos(N, SEED):
        assert chassis_eligible(build.delivery_item)
        build.delivery  # must not raise


def test_shape_strata_are_roughly_40_40_20():
    builds = select_combos(300, SEED)
    shapes = [sum(1 for _, i in b.slots() if i is not None) for b in builds]
    assert abs(shapes.count(2) - 120) <= 45
    assert abs(shapes.count(3) - 120) <= 45
    assert abs(shapes.count(4) - 60) <= 45


def test_selection_round_trips_through_json(tmp_path):
    builds = select_combos(N, SEED)
    path = tmp_path / "combos.json"
    write_selection(builds, path, SEED)
    loaded = load_selection(path)
    assert list(loaded) == _ids(builds)
    assert all(combo_id(b) == cid for cid, b in loaded.items())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_select.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolver.bake.select'`

- [ ] **Step 3: Implement**

Create `resolver/bake/select.py`:

```python
"""Deterministic stratified combo selection for a bake wave.

Seeded and reproducible: the exact selection is written to JSON and reviewed
before any money moves. Strata are targets, not hard guarantees (some cells,
e.g. high-coherence 4-item, may be unreachable); the achieved distribution
is visible in the selection file and the wave report.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from resolver.bake.schema import combo_id
from resolver.coherence import coherence
from resolver.harness import PROBE_BUILDS
from resolver.items import CATALOG, Build, Item
from resolver.router import C_HIGH, C_LOW

# Always-selected refusal hot-spots: the six live-validated probes plus the
# 9/9-refused live build. The exact powder item of that build was never
# recorded (HANDOFF: "a powder item"); fertilizer (powder + ignition) is the
# most refusal-prone reconstruction. The spec's fan+duck pin is unbuildable —
# the rubber duck left the catalog in the 2026-07-12 rewrite; its successor
# probe_whimsical is already pinned.
PINNED_BUILDS: dict[str, Build] = {
    **PROBE_BUILDS,
    "pinned_extinguisher": Build(
        delivery_item=CATALOG["fire extinguisher"],
        damage_item=CATALOG["sack of fertilizer"],
        utility_item=CATALOG["industrial fan"],
        modifier_item=CATALOG["roman candle"],
    ),
}

SHAPE_QUOTAS: dict[int, float] = {2: 0.4, 3: 0.4, 4: 0.2}
_SLOTS = ("damage", "utility", "modifier")


def chassis_eligible(item: Item) -> bool:
    """Mirrors Build.delivery: an item can chair the delivery slot iff it
    locks a form or has a base use to inherit one from."""
    return item.delivery is not None or item.base_use is not None


def _tercile(c: float) -> int:
    if c <= C_LOW:
        return 0
    if c >= C_HIGH:
        return 2
    return 1


def _shape(build: Build) -> int:
    return sum(1 for _, item in build.slots() if item is not None)


def _random_build(rng: random.Random, shape: int, must_include: Item | None = None) -> Build:
    chassis = sorted((i for i in CATALOG.values() if chassis_eligible(i)), key=lambda i: i.name)
    pool = sorted(CATALOG.values(), key=lambda i: i.name)
    if must_include is not None and chassis_eligible(must_include) and rng.random() < 0.5:
        delivery = must_include
    else:
        delivery = rng.choice(chassis)
    picks = rng.sample([i for i in pool if i.name != delivery.name], shape - 1)
    if (must_include is not None and must_include.name != delivery.name
            and all(p.name != must_include.name for p in picks)):
        picks[0] = must_include
    slots: dict[str, Item | None] = dict.fromkeys(_SLOTS, None)
    for slot, item in zip(rng.sample(_SLOTS, len(picks)), picks):
        slots[slot] = item
    return Build(delivery_item=delivery, damage_item=slots["damage"],
                 utility_item=slots["utility"], modifier_item=slots["modifier"])


def select_combos(n: int = 300, seed: int = 20260717) -> list[Build]:
    rng = random.Random(seed)
    chosen: dict[str, Build] = {}

    def add(build: Build) -> bool:
        cid = combo_id(build)
        if cid in chosen or len(chosen) >= n:
            return False
        chosen[cid] = build
        return True

    for build in PINNED_BUILDS.values():
        add(build)

    def covered() -> set[str]:
        return {item.name for b in chosen.values() for _, item in b.slots() if item is not None}

    # coverage: every catalog item (every association cloud) gets exercised
    shapes, weights = list(SHAPE_QUOTAS), list(SHAPE_QUOTAS.values())
    for item in sorted(CATALOG.values(), key=lambda i: i.name):
        if item.name in covered():
            continue
        for _ in range(200):
            build = _random_build(rng, rng.choices(shapes, weights)[0], must_include=item)
            in_build = {i.name for _, i in build.slots() if i is not None}
            if item.name in in_build and add(build):
                break

    # strata fill over the remainder: (shape, coherence tercile) cells
    remainder = n - len(chosen)
    targets: dict[tuple[int, int], int] = {}
    for shape, frac in SHAPE_QUOTAS.items():
        per_shape = round(frac * remainder)
        for t in range(3):
            targets[(shape, t)] = per_shape // 3 + (1 if t < per_shape % 3 else 0)
    filled = dict.fromkeys(targets, 0)
    attempts = 0
    while len(chosen) < n and attempts < 200 * n:
        attempts += 1
        open_shapes = sorted({s for (s, t) in targets if filled[(s, t)] < targets[(s, t)]})
        if not open_shapes:
            break
        build = _random_build(rng, rng.choice(open_shapes))
        cell = (_shape(build), _tercile(coherence(build)))
        if cell in targets and filled[cell] < targets[cell] and add(build):
            filled[cell] += 1

    # top-off: unreachable cells must not shrink the wave
    while len(chosen) < n and attempts < 400 * n:
        attempts += 1
        add(_random_build(rng, rng.choices(shapes, weights)[0]))
    return list(chosen.values())


def write_selection(builds: list[Build], path: Path, seed: int) -> None:
    payload = {
        "seed": seed,
        "n": len(builds),
        "combos": [
            {"combo_id": combo_id(b),
             "slots": {slot: (item.name if item is not None else None)
                       for slot, item in b.slots()}}
            for b in builds
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_selection(path: Path) -> dict[str, Build]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Build] = {}
    for entry in payload["combos"]:
        slots = entry["slots"]

        def item(key: str) -> Item | None:
            return CATALOG[slots[key]] if slots[key] else None

        out[entry["combo_id"]] = Build(
            delivery_item=CATALOG[slots["delivery"]], damage_item=item("damage"),
            utility_item=item("utility"), modifier_item=item("modifier"),
        )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_select.py -q` then `python -m pytest -q`
Expected: PASS; full suite green. If `test_shape_strata_are_roughly_40_40_20` fails, the algorithm (not the tolerance) is wrong — the coverage pass plus strata fill should land well inside ±45 at n=300.

- [ ] **Step 5: Commit**

```bash
git add resolver/bake/select.py tests/test_bake_select.py
git commit -m "feat: bake combo selection - deterministic stratified pilot wave

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Bake prompt + runner (`run.py`)

**Files:**
- Create: `resolver/prompts/bake_prompt.txt`
- Create: `resolver/bake/run.py`
- Modify: `resolver/prompt.py` (promote `_slot_line` → public `slot_line`)
- Test: `tests/test_bake_run.py`

**Interfaces:**
- Consumes: Task 1 schema; `resolver.prompt.slot_line` (promoted here); `resolver.items.Build`.
- Produces: `BAKE_PROMPT: str`; `MAX_TOKENS = 16000`; `render_bake_message(build) -> str`; `render_top_up_message(build, record) -> str`; `palette(draft) -> frozenset[tuple[EffectKind, Target]]`; `width(record) -> int` (resolved records only); `TOP_UP_WIDTH = 3`; `bake_combo(client, models, build) -> BakeRecord`; `load_records(path) -> dict[str, BakeRecord]`; `append_record(path, record)`; `write_records(path, records)`; `run_wave(client, models, builds: dict[str, Build], path, retry_unresolved=False) -> dict[str, int]` (stats: attempted/resolved/unresolved/skipped/topped_up). In `resolver/prompt.py`: `slot_line(item) -> str`.

- [ ] **Step 1: Promote `slot_line`**

In `resolver/prompt.py` rename `_slot_line` to `slot_line` (update its four call sites inside `render_user_message`; nothing outside the module imports the private name). Run: `python -m pytest tests/test_prompt.py -q` — Expected: PASS.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_bake_run.py`:

```python
from types import SimpleNamespace

from resolver.bake.run import (
    BAKE_PROMPT, TOP_UP_WIDTH, bake_combo, load_records, palette,
    render_bake_message, run_wave, width, write_records,
)
from resolver.bake.schema import BakeRecord, Depth, ScaffoldSet, combo_id, contract_fingerprint
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger
from resolver.items import CATALOG, Build

BUILD = Build(delivery_item=CATALOG["baseball bat"], modifier_item=CATALOG["car battery"])
LADDER = ["claude-sonnet-5", "claude-sonnet-5", "claude-opus-4-8"]


class FakeMessages:
    """One canned outcome per parse() call: a ScaffoldSet (success), None
    (refusal), or an Exception (transport error)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.models_used = []
        self.captured = []

    def parse(self, **kwargs):
        self.captured.append(kwargs)
        self.models_used.append(kwargs["model"])
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        stop = "refusal" if outcome is None else "end_turn"
        return SimpleNamespace(parsed_output=outcome, stop_reason=stop,
                               usage=SimpleNamespace(input_tokens=100, output_tokens=200))


class FakeClient:
    def __init__(self, outcomes):
        self.messages = FakeMessages(outcomes)


def _draft(name, kind=EffectKind.DAMAGE, target=Target.STRUCK):
    return GadgetDraft(name=name, description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_HIT,
              effects=[Effect(kind=kind, target=target, amount=1.0)]),
    ])


def _narrow_set():
    # all three depths read the same (kind, target) palette -> width 1
    return ScaffoldSet(shallow=_draft("a"), medium=_draft("b"), deep=_draft("c"))


def _wide_set():
    # three pairwise-distinct palettes -> width 3
    return ScaffoldSet(
        shallow=_draft("a", EffectKind.DAMAGE),
        medium=_draft("b", EffectKind.SNARE),
        deep=_draft("c", EffectKind.HEAL, Target.SELF),
    )


def test_bake_message_lists_slots_without_a_tier_line():
    msg = render_bake_message(BUILD)
    assert "baseball bat" in msg and "car battery" in msg
    assert "LOCKED DELIVERY FORM: SWING" in msg
    assert "TIER" not in msg.replace("LOCKED DELIVERY", "")


def test_bake_combo_resolved_record():
    client = FakeClient([_narrow_set()])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "resolved" and record.combo_id == combo_id(BUILD)
    assert record.model == "claude-sonnet-5"
    assert record.contract_fingerprint == contract_fingerprint()
    assert [len(record.scaffolds[d]) for d in Depth] == [1, 1, 1]
    assert record.usage == {"input_tokens": 100, "output_tokens": 200}
    call = client.messages.captured[0]
    assert call["system"] == BAKE_PROMPT and call["output_format"] is ScaffoldSet
    assert "temperature" not in call and "top_p" not in call and "top_k" not in call


def test_ladder_escalates_past_refusal_and_transport_error():
    client = FakeClient([None, RuntimeError("boom"), _narrow_set()])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "resolved" and record.model == "claude-opus-4-8"
    assert client.messages.models_used == LADDER


def test_exhausted_ladder_records_unresolved_without_reasons():
    client = FakeClient([None, None, None])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "unresolved" and record.scaffolds == {}
    assert record.model is None
    # rates only: no reason text anywhere in the stored line
    assert "refusal" not in record.model_dump_json()


def test_width_signal_counts_distinct_palettes():
    assert palette(_draft("x")) == frozenset({(EffectKind.DAMAGE, Target.STRUCK)})
    narrow = bake_combo(FakeClient([_narrow_set()]), LADDER, BUILD)
    assert width(narrow) == 1
    wide = bake_combo(FakeClient([_wide_set(), _wide_set()]), LADDER, BUILD)
    assert width(wide) == TOP_UP_WIDTH


def test_wide_combo_gets_exactly_one_top_up_call():
    client = FakeClient([_wide_set(), _wide_set()])
    record = bake_combo(client, LADDER, BUILD)
    assert len(client.messages.captured) == 2
    assert [len(record.scaffolds[d]) for d in Depth] == [2, 2, 2]
    assert record.usage == {"input_tokens": 200, "output_tokens": 400}
    top_up_msg = client.messages.captured[1]["messages"][0]["content"]
    assert "ALREADY HAVE" in top_up_msg and "a" in top_up_msg


def test_narrow_combo_gets_no_top_up_call():
    client = FakeClient([_narrow_set()])
    bake_combo(client, LADDER, BUILD)
    assert len(client.messages.captured) == 1


def test_failed_top_up_keeps_the_base_scaffolds():
    client = FakeClient([_wide_set(), None, None, None])
    record = bake_combo(client, LADDER, BUILD)
    assert record.status == "resolved"
    assert [len(record.scaffolds[d]) for d in Depth] == [1, 1, 1]


def test_run_wave_skips_existing_and_appends_new(tmp_path):
    path = tmp_path / "scaffolds.jsonl"
    first = bake_combo(FakeClient([_narrow_set()]), LADDER, BUILD)
    write_records(path, {first.combo_id: first})
    other = Build(delivery_item=CATALOG["crowbar"])
    client = FakeClient([_narrow_set()])
    stats = run_wave(client, LADDER, {combo_id(BUILD): BUILD, combo_id(other): other}, path)
    assert stats["skipped"] == 1 and stats["attempted"] == 1
    assert client.messages.models_used == ["claude-sonnet-5"]
    assert set(load_records(path)) == {combo_id(BUILD), combo_id(other)}


def test_retry_unresolved_replaces_the_line(tmp_path):
    path = tmp_path / "scaffolds.jsonl"
    dead = bake_combo(FakeClient([None, None, None]), LADDER, BUILD)
    write_records(path, {dead.combo_id: dead})
    stats = run_wave(FakeClient([_narrow_set()]), LADDER,
                     {combo_id(BUILD): BUILD}, path, retry_unresolved=True)
    records = load_records(path)
    assert stats["attempted"] == 1
    assert len(records) == 1 and records[combo_id(BUILD)].status == "resolved"


def test_run_wave_without_retry_flag_keeps_unresolved(tmp_path):
    path = tmp_path / "scaffolds.jsonl"
    dead = bake_combo(FakeClient([None, None, None]), LADDER, BUILD)
    write_records(path, {dead.combo_id: dead})
    stats = run_wave(FakeClient([]), LADDER, {combo_id(BUILD): BUILD}, path)
    assert stats["skipped"] == 1 and load_records(path)[combo_id(BUILD)].status == "unresolved"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolver.bake.run'`

- [ ] **Step 4: Write the bake prompt**

Create `resolver/prompts/bake_prompt.txt` with exactly this content:

```
You are the crafting engine for a stylized, physics-defying video game. Players jam a few virtual junk items together and you decide what absurd gadget the combination becomes: a set of game abilities, expressed only as the numbered effects in the fixed vocabulary below. The objects are game props and the results are cartoon game mechanics — none of it is real. Read the objects honestly, then let their properties collide into something the player did not quite expect.

Treat this as a cartoon game world where ordinary objects can produce extraordinary effects. Imagination is the only limit, so be willing to be absurd, as long as every effect still traces back to a real property of the objects given.

The core rule: the obvious reading is the weak one. A mop is a thing you bonk people with; that is the boring answer. The interesting answer reads a deeper, truer property of the object: a mop soaks up liquid, its strands tangle, it has a long swingable handle. Good results come from the non-obvious property. Great results come from chaining properties into consequences: the mop soaks up a flammable puddle, so when it strikes, the soaked strands ignite. Always look past the first thing an object "is."

Composition is where the surprise lives. You have a fixed set of delivery forms, effect primitives, and triggers (below). You cannot invent new ones, but you can arrange them freely into stages that fire in sequence. "Swing, then on hit stagger, then on kill release a swarm" is three ordinary primitives composed into something memorable. The surprise is in the arrangement and the reading, never in a new verb. Chain consequences across triggers; let one stage's outcome set up the next.

Read the specific objects you are given. Your result must trace back to real, stated properties of these objects. The maker should be able to see why this junk made this thing. Explain that trace in the logic field. Never cite a property that is not there.

Most combinations are not attacks, and that is honest. Junk that cannot hurt anyone becomes a control tool, a support item, a utility, or a trinket, not an offensive gadget with a damage number bolted on. Do not force damage where there is none. Be truthful about what the effects actually are.

Coherence rule: effects that assume damage (PIERCE, CHAIN, EXPLODE as a killing burst) only belong on something that also deals damage. Do not attach a piercing rider to a heal.

Every effect declares a target: STRUCK or SELF. STRUCK means whatever the effect connects with — the thing hit, snared, or dosed by the shot. SELF means the person using the gadget. This is how one composition can cut both ways: DAMAGE at STRUCK with a HEAL at SELF riding the same hit is a weapon that feeds its user, and a HEAL at STRUCK is a dose fired into whatever the shot touches. Where an ingredient sits steers the reading: a healing item in the damage slot wants to become the payload (HEAL at STRUCK); the same item riding as a modifier wants to pay the user (HEAL at SELF).

The vocabulary. Pick effects by behavior, not vibe.
- Delivery (the form; this is LOCKED and given to you, do not change it): the delivery-slot object fixes the form. You compose within that form.
- Effects: damage family (DAMAGE, BURN, EXPLODE, PIERCE, CHAIN); control family (KNOCKBACK, LAUNCH, STAGGER, SNARE, SLOW, FREEZE); self family (HEAL, SHIELD, SPEED); other (SUMMON, LURE).
- Triggers: ON_USE, ON_HIT, ON_IMPACT, ON_TRIGGER, ON_EXPIRE, ON_KILL, ON_BLOCK.
- Targets: STRUCK (whatever the effect connects with) or SELF (the person using it). Every effect declares one.
- Triggers on a SELF delivery form (a kit worn or used on yourself): ON_USE fires when it is activated, ON_EXPIRE when it wears off, ON_HIT means when the user gets hit (it only belongs on protective gear), and ON_KILL means when the user downs someone while the kit is active. Effects on a self-kit land on the user; a reactive hit may also bite back at whoever struck them.

Your job here: give THREE readings of the same junk, at three depths. Not the same gadget at three sizes — three different interpretations, the same objects seen by a sleeping mind, a waking one, and a lucid one.
- shallow: the junk barely cooperates, or does the one obvious thing. One weak effect or one clean beat, the obvious-or-failed reading. Slightly pathetic to merely functional.
- medium: the workmanlike reading. Two effects or a two-stage sequence; one mildly clever reading; a genuine interaction between the objects' properties.
- deep: the inspired reading. Multi-stage, reactive, interconnected; a chain of consequences the maker would not have guessed, while still tracing honestly back to what the junk actually is. It should feel discovered, not assembled.

The three readings should differ in interpretation, not just in count of stages. If the deep reading is the shallow reading with more numbers, you have not gone deeper — you have gone louder.

Magnitudes: the numbers you write only express proportions — the game rescales every number to whatever power the gadget lands at. What you control is the ratio between effects within a reading (this hits harder than it slows, the burn is long but weak). Keep them in sane, modest ranges and spend your attention on the reading.

Naming. Each reading gets its own name a person would grin at. No mechanic-words in the name (not "Snare Launcher"; call it something with character). Names should differ across the three readings. The name sells the fantasy; the logic field explains the trick.

Output. Fill the structured schema: three gadgets — shallow, medium, deep — each with name, stages (each stage a trigger and effects, each effect with a target and amount / duration / radius / count and a short note), description (flavor), and logic (the trace: how this reading sees each object). The delivery form, rarity, category, and whether it is harmless are decided by code, not by you; focus on the readings and the composition.
```

- [ ] **Step 5: Implement the runner**

Create `resolver/bake/run.py`:

```python
"""Bake runner: one structured-output call per combo -> ScaffoldSet, retry
ladder on refusal/transport failure, resumable append-only JSONL, adaptive
top-up for combos whose scaffolds show real interpretive width.

Rates are logged; the *reason* a call failed is never asked, classified, or
recorded (standing rule: log rates, ablate by item swap, never chase the
reason). This is offline tooling — never the runtime hot path.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from resolver.bake.schema import (
    BakeRecord, Depth, ScaffoldSet, combo_id, contract_fingerprint,
)
from resolver.contract import EffectKind, GadgetDraft, Target
from resolver.items import Build
from resolver.prompt import slot_line

# ScaffoldSet is three drafts plus adaptive thinking; starve it and the JSON
# truncates mid-token (same failure mode MAX_TOKENS=8000 fixed for one draft).
MAX_TOKENS = 16000

BAKE_PROMPT: str = (
    Path(__file__).parent.parent / "prompts" / "bake_prompt.txt"
).read_text(encoding="utf-8").strip()

_TEMPLATE = """BUILD
  delivery: {delivery}
  damage:   {damage}
  utility:  {utility}
  modifier: {modifier}

LOCKED DELIVERY FORM: {form}

Give the three readings of this build: shallow, medium, deep. Trace every
effect back to a stated property of the specific objects above. Compose
within the locked delivery form."""

_TOP_UP_SUFFIX = """

ALREADY HAVE (from an earlier pass over this same build):
{existing}

Read the build differently: another three readings — shallow, medium, deep —
built on different properties or a different arrangement than the ones above.
Do not repeat those compositions or names."""


def render_bake_message(build: Build) -> str:
    slots = dict(build.slots())
    return _TEMPLATE.format(
        delivery=slot_line(slots["delivery"]),
        damage=slot_line(slots["damage"]),
        utility=slot_line(slots["utility"]),
        modifier=slot_line(slots["modifier"]),
        form=build.delivery.value,
    )


def _shape_line(depth: Depth, draft: GadgetDraft) -> str:
    kinds = ", ".join(f"{e.kind.value}@{e.target.value}"
                      for stage in draft.stages for e in stage.effects)
    return f"- {depth.value.lower()} \"{draft.name}\": {kinds}"


def render_top_up_message(build: Build, record: BakeRecord) -> str:
    existing = "\n".join(_shape_line(d, record.scaffolds[d][0]) for d in Depth)
    return render_bake_message(build) + _TOP_UP_SUFFIX.format(existing=existing)


def palette(draft: GadgetDraft) -> frozenset[tuple[EffectKind, Target]]:
    return frozenset((e.kind, e.target) for stage in draft.stages for e in stage.effects)


TOP_UP_WIDTH = 3  # top up only maximal-width combos (placeholder threshold;
                  # the report shows the width distribution to tune it on evidence)


def width(record: BakeRecord) -> int:
    """Distinct (kind, target) palettes among the base scaffolds (resolved
    records only). Palettes, not stage structure: depth mandates structural
    growth, so structure always differs; palettes differ only when the depths
    read the items differently."""
    return len({palette(record.scaffolds[d][0]) for d in Depth})


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _call_ladder(client, models: list[str], user: str):
    """Try each model in order; first parseable ScaffoldSet wins. Returns
    (scaffold_set | None, model | None, usage). Failure reasons are never
    recorded — rates only."""
    usage = {"input_tokens": 0, "output_tokens": 0}
    for model in models:
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=MAX_TOKENS,
                system=BAKE_PROMPT,
                messages=[{"role": "user", "content": user}],
                output_format=ScaffoldSet,
            )
        except Exception:  # noqa: BLE001 - next rung; the reason is deliberately dropped
            continue
        used = getattr(response, "usage", None)
        if used is not None:
            usage["input_tokens"] += used.input_tokens
            usage["output_tokens"] += used.output_tokens
        if response.parsed_output is not None:
            return response.parsed_output, model, usage
    return None, None, usage


def bake_combo(client, models: list[str], build: Build) -> BakeRecord:
    scaffold_set, model, usage = _call_ladder(client, models, render_bake_message(build))
    if scaffold_set is None:
        return BakeRecord(combo_id=combo_id(build), status="unresolved",
                          contract_fingerprint=contract_fingerprint(),
                          baked_at=_now(), usage=usage)
    record = BakeRecord(
        combo_id=combo_id(build), status="resolved",
        contract_fingerprint=contract_fingerprint(),
        model=model, baked_at=_now(), usage=usage,
        scaffolds={Depth.SHALLOW: [scaffold_set.shallow],
                   Depth.MEDIUM: [scaffold_set.medium],
                   Depth.DEEP: [scaffold_set.deep]},
    )
    if width(record) >= TOP_UP_WIDTH:  # one extra call max at pilot scale
        extra, _, more = _call_ladder(client, models, render_top_up_message(build, record))
        for key, value in more.items():
            record.usage[key] = record.usage.get(key, 0) + value
        if extra is not None:
            record.scaffolds[Depth.SHALLOW].append(extra.shallow)
            record.scaffolds[Depth.MEDIUM].append(extra.medium)
            record.scaffolds[Depth.DEEP].append(extra.deep)
    return record


def load_records(path: Path) -> dict[str, BakeRecord]:
    if not path.exists():
        return {}
    out: dict[str, BakeRecord] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = BakeRecord.model_validate_json(line)
            out[record.combo_id] = record
    return out


def append_record(path: Path, record: BakeRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")


def write_records(path: Path, records: dict[str, BakeRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r.model_dump_json() + "\n" for r in records.values()),
                    encoding="utf-8")


def run_wave(client, models: list[str], builds: dict[str, Build], path: Path,
             retry_unresolved: bool = False) -> dict[str, int]:
    """Resumable: existing combo_ids are skipped (a crash or a later wave is
    just a re-run); with retry_unresolved, unresolved lines are re-attempted
    and replaced, never duplicated. Appends after every combo — crash-safe."""
    existing = load_records(path)
    stats = {"attempted": 0, "resolved": 0, "unresolved": 0, "skipped": 0, "topped_up": 0}
    for cid, build in builds.items():
        prior = existing.get(cid)
        if prior is not None and not (retry_unresolved and prior.status == "unresolved"):
            stats["skipped"] += 1
            continue
        record = bake_combo(client, models, build)
        stats["attempted"] += 1
        stats[record.status] += 1
        if record.status == "resolved" and len(record.scaffolds[Depth.SHALLOW]) > 1:
            stats["topped_up"] += 1
        existing[cid] = record
        if prior is None:
            append_record(path, record)
        else:
            write_records(path, existing)
    return stats
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_run.py tests/test_prompt.py -q` then `python -m pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 7: Commit**

```bash
git add resolver/prompts/bake_prompt.txt resolver/bake/run.py resolver/prompt.py tests/test_bake_run.py
git commit -m "feat: bake runner - depth prompt, ladder calls, resumable JSONL, adaptive top-up

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Name dedup + rename pass (`dedup.py`)

**Files:**
- Create: `resolver/bake/dedup.py`
- Test: `tests/test_bake_dedup.py`

**Interfaces:**
- Consumes: `BakeRecord`, `Depth` (Task 1).
- Produces: `Rename(BaseModel)` with `name: str`; `normalize(name: str) -> str`; `iter_scaffolds(records: list[BakeRecord])` yielding `((combo_id, depth_value, index), draft)` in first-baked order; `load_registry(path) -> dict`; `save_registry(path, registry)`; `dedup_wave(records: list[BakeRecord], registry: dict, client, models) -> list[dict]` (rename events; mutates names + registry in place); constants `RENAME_ATTEMPTS = 2`, `RENAME_MAX_TOKENS = 1000`. Registry shape: `{normalized: {"owner": [combo_id, depth, index], "display": str}}`. Event shape: `{"owner": [...], "old": str, "new": str, "outcome": "renamed" | "suffixed"}`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bake_dedup.py`:

```python
from types import SimpleNamespace

from resolver.bake.dedup import (
    Rename, dedup_wave, iter_scaffolds, load_registry, normalize, save_registry,
)
from resolver.bake.schema import BakeRecord, Depth, contract_fingerprint
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Trigger

LADDER = ["claude-sonnet-5"]


class FakeMessages:
    def __init__(self, names):
        self.names = list(names)
        self.captured = []

    def parse(self, **kwargs):
        self.captured.append(kwargs)
        name = self.names.pop(0)
        parsed = None if name is None else Rename(name=name)
        return SimpleNamespace(parsed_output=parsed, stop_reason="end_turn")


class FakeClient:
    def __init__(self, names):
        self.messages = FakeMessages(names)


def _draft(name):
    return GadgetDraft(name=name, description="flavor", logic="trace", stages=[
        Stage(trigger=Trigger.ON_HIT,
              effects=[Effect(kind=EffectKind.DAMAGE, target=Target.STRUCK, amount=1.0)]),
    ])


def _record(cid, names3):
    return BakeRecord(
        combo_id=cid, status="resolved", contract_fingerprint=contract_fingerprint(),
        baked_at="t", scaffolds={d: [_draft(n)] for d, n in zip(Depth, names3)},
    )


def test_normalize_folds_case_punctuation_and_whitespace():
    # punctuation strips without leaving a space; whitespace collapses; casefold applies
    assert normalize("Load-Bearing  Argument!") == "loadbearing argument"
    assert normalize("The  Bouncer") == "the bouncer"
    assert normalize("Mk. II") == normalize("mk ii")


def test_iter_scaffolds_yields_first_baked_order():
    records = [_record("c1", ["a", "b", "c"]), _record("c2", ["d", "e", "f"])]
    owners = [owner for owner, _ in iter_scaffolds(records)]
    assert owners == [
        ("c1", "SHALLOW", 0), ("c1", "MEDIUM", 0), ("c1", "DEEP", 0),
        ("c2", "SHALLOW", 0), ("c2", "MEDIUM", 0), ("c2", "DEEP", 0),
    ]


def test_first_baked_keeps_the_name_and_loser_is_renamed():
    records = [_record("c1", ["Same Name", "b", "c"]), _record("c2", ["Same Name", "e", "f"])]
    registry = {}
    events = dedup_wave(records, registry, FakeClient(["Fresh Name"]), LADDER)
    assert records[0].scaffolds[Depth.SHALLOW][0].name == "Same Name"
    assert records[1].scaffolds[Depth.SHALLOW][0].name == "Fresh Name"
    assert events == [{"owner": ["c2", "SHALLOW", 0], "old": "Same Name",
                       "new": "Fresh Name", "outcome": "renamed"}]
    assert registry[normalize("Same Name")]["owner"] == ["c1", "SHALLOW", 0]
    assert registry[normalize("Fresh Name")]["owner"] == ["c2", "SHALLOW", 0]


def test_registry_from_an_earlier_wave_wins():
    registry = {normalize("Old Glory"): {"owner": ["old", "DEEP", 0], "display": "Old Glory"}}
    records = [_record("c1", ["Old Glory", "b", "c"])]
    dedup_wave(records, registry, FakeClient(["New Name"]), LADDER)
    assert records[0].scaffolds[Depth.SHALLOW][0].name == "New Name"
    assert registry[normalize("Old Glory")]["owner"] == ["old", "DEEP", 0]


def test_rename_touches_only_the_name():
    records = [_record("c1", ["Dup", "b", "c"]), _record("c2", ["Dup", "e", "f"])]
    before = records[1].scaffolds[Depth.SHALLOW][0].model_dump()
    dedup_wave(records, {}, FakeClient(["Renamed"]), LADDER)
    after = records[1].scaffolds[Depth.SHALLOW][0].model_dump()
    assert after["name"] == "Renamed"
    assert {k: v for k, v in after.items() if k != "name"} == \
        {k: v for k, v in before.items() if k != "name"}


def test_suffix_fallback_after_two_colliding_rename_attempts():
    records = [_record("c1", ["Dup", "b", "c"]), _record("c2", ["Dup", "e", "f"])]
    # both rename attempts return names that are already taken
    events = dedup_wave(records, {}, FakeClient(["Dup", "b"]), LADDER)
    assert events[0]["outcome"] == "suffixed"
    new = records[1].scaffolds[Depth.SHALLOW][0].name
    assert new.startswith("Dup") and new != "Dup"


def test_refused_rename_call_counts_as_a_failed_attempt():
    records = [_record("c1", ["Dup", "b", "c"]), _record("c2", ["Dup", "e", "f"])]
    events = dedup_wave(records, {}, FakeClient([None, None]), LADDER)
    assert events[0]["outcome"] == "suffixed"


def test_registry_round_trips(tmp_path):
    path = tmp_path / "names.json"
    registry = {"x": {"owner": ["c", "DEEP", 0], "display": "X"}}
    save_registry(path, registry)
    assert load_registry(path) == registry
    assert load_registry(tmp_path / "missing.json") == {}
```

Note on the first `normalize` assertion: replace it with the direct form —

```python
    assert normalize("Load-Bearing  Argument!") == normalize("LOADBEARING argument")
```

(hyphen and punctuation strip to nothing, whitespace collapses, casefold applies).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_dedup.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolver.bake.dedup'`

- [ ] **Step 3: Implement**

Create `resolver/bake/dedup.py`:

```python
"""Global name dedup: bake calls are stateless (no exclusion lists in
prompts — they break prompt caching, cannot scale, and parallel calls would
still collide); uniqueness is enforced by this post-wave pass against a
persistent registry. First-baked keeps the name. Only the name field is
ever touched — composition is immutable once baked. The pass rewrites
scaffolds.jsonl and names.json; the git diff is the rename audit.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

from resolver.bake.schema import BakeRecord, Depth
from resolver.contract import GadgetDraft

RENAME_ATTEMPTS = 2
RENAME_MAX_TOKENS = 1000

RENAME_PROMPT = (
    "You are renaming one gadget in a stylized video game so its name is "
    "unique. You will see the gadget's current name, description, and logic, "
    "plus names that are already taken. Give it a new name with the same "
    "character: something a person would grin at, no mechanic-words, clearly "
    "different from every taken name. Change only the name."
)


class Rename(BaseModel):
    name: str


Owner = tuple[str, str, int]  # (combo_id, depth value, alternate index)


def normalize(name: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", name.casefold())
    return re.sub(r"\s+", " ", cleaned).strip()


def iter_scaffolds(records: list[BakeRecord]) -> Iterator[tuple[Owner, GadgetDraft]]:
    """Canonical first-baked order: record (JSONL line) order, then depth
    order SHALLOW -> MEDIUM -> DEEP, then alternate index."""
    for record in records:
        for depth in Depth:
            for index, draft in enumerate(record.scaffolds.get(depth, [])):
                yield (record.combo_id, depth.value, index), draft


def load_registry(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(path: Path, registry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")


def _rename_message(draft: GadgetDraft, taken: list[str]) -> str:
    lines = "\n".join(f"- {name}" for name in taken)
    return (f"Current name: {draft.name}\n"
            f"Description: {draft.description}\n"
            f"Logic: {draft.logic}\n\n"
            f"Taken names:\n{lines}\n\n"
            "Give the new unique name.")


def _try_rename(client, models: list[str], draft: GadgetDraft, taken: list[str]) -> str | None:
    """One rename attempt down the ladder; None if nothing parseable came back.
    Reasons are never recorded."""
    for model in models:
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=RENAME_MAX_TOKENS,
                system=RENAME_PROMPT,
                messages=[{"role": "user", "content": _rename_message(draft, taken)}],
                output_format=Rename,
            )
        except Exception:  # noqa: BLE001 - next rung
            continue
        if response.parsed_output is not None:
            return response.parsed_output.name
    return None


def _suffixed(name: str, registry: dict) -> str:
    mark = 2
    while normalize(f"{name} Mk {mark}") in registry:
        mark += 1
    return f"{name} Mk {mark}"


def dedup_wave(records: list[BakeRecord], registry: dict, client, models: list[str]) -> list[dict]:
    """Detect collisions (wave-internal and against the registry), rename the
    losers, register every final name. Mutates draft names and the registry
    in place; returns the rename events for the report."""
    events: list[dict] = []
    for owner, draft in iter_scaffolds(records):
        key = normalize(draft.name)
        claimed = registry.get(key)
        if claimed is None:
            registry[key] = {"owner": list(owner), "display": draft.name}
            continue
        if tuple(claimed["owner"]) == owner:
            continue  # this scaffold already owns the name (re-run of the pass)
        old = draft.name
        taken = [claimed["display"]]
        outcome = "suffixed"
        for _ in range(RENAME_ATTEMPTS):
            candidate = _try_rename(client, models, draft, taken)
            if candidate is None:
                continue
            if normalize(candidate) not in registry:
                draft.name = candidate
                outcome = "renamed"
                break
            taken.append(candidate)
        if outcome == "suffixed":
            draft.name = _suffixed(old, registry)
        registry[normalize(draft.name)] = {"owner": list(owner), "display": draft.name}
        events.append({"owner": list(owner), "old": old,
                       "new": draft.name, "outcome": outcome})
    return events
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_dedup.py -q` then `python -m pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add resolver/bake/dedup.py tests/test_bake_dedup.py
git commit -m "feat: bake name dedup - global registry, rename pass, suffix fallback

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Wave report (`report.py`)

**Files:**
- Create: `resolver/bake/report.py`
- Test: `tests/test_bake_report.py`

**Interfaces:**
- Consumes: Tasks 1–5 (`BakeRecord`, `Depth`, `DEPTH_TIERS`, `derive_instance`, `width`, `iter_scaffolds`, `PINNED_BUILDS`, `combo_id`); `resolver.clamp` (`TIER_BUDGET`, `total_cost`); `resolver.items.Build`.
- Produces: `REPORT_SEED = 20260717`; `PRICE_PER_MTOK: dict[str, tuple[float, float]]`; `instance_seed(cid: str, depth: str, index: int, tier: Tier) -> int`; `wave_report(records: list[BakeRecord], builds: dict[str, Build], rename_events: list[dict], wave: str) -> str` (markdown). Task 7's CLI writes it to `data/bake/reports/`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bake_report.py`:

```python
from resolver.bake.report import instance_seed, wave_report
from resolver.bake.schema import BakeRecord, Depth, contract_fingerprint
from resolver.contract import Effect, EffectKind, GadgetDraft, Stage, Target, Tier, Trigger
from resolver.items import CATALOG, Build


def _draft(name, kind=EffectKind.DAMAGE):
    return GadgetDraft(name=name, description="d", logic="l", stages=[
        Stage(trigger=Trigger.ON_HIT,
              effects=[Effect(kind=kind, target=Target.STRUCK, amount=2.0)]),
    ])


def _resolved(cid, kinds):
    return BakeRecord(
        combo_id=cid, status="resolved", contract_fingerprint=contract_fingerprint(),
        model="claude-sonnet-5", baked_at="t",
        usage={"input_tokens": 1000, "output_tokens": 2000},
        scaffolds={d: [_draft(f"{cid}-{d.value}", k)] for d, k in zip(Depth, kinds)},
    )


BUILD = Build(delivery_item=CATALOG["baseball bat"])
RECORDS = [
    _resolved("c1", [EffectKind.DAMAGE, EffectKind.DAMAGE, EffectKind.DAMAGE]),  # width 1
    _resolved("c2", [EffectKind.DAMAGE, EffectKind.SNARE, EffectKind.HEAL]),     # width 3
    BakeRecord(combo_id="c3", status="unresolved",
               contract_fingerprint=contract_fingerprint(), baked_at="t",
               usage={"input_tokens": 500, "output_tokens": 0}),
]
BUILDS = {"c1": BUILD, "c2": BUILD, "c3": BUILD}
EVENTS = [{"owner": ["c2", "SHALLOW", 0], "old": "x", "new": "y", "outcome": "suffixed"}]


def test_instance_seed_is_deterministic_and_distinct():
    a = instance_seed("c1", "SHALLOW", 0, Tier.DUD)
    assert a == instance_seed("c1", "SHALLOW", 0, Tier.DUD)
    assert a != instance_seed("c1", "SHALLOW", 0, Tier.COMMON)
    assert a != instance_seed("c2", "SHALLOW", 0, Tier.DUD)


def test_report_is_deterministic():
    assert wave_report(RECORDS, BUILDS, EVENTS, "wave1") == \
        wave_report(RECORDS, BUILDS, EVENTS, "wave1")


def test_report_carries_the_headline_stats():
    md = wave_report(RECORDS, BUILDS, EVENTS, "wave1")
    assert "wave1" in md
    assert "unresolved: 1/3" in md
    assert "width 1: 1" in md and "width 3: 1" in md
    assert "renames: 1" in md and "suffixed: 1" in md
    assert "input tokens: 2500" in md and "output tokens: 2000" in md
    assert "$" in md  # a dollar figure is present


def test_report_covers_all_six_tiers():
    md = wave_report(RECORDS, BUILDS, EVENTS, "wave1")
    for tier in Tier:
        assert tier.value in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_report.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'resolver.bake.report'`

- [ ] **Step 3: Implement**

Create `resolver/bake/report.py`:

```python
"""Per-wave statistical report: a library this size is never hand-QA'd.
Everything here is read-only over the frozen records; the derive sweep uses
a fixed report seed so two runs of the report agree byte-for-byte.
"""
from __future__ import annotations

import hashlib
from collections import Counter

from resolver.bake.dedup import iter_scaffolds
from resolver.bake.derive import DEPTH_TIERS, derive_instance
from resolver.bake.run import width
from resolver.bake.schema import BakeRecord, Depth
from resolver.bake.select import PINNED_BUILDS
from resolver.bake.schema import combo_id as _combo_id
from resolver.clamp import TIER_BUDGET, total_cost
from resolver.contract import Tier
from resolver.items import Build

REPORT_SEED = 20260717

# $ per million tokens (input, output). 2026-07 list prices — verify against
# the current pricing page before reading a pilot's dollar figure as truth.
PRICE_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
}


def instance_seed(cid: str, depth: str, index: int, tier: Tier) -> int:
    digest = hashlib.sha256(
        f"{cid}|{depth}|{index}|{tier.value}|{REPORT_SEED}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big")


def _dollars(records: list[BakeRecord]) -> float:
    total = 0.0
    for record in records:
        price_in, price_out = PRICE_PER_MTOK.get(record.model or "", (0.0, 0.0))
        total += record.usage.get("input_tokens", 0) / 1e6 * price_in
        total += record.usage.get("output_tokens", 0) / 1e6 * price_out
    return total


def wave_report(records: list[BakeRecord], builds: dict[str, Build],
                rename_events: list[dict], wave: str) -> str:
    resolved = [r for r in records if r.status == "resolved"]
    unresolved = [r for r in records if r.status == "unresolved"]
    pinned_ids = {_combo_id(b): key for key, b in PINNED_BUILDS.items()}
    lines: list[str] = [f"# Bake report — {wave}", ""]

    lines += [f"- combos: {len(records)}",
              f"- unresolved: {len(unresolved)}/{len(records)}"]
    for record in unresolved:
        tag = pinned_ids.get(record.combo_id, "")
        lines.append(f"  - `{record.combo_id}`" + (f" (pinned: {tag})" if tag else ""))
    pinned_unresolved = [r for r in unresolved if r.combo_id in pinned_ids]
    lines.append(f"- pinned unresolved: {len(pinned_unresolved)}/{len(pinned_ids)}")

    widths = Counter(width(r) for r in resolved)
    topped = sum(1 for r in resolved if len(r.scaffolds[Depth.SHALLOW]) > 1)
    lines += ["", "## Width / top-up",
              *(f"- width {w}: {widths.get(w, 0)}" for w in (1, 2, 3)),
              f"- topped up: {topped}"]

    suffixed = sum(1 for e in rename_events if e["outcome"] == "suffixed")
    lines += ["", "## Names",
              f"- renames: {len(rename_events)}",
              f"- suffixed: {suffixed}"]
    for event in rename_events:
        if event["outcome"] == "suffixed":
            lines.append(f"  - FLAG suffixed: {event['old']!r} -> {event['new']!r} ({event['owner']})")

    lines += ["", "## Derive sweep (fixed report seed)"]
    ratios: list[tuple[float, str]] = []
    per_tier: dict[Tier, list[float]] = {t: [] for t in Tier}
    categories: Counter = Counter()
    harmless_count = 0
    total_instances = 0
    for record in resolved:
        build = builds[record.combo_id]
        for (cid, depth_value, index), draft in iter_scaffolds([record]):
            for tier in DEPTH_TIERS[Depth(depth_value)]:
                seed = instance_seed(cid, depth_value, index, tier)
                instance = derive_instance(draft, build, tier, seed)
                ratio = (total_cost(instance.draft) / TIER_BUDGET[tier]
                         if TIER_BUDGET[tier] else 0.0)
                ratios.append((ratio, f"{instance.draft.name} [{tier.value}]"))
                per_tier[tier].append(ratio)
                categories[instance.category.value] += 1
                harmless_count += instance.harmless
                total_instances += 1
    for tier in Tier:
        values = per_tier[tier]
        if values:
            lines.append(f"- {tier.value}: n={len(values)} "
                         f"cost/budget mean={sum(values) / len(values):.3f} "
                         f"min={min(values):.3f} max={max(values):.3f}")
        else:
            lines.append(f"- {tier.value}: n=0")
    lines += ["", "### Categories",
              *(f"- {cat}: {count}" for cat, count in sorted(categories.items()))]
    if total_instances:
        lines.append(f"- harmless: {harmless_count}/{total_instances}")

    outliers = max(1, len(ratios) // 100)
    ranked = sorted(ratios)
    lines += ["", "### Outliers by cost share",
              *(f"- low: {name} ({ratio:.3f})" for ratio, name in ranked[:outliers]),
              *(f"- high: {name} ({ratio:.3f})" for ratio, name in ranked[-outliers:])]

    tokens_in = sum(r.usage.get("input_tokens", 0) for r in records)
    tokens_out = sum(r.usage.get("output_tokens", 0) for r in records)
    dollars = _dollars(records)
    per_combo = dollars / len(records) if records else 0.0
    lines += ["", "## Cost",
              f"- input tokens: {tokens_in}",
              f"- output tokens: {tokens_out}",
              f"- total: ${dollars:.2f} (prices from PRICE_PER_MTOK — verify before trusting)",
              f"- $/combo: ${per_combo:.4f}"]
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_report.py -q` then `python -m pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add resolver/bake/report.py tests/test_bake_report.py
git commit -m "feat: bake wave report - rates, width, rename flags, derive sweep, cost

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: CLI (`__main__.py`)

**Files:**
- Create: `resolver/bake/__main__.py`
- Test: `tests/test_bake_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 3–6; `resolver.harness.build_model_list`, `DEFAULT_MODEL`, `DEFAULT_ESCALATE_MODEL`.
- Produces: `main(argv: list[str] | None = None) -> int` with subcommands `select | run | dedup | report`. Task 8 drives the pilot through it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bake_cli.py`:

```python
import json

import pytest

from resolver.bake.__main__ import main
from resolver.bake.run import write_records
from resolver.bake.schema import BakeRecord, contract_fingerprint


def test_select_writes_a_reviewable_selection(tmp_path, capsys):
    out = tmp_path / "combos.json"
    assert main(["select", "--n", "80", "--seed", "1", "--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["n"] == 80 and len(payload["combos"]) == 80
    assert "80" in capsys.readouterr().out


def test_run_without_key_exits_loud_without_spending(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    combos = tmp_path / "combos.json"
    main(["select", "--n", "10", "--seed", "1", "--out", str(combos)])
    code = main(["run", "--combos", str(combos), "--out", str(tmp_path / "s.jsonl")])
    assert code == 1
    assert not (tmp_path / "s.jsonl").exists()


def test_dedup_without_key_exits_loud(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scaffolds = tmp_path / "s.jsonl"
    write_records(scaffolds, {})
    assert main(["dedup", "--scaffolds", str(scaffolds),
                 "--names", str(tmp_path / "names.json")]) == 1


def test_report_runs_offline(tmp_path):
    combos = tmp_path / "combos.json"
    main(["select", "--n", "10", "--seed", "1", "--out", str(combos)])
    scaffolds = tmp_path / "s.jsonl"
    payload = json.loads(combos.read_text(encoding="utf-8"))
    cid = payload["combos"][0]["combo_id"]
    write_records(scaffolds, {cid: BakeRecord(
        combo_id=cid, status="unresolved",
        contract_fingerprint=contract_fingerprint(), baked_at="t")})
    out = tmp_path / "report.md"
    assert main(["report", "--scaffolds", str(scaffolds), "--combos", str(combos),
                 "--wave", "test", "--out", str(out)]) == 0
    assert "unresolved: 1/1" in out.read_text(encoding="utf-8")


def test_unknown_command_fails():
    with pytest.raises(SystemExit):
        main(["frobnicate"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_bake_cli.py -q`
Expected: FAIL — `ModuleNotFoundError` (no `resolver.bake.__main__`)

- [ ] **Step 3: Implement**

Create `resolver/bake/__main__.py`:

```python
"""CLI: python -m resolver.bake <select|run|dedup|report>.

Offline tooling beside the runtime resolvers, never the hot path. select and
report run keyless; run and dedup need a live key and exit loudly without
one — never a silent spend. Windows live runs need PYTHONUTF8=1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from resolver.bake.dedup import dedup_wave, load_registry, save_registry
from resolver.bake.report import wave_report
from resolver.bake.run import load_records, run_wave, write_records
from resolver.bake.select import load_selection, select_combos, write_selection
from resolver.harness import DEFAULT_ESCALATE_MODEL, DEFAULT_MODEL, build_model_list

DATA = Path("data/bake")


def _client_or_none():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic  # lazy: keyless commands need no SDK auth

    return anthropic.Anthropic()


def _add_ladder_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--escalate-model", default=DEFAULT_ESCALATE_MODEL)


def _ladder(args: argparse.Namespace) -> list[str]:
    escalate = None if args.escalate_model.lower() == "none" else args.escalate_model
    return build_model_list(args.model, args.attempts, escalate)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="resolver.bake",
                                     description="Offline bake pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_select = sub.add_parser("select", help="write the reviewable combo selection")
    p_select.add_argument("--n", type=int, default=300)
    p_select.add_argument("--seed", type=int, default=20260717)
    p_select.add_argument("--out", default=str(DATA / "combos-pilot.json"))

    p_run = sub.add_parser("run", help="bake scaffolds for the selection (spends money)")
    p_run.add_argument("--combos", default=str(DATA / "combos-pilot.json"))
    p_run.add_argument("--out", default=str(DATA / "scaffolds.jsonl"))
    p_run.add_argument("--retry-unresolved", action="store_true")
    _add_ladder_args(p_run)

    p_dedup = sub.add_parser("dedup", help="post-wave global rename pass")
    p_dedup.add_argument("--scaffolds", default=str(DATA / "scaffolds.jsonl"))
    p_dedup.add_argument("--names", default=str(DATA / "names.json"))
    p_dedup.add_argument("--events-out", default=str(DATA / "reports" / "rename-events.json"))
    _add_ladder_args(p_dedup)

    p_report = sub.add_parser("report", help="per-wave stats report (offline)")
    p_report.add_argument("--scaffolds", default=str(DATA / "scaffolds.jsonl"))
    p_report.add_argument("--combos", default=str(DATA / "combos-pilot.json"))
    p_report.add_argument("--renames", default=str(DATA / "reports" / "rename-events.json"))
    p_report.add_argument("--wave", default="wave1")
    p_report.add_argument("--out", default="")

    args = parser.parse_args(argv)

    if args.command == "select":
        builds = select_combos(args.n, args.seed)
        write_selection(builds, Path(args.out), args.seed)
        print(f"selected {len(builds)} combos (seed {args.seed}) -> {args.out}")
        print("review the file before running the bake - money moves on `run`.")
        return 0

    if args.command == "run":
        client = _client_or_none()
        if client is None:
            print("ANTHROPIC_API_KEY not set - `run` spends money and needs a live key.")
            return 1
        builds = load_selection(Path(args.combos))
        stats = run_wave(client, _ladder(args), builds, Path(args.out),
                         retry_unresolved=args.retry_unresolved)
        print("rates: " + ", ".join(f"{k} {v}" for k, v in stats.items()))
        return 0

    if args.command == "dedup":
        client = _client_or_none()
        if client is None:
            print("ANTHROPIC_API_KEY not set - `dedup` renames via the live ladder.")
            return 1
        path = Path(args.scaffolds)
        records = list(load_records(path).values())
        registry = load_registry(Path(args.names))
        events = dedup_wave(records, registry, client, _ladder(args))
        write_records(path, {r.combo_id: r for r in records})
        save_registry(Path(args.names), registry)
        events_path = Path(args.events_out)
        events_path.parent.mkdir(parents=True, exist_ok=True)
        events_path.write_text(json.dumps(events, indent=2), encoding="utf-8")
        suffixed = sum(1 for e in events if e["outcome"] == "suffixed")
        print(f"renames: {len(events)} (suffixed: {suffixed}) -> {args.events_out}")
        return 0

    # report
    records = list(load_records(Path(args.scaffolds)).values())
    builds = load_selection(Path(args.combos))
    renames_path = Path(args.renames)
    events = (json.loads(renames_path.read_text(encoding="utf-8"))
              if renames_path.exists() else [])
    md = wave_report(records, builds, events, args.wave)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"report -> {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_bake_cli.py -q` then `python -m pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
git add resolver/bake/__main__.py tests/test_bake_cli.py
git commit -m "feat: bake CLI - select/run/dedup/report subcommands, keyless-loud

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: Live pilot — HARD USER GATE (real dollars)

No new code. This is the validation gate from the spec (§10): run the pipeline against the real catalog with the real ladder and read the report with the user. **Do not start this task without the user's explicit go-ahead in this session — it spends real money.**

- [ ] **Step 1: Full suite green**

Run: `python -m pytest -q` — Expected: all green.

- [ ] **Step 2: Produce the reviewable selection**

```bash
python -m resolver.bake select --n 300 --seed 20260717 --out data/bake/combos-pilot.json
```

- [ ] **Step 3: STOP — user reviews the selection and approves the spend**

Present: combo count, shape/coherence distribution, the 7 pinned combos, and the econ-doc cost estimate (~$0.05/combo → ~$15 ± the top-up rate). The user must explicitly approve before Step 4. If they want a different N/seed, re-run Step 2.

- [ ] **Step 4: Commit the selection, then bake**

```bash
git add data/bake/combos-pilot.json
git commit -m "data: pilot combo selection (n=300, seed 20260717)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
PYTHONUTF8=1 python -m resolver.bake run
```

The run is resumable — if it dies, re-run the same command; existing combos are skipped. Record the printed rates (rates only — never investigate *why* any combo went unresolved).

- [ ] **Step 5: Dedup, report, commit the wave**

```bash
PYTHONUTF8=1 python -m resolver.bake dedup
python -m resolver.bake report --wave wave1 --out data/bake/reports/2026-07-17-wave1.md
git add data/bake/scaffolds.jsonl data/bake/names.json data/bake/reports/rename-events.json data/bake/reports/2026-07-17-wave1.md
git commit -m "data: pilot bake wave 1 - scaffolds, name registry, wave report

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Read the report with the user**

Walk through: unresolved rate (overall + pinned), width distribution and top-up count, rename outcomes and any suffix flags, per-tier cost adherence, category/harmless mix, outliers, measured $/combo and the marginal-item price it implies. Follow-ups (econ-doc measured-numbers edit, catalog-expansion decision) are the user's call — offer, don't start.

---

## Self-Review Notes (completed at plan-writing time)

- **Spec coverage:** §1 layout → Tasks 1–7; §2 schema/prompt → Tasks 1+4; §3 selection → Task 3; §4 derivation → Task 2; §5 runner/top-up → Task 4; §6 dedup → Task 5; §7 report → Task 6; §8 cost model → Tasks 6+8; §9 launch-scale is recorded-not-built (no task, by design); §10 testing → every task's tests + Task 8 gate.
- **Spec deviations (2), both flagged in File Structure:** fan+duck unpinnable (rubber duck left the catalog); the 9/9 build's powder item reconstructed as fertilizer (never recorded).
- **Type consistency:** `combo_id`/`contract_fingerprint`/`Depth`/`ScaffoldSet`/`BakeRecord` names match across Tasks 1–7; `fit_cost` defined in Task 2, used in Task 2 only; `slot_line` promoted in Task 4 before use; `run_wave(client, models, builds: dict[str, Build], path, retry_unresolved)` identical at definition (Task 4) and call site (Task 7).
