# Resolver Economics & Bake Strategy

*Refines GAME_IDENTITY §6 (the signature roll / pre-baked variance) and §9 (item-count discipline). Where this doc and §6 disagree on the **cost model** or the **LLM's role**, this doc is current — §6's prose predates the combination-scale math below. The *reasoning* in §6 still holds; the numbers and the division of labor are sharpened here.*

Date: 2026-07-11.

## TL;DR

Three problems — bake cost, balance at scale, and content cadence — collapse into **one** decision:

> **The LLM owns composition; code owns every number.**

The model produces a creative *scaffold* (which primitives, staged sequence, relative weights, name/flavor — **no magnitudes**). Code derives the tier ladder, the magnitudes, and the intra-tier variance from small primitive tables. That single split makes bakes affordable, makes rebalancing free, and makes content self-funding. This doc records why, and the bake strategy that follows.

## 1. The scale reality

At **~150 base items** (v1 target, well within §9's low-three-digits discipline) the *combination* space is enormous:

| items folded in | combinations |
|---|---|
| 2 | ~11,175 (C(150,2)) |
| 3 | ~551,300 (C(150,3)) |
| 4 | ~20,260,275 (C(150,4)) |
| **2–4 total** | **~20.8 million** |

Before slot-role assignment (delivery/damage/utility/modifier are distinct) and before ~10–20 variations per combo. Folded in: **hundreds of millions of theoretically-possible instances from 150 items.**

**This does not conflict with §9.** The item *catalog* stays small (≈150); the "hundreds of thousands / millions" is the *instance library*, which §6 always anticipated ("pre-generate many resolved instances offline"). Item count is a content-cost discipline (§9); instance count is a bake-strategy problem (this doc).

## 2. Why the full space is un-bakeable — the cost correction

Per resolved instance via the LLM (Sonnet, ~$3/$15 per 1M, prompt-cached system prompt, adaptive thinking on): output tokens dominate at ~$0.03–0.05/instance; **batch API halves it**. Under the naive model (~15 LLM calls/combo for 6 tiers × variants), that's ~$0.50/combo:

| bake scope | naive cost |
|---|---|
| all 2-item | ~$5,600 |
| all 3-item | ~$275,000 |
| all 4-item | ~$10,000,000 |

**GAME_IDENTITY §6's "a full offline bake is a few hundred dollars, once" does not hold at 150 items × 4 slots** — it was priced for a far smaller space. Baking the full combination space is economically impossible and always will be. This is not a tuning problem; it forces the architecture below.

## 3. The architecture — LLM scaffold, code fills

This is already the §6/§9 split ("tier = code-owned power budget; composition = model-owned creativity"; CLAUDE.md invariant #4), taken to its conclusion.

- **The LLM emits a scaffold, not an instance.** Per combo, one call produces **a few compositions of increasing *depth*** (a shallow reading, a medium one, a deep one) — each = an ordered list of stages (trigger + which effect *kinds*) with *relative weights* ("this effect is the payload, these are riders") plus name/description/logic. **No magnitudes.**
- **Code derives everything numeric.** Map depth → tier; fill magnitudes from `tier budget × per-effect cost × relative weight`; generate intra-tier variance by RNG jitter on that distribution (plus boosters) within the ~10–15% over-budget cap.
- **Why depth-scaffolds, not one:** §6 requires "different *depth* of reading, not different numbers" across tiers — a DUD is one limp stage, a LEGENDARY chains extra stages and an `ON_KILL`. A single scaffold scaled across tiers would make DUD and LEGENDARY the same weapon at different sizes, which §6 forbids. Emitting compositions at several depths in one call preserves the ladder *and* batches the work.

**Cost after the pivot** (~1 call/combo producing ~3 scaffolds, ~$0.05/combo; batch ~$0.03):

| bake scope | naive | scaffold |
|---|---|---|
| top 5,000 combos | $2,500 | **~$250** |
| top 50,000 combos | $25,000 | **~$2,500** |
| all 3-item (551k) | $275,000 | **~$27,000** |

A head-of-Zipf launch bake lands in **hundreds of dollars.** The pre-bake model survives.

**What the pivot preserves vs. costs:** it keeps the model's irreplaceable value (the creative *reading* — non-obvious properties, the chain, the flavor). It *reduces* per-instance uniqueness of the *numbers* and some horizontal character, since intra-tier variance is now partly code-manufactured (RNG jitter) rather than fully model-authored. §6 already frames intra-tier variance as horizontal and partly booster/RNG-driven, so this is a sharpening, not a reversal — but it is a real, deliberate reduction in per-instance model touch. The validated finding that the LLM produces genuine *range* still applies; it is repackaged as "give me a shallow, medium, and deep reading" instead of "make a LEGENDARY."

## 4. Bake strategy — head-of-Zipf + lazy tail + revenue-funded waves

You never bake the space. You bake the **head of a Zipf curve** and let the rest self-heal — the deliberate version of §6's "common combos pre-baked, long tail lazily generated on first discovery."

- **Launch:** bake the top few thousand combos for the starter catalog (hundreds of dollars). Ship the lazy pipeline and the deterministic instant-path (§5).
- **Lazy tail:** an un-baked combo is generated once, on first discovery, server-side, globally cached, then it's pre-baked for everyone (§6's "frontier explorer, never the workhorse"). Most of the 20M+ 4-item combos are *never generated at all* unless a player actually crafts one.
- **Waves:** as revenue arrives, proactively pre-fill the next tranche of the tail and **add items**. A wave is just running the bake ahead of demand. Content velocity becomes a function of revenue, not a fixed upfront capital risk — a solo-dev-friendly shape.
- **Items are the cheapest content lever.** Baking 10 new items into a 150-item catalog explodes the combination frontier (each new item pairs with all existing ones) for near-zero *authoring* cost — you run a bake, you don't hand-craft weapons.

## 5. First-discovery UX — the deterministic resolver's third job

The instant a player crafts a never-baked combo:

1. **The deterministic resolver serves a valid instance immediately** (always works, no wait, no API).
2. The richer LLM-baked version is generated async, globally cached, and **swaps in for everyone** once forged.

The deterministic resolver now does **triple duty**: no-API fallback, instant-craft-while-the-frontier-bakes, *and* the numeric filler that turns scaffolds into instances. It keeps earning its place (CLAUDE.md invariant #6).

## 6. Balance at scale — the same fix, for free

Because magnitudes are 100% code-derived, balance is **not** a function of instance count:

- **Balance surface = `O(effect-kinds × tiers)`** — a few hundred numbers (per-effect costs, tier budgets, secondary-field weights), fixed whether the library is 300k or 300M instances. You tune 16 primitives across the tier ladder, never items or pairs or combos.
- **Rebalancing is a re-clamp, not a re-bake.** Store the model's composition (relative weights); final magnitude = pure function of `(composition, tables, tier)`, recomputed — never mutated in place. Nerf `BURN` globally = edit one cost + run a deterministic re-clamp pass over the frozen library. Cents, not a re-bake, and the composition (creativity) is untouched. *(Note: the current `clamp.py` scales-to-fit in place and is not yet cleanly re-derivable — closing that gap is the concrete task this implies.)*
- **Validation is statistical, never manual.** You cannot hand-QA hundreds of thousands of instances. The bake pipeline must emit per-tier distributions and outlier reports (magnitude spread, effect-mix, budget adherence, top/bottom 1%); you tune tables against aggregates and hunt outliers.

## 7. Wave discipline — the power-creep guard

The one rule that keeps balance from drifting across seasons:

- **Waves add *items* freely.** An item just composes the existing primitives; the code-owned budget clamps it. No balance event.
- **Touching the primitive vocabulary or the budgets is deliberate and rare.** Adding a new *effect kind*, or bumping tier budgets, is a whole-library balance event (a re-clamp), not a casual wave addition. Break this line and the library power-creeps.

## 8. Status: decided vs. open

**Decided / strongly converged (this doc):**
- Full combination space is un-bakeable; §6's cost estimate is superseded.
- LLM = composition scaffold (no magnitudes); code = tier ladder + magnitudes + variance.
- Magnitudes must be re-derivable (store composition; recompute numbers) → rebalance by re-clamp, not re-bake.
- Bake = head-of-Zipf + lazy tail + revenue-funded waves.
- First-discovery: deterministic instance instantly, LLM version swaps in globally once baked.
- Balance surface is primitive-table-sized and instance-count-independent; validated statistically.
- Waves add items freely; vocabulary/budget changes are deliberate, rare, whole-library events.

**Open (design next):**
- **Scaffold schema** — exactly what the model emits (stages + effect kinds + relative weights + flavor) and what the deterministic filler needs to turn it into a tier ladder.
- **Depth-scaffolds per combo** — 3? 5? (the horizontal-character budget vs. per-call cost/quality).
- **Variance line** — how much intra-tier variance is pure code RNG vs. still model-touched (RNG jitter reads thinner than model-authored character).
- **Tier count** — keep 6 for loot-ladder feel (nearly free under code-derived tiers) vs. cut to 4. Now a *feel* decision, not a cost one.

## 9. Relationship to GAME_IDENTITY

- **§6 refined:** the "few hundred dollars" full-bake estimate is superseded (the full space is millions); the LLM's role narrows from "generate many instances per combo" to "generate a few depth-scaffolds per combo," with code deriving tiers/magnitudes/variance. The *soul* of §6 — pre-baked variance, frozen deterministic instances, the frontier explorer, the roll-quality-from-risk — is unchanged.
- **§9 upheld:** ~150-item catalog is correct; the large number is the instance library, not the catalog.
- **CLAUDE.md invariant #4 sharpened, not broken:** "Code owns balance; the model owns creativity" becomes "the model authors *composition only*; code authors *every number*, re-derivably."
