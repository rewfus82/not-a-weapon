# Design — Reframe the resolver prompt as a game to cut false refusals

*Date: 2026-07-10 · Scope: the resolver system prompt (framing only) + a HANDOFF directive amendment. No code, no item-data changes.*

## Problem

A live spread run (Sonnet 5, 36 calls) produced a refusal rate that makes the bake unusable:

```
fallbacks: broom+oil 0/12 | aerosol+candles 7/12 (58%) | fan+duck 12/12 (100%)
```

The rate is **inversely** correlated with real-world danger: the incendiary `broom+oil` build never refuses, while the harmless `fan+duck` build refuses every time. So the trigger is not weapon-danger — it is **how the text reads**.

Root cause: `resolver/prompts/system_prompt.txt` contains **no signal that this is a video game**. It opens *"You are an engine that decides what a jury-rigged contraption does… trying to make a weapon,"* and the objects are presented with real-world associations. Stripped of any game frame, a general-purpose model reads the task as a request for real improvised-weapon construction. The earlier "scrub all fiction" hardening (per HANDOFF) removed the *lore* correctly but also removed the *medium* frame ("this is make-believe"), which is the actual false-refusal lever.

## Non-goals

- **No item-association edits.** Cartoonifying the association clouds is the *next* isolated lever if framing alone is insufficient. Keeping it out isolates the variable so we can attribute the improvement.
- **No model swap, no best-of-N retry logic, no clamp/schema/harness changes.**
- **No refusal-reason introspection.** We measure the rate; we never ask a model (or ourselves via a model) to categorize *why* a build refused. That is a hard project rule and has flagged a session.
- Not aiming for zero refusals — reframing reduces false trips, it does not eliminate them.

## The change

### 1. System prompt framing (`resolver/prompts/system_prompt.txt`)

Three edits; the creative mechanic is untouched.

**a. Add an opening game frame.** Replace the current first paragraph
(*"You are an engine that decides what a jury-rigged contraption does. Someone
has jammed a few ordinary objects together and is trying to make a weapon or
gadget out of them…"*) with an unmistakable statement that this is a stylized,
physics-defying **video game**: the objects are virtual game items, the results
are cartoon game **abilities** expressed only as numbered effects drawn from a
fixed vocabulary, and nothing here describes anything real or actionable. One to
two sentences, placed first so it frames everything that follows. It must read
as plainly fictional and game-scoped, not as a disclaimer bolted on.

**Hard wording constraint:** `tests/test_prompt.py` asserts the prompt contains
none of these substrings (case-insensitive): `diver`, `jack-in`, `jack in`,
`signature`, `the simulation`. The frame must therefore say **"video game" —
never "simulation"** — and must not reintroduce any banned lore word. This keeps
`test_system_prompt_is_loaded_and_jargon_free` green and is consistent with the
KEEP-medium / CUT-lore split (medium = "game"; lore = "simulation"/"diver").

**b. Soften "weapon" language.** The words "weapon"/"make a weapon" recur and
push the real-world reading. Recast toward *gadget / contraption / ability /
gizmo / effect* throughout, leaning into the fact that output is already
abstract game primitives. "Most combinations are not weapons" style honesty
about non-lethal results stays — reworded to the softened vocabulary.

**c. Preserve the load-bearing mechanic verbatim in substance.** Do NOT alter
the rules that produce the spread: obvious reading is weak; read the non-obvious
property; trace every effect to a stated property of the given objects; chain
properties into consequences across staged triggers; tier = depth of reading,
not bigger numbers; the DUD→LEGENDARY ladder definitions; the two worked
examples. `broom+oil` already produces a genuine dud→god spread with real
within-tier variety under these rules — the reframe changes the *medium*, never
the *method*.

The `docs/RESOLVER_PROMPT_v0.md` "SYSTEM PROMPT" section mirrors the runtime
file (it says so at its head). Update the doc mirror to match the edited
`system_prompt.txt` so they do not drift.

### 2. HANDOFF directive amendment (`docs/HANDOFF.md`)

The "Early step — harden the resolver prompt for a cold model" section currently
says to scrub *all* in-world fiction. Amend it to split the rule:

- **KEEP — medium framing.** State that this is a stylized video game and the
  results are game abilities. This is task-relevant (it changes how the model
  resolves the build) and it measurably suppresses false refusals. It is not
  lore.
- **CUT — world lore.** "diver," "jack-in," "the simulation," extraction,
  economy, knowledge-not-power — still removed; none of it helps resolve one
  build.

Record the *why*: a live run showed a general model reads context-free
weapon-crafting as real-world instructions, and the game frame is the honest,
task-relevant signal that prevents it. Cross-reference the "Refusals are an
expected pipeline outcome" section already in the doc.

## Validation

The harness (`python -m resolver.harness`) is the measurement instrument. With a
key set:

1. Re-run `--build aerosol+candles --build fan+duck --repeats 3` live and
   compare the printed `fallbacks:` rates to the baseline (58% / 100%).
2. **Regression guard:** re-run `--build broom+oil --repeats 3` and read the
   spread — confirm it is still rich (multi-stage high tiers, distinct within-tier
   character). The reframe must not flatten the creativity that already works.
3. Judge qualitatively. Refusal rate is model-side and stochastic; success is
   "meaningfully lower on the two problem builds, with the `broom+oil` spread
   intact." No hard numeric threshold is committed.

If framing alone does not move the rate enough, the next isolated change is
association cartoonification (a separate spec), not a retreat from this one.

## Acceptance

- `system_prompt.txt` opens with an unmistakable game frame; "weapon" language
  softened; the trace/tier/spread mechanic and both worked examples preserved.
- `docs/RESOLVER_PROMPT_v0.md` SYSTEM PROMPT section matches the runtime file.
- `docs/HANDOFF.md` early-step directive split into KEEP-medium / CUT-lore with
  reasoning.
- Existing tests still pass (no code changed, but `test_prompt.py` loads the
  file — confirm it still loads and any asserted substrings still hold; update
  the test only if it asserts now-reworded text).
- A live re-run recorded for the two problem builds plus the `broom+oil`
  regression read.
