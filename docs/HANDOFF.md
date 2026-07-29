# HANDOFF (2026-07-27) — game-loop prototype PAUSED by user; Tasks 1–8 done, Task 9 review clean, checklist re-handed, results still not reported

You are a fresh agent. **The user paused this project on 2026-07-27** — do not assume they want to
resume the moment they say hello; ask. When they do resume: get the Task 9 editor-checklist
verdict from the user (the checklist was handed to them 2026-07-22 and re-handed 2026-07-27 — ask
for results before re-explaining it), close that gate, then execute Task 10, the final whole-branch
review, and superpowers:finishing-a-development-branch — then STOP. The plan
`docs/superpowers/plans/2026-07-20-game-loop-prototype.md` is mid-execution under
**superpowers:subagent-driven-development** (user-chosen mode — fresh implementer subagent per
task, task reviewer after each, fix subagents for Critical/Important, Minors deferred to the
ledger, final whole-branch review at the end). Do not re-litigate the mode or re-dispatch
completed tasks.

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: `docs: rewrite HANDOFF for project pause at Task 9 gate` (THIS file), sitting directly
  atop `c7aff76` "feat(game): craft spot - heads-down exposed crafting, failure keeps junk"
  (Task 9 implementation; build `Result: Succeeded`; review clean — user editor checklist
  still pending). The last *code* commit is `c7aff76`.
- Task commits since plan base `80d6ad3`: `bd1b583` (T1), `17ce1cf` (T2), `35cb434` (T3),
  `b3eafa3`+`1c19fa0` (T4), `8c443a5` (T5), `177f937` (T6), `1176286`+`ab2ebe0` (T7),
  `b770a3e` (T8), `9b98c4e` (docs), `c7aff76` (T9 impl).
- Working tree: `M game/Content/Maps/Blockout.umap` only (user's own editor saves during the Task 8/9 checklists —
  NOT agent-made; the user decides at the Task 9 gate whether to commit it, likely together
  with the craft-spot placement). Long-standing intentional untracked files
  (`data/bake/combos-pilot.json` = HELD pilot, `docs/CAPABILITY_CONTRACT_v0.md` superseded by
  `docs/CAPABILITY_CONTRACT_v1.md`, `hello.md`, the 2026-07-10 docs) — leave alone; never stage
  wholesale.
- Ledger: `.superpowers/sdd/progress.md` (git-ignored) — the durable task history including all
  deferred Minors. Trust it + `git log` over conversation memory.
