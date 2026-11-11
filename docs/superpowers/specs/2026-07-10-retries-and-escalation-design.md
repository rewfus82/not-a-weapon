# Design — LLM retries + Opus escalation + softer tier-max

*Date: 2026-07-10 · Scope: `resolver/llm.py`, `resolver/harness.py`, `resolver/prompts/system_prompt.txt` (+ doc mirror). No schema/clamp/contract changes.*

## Problem

A live single-shot bake refuses too often to be usable (`aerosol+candles` 58–92%). The working prototype (`../not-a-weapon[PROTOTYPE]/combine/llm.py`) never surfaced this, and a diff of the two systems shows why:

- **The prototype retries the live call up to 3 times** before falling back (`attempts=3`); the new harness tries **once**. `stop_reason: "refusal"` is a *per-call* classifier result, so independent retries turn a per-call rate *p* into ≈*pᴺ* (58% → ~20% at 3 tries). The prototype's retries were masking the raw rate the new harness measures single-shot.
- Both systems run `claude-sonnet-5` with adaptive thinking on by default (neither passes `thinking`), so **thinking is not the difference** — an earlier hypothesis, corrected against the API reference.
- The new prompt pushes a maximal "a little unhinged / top roll" LEGENDARY, vs. the prototype's neutral single-resolution ask — a plausible per-call-rate amplifier.

## Approach

Three composed levers:

1. **Retry with model escalation.** `LLMResolver` tries an ordered list of models; the first parseable draft wins; a refusal/error advances to the next. Default for `--attempts 3`: `[primary, primary, escalate]` = two Sonnet tries then an Opus-4.8 rescue. Only if *every* attempt refuses does the deterministic fallback fire.
2. **Opus rescue is client-side**, implemented as model escalation in that retry loop — **not** the beta `server-side-fallback` parameter. Rationale: that beta's compatibility with structured-output `.parse()` is undocumented; client-side escalation composes cleanly with `.parse()`, needs no beta header, and is fully unit-testable. Same outcome (Sonnet refuses → Opus rescues).
3. **Soften the tier-max prompt** — recast the LEGENDARY/EPIC max-power language ("a little unhinged", "the top roll", "Earn it") toward "inspired, discovered, surprising", keeping the DUD→LEGENDARY depth-of-reading ladder intact.

## Non-goals

- No beta `server-side-fallback-2026-06-01` / `BetaRefusalFallbackMiddleware` (client-side escalation instead — see above).
- No schema/clamp/contract/item changes.
- No refusal-reason introspection — measure the rate only.
- Not aiming for 0% — the genuine incendiary ceiling (`aerosol+candles`) will stay elevated even Opus-rescued; retries help the moderate builds most.

## Component changes

### `resolver/llm.py`

`LLMResolver.__init__(self, client, models: list[str])` — replaces the single `model: str`. `models` is the ordered attempt list (≥1 entry).

`resolve(build, tier) -> GadgetDraft`:
```
last_reason = None
for model in self.models:
    try:
        response = client.messages.parse(model=model, max_tokens=MAX_TOKENS,
                                          system=SYSTEM_PROMPT,
                                          messages=[{"role": "user", "content": render_user_message(build, tier)}],
                                          output_format=GadgetDraft)
        draft = response.parsed_output
        if draft is not None:
            return draft
        last_reason = f"no GadgetDraft (stop_reason={response.stop_reason!r})"
    except Exception as exc:
        last_reason = f"{type(exc).__name__}: {exc}"
# every attempt refused or errored
raise RuntimeError(f"resolver exhausted {len(self.models)} attempt(s); last: {last_reason}")
```
`MAX_TOKENS` unchanged (8000 — adaptive thinking still on, still needs the headroom). The raised `RuntimeError` is what the harness already catches to trigger the deterministic fallback + rate metric.

### `resolver/harness.py`

