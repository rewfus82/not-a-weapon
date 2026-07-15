# Playground: solo cards + chassis eligibility — design

**Date:** 2026-07-14
**Scope:** `resolver/serve.py` and `tests/test_serve.py` only. Zero changes to the resolver core (`items.py`, `solo.py`, `clamp.py`, contract enums), `/api/roll` semantics, or the harness.

## Problem

Two gaps left by the base-use plan, both playground-only:

1. **Chassis eligibility is invisible.** Since `Build.delivery` falls back through `base_use`, any non-ammo item is a valid delivery chassis server-side — but `catalog_payload` exposes only the craft-form `delivery` field, and the page's delivery picker filters on it (`items.filter(i => i.delivery)`). A jerrycan is accepted by `/api/roll` yet impossible to pick in the UI, and the payload gives a UI no way to distinguish a valid substance chassis from invalid ammo (both serialize `delivery: null`).
2. **Solo uses have no affordance.** `resolver/solo.py` resolves every non-ammo item's base use at the DUD floor — deterministic, free, instant — but nothing in the playground shows "what does this item do bare?"

## Design

### 1. Payload: four new per-item fields in `catalog_payload`

Existing fields keep their exact meaning (`delivery` stays craft-form-only; `tests/test_serve.py` pins `by_name["jerrycan of gasoline"]["delivery"] is None`). Each item entry gains:

| field | type | value |
|---|---|---|
| `chassis` | bool | `item.delivery is not None or item.base_use is not None` — may occupy the delivery slot. False only for ammo. |
| `mechanism` | bool | `item.delivery is not None` — has a true craft form. Drives the picker's optgroup split. |
| `form` | str \| null | The delivery form the item locks as a chassis: `item.delivery.value` if set, else `item.base_use.delivery.value`; `null` for ammo. |
| `solo` | dict \| null | The item's resolved solo card: `gadget_to_dict(resolve_solo(item), "solo")` — the same shape as a roll result, so the page reuses its `card()` renderer verbatim. `null` for ammo. |

Solo cards are computed per catalog request (55 pure resolve+clamp calls, sub-millisecond). No caching — `resolve_solo` is deterministic, and the playground is a local single-user tool.

Import addition in `serve.py`: `from resolver.solo import resolve_solo`.

### 2. UI: grouped chassis picker + solo card on pick

**Delivery picker.** Replaces the `i.delivery`-filtered flat list with two `<optgroup>`s over `items.filter(i => i.chassis)`:

- **mechanisms** — `mechanism: true`, labeled `name (FORM)` (unchanged labels, e.g. `crowbar (SWING)`)
- **containers & junk** — `chassis && !mechanism`, labeled `name (FORM)` from the inherited base-use form, e.g. `jerrycan of gasoline (THROWN)`

Ammo (`chassis: false`) appears in neither group (it remains pickable in damage/utility/modifier slots, as today).

**Solo card.** On any slot `change`, the just-picked item's `solo` card renders in the left panel below the associations preview, under a small "solo — as found" label, using the existing `card()` function (it will naturally show the DUD tier badge and stage/effect lines). One card only — the most recent pick; picking `(none)` or an ammo item clears it (ammo shows the hint `(no solo use — ammunition)`). A `source: "solo"` badge reuses the existing badge styling (styled like the `fallback` badge but labeled `solo`).

No new endpoints; no change to `/api/roll`, error handling, or the roll flow.

### 3. Tests (`tests/test_serve.py`)

- jerrycan payload: `chassis is True`, `mechanism is False`, `form == "THROWN"`, `solo` is a two-stage card (`ON_IMPACT` then `ON_TRIGGER`, tier `"DUD"`, `source == "solo"`).
- `.22 rounds`: `chassis is False`, `solo is None`, `form is None`.
- crowbar: `mechanism is True`, `form == "SWING"`, solo card has one `ON_HIT` stage.
- Whole payload survives `json.dumps` (guards enum leakage).
- Existing pins (e.g. craft-form `delivery` semantics, roll guards) stay untouched and green.

The embedded page's JS remains untested, as today (zero-dependency stdlib page; behavior is eyeballed via the CLI smoke run).

## Out of scope

- Rolling a solo use at other tiers (solo is DUD-pinned by design — GAME_IDENTITY: the zero-risk act of picking something up never competes with crafting).
- A full item-browser view; per-slot solo cards for all four slots at once.
- Any resolver-core or contract change.
