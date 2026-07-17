# Live-path budget normalization + parallel playground rolls — design

**Date:** 2026-07-16
**Scope:** `resolver/clamp.py` (one new pure function), `resolver/llm.py` (one call site), `resolver/serve.py` (`roll` parallelism), and tests. No enum/contract changes; solo and the deterministic composer untouched.

## Problems (observed in play, 2026-07-16)

1. **Live rolls don't honor §6.** Nine pasted LEGENDARY rolls totaled 28.6–134.4: the model free-hands magnitudes, the clamp has only a ceiling, and overshooters get scaled to the *cap* (134.4 = 120 × 1.12), not the budget — consuming the booster-only headroom. Same tier, same build, ~4.7× power spread.
2. **Playground rolls are sequential.** `roll()` loops n times; 3 LEGENDARY rolls ≈ 3 minutes of wall-clock for fully independent calls.

## Design

### 1. `clamp.fill_budget(draft, tier)` — LLM drafts land on the budget

New pure function in `resolver/clamp.py` (the balance module owns budget math; reuses the existing `total_magnitude` and `_scale`):

- If `total_magnitude(draft) > 0`: return `_scale(draft, TIER_BUDGET[tier] / total)` — the draft's total becomes exactly the tier budget, **preserving the model's proportions** (a KNOCKBACK-dominant composition stays KNOCKBACK-dominant). Scales up (undershooters) and down (overshooters) alike.
- If total is 0 (a pure duration-carried control draft with all amounts zero): return the draft unchanged — there are no proportions to scale, and inventing amounts for effects the model zeroed is a different decision. Rare; documented.

**Call site:** `LLMResolver.resolve` (`resolver/llm.py`) applies `fill_budget(draft, tier)` to a successfully parsed draft before returning it. Nothing else calls it:

- `clamp.apply` does NOT call it — the clamp stays a pure safety net (cap + DUD floor), and **solo stays pathetic** (2.0, not inflated to the DUD budget).
- The deterministic composer already fills the budget by construction (2026-07-15 change) — after this, *both* resolvers hand `clamp.apply` drafts that already sit on budget, and the cap headroom is booster-only in fact as well as intent.

### 2. Parallel playground rolls

`serve.roll` runs its n resolutions (already capped at 4) through `concurrent.futures.ThreadPoolExecutor(max_workers=n)` via `executor.map`, preserving result order. Each worker is the existing `_resolve_once` (independent; the Anthropic SDK client and both resolvers are safe for concurrent request use). Wall-clock for 4 rolls ≈ 1 roll. `--fallback` mode parallelizes harmlessly (sub-millisecond calls).

The harness stays sequential — its job is controlled measurement, not interactivity.

## Testing (all keyless)

- `fill_budget`: undershooting draft scales up to exactly `TIER_BUDGET[tier]` with ratios preserved (e.g. 3:1 stays 3:1); overshooting draft scales down to the budget (not the cap); zero-total draft passes through unchanged; DUD tier works (budget 6.0).
- `LLMResolver` + fake client: a parsed draft comes back totaling exactly the tier budget (extends the existing fake-client contract tests in `tests/test_llm.py`).
- `serve.roll`: still returns n ordered results; a resolver stub that fails on one call still yields a fallback-tagged slot in the right position (thread-safe counter). No timing assertions (flaky); parallelism is verified by construction plus a live eyeball.
- Existing pins that must survive: solo totals 2.0; deterministic composer totals; clamp cap/floor tests.

## Out of scope

- Sampling params / name-dedup for repeated rolls (bake-pipeline requirement, logged).
- UI progress feedback per attempt ("Rolling… attempt 2") — nice-to-have, not in this pass.
- Any harness changes.
