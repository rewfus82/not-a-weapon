# CLAUDE.md — This Is Not A Weapon (`not-a-weapon`)

Persistent constraints for this repo. Read `docs/GAME_IDENTITY.md` for the full design and the *why* behind every decision — this file is only the load-bearing rules that must not be broken, plus how to work in this repo.

## What this is

**This Is Not A Weapon** — a solo-scale, Unreal, **extraction game** with a Matrix jack-in fiction: dive into a simulation, scavenge junk, craft absurd weapons from it while exposed, extract knowledge or die. The title is the thesis (Magritte: the thing isn't the thing — nothing in the sim is real, including the weapons). The signature system (junk → weapon) is powered by a resolver "brain" (engine-agnostic Python, LLM + deterministic fallback). See `docs/GAME_IDENTITY.md`.

Current focus: the **resolver** (weapon generation) — prompt, capability contract, and a test harness. Not the Unreal game yet. See `docs/HANDOFF.md` for the active task.

## Non-negotiable invariants

These come from GAME_IDENTITY §11 and the resolver design. Do not violate them, even if a simpler implementation tempts you. If a task seems to require breaking one, stop and flag it.

1. **Only knowledge and currency persist across runs — never power.** No persistent materials, no carried pre-built weapons, no bought power. Blueprints (knowledge) and currency (data) are the only things that survive a run.
2. **Acquisition is random; combat is deterministic.** The rarity roll varies *which pre-baked instance you draw*. Once extracted, an instance is frozen and identical for everyone. A frozen weapon must never behave differently per player.
3. **The safest crafting is never the best crafting.** Danger and reward point the same way (roll quality is gated by raid risk).
4. **Code owns balance; the model owns creativity.** The resolver LLM proposes composition (which primitives, sequence, interpretation). Code owns and clamps everything touching fairness or feasibility: delivery form, tier/budget, magnitude caps/floors, `harmless`, `category`, the ~10–15% over-budget cap. `harmless` and `category` are always re-derived, never trusted from the model.
5. **The enums are the capability contract.** The model may only emit tokens the renderer can execute AND present (`docs/CAPABILITY_CONTRACT_v0.md`). Never widen the vocabulary to accommodate the model.
6. **Never a hard LLM dependency.** The deterministic fallback + clamp must keep the system fully functional with no API key. The live LLM is for frontier/offline generation, never the runtime hot path.

## Resolver specifics

- **Tier is an input to generation, not an output.** The model composes *toward* a told target tier; this is how best-of-N produces a real dud→god spread (models won't volunteer duds). Code still owns the budget the tier implies.
- **The item association clouds are half the system.** The model can only be as clever as the associations fed to it. Thin item data → bland weapons regardless of prompt quality.
- Structured output enforces the schema; the prompt spends its words on creativity, not JSON.
- **The model authors composition; code authors every number.** At real scale the LLM emits a few creative *composition scaffolds* (primitives, staged sequence, relative weights, flavor — no magnitudes) per combo; code derives the tier ladder, magnitudes, and intra-tier variance from primitive tables, re-derivably (rebalance = deterministic re-clamp, never a re-bake). Bake = head-of-Zipf + lazy tail + revenue-funded waves. See `docs/RESOLVER_ECONOMICS_AND_BAKE.md`.

## How we work here

- This repo uses **Superpowers**. Let it drive workflow: brainstorm → spec → plan → TDD → review. Do not stand up a competing orchestration layer (subagents/hooks) that duplicates it. This file and the `docs/` own the *domain rules*; Superpowers owns the *process*.
- **TDD applies to the brain** (pure Python, deterministic — unit-test it, red-green-refactor). It does **not** apply to game *feel* — "is the weapon fun to fire / is melee punchy" has no failing test and is play-tuned, per GAME_IDENTITY §9. Don't try to test-drive feel.
- Keep the resolver brain **engine-agnostic** — zero Unreal/engine references in the Python. It's a service the game consumes over a boundary.
- Small commits. Evidence over claims — verify it runs before declaring done.

## Pointers

- `docs/GAME_IDENTITY.md` — the full design + reasoning (the north star).
- `docs/CAPABILITY_CONTRACT_v0.md` — the enum vocabulary (delivery/effect/trigger) + schema.
- `docs/RESOLVER_PROMPT_v0.md` — the resolver system prompt + user template.
- `docs/RESOLVER_ECONOMICS_AND_BAKE.md` — bake cost model, the LLM-scaffold/code-numbers split, wave strategy, balance at scale (refines GAME_IDENTITY §6).
- `docs/HANDOFF.md` — the active first task.
