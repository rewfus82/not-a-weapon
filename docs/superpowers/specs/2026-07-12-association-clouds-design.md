# Association Clouds for the 60-Item Catalog — Design

**Date:** 2026-07-12
**Status:** Approved (brainstorm complete)
**Depends on:** `docs/superpowers/specs/2026-07-12-item-catalog-and-behavior-taxonomy-design.md` (executed), `resolver/items.py` as of `cafe68e`.

## Why

The 60 catalog items have (almost) no `associations`. `Item.describe()` falls back to
verb + tags, which serves the deterministic path but starves the LLM path — the
association clouds are half the system (thin item data → bland weapons, CLAUDE.md
invariant). This gates all LLM-path and bake work.

Hard-won context this design builds on (see `.superpowers/sdd/progress.md`):

- **Associations are the refusal lever, not the system prompt.** A/B runs proved
  system-prompt reframing does nothing; the user-message item associations drive
  refusals. Cartoon register on an item's associations took a 92%-refused harmless
  build to 0% without flattening the dud→god spread.
- **Retries + model escalation solve merit-refusals.** `LLMResolver` retries with an
  ordered model list (default sonnet ×2 → opus-4-8); that took genuinely weapon-shaped
  content to 0%. Both levers exist — the clouds are written knowing they exist.
- Register fixes phrasing-driven false refusals on harmless content; retries+Opus fix
  the rest. Neither of the two previously-cartoonified items (rubber duck, box fan)
  survived into the new catalog, so nothing starts cartoonified.

## Decisions (settled in brainstorm)

1. **Scope:** all 60 items. Junk (48) gets the full creative treatment; real guns (6)
   get minimal dry lines; real ammo (6) gets near-nothing dry lines.
2. **Register:** real by default. Cartoon register is a *repair tool*, applied
   per-item only after live validation implicates that item in refusals (the
   fan+duck playbook). Never applied pre-emptively.
3. **Validation:** 4–6 risk-class probe builds, ~9–12 calls each (~50–70 total),
   not just the 3 `DEFAULT_BUILDS`.
4. **Quality gate:** the user reviews all 60 clouds as text at a checkpoint after
   authoring and *before* any live calls.
5. **Authoring:** hand-authored in-session, batched by catalog layer, single voice.

## Data shape

Clouds live inline in `resolver/items.py` on the existing `Item.associations` field
(`tuple[str, ...]`). No new files, no schema change, `describe()` untouched (it
already prefers associations and joins with ", "). The file grows ~300 lines,
acceptable for a data catalog.

## Cloud conventions (the editorial contract)

**Junk items (48):** 3–5 lines, target 4, ordered:

1. *Obvious* — the physical property anyone sees first.
2. *Non-obvious / exploitable* — the property a scavenger notices.
3. (optionally another of 1–2)
4. *Chainable consequence* — what happens when this meets something else; the
   "X + Y = Z" hook, always last.

