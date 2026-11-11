# Resolver Test Harness — Design (v0)

*Date: 2026-07-10. Repo: `not-a-weapon`. Precedes: the implementation plan (via superpowers:writing-plans).*

Read `CLAUDE.md`, `docs/GAME_IDENTITY.md`, `docs/CAPABILITY_CONTRACT_v0.md`, and `docs/HANDOFF.md` first — this spec assumes those constraints and does not repeat them.

## 1. Goal (the one question this exists to answer)

Build a small, engine-agnostic Python harness that answers, empirically:

> **Does the resolver prompt produce a genuine dud→god quality *spread*, and do same-tier results vary in *character* (horizontal), not just wording?**

Everything about the rarity system (GAME_IDENTITY §6) depends on the answer being yes. The harness is how we find out, and it is cheap to run. It is **not** the final resolver — it is the instrument that proves (or disproves) that the prompt produces range.

## 2. Non-goals (explicitly out of scope)

The Unreal game, the renderer, the real item catalog, the economy, the gradient, netcode, the bake pipeline, best-of-N cost optimization, live-LLM runtime paths. This is *only* the harness. Resist scope creep (GAME_IDENTITY §11 discipline).

## 3. Constraints carried in from CLAUDE.md / HANDOFF (restated because they are easy to violate here)

1. **Tier is an input**, told to the model per call. The model never self-assigns tier.
2. **Code owns** delivery (locked from the delivery item), color, tier budget, all magnitude clamps, `harmless`, `category`. Model owns `name`, `logic`, composition, flavor.
3. **The enums are the wall.** The model may only emit contract tokens; structured output enforces this. A result citing a primitive not in the contract is a bug.
4. **A deterministic fallback must exist** and produce a valid (if boring) result with no API key.
5. **Never a hard LLM dependency**; this is an *offline generation* harness, not a runtime hot path.
6. Brain stays **engine-agnostic** — zero Unreal/engine references in the Python.

## 4. Architecture — module layout

An installable-shape package `resolver/` plus a CLI. Each module has one clear purpose and a well-defined interface.

```
resolver/
  contract.py    # enums (Delivery, EffectKind, Trigger, Category, Tier) + Pydantic models
  items.py       # ~8 invented junk items w/ tiered association clouds; Build assembly; delivery-lock map
  prompt.py      # loads hardened system prompt from text file; renders the user-message template
  llm.py         # LLM resolver: client.messages.parse(output_format=GadgetDraft); injectable client
  fallback.py    # deterministic resolver: valid boring GadgetDraft from build + tier, no API
  clamp.py       # re-derive harmless + category; enforce per-tier magnitude budget (+~12% cap, DUD floor)
  render.py      # human-readable output, grouped build -> tier
  harness.py     # CLI entry: assemble builds, run tiers + repeats, apply clamp, print
  prompts/
    system_prompt.txt   # the hardened, jargon-free prompt (runtime source of truth; data, not code)
tests/
  test_clamp.py         # budget/caps/floors + harmless/category re-derivation (TDD)
  test_contract.py      # schema rejects non-contract tokens; valid drafts round-trip
  test_items.py         # build assembly + delivery-lock validation
  test_llm_contract.py  # LLM resolver against a FAKE client returning canned GadgetDrafts
```

**Prompt storage decision:** the hardened prompt is the plain-text file `resolver/prompts/system_prompt.txt` (runtime source of truth, easy to iterate between test runs). `docs/RESOLVER_PROMPT_v0.md` is updated to hold the same hardened text as the design reference. The two are kept in sync by hand; the code never parses the markdown doc (avoids fragile heading-based extraction).

## 5. The contract & schema (`contract.py`)

Enums mirror `docs/CAPABILITY_CONTRACT_v0.md` exactly and are the single source of truth in code:

- `Delivery`: `HITSCAN, PROJECTILE, LOBBED, BEAM, THROWN, SPRAY, PLACED, SWING, THRUST, SLAM, WHIP, GUARD, SELF, DASH`
- `EffectKind`: `DAMAGE, BURN, EXPLODE, PIERCE, CHAIN, KNOCKBACK, LAUNCH, STAGGER, SNARE, SLOW, FREEZE, HEAL, SHIELD, SPEED, SUMMON, LURE`
- `Trigger`: `ON_USE, ON_HIT, ON_IMPACT, ON_TRIGGER, ON_EXPIRE, ON_KILL, ON_BLOCK`
- `Category`: `WEAPON, CONTROL, SUPPORT, MOBILITY, UTILITY, TRINKET, DUD`
- `Tier`: `DUD, COMMON, UNCOMMON, RARE, EPIC, LEGENDARY`

Two Pydantic models split ownership at the schema boundary — this is how "the model may only emit contract tokens" is *enforced*, not just requested:

