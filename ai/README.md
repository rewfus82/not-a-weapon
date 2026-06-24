# AI combine evaluator

A standalone test harness to prove the AI-driven combine mechanic **before** it's
wired into Godot. Type a combination of junk; Claude Haiku 4.5 **composes** a
gadget out of a fixed vocabulary of effect primitives the engine can execute, and
the harness clamps it for balance.

It does **not** pick from a list of pre-written weapons, and it can't invent a
mechanic the engine can't run. It assembles behavior from building blocks:

```
Gadget = name + description + category + rarity
         + delivery        (projectile | lobbed | hitscan | melee | aura | placed | self)
         + effects[]       (damage, slow, snare, stun, knockback, explode, burn,
                            pierce, bounce, chain, spawn, turret, pull, mark,
                            lifesteal, heal, dash, collect)
```

The richer this primitive set, the more the same items can yield mechanically
distinct weapons rather than reskins.

## Why this exists first

Same philosophy as the graybox: prove the idea is fun/balanced for pennies before
building the integration. If `magnet + beehive + grenade` reliably produces
something delightful *and* in-range, the whole approach is de-risked.

## Run it (BYOK)

You bring your own Anthropic API key — nothing is stored in the repo.

```bash
pip install anthropic pydantic
ANTHROPIC_API_KEY=sk-ant-... python ai/combine_eval.py
```

Then:

```
combine> m16, anchovies
combine> beehive, grenade, magnet
combine> pixie_stix, wire_hanger, zip_ties   # fires, harmlessly
newrun                                       # reshuffle: same items, new results
items                                        # list the junk
quit
```

## How it maps to the design

| Decision | Where |
|---|---|
| Model composes from primitives, doesn't free-form | `Gadget` + `Effect` Pydantic models + `messages.parse(..., output_format=Gadget)` |
| Balance stays ours | `_balance()` clamps effect count + each effect's numbers per rarity |
| Occasional insane weapon | `GLITCH_CHANCE` lifts the caps to the `GLITCHED` tier |
| Per-run reroll (roguelike) | per-run `cache` + `newrun` reseeds the "reality instability signature" |
| BYOK + graceful absence | requires `ANTHROPIC_API_KEY`; in-game, missing/failed key falls back to deterministic `compose()` |

To make weapons feel *more* novel, add primitives to `EffectKind` (and teach them
in the system prompt) — that widens what the AI can compose. To stay balanced, add
their clamp rule in `_balance()`.

## Next step

Once the outputs feel good, port this into Godot: an `HTTPRequest` call to the
same model + schema, the per-run cache, a "the player is figuring it out" spinner
to hide latency, and `scripts/resolver.gd`'s `compose()` as the no-key / offline
fallback.