Every line is a concrete physical property the model can trace an effect back to —
the user-message template demands exactly that ("Trace every effect back to a stated
property of the specific objects above").

**Consistency rules:**

- Associations must embody the item's `tags` and `verb`, never contradict them. A
  `slippery`-tagged item's cloud must contain the slick; a `loud` item's cloud must
  make noise.
- **No numbers, no magnitudes.** Code owns every number (CLAUDE.md invariant); the
  clouds are prose properties only. "Dead-weight heavy", never "20 kg". Caliber
  *names* ("9mm", ".30-06") are identifiers, not magnitudes, and are allowed in the
  gun/ammo dry lines.
- No capability-contract vocabulary leaks: clouds describe physical properties, not
  effect/trigger/delivery enum tokens.

**Real guns (6):** 2–3 dry, matter-of-fact lines. "Does exactly what a rifle does"
register — no ballistic elaboration, no creative hooks. The coherent-firearm path
routes deterministic anyway; keep the refusal surface small.

**Real ammo (6):** 1–2 dry lines; inert-until-loaded framing.

### Worked exemplars (canonical for voice and ladder)

`blender` (mechanism · stream; verb `blend-&-spit`; tags liquid, scatter, electrical):

```python
associations=(
    "a pitcher of whirling blades on a motor base",
    "chews anything dropped in into a slurry",
    "the lid never holds — run it open and it slings its contents out in a cone",
    "whatever you feed it comes out the top as a fine flying spray",
),
```

`motor oil` (substance; verb `slick`; tags liquid, flammable, slippery):

```python
associations=(
    "slick, viscous, impossible to get traction on",
    "clings in a dark film to whatever it coats",
    "flammable once something gets it hot enough",
    "poured across a floor it turns the whole stretch into a skating rink",
),
```

`9mm pistol` (real gun — dry register):

```python
associations=(
    "a standard 9mm sidearm",
    "does exactly what a pistol does; nothing clever about it",
),
```

## Authoring process

Four batches, each a commit with tests green:

1. **Mechanisms — ranged:** ballistic, spread, stream, arc, thrown, beam
   (includes the 6 guns' dry lines).
2. **Mechanisms — contact & mobility:** melee, placed, self/mobility.
3. **Modifiers / energizers.**
4. **Substances + ammo/feeders** (real ammo dry lines; improvised ammo full
   treatment).

The spec's conventions + exemplars above are the style guide; batches must keep one
voice.

## User review checkpoint (hard gate)

After all four batches land and before any live API call, present all 60 clouds to
the user for editorial read-through. Apply edits, commit, then validate. Blandness
is cheap to fix as text and expensive to discover in live output.

## Validation

**Probe builds** — 4–6 throwaway builds covering the refusal-risk classes, wired as
harness-layer fixtures, *not* added to `DEFAULT_BUILDS` (exact wiring decided in the
plan after reading the harness CLI). Candidate set:

| Class | Build sketch |
|---|---|
| incendiary | potato cannon + gasoline + road flare |
| corrosive | pressure washer + pool chlorine |
| whimsical-harmless | blender + marbles + expanding foam |
| electrical | weed whacker + jumper cables |
| coherent firearm | 9mm pistol + 9mm rounds |
| placed trap | bear trap + motor oil |

**Run shape:** default retry ladder (sonnet ×2 → opus-4-8) via existing
`--attempts` / `--escalate-model`; ~9–12 calls per build across the tier schedule;
`PYTHONUTF8=1`, output redirected to a UTF-8 file (Windows mojibake).

**Acceptance:**

- Refusal/fallback rate ~0% per build with retries+escalation.
- Dud→god spread and within-tier variety confirmed by eyeball on rendered output.

**Repair loop for a refusing build:** identify the implicated item(s) by *ablation* —
swap items in/out and re-run that build — **never** by asking any model why it
refused (standing AUP lesson: refusals are a normal fallback outcome; log the rate,
never chase the reason). Rewrite only the implicated item's register (cartoonify the
register, preserve the mechanism hooks), re-run that build only.

## Testing (TDD on the mechanical, not the prose)

- Every catalog item has non-empty `associations`.
- Junk items have 3–5 lines; guns and ammo have 1–3.
- No association line contains a digit, except lines on caliber-carrying items
  (guns/real ammo) where the only digits form the item's own caliber name (the
  no-numbers rule, mechanically enforceable).
- `describe()` behavior is already pinned by existing tests.

Prose *quality* is gated by user review, not tests — creative text has no failing
test, per the GAME_IDENTITY §9 principle.

## Risks

- **Second register pass needed:** some items may drive refusals despite real
  register — bounded by the targeted-cartoonify repair loop, which is per-item and
  per-build.
- **Validation cost creep:** several refusing builds would multiply re-runs —
  mitigated by re-running only the affected build after each repair.
- **Cloud/tag drift over future edits:** the consistency rule goes into the
  `items.py` header comment so future editors see it at the point of edit.

## Out of scope

Bake pipeline, best-of-N cost optimization, `_TIER_SEED` tuning, tagless-gun
presentation (all queued in `docs/HANDOFF.md`); any change to enums, schema,
`clamp.py`, router thresholds, or the system prompt.
