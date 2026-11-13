# Writer guide: teacher data for "This Is Not A Weapon"

You are the **teacher** for Forge, the small local model behind `python -m resolver.serve --forge`
(see `docs/FORGE.md`). Players craft absurd gadgets from junk; your readings become the training data
the model learns from. Every line you write teaches it, so quality and variety matter.

Work from a checkout of this repo. Treat everything except your own crafts file as read-only.

## Read these first (in full)
1. **Your system prompt:** `resolver/prompts/bake_prompt.txt` . This is exactly what
   the game's bake pipeline tells its LLM teacher. Follow it: three readings per build (shallow,
   medium, deep), properties traced honestly, composition over invention, honest non-attacks, the
   coherence rule, the target rules, naming rules and magnitudes as proportions.
2. **The vocabulary:** `docs/CAPABILITY_CONTRACT_v1.md` . It lists the deliveries,
   effect kinds, targets and triggers, and the SELF-chassis trigger rules.
3. **Do not open** anything under `data/bake/` . That is the held-out evaluation set.

## Your input
Each line of your combos file has a `combo_id`, the `slots`, the locked delivery `form`, and a
`prompt`. **The `prompt` is the exact user message the bake pipeline would send.** It lists each
item's association cloud and the locked form. Answer it the way the bake prompt asks.

## Your output: one JSON object per line
```json
{"combo_id": "<copy exactly>", "scaffolds": {"SHALLOW": <draft>, "MEDIUM": <draft>, "DEEP": <draft>}}
```
Each `<draft>` follows the game's `GadgetDraft` schema:
```json
{"name": "...", "description": "...", "logic": "...",
 "stages": [{"trigger": "ON_HIT", "note": "",
             "effects": [{"kind": "DAMAGE", "target": "STRUCK", "amount": 10, "duration": 0, "radius": 0, "count": 0, "note": ""}]}]}
```

### Project defaults that differ from the bake prompt
- **`logic`:** a *short* trace, 1–2 sentences and 5–45 words, saying which property of which object
  drives the reading. Do the full thinking yourself, but write only the gist.
- **`note` fields:** always `""` (stage notes and effect notes). They are not used.
- **`description`:** one line, 8–40 words of flavor the player reads.
- **`name`:** 1–5 words, at most 40 characters, and different for each of the three readings.
  - No mechanic words: not "Snare Launcher", not names built on effect kinds.
  - Vary the patterns across the shard: evocative two-word names, "The ___", puns, portmanteaus,
    mock product names, character names.

### Hard rules (the validator enforces these)
- Exact enum tokens only. Every effect has `kind`, `target`, `amount`, `duration`, `radius`,
  `count` and `note`.
- Each reading has 1–4 stages, and each stage has 1–4 effects. Amounts, durations and radii are
  modest proportions (0–1000). `count` is an integer from 0 to 8.
- **The weapon must actually fire.** These are the triggers the game's renderer fires for each
  locked form. Every reading needs at least one stage on one of them:

  | Locked form | Triggers that fire |
  |---|---|
  | `PLACED` | `ON_TRIGGER` (the trap goes off) |
  | `GUARD` | `ON_USE`, `ON_BLOCK` |
  | `SELF`, `DASH` | `ON_USE` (`ON_HIT` only on protective gear; see below) |
  | everything else (melee, guns, sprays, beams, thrown, lobbed, projectile) | `ON_USE`, `ON_HIT`, `ON_IMPACT` |

  `ON_KILL` and `ON_EXPIRE` are legal *extra* stages; they're great in deep readings. They can't be
  a reading's only trigger.
- **SELF-chassis trigger semantics** (contract v1; the game's repair code would otherwise rewrite
  your draft):
  - On a `SELF` form, `ON_IMPACT`, `ON_TRIGGER` and `ON_BLOCK` are illegal.
  - `ON_HIT` means "when *you* get hit" and is only legal if the chassis item is protective
    gear (the firefighter turnout coat).
  - Effects in `ON_USE`, `ON_EXPIRE` and `ON_KILL` stages must target `SELF`.
- Each draft must resolve through the game's own `clamp.apply`. The validator runs it.
- Shard-wide: no duplicate descriptions, and at most 3% duplicate names.

### Soft rules (warnings)
- Coherence: `PIERCE` or `CHAIN` only on something that also deals damage (`DAMAGE`, `BURN`,
  `EXPLODE`, `SUMMON`).
- SHALLOW should not be more complex than DEEP. The three readings should differ in
  *interpretation*, not just in how many stages they have.

## Reference example (from the game's own system prompt, adapted to this format)
```jsonl
{"combo_id": "d:baseball bat|dmg:-|u:-|m:car battery", "scaffolds": {"SHALLOW": {"name": "Warm-Up Swing", "description": "A baseball bat with a battery duct-taped on for no good reason.", "logic": "A bat is a bat; the taped-on battery is just dead weight, so it swings like any bat.", "stages": [{"trigger": "ON_HIT", "note": "", "effects": [{"kind": "DAMAGE", "target": "STRUCK", "amount": 8, "duration": 0, "radius": 0, "count": 0, "note": ""}]}]}, "MEDIUM": {"name": "Jump Start", "description": "The battery rides the barrel with its terminals bared, so every clean hit lands with a jolt that locks the target up for a beat.", "logic": "The battery holds a charge that arcs across a gap; strapped at the sweet spot, the charge rides the contact into whoever gets hit.", "stages": [{"trigger": "ON_HIT", "note": "", "effects": [{"kind": "DAMAGE", "target": "STRUCK", "amount": 10, "duration": 0, "radius": 0, "count": 0, "note": ""}, {"kind": "STAGGER", "target": "STRUCK", "amount": 3, "duration": 1.0, "radius": 0, "count": 0, "note": ""}]}]}, "DEEP": {"name": "Overtime", "description": "A slugger's bat wired to a dying battery, still swinging like it's got one more inning in it.", "logic": "Acid-slick terminals bite on contact, the battery's dead weight rides the bat's springy rebound, and the leftover charge arcs onward when a target drops.", "stages": [{"trigger": "ON_HIT", "note": "", "effects": [{"kind": "DAMAGE", "target": "STRUCK", "amount": 22, "duration": 0, "radius": 0, "count": 0, "note": ""}, {"kind": "KNOCKBACK", "target": "STRUCK", "amount": 140, "duration": 0, "radius": 0, "count": 0, "note": ""}]}, {"trigger": "ON_KILL", "note": "", "effects": [{"kind": "CHAIN", "target": "STRUCK", "amount": 10, "duration": 0, "radius": 0, "count": 2, "note": ""}]}]}}}
```

## Process
- **Write every reading yourself.** No code that generates names, descriptions, logic or stage
  compositions: no templates, random choices or loops. Scripts may only append text you wrote, run
  the validator and count lines. Code-generated content is detectable and gets thrown away.
- Work in batches of about 10 combos, which is 30 readings. Append them to your crafts file, then
  run the validator and fix every error before the next batch:
  `python -m forge.validate_data <your crafts file>`
- You're done when the same command with `--final` exits with 0 errors.
- Touch only your own crafts file. Don't commit, and don't modify anything else in the repo.
