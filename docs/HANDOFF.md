# HANDOFF (2026-07-19) — item-cloud editorial pass: spec + plan committed; execute the plan next

You are a fresh agent. Your job: **execute `docs/superpowers/plans/2026-07-19-item-cloud-editorial-pass.md`, starting with Task 1's user editorial checkpoint, then STOP** (rewrite this handoff when done). The design is settled and user-approved section-by-section — do not re-litigate scope, item choices, or the ammo-hook reversal. The user has NOT yet chosen an execution mode (they invoked /handoff at the choice prompt); re-offer Subagent-Driven vs Inline when you start, and note Task 1 always runs inline because it is user-interactive.

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: `5ce21a5` "docs: implementation plan for the item-cloud editorial pass". Below it: `7b6bbeb` (the approved spec), `ac7e5b8` (bake-phase handoff close-out), `abb8775` (pre30 data).
- Working tree: clean except long-standing intentional untracked files — `data/bake/combos-pilot.json` (HELD pilot selection; committing it is gated on pilot approval), `docs/CAPABILITY_CONTRACT_v0.md` (superseded; `resolver/contract.py` is the contract of record), `hello.md`, ten 2026-07-10 files under `docs/superpowers/plans|specs/`. Leave all alone; never stage wholesale.

## Clean-baseline checks

- `git branch --show-current` → `main`; `git log --oneline -1` → `5ce21a5 …`.
- `python -m pytest -q` → **340 passed**. (Becomes **348 passed** after plan Task 3.)

If any differ, STOP and report before doing anything.

## Read first (in order)

1. `docs/superpowers/plans/2026-07-19-item-cloud-editorial-pass.md` — the plan you are executing; contains all draft prose, exact test edits, and anchors.
2. `docs/superpowers/specs/2026-07-19-item-cloud-editorial-pass-design.md` — the approved design (why each item, the ammo-dryness partial reversal, blast radius).
3. `CLAUDE.md` — invariants (enums are the contract; code owns numbers; no hard LLM dependency).

Do NOT re-read the whole bake pipeline (`resolver/bake/*`) or the 2026-07-10 docs — this pass doesn't touch them. `docs/superpowers/specs/2026-07-12-association-clouds-design.md` only if a cloud-convention question comes up.

## Done and verified

- **Bake phase closed** (through `abb8775`): pre30 wave — 28/30 resolved, 168 gadgets committed in `data/bake/`, $0.181/combo measured. Quality verdict (user-reviewed): generator/prompt good enough; **the quality ceiling is the item association clouds** — that verdict is what this pass answers.
- **Editorial-pass spec** (`7b6bbeb`): 4 new items (firefighter turnout coat = flagship, wakes the dormant ON_HIT self-kit path via existing `validate.py` protective check; battery boombox + cooler of raw steaks feed starved UTILITY; coat + case of energy drinks feed starved SUPPORT) + one distinct non-fire hook line per real-ammo cloud (anti-cook-off). Approved with all mechanics locked (roles/tags/delivery/base_use/verb); only prose is open, and only at the Task 1 checkpoint.
- **Implementation plan** (`5ce21a5`): grounded against the actual test suite — it already covers `test_items.py` (61→65), `test_base_use.py` (`EXPECTED` +4, `JUDGMENT_CALLS` +steaks), `test_associations.py` (ammo range (1,2)→(2,3), batch tuples +4), `test_validate.py` (stale dormancy comment). Verified self-adjusting, no edits needed: `test_bake_select.py` (selection has a per-item coverage loop) and `test_solo.py` (all four items carry a base use).
- Blast radius verified: `contract_fingerprint` hashes enums only → pre30 scaffolds and the HELD pilot selection are unaffected by catalog/prose changes.

## Next steps

1. Re-offer the execution choice (Subagent-Driven recommended vs Inline), then run the plan.
2. **Task 1 (inline, hard gate):** write the review doc from the plan into your session scratchpad, show the full prose in-conversation, and wait for the user's red-pen. Approved/amended text is authoritative over the plan's drafts. Mechanics are not up for edit.
3. **Task 2:** six ammo hook lines (add lines → 6 red → widen pin to (2,3) → 340 passed → commit).
4. **Task 3:** four items (test pins red → three anchored insertions in `resolver/items.py` → 348 passed → commit).
5. Rewrite this handoff.

## Standing constraints & traps

- **Pilot spend HELD:** never run `python -m resolver.bake run` or `dedup` without fresh explicit user approval in your own session. **No live API calls anywhere in this pass** (per spec §Process).
- **The enums are the capability contract — never widen them**; never widen the tag taxonomy in `resolver/interactions.py` (all four items use existing tags).
- **NEVER introspect why a call was refused. Log rates only. No stop reasons, exception text, or failure classification in records or console output.** (Standing AUP rule.)
- Code owns every number; `harmless`/`category` always re-derived; engine-agnostic `resolver/`.
- `git add` only explicitly named files; commits end `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- When dispatching subagents, copy plan Global Constraints **verbatim** — paraphrases have introduced false constraints twice.
- Trap: the ammo range change is a widening, so test-first can't go red — the plan deliberately adds lines first (red against the old pin), then widens. Don't "fix" the order.
- Trap: the steaks have no `delivery=` (substance; base use supplies PLACED) and need the `JUDGMENT_CALLS` entry (`slippery` derives SLOW, base use is LURE) — both are in the plan; don't improvise around the governing-rule test.
- API key: presence check only, never print. Windows live runs need `PYTHONUTF8=1` (not relevant this pass).

## Human TODOs

- **Red-pen the Task 1 review doc** (the pass is blocked on this; it's the whole point of the checkpoint).
- Choose execution mode when re-offered.
- Pilot spend stays HELD until deliberately re-opened (post-prototype, post-top-up/Batch-API optimization — see `13019bd`-era notes in the ledger).
- Prototype direction (game loop against the 168 committed gadgets) remains the stated next phase after this pass.
