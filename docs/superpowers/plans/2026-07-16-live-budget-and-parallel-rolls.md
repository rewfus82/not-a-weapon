# Live Budget Normalization + Parallel Rolls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Live LLM drafts land exactly on the tier budget (proportions preserved), and playground rolls run in parallel.

**Architecture:** New pure `fill_budget(draft, tier)` in `resolver/clamp.py` (reuses `total_magnitude`/`_scale`), called only from `LLMResolver.resolve` on parsed drafts; `serve.roll` maps its n independent resolutions over a `ThreadPoolExecutor`. `clamp.apply`, solo, and the deterministic composer are untouched.

**Tech Stack:** Python 3.13 stdlib (`concurrent.futures`), pytest.

**Spec:** `docs/superpowers/specs/2026-07-16-live-budget-and-parallel-rolls-design.md`

## Global Constraints

- Scope: `resolver/clamp.py` (one added function only — `apply`/`clamp_magnitudes`/`TIER_BUDGET` values unchanged), `resolver/llm.py` (import + one call site), `resolver/serve.py` (`roll` only), and `tests/test_clamp.py`, `tests/test_llm.py`, `tests/test_serve.py`.
- `fill_budget` is called ONLY from `LLMResolver.resolve`. Solo must still total 2.0; deterministic composer totals must be unchanged (existing pins prove both).
- Zero-total drafts pass through `fill_budget` unchanged.
- No sampling params added to the API call (existing pin in `tests/test_llm.py:60`).
- The harness stays sequential — no `resolver/harness.py` changes.
- Keep the suite green at every commit. Baseline **244 passed**; Task 1 → 249, Task 2 → 251.
- Run tests with: `python -m pytest -q` from the repo root. No API key needed anywhere in this plan.
- Commit per task, conventional messages, ending with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Do NOT touch or stage `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`, or the 2026-07-10 plan/spec files (intentionally uncommitted).

---

### Task 1: `clamp.fill_budget` + LLM call site

**Files:**
- Modify: `resolver/clamp.py` (add one function after `clamp_magnitudes`)
- Modify: `resolver/llm.py` (import + the `return draft` line)
- Test: `tests/test_clamp.py`, `tests/test_llm.py`

**Interfaces:**
- Consumes: existing `total_magnitude(draft)`, `_scale(draft, factor)`, `TIER_BUDGET` in `resolver/clamp.py`.
- Produces: `fill_budget(draft: GadgetDraft, tier: Tier) -> GadgetDraft` — public, pure; consumed by `resolver/llm.py` in this task and by nothing else.

- [ ] **Step 1: Write the failing tests**

In `tests/test_clamp.py`, add `import pytest` above the existing imports, then append:

```python
def test_fill_budget_scales_up_preserving_ratios():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=30), Effect(kind=EffectKind.BURN, amount=10))
    out = clamp.fill_budget(d, Tier.LEGENDARY)  # budget 120, ratios 3:1
    amounts = [e.amount for s in out.stages for e in s.effects]
    assert amounts == [pytest.approx(90.0), pytest.approx(30.0)]


def test_fill_budget_scales_down_to_budget_not_cap():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=500))
    out = clamp.fill_budget(d, Tier.LEGENDARY)
    assert clamp.total_magnitude(out) == pytest.approx(clamp.TIER_BUDGET[Tier.LEGENDARY])


def test_fill_budget_passes_zero_total_through():
    d = _draft(Effect(kind=EffectKind.SNARE, amount=0))
    out = clamp.fill_budget(d, Tier.LEGENDARY)
    assert clamp.total_magnitude(out) == 0


def test_fill_budget_works_at_the_dud_floor():
    d = _draft(Effect(kind=EffectKind.DAMAGE, amount=1))
    out = clamp.fill_budget(d, Tier.DUD)
    assert clamp.total_magnitude(out) == pytest.approx(6.0)
```

In `tests/test_llm.py`, add `from resolver.clamp import TIER_BUDGET` to the imports, then append:

```python
def test_resolver_normalizes_parsed_drafts_to_the_tier_budget():
    # the model free-hands magnitudes; the resolver lands them on the budget
    client = FakeClient([_canned_draft()])  # canned draft totals 1
    resolver = LLMResolver(client, models=["claude-sonnet-5"])
    out = resolver.resolve(DEFAULT_BUILDS["broom_bat"], Tier.LEGENDARY)
    total = sum(e.amount for s in out.stages for e in s.effects)
    assert total == pytest.approx(TIER_BUDGET[Tier.LEGENDARY])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_clamp.py tests/test_llm.py -q`
Expected: the four `fill_budget` tests FAIL with `AttributeError: module 'resolver.clamp' has no attribute 'fill_budget'`; the llm test FAILS with total 1 ≠ 120.

- [ ] **Step 3: Implement**

In `resolver/clamp.py`, after `clamp_magnitudes`, add:

