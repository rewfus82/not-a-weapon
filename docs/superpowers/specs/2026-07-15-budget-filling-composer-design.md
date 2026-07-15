# Budget-filling composer — design

**Date:** 2026-07-15
**Scope:** `resolver/fallback.py`, `resolver/solo.py`, and their tests. The clamp, the LLM path, the contract enums, and `TIER_BUDGET`'s values are untouched.

## Problem

GAME_IDENTITY §6: within a tier, every build spends the **same power budget** — variance is shape/character, never total. The deterministic composer violates this: `_TIER_SEED` is a flat per-effect amount, so totals scale with effect count. At LEGENDARY a single-effect build (any tagless gun) totals 45 while a three-effect build totals 134.4 — a ~3× power gap §6 says must not exist, and the 134.4 sits at the over-budget cap, silently consuming the ~12% headroom §6 reserves for boosters.

## Decisions (made 2026-07-14/15)

1. **The composer fills the budget** — enforcement lives in `fallback.resolve`'s amount derivation, not in a clamp floor. The LLM path stays cap-only; at bake scale code derives its magnitudes anyway (RESOLVER_ECONOMICS), so a clamp floor now would be throwaway machinery and would need a solo exemption.
2. **Sparse builds get the full budget.** A single-item craft riding the full tier ladder is legitimate: the risk gate is the tier roll; ingredient count buys breadth and character, not total. (Solo use — no craft — stays pinned at the DUD floor, unchanged.)
3. **Weighted split: overlays half-share.** Base-chain effects weight 1, RARE+ modifier overlays weight 0.5 — overlays keep reading as bonuses riding the main effects.

## Composer math (`resolver/fallback.py`)

Delete `_TIER_SEED`. In `resolve`, amounts derive from the tier budget:

- Chosen base effects (existing take-by-tier logic, unchanged) get weight `1.0`; overlays appended at RARE+ (existing logic, unchanged) get weight `0.5`.
- Each effect's amount = `TIER_BUDGET[tier] * weight / total_weight`.
- Every deterministic draft therefore totals exactly `TIER_BUDGET[tier]` (float-exact within `pytest.approx`), for every build shape at every tier.

Worked example, LEGENDARY (budget 120): 3 base + 1 overlay → Σw = 3.5 → base effects ≈ 34.29 each, overlay ≈ 17.14, total 120. Lone-DAMAGE gun → one effect at 120.

`TIER_BUDGET` (imported from `resolver.clamp`) becomes the single play-tuning knob for deterministic power. The clamp still runs after composition; the deterministic path never trips its cap (`budget < budget × 1.12`), returning the over-budget headroom to booster-only use.

## Solo decoupling (`resolver/solo.py`)

Replace the private import `from resolver.fallback import _TIER_SEED` and `_SOLO_SEED = _TIER_SEED[BASE_USE_TIER]` with solo's own pinned constant:

```python
_SOLO_AMOUNT: float = 2.0  # code-owned; a bare item is pathetic, below even a DUD craft
```

Same value as today — solo behavior is byte-identical. This also retires the ledger's deferred minor about the cross-module private import (the `substance_stages` import from fallback is public and stays).

## Consequences (deliberate)

- **Gun builds stop reading underpowered:** lone DAMAGE at LEGENDARY goes 45 → 120 (one big honest hit). The HANDOFF "tagless guns read stark" note remains true for *shape* (DAMAGE-only every tier) but no longer for magnitude.
- **Multi-effect builds renormalize down:** 3-effect LEGENDARY 134.4 → 120.
- **Crafted DUD (6.0) now strictly beats solo use (2.0)** — previously both totaled 2.0. Crafting always beats bare pickup, even at the floor.
- Playground/harness numbers change everywhere on the deterministic path; names, kinds, stages, and tier-growth structure do not.

## Testing

Pin relationships, not magic numbers:

- For every `DEFAULT_BUILDS` build × every tier: `total_magnitude(fallback.resolve(build, tier)) == pytest.approx(TIER_BUDGET[tier])`.
- Where an overlay fires: overlay amount == base amount / 2, and per-effect amounts follow the weight formula. **Erratum (found in implementation):** swamp_cooler never produces an overlay — its only candidate (CHAIN from the car battery) is always in the base chain via `electrical+liquid` and gets deduped; the test uses t-shirt cannon + propane tank (BURN base, EXPLODE overlay) instead. Do not "fix" the test back to swamp_cooler — it would assert nothing.
- Deterministic path never trips the clamp cap: resolved total == draft total at every tier.
- Solo: existing pins hold unchanged (2.0 total, below `TIER_BUDGET[COMMON]`, DUD tier); add a pin that solo total < deterministic DUD craft total.
- Update any existing tests that assert old seed-derived amounts; kind/stage/count assertions are unaffected.

## Out of scope

- Clamp changes of any kind; `TIER_BUDGET` value changes (the knob stays where it is — this pass makes it *the* knob; turning it is later play-tuning).
- LLM-path magnitude enforcement (bake-scale code ownership per RESOLVER_ECONOMICS).
- Minimum-item-count rules or sparse-build haircuts (decision 2 rejects them).
