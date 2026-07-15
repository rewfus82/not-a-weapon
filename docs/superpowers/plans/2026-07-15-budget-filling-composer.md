# Budget-Filling Composer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every deterministic build totals exactly `TIER_BUDGET[tier]` regardless of item/effect count (GAME_IDENTITY §6), with overlays at half a base share; solo resolution decouples from the deleted `_TIER_SEED`.

**Architecture:** `fallback.resolve` derives each effect's amount from the tier budget (`budget × weight / total_weight`; base weight 1.0, overlay 0.5) instead of flat per-effect seeds. `solo.py` gets its own pinned `_SOLO_AMOUNT = 2.0` and `_TIER_SEED` is deleted. The clamp and LLM path are untouched.

**Tech Stack:** Python 3.13, pytest.

**Spec:** `docs/superpowers/specs/2026-07-15-budget-filling-composer-design.md`

## Global Constraints

- Scope: `resolver/fallback.py`, `resolver/solo.py`, `tests/test_fallback.py`, `tests/test_solo.py` ONLY. Zero changes to `resolver/clamp.py` (including `TIER_BUDGET` values), `resolver/llm.py`, `resolver/contract.py`.
- Solo behavior stays byte-identical: total 2.0 at `Tier.DUD` (the constant moves, the value doesn't).
- The existing take-by-tier logic (1 effect at DUD, 2 until RARE, full chain at RARE+) and overlay gating (RARE+) are unchanged — only amounts change.
- Effect `note` values stay `"base"` / `"overlay"` as today.
- Keep the suite green at every commit. Baseline **240 passed**; Task 1 → 243, Task 2 → 244.
- Run tests with: `python -m pytest -q` from the repo root. No API key needed anywhere in this plan.
- Commit per task, conventional messages, ending with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Do NOT touch or stage `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`, or the 2026-07-10 plan/spec files (intentionally uncommitted).

---

### Task 1: Composer fills the tier budget

**Files:**
- Modify: `resolver/fallback.py` (imports + the effect construction in `resolve`, lines ~15-18 and ~64-81)
- Test: `tests/test_fallback.py`

**Interfaces:**
- Consumes: `TIER_BUDGET: dict[Tier, float]` from `resolver/clamp.py` (existing; clamp imports nothing from fallback, so no import cycle).
- Produces: `fallback.resolve(build, tier)` drafts whose `sum(e.amount)` == `TIER_BUDGET[tier]` exactly — consumed by Task 2's solo-below-DUD-craft pin. `_TIER_SEED` stays in the module for now (solo still imports it; Task 2 deletes it).

- [ ] **Step 1: Write the failing tests**

In `tests/test_fallback.py`, add to the top imports:

```python
import pytest

from resolver.clamp import TIER_BUDGET, apply as clamp_apply
```

Append:

```python
def test_every_build_fills_the_tier_budget_exactly():
    # §6: same power total within a tier, whatever the item/effect count
    builds = {
        **DEFAULT_BUILDS,
        "lone_gun": Build(delivery_item=CATALOG["9mm pistol"]),
        "lone_jerrycan": Build(delivery_item=CATALOG["jerrycan of gasoline"]),
        "overlay_build": Build(delivery_item=CATALOG["t-shirt cannon"],
                               modifier_item=CATALOG["propane tank"]),
    }
    for key, build in builds.items():
        for tier in Tier:
            draft = fallback.resolve(build, tier)
            total = sum(e.amount for s in draft.stages for e in s.effects)
            assert total == pytest.approx(TIER_BUDGET[tier]), (key, tier.value)


def test_overlay_rides_at_half_a_base_share():
    # cannon+propane at LEGENDARY: base [BURN] w=1, overlay [EXPLODE] w=0.5
    build = Build(delivery_item=CATALOG["t-shirt cannon"],
                  modifier_item=CATALOG["propane tank"])
    draft = fallback.resolve(build, Tier.LEGENDARY)
    amounts = {e.note: e.amount for s in draft.stages for e in s.effects}
    assert amounts["overlay"] == pytest.approx(amounts["base"] / 2)


def test_deterministic_path_never_trips_the_clamp_cap():
    # budget < budget*1.12, so the clamp must pass composed drafts through
    # untouched — the over-budget headroom is booster-only again
    for build in DEFAULT_BUILDS.values():
        for tier in Tier:
            draft = fallback.resolve(build, tier)
            resolved = clamp_apply(draft, build, tier)
            before = sum(e.amount for s in draft.stages for e in s.effects)
            after = sum(e.amount for s in resolved.draft.stages for e in s.effects)
            assert after == pytest.approx(before)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fallback.py -q`
Expected: `test_every_build_fills_the_tier_budget_exactly` and `test_overlay_rides_at_half_a_base_share` FAIL (totals are seed-based today, e.g. DUD totals 2.0 ≠ 6.0; overlay is seed×0.5, not base/2 of a budget share — numerically overlay == base/2 holds today too, so if that one passes, note it and move on; the budget test is the real RED). `test_deterministic_path_never_trips_the_clamp_cap` FAILS at LEGENDARY (3-effect builds total 135 > cap 134.4 and get scaled).

- [ ] **Step 3: Implement the budget-derived amounts**

In `resolver/fallback.py`, add to the imports:

```python
from resolver.clamp import TIER_BUDGET
```

In `resolve`, delete the line `seed = _TIER_SEED[tier]` and replace the effect-construction block:

```python
    effects = [Effect(kind=k, amount=seed, note="base") for k in chosen]
    # overlays only unlock at RARE+; a kind the base chain already has is skipped
    if tier_at_least(tier, Tier.RARE):
        for k in _overlays(build):
            if k in chosen:
                continue
            effects.append(Effect(kind=k, amount=seed * 0.5, note="overlay"))
```

with:

```python
    # §6: every build at a tier spends the same budget — it splits across the
    # composed effects (overlays ride at half a base share). Overlays only
    # unlock at RARE+; a kind the base chain already has is skipped.
    parts: list[tuple[EffectKind, float, str]] = [(k, 1.0, "base") for k in chosen]
    if tier_at_least(tier, Tier.RARE):
        for k in _overlays(build):
            if k in chosen:
                continue
            parts.append((k, 0.5, "overlay"))
    budget = TIER_BUDGET[tier]
    total_weight = sum(w for _, w, _ in parts)
    effects = [
        Effect(kind=k, amount=budget * w / total_weight, note=note)
        for k, w, note in parts
    ]
```

Leave the `_TIER_SEED` dict itself in place — `resolver/solo.py` still imports it until Task 2.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: 243 passed.

- [ ] **Step 5: Commit**

```bash
git add resolver/fallback.py tests/test_fallback.py
git commit -m "feat: composer fills the tier budget exactly (§6 same-power-within-tier)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Solo decoupling; delete `_TIER_SEED`

**Files:**
- Modify: `resolver/solo.py` (imports + the seed constant)
- Modify: `resolver/fallback.py` (delete the `_TIER_SEED` dict)
- Test: `tests/test_solo.py`

**Interfaces:**
- Consumes: `fallback.resolve` budget-filling behavior (Task 1) for the pin test.
- Produces: nothing consumed later (final task). `_TIER_SEED` no longer exists anywhere.

- [ ] **Step 1: Add the pin test (passes already — it is a regression pin, not a RED)**

In `tests/test_solo.py`, extend the imports: change `from resolver.items import CATALOG` to `from resolver.items import CATALOG, Build` and add `from resolver import fallback`. Append:

```python
def test_solo_stays_below_even_a_dud_craft():
    # bare pickup never competes with crafting, even at the floor:
    # solo is a pinned 2.0; a DUD craft fills the DUD budget (6.0)
    r = solo.resolve_solo(CATALOG["crowbar"])
    solo_total = sum(e.amount for s in r.draft.stages for e in s.effects)
    craft = fallback.resolve(Build(delivery_item=CATALOG["crowbar"]), Tier.DUD)
    craft_total = sum(e.amount for s in craft.stages for e in s.effects)
    assert solo_total < craft_total
```

Run: `python -m pytest tests/test_solo.py -q`
Expected: all pass (this pin holds after Task 1; it exists to catch future regressions).

- [ ] **Step 2: Decouple solo**

In `resolver/solo.py`, drop `_TIER_SEED` from the fallback import (keep `substance_stages`), and replace:

```python
BASE_USE_TIER: Tier = Tier.DUD
_SOLO_SEED: float = _TIER_SEED[BASE_USE_TIER]
```

with:

```python
BASE_USE_TIER: Tier = Tier.DUD
_SOLO_AMOUNT: float = 2.0  # code-owned; a bare item is pathetic, below even a DUD craft
```

and update its single use in `solo_draft` (`amount=_SOLO_SEED` → `amount=_SOLO_AMOUNT`).

- [ ] **Step 3: Delete `_TIER_SEED` from `resolver/fallback.py`**

Remove the whole dict. Then verify nothing references it:

Run: `grep -rn "_TIER_SEED" resolver/ tests/`
Expected: no matches.

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: 244 passed (solo totals still 2.0 — behavior byte-identical; the determinism and floor tests in `tests/test_solo.py` prove the refactor changed nothing).

- [ ] **Step 5: Commit**

```bash
git add resolver/solo.py resolver/fallback.py tests/test_solo.py
git commit -m "refactor: solo owns its floor amount; _TIER_SEED deleted

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Verification (no new code)

- [ ] **Step 1: Full suite**

Run: `python -m pytest -q`
Expected: 244 passed.

- [ ] **Step 2: Eyeball the deterministic spread**

Run (PowerShell): `$env:PYTHONUTF8 = '1'; python -m resolver.harness --fallback --build swamp_cooler --build gun_ammo --repeats 1`
Expected: every tier's amounts sum to that tier's budget on both builds — e.g. swamp_cooler LEGENDARY shows three effects at 40 each (was 44.8 each); gun_ammo LEGENDARY shows one DAMAGE at 120 (was 45). No exceptions, no API key.

- [ ] **Step 3: Report**

No commit. Paste the two LEGENDARY snippets for the user's eyeball check and note that further tuning is now a single knob (`TIER_BUDGET`).