```
Effect:        kind: EffectKind, amount: float, duration: float = 0,
               radius: float = 0, count: int = 0, note: str = ""
Stage:         trigger: Trigger, effects: list[Effect], note: str = ""

GadgetDraft:   name: str, description: str, logic: str, stages: list[Stage]   # MODEL-FACING
```

`GadgetDraft` contains **only** model-owned fields. The model literally cannot emit `delivery`, `tier`, `category`, `harmless`, `color`, or `params` — they are not in its schema. The enums inside `Stage`/`Effect` constrain the model to the contract vocabulary via structured output.

The full resolved artifact is assembled by code:

```
ResolvedGadget: draft: GadgetDraft
                delivery: Delivery      # locked from the delivery item
                tier: Tier              # the input tier (code-owned budget)
                category: Category      # DERIVED by clamp, never trusted
                harmless: bool          # DERIVED by clamp, never trusted
                color: str              # set by code from delivery item
                params: dict[str, float]# per-delivery-family defaults (stub)
```

## 6. Ownership split (data flow)

```
Build + target Tier
   -> prompt.render_user_message(build, tier)          # tells the model the LOCKED delivery form + target tier
   -> llm.resolve(...) OR fallback.resolve(...)         # -> GadgetDraft (model-owned fields only)
   -> clamp.apply(draft, build, tier)                   # re-derive harmless + category; enforce tier budget
   -> ResolvedGadget                                    # code fills delivery/color/tier/params
   -> render                                            # grouped build -> tier
```

Model proposes; code disposes on anything touching fairness or feasibility.

## 7. The clamp (`clamp.py`) — real enough to TDD

Deterministic, pure, unit-tested (red-green-refactor). Given a `GadgetDraft` + `Build` + `Tier`:

1. **Tier budget.** Each `Tier` maps to a numeric total-magnitude budget, increasing DUD → LEGENDARY (exact numbers are v0 placeholders, owned by code, tuned later).
2. **Over-budget cap.** Sum effect magnitudes; if the total exceeds `budget * 1.12` (the ~10–15% over-budget cap from GAME_IDENTITY §6), scale all magnitudes down proportionally to land at the cap.
3. **DUD floor.** Enforce a minimum so a DUD is "slightly pathetic but not broken," never literally nothing.
4. **Re-derive `harmless`.** True iff every effect is in a non-lethal family (control/self/`LURE`); any damage-family effect makes it false. Never trusted from the model.
5. **Re-derive `category`.** From the actual effects: lethal → `WEAPON`; non-lethal disruptive → `CONTROL`; self/ally buffs → `SUPPORT`; movement → `MOBILITY`; `LURE`/non-combat → `UTILITY`; trivial → `TRINKET`; the low tail → `DUD`. Never trusted from the model.

This proves the model→code ownership split end to end even though the budget numbers are provisional.

## 8. Item catalog (`items.py`) — ~8 invented items, rich clouds

The association clouds are half the system (GAME_IDENTITY §6). Each item carries tiered associations (obvious → non-obvious → chainable-consequence) so the model has depth to read. Starter set (final wording during implementation):

- **push broom** — long swingable handle; bristles soak/hold liquid; sweeps wide across the floor
- **spilled fry oil** — flammable; slippery underfoot; coats and clings
- **birthday candles** — many tiny flames; drips hot wax; the trick-relight gag
- **aerosol can** — pressurized propellant; flammable spray; bursts under heat
- **car battery** — acid; stored charge that arcs; dead-weight heavy
- **rubber duck** — buoyant; squeaks/makes noise; harmless-looking decoy
- **box fan** — pushes air; spinning blades; shoves light things around
- **mop** — strands tangle and hold liquid; long reach (mirrors the prompt's hero example for cross-checking against the doc's DUD/LEGENDARY samples)

