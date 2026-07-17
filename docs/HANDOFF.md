# HANDOFF — live-budget + parallel-rolls plan EXECUTED; next: contract-v1 pass before bake volume

For a fresh Claude Code session. **Read `CLAUDE.md` and `docs/GAME_IDENTITY.md` first.** This repo uses **Superpowers**. The SDD ledger (`.superpowers/sdd/progress.md`, git-ignored) has full task history — read it, don't `git clean` it.

---

## The active task: none assigned — recommend brainstorming the contract-v1 pass

The 2026-07-16 live-budget + parallel-rolls plan is **COMPLETE** (commits `5ab5bf1`, `8a97ccc`; suite 251 green; final review clean, one inherited minor deferred in the ledger). The 2026-07-16 evening playtest (five live batches across DUD/COMMON/UNCOMMON/EPIC/LEGENDARY, two builds) validated it — **every roll landed exactly on `TIER_BUDGET[tier]`** — and produced the contract-v1 evidence below.

**Recommended sequencing (surfaced to user, not yet decided as a plan): a small contract-v1 pass BEFORE any real bake volume.** The bake is the expensive frozen artifact; baking scaffolds against a v0 schema that's about to grow a recipient field means re-baking. The v1 pass is small (one field, a few semantic rules, budget-weight defaults); the bake *design* (schema/dedup/waves — thinking, not spending) can proceed in parallel.

## Where things stand (done, committed, all on `main`)

Everything below is reviewed-and-merged; suite baseline **251 green** (`python -m pytest -q`, no API key needed):

- **Live budget + parallel rolls** (2026-07-16, `5ab5bf1..8a97ccc`): `clamp.fill_budget(draft, tier)` (pure; exact tier budget, proportions preserved, zero-total pass-through) called ONLY from `LLMResolver.resolve`; `serve.roll` runs its n rolls through a `ThreadPoolExecutor` (slot order preserved, per-slot fallback degrade intact; 4×0.5s rolls = 0.50s wall-clock). Solo still 2.0; composer untouched. Deferred minor in ledger: `fill_budget` would sign-flip a negative-total draft (inherited class; cheapest fix `ge=0` on `Effect.amount`).

- **Junk base-use plan** (2026-07-14, `962fcdd..41f94dc`): container renames, industrial fan (tags `{wind, heavy}` — adjudicated coherence fix, see items.py comment), airhorn, catalog=61, `BaseUse` for all non-ammo items (closed 17-entry allowlist, closed both directions), substance chassis via `Build.delivery` fallback, `resolver/solo.py` (DUD floor), composer burst/armed-patch shapes (shared `fallback.substance_stages`).
- **Association clouds**: authored, user-approved, live-validated **0/72 refusals** (retry ladder sonnet×2 → opus-4-8).
- **Playground pass** (`fe0aa66..6f5d923`): grouped chassis picker (mechanisms / containers & junk), instant solo cards, payload fields `chassis`/`mechanism`/`form`/`solo`.
- **Budget-filling composer** (2026-07-15, `f8d25f0..80c691c`): every deterministic build totals exactly `TIER_BUDGET[tier]`; overlays half-share; `_TIER_SEED` deleted; solo owns `_SOLO_AMOUNT = 2.0`. **Deterministic power tuning is one knob: `TIER_BUDGET` in `clamp.py`.**

## Contract-v1 evidence (2026-07-16 evening playtest — the case for the recommended next task)

Five live batches (sledgehammer+shells+shotgun+thermite ladder DUD→EPIC; M16+t-shirt-cannon+cinder-block+gravel at LEGENDARY; nail-gun and first-aid-kit builds at EPIC), all rolls exactly on budget. The theme: **the model's imagination is now richer than the schema — meanings live in `note` strings only a human can read.**

