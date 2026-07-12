# Design — Sensible↔Absurd Combos: routing, catalog, handoff

*Date: 2026-07-11. Designs three interdependent pieces so the resolver spends LLM tokens only where creativity adds value. Builds on `docs/RESOLVER_ECONOMICS_AND_BAKE.md` (LLM = composition, code = numbers) and GAME_IDENTITY §6/§7/§9.*

> **⚠️ Superseded in part (2026-07-12).** Piece 1 (tag taxonomy) and Piece 2 (item catalog) below are replaced by `2026-07-12-item-catalog-and-behavior-taxonomy-design.md`, which reimagines the catalog around functional verbs and a three-layer behavior model. **Piece 3 (the coherence score) and the handoff rule still stand** and consume the new catalog. Read the two docs together; where the catalog/tags differ, the 2026-07-12 doc wins.

## The core model — two axes decide the resolver

A build sits on two axes:

- **Coherence** (sensible ↔ absurd): do the items have a real-world interaction, or does only the simulation make them combine?
- **Depth** (DUD ↔ LEGENDARY): the obvious reading vs. the clever chain.

The resolver is chosen from those two axes:

| | DUD–COMMON (obvious) | UNCOMMON–LEGENDARY (clever) |
|---|---|---|
| **Coherent** (sensible) | deterministic | deterministic (the sensible chain scales up) |
| **Incoherent** (absurd) | deterministic (weak/failed reading) | **LLM** (the sim invents) |

**The LLM is reserved for one quadrant: absurd combos at higher tiers** — exactly where a non-obvious creative leap is the whole value. Everything else is code, for free. Design consequence: **coherent combos get a *tight* distribution (reliable tools); absurd combos get a *wide* dud→god distribution (the jackpot you chase).** This maps onto the map — §7's stable outskirts (sensible, deterministic) vs. the distorted center (absurd, "reality is thin here," LLM). The resolution axis and the spatial gradient are the same axis.

---

## Piece 1 — The routing signal (coherence score)

Code needs to decide sensible vs. absurd. Mechanism: **affinity tags + a known-interaction table.**

**Affinity tags** — each item carries a small set of real-world property tags. **Taxonomy locked at 26 (Fork 1 decided):**

- **Physical / impact (6):** `sharp, blunt, heavy, long-reach, springy, brittle`
- **Substance / state (9):** `flammable, ignition, corrosive, cold, liquid, slippery, sticky, pressurized-gas, powder`
- **Energy / field (4):** `electrical, wind, loud, light-source`
- **Behavioral / dispersal (4):** `decoy, buoyant, swarm, scatter`
- **Self / support (3):** `restorative, stimulant, protective`

Principle: **every tag is interaction-bearing, not flavor** — each must drive an effect (or a param) via the known-interaction table. `bait` folded into `decoy`; `magnetic` dropped (no effect to drive — see parked contract question below).

**Known-interaction table** — tag pairs that produce an emergent effect the deterministic composer can chain (a small, code-owned table):
- `flammable` + `ignition`/`electrical` → BURN / EXPLODE
- `liquid` + `slippery` → SLOW / SNARE (slick)
- `electrical` + `liquid` → CHAIN
- `corrosive` → BURN(acid) / DAMAGE
- `sticky` → SNARE
- `pressurized-gas` + `ignition` → EXPLODE
- `wind` + `powder`/`light`/`gas` → area spread (radius up)
- `decoy`/`loud`/`bait` → LURE
- `cold` → FREEZE / SLOW
- `heavy` (+ thrown/swing form) → KNOCKBACK / DAMAGE

**Coherence score `C ∈ [0,1]`** — roughly: build a graph of the build's items; draw an edge when two items share a tag **or** trigger a known interaction. `C` = how connected the build is (e.g. fraction of item-pairs with an edge, or "is there a chain that explains all items"). Fully connected → coherent (C≈1); disconnected junk → incoherent (C≈0). Pure function of tags + the table → unit-testable, cheap, no LLM.

