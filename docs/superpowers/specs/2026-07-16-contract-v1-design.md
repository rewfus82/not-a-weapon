# Capability Contract v1 — Design

*Date: 2026-07-16. Repo: `not-a-weapon`. Precedes: the implementation plan (via superpowers:writing-plans).*

Read `CLAUDE.md`, `docs/GAME_IDENTITY.md`, `docs/CAPABILITY_CONTRACT_v0.md`, and `docs/HANDOFF.md` first — this spec assumes those constraints and does not repeat them. Driven by the contract-v1 evidence in `docs/HANDOFF.md` (2026-07-16 evening playtest).

## 1. Goal

Tighten the contract so the meanings the model already composes stop living in `note` strings only a human can read — **before** any real bake volume freezes thousands of instances against the ambiguous v0 schema. Four changes:

1. Every effect declares **who it hits** (`target: SELF | STRUCK`), model-emitted, code-validated.
2. `harmless`/`category` derivation keys on **(kind, target)** so token choice can never flip lethality again (the invariant-4 bug).
3. **Trigger semantics for self-kits** (SELF chassis) are written down and enforced: reactive ON_HIT gated to protective chassis items; ON_KILL blessed for all self-kits.
4. **Budget weights**: duration and count cost budget (structure now, exchange-rate tuning later) — closes the free-rider exploit.

Plus one deferred minor: `Effect.amount` gains `ge=0` (kills the sign-flip class from the last review).

This is schema *tightening*. No enum family gains a token except the new `Target` enum, which is a validation axis, not a renderer capability — it names who an existing effect applies to, which the renderer already had to know.

## 2. Non-goals

Exchange-rate *values* (play-tuned, renderer-era), the renderer, the bake pipeline, `TIER_BUDGET` retuning, new items, new EffectKinds (lifedrain is composition: `DAMAGE@STRUCK + HEAL@SELF`, never a token), the Unreal game.

## 3. Constraints carried in (easy to violate here)

1. **Code owns every number**; `harmless`/`category` always re-derived, never trusted.
2. **Model proposes; code disposes** — illegal drafts are deterministically *repaired*, not rejected (the keyless path must never fail).
3. **Never a hard LLM dependency** — fallback/composer/solo emit the new field from code-authored defaults.
4. Solo stays pathetic (2.0); never inflated by this pass.
5. Engine-agnostic; zero engine references.

## 4. Schema change (`contract.py`)

```python
class Target(str, Enum):
    SELF = "SELF"      # applies to the wielder
    STRUCK = "STRUCK"  # applies to whatever the effect connects with

class Effect(BaseModel):
    kind: EffectKind
    target: Target                       # REQUIRED — no default; structured output forces it
    amount: float = Field(0.0, ge=0)     # deferred minor: negative amounts rejected at parse
    duration: float = 0.0
    radius: float = 0.0
    count: int = 0
    note: str = ""
```

`target` is required so the model must declare intent on every effect and a baked scaffold can never contain an ambiguous "whatever the default was that week" absence.

## 5. Legality table + deterministic repair

A pure function (new `resolver/validate.py`, called from `clamp.apply` before derivation) repairs drafts against a code-owned table. Repair, never reject.

**Non-SELF chassis:** every (kind, target) combination is legal. Lifedrain (`DAMAGE@STRUCK + HEAL@SELF` on one stage), the healing gun (`HEAL@STRUCK`), self-costs (`DAMAGE@SELF`) are all intended compositions.

**SELF chassis (self-kits):**

| Rule | Repair |
| --- | --- |
| Triggers legal: `ON_USE`, `ON_EXPIRE`, `ON_KILL` always | — |
| `ON_HIT` ("when *you* get hit") legal **only if** the chassis item carries the `protective` tag | retrigger stage to `ON_USE` |
| `ON_IMPACT`, `ON_TRIGGER`, `ON_BLOCK` illegal | retrigger stage to `ON_USE` |
| Effects in `ON_USE` / `ON_EXPIRE` stages must target `SELF` | retarget to `SELF` |
| Effects in a legal reactive `ON_HIT` stage may target either (`STRUCK` = whoever hit you — retaliation) | — |
| Effects in `ON_KILL` stages must target `SELF` (the reward reading; the target is dead) | retarget to `SELF` |

Semantics written into the contract doc: on a self-kit, `ON_HIT` = "when you get hit", `ON_KILL` = "when you down something while this is active".

Dormant-rule note: today the only `protective` item (riot shield) locks a GUARD chassis, so no catalog item can currently produce a reactive self-kit. The rule ships defined-but-dormant; the first worn protective item (hard hat, vest…) activates it with zero code change.

## 6. Derivation matrix (`clamp.py`)

