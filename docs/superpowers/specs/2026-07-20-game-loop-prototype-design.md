# Game-Loop Prototype with In-Game On-Demand Generation — Design

**Date:** 2026-07-20
**Status:** Approved (brainstorm complete)
**Depends on:** `docs/GAME_IDENTITY.md` (§3 loop, §9 constraints, §10 vertical slice),
`docs/CAPABILITY_CONTRACT_v1.md` + `resolver/contract.py` (the enum vocabulary and
`contract_fingerprint`), `resolver/serve.py` / `resolver/llm.py` / `resolver/fallback.py`
(the runtime surface), the deferred fallback PLACED-chassis finding
(`docs/HANDOFF.md` 2026-07-20, `.superpowers/sdd/progress.md`).

## Why

The resolver pipeline is proven offline (168 committed gadgets, pre30 wave). The next
risk is the game: does the jack-in loop hold up with real generated weapons in a real
engine? The user's direction: start the prototype now, and during testing generate
weapons **in-game on demand** (live resolver at craft time) instead of pre-baking —
cheaper while iterating, since a play session crafts dozens of combos, not thousands.

**Invariant framing (explicit):** live-LLM-in-the-hot-path is a *dev-mode testing
convenience*, not a change of shipping architecture. GAME_IDENTITY §6 stands: shipped
acquisition draws from pre-baked frozen instances; the live model explores the
frontier. When the prototype works, pre-baking resumes as the source of instances.
Nothing in this design may create a structural dependency on the live path — the
deterministic fallback keeps the game fully functional with no API key.

## Decisions (settled in brainstorm)

- **Form:** the real GAME_IDENTITY §10 vertical slice in Unreal — blockout, not a
  throwaway 2D/text prototype.
- **Engine:** UE 5.x (already installed).
- **Authoring split:** C++ core + Blueprint glue. Gameplay systems, authority logic,
  and the resolver client are C++ (agent-authorable, diffable); Blueprints are thin
  in-editor wiring only.
- **Repo layout:** UE project lives in `game/` in this repo, next to `resolver/`,
  with a proper UE `.gitignore` (exclude `Binaries/`, `Intermediate/`,
  `DerivedDataCache/`, `Saved/`). Game and contract version in lockstep.
- **Craft mode:** live LLM with deterministic fallback on failure/refusal/keylessness.
  This approves per-craft API spend during the user's play sessions — and only that.
  Bake/dedup spend stays HELD.
- **Finish line ("prototype working"):** the loop functions end-to-end in a blockout
  zone — move, scavenge junk, craft via the live resolver, the weapon visibly does
  what its JSON says, extract (roll banked) or die (roll lost). **No bot threat
  required for this finish line**; the §10 fun-gate slice builds on it next.
- **Integration approach:** local HTTP sidecar + generic gadget interpreter (chosen
  over craft-ahead batching and over porting/embedding the resolver in-engine, which
  would duplicate balance code and break engine-agnosticism).

## Architecture

Two processes, one contract:

```
Unreal game (game/, UE 5.x C++)                Python resolver sidecar
┌─────────────────────────────┐                ┌──────────────────────────┐
│ client pawn(s)              │                │ resolver/serve.py        │
│   │ replicated              │   POST /craft  │   /craft endpoint        │
│ game server (listen host) ──┼───────────────▶│   LLMResolver (if key)   │
│   ResolverClient (async)    │◀───────────────│   fallback (always)      │
│   GadgetInterpreter         │  gadget JSON   │   clamp + re-derive +    │
│   Run state                 │                │   validate               │
└─────────────────────────────┘                └──────────────────────────┘
        startup: GET fingerprint ──▶ compare to compiled-in mirror
```

- The game **server** (listen host, `HasAuthority` from line one) owns all resolver
  traffic; clients never call the sidecar.
- At startup the game fetches `contract_fingerprint` from the sidecar and compares
  it to the fingerprint its C++ enum mirror was built against. Mismatch → loud
  on-screen error, refuse to craft. Never silent drift.
- Craft flow: pick up junk → craft spot → select items → request → heads-down
  window while the call runs (1–5s live, near-instant fallback; the latency lands
  inside the exposed-crafting moment, which is diegetically correct) → weapon
  spawns → fire → extract or die.

## Resolver side (Python)

1. **Fallback PLACED-chassis fix (lands first).** `fallback._stages_for` keys
   delivery-less chassis stages off `base_use.delivery` — THROWN → existing burst
   shape, PLACED → ON_TRIGGER — mirroring `resolver/solo.py`'s discrimination, plus
   a pin test for the steaks-as-chassis case. On-demand crafting puts the fallback
   in the live path; an ON_IMPACT-only PLACED gadget that can never fire would be a
   dead weapon handed to the player mid-run.
