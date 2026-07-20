# HANDOFF (2026-07-20) — item-cloud editorial pass COMPLETE; next: pick the follow-up fix, then prototype direction

You are a fresh agent. The item-cloud editorial pass (`docs/superpowers/plans/2026-07-19-item-cloud-editorial-pass.md`) is **done, reviewed, and committed** — do not re-execute any of it. Your job: orient, surface the one **user decision** below (the fallback PLACED-chassis fix), and take direction. No pre-approved work is queued; do not start the prototype or any bake work without the user asking.

## Repo & branch state

- Branch: `main` (only branch; **no remote — do not push, do not add one**).
- HEAD: `990c0d0` "docs: dormancy claims for the protective ON_HIT path are stale - the turnout coat woke it". Below it: `c6f19c9` (4 new catalog items), `678af6f` (6 ammo hook lines), `16cda28` (prior handoff).
- Working tree: clean except long-standing intentional untracked files — `data/bake/combos-pilot.json` (HELD pilot selection; committing it is gated on pilot approval), `docs/CAPABILITY_CONTRACT_v0.md` (superseded; `resolver/contract.py` + `docs/CAPABILITY_CONTRACT_v1.md` are the record), `hello.md`, ten 2026-07-10 files under `docs/superpowers/plans|specs/`. Leave all alone; never stage wholesale.

## Clean-baseline checks

- `git branch --show-current` → `main`; `git log --oneline -1` → `990c0d0 …`.
- `python -m pytest -q` → **348 passed**.

If any differ, STOP and report before doing anything.

## Done and verified (this pass)

- **Editorial pass landed** (3 commits `16cda28..990c0d0`): six ammo hook lines (one non-fire improvisation per real-ammo cloud, anti-cook-off), four new items — **firefighter turnout coat** (worn SELF+`protective`; wakes the ON_HIT self-kit path in `validate.py` with zero code change), **battery boombox** + **cooler of raw steaks** (feed starved UTILITY via pure-LURE), **case of energy drinks** (feeds SUPPORT via SPEED). Catalog 61→65. All prose user-approved as-is at the Task 1 hard gate ("auto engage", zero amendments).
- **Both task reviews clean** (zero Critical/Important, zero deferred minors from this pass).
- **Final whole-branch review (Fable): READY TO MERGE, zero Critical.** Reviewer independently re-ran the suite (348) and verified: `contract_fingerprint` hashes enums only (pre30 scaffolds + HELD pilot unaffected), self-adjusting tests (`test_solo.py`, `test_bake_select.py`) genuinely self-adjust, and category/harmless derivations are sound for all four new shapes (coat→SUPPORT, boombox/steaks→UTILITY harmless, drinks→SUPPORT).
- **Review Important #2 fixed** (`990c0d0`, text-only): stale "protective rule ships dormant" claims in the `resolver/validate.py` docstring and `docs/CAPABILITY_CONTRACT_v1.md` — the turnout coat made them false.
- **Review Important #1 deliberately NOT fixed** — it needs resolver code the plan scoped out. See the user decision below.

## USER DECISION REQUIRED — fallback PLACED-chassis incoherence (before next bake wave)

Found by the final review; the reviewer calls it a **gap in the plan**, not a defect in what was asked:

- `chassis_eligible` (`resolver/bake/select.py`) accepts any item with a base use, so the **steaks can chair the delivery slot** in a future selection or keyless runtime craft. A delivery-less chassis inherits its base-use delivery — for the steaks, **PLACED**.
- But `fallback._stages_for` treats *every* delivery-less chassis as a thrown container and emits **ON_IMPACT** — and per the contract, a PLACED gadget fires ON_TRIGGER; an ON_IMPACT-only PLACED gadget **can never fire**. All DUD/COMMON tiers route through this path.
- **Latent today**: no current selection contains the steaks. **Required before the next bake wave or any selection regeneration.**
- Fix shape (reviewer's recommendation): key delivery-less chassis stages off `base_use.delivery` — THROWN → the existing burst shape, PLACED → ON_TRIGGER — mirroring the discrimination `resolver/solo.py` already does; plus a pin test for the steaks-as-chassis case. Small, well-understood, precedented (the 2026-07-14 `b90fd84..41f94dc` follow-up was the same kind of solo/fallback stage-shape alignment).

Present this and ask: fix it now as a small user-approved follow-up (recommended — it's a bug on the deterministic path, and the deterministic path must always be fully functional), or fold it into the next bake-wave plan. Do not fix it unprompted.

## Next phase (after the decision): prototype direction

The stated next phase is the **game-loop prototype against the 168 committed gadgets** in `data/bake/` (see GAME_IDENTITY; this is a brainstorm-first effort — use superpowers:brainstorming, not a jump to code). Live validation of the four new items rides with the next bake wave, which must bake new-item combos anyway and will surface refusal rates at no extra cost — nothing to do about that now.

## Read first (in order)

1. This file.
2. `CLAUDE.md` — invariants (enums are the contract; code owns numbers; no hard LLM dependency).
3. `.superpowers/sdd/progress.md` — the ledger; the "2026-07-19-item-cloud-editorial-pass" section has the full review findings (including the deferred minor and the pilot-seed note).
4. Only if the user takes the fallback fix: `resolver/fallback.py` (`_stages_for`, `substance_stages`), `resolver/solo.py` (the discrimination to mirror), `resolver/bake/select.py` (`chassis_eligible`).

Do NOT re-read the bake pipeline docs or the 2026-07-10 docs unless the user opens bake work.

## Standing constraints & traps

- **Pilot spend HELD:** never run `python -m resolver.bake run` or `dedup` without fresh explicit user approval in your own session. **No live API calls without explicit approval.**
- **The enums are the capability contract — never widen them**; never widen the tag taxonomy in `resolver/interactions.py`.
- **NEVER introspect why a call was refused. Log rates only. No stop reasons, exception text, or failure classification in records or console output.** (Standing AUP rule.)
- Code owns every number; `harmless`/`category` always re-derived; engine-agnostic `resolver/`.
- `git add` only explicitly named files; commits end `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- When dispatching subagents, copy plan Global Constraints **verbatim** — paraphrases have introduced false constraints twice.
- Trap: the HELD pilot (`data/bake/combos-pilot.json`) must only be consumed via `load_selection` on the frozen file — the catalog grew, so re-running `select_combos` with the pinned seed no longer reproduces it.
- API key: presence check only, never print. Windows live runs need `PYTHONUTF8=1`.

## Human TODOs

- **Decide on the fallback PLACED-chassis fix** (the user-decision section above).
- Pilot spend stays HELD until deliberately re-opened (post-prototype, post-top-up/Batch-API optimization).
- Prototype direction (game loop against the 168 committed gadgets) is the next phase — brainstorm first.