`harmless` = no lethal-kind effect targeting `STRUCK`. ("Harmless" means *can't hurt others*; hurting yourself is a cost, not a threat.)

`derive_category` walks in priority order over (kind, target) pairs present:

1. no effects → `DUD`
2. any `LETHAL_KINDS`@`STRUCK` → `WEAPON`
3. any `CONTROL_KINDS`@`STRUCK` → `CONTROL`
4. any `SELF_KINDS` (either target) **or** any non-`LURE` kind @`SELF` → `SUPPORT`
5. any `LURE` → `UTILITY`
6. else → `TRINKET`

Fixtures from the playtest, pinned as tests:
- **Adrenaline-crash kit** (`HEAL@SELF + SPEED@SELF + DAMAGE@SELF`) → `SUPPORT`, harmless — regardless of whether the crash is written as `DAMAGE` or `SLOW`.
- **Dosing nail** (`HEAL@STRUCK`, nothing lethal) → `SUPPORT`, harmless — the healing gun; heals whatever it shoots.
- **Lifedrain** (`DAMAGE@STRUCK + HEAL@SELF`) → `WEAPON`, not harmless — the self-heal doesn't launder the damage.

Accepted edge (documented, not special-cased): a build whose only effect is `DAMAGE@SELF` derives `SUPPORT` — a pure self-cost with no benefit won't survive composition in practice, and the deterministic answer is what matters.

## 7. Budget weights (`clamp.py`)

Weighted cost replaces raw amount-sum as the budget accounting unit:

```python
cost(effect) = effect.amount   * W_AMOUNT[effect.kind]
             + effect.duration * W_DURATION
             + effect.radius   * W_RADIUS
             + effect.count    * W_COUNT
```

- `W_AMOUNT` is a per-kind table, **all 1.0 at v1** — the self-family exchange rate (heal-80 vs damage-80) becomes a named, tunable knob without pretending we know its value.
- `W_DURATION`, `W_RADIUS`, `W_COUNT` are placeholder constants (> 0) beside `TIER_BUDGET` — one tuning location. Values are explicitly *not* play-tuned; the point is that a 2.5 s snare or a count-2 pierce can no longer ride free on a full damage budget.
- `total_magnitude`, `clamp_magnitudes`, and `fill_budget` switch to weighted cost. Normalization scales the float fields (`amount`, `duration`, `radius`) by one factor, proportions preserved; `count` is integer and contributes fixed cost. If count-cost alone exceeds the tier budget, counts are floor-scaled down first (deterministic; small under-budget residue from integer floor is acceptable). Zero-cost drafts still pass through.
- The **deterministic composer must fill the weighted budget exactly** by construction (its tables account for the durations/counts it emits). Solo keeps `_SOLO_AMOUNT = 2.0` and is never budget-filled — unchanged in spirit; its weighted total may shift slightly and stays pathetic.
- `target` does not affect cost at v1 (a drawback *discount* for self-costs is renderer-era tuning, noted as future).

Weights are code-side: tuning them later is a deterministic re-clamp, never a re-bake.

## 8. Ripples

- **Prompt** (`system_prompt.txt` + doc mirror): explain `target`; the slot steering (heal item as substance → healing payload aimed at them; as modifier → self-rider, i.e. lifedrain); self-kit trigger meanings. Spend words on creativity, not JSON — the schema enforces shape.
- **Deterministic paths** (`fallback.py`, composer shapes, `solo.py`): emit `target` from code-authored defaults — lethal/control kinds → `STRUCK`, self-family → `SELF`, `LURE` → `STRUCK`; self-kit/armed-patch shapes per §5.
- **Docs**: write `docs/CAPABILITY_CONTRACT_v1.md` (committed — unlike the intentionally-uncommitted v0 file, which stays untouched and retires by reference). Update `docs/RESOLVER_PROMPT_v0.md` mirror if prompt text changes. HANDOFF updated at session end per repo norm.

## 9. Testing (TDD throughout)

- Schema: `target` required (parse fails without it); negative `amount` rejected.
- Derivation: one test per matrix row, plus the three playtest fixtures above pinned by name.
- Legality: one test per repair rule in §5's table, including the dormant protective gate (fabricated protective SELF item fixture).
- Weights: free-snare now costs (a duration-only effect consumes budget); weighted `fill_budget` lands exactly on `TIER_BUDGET[tier]`; count-overflow floor-scaling; composer exact weighted budget at all six tiers; solo untouched.
- Suite baseline 251 green stays green at every commit.

## 10. Open questions (small, non-blocking)

1. Should `LURE@SELF` (bait-on-yourself, a taunt) be repaired or kept legal? v1 keeps it legal on non-SELF chassis (maximally permissive where no invariant is at stake); revisit if live rolls abuse it.
2. Placeholder weight values (`W_DURATION`, `W_COUNT`, `W_RADIUS`) — plan picks crude round numbers; any value > 0 satisfies v1's goal.
