# HANDOFF — implement the reimagined catalog + behavior taxonomy + composer/router

For a fresh Claude Code session. **Read `CLAUDE.md` and `docs/GAME_IDENTITY.md` first** — this brief assumes those constraints and won't repeat them. This repo uses **Superpowers**; let it drive workflow.

## Where things stand (what's done)

The **design phase for this task is complete and committed.** Do **not** re-brainstorm or re-open the design — execute the plan below.

- The resolver test harness exists and works (prior task). The LLM path (`llm.py`, `prompt.py`), deterministic fallback, clamp, render, and a local play server (`serve.py`) are all in place and tested.
- A full design conversation reimagined the item catalog and locked several decisions. The outputs:
  - **`docs/superpowers/specs/2026-07-12-item-catalog-and-behavior-taxonomy-design.md`** — the spec. Verb-first catalog, the **three-layer behavior model** (base delivery × behavioral overlay × effect), the reconciled **24-tag taxonomy**, the **53-item catalog** (this is the authoritative item list), and the game-mechanics decisions.
  - **`docs/superpowers/plans/2026-07-12-item-catalog-and-behavior-taxonomy.md`** — the implementation plan. **This is your task list.** 9 TDD tasks, each with real test + implementation code and exact paths.
  - `docs/superpowers/specs/2026-07-11-sensible-vs-absurd-routing-design.md` — earlier routing spec. Its Pieces 1–2 (old tags/catalog) are **superseded**; its Piece 3 (coherence score) + handoff rule **stand** and are implemented by the plan.
  - `GAME_IDENTITY.md` was refined (dated 2026-07-12) with the armory / deconstruct / two-blueprint-kinds / loadout mechanics. Those are **canon, not code** — the resolver brain does not implement them; they're future game systems.

## Your task

**Execute `docs/superpowers/plans/2026-07-12-item-catalog-and-behavior-taxonomy.md` task by task**, using **`superpowers:subagent-driven-development`** (a fresh subagent per task, two-stage review between tasks). The plan is written for a cold implementer — follow it in order; each task ends green and committed.

In one sentence: replace the 8 placeholder items + the plain-hit stub with the real 53-item verb-tagged catalog, a coherence scorer, a three-layer deterministic composer, and a router — so the resolver actually *composes* weapons instead of returning a stub.

## State you need

- **Branch:** `resolver-harness` (stay on it; do not merge to `main` or push unless the user asks).
- **Tests:** `python -m pytest -q` from repo root. Currently **green** — keep it green at every commit.
- **Shell:** PowerShell primary; a Bash tool is also available. Commands in the plan use `python -m pytest ...` and run verbatim in either.
- **Commits:** conventional; end each with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. The repo's rule is "commit per task" for this workflow.

## Load-bearing constraints for THIS task (easy to violate — see the plan's Global Constraints for the full list)

