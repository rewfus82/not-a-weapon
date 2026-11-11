# Design — Cartoonify item associations to cut false refusals

*Date: 2026-07-10 · Scope: the association clouds in `resolver/items.py` only. No code logic, no prompt, no schema changes.*

## Problem

After reframing the system prompt as a game, the live refusal rate barely moved:

```
baseline:  broom+oil 0/12 | aerosol+candles 7/12 (58%) | fan+duck 12/12 (100%)
reframed:  broom+oil 0/12 | aerosol+candles 7/12 (58%) | fan+duck 11/12 (92%)
```

`aerosol+candles` was **bit-for-bit identical** (7/12) — proof the refusal is driven not by the system prompt but by the **user message**, which lists item associations verbatim. Those associations are written as real-world mechanisms (*"a mist plus a spark becomes a gout of flame," "a hard enough knock cracks the case and spills the acid"*) that read as how-to regardless of framing.

## Approach

Rewrite every item's association cloud into a **slapstick cartoon register while preserving each item's concrete mechanical hooks** — the specific composable properties that produce good weapons. The spread mechanic depends on "every effect traces back to a stated property," so the hooks must survive; only the register changes.

Principle: `"a mist plus a spark becomes a gout of flame"` → `"that cloud loves to catch into a cartoon whoosh of flame."` Same hook (this makes fire), different register (slapstick, not molotov how-to). Real-world hazard specifics that read as instructions (corrosive *acid*, ignition *sources*) are recast into cartoon equivalents (fizzy *goo*, a *bouquet of flames*) that keep the compositional hook (coats/hazard, can-light-things) without the real-world reading.

## Constraints

- **`resolver/items.py` `_ITEMS` only.** Names, `DELIVERY_LOCK`, `COLOR_BY_ITEM`, `Build`, `DEFAULT_BUILDS`, `params_for` — all untouched.
- **4 associations per item**, keeping the existing **obvious → non-obvious → chainable-consequence** ordering (`associations[0]` is still the obvious reading — the deterministic fallback quotes it).
- **Preserve each delivery item's form-justifying hook:** push broom / mop = swingable reach (SWING); aerosol = sprays a cloud (SPRAY); box fan = pushes air (PLACED); car battery = throwable heft (THROWN).
- **Keep the substring `"bristles"` in push broom** so `test_prompt.py:22` stays green. `test_items.py` asserts only counts (≥8 items, ≥3 associations) — no text — so it needs no change.
- **All 8 items rewritten** for one consistent voice (operator decision). This means `broom+oil` is no longer a pristine regression control; accepted.

## Non-goals / caveats

- No model swap, no best-of-N, no prompt or code changes.
- Never introspect *why* a build refused — measure the rate only.
- **Ceiling risk:** if the fire/hazard *property itself* trips the model (not its phrasing), register won't fix it. This experiment is what tells us. `fan+duck` has no chemistry; if it stays high, the driver is not content and it may be accepted as deterministic-only.

## Proposed rewrites (the substance — review these)

**push broom** (SWING; keeps "bristles")
1. a big goofy handle you can swing with real reach
2. stiff bristles that slurp up and cling onto any liquid
3. sweeps in one wide dramatic arc across the floor
4. swing it fast and the bristles fling whatever they soaked up in a spray

**mop** (SWING)
1. a floppy pole with silly long reach
2. loose stringy strands that tangle and snag onto things
3. those strands gulp up liquid and hold a big sloppy load
4. whip it around and the soaked strands sling their load everywhere

**spilled fry oil**
1. a greasy puddle that sends cartoon feet flying out from under
2. gets hot and bursts into big whooshy cartoon flames
3. gloops onto and coats anything it splats against
4. leaves a banana-peel slick that drops whoever skates across it

**birthday candles**
1. a fistful of tiny wobbling party flames
2. dribble goofy hot wax blobs as they burn
3. the trick kind pop back alight the instant you puff them out
4. bunched together they're a silly little bouquet of flames

**aerosol can** (SPRAY)
1. hisses out a big dramatic cloud on cue
2. that cloud loves to catch into a cartoon whoosh of flame
3. shake it up and it gets over-excited, ready to pop like a gag prop
4. point it at anything and it makes a whole scene

**car battery** (THROWN)
1. a heavy clunky brick you can hurl
2. crackles with cartoon zap-electricity across a gap
3. sloshing with green fizzy goo inside
4. give it a good whack and the case cracks, glugging goo everywhere

**rubber duck**
1. bobbing, wide-eyed, and utterly harmless-looking
2. lets out a loud indignant SQUEAK when squeezed
3. the world's most obvious decoy, taken seriously by no one
4. its squeak yanks every eye toward wherever you plop it

**box fan** (PLACED)
1. blasts out a steady whooshing wall of wind
2. whirring cartoon blades buzzing behind a flimsy grille
3. strong enough to shove light junk skittering across the floor
4. aim it down a hall and its wind ferries along whatever's floating — mist, dust, sparks

## Validation

1. Re-run all three builds live: `PYTHONUTF8=1 python -m resolver.harness --repeats 3`. Compare `fallbacks:` to the post-reframe numbers (0% / 58% / 92%).
2. Read the spread on a cooperating build (`broom+oil`, and ideally a now-cooperating `aerosol+candles`) — confirm the cartoon associations still yield multi-stage, character-varied high-tier results, not flattened whimsy.
3. Qualitative judgement; refusal rate is stochastic; no hard threshold. Record the outcome in the ledger.

## Acceptance

- All 8 `_ITEMS` associations rewritten in cartoon register, 4 each, ordering preserved, delivery hooks intact, "bristles" retained.
- `python -m pytest -q` still green (no code changed; `test_items.py` / `test_prompt.py` pass).
- A live re-run recorded with the new rates and a spread read.
