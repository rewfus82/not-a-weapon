# HANDOFF — resolver test harness (first task)

For a fresh Claude Code session. Read `CLAUDE.md` and `docs/GAME_IDENTITY.md` first — this brief assumes those constraints and won't repeat them.

## Context in one paragraph

The design is settled (see `docs/GAME_IDENTITY.md`). We are building the **resolver** — the system that turns a diver's junk-in-slots into a resolved weapon — before any Unreal work. A prior proof-of-concept ("combine brain") validated the *pattern* (LLM resolver + deterministic fallback, code-owned balance, enums-as-contract) but was built for a different, top-down survival game; its content and vocabulary are being rebuilt for a melee-and-guns 3D FPS. The immediate goal is not the final resolver — it's a **test harness** to answer one question empirically.

## The one question this task exists to answer

**Does the resolver prompt produce a genuine dud→god quality *spread*, and do same-tier results vary in *character* (horizontal), not just wording?**

Everything about the rarity system (GAME_IDENTITY §6) depends on the answer being yes. If the model can't produce range, the mechanic doesn't exist. This harness is how we find out, and it's cheap to run.

## Early step — harden the resolver prompt for a cold model (do this first)

`docs/RESOLVER_PROMPT_v0.md` currently assumes the reader shares this project's context. It does not. The resolver system prompt is sent to a **context-free model** that gets only that prompt plus the build — no design doc, no conversation, no game knowledge. Two problems to fix before/while testing:

1. **It uses game jargon that misleads a cold model.** It literally says a "diver" has junk and refers to "the simulation" — a cold model reads "diver" as scuba and has no idea what simulation. Scrub *all* in-world proper nouns: "diver," "jack-in," "signature," "the simulation," etc. The model does not need the fiction; it needs the task.
2. **The rule for what stays:** every sentence must change how the model resolves *this weapon*. Keep fiction only as *behavioral instruction* — "read objects for their non-obvious properties," "treat the world as one where ordinary objects can produce extraordinary effects" (this permission-to-be-absurd genuinely affects output). Cut fiction that's *world-building* — extraction, economy, gradient, tank, knowledge-not-power. None of it helps resolve one weapon; it only distracts and burns tokens.
3. **Medium framing is not lore — keep it.** A live spread run (Sonnet 5) showed a general model reads context-free crafting as real-world instructions and refuses: the harmless `fan+duck` build refused 100% while the incendiary `broom+oil` refused 0% — inversely correlated with danger, so the trigger is how the text *reads*, not what the gadget does. The fix is to state plainly that this is a **stylized video game** and the results are game abilities. That frame is *medium*, not *lore*: it changes how the model resolves the build and it measurably suppresses false refusals, so it **stays**. Keep cutting the *world lore* — "diver," "jack-in," "the simulation," extraction, economy, knowledge-not-power — none of which helps resolve one build. In short: **KEEP "it's a game"; CUT the world.** See "Refusals are an expected pipeline outcome" below for how the pipeline absorbs the refusals that remain.

Rewrite the prompt to be **self-contained and jargon-free**, then use the harness's first cold-model outputs to find remaining confusion and add *task-relevant* context only — never game lore. Do not theorize the right amount of context; run it and read where the model gets confused.

## Build this

A small Python harness (engine-agnostic, no Unreal) that:

1. Loads the resolver system prompt from `docs/RESOLVER_PROMPT_v0.md` and the vocabulary from `docs/CAPABILITY_CONTRACT_v0.md`.
2. Defines **a handful of test item builds** with association clouds. The real catalog doesn't exist yet — invent ~6–10 evocative junk items with tiered associations (mop, fry oil, push broom, birthday candles, aerosol can, rubber duck, car battery, etc.) purely to exercise the resolver. Make the associations *rich* — this is half the system.
3. For a given build, calls the Anthropic API with **structured output** (Pydantic `GadgetDraft` matching the schema in the contract), the way the POC did (`client.messages.parse(...)`), passing the build + a **target tier**.
4. Runs each build **across all six tiers** (DUD→LEGENDARY) once, and **3–4× at RARE/EPIC/LEGENDARY**, so we can read both axes.
5. Dumps results in a **human-readable** format (not raw JSON) — grouped by build, then tier, showing name / logic / staged effects — so a person can eyeball the spread in one scroll.
6. Applies the **deterministic clamp** to every result (caps/floors, re-derive `harmless`/`category`) — even a stub is fine for v0 — to prove the model→code ownership split works end to end.

## Acceptance criteria

- Runs from the CLI with an API key; degrades gracefully / errors clearly with none.
- Output makes the two axes legible at a glance: **depth across tiers** and **variety within a tier**.
- The brain is pure Python, zero engine references, unit-tested where deterministic (the clamp, the schema, the build/validation — TDD these). The LLM call is contract-tested with a fake client (creativity itself isn't unit-testable).
- Model defaults to **Sonnet** (the tested floor); make the model swappable via env var so a Sonnet-best-of-4 vs. single-Fable comparison is a one-line change.
- No live-LLM assumptions leak into the design: this is an **offline generation** harness (the game will consume pre-baked results), not a runtime path.

## Hard constraints (from CLAUDE.md — restated because they're easy to violate here)

- **Tier is an input**, told to the model per call. Do not have the model self-assign tier.
- **Code owns** delivery (locked from the delivery item), color, tier budget, all magnitude clamps, `harmless`, `category`. Model owns name, logic, composition, flavor.
- **Enums are the wall.** The `GadgetDraft` schema must constrain the model to the contract's tokens. A result citing a primitive not in the contract is a bug.
- **Deterministic fallback must exist** and produce a valid (if boring) result with no API key.

## Explicitly NOT in this task

The Unreal game, the renderer, the real item catalog, the economy, the gradient, netcode, the bake pipeline, best-of-N cost optimization. This is *only* the harness that proves the prompt produces range. Resist scope creep — GAME_IDENTITY's discipline rules apply.

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

## After this task

Once the spread is confirmed (or the prompt is tuned until it is), the natural next steps are: expand to a real item catalog with association clouds, then the batch bake pipeline (best-of-N across the catalog, tier-organized instance sets), then the deterministic resolver proper. Not now — one thing at a time.

## Known open question to surface, not silently decide

`GAME_IDENTITY.md` §6 open note: whether a combination's tier *headroom* varies by combination (a tube-launcher ladder taller than a sword ladder). The harness doesn't need to solve this, but if it becomes relevant while testing, flag it rather than baking in an assumption.
EOF