- New args: `--attempts N` (int, default 3, min 1) and `--escalate-model` (str, default `claude-opus-4-8`; the literal `none` disables escalation).
- Build the attempt list in `_build_resolver`. **`attempts` is the total call budget; escalation replaces the final attempt** (never adds beyond the budget):
  - escalation disabled (`--escalate-model none`, or escalate equals primary): `[primary] * attempts`.
  - escalation enabled and `attempts >= 2`: `[primary] * (attempts - 1) + [escalate]`.
  - `attempts == 1`: `[primary]` — no room to escalate; escalation is a no-op at a budget of 1.
  - Worked: `attempts=3, escalate=opus` → `[primary, primary, opus]`; `attempts=3, escalate=none` → `[primary, primary, primary]`; `attempts=1` → `[primary]`.
- Pass `LLMResolver(anthropic.Anthropic(), models).resolve`. The label string reports the attempt list, e.g. `live LLM (claude-sonnet-5 ×2 → claude-opus-4-8)`.
- The per-slot `try/except → deterministic fallback` and the `fallbacks:` summary are unchanged; they now fire only after the whole attempt list is exhausted, so the metric means "every attempt (Sonnet retries + Opus rescue) refused."

### `resolver/prompts/system_prompt.txt` (+ `docs/RESOLVER_PROMPT_v0.md` mirror)

Soften the two top tiers, preserving the ladder's *shape* (depth of reading, not magnitude):
- **EPIC** — keep "inventive and interconnected. Multi-stage, a reading the maker would not have guessed, effects that feed each other." (already fine; no change needed unless it reads as power-maxxing — leave as-is.)
- **LEGENDARY** — from *"inspired. It feels discovered, not assembled: the objects' properties chain into a consequence that is genuinely surprising and a little unhinged, while still tracing honestly back to what the junk actually is. This is the top roll. Earn it."* → *"inspired. It feels discovered, not assembled: the objects' properties chain into a consequence that is genuinely surprising and clever, while still tracing honestly back to what the junk actually is. This is the deepest reading of the same objects."*

Change nothing else in the file; keep the guard green (no `diver`/`jack-in`/`signature`/`the simulation`; still frames as a video game; > 500 chars).

## Testing (TDD, deterministic — fakes, no live API)

`tests/test_llm.py` (contract tests with a fake client):
1. **Success on first attempt** — fake returns a draft on call 1 → `resolve` returns it, exactly 1 call, model == first in list.
2. **Escalation** — fake returns `parsed_output=None` (refusal) on calls to `primary`, a draft on the call to `escalate` → `resolve` returns the draft; the models used, in order, are `[primary, primary, escalate]`; call count == 3.
3. **Exhaustion** — fake always returns `parsed_output=None` → `resolve` raises `RuntimeError` after exactly `len(models)` calls; the message contains the last `stop_reason`.
4. **Error attempts still advance** — fake raises on the first model, drafts on the second → returns the draft after 2 calls (exception is caught and retried, not propagated).

`tests/test_harness.py`:
5. `_build_resolver`-level (or a small helper) test that `--attempts 3 --escalate-model claude-opus-4-8` yields the model list `["<primary>", "<primary>", "claude-opus-4-8"]`, and `--escalate-model none` yields `["<primary>", "<primary>", "<primary>"]`, and `--attempts 1` yields `["<primary>"]`.
6. Existing refusal→deterministic-fallback + rate tests remain green (a resolver that always raises still degrades to a labeled fallback slot).

`tests/test_prompt.py`: unchanged, must stay green after the prompt edit.

## Validation

Re-run all three builds live: `PYTHONUTF8=1 python -m resolver.harness --repeats 3`. Compare the `fallbacks:` line to the current post-cartoonify baseline (`broom+oil 0/12 | aerosol+candles 92% | fan+duck 0%`). Expect the moderate builds to drop toward their Opus-rescued floor; `broom+oil`/`fan+duck` stay near 0. Record the outcome; refusal rate is stochastic; no hard threshold; no introspection.

## Acceptance

- `LLMResolver` takes an ordered model list, retries with escalation, raises only when all attempts fail.
- Harness `--attempts` / `--escalate-model` build the list as specified; default is two Sonnet tries + one Opus rescue.
- Prompt's LEGENDARY line softened; guard + all tests green.
- A live re-run recorded with the new rates.
