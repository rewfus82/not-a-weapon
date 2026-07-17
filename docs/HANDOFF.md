# HANDOFF (2026-07-17, evening) — bake-pipeline brainstorm still the assigned job; baseline re-verified

You are a fresh agent. Your job: **brainstorm the bake pipeline** (superpowers:brainstorming, off `docs/RESOLVER_ECONOMICS_AND_BAKE.md`), carry it through spec → plan per Superpowers, then STOP for the user before executing. This assignment is unchanged from the previous handoff — the 2026-07-17 pickup session verified the baseline (zero drift, 279 green) and did no work. The contract-v1 pass that was blocking bake volume is done and user-approved — do not re-litigate the Target axis, the repair rules, the derivation matrix, or the weighted budget; they are shipped and tested.

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: this handoff's own commit (subject "docs: handoff — bake brainstorm reconfirmed..."); the last code commit is `2d863b5`.
- Working tree: only the intentionally-uncommitted files below. **Leave them alone:**
  - `docs/CAPABILITY_CONTRACT_v0.md` (superseded contract, kept as history)
  - the ten 2026-07-10 files under `docs/superpowers/plans/` and `docs/superpowers/specs/`
  - `hello.md`
- Commits: conventional, small, per plan task, ending `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## Clean-baseline checks (run before any work)

```
git branch --show-current      # expect: main
git log --oneline -1           # expect: docs: handoff — bake brainstorm reconfirmed ...
python -m pytest -q            # expect: 279 passed
```

If any differ, STOP and report the drift — don't fix it silently.

## Read first (in order)

1. `CLAUDE.md` — repo invariants and how we work.
2. `docs/GAME_IDENTITY.md` — the design north star (§6 economy, §11 invariants).
3. `docs/RESOLVER_ECONOMICS_AND_BAKE.md` — the doc this brainstorm refines: LLM-scaffold/code-numbers split, wave strategy, cost model sketch.
4. `docs/CAPABILITY_CONTRACT_v1.md` — the contract of record the bake freezes against.
5. `.superpowers/sdd/progress.md` — git-ignored ledger, full task history (don't `git clean` it).

Do NOT read: the 2026-07-10 plan/spec files (historical refusal-era work), `docs/CAPABILITY_CONTRACT_v0.md` (superseded), the 2026-07-16 contract-v1 plan/spec (done; skim only if a contract question arises).

## Done and verified (all on `main`)

- **Baseline re-verification (2026-07-17 pickup session):** branch/HEAD/working-tree matched the prior handoff exactly; `python -m pytest -q` → **279 passed**. No code or doc changes besides this handoff rewrite.
- **Contract-v1 plan** (2026-07-16/17, commits `327df5c..2d863b5`, five TDD tasks, suite 251→279):
  - `Target` axis (`STRUCK`/`SELF`) required on every `Effect`; `amount` now `ge=0`; `default_target(kind)` for code-authored paths. Lifedrain is a composition (`DAMAGE@STRUCK + HEAL@SELF`), never a token.
  - `resolver/validate.py` — deterministic legality **repair, never reject** (SELF chassis only): ON_IMPACT/ON_TRIGGER/ON_BLOCK → ON_USE; ON_HIT without a `protective` chassis tag → ON_USE; ON_USE/ON_EXPIRE/ON_KILL stages retarget effects to SELF. Protective rule ships dormant (riot shield, the only `protective` item, locks GUARD). Wired into `clamp.apply` ahead of the magnitude clamp.
  - Derivation on (kind, target) in `clamp.py`: `harmless` = no lethal@STRUCK; category priority DUD → WEAPON → CONTROL → SUPPORT → UTILITY → TRINKET. Accepted edge: DAMAGE@SELF-only derives SUPPORT (documented, not special-cased).
  - Weighted budget: `effect_cost = amount*W_AMOUNT[kind] + duration*W_DURATION + radius*W_RADIUS + count*W_COUNT`, weights beside `TIER_BUDGET` in `clamp.py`. Floats share one scale factor; counts floor-scale only when count cost alone exceeds target. Composer fills the weighted budget exactly; solo stays pinned 2.0.
  - Prompt teaches the target axis + self-kit trigger semantics; `docs/RESOLVER_PROMPT_v0.md` mirrors it; playground and text renderer show `KIND@TARGET`; `docs/CAPABILITY_CONTRACT_v1.md` created.
- Earlier baselines (live budget + parallel rolls, budget-filling composer, base uses, association clouds 0/72 refusals, playground pass) — see the ledger; all merged and stable.

## Next steps (prioritized)

1. **Bake-pipeline brainstorm** (the assigned job). Must settle: scaffold schema (frozen against contract v1 — composition only, no magnitudes), **global** name-dedup pool + rename pass (collisions are global attractors: "Load-Bearing Argument" ×3 across different builds), **adaptive per-combo N** (variance width is per-combination), wave strategy, cost model (head-of-Zipf + lazy tail + revenue-funded waves).
2. **Catalog expansion decision — deliberately AFTER the brainstorm** (user asked "when do we add items"; this sequencing was the answer given). The cost model from step 1 prices a marginal item; size the wave-1 catalog against it, then run an item pass (clouds authored → user editorial approval → live refusal validation). First slot in any such pass: **one worn protective item** — it activates the dormant self-kit ON_HIT path with zero code change.
3. Optional, non-gating: live playground smoke of the target axis (`PYTHONUTF8=1`, needs API key) — see `@STRUCK`/`@SELF` on live cards, ideally a first-aid-kit build to watch repair act on real model output.

## Standing constraints & traps

- **The enums are the capability contract — never widen them.** (`Target` was a validation axis, not a widening; the bar stays.)
- **Code owns every number**; `harmless`/`category` always re-derived in `clamp.py`. Solo stays pathetic (2.0), never budget-filled.
- **Illegal drafts are repaired deterministically, never rejected** (`resolver/validate.py`).
- **Never a hard LLM dependency** — deterministic path fully works keyless. The LLM is bake/offline, never the runtime hot path.
- **Engine-agnostic** — zero engine references in `resolver/`.
- **Renderer gates tuning, not generation** (settled 2026-07-17): weight *values* (`W_DURATION` etc.), `TIER_BUDGET`, and token-vs-note visuals are renderer-era and play-tuned — not TDD, not now. Bake volume is safe regardless because scaffolds carry no magnitudes; rebalance = re-clamp, never re-bake. The renderer need not be Unreal — anything executing the contract unlocks tuning.
- **Never have an agent introspect *why* a build was refused.** Asking a model to categorize a refusal has flagged a session for an AUP violation. Log rates; ablate by item swap; never chase the reason.
- Windows live runs: `PYTHONUTF8=1` or redirect to a UTF-8 file (em-dash mojibake).
- The harness `routing:` line is observational (what `route()` would pick) — the actual resolver is chosen by CLI flags.
- Contract-v1 open questions ride in `docs/CAPABILITY_CONTRACT_v1.md` §"v1 open questions" — don't resolve them opportunistically.

## Human TODOs

- Decide when to run the optional live target-axis smoke (needs the API key; rotated 2026-07-14, present in env).
- The 9/9-refused build (extinguisher + roman candle + fan + a powder item) still rides on deterministic fallback; ablation-by-item-swap remains offered, not requested. User's call whether to pursue.
- Catalog expansion is a user decision once the bake cost model exists (step 2 above); item clouds need user editorial approval before validation.
