# HANDOFF — execute the live-budget + parallel-rolls plan (active implementation task)

For a fresh Claude Code session. **Read `CLAUDE.md` and `docs/GAME_IDENTITY.md` first**, then the spec and plan below. This repo uses **Superpowers** — brainstorm/spec/plan are DONE and user-approved; your job is execution. Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans`. Do NOT re-brainstorm the design. The SDD ledger (`.superpowers/sdd/progress.md`, git-ignored) has full task history — read it, don't `git clean` it.

---

## The active task: execute the plan

`docs/superpowers/plans/2026-07-16-live-budget-and-parallel-rolls.md` — 2 TDD tasks, exact code and commits included:

1. `clamp.fill_budget(draft, tier)` (pure; scale to exact tier budget, proportions preserved, zero-total pass-through) called ONLY from `LLMResolver.resolve` — live drafts land on budget like the deterministic path already does.
2. `serve.roll` runs its n rolls through a `ThreadPoolExecutor` (barrier-based concurrency test, no timing assertions).

Spec: `docs/superpowers/specs/2026-07-16-live-budget-and-parallel-rolls-design.md` (committed `2a0d1cf`). Plan committed `a0478ed`. **Execution NOT started.**

### Decisions already made — do NOT relitigate

- Playtest evidence (nine live LEGENDARY rolls totaling 28.6–134.4; overshooters clamped to the cap, eating booster headroom) drove this. §6: same power within a tier.
- `fill_budget` lives in `clamp.py` (owns budget math) but `clamp.apply` never calls it — solo stays 2.0, deterministic composer already fills budget by construction.
- Zero-total drafts pass through unscaled (no inventing amounts for duration-only control).
- Harness stays sequential. No sampling params on API calls (pinned by test).

## Where things stand (done, committed, all on `main`)

Everything below is reviewed-and-merged; suite baseline **244 green** (`python -m pytest -q`, no API key needed):

- **Junk base-use plan** (2026-07-14, `962fcdd..41f94dc`): container renames, industrial fan (tags `{wind, heavy}` — adjudicated coherence fix, see items.py comment), airhorn, catalog=61, `BaseUse` for all non-ammo items (closed 17-entry allowlist, closed both directions), substance chassis via `Build.delivery` fallback, `resolver/solo.py` (DUD floor), composer burst/armed-patch shapes (shared `fallback.substance_stages`).
- **Association clouds**: authored, user-approved, live-validated **0/72 refusals** (retry ladder sonnet×2 → opus-4-8).
- **Playground pass** (`fe0aa66..6f5d923`): grouped chassis picker (mechanisms / containers & junk), instant solo cards, payload fields `chassis`/`mechanism`/`form`/`solo`.
- **Budget-filling composer** (2026-07-15, `f8d25f0..80c691c`): every deterministic build totals exactly `TIER_BUDGET[tier]`; overlays half-share; `_TIER_SEED` deleted; solo owns `_SOLO_AMOUNT = 2.0`. **Deterministic power tuning is one knob: `TIER_BUDGET` in `clamp.py`.**

## Playtest findings (2026-07-16, logged — not tasks unless queued below)

- The live creative path is excellent: one build reliably yields genuinely different weapons (wall-builder / pressure-bomb / joint-cast from laser+foam×2); locked delivery form holds; effects trace to real association lines.
- **One build refused 9/9 live attempts** (extinguisher + roman candle + fan + a powder item): deterministic fallback carried it (correctly identical each roll). Ablation offered, user hasn't asked. Protocol if pursued: ablate by item swap, NEVER ask a model why (AUP — see constraints).
- **Name collisions across rolls** ("Souvenir Nail-Biter" ×2): expected (independent calls); fix belongs in the bake pipeline as code-owned name-dedup-per-combo. Bake-spec requirement, logged here.
- Model reinterprets effect tokens through flavor (FREEZE "as set-solid, not cold"; SHIELD as foam wall). Mechanically legal; renderer-phase question whether visuals follow the token or the note.
- Live LEGENDARY roll ≈ 30–60s (adaptive thinking + sequential retry ladder) — by design (LLM path is offline/bake, never runtime); Task 2 of the active plan parallelizes the playground's n rolls.

## Follow-up queue (after the plan lands)

- `TIER_BUDGET` value tuning: play-tuned, user-driven, not TDD.
- Bake pipeline (next big phase; brainstorm off `docs/RESOLVER_ECONOMICS_AND_BAKE.md`): scaffold schema, name-dedup-per-combo, wave strategy, cost model.
- Riding minors live per-task in the ledger. `grey` color badge is a stub (`_COLOR_BY_ITEM` empty) — renderer-era or rip-out.
- Out of resolver scope: renderer, the Unreal game, GAME_IDENTITY mechanics.

## Standing constraints (easy to violate)

- **The enums are the capability contract — never widen them.**
- **Code owns every number**; `harmless`/`category` always re-derived in `clamp.py`. Solo stays pathetic (2.0), never inflated.
- **Never a hard LLM dependency** — deterministic path fully works keyless.
- **Engine-agnostic** — zero engine references in `resolver/`.
- **Never have an agent introspect *why* a build was refused.** Asking a model to categorize a refusal has flagged a session for an AUP violation. Log the rate; ablate by item swap; never chase the reason.
- Windows live runs: `PYTHONUTF8=1` or redirect to a UTF-8 file (em-dash mojibake).
- The harness `routing:` line is observational (what `route()` would pick) — the actual resolver is chosen by CLI flags.

## State you need

- **Branch:** `main` (only branch, no remote — do not push).
- **Tests:** `python -m pytest -q` — 244 green baseline; the plan grows this to 251. Keep green at every commit.
- **Commits:** conventional, per plan task, ending `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Intentionally uncommitted** (leave alone): the 2026-07-10 plan/spec files, `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`.
- API key: rotated 2026-07-14, present in env; NOT needed for the active plan.
