# Design — Refusals as a normal fallback outcome

*Date: 2026-07-10 · Scope: resolver harness plumbing + a durable doc note. No weapon-content generation.*

## Problem

The offline generation harness calls a live LLM to propose weapon composition. A general-purpose model will, for some fraction of (build, tier) calls, **refuse or return no parseable draft** — sometimes for reasons unrelated to intent. Today the harness catches the raised exception and records the slot as an empty `[resolution failed]` DUD (`harness.py:44-56`). That survives the run but leaves a **hole** in the spread: no valid instance for that slot, and no visibility into how often it happens.

Per the resolver invariants (CLAUDE.md #6, GAME_IDENTITY §6/§9), a refusal must degrade to the **deterministic fallback producing a valid instance**, and a bake should read a **refusal rate as an expected metric**, never a crash.

## Non-goals

- **No introspection of *why* a build refused.** Asking a model to categorize a refusal is a dead end that has flagged a session. We treat a refusal as a normal outcome and move on.
- **No item-data / prompt-framing changes** in this task (separate follow-up). We only note the design lever.
- No changes to the clamp, contract, fallback resolver, or LLM call itself beyond what the harness needs.

## Behavior

`run()` distinguishes two outcomes per slot instead of one:

- **Success** — resolver returned a draft → clamp it → slot is `source="llm"` (unchanged from today).
- **Refusal or error** — resolver raised (covers `llm.py`'s "no GadgetDraft" `RuntimeError` *and* transport/SDK errors) → call `fallback_resolve(build, tier)` → clamp that → slot is `source="fallback"`, with a one-line `reason` captured from the exception (`f"{type(exc).__name__}: {exc}"`).

Refusal and transport error are handled **identically** (both fall back). We capture the exception string only to label the slot — this is reporting our own failure mode, not classifying the model's refusal category.

The empty `[resolution failed]` DUD path is removed; a refused slot now always holds a valid deterministic instance.

## Rate metric

`run()` tallies, per build, `fallback_count / total_slots`. The harness prints a summary block after the spread:

```
fallbacks: broom+oil 0/9 · aerosol+candles 1/9 (11%) · fan+duck 6/9 (67%)
```

A build with 0 fallbacks still appears (shows `0/N`) so the metric is always legible.

## Components touched

- **`resolver/render.py`** — `RunResult` gains `source: str` (`"llm"` | `"fallback"`) and `reason: str | None`. The renderer prefixes fallback slots with a `[fallback]` tag and prints the reason line; llm slots are unchanged. A new summary renderer formats the per-build rate line. (Read the file first; match existing format.)
- **`resolver/harness.py`** — `run()` implements the success/fallback split and constructs `RunResult`s with `source`/`reason`. The per-build tally is derived from `results` (each `RunResult` already carries `source`), so `run()`'s return type is unchanged — no separate tally object. `main()` computes the tally from the returned results and prints the summary block.
- **`docs/HANDOFF.md`** — durable note (below).

The deterministic `fallback_resolve` and `clamp_apply` are reused as-is; no signature changes.

## Data flow

```
for build, tier in schedule:
    try:
        draft  = resolver_fn(build, tier)      # live LLM
        source = "llm";  reason = None
    except Exception as exc:
        draft  = fallback_resolve(build, tier) # deterministic, always valid
        source = "fallback"
        reason = f"{type(exc).__name__}: {exc}"
    resolved = clamp_apply(draft, build, tier) # code owns balance either way
    results.append(RunResult(key, resolved, i, n, source, reason))
# summary: per-build fallback_count / total
```

Note: if `fallback_resolve` *itself* raised, that is a genuine bug in deterministic code (the fallback must never fail) and should propagate — we do not swallow it. Only the live-LLM call is wrapped.

## Testing (TDD — deterministic, red-green-refactor)

Contract tests with fake resolvers (no live API, matching the repo's existing `test_llm.py` style):

1. **Selective refusal** — fake resolver raises on chosen (build, tier) pairs, returns a draft otherwise. Assert: raised slots come back `source="fallback"` with a non-empty clamped instance; other slots are `source="llm"`; tally counts only the raised ones.
2. **Total refusal** — fake raises on every call. Assert: every slot is a valid fallback instance, rate = 100%, no exception escapes `run()`.
3. **Reason capture** — the raised exception's `type: message` appears in the slot's `reason`.
4. **Renderer** — a fallback `RunResult` renders the `[fallback]` tag + reason; an llm one does not; the summary line formats `k/n (pct%)` and includes 0-fallback builds.

## Durable doc note (`docs/HANDOFF.md`)

Add a section, roughly:

> **Refusals are an expected pipeline outcome — design for them.**
> A general-purpose model refuses or returns no draft on a fraction of builds, sometimes for reasons unrelated to intent. The harness treats this as normal: a refused (build, tier) falls back to the deterministic resolver (a valid, if less inspired, instance) and is counted toward a per-build fallback rate. A refusal is never an error and never a hole in the spread. This is why the deterministic fallback is non-negotiable (CLAUDE.md #6) — it is the shock absorber that keeps the bake whole.
>
> **Never have an agent introspect *why* a build was refused.** Asking a model to categorize a refusal reads worse than the original generation and has flagged a session. Log the rate; do not chase the reason.
>
> **When a *harmless* build refuses often, look at its item associations as data** — a word in the association cloud may point somewhere unintended. Prefer stylized/cartoon associations over accurate real-world chemistry; the more the content reads as non-real, the fewer false trips. This is a data/framing lever, tracked separately from the pipeline.

## Acceptance

- No live API needed for tests; `run()` never raises on a refusing resolver.
- Spread shows valid instances in every slot; fallback slots are visibly labeled.
- Summary block reports per-build fallback rate, including 0-fallback builds.
- HANDOFF note committed.
