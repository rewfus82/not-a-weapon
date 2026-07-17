# HANDOFF — contract-v1 plan EXECUTED; next: bake pipeline brainstorm

For a fresh Claude Code session. **Read `CLAUDE.md` and `docs/GAME_IDENTITY.md` first.** This repo uses **Superpowers**. The SDD ledger (`.superpowers/sdd/progress.md`, git-ignored) has full task history — read it, don't `git clean` it.

---

## The active task: none assigned — recommend brainstorming the bake pipeline

The 2026-07-16 contract-v1 plan is **COMPLETE** (commits `327df5c..2d863b5`, five tasks, suite **279 green**, every task reviewed at its TDD gate). The schema is now the one the bake should freeze against: real bake volume was deliberately blocked on this pass, and that blocker is gone.

**Recommended next: brainstorm the bake pipeline** off `docs/RESOLVER_ECONOMICS_AND_BAKE.md` — scaffold schema, **global** name-dedup + rename pass (not per-combo), **adaptive per-combo N** (variance width differs per combination), wave strategy, cost model.

## What contract-v1 shipped (2026-07-16/17, commits `327df5c..2d863b5`, all on `main`)

Driven by the 2026-07-16 playtest evidence (see the spec `docs/superpowers/specs/2026-07-16-contract-v1-design.md` and plan `docs/superpowers/plans/2026-07-16-contract-v1.md`):

- **`Target` axis** (`STRUCK`/`SELF`) — required on every `Effect`, no default (`default_target(kind)` exists for code-authored paths); `amount` now `ge=0` (retired the ledger's sign-flip minor). Lifedrain is a composition (`DAMAGE@STRUCK + HEAL@SELF`), never a token.
- **`resolver/validate.py`** — deterministic legality **repair, never reject**, SELF chassis only: ON_IMPACT/ON_TRIGGER/ON_BLOCK → ON_USE; ON_HIT without a `protective` chassis tag → ON_USE; ON_USE/ON_EXPIRE/ON_KILL stages retarget effects to SELF. Protective rule ships dormant (riot shield locks GUARD; first worn protective item activates it free). Wired into `clamp.apply` ahead of the magnitude clamp.
- **Derivation on (kind, target)** — `harmless` = no lethal@STRUCK; category priority: no effects→DUD, lethal@STRUCK→WEAPON, control@STRUCK→CONTROL, self-family or non-LURE@SELF→SUPPORT, LURE→UTILITY, else TRINKET. Fixes the playtest's WEAPON-vs-harmless coin-flip on identical self-kits.
- **Weighted budget cost** — `effect_cost = amount*W_AMOUNT[kind] + duration*W_DURATION + radius*W_RADIUS + count*W_COUNT` (weights beside `TIER_BUDGET` in `clamp.py`; duration/radius/count no longer ride free). Floats share one scale factor; counts floor-scale only when count cost alone exceeds the target. Composer fills the weighted budget exactly; solo stays pinned 2.0.
- **Prompt + surfacing** — system prompt teaches the target axis and self-kit trigger semantics (doc mirror in `docs/RESOLVER_PROMPT_v0.md` matches); playground JSON/cards and text renderer show `KIND@TARGET`.
- **`docs/CAPABILITY_CONTRACT_v1.md`** — the new contract of record (v0 file remains as history, still intentionally uncommitted).

## Playtest findings still open (2026-07-16, logged — not tasks unless queued below)

- **One build refused 9/9 live attempts** (extinguisher + roman candle + fan + a powder item): deterministic fallback carried it. Ablation offered, user hasn't asked. Protocol if pursued: ablate by item swap, NEVER ask a model why (AUP — see constraints).
- **Name collisions are global attractors, not per-combo** ("Load-Bearing Argument" ×3 across builds/tiers). Bake dedup must be a global pool + rename pass.
- **Intra-tier variance width is per-combination** — bake should spend its per-combo N adaptively.
- **Tier legibility emerges as "how much of the junk activates"** — if low tiers feel samey, the lever is prompt-side, not budget code.
- Model reinterprets effect tokens through flavor (FREEZE as set-solid; SHIELD as foam wall) — renderer-phase question whether visuals follow the token or the note.
- Live LEGENDARY roll ≈ 30–60s (adaptive thinking + retry ladder) — by design; playground rolls run in parallel.

## Follow-up queue

- **Bake pipeline (recommended next):** brainstorm off `docs/RESOLVER_ECONOMICS_AND_BAKE.md`. Requirements already logged: global name-dedup + rename pass, adaptive per-combo N, wave strategy, cost model, scaffold schema (freeze against contract v1).
- Optional live playground smoke of the target axis (`PYTHONUTF8=1`, needs API key) — see `@STRUCK`/`@SELF` on live cards. Not a gate; the suite is the gate.
- Weight *values* (`W_DURATION` etc.) and `TIER_BUDGET` tuning: play-tuned, renderer-era, user-driven, not TDD.
- Contract-v1 open questions (in the doc): `LURE@SELF` taunt stays legal; melee params / DASH-LAUNCH overlap / slice scope carried from v0.
- `grey` color badge is a stub (`_COLOR_BY_ITEM` empty) — renderer-era or rip-out.
- Out of resolver scope: renderer, the Unreal game, GAME_IDENTITY mechanics.

## Standing constraints (easy to violate)

- **The enums are the capability contract — never widen them.** (`Target` was a validation axis, not a widening; the bar stays.)
- **Code owns every number**; `harmless`/`category` always re-derived in `clamp.py`. Solo stays pathetic (2.0), never inflated.
- **Illegal drafts are repaired deterministically, never rejected** (`resolver/validate.py`).
- **Never a hard LLM dependency** — deterministic path fully works keyless.
- **Engine-agnostic** — zero engine references in `resolver/`.
- **Never have an agent introspect *why* a build was refused.** Asking a model to categorize a refusal has flagged a session for an AUP violation. Log the rate; ablate by item swap; never chase the reason.
- Windows live runs: `PYTHONUTF8=1` or redirect to a UTF-8 file (em-dash mojibake).
- The harness `routing:` line is observational (what `route()` would pick) — the actual resolver is chosen by CLI flags.

## State you need

- **Branch:** `main` (only branch, no remote — do not push).
- **Tests:** `python -m pytest -q` — **279 green** baseline. Keep green at every commit.
- **Commits:** conventional, per plan task, ending `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Intentionally uncommitted** (leave alone): the 2026-07-10 plan/spec files, `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`.
- API key: rotated 2026-07-14, present in env; NOT needed unless doing live smokes.
