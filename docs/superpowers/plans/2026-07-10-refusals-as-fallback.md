# Refusals as a Normal Fallback Outcome — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the resolver harness treat a live-LLM refusal/no-draft as a normal outcome — fall back to the deterministic resolver (a valid, labeled instance) and report a per-build fallback rate — instead of leaving an empty `[resolution failed]` hole in the spread.

**Architecture:** The harness's per-slot `try/except` stops emitting an empty draft on failure and instead calls the existing deterministic `fallback_resolve`, tags the slot `source="fallback"` with a one-line reason, and clamps it like any other. `RunResult` carries the source/reason; the renderer marks fallback slots and a new summary renderer prints the rate. No changes to the clamp, contract, LLM call, or fallback resolver.

**Tech Stack:** Python 3, dataclasses, pytest. No new dependencies.

## Global Constraints

- **Engine-agnostic:** zero Unreal/engine references in the Python (CLAUDE.md).
- **Deterministic fallback must always produce a valid instance** and never depend on an API key (CLAUDE.md #6). Only the live-LLM call is wrapped; if `fallback_resolve` itself raises, that is a bug and must propagate — do not swallow it.
- **Never classify *why* a build refused.** Capture only the exception's `type: message` string to label the slot. No model call that introspects a refusal.
- **Code owns balance:** every draft (LLM or fallback) still passes through `clamp_apply` (CLAUDE.md #4).
- **TDD:** deterministic behavior — red-green-refactor, commit per task.
- Separator in the summary line is ASCII `" | "` (not a middle-dot) to avoid Windows console encoding issues; this is a deliberate, cosmetic deviation from the spec's example.

---

### Task 1: `RunResult` carries source/reason; renderer marks fallback slots

**Files:**
- Modify: `resolver/render.py` (the `RunResult` dataclass, lines 13-18; `_render_one`, lines 35-48)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: existing `RunResult(build_key, resolved, run_index, run_total)` positional construction (must stay valid — several tests build it positionally).
- Produces: `RunResult` with two new **optional** fields — `source: str = "llm"`, `reason: str | None = None`. `_render_one` appends `  [fallback]` to the tier header and a `  fallback: <reason>` line when `source == "fallback"`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render.py`:

```python
def test_render_marks_fallback_slots_with_tag_and_reason():
    results = [
        RunResult("fan+duck", _resolved("Plan B", Tier.RARE, Category.WEAPON, False), 1, 3,
                  source="fallback", reason="RuntimeError: no GadgetDraft (stop_reason='refusal')"),
        RunResult("fan+duck", _resolved("Live One", Tier.RARE, Category.WEAPON, False), 2, 3),
    ]
    out = render_run(results)
    assert out.count("[fallback]") == 1          # only the fallback slot is tagged
    assert "RuntimeError: no GadgetDraft" in out # its reason is shown
    assert "Plan B" in out and "Live One" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render.py::test_render_marks_fallback_slots_with_tag_and_reason -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'source'`

- [ ] **Step 3: Write minimal implementation**

In `resolver/render.py`, extend the dataclass:

```python
@dataclass
class RunResult:
    build_key: str
    resolved: ResolvedGadget
    run_index: int
    run_total: int
    source: str = "llm"
    reason: str | None = None
```

And update `_render_one` to tag fallback slots and print the reason:

```python
def _render_one(result: RunResult) -> str:
    rg = result.resolved
    tag = "  [fallback]" if result.source == "fallback" else ""
    lines = [
        f"--- {rg.tier.value} ---  ({rg.category.value}, harmless={rg.harmless})  "
        f"[run {result.run_index}/{result.run_total}]{tag}",
        f"  name:  {rg.draft.name}",
        f"  logic: {rg.draft.logic}",
    ]
    if result.source == "fallback" and result.reason:
        lines.append(f"  fallback: {result.reason}")
    lines.append("  stages:")
    for stage in rg.draft.stages:
        lines.append(f"    {stage.trigger.value}:")
        for effect in stage.effects:
            lines.append(f"      {_render_effect(effect)}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_render.py -v`
Expected: PASS (the new test and the existing `test_render_groups_by_build_and_shows_both_axes` / `test_render_prints_build_header_once_per_build`, which construct `RunResult` positionally and rely on the new defaults).

- [ ] **Step 5: Commit**

```bash
git add resolver/render.py tests/test_render.py
git commit -m "feat: RunResult carries source/reason; renderer tags fallback slots"
```

---

### Task 2: Per-build fallback-rate summary renderer

**Files:**
- Modify: `resolver/render.py` (add `render_fallback_summary`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `RunResult` with `source` from Task 1.
- Produces: `render_fallback_summary(results: list[RunResult]) -> str` — a single line `"fallbacks: <key> k/n[ (pct%)] | <key> k/n ..."`, builds in first-appearance order, every build shown (including `0/n`), percent only when `k > 0`, `pct = round(100*k/n)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_render.py`:

```python
from resolver.render import RunResult, render_run, render_fallback_summary  # update existing import


def test_fallback_summary_reports_rate_including_zero_builds():
    results = [
        RunResult("broom+oil", _resolved("A", Tier.DUD, Category.WEAPON, False), 1, 1),
        RunResult("fan+duck", _resolved("B", Tier.RARE, Category.WEAPON, False), 1, 3,
                  source="fallback", reason="x"),
        RunResult("fan+duck", _resolved("C", Tier.RARE, Category.WEAPON, False), 2, 3,
                  source="fallback", reason="x"),
        RunResult("fan+duck", _resolved("D", Tier.RARE, Category.WEAPON, False), 3, 3),
    ]
    summary = render_fallback_summary(results)
    assert summary.startswith("fallbacks:")
    assert "broom+oil 0/1" in summary            # zero-fallback build still shown, no percent
    assert "fan+duck 2/3 (67%)" in summary       # round(100*2/3) == 67
```

(The `render_fallback_summary` name in the import line is what makes this fail first.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_render.py::test_fallback_summary_reports_rate_including_zero_builds -v`
Expected: FAIL with `ImportError: cannot import name 'render_fallback_summary'`

- [ ] **Step 3: Write minimal implementation**

Append to `resolver/render.py`:

```python
def render_fallback_summary(results: list[RunResult]) -> str:
    order: list[str] = []
    total: dict[str, int] = {}
    fell: dict[str, int] = {}
    for result in results:
        key = result.build_key
        if key not in total:
            order.append(key)
            total[key] = 0
            fell[key] = 0
        total[key] += 1
        if result.source == "fallback":
            fell[key] += 1
    parts: list[str] = []
    for key in order:
        n, k = total[key], fell[key]
        part = f"{key} {k}/{n}"
        if k:
            part += f" ({round(100 * k / n)}%)"
        parts.append(part)
    return "fallbacks: " + " | ".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_render.py -v`
Expected: PASS (all render tests).

- [ ] **Step 5: Commit**

```bash
git add resolver/render.py tests/test_render.py
git commit -m "feat: per-build fallback-rate summary renderer"
```

---

### Task 3: Harness falls back on refusal and prints the summary

**Files:**
- Modify: `resolver/harness.py` (`run`, lines 33-57; `main`, lines 70-91; imports, line 16)
- Test: `tests/test_harness.py`

**Interfaces:**
- Consumes: `fallback_resolve` (already imported at `harness.py:14`), `clamp_apply`, `RunResult` (now with `source`/`reason` from Task 1), `render_fallback_summary` from Task 2.
- Produces: `run()` returns `list[RunResult]` where each slot is `source="llm"` (resolver succeeded) or `source="fallback"` (resolver raised → deterministic substitute); `run()` never raises when `resolver_fn` raises. `main()` prints the spread then the fallback summary.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_harness.py`:

```python
def test_run_falls_back_on_resolver_refusal():
    def flaky(build, tier):
        if tier is Tier.LEGENDARY:
            raise RuntimeError("no GadgetDraft (stop_reason='refusal')")
        return fallback.resolve(build, tier)

    results = harness.run(flaky, build_keys=["broom+oil"], repeats=3)
    leg = [r for r in results if r.resolved.tier is Tier.LEGENDARY]
    assert len(leg) == 3
    assert all(r.source == "fallback" for r in leg)
    assert all(r.resolved.draft.stages for r in leg)          # valid, non-empty instance
    assert all("RuntimeError" in (r.reason or "") for r in leg)
    non_leg = [r for r in results if r.resolved.tier is not Tier.LEGENDARY]
    assert non_leg and all(r.source == "llm" for r in non_leg)


def test_run_survives_total_refusal_with_all_fallbacks():
    def always_refuse(build, tier):
        raise RuntimeError("no GadgetDraft")

    results = harness.run(always_refuse, build_keys=["broom+oil"], repeats=3)
    assert len(results) == 12
    assert all(r.source == "fallback" for r in results)


def test_main_prints_fallback_summary(capsys):
    exit_code = harness.main(["--fallback", "--build", "broom+oil", "--repeats", "2"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "fallbacks:" in out
    assert "broom+oil 0/" in out   # the deterministic resolver never "refuses"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_harness.py::test_run_falls_back_on_resolver_refusal tests/test_harness.py::test_main_prints_fallback_summary -v`
Expected: FAIL — the refusal test fails because the current except block builds a `GadgetDraft(name="[resolution failed]", stages=[])` (empty stages, `source` defaults to `"llm"`), so `r.source == "fallback"` and the non-empty-stages assertions fail; the summary test fails because `main` prints no `fallbacks:` line.

- [ ] **Step 3: Write the implementation**

In `resolver/harness.py`, replace the `run` loop body (the `try/except` at lines 43-56) so a failure falls back to the deterministic resolver:

```python
def run(resolver_fn: ResolverFn, build_keys: list[str], repeats: int) -> list[RunResult]:
    results: list[RunResult] = []
    schedule = tier_schedule(repeats)
    totals: dict[Tier, int] = {t: schedule.count(t) for t in set(schedule)}
    for key in build_keys:
        build = DEFAULT_BUILDS[key]
        counters: dict[Tier, int] = {}
        for tier in schedule:
            counters[tier] = counters.get(tier, 0) + 1
            try:
                draft = resolver_fn(build, tier)
                source, reason = "llm", None
            except Exception as exc:
                # A refusal or transport error is a normal, expected outcome for a
                # fraction of builds. Fall back to the deterministic resolver (always
                # a valid instance) and record the slot. We never classify *why*.
                draft = fallback_resolve(build, tier)
                source = "fallback"
                reason = f"{type(exc).__name__}: {exc}"
            resolved = clamp_apply(draft, build, tier)
            results.append(RunResult(key, resolved, counters[tier], totals[tier], source, reason))
    return results
```

Update the imports at `harness.py:16` to pull in the summary renderer:

```python
from resolver.render import RunResult, render_fallback_summary, render_run
```

Remove the now-unused `GadgetDraft` import if nothing else in the file uses it (check line 13: `from resolver.contract import GadgetDraft, Tier` → becomes `from resolver.contract import Tier`).

In `main`, print the summary after the spread (replace lines 89-90):

```python
    results = run(resolver_fn, build_keys, args.repeats)
    print(render_run(results))
    print()
    print(render_fallback_summary(results))
    return 0
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `python -m pytest -v`
Expected: PASS — all new harness tests plus the existing suite (including `test_main_runs_the_fallback_path_and_prints`, which still finds `BUILD: broom+oil` and `LEGENDARY`).

- [ ] **Step 5: Commit**

```bash
git add resolver/harness.py tests/test_harness.py
git commit -m "feat: harness falls back on refusal and reports per-build fallback rate"
```

---

### Task 4: Durable note in HANDOFF

**Files:**
- Modify: `docs/HANDOFF.md` (append a new section before "## After this task")

No test — documentation only. Folded into its own task because it is the durable knowledge this whole change exists to preserve, and a reviewer can accept it independently.

- [ ] **Step 1: Add the section**

Insert into `docs/HANDOFF.md`, immediately before the `## After this task` heading:

```markdown
## Refusals are an expected pipeline outcome — design for them

A general-purpose model refuses or returns no parseable draft on a fraction of
builds, sometimes for reasons unrelated to intent. The harness treats this as
normal: a refused (build, tier) falls back to the deterministic resolver (a
valid, if less inspired, instance), is tagged `[fallback]` in the spread, and is
counted toward a per-build fallback rate printed after the run. A refusal is
never an error and never a hole in the spread. This is exactly why the
deterministic fallback is non-negotiable (CLAUDE.md #6) — it is the shock
absorber that keeps an offline bake whole.

**Never have an agent introspect *why* a build was refused.** Asking a model to
categorize a refusal reads worse than the original generation and has flagged a
session. Log the rate; do not chase the reason.

**When a *harmless* build refuses often, look at its item associations as data.**
A word in the association cloud may point somewhere unintended. Prefer stylized,
plainly-non-real associations over accurate real-world chemistry; the more the
content reads as make-believe, the fewer false trips. This is a data/framing
lever, tracked separately from the pipeline plumbing above.
```

- [ ] **Step 2: Commit**

```bash
git add docs/HANDOFF.md
git commit -m "docs: refusals are an expected fallback outcome; never introspect them"
```

---

## Self-Review

**Spec coverage:**
- Behavior split (success vs refusal→fallback) → Task 3. ✓
- Rate metric / summary block → Task 2 (renderer) + Task 3 (main prints it). ✓
- `RunResult` gains `source`/`reason`; renderer tags `[fallback]` + reason line → Task 1. ✓
- Reason captured from exception (`type: message`, no why-classification) → Task 3 impl + assertion. ✓
- Fallback itself raising must propagate → Global Constraints + only the `resolver_fn` call is wrapped. ✓
- Tests: selective refusal, total refusal, reason capture, renderer tag, summary incl. zero-builds → Tasks 1–3. ✓
- Durable doc note → Task 4. ✓
- No item-data / prompt changes → none in plan. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code; every command has expected output. ✓

**Type consistency:** `RunResult(..., source: str = "llm", reason: str | None = None)` defined in Task 1 and used positionally/by-keyword identically in Tasks 2–3. `render_fallback_summary(results: list[RunResult]) -> str` defined in Task 2, imported and called in Task 3. `source` compared to the literals `"llm"`/`"fallback"` everywhere. ✓

**Deviation noted:** summary separator is ASCII `" | "` rather than the spec's cosmetic middle-dot, to avoid Windows console encoding failures on `print`. ✓
