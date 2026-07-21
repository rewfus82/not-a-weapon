# HANDOFF (2026-07-21) — game-loop prototype EXECUTING; Tasks 1–7 done, Task 8 review clean, awaiting user checklist

You are a fresh agent. Your job: finish Task 8's review loop, then execute Tasks 9–10, the final
whole-branch review, and superpowers:finishing-a-development-branch — then STOP. The plan
`docs/superpowers/plans/2026-07-20-game-loop-prototype.md` is mid-execution under
**superpowers:subagent-driven-development** (user-chosen mode — fresh implementer subagent per
task, task reviewer after each, fix subagents for Critical/Important, Minors deferred to the
ledger, final whole-branch review at the end). Do not re-litigate the mode or re-dispatch
completed tasks.

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: `b770a3e` "feat(game): six-slot inventory, junk pickups, slot-select HUD" (Task 8
  implementation, build green, review clean — user editor checklist still pending).
- Task commits since plan base `80d6ad3`: `bd1b583` (T1), `17ce1cf` (T2), `35cb434` (T3),
  `b3eafa3`+`1c19fa0` (T4), `8c443a5` (T5), `177f937` (T6), `1176286`+`ab2ebe0` (T7),
  `b770a3e` (T8 impl).
- Working tree: clean except long-standing intentional untracked files (`data/bake/combos-pilot.json`
  = HELD pilot, `docs/CAPABILITY_CONTRACT_v0.md` superseded, `hello.md`, the 2026-07-10 docs).
  Leave alone; never stage wholesale.
- Ledger: `.superpowers/sdd/progress.md` (git-ignored) — the durable task history including all
  deferred Minors. Trust it + `git log` over conversation memory.
- SDD artifacts for Task 8: `.superpowers/sdd/task-8-brief.md`,
  `.superpowers/sdd/task-8-report.md`, `.superpowers/sdd/review-ab2ebe0..b770a3e.diff`
  (review done — kept for reference; the brief's Step 5 is the user's checklist).

## Clean-baseline checks

- `git branch --show-current` → `main`; `git log --oneline -2` → `b770a3e feat(game): six-slot
  inventory…` atop `ab2ebe0 fix(game): DebugCraftThrown…`.
- `$env:PYTHONUTF8 = "1"; python -m pytest -q` → **356 passed**.

If any differ, STOP and report before doing anything.

## Read first (in order)

1. This file.
2. `CLAUDE.md` — invariants.
3. `.superpowers/sdd/progress.md` — ledger (Tasks 1–7 entries + deferred Minors; Task 8's
   entry says "review clean, AWAITING user editor checklist" — that is the resume point).
4. Do NOT read the whole plan; pull single tasks via
   `bash "/c/Users/rewfu/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/scripts/task-brief" docs/superpowers/plans/2026-07-20-game-loop-prototype.md N`
   (companion: `.../scripts/review-package BASE HEAD`). The plan's **Global Constraints** section
   (plan lines ~13–31) is the one part to read directly — you must copy it **verbatim** into
   every dispatch.

## Done and verified

- **Tasks 1–3 (Python):** fallback PLACED-chassis fix, `GET /api/contract`, `POST /craft`.
  Suite 356 green.
- **Task 4:** UE 5.8 project scaffold in `game/`, Blockout map, PIE movement. USER CONFIRMED.
- **Task 5:** C++ contract mirror + fingerprint constant
  (`a33fabbb515c220926ed774fed2bbe945b243165392b434a34f3093d22ce31cf`). USER CONFIRMED self-test.
- **Task 6:** `NAWResolverSubsystem` — startup fingerprint probe, async `/craft`, 20s timeout,
  one-in-flight guard. USER CONFIRMED both fingerprint-OK and sidecar-unreachable paths.
- **Task 7:** gadget interpreter — health component, effect executor (all 16 effect kinds),
  weapon actor (all 14 deliveries), projectile, placed trap, target dummy, debug craft commands.
  USER CONFIRMED full checklist ("everything works": placed SLOW trap, thrown BURN+SNARE, dummy
  death, weapon tint). Mid-checklist bug found+fixed (`ab2ebe0`): brief hardcoded item
  `"jerrycan"`; catalog name is `"jerrycan of gasoline"`; sidecar 400 surfaced as "sidecar
  down?". Adjudicated deviation (reviewer-confirmed): `#include "Engine/OverlapResult.h"` added
  in `NAWEffectExecutor.cpp` — UE 5.8 only forward-declares `FOverlapResult` transitively.
