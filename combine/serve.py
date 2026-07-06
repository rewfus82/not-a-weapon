"""Local HTTP bridge so a browser console (or a game engine) can drive the combine brain.

Endpoints
    POST /resolve  {delivery,damage,utility,modifier,awakening}
        -> {gadget: <full structured Gadget>, engine: <to_engine flat dict>,
            prompt: {user}, model, source}   (source = "llm" | "deterministic ...")
    GET  /catalog  -> {slots, items[], system}   (populate the console pickers)
    GET  /         -> {ok:true}                   (health check)

CORS is open so a local `file://` console can call it. The brain stays in Python —
portable and tested; every caller is a thin renderer.

Run:  python -m combine.serve
Uses .anthropic_key / ANTHROPIC_API_KEY (BYOK); deterministic floor if no key. Ctrl-C to stop.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_CONSOLE_HTML = Path(__file__).resolve().parent.parent / "tools" / "combine_console.html"

from .compile import to_engine
from .eval import _make_client
from .grammar import Build
from .items import CATALOG, SLOTS
from .llm import MODEL, SYSTEM, build_user_message, llm_resolve
from .lucidity import Awakening
from .resolver import SHAPE, clamp_gadget, deterministic_resolve

PORT = 8777
_CLIENT: object | None = None


def _catalog() -> dict:
    return {
        "slots": list(SLOTS),
        "system": SYSTEM,  # static prompt shown once in the console
        "items": [
            {
                "id": it.id,
                "name": it.name,
                "color": it.color,
                "shape": SHAPE[it.id].value if it.id in SHAPE else None,
                "assoc": [a.text for a in it.associations],
            }
            for it in CATALOG.values()
        ],
    }


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
    prompt_user = build_user_message(build, awakening)

    gadget = None
    source = "deterministic (no key)"
    if _CLIENT is not None:
        try:
            gadget = clamp_gadget(llm_resolve(build, awakening, _CLIENT))
            source = "llm"
        except Exception as exc:  # noqa: BLE001 - report the fallback reason to the console
            source = f"deterministic (llm failed: {exc})"
    if gadget is None:
        gadget = deterministic_resolve(build, awakening)

    engine = to_engine(gadget)
    engine["logic"] = gadget.logic
    engine["category"] = gadget.category.value
    engine["stage_count"] = len(gadget.stages)
    return {
        "gadget": gadget.model_dump(mode="json"),
        "engine": engine,
        "prompt": {"user": prompt_user},
        "model": MODEL if _CLIENT is not None else "deterministic",
        "source": source,
    }


class _Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:  # noqa: N802 - CORS preflight
        self._send(204, b"")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.dumps(_resolve_request(json.loads(raw))).encode("utf-8")
            self._send(200, payload)
        except Exception as exc:  # noqa: BLE001 - report every failure to the client
            self._send(500, json.dumps({"error": str(exc)}).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802 - console / catalog / health
        if self.path.startswith("/catalog"):
            self._send(200, json.dumps(_catalog()).encode("utf-8"))
        elif self.path in ("/", "/index.html", "/console"):
            if _CONSOLE_HTML.exists():
                self._send(200, _CONSOLE_HTML.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, b'{"error":"tools/combine_console.html not found"}')
        else:
            self._send(200, json.dumps({"ok": True}).encode("utf-8"))

    def _send(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, *args) -> None:  # quiet the per-request stderr spam
        return


def main() -> int:
    global _CLIENT
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _CLIENT = _make_client(False)
    where = f"{MODEL} (BYOK)" if _CLIENT is not None else "deterministic (no key)"
    print(f"combine brain serving on http://127.0.0.1:{PORT}  ({where})")
    print("POST /resolve  ·  GET /catalog  ·  Ctrl-C to stop.")
    try:
        HTTPServer(("127.0.0.1", PORT), _Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
