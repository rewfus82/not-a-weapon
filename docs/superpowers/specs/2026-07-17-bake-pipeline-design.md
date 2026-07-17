# Bake Pipeline — Design (2026-07-17)

Implements the bake strategy decided in `docs/RESOLVER_ECONOMICS_AND_BAKE.md`
against contract v1 (`docs/CAPABILITY_CONTRACT_v1.md`). Deliverable: the
complete bake pipeline as a new `resolver/bake/` subpackage, proven by a
real-dollar **pilot bake** over the current 61-item catalog (~300 combos,
roughly $10–25). Launch-scale strategy is recorded here but not built.

Decisions settled in brainstorm (user-approved):

1. **Scope:** pilot bake pipeline — full pipeline code, small real spend;
   scales later by changing inputs, not code.
2. **Scaffold shape:** reuse `GadgetDraft` as the scaffold body; its numbers
   are formally *relative weights* (the deriver, not the schema, enforces
   "no magnitudes").
3. **Scaffolds per combo:** 3 depth scaffolds (2-tier bands) + adaptive
   top-up for combos whose scaffolds show real width.
4. **Name dedup:** stateless bake calls + post-wave rename pass against a
   persistent global registry.
5. **Store:** git-tracked JSONL + JSON registry under `data/bake/`.

## Non-goals

- No server, no lazy-tail service (post-slice; recorded in §9 only).
- No Batch API integration — documented as the launch-scale cost halver;
  the pilot runs sync where the retry ladder and structured `.parse` are
  proven. Revisit at launch scale.
- No jitter/threshold *value* tuning — structure now, values renderer-era
  (same rule as `W_DURATION` and `TIER_BUDGET`).
- No catalog expansion — this pass **prices** the marginal item (§8); the
  expansion itself is a separate user decision.
- No change to the runtime resolvers (`llm.py`, `fallback.py`, `solo.py`,
  `serve.py`) — the bake is offline tooling beside them, never the hot path.

## 1. Package layout

```
resolver/bake/
  __init__.py
  schema.py      # ScaffoldSet, BakeRecord, depth enum, combo_id, fingerprint
  select.py      # deterministic stratified combo selection
  run.py         # bake runner: base pass + adaptive top-up, resumable
  derive.py      # derive_instance — the pure scaffold->instance function
  dedup.py       # name registry, collision detection, rename pass
  report.py      # per-wave stats + outlier report
  __main__.py    # CLI: python -m resolver.bake <select|run|dedup|report>
resolver/prompts/bake_prompt.txt   # depth-scaffold system prompt (data, not code)
data/bake/
  combos-pilot.json    # selection output (reviewable before money moves)
  scaffolds.jsonl      # the library: one BakeRecord per line, append-per-wave
  names.json           # global name registry
  reports/             # per-wave markdown reports
```

All of `data/bake/` is **git-tracked**: a bake wave is a commit, a rename
pass is a commit, and "frozen forever" is enforced by history. SQLite is a
launch-scale revisit, not a pilot need. The bake stays engine-agnostic pure
Python, same as the rest of `resolver/`.

## 2. Scaffold schema (`schema.py`)

Model-facing structured output — one bake call returns:

```
class ScaffoldSet(BaseModel):
    shallow: GadgetDraft   # one limp stage — the DUD/COMMON reading
    medium:  GadgetDraft   # the workmanlike reading — UNCOMMON/RARE
    deep:    GadgetDraft   # chained stages, reactive triggers — EPIC/LEGENDARY
```

Three named fields, not a list: "exactly one scaffold per depth" is enforced
by construction, and the depth semantics live in the field names the model
fills. `Depth` is a code-side enum (`SHALLOW`/`MEDIUM`/`DEEP`) used by
storage and derivation.

**Numbers are relative weights.** `fill_budget` already rescales every draft
to land exactly on the tier budget, so magnitudes the model emits are only
proportions. The bake stores them untouched; every real magnitude is
produced by `derive_instance` (§4) at read time. This satisfies the econ
doc's "no magnitudes" semantically with zero new repair/derivation surface.

Stored record — one JSONL line per combo:

```
class BakeRecord(BaseModel):
    combo_id: str
    status: Literal["resolved", "unresolved"]
    contract_version: str          # "v1"
    contract_fingerprint: str      # stable hash of sorted enum tokens
    model: str | None              # the ladder model that produced it
    baked_at: str                  # ISO timestamp
    usage: dict[str, int]          # input/output token totals across its calls
    scaffolds: dict[Depth, list[GadgetDraft]]  # lists grow via top-up; empty when unresolved
```