*(The prototype's per-slot `fit` measured "does this item suit this role"; coherence measures "do these items interact." We want the latter. `fit` may return later as a secondary naturalness signal, but it is not the routing signal.)*

---

## Piece 2 — The item catalog

**Schema:** extend `Item` with `tags: list[str]` (affinity tags). Existing fields stay: `name`, `associations` (obvious→non-obvious→chainable), plus `DELIVERY_LOCK` form + `COLOR_BY_ITEM` for delivery-capable items.

**Design goal:** the *combination* space must naturally span sensible→insane. That comes from an **archetype mix** — functional items whose combos read sensibly, and absurd-junk items whose combos read as sim-magic. The spread emerges from mixing them (knife + shears = sensible; knife + rubber duck = the sim improvising).

**Locked v1 test catalog (Fork 3 decided) — 36 items.** All 14 delivery forms have ≥1 carrier; every tag has ≥1 carrier; spans sensible / both / absurd / support.

| # | Item | Form | Tags | Quadrant |
|---|------|------|------|----------|
| 1 | push broom | SWING | long-reach, blunt | sensible |
| 2 | mop | SWING | long-reach, blunt, liquid | sensible |
| 3 | frying pan | SWING | blunt, heavy | sensible |
| 4 | crowbar | SWING | blunt, heavy, long-reach | sensible |
| 5 | sledgehammer | SLAM | blunt, heavy | sensible |
| 6 | kitchen knife | THRUST | sharp | sensible |
| 7 | screwdriver | THRUST | sharp | sensible |
| 8 | garden shears | THRUST | sharp, long-reach | sensible |
| 9 | aerosol can | SPRAY | pressurized-gas, flammable | both |
| 10 | fire extinguisher | SPRAY | pressurized-gas, cold, powder | sensible |
| 11 | garden hose | SPRAY | liquid, long-reach | sensible |
| 12 | car battery | THROWN | heavy, corrosive, electrical | both |
| 13 | brick | THROWN | heavy, blunt, brittle | sensible |
| 14 | bowling ball | THROWN | heavy, blunt | both |
| 15 | mason jar | LOBBED | brittle, liquid | sensible |
| 16 | box fan | PLACED | wind, electrical | absurd |
| 17 | mousetrap | PLACED | springy, sharp | both |
| 18 | bear trap | PLACED | sharp, heavy, springy | sensible |
| 19 | taser | HITSCAN | electrical | sensible |
| 20 | jumper cables | BEAM | electrical, long-reach | both |
| 21 | laser pointer | BEAM | light-source | absurd |
| 22 | nail gun | PROJECTILE | sharp, pressurized-gas | sensible |
| 23 | spilled fry oil | *(payload)* | liquid, flammable, slippery | both |
| 24 | bleach | *(payload)* | liquid, corrosive | sensible |
| 25 | birthday candles | *(payload)* | ignition, light-source | absurd |
| 26 | bag of flour | *(payload)* | powder, flammable | both |
| 27 | rubber duck | *(payload)* | buoyant, decoy, springy | absurd |
| 28 | glitter | *(payload)* | powder, scatter, light-source | absurd |
| 29 | silly string | *(payload)* | sticky, scatter | absurd |
| 30 | garden gnome | THROWN | heavy, brittle, decoy | absurd |
| 31 | energy drink | SELF | stimulant | support |
| 32 | first-aid kit | SELF | restorative | support |
| 33 | trash can lid | GUARD | protective, blunt | support |
| 34 | leaf blower | DASH | wind | both |
| 35 | extension cord | WHIP | electrical, long-reach | both |
| 36 | box of crickets | LOBBED | swarm, decoy | absurd |

*(§9 discipline holds — 36 is the test slice; scale toward low-three-digits later. Payload items have no `DELIVERY_LOCK`; they modify whatever delivery the paired item brings.)*

---

## Piece 3 — The handoff rule

`route(build, tier) -> "deterministic" | "llm"`, from coherence `C` and tier `T`:

```
if T in {DUD, COMMON}:            deterministic      # obvious reading, always code
elif C >= C_HIGH (~0.66):         deterministic      # coherent: sensible chain scales up
elif C <= C_LOW (~0.33):         llm  if T >= UNCOMMON else deterministic
else (middle):                   llm  if T >= RARE     else deterministic
```

The bake pipeline calls `route()` per (build, tier) slot to decide which slots cost LLM tokens. This is the **cost lever**: sensible combos and all low tiers are free; the LLM budget concentrates on absurd high-tier rolls. Pairs with the economics doc's head-of-Zipf + lazy-tail + waves — most *sensible* head-of-Zipf combos now cost nothing, and the LLM spend shifts to the *absurd* frontier.

---

## Hard dependency — the deterministic composer must be real

Today `resolver/fallback.py` is a **stub** ("the obvious reading — a plain hit"). For "sensible → deterministic" to produce *good* weapons (not stubs), the deterministic resolver must actually compose: read item tags → known interactions → staged effects → scale by tier budget. This is the prototype's `SHAPE`/`BRINGS`/`MODIFIERS` composer, reborn tag-driven. **This is central, not optional** — the whole sensible quadrant rests on it. It also becomes the numeric filler for LLM scaffolds (economics doc §5) and the instant-craft path (§5). One composer, three jobs.

---

## Phased implementation

- **P1 — Catalog + tags.** Extend `Item` with `tags`; expand catalog to ~30 archetype-spanning tagged items. *(TDD: schema, catalog invariants — every item tagged, every delivery form represented, tags drawn from the taxonomy.)*
- **P2 — Coherence scorer.** `coherence(build) -> float` from tags + the interaction table. *(TDD: coherent build ≈1, junk build ≈0, known pairs wired.)*
- **P3 — Deterministic composer v1.** Replace the stub: tags/interactions → staged effects, tier-scaled, clamped. *(TDD: a coherent build yields the sensible chain; magnitudes fit the tier budget.)*
- **P4 — Router.** `route(build, tier)` per the rule above; wire into the harness so a run reports the deterministic/LLM split and the LLM-call reduction. *(TDD: the rule table.)*
- **P5 — Integration read.** Run a mixed sensible+absurd build set; confirm sensible→deterministic reads well and absurd→LLM still delights. *(Play-tuned, not unit-tested — GAME_IDENTITY §9.)*

## Decided vs. open

**Proposed (this doc) — confirm or adjust:**
- Two-axis model (coherence × depth) → resolver quadrant; LLM reserved for absurd + higher tiers.
- Routing signal = affinity tags + known-interaction table → coherence score.
- Catalog gains `tags`; grow to ~30 archetype-spanning items.
- The deterministic composer must be richened (stub → real) — the sensible path depends on it.

**Parked contract question:** the self/support family (`restorative/stimulant/protective`) maps to HEAL/SHIELD/SPEED, which exist. But a `magnetic`-style pull has **no effect to drive** — the contract has no PULL/COLLECT/GRAVITY effect. Revisit if a field/pull mechanic is wanted later (would be a deliberate vocabulary addition per economics doc §7, not a casual tag).

**Open forks (need your call):**
1. ~~**Tag taxonomy.**~~ **DECIDED — 26 tags** (23 core + self/support family). See taxonomy above.
2. **Coherence thresholds** — `C_HIGH`/`C_LOW` and whether the "middle" leans deterministic or LLM. Tunable, but sets the LLM spend.
3. ~~**Catalog content.**~~ **DECIDED — 36-item catalog** (see Piece 2 table). All forms + tags carried.
4. **Coherent high-tiers** — pure deterministic, or an occasional LLM "polish" pass at LEGENDARY for flavor? (cost vs. sparkle.)
5. **Sequencing the composer** — richen the deterministic composer now (P3, needed for a *good* sensible path), or ship router + absurd→LLM first and let sensible combos keep the stub temporarily?

## Ties to the canon
- **§6:** extends the pre-baked-variance model — coherent combos have tight distributions, absurd wide ones; the LLM stays the frontier explorer, now scoped to the absurd quadrant.
- **§7:** the coherence axis *is* the radial gradient (stable outskirts = sensible/deterministic; distorted center = absurd/LLM). Free geometry.
- **§9:** item-count discipline intact (~30 test slice → low-three-digits v1). The deterministic composer is exactly the "balance primitives, not pairs" machinery.
- **Economics doc:** the router is the cost lever that concentrates LLM spend on the absurd frontier; the deterministic composer is the shared numeric filler.
