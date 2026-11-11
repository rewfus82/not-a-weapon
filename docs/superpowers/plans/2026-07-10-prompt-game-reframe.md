# Prompt Game-Reframe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reframe the resolver system prompt as a stylized video game (and amend the HANDOFF directive to sanction it) so a general model stops reading context-free crafting as real-world instructions — cutting the false-refusal rate that made the bake 53% deterministic.

**Architecture:** Pure text/data change. Rewrite `resolver/prompts/system_prompt.txt` to open with a game frame and soften "weapon" language, preserving the trace/tier/spread mechanic and both worked examples verbatim. Mirror the change into `docs/RESOLVER_PROMPT_v0.md`. Amend `docs/HANDOFF.md`. Validate empirically with the existing harness (re-run the two problem builds + a regression read on `broom+oil`). No Python, no schema, no tests to author.

**Tech Stack:** Plain text prompt file; pytest for the existing guard; the CLI harness as the measurement instrument.

## Global Constraints

- **Frame as "video game," NEVER "simulation."** `tests/test_prompt.py::test_system_prompt_is_loaded_and_jargon_free` asserts the prompt contains none of (case-insensitive): `diver`, `jack-in`, `jack in`, `signature`, `the simulation`. Do not reintroduce any of these. The prompt must stay > 500 chars.
- **Preserve the creative mechanic verbatim in substance:** obvious reading is weak; read the non-obvious property; trace every effect to a stated property; chain across staged triggers; tier = depth of reading; the six tier definitions; both worked examples (Damp Sweep / Last Call). The reframe changes the *medium*, not the *method* — `broom+oil` already produces a real dud→god spread under these rules.
- **KEEP medium framing (it's a game); CUT world lore** (diver, extraction, economy, "the simulation"). This is the reconciliation of the HANDOFF scrub directive.
- **No item-association edits, no model swap, no code changes** in this plan.
- **Never introspect *why* a build refused** — measure the rate only.
- `docs/RESOLVER_PROMPT_v0.md` states its SYSTEM PROMPT section mirrors the runtime file; keep them identical.

---

### Task 1: Rewrite the system prompt with a game frame

**Files:**
- Modify: `resolver/prompts/system_prompt.txt` (full replacement of paragraphs 1–2 and the "Most combinations are not weapons" paragraph; everything else byte-identical)
- Modify: `docs/RESOLVER_PROMPT_v0.md` (the "## SYSTEM PROMPT" mirror, lines 13–60, to match)
- Test: `tests/test_prompt.py` (existing; must stay green — no new test)

**Interfaces:**
- Consumes: nothing new. `resolver/prompt.py` reads the file as-is.
- Produces: a reframed `SYSTEM_PROMPT` string still satisfying the jargon-free guard.

- [ ] **Step 1: Replace the opening two paragraphs of `resolver/prompts/system_prompt.txt`**

Replace the current lines 1–3 (the two opening paragraphs) with exactly:

```
You are the crafting engine for a stylized, physics-defying video game. Players jam a few virtual junk items together and you decide what absurd gadget the combination becomes: a set of game abilities, expressed only as the numbered effects in the fixed vocabulary below. The objects are game props and the results are cartoon game mechanics — none of it is real. Read the objects honestly, then let their properties collide into something the player did not quite expect.

Treat this as a cartoon game world where ordinary objects can produce extraordinary effects. Imagination is the only limit, so be willing to be absurd, as long as every effect still traces back to a real property of the objects given.
```

- [ ] **Step 2: Soften the "Most combinations are not weapons" paragraph**

Replace the current paragraph (runtime line 11) that begins "Most combinations are not weapons, and that is honest." with exactly:

```
Most combinations are not attacks, and that is honest. Junk that cannot hurt anyone becomes a control tool, a support item, a utility, or a trinket, not an offensive gadget with a damage number bolted on. Do not force damage where there is none. A thing that snares and lures is a control tool; describe it as one. Be truthful about what the effects actually are.
```

Leave every other line of `system_prompt.txt` byte-for-byte unchanged — in particular the core-rule paragraph, the composition paragraph, the trace paragraph, the coherence rule, the vocabulary list, the tier ladder, the naming/output paragraphs, and BOTH worked examples (Damp Sweep and Last Call).

- [ ] **Step 3: Run the prompt guard to verify it stays green**

Run: `python -m pytest tests/test_prompt.py -v`
Expected: PASS — `test_system_prompt_is_loaded_and_jargon_free` (no banned word introduced; length still > 500) and `test_render_user_message_includes_slots_associations_delivery_and_tier` both pass.

- [ ] **Step 4: Update the doc mirror in `docs/RESOLVER_PROMPT_v0.md`**

In the "## SYSTEM PROMPT" section, replace the first two paragraphs (currently lines 13–15) and the "Most combinations are not weapons…" paragraph (currently line 23) with the SAME replacement text used in Steps 1 and 2, so the mirror matches the runtime file exactly. Change nothing else in that section.

- [ ] **Step 5: Verify the mirror matches the runtime file**

Run this check (bash) and confirm it prints `MIRROR OK`:

```bash
python - <<'PY'
from pathlib import Path
rt = Path("resolver/prompts/system_prompt.txt").read_text(encoding="utf-8")
doc = Path("docs/RESOLVER_PROMPT_v0.md").read_text(encoding="utf-8")
for probe in [
    "You are the crafting engine for a stylized, physics-defying video game.",
    "Treat this as a cartoon game world",
    "Most combinations are not attacks, and that is honest.",
]:
    assert probe in rt, f"missing in runtime: {probe!r}"
    assert probe in doc, f"missing in doc mirror: {probe!r}"
print("MIRROR OK")
PY
```

Expected: `MIRROR OK`.

- [ ] **Step 6: Commit**

```bash
git add resolver/prompts/system_prompt.txt docs/RESOLVER_PROMPT_v0.md
git commit -m "feat: reframe resolver prompt as a stylized video game to cut false refusals"
```

---

### Task 2: Amend the HANDOFF scrub directive

**Files:**
- Modify: `docs/HANDOFF.md` (the "## Early step — harden the resolver prompt for a cold model" section)

No test — documentation. Separate task because it is an independently reviewable decision (reconciling a standing directive) and a reviewer could accept the prompt rewrite while rejecting the doc wording, or vice versa.

- [ ] **Step 1: Add the KEEP/CUT split to the early-step section**

In `docs/HANDOFF.md`, find the numbered list item #1 in the "Early step" section (the one beginning "**It uses game jargon that misleads a cold model.**"). Immediately after that section's existing paragraph #2 ("**The rule for what stays:** …"), insert this new paragraph:

```markdown
3. **Medium framing is not lore — keep it.** A live spread run (Sonnet 5) showed a general model reads context-free crafting as real-world instructions and refuses: the harmless `fan+duck` build refused 100% while the incendiary `broom+oil` refused 0% — inversely correlated with danger, so the trigger is how the text *reads*, not what the gadget does. The fix is to state plainly that this is a **stylized video game** and the results are game abilities. That frame is *medium*, not *lore*: it changes how the model resolves the build and it measurably suppresses false refusals, so it **stays**. Keep cutting the *world lore* — "diver," "jack-in," "the simulation," extraction, economy, knowledge-not-power — none of which helps resolve one build. In short: **KEEP "it's a game"; CUT the world.** See "Refusals are an expected pipeline outcome" below for how the pipeline absorbs the refusals that remain.
```

(If the surrounding list numbering makes "3." awkward, renumber so the new item is the third in that list; keep the existing two items' text unchanged.)

- [ ] **Step 2: Commit**

```bash
git add docs/HANDOFF.md
git commit -m "docs: HANDOFF — keep medium (game) framing, cut world lore; record why"
```

---

### Task 3: Validate the reframe against the live baseline

**Files:** none modified. This task runs the harness and records the result; it is the acceptance measurement, not a code change.

**Prerequisite:** an `ANTHROPIC_API_KEY` in the environment (supplied by the operator at run time; do NOT hard-code or commit it).

- [ ] **Step 1: Re-run the two problem builds live**

Run (with the key set in the environment):

```bash
PYTHONUTF8=1 python -m resolver.harness --build aerosol+candles --build fan+duck --repeats 3
```

Read the final `fallbacks:` line. Baseline was `aerosol+candles 7/12 (58%)` and `fan+duck 12/12 (100%)`. Record the new rates.

- [ ] **Step 2: Regression read on the build that already worked**

Run:

```bash
PYTHONUTF8=1 python -m resolver.harness --build broom+oil --repeats 3
```

Confirm the spread is still rich: DUD is a weak/harmless reading, high tiers are multi-stage, and the three RARE (or EPIC/LEGENDARY) instances differ in *character*, not just wording. The reframe must not flatten this.

- [ ] **Step 3: Judge and record**

Success = the two problem builds' fallback rates are meaningfully below baseline AND `broom+oil` remains a real dud→god spread. Record the outcome (the two `fallbacks:` lines and a one-line spread verdict) in the progress ledger. Refusal rate is stochastic and model-side; do not chase a hard number, and do not introspect *why* any remaining slot refused.

- [ ] **Step 4 (conditional): flag the next lever if needed**

If framing alone did not move the rate enough, note in the ledger that the next isolated change is item-association cartoonification (a separate spec) — do not begin it here.

---

## Self-Review

**Spec coverage:**
- Opening game frame added → Task 1 Step 1. ✓
- "weapon" language softened → Task 1 Steps 1–2 (opening + "not attacks" paragraph). ✓
- Mechanic + both examples preserved → Task 1 Step 2 instruction to leave all other lines byte-identical; Global Constraints. ✓
- "video game" not "simulation"; guard stays green → Global Constraints + Task 1 Step 3. ✓
- Doc mirror updated to match → Task 1 Steps 4–5. ✓
- HANDOFF KEEP-medium / CUT-lore with reasoning → Task 2. ✓
- Validation: re-run two problem builds + broom+oil regression, qualitative judgement → Task 3. ✓
- No item edits / model swap / code changes → none present. ✓

**Placeholder scan:** All replacement text is given verbatim; commands have expected output. No TBD/TODO. ✓

**Consistency:** The three probe strings in Task 1 Step 5 exactly match the replacement text in Steps 1–2 and are reused in Task 1 Step 4's mirror edit. "video game" used; "simulation" never introduced. ✓
