# Cartoonify Item Associations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite all 8 item association clouds in `resolver/items.py` into a slapstick cartoon register (preserving every mechanical hook) so the user-message content stops reading as real-world how-to, then measure the refusal-rate delta live.

**Architecture:** Single-file data edit — replace the `_ITEMS` list body. No logic, prompt, schema, or test-code changes. Validate with the existing harness.

**Tech Stack:** Plain Python data (a list of `Item` dataclasses); pytest guard; the CLI harness as measurement.

## Global Constraints

- **Edit `resolver/items.py` `_ITEMS` only.** Do not touch `Item`, `CATALOG`, `DELIVERY_LOCK`, `COLOR_BY_ITEM`, `Build`, `DEFAULT_BUILDS`, `params_for`.
- **4 associations per item**, ordering **obvious → non-obvious → chainable-consequence** (`associations[0]` stays the obvious reading — the deterministic fallback quotes it).
- **Keep the substring `bristles` in push broom** (`test_prompt.py:22` asserts it in the broom message).
- **Preserve delivery-form hooks:** push broom / mop swingable; aerosol sprays; box fan pushes air; car battery throwable.
- **No refusal-reason introspection** — measure the rate only.
- All 8 items rewritten (one consistent voice); `broom+oil` is no longer a pristine control — accepted.

---

### Task 1: Rewrite the `_ITEMS` associations

**Files:**
- Modify: `resolver/items.py` (replace the `_ITEMS` list, currently lines 19–68)
- Test: `tests/test_items.py`, `tests/test_prompt.py` (existing; must stay green — no new test)

**Interfaces:**
- Consumes: nothing new. `Item(name, associations)` shape unchanged.
- Produces: same 8 item names with rewritten association text.

- [ ] **Step 1: Replace the `_ITEMS` list**

In `resolver/items.py`, replace the entire `_ITEMS: list[Item] = [ ... ]` block (lines 19–68) with exactly:

```python
_ITEMS: list[Item] = [
    Item("push broom", [
        "a big goofy handle you can swing with real reach",
        "stiff bristles that slurp up and cling onto any liquid",
        "sweeps in one wide dramatic arc across the floor",
        "swing it fast and the bristles fling whatever they soaked up in a spray",
    ]),
    Item("mop", [
        "a floppy pole with silly long reach",
        "loose stringy strands that tangle and snag onto things",
        "those strands gulp up liquid and hold a big sloppy load",
        "whip it around and the soaked strands sling their load everywhere",
    ]),
    Item("spilled fry oil", [
        "a greasy puddle that sends cartoon feet flying out from under",
        "gets hot and bursts into big whooshy cartoon flames",
        "gloops onto and coats anything it splats against",
        "leaves a banana-peel slick that drops whoever skates across it",
    ]),
    Item("birthday candles", [
        "a fistful of tiny wobbling party flames",
        "dribble goofy hot wax blobs as they burn",
        "the trick kind pop back alight the instant you puff them out",
        "bunched together they're a silly little bouquet of flames",
    ]),
    Item("aerosol can", [
        "hisses out a big dramatic cloud on cue",
        "that cloud loves to catch into a cartoon whoosh of flame",
        "shake it up and it gets over-excited, ready to pop like a gag prop",
        "point it at anything and it makes a whole scene",
    ]),
    Item("car battery", [
        "a heavy clunky brick you can hurl",
        "crackles with cartoon zap-electricity across a gap",
        "sloshing with green fizzy goo inside",
        "give it a good whack and the case cracks, glugging goo everywhere",
    ]),
    Item("rubber duck", [
        "bobbing, wide-eyed, and utterly harmless-looking",
        "lets out a loud indignant SQUEAK when squeezed",
        "the world's most obvious decoy, taken seriously by no one",
        "its squeak yanks every eye toward wherever you plop it",
    ]),
    Item("box fan", [
        "blasts out a steady whooshing wall of wind",
        "whirring cartoon blades buzzing behind a flimsy grille",
        "strong enough to shove light junk skittering across the floor",
        "aim it down a hall and its wind ferries along whatever's floating — mist, dust, sparks",
    ]),
]
```

- [ ] **Step 2: Run the guards to verify green**

Run: `python -m pytest tests/test_items.py tests/test_prompt.py -v`
Expected: PASS — `test_catalog_has_rich_association_clouds` (8 items, ≥3 associations each), `test_system_prompt_is_loaded_and_jargon_free`, and `test_render_user_message_includes_slots_associations_delivery_and_tier` (still finds `bristles` in the broom message).

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS — 46 tests (no code changed).

- [ ] **Step 4: Commit**

```bash
git add resolver/items.py
git commit -m "feat: cartoonify item associations to cut false refusals (keep compositional hooks)"
```

---

### Task 2: Validate against the post-reframe baseline

**Files:** none modified. Runs the harness and records the result.

**Prerequisite:** `ANTHROPIC_API_KEY` set in the environment at run time (operator-supplied; never committed).

- [ ] **Step 1: Re-run all three builds live**

Run:

```bash
PYTHONUTF8=1 python -m resolver.harness --repeats 3
```

Read the final `fallbacks:` line. Compare to the post-reframe baseline: `broom+oil 0/12 | aerosol+candles 7/12 (58%) | fan+duck 11/12 (92%)`.

- [ ] **Step 2: Spread read on a cooperating build**

Confirm `broom+oil` (and any now-cooperating `aerosol+candles`) still produces a real spread — multi-stage high tiers, distinct within-tier character — and did not flatten into vague whimsy. The cartoon associations must still carry concrete composable hooks.

- [ ] **Step 3: Record and judge**

Record in the ledger: the new `fallbacks:` line, the delta vs. 0% / 58% / 92%, and a one-line spread verdict. Success = the two problem builds meaningfully below their post-reframe rates with spreads intact. Refusal rate is stochastic and model-side; no hard threshold; do not introspect *why* any remaining slot refused.

- [ ] **Step 4 (conditional): flag the ceiling if unmoved**

If the rate on the fire builds (`aerosol+candles`) is essentially unchanged, note in the ledger that register is NOT the lever for fire content — the property itself is the ceiling — and the remaining levers are model swap or accepting those builds as deterministic-only. Do not begin either here.

---

## Self-Review

**Spec coverage:**
- All 8 items rewritten, cartoon register, hooks preserved → Task 1 Step 1 (verbatim). ✓
- 4 each, obvious-first ordering → the block as written. ✓
- "bristles" retained; only `_ITEMS` touched → Task 1 Step 1 + Global Constraints. ✓
- Delivery hooks intact (swing/spray/air/throw) → present in the rewritten text. ✓
- Tests stay green → Task 1 Steps 2–3. ✓
- Live validation + spread read + record → Task 2. ✓
- Ceiling caveat → Task 2 Step 4. ✓

**Placeholder scan:** Full replacement block given verbatim; commands have expected output. No TBD/TODO. ✓

**Consistency:** The `_ITEMS` block keeps all 8 original names (so `DELIVERY_LOCK`/`COLOR_BY_ITEM`/`DEFAULT_BUILDS` keys still resolve) and the `Item(name, [associations])` shape. `associations[0]` remains the obvious reading for every item (fallback quotes it). ✓
