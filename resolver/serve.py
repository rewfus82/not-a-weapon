"""A tiny local web UI for playing with the resolver: assemble a junk build,
pick a target tier, and roll resolved weapons in the browser. Zero-dependency
(stdlib http.server). Live by default (uses your API key, with retries +
Opus escalation); pass --fallback for the free deterministic resolver.

This is a consumer of the resolver brain, like the CLI harness — not part of
the engine-agnostic core.
"""
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from resolver.bake.schema import contract_fingerprint
from resolver.clamp import apply as clamp_apply
from resolver.contract import Tier
from resolver.fallback import resolve as fallback_resolve
from resolver.harness import DEFAULT_ESCALATE_MODEL, DEFAULT_MODEL, _label_models, build_model_list
from resolver.items import CATALOG, Build
from resolver.solo import resolve_solo

# ---------------------------------------------------------------- pure helpers


def _color_for(name: str) -> str:
    return "grey"


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


def build_from_request(sel: dict) -> Build:
    """Assemble a Build from a slot->item-name mapping. Raises ValueError with a
    human message on a missing/invalid delivery or an unknown item."""
    def pick(slot: str):
        name = sel.get(slot)
        if not name:
            return None
        if name not in CATALOG:
            raise ValueError(f"unknown item: {name!r}")
        return CATALOG[name]

    delivery_item = pick("delivery")
    if delivery_item is None:
        raise ValueError("a delivery item is required")
    if delivery_item.delivery is None and delivery_item.base_use is None:
        raise ValueError(f"{delivery_item.name!r} cannot be a delivery chassis")
    return Build(
        delivery_item=delivery_item,
        damage_item=pick("damage"),
        utility_item=pick("utility"),
        modifier_item=pick("modifier"),
    )


def gadget_to_dict(resolved, source: str) -> dict:
    d = resolved.draft
    return {
        "source": source,
        "name": d.name,
        "description": d.description,
        "logic": d.logic,
        "tier": resolved.tier.value,
        "category": resolved.category.value,
        "harmless": resolved.harmless,
        "delivery": resolved.delivery.value,
        "color": resolved.color,
        "stages": [
            {
                "trigger": s.trigger.value,
                "note": s.note,
                "effects": [
                    {"kind": e.kind.value, "target": e.target.value, "amount": e.amount,
                     "duration": e.duration, "radius": e.radius, "count": e.count,
                     "note": e.note}
                    for e in s.effects
                ],
            }
            for s in d.stages
        ],
    }


def _resolve_once(resolver_fn, build: Build, tier: Tier):
    """(source, ResolvedGadget). A refused/failed live call degrades to the
    deterministic fallback — the same shock absorber the harness uses."""
    try:
        draft = resolver_fn(build, tier)
        source = "llm"
    except Exception:  # noqa: BLE001 - any resolver failure -> deterministic fallback
        draft = fallback_resolve(build, tier)
        source = "fallback"
    return source, clamp_apply(draft, build, tier)


def roll(resolver_fn, build: Build, tier: Tier, n: int) -> list[dict]:
    """The n rolls are independent resolver calls; run them concurrently so
    n live rolls cost roughly one roll of wall-clock. Results stay in slot
    order (executor.map preserves it)."""
    n = max(1, n)

    def one(_: int) -> dict:
        source, resolved = _resolve_once(resolver_fn, build, tier)
        return gadget_to_dict(resolved, source)

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(one, range(n)))


# ---------------------------------------------------------------- HTTP server


class PlayServer(ThreadingHTTPServer):
    def __init__(self, addr, handler, resolver_fn, mode_label):
        super().__init__(addr, handler)
        self.resolver_fn = resolver_fn
        self.mode_label = mode_label


class PlayHandler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, status: int = 200) -> None:
        self._send(json.dumps(obj).encode("utf-8"), "application/json", status)

    def do_GET(self):  # noqa: N802
        if self.path == "/" or self.path.startswith("/?"):
            self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path == "/api/catalog":
            self._json({**catalog_payload(), "mode": self.server.mode_label})
        elif self.path == "/api/contract":
            self._json({"fingerprint": contract_fingerprint()})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):  # noqa: N802
        if self.path != "/api/roll":
            self._json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw or b"{}")
            build = build_from_request(payload.get("slots", {}))
            tier = Tier(payload.get("tier", "COMMON"))
            n = min(4, max(1, int(payload.get("rolls", 1))))
            self._json({"results": roll(self.server.resolver_fn, build, tier, n)})
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001 - surface any server error as JSON
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def log_message(self, *args):  # quiet console
        pass


