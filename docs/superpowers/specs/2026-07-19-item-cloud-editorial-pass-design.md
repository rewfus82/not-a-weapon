# Item-Cloud Editorial Pass — Design

**Date:** 2026-07-19
**Status:** Approved (brainstorm complete)
**Depends on:** `docs/superpowers/specs/2026-07-12-association-clouds-design.md` (the
cloud conventions and voice, which this pass inherits wholesale),
`resolver/items.py`, `tests/test_associations.py`, the pre30 wave evidence
(`data/bake/reports/2026-07-18-pre30.md`, `docs/HANDOFF.md`).

## Why

The pre30 wave's quality verdict: the generator and prompt are good enough; the
quality ceiling is now the item association clouds. Three findings drive this pass:

1. **The ON_HIT self-kit path is dormant.** `resolver/validate.py` demotes ON_HIT
   to ON_USE on a SELF chassis unless the delivery item carries the `protective`
   tag, and the only protective item (riot shield) locks GUARD. No worn protective
   item exists, so "effects when you get hit" never fires.
2. **SUPPORT and UTILITY are starved** (pre30 derive sweep: 30 SUPPORT, 2 UTILITY
   of 336 instances). `derive_category` is a strict priority ladder: UTILITY needs
   *pure-LURE* gadgets and the airhorn is the catalog's only lure; SUPPORT needs
   HEAL/SHIELD/SPEED feeders and only the adrenaline shot and first-aid kit exist.
3. **The delayed cook-off trope is overused** (~6 of 28 combos). Mismatched-caliber
   ammo draws are frequent, and the deliberately dry ammo clouds ("inert until a
   matching firearm feeds them") give the model exactly one improvisation to
   converge on.

Scope was settled in brainstorm: **both levers, kept small** — four new items plus
one hook line per real-ammo cloud. No full-catalog re-read.

## New items (4)

All slots use existing enum values and existing taxonomy tags — no contract change,
no taxonomy widening, no resolver code change.

| Item | Roles | Delivery | Tags | Base use | Verb |
|---|---|---|---|---|---|
| firefighter turnout coat | MECHANISM | SELF | `protective` | SELF → SHIELD | shrug-off |
| battery boombox | MECHANISM | PLACED | `loud` | PLACED → LURE | blast |
| cooler of raw steaks | SUBSTANCE | — | `slippery` | PLACED → LURE | bait |
| case of energy drinks | MECHANISM + SUBSTANCE | SELF | `stimulant`, `liquid` | SELF → SPEED | chug |

Design notes, one per item:

- **Turnout coat** — the flagship: a worn SELF + `protective` item activates the
  ON_HIT self-kit path through the *existing* `validate.py` check with zero code
  change. Fire register chains richly with the burn/ignition-heavy substance
  layer ("walk through your own fire"). Mirrors the riot shield's tag and the
  adrenaline shot's SELF delivery.
- **Boombox** — the airhorn's sustained partner; gives `loud` (single-tag effect:
  LURE) a placeable carrier and feeds pure-LURE (UTILITY) compositions.
- **Raw steaks** — bait payload, SUBSTANCE-only: it needs a chassis (bear trap,
  t-shirt cannon) to become a build; solo it is meat on the ground. `slippery` is
  the honest interaction-bearing tag (slick pulp underfoot, like the produce
  crate). Chains directly with the bear trap's "anything lured onto it" line.
- **Energy drinks** — junk-register stimulant mirroring the adrenaline shot's
  MECHANISM+SUBSTANCE shape (chug it solo, feed it as a substance). `liquid` buys
  the electrical/cold pair interactions.

Clouds follow the 2026-07-12 conventions unchanged: 3–5 lines, obvious →
non-obvious → chainable-last, lines embody tags and verb, no digits, no enum
vocabulary, real register.

## Ammo hook lines (6)

Each real-ammo cloud keeps its two dry lines and gains **one** hook line — a
concrete non-fire improvisation. The six hooks must be *distinct from each other*
(e.g. rattle-as-gunfire decoy, ballast weight, brass underfoot — final text at the
review checkpoint) so that mismatched-caliber draws stop converging on cook-off.

This deliberately and partially reverses the 2026-07-12 spec's ammo-dryness
decision (small refusal surface). Evidence for the reversal: pre30's "Gunfire
Echo" invented the rattle-decoy angle unprompted and resolved fine, and the retry
ladder + escalation exist precisely to absorb marginal refusal pressure. The
reversal is *partial*: hooks are non-fire, non-ballistic improvisations; the
inert-until-fed framing stays.

## Process

1. **Draft as text.** All content — four full item clouds and six ammo hook
   lines — drafted in a plain review document (scratchpad, not committed).
2. **User editorial checkpoint (hard gate).** The user red-pens the text.
   Blandness is cheap to fix as text, expensive to discover in live output.
3. **Land approved text** in `resolver/items.py` + test updates via the normal
   plan/TDD flow; tests green; commit. Item definitions land exactly as tabled
   above; only the prose is at the checkpoint's discretion.
4. **No live API calls anywhere in this pass.** Live validation of the new items
   rides with the next bake wave, which must bake scaffolds for new-item combos
   anyway and will surface refusal rates at no extra cost.

## Testing (mechanical only, per the standing split)

`tests/test_associations.py` changes:

- Ammo line range widens from (1, 2) to (2, 3).
- New names join batch tuples: coat + boombox → `BATCH_CONTACT`, steaks +
  drinks → `BATCH_SUBSTANCES` (the partition test then covers them
  automatically).
- Existing invariants (non-empty clouds, no digits outside caliber names) apply
  to the new items unchanged.

Prose quality is gated by the user checkpoint, not tests.

## Blast radius

- **Pre30 scaffolds: unaffected.** `contract_fingerprint` hashes only the four
  enum vocabularies; item text and catalog membership are not part of it. The
  168 committed gadgets stay valid.
- **HELD pilot selection (`data/bake/combos-pilot.json`): unaffected.** It is a
  frozen file keyed by item names; existing names don't change. New items simply
  don't appear in it — a future selection can include them.
- **Deterministic path: mildly enriched.** The new items' tags/base uses feed the
  fallback composer through existing tables; no table changes.
- **Category mix at the next bake:** boombox + steaks feed UTILITY, coat + drinks
  feed SUPPORT. No guarantee of proportions — the model still composes — but the
  starved categories stop being structurally impossible to reach.

## Out of scope

The 300-combo pilot (stays HELD), any live API call, prompt or contract changes,
combo-selection changes (an alternative anti-cook-off lever, deliberately not
taken here), the full-catalog cloud re-read, ON_KILL rider filler (a prompt-side
issue), name-style repetition (dedup-side), catalog expansion beyond these four.
