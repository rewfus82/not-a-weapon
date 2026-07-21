# HANDOFF (2026-07-20) — game-loop prototype plan WRITTEN; next: self-review it, then execution handoff

You are a fresh agent. Your job: run the writing-plans self-review on the completed implementation plan, fix findings inline, then present the execution choice to the user — then STOP and take direction. Do not start executing plan tasks without the user picking an execution mode.

**Decided and user-approved (do not re-litigate):**
- The prototype effort itself: real GAME_IDENTITY §10 vertical slice in UE 5.x blockout, C++ core + Blueprint glue, UE project in `game/`, local HTTP sidecar + generic gadget interpreter. Spec is committed and approved: `docs/superpowers/specs/2026-07-20-game-loop-prototype-design.md`.
- Craft mode: live LLM with deterministic fallback at craft time — a dev-mode convenience, NOT a change of shipping architecture (GAME_IDENTITY §6 stands). This approves per-craft API spend during the user's play sessions ONLY. No schedules, no batches, no CI. Bake/dedup spend stays HELD.
- Finish line: loop end-to-end (move, scavenge, craft via resolver, weapon visibly does its JSON, extract→banked to `extracted.jsonl` or die→lost). No bot threat; the §10 fun-gate slice is the NEXT effort.
- User preference (this session): default testing runs the sidecar with `--fallback` / no key — free and instant; live LLM only for sessions where the user specifically wants real generated weapons. The plan is already written this way (all checklists use `--fallback`; the one live craft in Task 9 is an optional user-run step).

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: `864035e` "docs: correct sidecar default port to 8000 (serve.py's actual default)". Below it: `fefbf87` (the prototype design spec), `b48c3ed` (prior handoff).
- Working tree: clean except untracked files. **`docs/superpowers/plans/2026-07-20-game-loop-prototype.md` is the deliverable and is NOT yet committed** — committing it is part of your job (offer at the handoff; prior plan docs in this repo were committed as part of the flow, but never commit without the user's go-ahead). The rest are long-standing intentional untracked files — `data/bake/combos-pilot.json` (HELD pilot; committing gated on pilot approval), `docs/CAPABILITY_CONTRACT_v0.md` (superseded; `resolver/contract.py` + `docs/CAPABILITY_CONTRACT_v1.md` are the record), `hello.md`, ten 2026-07-10 files under `docs/superpowers/plans|specs/`. Leave all alone; never stage wholesale.

## Clean-baseline checks

- `git branch --show-current` → `main`; `git log --oneline -1` → `864035e …`.
- `$env:PYTHONUTF8 = "1"; python -m pytest -q` → **348 passed** (~13s).

If any differ, STOP and report before doing anything.

## Done and verified (this session)

- **Brainstorm complete → spec committed** (`fefbf87`, port fix `864035e`): `docs/superpowers/specs/2026-07-20-game-loop-prototype-design.md`. User approved every section.
- **Implementation plan fully written** (uncommitted): `docs/superpowers/plans/2026-07-20-game-loop-prototype.md`. All 10 tasks with complete code, build commands, manual checklists, and per-task commit messages, plus an Execution notes section. Shape: Tasks 1–3 Python (fallback PLACED-chassis fix + pin test; `GET /api/contract` fingerprint endpoint; `POST /craft`), Tasks 4–10 Unreal in `game/` (project scaffold; C++ contract mirror + fingerprint constant; resolver subsystem; effect executor + gadget weapons; inventory + junk pickups; craft spot; health/death/extract/restart).
- Design-level catches already encoded in the plan (don't re-derive): `craft()` forces `source="fallback"` when the resolver fn IS the fallback (serve.py's `_resolve_once` would misreport `llm`); the C++ contract self-test registers via `FCoreDelegates::OnPostEngineInit.AddStatic`, never called directly in `StartupModule` (UENUM registration timing); Task 1 fixes fallback `_stages_for` so PLACED chassis emit ON_TRIGGER (the Task 7 placed-gadget checklist makes the fix visible in-game).
- **Nothing executed**: no code written, no `game/` directory, zero API spend this session.

## Next steps (in order)

1. **Writing-plans self-review** of the plan (inline, fix-and-move-on, no re-review):
   - Spec coverage: every spec section maps to a task (fallback fix→1, contract endpoint→2, /craft + "no craft-mode config"→3, mirror→5, ResolverClient→6, interpreter→7, pickups→8, craft interaction→9, run state→10, error handling→6+9, testing→per-task checklists + Task 10 finish line).
   - Placeholder scan: no TBD / "add appropriate…" / "similar to Task N".
   - Type consistency across tasks: `Inventory` public member (Task 8) vs users; `EquippedWeapon` protected (Task 7) vs `GetEquippedWeapon()` accessor added in Task 10; `FNAWCraftComplete` signature identical in Tasks 6/7/9; `RestartRun` (Task 4) used in Task 10; `LogNAW` everywhere. Optional minor: extend Task 3's import note to mention pytest.
2. **Execution handoff** via AskUserQuestion: plan path + two options — Subagent-Driven (recommended) vs Inline Execution — and in the SAME message flag the one deliberate spec deviation for sign-off: the plan hand-authors a minimal UE project + legacy input (`DefaultInput.ini`) instead of the spec's "first-person template base", because the template wizard is interactive and drags in binary assets. Also offer to commit the plan doc.
3. Then follow the chosen execution skill (superpowers:subagent-driven-development or superpowers:executing-plans).

## Standing constraints & traps

- **Pilot spend HELD:** never run `python -m resolver.bake run` or `dedup` without fresh explicit user approval in your own session. **No live API calls without explicit approval** (the spec's craft-mode approval covers ONLY per-craft calls during the user's own play sessions; agents never start the sidecar in live mode).
- **NEVER introspect why a call was refused. Log rates only. No stop reasons, exception text, or failure classification in records or console output.** (Standing AUP rule. In-game the only trace of a failed live call is `source: fallback`; the UE client logs HTTP status codes only — this is encoded in Task 6.)
- **The enums are the capability contract — never widen them**; never widen the tag taxonomy in `resolver/interactions.py`. Contract fingerprint hashes ONLY the four enum vocabularies.
- Code owns every number; `harmless`/`category` always re-derived; engine-agnostic `resolver/` (zero Unreal references in Python).
- `git add` only explicitly named files; commits end `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- When dispatching subagents, copy plan Global Constraints **verbatim** — paraphrases have introduced false constraints twice.
- Unreal tasks have **manual checklist steps that require the user** (editor work, PIE tests); a task is not complete until the user confirms its checklist passed.
- Trap: the HELD pilot (`data/bake/combos-pilot.json`) must only be consumed via `load_selection` on the frozen file — the catalog grew, so re-running `select_combos` with the pinned seed no longer reproduces it.
- API key: presence check only, never print. Windows runs need `PYTHONUTF8=1`.
- User preference: auto-compact stays ON; durable state lives in this file, the plan doc, and `.superpowers/sdd/progress.md` — trust those + `git log` over conversation memory after compaction.

## Read first (in order)

1. This file.
2. `CLAUDE.md` — invariants.
3. `docs/superpowers/specs/2026-07-20-game-loop-prototype-design.md` — the approved spec (the self-review checks the plan against it).
4. `docs/superpowers/plans/2026-07-20-game-loop-prototype.md` — the plan under review (large; read fully for the self-review).
5. Only if executing begins: `.superpowers/sdd/progress.md` (ledger) and the execution skill's templates.

Do NOT read the bake pipeline docs, the 2026-07-10 docs, or the item-cloud editorial plan — that work is closed.

## Human TODOs

- Pick the execution mode (subagent-driven vs inline) and sign off on the hand-authored-UE-project substitution when presented.
- Approve committing the plan doc.
- During execution: run the per-task manual checklists in the editor (Tasks 4–10); optionally the one live craft in Task 9.
- Pilot spend stays HELD until deliberately re-opened (post-prototype).
- §10 fun-gate slice (bot threat) is the next effort after this prototype.