- **Task 8 implementation + review:** `NAWInventoryComponent`, `NAWJunkPickup`, NAWCharacter
  slot bindings + HUD tick (`b770a3e`). Build `Result: Succeeded`, zero deviations. Task review
  clean: spec ✅ byte-accurate to the brief, quality Approved, zero Critical/Important; three
  Minors (replication debt) deferred to the ledger. NOT complete — the user's editor checklist
  has not been run.

## Next steps (in order)

1. Verify the clean baseline above.
2. **User runs the Task 8 editor checklist** (brief Step 5): sidecar up in fallback mode, get
   real catalog names (`(Invoke-RestMethod http://127.0.0.1:8000/api/catalog).items |
   Select-Object -ExpandProperty name`), place 4–6 `NAWJunkPickup` actors in Blockout and set
   each `ItemName` to an exact catalog name; PIE-verify walk-over pickup + HUD line, 1–6 slot
   toggles, and full-inventory refusal (7th pickup stays). Task is not complete until they
   confirm; then mark the ledger's Task 8 entry complete.
3. **Task 9** (craft spot), **Task 10** (health/death/extract/restart) — per task:
   record BASE → `task-brief` → implementer (sonnet for UE tasks) → build →
   `review-package BASE HEAD` → reviewer (sonnet) → resolve ⚠️ → user checklist → ledger line.
   Task 9's checklist optionally includes ONE live craft (user-run only) and exercises the
   fingerprint-mismatch path via a temporary constant edit (revert it after). Task 9's reviewer
   must also weigh the ledger's T8 Minor: slot selection is client-local — if craft resolves
   server-side for non-host clients, selection needs an RPC.
5. After Task 10: final whole-branch review on the **most capable model**
   (`scripts/review-package 80d6ad3 HEAD`), pointed at the ledger's deferred Minors, then
   superpowers:finishing-a-development-branch.

## Standing constraints & traps

- **Copy the plan's Global Constraints verbatim into every dispatch** — paraphrases have
  introduced false constraints twice.
- **Pilot spend HELD:** never run `python -m resolver.bake run` or `dedup`. **No live API calls
  without explicit approval** (craft-mode approval covers ONLY per-craft calls during the user's
  own play sessions; agents never start the sidecar in live mode). No live calls in tests, ever.
- **NEVER introspect why a call was refused. Log rates only.** The only trace of a failed live
  call is `source: fallback`.
- **Enums are the capability contract — never widen them**; no tag-taxonomy changes in
  `resolver/interactions.py`. Code owns every number; `harmless`/`category` re-derived;
  `resolver/` stays engine-agnostic.
- `git add` only explicitly named files; commits end
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Never commit `game/Binaries|Intermediate|DerivedDataCache|Saved` (gitignored; verify status
  before staging).
- API key: presence check only, never print. Windows Python runs need `PYTHONUTF8=1`.
- Trap: the HELD pilot (`data/bake/combos-pilot.json`) is only consumed via `load_selection` on
  the frozen file — re-running `select_combos` no longer reproduces it.
- **Trap (recurring): Build.bat fails while the Unreal Editor is open** (Live Coding mutex). Ask
  the user to close the editor before any build; never kill their editor process.
- Trap: debug/test item strings must match `resolver/items.py` catalog names exactly — a wrong
  name yields sidecar 400, which the game deliberately collapses to "sidecar down?". Verify with
  `curl -s -X POST http://127.0.0.1:8000/craft ...` (from Git Bash; PowerShell mangles the JSON
  quoting) before blaming the sidecar.
- Env (user-side): `run-sidecar.ps1` needs
  `powershell -ExecutionPolicy Bypass -File game\run-sidecar.ps1 --fallback`; Ctrl+C can orphan
  the python child holding port 8000 — kill via
  `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess`.
- UE 5.8 at `D:\UE_5.8` (NOT Program Files). Build:
  `& "D:\UE_5.8\Engine\Build\BatchFiles\Build.bat" NotAWeaponEditor Win64 Development -project="C:\Users\rewfu\repos\not-a-weapon\game\NotAWeapon.uproject" -waitmutex`
- `Blockout.umap` has NO dummies/pickups committed — the user chose not to save scratch
  placements; actors are re-placed ad hoc per checklist (Place Actors panel → search class name).

## Human TODOs

- Task 8 editor checklist (review already clean — this is the only gate left): place
  `NAWJunkPickup` actors with real catalog names, verify pickup/slots/HUD/full-inventory refusal.
- Task 9 checklist: craft-at-spot flow; optional single live craft (user-run only); fingerprint
  mismatch drill via temporary constant edit.
- Task 10 checklist: damage/death/extract/restart loop.
- Pilot spend stays HELD until deliberately re-opened (post-prototype).
- §10 fun-gate slice (bot threat) is the next effort after this prototype ships.