def _make_resolver(use_fallback: bool, model: str, attempts: int, escalate):
    if use_fallback or not os.environ.get("ANTHROPIC_API_KEY"):
        return fallback_resolve, "fallback (free)"
    import anthropic  # lazy: the fallback path needs no SDK auth

    from resolver.llm import LLMResolver

    models = build_model_list(model, attempts, escalate)
    return LLMResolver(anthropic.Anthropic(), models).resolve, f"LIVE ({_label_models(models)})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local web UI for rolling resolved weapons.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default=os.environ.get("RESOLVER_MODEL", DEFAULT_MODEL))
    parser.add_argument("--attempts", type=int, default=3,
                        help="live attempts per roll before the deterministic fallback (default 3)")
    parser.add_argument("--escalate-model", default=DEFAULT_ESCALATE_MODEL,
                        help="model for the final attempt; 'none' disables escalation")
    parser.add_argument("--fallback", action="store_true",
                        help="use the free deterministic resolver instead of the live LLM")
    args = parser.parse_args(argv)

    escalate = None if args.escalate_model.lower() == "none" else args.escalate_model
    resolver_fn, label = _make_resolver(args.fallback, args.model, args.attempts, escalate)
    server = PlayServer((args.host, args.port), PlayHandler, resolver_fn, label)
    url = f"http://{args.host}:{args.port}"
    print(f"resolver: {label}")
    print(f"play at:  {url}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.server_close()
    return 0


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>This Is Not A Weapon — resolver playground</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 15px/1.5 ui-sans-serif, system-ui, sans-serif;
         background: #14161a; color: #e7e9ee; }
  header { padding: 16px 20px; border-bottom: 1px solid #262a31; }
  header h1 { margin: 0; font-size: 17px; letter-spacing: .02em; }
  #mode { font-size: 12px; margin-top: 4px; }
  #mode.live { color: #ffb454; } #mode.free { color: #7d8590; }
  main { display: grid; grid-template-columns: 300px 1fr; gap: 0; align-items: start; }
  @media (max-width: 720px) { main { grid-template-columns: 1fr; } }
  .panel { padding: 18px 20px; border-right: 1px solid #262a31; position: sticky; top: 0; }
  label { display: block; font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
          color: #8b93a1; margin: 12px 0 4px; }
  select, button, input { width: 100%; padding: 8px 10px; border-radius: 8px;
          border: 1px solid #303640; background: #1b1e24; color: #e7e9ee; font: inherit; }
  .row { display: flex; gap: 8px; }
  .row > * { flex: 1; }
  button.roll { margin-top: 16px; background: #2f6feb; border-color: #2f6feb; color: #fff;
          font-weight: 600; cursor: pointer; }
  button.roll:hover { background: #3b7bff; }
  button.roll:disabled { opacity: .5; cursor: default; }
  #assoc { margin-top: 14px; font-size: 12px; color: #7d8590; }
  #assoc b { color: #aab2c0; font-weight: 600; }
  #results { padding: 18px 20px; display: grid; gap: 14px; }
  .card { border: 1px solid #2b303a; border-radius: 12px; padding: 14px 16px; background: #171a20; }
  .meta { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #8b93a1;
          display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .tier { font-weight: 700; color: #e7e9ee; }
  .badge { padding: 1px 7px; border-radius: 999px; border: 1px solid #333a45; }
  .harm { color: #64d19a; border-color: #24503b; }
  .weap { color: #ff8a6a; border-color: #5a2a1e; }
  .fb { color: #ffb454; border-color: #5a4420; }
  .sb { color: #9cc4ff; border-color: #2a3f66; }
  .name { font-size: 19px; font-weight: 700; margin: 6px 0 2px; }
  .logic { color: #b6bdc9; font-style: italic; margin: 4px 0 10px; }
  .stage { margin: 6px 0; }
  .trig { font-size: 12px; color: #7d8590; text-transform: uppercase; letter-spacing: .05em; }
  .fx { padding-left: 14px; }
  .kind { color: #9cc4ff; font-weight: 600; }
  .num { color: #8b93a1; }
  .fxnote { color: #cfd6e2; }
  .err { color: #ff8a6a; }
  .hint { color: #7d8590; }
</style></head>
<body>
<header>
  <h1>This Is Not A Weapon — resolver playground</h1>
  <div id="mode">loading…</div>
</header>
<main>
  <div class="panel">
    <label for="delivery">Delivery (chassis)</label>
    <select id="delivery"></select>
    <label for="damage">Damage</label>
    <select id="damage"></select>
    <label for="utility">Utility</label>
    <select id="utility"></select>
    <label for="modifier">Modifier</label>
    <select id="modifier"></select>
    <div class="row">
      <div><label for="tier">Tier</label><select id="tier"></select></div>
      <div><label for="rolls">Rolls</label>
           <select id="rolls"><option>1</option><option>2</option><option>3</option><option>4</option></select></div>
    </div>
    <button class="roll" id="roll">Roll</button>
    <div id="assoc"></div>
    <div id="solo"></div>
  </div>
  <div id="results"><div class="hint">Pick a delivery item and hit Roll.</div></div>
</main>
<script>
let CATALOG = null;
const $ = id => document.getElementById(id);

function opt(v, label) { const o = document.createElement('option'); o.value = v; o.textContent = label; return o; }

async function load() {
  const data = await (await fetch('/api/catalog')).json();
  CATALOG = data;
  const modeEl = $('mode');
  const live = /^LIVE/.test(data.mode);
  modeEl.textContent = live ? 'LIVE — each roll uses your API key (up to 3 calls incl. an Opus rescue)'
                            : 'fallback (free) — deterministic, boring, no API calls';
  modeEl.className = live ? 'live' : 'free';

  const groups = [
    ['mechanisms', data.items.filter(i => i.mechanism)],
    ['containers & junk', data.items.filter(i => i.chassis && !i.mechanism)],
  ];
  for (const [label, items] of groups) {
    const g = document.createElement('optgroup'); g.label = label;
    g.append(...items.map(i => opt(i.name, i.name + '  (' + i.form + ')')));
    $('delivery').append(g);
  }
  for (const slot of ['damage','utility','modifier']) {
    $(slot).append(opt('', '(none)'), ...data.items.map(i => opt(i.name, i.name)));
  }
  $('tier').append(...data.tiers.map(t => opt(t, t)));
  $('tier').value = 'LEGENDARY';
  for (const slot of ['delivery','damage','utility','modifier']) {
    $(slot).onchange = () => { showAssoc(); showSolo(slot); };
  }
  showAssoc();
  showSolo('delivery');
}

function showSolo(slot) {
  const byName = Object.fromEntries(CATALOG.items.map(i => [i.name, i]));
  const name = $(slot).value;
  const el = $('solo');
  if (!name) { el.innerHTML = ''; return; }
  const it = byName[name];
  el.innerHTML = '<label>solo — as found</label>' +
    (it.solo ? card(it.solo) : '<div class="hint">(no solo use — ammunition)</div>');
}

function showAssoc() {
  const byName = Object.fromEntries(CATALOG.items.map(i => [i.name, i]));
  const parts = [];
  for (const slot of ['delivery','damage','utility','modifier']) {
    const name = $(slot).value; if (!name) continue;
    const it = byName[name];
    parts.push('<div><b>' + name + '</b> — ' + it.associations.join('; ') + '</div>');
  }
  $('assoc').innerHTML = parts.join('');
}

function fx(e) {
  const bits = ['<span class="kind">' + e.kind + '</span>',
                '<span class="num">@' + e.target + '</span>'];
  const num = [];
  if (e.amount) num.push('a=' + (+e.amount.toFixed(3)));
  if (e.duration) num.push('d=' + (+e.duration.toFixed(2)));
  if (e.radius) num.push('r=' + (+e.radius.toFixed(0)));
  if (e.count) num.push('n=' + e.count);
  if (num.length) bits.push('<span class="num">' + num.join(' ') + '</span>');
  if (e.note) bits.push('<span class="fxnote">“' + e.note + '”</span>');
  return '<div class="fx">' + bits.join(' ') + '</div>';
}

function card(g) {
  const badges = [];
  badges.push('<span class="tier">' + g.tier + '</span>');
  badges.push('<span class="badge">' + g.category + '</span>');
  badges.push('<span class="badge ' + (g.harmless ? 'harm' : 'weap') + '">' + (g.harmless ? 'harmless' : 'lethal') + '</span>');
  badges.push('<span class="badge">' + g.delivery + '</span>');
  if (g.color) badges.push('<span class="badge">' + g.color + '</span>');
  if (g.source === 'fallback') badges.push('<span class="badge fb">fallback</span>');
  if (g.source === 'solo') badges.push('<span class="badge sb">solo</span>');
  const stages = g.stages.map(s =>
    '<div class="stage"><div class="trig">' + s.trigger + '</div>' +
    s.effects.map(fx).join('') + '</div>').join('');
  return '<div class="card"><div class="meta">' + badges.join('') + '</div>' +
         '<div class="name">' + g.name + '</div>' +
         '<div class="logic">' + g.logic + '</div>' + stages + '</div>';
}

async function doRoll() {
  const btn = $('roll'); btn.disabled = true; btn.textContent = 'Rolling…';
  const slots = { delivery: $('delivery').value, damage: $('damage').value,
                  utility: $('utility').value, modifier: $('modifier').value };
  try {
    const res = await fetch('/api/roll', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ slots, tier: $('tier').value, rolls: +$('rolls').value }) });
    const data = await res.json();
    if (data.error) { $('results').innerHTML = '<div class="err">' + data.error + '</div>'; }
    else { $('results').innerHTML = data.results.map(card).join(''); }
  } catch (e) {
    $('results').innerHTML = '<div class="err">' + e + '</div>';
  } finally { btn.disabled = false; btn.textContent = 'Roll'; }
}

$('roll').onclick = doRoll;
load();
</script>
</body></html>
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