- **Do NOT add `Seeking` or `Physics` to the capability contract.** They are deliberately parked as design-only. The enums are the wall (invariant #5) — never widen them.
- **The 24-tag taxonomy is exact** (listed in the plan and spec). Every item's tags must be a subset; the invariant tests enforce this.
- **Code owns every number.** The composer proposes composition; `clamp.py` still owns final magnitudes, `harmless`, and `category` — the composer must not set those.
- **Never a hard LLM dependency.** The deterministic composer must fully resolve any build with no API key (invariant #6).
- **Engine-agnostic:** zero engine references in `resolver/`.
- **The interaction tables and tier seeds are v0 and expected to churn.** Tests assert *wiring and structure*, never balance numbers. **If a transcribed item's tags make a test contradict the spec, fix the tags to match the spec — not the test.**

## The one spot that needs real care

**Task 4 (the catalog swap)** is the big, rippling task: it replaces the catalog, moves `delivery` onto the item, deletes `DELIVERY_LOCK`, and migrates the consumers that read the old schema (`prompt.py`, `serve.py`, `harness.py`) plus their tests — all in one green commit. The plan shows ~13 representative item constructions; **you must transcribe the remaining items from the spec's catalog tables** (§ "The catalog — 53 items"), assigning `roles` / `verb` / `tags` / `delivery` / `caliber` / `flags` per the spec. Four invariant tests enforce completeness (≥50 items, every delivery form carried, every tag carried, every firearm caliber matched by ammo). Take this task slowly.

## Explicitly NOT in this task

The Unreal game, the renderer, the real bake pipeline, best-of-N cost optimization, and the game-mechanics systems now in GAME_IDENTITY (armory, deconstruct spot, blueprints, loadout). This task is the resolver **brain**: catalog → coherence → composer → router. Resist scope creep — §9 discipline applies.

## Lesson from prior sessions — do not repeat

**Never have an agent introspect *why* a build was refused** by the safety classifier. Asking a model to categorize a refusal has flagged a session for an AUP violation. If you touch the LLM path, treat refusals as a normal fallback outcome, log the rate, and never chase the reason. (Fuller note preserved in git history / the routing spec.)

## Housekeeping note for the user (not an agent action)

The user's Anthropic API key was exposed earlier in a prior conversation and should be rotated in the console — independent of this task.

## Integration read 2026-07-12

Ran (no API key set, `--fallback` forces deterministic explicitly):
`python -m resolver.harness --build broom_bat --build gun_ammo --build bananarama --fallback`
Routing observed: **deterministic 27 / llm 9** (36 total slots). `gun_ammo` (C=1.0, firearm+caliber match) and `broom_bat` (C=1.0, shared `heavy` tag) route deterministic at all 6 tiers, 12/12 each. `bananarama` is C=2/3≈0.667 — just under `C_HIGH=0.67` as designed — so DUD/COMMON/UNCOMMON (3) go deterministic and RARE/EPIC/LEGENDARY×3-reps (9) go llm.

**Read well:**
- `gun_ammo`: DAMAGE-only at every tier (2→6→10→18→30→45), reliable and legible; no clamp scaling needed (well under the tier budget cap even at LEGENDARY).
- `broom_bat`: blunt+heavy+springy (bat) ∪ electrical+corrosive+heavy (car battery) → DAMAGE at DUD, +BURN at COMMON/UNCOMMON, +CHAIN/KNOCKBACK/LAUNCH at RARE+. Reads as an electrified, acid-leaking bat — a sensible "kick." Every effect traces cleanly to a tag or pair (`interactions.py` `SINGLE_TAG_EFFECTS`).
- `bananarama` deterministic drafts (DUD–UNCOMMON): BURN (corrosive+liquid pair) then +CHAIN (electrical+liquid pair) — legible and valid, though the brief's expected narrative ("stream + snare, gaining CHAIN at RARE+") doesn't match: SNARE (sticky+liquid) actually appears at RARE alongside KNOCKBACK/SLOW, not before CHAIN. Not a bug — just the brief's prose predating the actual table wiring.
- Magnitudes: all instances land at or under `TIER_BUDGET[tier] * 1.12`; the 5-effect builds (broom_bat, bananarama RARE+) get scaled down to hit the cap almost exactly (e.g., RARE 5×18=90 clamped to 5×10.752=53.76), while single-effect `gun_ammo` never approaches the cap.

**Needs table tuning:**
- `_TIER_SEED` in `fallback.py` gives every effect the same flat seed regardless of effect count, so multi-effect coherent builds get clamp-scaled down to the budget ceiling while single-effect builds (real guns — no tags at all) sit far under it. Guns read "reliable" but may read underpowered next to a same-tier improvised weapon; worth a per-effect-count seed adjustment or a floor that lets single-effect builds use more headroom.
- `m16 rifle` / `5.56 rounds` carry zero flavor tags, so `gun_ammo` has no distinguishing effect at any tier — intentional starkness for real weapons, but flag if that reads as bland once art/names land.

Full suite: `python -m pytest -q` green after the read (no code changed).
