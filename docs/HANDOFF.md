# HANDOFF — resolver state after base-uses + cloud validation (2026-07-14)

For a fresh Claude Code session. **Read `CLAUDE.md` and `docs/GAME_IDENTITY.md` first.** This repo uses **Superpowers**; the SDD ledger (`.superpowers/sdd/progress.md`, git-ignored) has the full task history — read it, don't `git clean` it.

---

## Where things stand (done, committed)

- **Junk base-use plan fully executed** (2026-07-14, commits `962fcdd..41f94dc`): 15 container renames, blender → industrial fan, airhorn (catalog pinned at 61), `BaseUse` on every non-ammo item (closed 17-entry judgment allowlist, closed both directions by test), `Build.delivery` fallback through `base_use` (ammo still rejected), `resolver/solo.py` at the DUD floor, burst/armed-patch composer shapes shared via `fallback.substance_stages()`. Final whole-branch review: clean.
  - **One adjudicated deviation:** industrial fan tags are `{wind, heavy}`, not the plan's `{wind, electrical}` — the plan's C=2/3 claim was wrong (electrical+liquid edges fan–hose → C=1.0). Why-comment pinned in `items.py`; C=2/3 independently recomputed twice.
- **Association clouds: authored, user-approved, and validated live** (clouds plan complete):
  - Cloud pass for the renamed items (commit `45d80b7`): only jerrycan + motor oil needed container fixes; fan/airhorn clouds kept as shipped. Review copy regenerated at 61 items (`docs/superpowers/review/2026-07-12-association-clouds-review.md`), user-approved 2026-07-14.
  - **Live validation PASSED: 0/72 fallbacks** (6 risk-class probes × 12 calls, retry ladder sonnet×2 → opus-4-8). Zero refusals, no cartoon repairs needed, full dud→god spread + within-tier variety on every probe. Per-probe tallies in the ledger.
- **Tests: `python -m pytest -q` — 238 green.** Keep green at every commit.
- API key was rotated by the user 2026-07-14 (the old exposure is resolved).

## Follow-up queue (rough priority)

- **`serve.py` playground pass:** a "use it solo" affordance for base uses (`resolver/solo.py` is ready to consume), and `catalog_payload` can't distinguish a valid substance chassis (jerrycan) from invalid ammo — both serialize `delivery: None`; expose base-use/chassis eligibility.
- **`_TIER_SEED` tuning** (`fallback.py`): play-tuned, not TDD (guns read underpowered vs multi-effect builds; flat per-effect seed). Promote `_TIER_SEED` to a public constant while there (solo.py imports it privately, plan-mandated).
- Tagless real guns read stark (DAMAGE-only every tier) — intentional for now.
- Riding minors are logged per-task in the ledger (docstring mentions, comment placement, coverage-breadth notes).
- Out of resolver scope (later phases): bake pipeline, best-of-N cost optimization, renderer, the Unreal game, GAME_IDENTITY mechanics (armory / deconstruct / blueprints / loadout — canon, not code).

## Standing constraints (easy to violate)

- **The enums are the capability contract — never widen them.** `Seeking`/`Physics` overlays and any `PULL`/`COLLECT` effect stay design-only.
- **Code owns every number**; `harmless`/`category` are always re-derived in `clamp.py`, never trusted from the model. Solo/base-use power is pinned at the DUD floor — fixed, code-owned, never rolled.
- **Never a hard LLM dependency** — the deterministic path must fully work with no API key.
- **Engine-agnostic** — zero engine references in `resolver/`.
- **Never have an agent introspect *why* a build was refused** by the safety classifier. Asking a model to categorize a refusal has flagged a session for an AUP violation. Refusals are a normal fallback outcome — log the rate, never chase the reason. Register (item associations) fixes false refusals; retries + Opus escalation (`LLMResolver`) fix merit refusals.
- Live harness runs on Windows: `PYTHONUTF8=1` (or redirect to a UTF-8 file) — em-dashes mojibake otherwise.
- The harness `routing:` line is **observational** (what `route()` would pick); the resolver actually used is chosen by CLI flags. Don't misread `deterministic 12 / llm 0` as "no live calls happened."

## State you need

- **Branch:** `main` (only branch, no remote — do not push; adding a remote is the user's call).
- **Commits:** conventional, small; end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Intentionally uncommitted** (leave alone): the 2026-07-10 plan/spec files, `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`.