2. **`POST /craft` endpoint** in `serve.py`. Request: `{items: [names],
   tier_target, seed?}`. Reuses the existing pipeline: `LLMResolver` with the
   sonnet→opus retry ladder when a key is present; `fallback` when keyless or when
   the live call fails/refuses; then clamp, re-derive `harmless`/`category`,
   validate. Response: the gadget JSON plus `source: live | fallback`. One craft =
   one resolve — no best-of-N in the hot path (that is bake-time machinery; a
   prototype craft is a single roll).
3. **Craft-mode config:** none added. Key present = live-with-fallback; key absent
   = fallback-only. No third mode until testing demands one.

Standing rules carried in unchanged: refusals are **counted, never introspected** —
`source` and rates only, no stop reasons or exception text anywhere. API key is
presence-checked, never printed. Live runs on Windows need `PYTHONUTF8=1`. The
resolver stays engine-agnostic: zero Unreal references in Python.

## Unreal side (C++ components)

UE 5.x C++ project in `game/`, first-person template base. One class (or small
cluster) per component:

- **Contract mirror** — hand-written UENUMs for delivery/effect/trigger/category,
  structs matching the gadget JSON, and the fingerprint constant they were built
  against. The one file that must move in lockstep with `resolver/contract.py`;
  the startup fingerprint check catches it when it doesn't.
- **ResolverClient** — async wrapper over `FHttpModule`:
  `Craft(items, tierTarget) → delegate(parsed gadget | error)`. Server-only.
  Sidecar URL configurable, default `127.0.0.1:8765`; `game/run-sidecar.ps1`
  starts the Python server for dev.
- **GadgetInterpreter** — the heart: takes a parsed gadget and spawns a weapon
  actor whose behavior is data-driven. Delivery form decides the fire action
  (projectile / thrown arc / placed / self-applied); stages bind to their triggers
  (impact / trigger / use / hit); effect primitives execute at blockout grade —
  damage numbers, simple radial volumes, debug particles, floating text for
  anything without a visual yet. Ugly is fine; **legible is the bar**: you should
  see the JSON happening.
- **Junk pickups** — pickup actor carrying a catalog item name + a simple
  inventory. A handful of hand-placed items in the blockout zone to start; spawn
  tables later.
- **Craft interaction** — a craft spot: choose items from inventory, commit,
  locked into the heads-down window until the response lands, weapon spawns in
  hand. Items are consumed only on a successful craft.
- **Run state** — jack in → play → reach the extract volume (gadget JSON appended
  to a local `extracted.jsonl`, the prototype's signature bank) or die (nothing
  banked). Restart loop.

All gameplay mutations behind `HasAuthority`. Weapon *feel* beyond "it visibly
works" is explicitly not chased in this effort (GAME_IDENTITY §9: feel is
human-owned, play-tuned).

## Error handling

- **Sidecar down/unreachable:** craft spot shows "sim unresponsive"; the craft
  neither consumes items nor locks the player. The game never crashes or hangs on
  resolver absence.
- **Live call fails/refuses:** handled server-side — fallback serves the craft.
  In-game you always get a weapon (§6: every craft succeeds). The only trace is
  `source: fallback`.
- **Malformed JSON reaching the game:** treated as sidecar-down (reject craft,
  release player, log), never a crash. Server-side validation makes this a
  should-never-happen.
- **Timeout:** client-side cap ~20s (covers the full retry ladder), after which
  the craft resolves as sidecar-down.
- **Spend guard:** live calls only during the user's play sessions against their
  local key. No schedules, no batches, no CI. Bake/dedup spend stays HELD.

## Testing

Per the standing split — TDD the brain, play-tune the feel:

- **Python (TDD, red-green):** pin test for the PLACED-chassis fix; `/craft`
  endpoint tests exercising fallback mode end-to-end with no key and no network —
  request → valid contract JSON, `source` field, item-name validation, error
  shapes. The live path gets a hand-run smoke script, never a suite test (no API
  calls in tests, ever).
- **Unreal:** no test framework for the prototype. Verification is a written
  manual checklist per milestone (e.g. "craft with sidecar stopped → items kept,
  message shown") plus the fingerprint check as a permanent runtime guard. C++
  unit scaffolding only if the interpreter grows hairy — YAGNI.
- **Feel:** explicitly untested; the finish line is "loop functions," play-judged
  by the user.

## Out of scope

Bot threat / the §10 fun-gate play-test (next effort, builds on this), pre-baking
and everything bake-side (pilot stays HELD), best-of-N or tier-ladder derivation in
the hot path, the economy/blueprints/boosters, neutrals, the hub, the radial
gradient, spawn tables, art or feel polish, contract changes (enums never widen),
any new Unreal-side generation logic (the game renders what the resolver returns —
code owns numbers, and that code is Python).
