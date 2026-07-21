# HANDOFF (2026-07-21) — game-loop prototype EXECUTING; Tasks 1–4 done, resume at Task 5

You are a fresh agent. The plan `docs/superpowers/plans/2026-07-20-game-loop-prototype.md` is
mid-execution under **superpowers:subagent-driven-development** (user-chosen mode — fresh
implementer subagent per task, task reviewer after each, fix subagents for Critical/Important,
Minors deferred to the ledger, final whole-branch review at the end). Resume at **Task 5** after
verifying the baseline. Do not re-dispatch Tasks 1–4.

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: this handoff's own commit, "docs: handoff - prototype Tasks 1-4 done, resume at Task 5
  (contract mirror)", directly atop `1c19fa0` "feat(game): Blockout map + editor-normalized
  configs (Task 4 checklist passed)".
- Plan base: `80d6ad3`. Task commits since: `bd1b583` (T1), `17ce1cf` (T2), `35cb434` (T3),
  `b3eafa3` (T4 scaffold), `1c19fa0` (T4 umap + configs).
- Working tree: clean except long-standing intentional untracked files (`data/bake/combos-pilot.json`
  = HELD pilot, `docs/CAPABILITY_CONTRACT_v0.md` superseded, `hello.md`, the 2026-07-10 docs).
  Leave alone; never stage wholesale.
- Ledger: `.superpowers/sdd/progress.md` (git-ignored) — the durable task history, including
  deferred Minors for the final review. Trust it + `git log` over conversation memory.

## Clean-baseline checks

- `git branch --show-current` → `main`; `git log --oneline -2` → this handoff's commit
  ("docs: handoff - prototype Tasks 1-4 done…") atop `1c19fa0 feat(game): Blockout map…`.
- `$env:PYTHONUTF8 = "1"; python -m pytest -q` → **356 passed**.

If any differ, STOP and report before doing anything.

## Done and verified

- **Tasks 1–3 (Python):** fallback PLACED-chassis fix + pin test (suite 349); `GET /api/contract`
  fingerprint endpoint (350); `POST /craft` — `build_from_items`, `craft()` with the
  source-honesty override (`resolver_fn is fallback_resolve` → force `source: "fallback"`) (356).
- **Task 4 (UE scaffold):** hand-authored project in `game/` — module, `ANAWGameMode`,
  `ANAWCharacter` (first-person pawn, legacy input bindings), configs, `.gitignore`,
  `run-sidecar.ps1`. Build green. User ran the editor checklist 2026-07-21: `Blockout.umap`
  created at `/Game/Maps/Blockout`, editor restarts into it, PIE WASD/mouse/jump verified.
- **Toolchain (this machine):** UE 5.8 at `D:\UE_5.8` (NOT `C:\Program Files\Epic Games`).
  NetFxSDK 4.8.1 installed (was a build blocker).
  Build: `& "D:\UE_5.8\Engine\Build\BatchFiles\Build.bat" NotAWeaponEditor Win64 Development -project="C:\Users\rewfu\repos\not-a-weapon\game\NotAWeapon.uproject" -waitmutex`
  Editor: `& "D:\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Users\rewfu\repos\not-a-weapon\game\NotAWeapon.uproject"`
- **Editor config note:** the editor rewrote `DefaultInput.ini` (expanded defaults;
  `DefaultPlayerInputClass=EnhancedInput.EnhancedPlayerInput`) and `DefaultEngine.ini`
  (AndroidFileServer boilerplate). Committed as-is — bindings preserved and PIE-verified under
  the EnhancedInput classes, so legacy BindAxis/BindAction (Tasks 7–9) works.

## Next steps (in order)

1. Verify the clean baseline above.
2. **Task 5** — C++ contract mirror + fingerprint constant (mirror constant
   `a33fabbb515c220926ed774fed2bbe945b243165392b434a34f3093d22ce31cf`). Then Tasks 6–10 in order:
   ResolverClient; GadgetInterpreter + gadget weapons; inventory + junk pickups; craft spot;
   health/death/extract/restart.
3. Per task: `scripts/task-brief PLAN N` → dispatch implementer (record BASE commit first; sonnet
   for UE tasks, sonnet reviewers) → build → `scripts/review-package BASE HEAD` → reviewer →
   resolve ⚠️ items yourself → **user runs the manual editor checklist — task is not complete
   until they confirm** → ledger line.
4. After Task 10: final whole-branch review on the most capable model
   (`scripts/review-package 80d6ad3 HEAD`), pointed at the ledger's deferred Minors, then
   superpowers:finishing-a-development-branch.

Script paths (Git Bash):
`bash "/c/Users/rewfu/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/subagent-driven-development/scripts/task-brief" docs/superpowers/plans/2026-07-20-game-loop-prototype.md N`
and `.../scripts/review-package BASE HEAD`.

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
- API key: presence check only, never print. Windows runs need `PYTHONUTF8=1`.
- Trap: the HELD pilot (`data/bake/combos-pilot.json`) is only consumed via `load_selection` on
  the frozen file — re-running `select_combos` no longer reproduces it.

## Read first (in order)

1. This file.
2. `CLAUDE.md` — invariants.
3. `.superpowers/sdd/progress.md` — ledger (Task 1–4 details + deferred Minors).
4. `docs/superpowers/plans/2026-07-20-game-loop-prototype.md` — the plan (large; the Global
   Constraints section and the current task are what you need, via `scripts/task-brief`).

## Human TODOs

- Per-task editor checklists for Tasks 5–10 (each UE task ends with one; Task 9 optionally
  includes one live craft, user-run only).
- Pilot spend stays HELD until deliberately re-opened (post-prototype).
- §10 fun-gate slice (bot threat) is the next effort after this prototype.
