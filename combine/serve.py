"""Local HTTP bridge so a game engine can call the combine brain.

Godot (or any client) POSTs a filled slot grid; this returns the compiled gadget
dict (`compile.to_engine`) the engine can execute directly. The brain stays in
Python — portable and tested — and the engine is a thin renderer.

    POST /resolve
    {"delivery":"bear_trap","damage":"beehive","utility":"fireworks",
     "modifier":"dry_ice","awakening":1.0}
    -> 200 {name, description, delivery, effects[], homing, harmless,
            projectile_speed, color, logic, stage_count}

Run:  python -m combine.serve
Uses .anthropic_key / ANTHROPIC_API_KEY for Sonnet; deterministic if no key.
Ctrl-C to stop.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from .compile import to_engine
from .eval import _make_client
from .grammar import Build
from .items import CATALOG, SLOTS
from .lucidity import Awakening
from .resolver import resolve

PORT = 8777
_CLIENT: object | None = None


def _resolve_request(req: dict) -> dict:
    kw = {}
    for slot in SLOTS:
        iid = req.get(slot)
        if iid:
            if iid not in CATALOG:
                raise ValueError(f"unknown item {iid!r} in slot {slot!r}")
            kw[slot] = CATALOG[iid]
    build = Build(**kw)
    awakening = Awakening(float(req.get("awakening", 1.0)))
    gadget = resolve(build, awakening, client=_CLIENT)
    out = to_engine(gadget)
    out["logic"] = gadget.logic
    out["category"] = gadget.category.value
    out["stage_count"] = len(gadget.stages)
    return out


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.dumps(_resolve_request(json.loads(raw))).encode("utf-8")
            self._send(200, payload)
        except Exception as exc:  # noqa: BLE001 - report every failure to the client
            self._send(500, json.dumps({"error": str(exc)}).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802 - a health check for "is the bridge up?"
        self._send(200, json.dumps({"ok": True}).encode("utf-8"))

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # quiet the per-request stderr spam
        return


def main() -> int:
    global _CLIENT
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _CLIENT = _make_client(False)
    where = "Sonnet (BYOK)" if _CLIENT is not None else "deterministic"
    print(f"combine brain serving on http://127.0.0.1:{PORT}  ({where})")
    print("POST /resolve with a slot grid. Ctrl-C to stop.")
    try:
        HTTPServer(("127.0.0.1", PORT), _Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
