# Playground Solo Cards + Chassis Eligibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The playground's delivery picker offers every eligible chassis (grouped mechanisms vs. containers & junk) and shows any picked item's solo base-use card instantly.

**Architecture:** `catalog_payload` gains four per-item fields (`chassis`, `mechanism`, `form`, `solo` — the solo card precomputed via `resolve_solo` in the roll-result dict shape); the embedded page consumes them with two `<optgroup>`s and a solo-card panel that reuses the existing `card()` renderer. No new endpoints; `/api/roll` untouched.

**Tech Stack:** Python 3.13 stdlib (`http.server`), vanilla JS in the embedded page, pytest.

**Spec:** `docs/superpowers/specs/2026-07-14-playground-solo-and-chassis-design.md`

## Global Constraints

- Scope is `resolver/serve.py` and `tests/test_serve.py` ONLY. Zero changes to the resolver core, contract enums, `/api/roll` semantics, or the harness.
- The existing `delivery` payload field keeps its craft-form-only meaning (`tests/test_serve.py` pins `by_name["jerrycan of gasoline"]["delivery"] is None` — must stay).
- Solo cards are computed per catalog request; no caching.
- Keep the suite green at every commit. Baseline **238 passed**; Task 1 brings it to **240**.
- Run tests with: `python -m pytest -q` from the repo root.
- Commit per task, conventional messages, ending with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Do NOT touch or stage `docs/CAPABILITY_CONTRACT_v0.md`, `hello.md`, or the 2026-07-10 plan/spec files (intentionally uncommitted).

---

### Task 1: Payload fields (`chassis`, `mechanism`, `form`, `solo`)

**Files:**
- Modify: `resolver/serve.py` (imports + `catalog_payload`, lines ~16-39)
- Test: `tests/test_serve.py`

**Interfaces:**
- Consumes: `resolver.solo.resolve_solo(item) -> ResolvedGadget` (existing), `serve.gadget_to_dict(resolved, source) -> dict` (existing).
- Produces: per-item payload keys `chassis: bool`, `mechanism: bool`, `form: str | None`, `solo: dict | None` — consumed by Task 2's page JS.

- [ ] **Step 1: Write the failing tests**

In `tests/test_serve.py`, add `import json` to the top imports (first line, before `import pytest`), then append:

```python
def test_catalog_payload_exposes_chassis_eligibility_and_solo_cards():
    payload = serve.catalog_payload()
    by_name = {item["name"]: item for item in payload["items"]}

    jerrycan = by_name["jerrycan of gasoline"]
    assert jerrycan["chassis"] is True
    assert jerrycan["mechanism"] is False
    assert jerrycan["form"] == "THROWN"
    solo = jerrycan["solo"]
    assert solo["source"] == "solo" and solo["tier"] == "DUD"
    assert [s["trigger"] for s in solo["stages"]] == ["ON_IMPACT", "ON_TRIGGER"]

    ammo = by_name[".22 rounds"]
    assert ammo["chassis"] is False
    assert ammo["solo"] is None and ammo["form"] is None

    crowbar = by_name["crowbar"]
    assert crowbar["mechanism"] is True and crowbar["form"] == "SWING"
    assert [s["trigger"] for s in crowbar["solo"]["stages"]] == ["ON_HIT"]


def test_catalog_payload_is_json_serializable():
    json.dumps(serve.catalog_payload())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_serve.py -q`
Expected: the first new test FAILS with `KeyError: 'chassis'`; the serializability test passes (current payload is already serializable).

- [ ] **Step 3: Implement the payload fields**

In `resolver/serve.py`, add to the imports (after the `resolver.items` import):

```python
from resolver.solo import resolve_solo
```

Replace the body of `catalog_payload` with:

```python
def catalog_payload() -> dict:
    """The catalog the page needs to build its slot pickers."""
    items = []
    for name, item in CATALOG.items():
        form = item.delivery or (item.base_use.delivery if item.base_use else None)
        items.append({
            "name": name,
            "associations": item.describe().split(", "),
            "delivery": item.delivery.value if item.delivery is not None else None,
            "chassis": form is not None,
            "mechanism": item.delivery is not None,
            "form": form.value if form is not None else None,
            "solo": gadget_to_dict(resolve_solo(item), "solo") if item.base_use else None,
            "color": _color_for(name),
        })
    return {"items": items, "tiers": [t.value for t in Tier]}
```