- SDD artifacts for Task 9: `.superpowers/sdd/task-9-brief.md`, `.superpowers/sdd/task-9-report.md`,
  `.superpowers/sdd/review-9b98c4e..c7aff76.diff` (review done — kept for reference; the brief's
  Step 4 is the user's checklist).
- **Sidecar: nothing is running.** A fallback-mode sidecar was started on 2026-07-27 for the
  re-handed checklist and stopped again when the user paused (PID 39508, killed). Port 8000 is
  free. Start one only when the checklist is actually being run, and only in fallback mode:
  `python -m resolver.serve --fallback` (or the user-side
  `powershell -ExecutionPolicy Bypass -File game\run-sidecar.ps1 --fallback`). Before assuming any
  pre-existing listener's mode, check its command line —
  `(Get-CimInstance Win32_Process -Filter "ProcessId=$((Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess)").CommandLine`
  — never probe mode by POSTing a craft (a live-mode sidecar would spend).

## Clean-baseline checks

- `git branch --show-current` → `main`; `git log --oneline -2` → `docs: rewrite HANDOFF for
  project pause…` atop `c7aff76 feat(game): craft spot…`.
- `git status --porcelain` → `M game/Content/Maps/Blockout.umap` + the untracked list above only.
- `$env:PYTHONUTF8 = "1"; python -m pytest -q` → **356 passed** (re-verified 2026-07-27, 15.2s).

If any differ, STOP and report before doing anything.

## Read first (in order)

1. This file.
2. `CLAUDE.md` — invariants.
3. `.superpowers/sdd/progress.md` — ledger (Tasks 1–8 complete; Task 9's entry says "review
   clean, AWAITING user editor checklist" — that is the resume point).
4. `.superpowers/sdd/task-9-brief.md` Step 4 — the exact checklist the user has in hand.
5. Do NOT read the whole plan; pull single tasks via
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
  USER CONFIRMED full checklist. Adjudicated deviation: `#include "Engine/OverlapResult.h"` in
  `NAWEffectExecutor.cpp` (UE 5.8 transitive-include gap).
- **Task 8:** `NAWInventoryComponent`, `NAWJunkPickup`, slot bindings + HUD tick (`b770a3e`).
  USER CONFIRMED checklist 2026-07-21 (pickup, HUD, slot toggles, full-inventory refusal).
- **Task 9 implementation + review (`c7aff76`):** `NAWCraftSpot` (heads-down lock, items
  consumed only on success, SIM UNRESPONSIVE release path) + `Interact` (E) wiring in
  `NAWCharacter`. Build `Result: Succeeded`. Review: spec ✅ byte-accurate (incl. commit
  contents + trailer), quality Approved, zero Critical/Important. DefaultInput.ini already had
  the Interact mapping from Task 4 (reviewer-verified). The T8 client-local-selection Minor was
  weighed: `HasAuthority()` early-return means no stale server-side read is possible today;
  future multiplayer needs a selection-carrying `ServerTryCraft` RPC (ledger Minor). NOT
  complete — the checklist was handed to the user 2026-07-22 and re-handed 2026-07-27, but
  **no results have been reported in either session**.

## Session 2026-07-27 (pickup + pause, no code changes)

Pickup verified zero drift against the 2026-07-25 handoff (356 passed). Started a fallback-mode
sidecar and re-handed the Task 9 checklist verbatim (setup + items 1–6, with the known-good
pickup names). The user paused the project before running any of it; the sidecar was stopped.
**No commits, no file edits other than this handoff rewrite.**

## Next steps (in order)

1. Confirm with the user that they want to resume (project was paused 2026-07-27).
2. Verify the clean baseline above.
3. **Ask the user for Task 9 checklist results** — they already have the full checklist
   (brief Step 4): craft-2-items happy path (`crafted: <name> [fallback]`, items consumed,
   lock/release), 0-selected yellow refusal without lock, sidecar-stopped craft → red
   `SIM UNRESPONSIVE - junk kept` within ~5s + release + items intact, sidecar-restart craft
   succeeds without PIE restart. If they've run it, collect pass/fail per item; if not,
   start the fallback sidecar and re-hand it from the brief. Then the **mismatch drill**
   (agent-assisted, editor must be CLOSED for both builds): flip one char of
   `NAW_CONTRACT_FINGERPRINT` in `game/Source/NotAWeapon/Contract.h`, rebuild, user PIEs → red
   CONTRACT MISMATCH banner + craft refused; **revert the constant, rebuild again** before
   continuing. Optional single live craft (user-run only, their key/spend, sidecar without
   `--fallback`): message shows `[llm]`. On confirmation: mark ledger Task 9 complete; offer to
   commit `Blockout.umap` (craft-spot placement) and this HANDOFF if the user wants them kept.
4. **Task 10** (health/death/extract/restart): record BASE → `task-brief 10` → implementer
   (sonnet) → build → `review-package BASE HEAD` → reviewer (sonnet) → resolve ⚠️ → user
   checklist → ledger line.
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
  the user to close the editor before any build; never kill their editor process. This bites the
  Task 9 mismatch drill twice (flip build + revert build).
- Trap: debug/test item strings must match `resolver/items.py` catalog names exactly — a wrong
  name yields sidecar 400, which the game deliberately collapses to "sidecar down?". Verify with
  `curl -s -X POST http://127.0.0.1:8000/craft ...` (from Git Bash; PowerShell mangles the JSON
  quoting) before blaming the sidecar. Known-good names given to the user for pickups:
  `fire extinguisher`, `garden hose`, `industrial fan`, `jerrycan of gasoline`.
- Env (user-side): `run-sidecar.ps1` needs
  `powershell -ExecutionPolicy Bypass -File game\run-sidecar.ps1 --fallback`; Ctrl+C can orphan
  the python child holding port 8000 — kill via
  `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess`.
- UE 5.8 at `D:\UE_5.8` (NOT Program Files). Build:
  `& "D:\UE_5.8\Engine\Build\BatchFiles\Build.bat" NotAWeaponEditor Win64 Development -project="C:\Users\rewfu\repos\not-a-weapon\game\NotAWeapon.uproject" -waitmutex`
- An unexplained Java install prompt appeared on the user's machine mid-session (2026-07-21).
  Nothing in this project needs Java; no agent installed anything. If it recurs, help the user
  identify the source (likely UE Android tooling or an unrelated updater) — do not approve
  installs.

## Human TODOs

- **Project is paused as of 2026-07-27** — resume is the user's call.
- Task 9 editor checklist (handed 2026-07-22, re-handed 2026-07-27; review already clean — this
  is the only gate left): craft happy path, 0-selected refusal, sidecar-down `SIM UNRESPONSIVE`
  drill, sidecar-restart re-craft, fingerprint-mismatch drill (with agent doing the two builds),
  optional single live craft. **Report results to the agent.**
- Decide whether to commit `Blockout.umap` (current diff = user's own checklist saves; the
  craft-spot placement would join it).
- Task 10 checklist: damage/death/extract/restart loop.
- Pilot spend stays HELD until deliberately re-opened (post-prototype).
- §10 fun-gate slice (bot threat) is the next effort after this prototype ships.