A **delivery-lock map** fixes the `Delivery` enum from the delivery-slot item (e.g. broom/mop → `SWING`, aerosol → `SPRAY`, battery → `THROWN` or `PLACED`, box fan → a shove-style delivery). A `Build` = items assigned to `delivery` / `damage` / `utility` / `modifier` slots (matching the prompt's user-message template).

## 9. Default run

**Three builds** (melee / ranged / not-a-weapon — chosen so the run exercises three delivery families *and* the harmless/category derivation path):

1. **broom + fry oil** — `SWING` melee; the prompt's hero example; sanity-checks against the doc's DUD/LEGENDARY samples.
2. **aerosol + candles** — `SPRAY`/ranged; flammable interaction.
3. **rubber duck + box fan** — control/utility; forces the "this is not a `WEAPON`" path (`CONTROL`/`UTILITY`/`harmless`).

Each build runs **all six tiers once**, plus **3× at RARE/EPIC/LEGENDARY** (≈15 calls/build, ≈45 total). CLI flags override which builds / tiers / repeats. `RESOLVER_MODEL` env var swaps the model; default **`claude-sonnet-5`** (the current Sonnet, the HANDOFF's "tested floor"), making a Sonnet-best-of-N vs. single-Fable comparison a one-line change.

## 10. Prompt hardening (`prompts/system_prompt.txt`) — do this first

Rewrite the resolver system prompt to be **self-contained and jargon-free for a cold, context-free model**:

- **Scrub all in-world proper nouns** that mislead a cold model: "diver," "jack-in," "signature," "the simulation," etc. A cold model reads "diver" as scuba and has no idea what "simulation" means.
- **Keep fiction only as behavioral instruction** — "read objects for their non-obvious properties," "treat the world as one where ordinary objects can produce extraordinary effects" (permission-to-be-absurd genuinely changes output). **Cut world-building** — extraction, economy, gradient, tank, knowledge-not-power. None of it helps resolve one weapon.
- Rule: every sentence must change how the model resolves *this weapon*.
- Do **not** theorize the right amount of context — run the harness's first cold-model outputs, read where the model gets confused, and add only *task-relevant* context (never game lore).

Keep the few-shot examples (the broom DUD vs. LEGENDARY pair) — they are load-bearing for the spread and the blandness check.

## 11. LLM resolver (`llm.py`)

- Uses `client.messages.parse(model=..., output_format=GadgetDraft, ...)` (Anthropic SDK structured-output path; Pydantic model enforces the schema).
- The Anthropic client is **injected**, so a fake client returning canned `GadgetDraft`s can contract-test the wiring without spending tokens.
- Model from `RESOLVER_MODEL` (default `claude-sonnet-5`). No sampling params set (current Sonnet rejects non-default `temperature`/`top_p`/`top_k`; adaptive thinking is on by default).
- Sends the hardened system prompt + the rendered user message (build slots with association clouds + LOCKED delivery form + TARGET tier).

## 12. Fallback resolver (`fallback.py`)

Pure Python, no API. Produces a valid (deliberately boring) `GadgetDraft` from the build + tier — e.g. a single obvious-reading effect scaled to the tier — so the whole pipeline (assemble → resolve → clamp → render) runs and is testable with **no API key**. Proves "never a hard LLM dependency."

## 13. CLI (`harness.py`)

- Runs from the command line. With a key: live Sonnet calls. Without a key: uses the fallback and says so clearly (degrades gracefully; errors clearly on genuine misconfiguration, not on "no key").
- Flags: which build(s), which tiers, repeat count, model override (also via env).
- Output via `render.py`: grouped by **build**, then **tier**, showing `name` / `logic` / staged effects in a human-readable form (not raw JSON) so a person can eyeball both axes in one scroll — **depth across tiers** and **variety within a tier**.

## 14. Testing strategy

TDD the deterministic brain (GAME_IDENTITY §9 / CLAUDE.md — feel is not test-driven, but this is pure logic):

- `test_clamp.py` — budget enforcement, over-budget cap, DUD floor, `harmless` re-derivation, `category` re-derivation. **Red-green-refactor.**
- `test_contract.py` — schema rejects tokens outside the enums; valid drafts round-trip; `GadgetDraft` exposes only model-owned fields.
- `test_items.py` — build assembly, delivery-lock correctness, slot validation.
- `test_llm_contract.py` — the LLM resolver against a **fake client**; asserts the call is wired correctly and the returned draft flows through clamp. Creativity itself is not unit-tested.

## 15. Acceptance criteria

- Runs from the CLI with an API key; degrades gracefully / errors clearly with none.
- Output makes the two axes legible at a glance: **depth across tiers** and **variety within a tier**.
- Brain is pure Python, zero engine references; deterministic pieces are unit-tested (clamp, schema, build/validation); the LLM call is contract-tested with a fake client.
- Model defaults to Sonnet, swappable via env var.
- No live-LLM assumptions leak into the design — offline generation harness, not a runtime path.
- The enums are the wall: a result citing a primitive not in the contract cannot occur (schema-enforced) and is treated as a bug if it does.

## 16. Open questions to surface, not silently decide

- **Tier headroom per combination** (GAME_IDENTITY §6 note): whether a combination's tier ceiling varies by combination (a tube-launcher ladder taller than a sword ladder). The harness does not solve this; if it becomes relevant while testing, **flag it** rather than baking in an assumption.
- **Tier budget numbers** are v0 placeholders owned by code; they will churn once the renderer is real. The harness's job is to prove *range exists*, not to finalize balance.
- **Delivery-lock choices** for a few items (battery → `THROWN` vs `PLACED`; box fan's delivery) are provisional and may be revisited when the renderer forces the `DASH`/`LAUNCH` and delivery-vs-effect overlaps in the contract's open questions.

## 17. After this task (not now)

Once the spread is confirmed (or the prompt is tuned until it is): expand to a real item catalog with association clouds, then the batch bake pipeline (best-of-N across the catalog, tier-organized instance sets), then the deterministic resolver proper. One thing at a time.