(`gadget_to_dict` is defined later in the module; module-level call order is fine at runtime.)

- [ ] **Step 4: Run the full suite**

Run: `python -m pytest -q`
Expected: 240 passed.

- [ ] **Step 5: Commit**

```bash
git add resolver/serve.py tests/test_serve.py
git commit -m "feat: catalog payload exposes chassis eligibility + solo cards

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Page UI — grouped chassis picker + solo card on pick

All changes are inside the `PAGE` string in `resolver/serve.py`. No Python-logic changes, so the pytest count stays 240; verification is the suite plus an HTTP smoke check.

**Files:**
- Modify: `resolver/serve.py` (the `PAGE` string: CSS block, panel HTML, `load()`, new `showSolo()`, `card()`)

**Interfaces:**
- Consumes: payload keys `chassis`, `mechanism`, `form`, `solo` (Task 1) and the existing `card(g)` / `opt(v, label)` JS helpers.
- Produces: nothing consumed by later tasks (final task).

- [ ] **Step 1: Add the solo badge CSS**

In the `PAGE` CSS block, directly after the `.fb { ... }` rule, add:

```css
  .sb { color: #9cc4ff; border-color: #2a3f66; }
```

- [ ] **Step 2: Add the solo panel container**

In the panel HTML, directly after `<div id="assoc"></div>`, add:

```html
    <div id="solo"></div>
```

- [ ] **Step 3: Group the delivery picker and wire solo previews**

In `load()`, replace these two lines:

```js
  const deliveries = data.items.filter(i => i.delivery);
  $('delivery').append(...deliveries.map(i => opt(i.name, i.name + '  (' + i.delivery + ')')));
```

with:

```js
  const groups = [
    ['mechanisms', data.items.filter(i => i.mechanism)],
    ['containers & junk', data.items.filter(i => i.chassis && !i.mechanism)],
  ];
  for (const [label, items] of groups) {
    const g = document.createElement('optgroup'); g.label = label;
    g.append(...items.map(i => opt(i.name, i.name + '  (' + i.form + ')')));
    $('delivery').append(g);
  }
```

Replace the four `onchange` assignments and the trailing `showAssoc();` call:

```js
  $('delivery').onchange = showAssoc; $('damage').onchange = showAssoc;
  $('utility').onchange = showAssoc; $('modifier').onchange = showAssoc;
  showAssoc();
```

with:

```js
  for (const slot of ['delivery','damage','utility','modifier']) {
    $(slot).onchange = () => { showAssoc(); showSolo(slot); };
  }
  showAssoc();
  showSolo('delivery');
```

- [ ] **Step 4: Add `showSolo` and the solo source badge**

Directly after the `showAssoc()` function, add:

```js
function showSolo(slot) {
  const byName = Object.fromEntries(CATALOG.items.map(i => [i.name, i]));
  const name = $(slot).value;
  const el = $('solo');
  if (!name) { el.innerHTML = ''; return; }
  const it = byName[name];
  el.innerHTML = '<label>solo — as found</label>' +
    (it.solo ? card(it.solo) : '<div class="hint">(no solo use — ammunition)</div>');
}
```

In `card(g)`, directly after the `if (g.source === 'fallback') ...` line, add:

```js
  if (g.source === 'solo') badges.push('<span class="badge sb">solo</span>');
```

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -q`
Expected: 240 passed (page string changes don't alter Python behavior).

- [ ] **Step 6: HTTP smoke check**

Run (bash, from repo root):

```bash
python -m resolver.serve --fallback --port 8123 &
sleep 2
curl -s localhost:8123/api/catalog | python -c "import json,sys; d=json.load(sys.stdin); i={x['name']:x for x in d['items']}['jerrycan of gasoline']; print(i['chassis'], i['form'], i['solo']['tier'])"
curl -s localhost:8123/ | grep -c 'containers & junk'
kill %1
```

Expected output: `True THROWN DUD` then `1`. (The server prints its own two startup lines; ignore them.)

- [ ] **Step 7: Commit**

```bash
git add resolver/serve.py
git commit -m "feat: playground picks substance chassis and shows solo cards

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