```python
def fill_budget(draft: GadgetDraft, tier: Tier) -> GadgetDraft:
    """Scale a draft so its total magnitude lands exactly on the tier budget,
    preserving the composition's proportions. The LLM path calls this on
    parsed drafts (models free-hand magnitudes); the deterministic composer
    already fills the budget by construction. Zero-total drafts (pure
    duration-carried control) pass through — there are no proportions to
    scale. Never called from `apply` — solo stays pathetic.
    """
    total = total_magnitude(draft)
    if total == 0:
        return copy.deepcopy(draft)
    return _scale(draft, TIER_BUDGET[tier] / total)
```

In `resolver/llm.py`, add the import:

```python
from resolver.clamp import fill_budget
```

and in `resolve`, replace `return draft` with:

```python
                    return fill_budget(draft, tier)
```

(The surrounding `if draft is not None:` guard stays as is.)

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: 249 passed (244 + 5). The existing solo pins (2.0) and composer budget pins prove nothing else moved.

- [ ] **Step 5: Commit**

```bash
git add resolver/clamp.py resolver/llm.py tests/test_clamp.py tests/test_llm.py
git commit -m "feat: live drafts normalize to the tier budget (proportions preserved)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Parallel playground rolls

**Files:**
- Modify: `resolver/serve.py` (imports + `roll`)
- Test: `tests/test_serve.py`

**Interfaces:**
- Consumes: existing `_resolve_once(resolver_fn, build, tier)` and `gadget_to_dict(resolved, source)` in `resolver/serve.py`.
- Produces: `roll(resolver_fn, build, tier, n) -> list[dict]` — same signature and result shape, now concurrent.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_serve.py` (`threading` import goes at the top of the file with the other imports):

```python
def test_roll_runs_slots_concurrently():
    # a resolver that blocks until all n calls have started can only finish
    # if roll() runs its slots in parallel — sequential execution deadlocks
    # (the barrier would time out and every slot would fall back)
    barrier = threading.Barrier(3, timeout=5)

    def blocking(build, tier):
        barrier.wait()
        return fallback.resolve(build, tier)

    results = serve.roll(blocking, DEFAULT_BUILDS["broom_bat"], Tier.EPIC, 3)
    assert len(results) == 3
    assert all(r["source"] == "llm" for r in results)


def test_roll_tags_only_the_failing_slot_as_fallback():
    lock = threading.Lock()
    calls = []

    def flaky(build, tier):
        with lock:
            calls.append(1)
            fail = len(calls) == 2
        if fail:
            raise RuntimeError("refused")
        return fallback.resolve(build, tier)

    results = serve.roll(flaky, DEFAULT_BUILDS["broom_bat"], Tier.EPIC, 3)
    assert len(results) == 3
    assert sum(1 for r in results if r["source"] == "fallback") == 1
    assert all(r["stages"] for r in results)
```

Also add `import threading` at the top of `tests/test_serve.py`.

- [ ] **Step 2: Run tests to verify the concurrency test fails**

Run: `python -m pytest tests/test_serve.py -q`
Expected: `test_roll_runs_slots_concurrently` FAILS — sequential `roll` deadlocks the barrier until its 5s timeout, every `barrier.wait()` raises `BrokenBarrierError`, and all three slots come back `"fallback"` (the `all(... == "llm")` assert fails). `test_roll_tags_only_the_failing_slot_as_fallback` PASSES already (it doesn't require concurrency) — that's expected; it pins the per-slot degrade surviving the rewrite.

- [ ] **Step 3: Implement**

In `resolver/serve.py`, add to the stdlib imports:

```python
from concurrent.futures import ThreadPoolExecutor
```

Replace `roll`:

```python
def roll(resolver_fn, build: Build, tier: Tier, n: int) -> list[dict]:
    """The n rolls are independent resolver calls; run them concurrently so
    n live rolls cost roughly one roll of wall-clock. Results stay in slot
    order (executor.map preserves it)."""
    n = max(1, n)

    def one(_: int) -> dict:
        source, resolved = _resolve_once(resolver_fn, build, tier)
        return gadget_to_dict(resolved, source)

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(one, range(n)))
```

- [ ] **Step 4: Run the full suite, then a keyless timing smoke**

Run: `python -m pytest -q`
Expected: 251 passed.

Run (bash):

```bash
python -c "
import time
from resolver import serve, fallback
from resolver.contract import Tier
from resolver.items import DEFAULT_BUILDS

def slow(build, tier):
    time.sleep(0.5)
    return fallback.resolve(build, tier)

t0 = time.perf_counter()
serve.roll(slow, DEFAULT_BUILDS['broom_bat'], Tier.EPIC, 4)
print(f'4 rolls with a 0.5s resolver: {time.perf_counter()-t0:.2f}s')
"
```

Expected: roughly `0.5s` (parallel), not `2.0s` (sequential).

- [ ] **Step 5: Commit**

```bash
git add resolver/serve.py tests/test_serve.py
git commit -m "feat: playground rolls run in parallel

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
