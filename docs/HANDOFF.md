# HANDOFF (2026-07-19) — bake pipeline DONE & reviewed; pilot HELD; next phase is prototype + item clouds

You are a fresh agent. The bake-pipeline plan (`docs/superpowers/plans/2026-07-17-bake-pipeline.md`) is **complete**: Tasks 1–7 implemented and task-reviewed, a 30-combo preliminary wave ran live, the final whole-branch review passed (verdict: ready to merge; sole pre-merge fix applied), and the branch was wrapped via finishing-a-development-branch. **The 300-combo pilot was explicitly HELD by the user** — do not run `python -m resolver.bake run` or `dedup` without a fresh, explicit user approval in your own session. There is no active plan; orient, then ask the user what's next (likely: prototype or item-cloud work).

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD closes the bake phase: `042d5ff` (T7 CLI) → `13019bd` (review fix: opus pricing $5/$25) → `abb8775` (pre30 data).
- Suite: `python -m pytest -q` → **340 passed**.
- Untracked, intentional — leave alone, never stage wholesale: `data/bake/combos-pilot.json` (the HELD 300-combo pilot selection; committing it is gated on pilot approval), `docs/CAPABILITY_CONTRACT_v0.md` (superseded; v1 in `resolver/contract.py` is the contract of record), `hello.md`, the ten 2026-07-10 files under `docs/superpowers/plans|specs/`.
- `.superpowers/sdd/progress.md` — git-ignored ledger with the full task history and all review findings. Don't `git clean` it.

## What the $5.44 preliminary wave established (2026-07-18, pre30)

Committed in `data/bake/`: `combos-pre30.json`, `scaffolds-pre30.jsonl`, `names-pre30.json`, `reports/2026-07-18-pre30.md`, `reports/rename-events-pre30.json`.

- **Rates:** 28/30 resolved (one unresolved is the pinned probe expected to be hard), 2 renames, 0 suffixes. 168 gadgets total (28 × 6 drafts).
- **Cost reality vs. model:** $0.181/combo measured vs. the econ doc's ~$0.05. Anatomy: the adaptive top-up fired 28/28 (TOP_UP_WIDTH=3 is a non-discriminating placeholder → blanket 2× calls) and real output ran ~3× modeled tokens. Path back to ~$0.045/combo: skip/tune top-up + Batch API. Shelved until a bake resumes.
- **Quality verdict (user-reviewed, positive):** the depth ladder works — shallows properly pathetic, deeps genuinely chain stated item properties ("The Long Fuse", "Permanent Fixture", "Gunfire Echo", "Standing Room Only"). Weak spots: the delayed-cook-off trope is overused (~6 combos — driven by how often mismatched-caliber ammo is drawn); ON_KILL SPEED/SHIELD@SELF riders are filler; name *style* repeats ("The Quiet …", two "Long Fuse"s) which dedup can't catch; category mix is CONTROL-heavy (172 WEAPON / 132 CONTROL / 30 SUPPORT / 2 UTILITY). **Conclusion: the quality ceiling is now the item association clouds, not the generator or prompt.**

## Final review (fbb36ed..042d5ff): ready to merge

- All invariants verified: enums never widened; code owns every number (`harmless`/`category` re-derived); keyless-loud; AUP-compliant (rates only); engine-agnostic; crash-safe JSONL.
- **Fixed (`13019bd`):** `report.py` opus pricing (15, 75) → (5, 25); sonnet left at standard list (conservative vs. intro pricing, self-corrects Sept 2026).
- **Riding (schema change, unauthorized by plan — fix when a bake resumes):** unresolved records price $0 (usage present, `model=None`), and escalated records price sonnet-rung tokens at opus rates. Same root cause: `BakeRecord` lacks per-rung model attribution. Until fixed the report's $ is directional (its caveat says so).
- Nine minors triaged ride — in the ledger. Notables: `rename-events.json` overwritten per dedup run (needs per-wave `--events-out` when waves stack); report raises bare KeyError on mismatched scaffolds/selection files.

## Next steps (no active plan — user decides)

1. **Prototype first** (user's stated direction): the game loop doesn't exist yet; the 168 committed gadgets + deterministic fallback are enough content to build against. Scaffolds are perishable across contract/prompt changes (contract_fingerprint), so baking more now is speculative.
2. **Item association clouds** — the highest-leverage content work (CLAUDE.md: clouds are half the system). Needs user editorial approval. First slot: one worn protective item (activates the dormant ON_HIT self-kit path, zero code change). Would also feed the starved SUPPORT/UTILITY categories.
3. **When a bake resumes:** tune/disable top-up on the pre30 width evidence, consider Batch API, fix the per-rung attribution schema, then re-open the pilot spend gate (~$15 at current measured rates, ~$4–7 optimized).

## Standing constraints & traps

- **The enums are the capability contract — never widen them** (contract v1, `resolver/contract.py`).
- **Code owns every number**; scaffolds carry no magnitudes; rebalance = re-clamp, never re-bake.
- **Never a hard LLM dependency:** `select`/`report` keyless; `run`/`dedup` fail loud without `ANTHROPIC_API_KEY`.
- **NEVER introspect why a call was refused.** Log rates only. No stop reasons, exception text, or failure classification anywhere. (Standing AUP rule.)
- **No sampling params** on `messages.parse`. Windows live runs: `PYTHONUTF8=1`.
- Engine-agnostic: zero engine references in `resolver/`.
- `load_selection`/`load_records` take `pathlib.Path`. Ladder default: `claude-sonnet-5` ×2 → `claude-opus-4-8`.
- Renderer gates tuning: jitter width, budget band, weights, prices are placeholders — don't tune without evidence.
- When dispatching subagents, copy plan Global Constraints **verbatim** — paraphrases have introduced false constraints twice.

## Human TODOs

- Decide the next phase: prototype vs. item-cloud editorial pass (or both, clouds are blocked on user approval anyway).
- Pilot spend stays HELD until re-opened deliberately (post-prototype, post-optimization).
- Catalog expansion decision rides with the item-cloud pass.