- `combo_id` is canonical and deterministic from the role-assigned slots:
  `d:{delivery}|dmg:{damage}|u:{utility}|m:{modifier}` with `-` for empty
  slots. Same items in different roles are different combos, matching
  `Build`.
- `contract_fingerprint` = stable hash of the sorted `Delivery`,
  `EffectKind`, `Trigger`, `Target` token lists. Derivation and re-clamp
  passes warn on mismatch and re-run `repair` — a contract change means
  deterministic re-validation, never a re-bake.

**Prompt:** new `resolver/prompts/bake_prompt.txt`, same jargon-free
register and rules as the existing system prompt, teaching one build → three
readings of increasing depth ("a shallow reading, a workmanlike reading, a
deep reading — different *interpretations*, not the same weapon at three
sizes"). The user message reuses the existing slot-line format
(`items.describe()`), minus the target-tier line (depth replaces tier as the
instruction axis).

## 3. Combo selection (`select.py`)

Deterministic, seeded, reproducible; output is `data/bake/combos-pilot.json`
so the exact selection is reviewable **before any money moves**.

- **Coverage:** every catalog item appears in ≥1 selected combo (every
  association cloud gets exercised).
- **Shape strata:** ~40% 2-item, ~40% 3-item, ~20% 4-item builds.
- **Coherence strata:** spread across the existing router bands
  (`coherence.py` / `C_LOW`/`C_HIGH` terciles) so both coherent and absurd
  combos are represented.
- **Pinned builds:** the six live-validated probes, fan+duck, and the
  9/9-refused extinguisher build are always included (known hot spots for
  refusal behavior).
- **Legality:** delivery slot must be chassis-eligible (existing `Build`
  rules); no other filtering.
- Default N = 300 (CLI flag), seeded RNG for the sampled remainder.

## 4. Instance derivation (`derive.py`) — the pure function

```
derive_instance(draft: GadgetDraft, build: Build, tier: Tier, seed: int) -> ResolvedGadget
```

Depth→tier bands: SHALLOW → {DUD, COMMON}, MEDIUM → {UNCOMMON, RARE},
DEEP → {EPIC, LEGENDARY}. Adjacent tiers share a composition at different
budgets (Diablo-natural); alternates from top-up widen the pool a tier band
draws from.

Pipeline, all existing pieces plus a seeded jitter:

1. `repair(draft, build)` — existing deterministic legality repair.
2. **Seeded jitter** — per-effect proportional perturbation of the float
   fields (placeholder ±10%), seeded RNG only; this is the intra-tier
   horizontal variance.
3. `_fit` to a seeded budget point in `[0.90, 1.12] × TIER_BUDGET[tier]`
   (placeholder band; cap = existing `OVER_BUDGET_FACTOR`; `DUD_FLOOR`
   still applies).
4. `derive_category` / `derive_harmless` — existing, never trusted.

Pure and re-derivable: same `(combo_id, scaffold index, tier, seed)` →
byte-identical instance, forever. Rebalance = edit tables, re-run
`derive_instance` over the frozen library — **re-clamp, never re-bake**.
This closes the econ doc §6 gap ("current clamp scales in place and is not
yet cleanly re-derivable"): the scaffold is the stored truth; instances are
always computed, never stored mutated.

Game-side (recorded, not built): the acquisition roll picks
`(scaffold alternate, tier, seed)` — that triple is the "which instance you
drew" RNG of GAME_IDENTITY §6; extraction freezes the triple. Acquisition
random, combat deterministic, by construction.

## 5. Bake runner (`run.py`)

- One sync call per combo → `ScaffoldSet` structured output, retry ladder on
  refusal/transport failure exactly like `LLMResolver` (default ladder:
  sonnet ×2 → opus-4-8, injectable client for tests).
- **Resumable, append-only:** combos whose `combo_id` already has a line in
  `scaffolds.jsonl` are skipped; a crash or a later wave is just a re-run.
  `--retry-unresolved` re-attempts previously unresolved combos (their line
  is replaced, not duplicated).
- A combo that exhausts the ladder is recorded `status="unresolved"` with
  empty scaffolds. **Rates are logged; reasons are never introspected**
  (standing AUP rule). Unresolved combos ride the deterministic path at
  runtime, per the first-discovery UX — the library self-heals later.
- Token usage accumulates on each `BakeRecord.usage` for the cost model (§8).

**Adaptive top-up (same command, second phase):**

- Width signal, deterministic: `palette(draft)` = the set of
  `(kind, target)` pairs across all stages. Width = number of pairwise
  distinct palettes among the 3 base scaffolds (1–3). Palettes, not stage
  structure, because depth *mandates* structural growth — a flat combo's
  deep reading is the shallow palette with more stages; a wide combo reads
  the items differently at each depth.
- Top-up iff width == 3 (named constant, placeholder threshold; the report
  shows the width distribution so the threshold can be tuned on evidence).
- One top-up call per combo (pilot cap): the prompt lists the existing
  three compositions' shapes ("already have these; read the build
  differently") and returns another `ScaffoldSet`; results append to the
  per-depth alternate lists.

## 6. Name dedup + rename pass (`dedup.py`)

- **Registry** `data/bake/names.json`: normalized name → owner
  (`combo_id` + depth + alternate index). Normalization: casefold, strip
  punctuation, collapse whitespace.
- Bake calls stay stateless — no exclusion list in prompts (breaks prompt
  caching, can't scale, and parallel calls would still collide).
- **Post-wave pass:** detect collisions within the wave and against the
  registry. **First-baked keeps the name** (JSONL line order, then depth
  order). Each loser gets one rename call: a small structured output
  (`Rename { name: str }`) given its own name/description/logic and its
  collision set — only the `name` field is ever touched; composition is
  immutable.
- Re-check after renames; a name still colliding after 2 rename attempts
  gets a deterministic suffix and a flag in the report (last resort,
  visibly logged).
- The pass rewrites `scaffolds.jsonl` and `names.json`; the git diff is the
  rename audit.

## 7. Stats report (`report.py`)

Per-wave markdown report to `data/bake/reports/<date>-<wave>.md`
(statistical validation — a library this size is never hand-QA'd):

- Unresolved rate, overall and per pinned/risk build (rates only).
- Collision count, rename outcomes, deterministic-suffix flags.
- Width distribution (how many combos at width 1/2/3; top-up count).
- After running `derive_instance` across the library at all six tiers with
  a fixed report seed: per-tier weighted-cost adherence, effect-mix and
  category/harmless distributions, top/bottom 1% outliers by cost share.
- Measured $/combo and token stats (feeds §8).

## 8. Cost model — what the pilot measures

Estimated (econ doc): ~$0.05/combo sync. The pilot replaces estimates with
measured numbers:

- **$/combo** = measured mean (base call + top-up rate × top-up call +
  rename amortization).
- **Marginal item price** ≈ new legal combos the item forms under the head
  policy × measured $/combo. This is the number the catalog-expansion
  decision (HANDOFF step 2) is waiting for.
- `docs/RESOLVER_ECONOMICS_AND_BAKE.md` gets the measured numbers as a
  follow-up edit after the pilot run.

## 9. Launch-scale strategy (recorded, not built)

- **Head:** all legal 2-item combos + a curated 3-item tranche (synthesized
  head — no player data exists; real Zipf replaces it post-launch).
- **Lazy tail:** server-side, deterministic-instant + async LLM swap-in,
  per econ doc §5. Post-slice.
- **Waves:** append to the same JSONL + registry; Batch API halves cost at
  volume; wave discipline per econ doc §7 (items free, vocabulary/budget
  changes are whole-library re-clamp events).
- **Contract drift:** fingerprint mismatch → deterministic re-validation
  through `repair` (repair-never-reject makes old scaffolds forward-safe);
  never a re-bake.

## 10. Testing

TDD (red-green) on everything deterministic:

- `schema.py`: combo_id canonicalization (role-sensitivity, empty slots),
  fingerprint stability, BakeRecord round-trip.
- `select.py`: determinism (same seed → same list), full item coverage,
  strata proportions, pinned builds present.
- `run.py` (fake client): resume-skip, unresolved recording,
  retry-unresolved replacement, ladder escalation, width signal values,
  top-up trigger and append.
- `derive.py`: same seed → identical instance; different seeds differ;
  budget lands in band at every tier; repair invariants hold on scaffold
  input; DUD floor.
- `dedup.py`: normalization, collision detection (wave-internal + registry),
  first-keeps ordering, rename-only-touches-name, suffix fallback.
- `report.py`: aggregation math on synthetic records.

Live pilot = a validation gate at the end (like the association-cloud live
pass), not a unit test: run select → run → dedup → report on the real
catalog with the real ladder, `PYTHONUTF8=1`, and read the report with the
user before any follow-on decision.