1. **`Effect` has no recipient field, and it now corrupts code-owned derivation (invariant 4), not just visuals.** Same-build EPIC self-kits classified `WEAPON/lethal` vs `CONTROL/harmless` purely by token choice: DAMAGE-as-adrenaline-crash (self-inflicted per note) counts as lethal, SLOW+STAGGER crash doesn't. Also HEAL fired *into the enemy* on ON_HIT ("the nail doses") vs HEAL patching the shooter on ON_EXPIRE — same token, opposite recipients, note-only. Fix direction: code-validated `target: self|struck` on `Effect`; `harmless`/`category` derivation counts only struck-target lethality.
2. **Trigger semantics are undefined for a SELF chassis.** Live rolls used ON_TRIGGER for "when the staple fires" and ON_HIT for "when *you* get hit" — legal tokens composed loosely because the contract only defines them for outbound weapons.
3. **Budget weights are an accounting identity, not verified power.** Zero-amount effects ride free (SNARE d=2.5, PIERCE n=2 cost nothing); self-family amounts cost the same as damage (a heal-yourself-80 ≡ damage-them-80). Fine by design, but "same power within a tier" is currently bookkeeping — exchange rates (duration/count/self vs damage) are the `TIER_BUDGET`-family play-tuning knob, only answerable with a renderer.
4. **Name collisions are global attractors, not per-combo.** "Load-Bearing Argument" ×3 across two different builds and three tiers; in-batch dupes ("Eviction Notice", "Compound Interest", "Buy Now, Bleed Later", "Just a Big Hammer"). Bake dedup must be a global pool + a rename pass, not a per-combo uniqueness check.
5. **Intra-tier variance width is per-combination, confirming GAME_IDENTITY §6's headroom note.** Hammer+thermite has one dominant aha (two UNCOMMON rolls came out numerically *identical* after normalization); the medkit build has many. Bake should spend its per-combo N adaptively.
6. **Tier legibility emerges as "how much of the junk activates"** (DUD/COMMON: hammer only; UNCOMMON: primer spark lights thermite; EPIC: impact-as-trigger-pull + structural collapse). If low tiers ever feel samey, the lever is prompt-side (invite a botched/partial activation at COMMON), not budget code.

## Playtest findings (2026-07-16, logged — not tasks unless queued below)

- The live creative path is excellent: one build reliably yields genuinely different weapons (wall-builder / pressure-bomb / joint-cast from laser+foam×2); locked delivery form holds; effects trace to real association lines.
- **One build refused 9/9 live attempts** (extinguisher + roman candle + fan + a powder item): deterministic fallback carried it (correctly identical each roll). Ablation offered, user hasn't asked. Protocol if pursued: ablate by item swap, NEVER ask a model why (AUP — see constraints).
- **Name collisions across rolls** ("Souvenir Nail-Biter" ×2): expected (independent calls); fix belongs in the bake pipeline as code-owned name-dedup-per-combo. Bake-spec requirement, logged here.
- Model reinterprets effect tokens through flavor (FREEZE "as set-solid, not cold"; SHIELD as foam wall). Mechanically legal; renderer-phase question whether visuals follow the token or the note.
- Live LEGENDARY roll ≈ 30–60s (adaptive thinking + sequential retry ladder) — by design (LLM path is offline/bake, never runtime); the playground's n rolls now run in parallel (`8a97ccc`).

## Follow-up queue

- **Contract-v1 pass (recommended next — brainstorm/spec, small):** `target: self|struck` on `Effect` + derivation update; trigger semantics for SELF chassis; budget-weight defaults for duration/count/self-family (explicit, tunable); optional `ge=0` on `Effect.amount` (ledger minor). Driven by the evidence section above. Schema *tightening* — never widen the enum vocabulary.
- Bake pipeline (next big phase; brainstorm off `docs/RESOLVER_ECONOMICS_AND_BAKE.md`): scaffold schema, **global** name-dedup + rename pass (not per-combo), **adaptive per-combo N** (variance width differs per combination), wave strategy, cost model. Real bake volume should wait for contract v1.
- `TIER_BUDGET` value tuning: play-tuned, user-driven, not TDD.
- Riding minors live per-task in the ledger. `grey` color badge is a stub (`_COLOR_BY_ITEM` empty) — renderer-era or rip-out.
- Out of resolver scope: renderer, the Unreal game, GAME_IDENTITY mechanics.

## Standing constraints (easy to violate)

- **The enums are the capability contract — never widen them.**
- **Code owns every number**; `harmless`/`category` always re-derived in `clamp.py`. Solo stays pathetic (2.0), never inflated.
- **Never a hard LLM dependency** — deterministic path fully works keyless.
- **Engine-agnostic** — zero engine references in `resolver/`.
- **Never have an agent introspect *why* a build was refused.** Asking a model to categorize a refusal has flagged a session for an AUP violation. Log the rate; ablate by item swap; never chase the reason.
- Windows live runs: `PYTHONUTF8=1` or redirect to a UTF-8 file (em-dash mojibake).
- The harness `routing:` line is observational (what `route()` would pick) — the actual resolver is chosen by CLI flags.

## State you need

- **Branch:** `main` (only branch, no remote — do not push).
- **Tests:** `python -m pytest -q` — 251 green baseline. Keep green at every commit.
- **Commits:** conventional, per plan task, ending `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Intentionally uncommitted** (leave alone): the 2026-07-10 plan/spec files, `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`.
- API key: rotated 2026-07-14, present in env; NOT needed for the active plan.
