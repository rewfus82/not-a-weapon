#!/usr/bin/env python3
"""Client for the interactive Godot control server (tools/agent_server.gd).

Each invocation opens one TCP connection, sends one line-delimited-JSON command,
prints the JSON response, and exits with 0 on {"ok": true} else 1. Game state
lives in the persistent server process, so successive calls compose.

Usage:
  python naw.py ping
  python naw.py screenshot [name]
  python naw.py key <name> [down|up|tap]     # e.g. key w down / key space tap
  python naw.py click [x] [y] [button]
  python naw.py aim <dx> <dy>                 # world-space aim direction
  python naw.py wait <frames> | wait -s <seconds>
  python naw.py state
  python naw.py eval "<gdscript expression>"  # e.g. eval "_zombies.size()"
  python naw.py restart
  python naw.py quit
  python naw.py raw '{"cmd":"key","name":"w","action":"down"}'
"""
from __future__ import annotations

import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 8899


def send(req: dict, host: str = HOST, port: int = PORT, timeout: float = 15.0) -> dict:
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall((json.dumps(req) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    line = buf.split(b"\n", 1)[0].decode("utf-8", "replace")
    return json.loads(line) if line else {"ok": False, "error": "no response"}


def build_request(argv: list[str]) -> dict:
    if not argv:
        raise SystemExit(__doc__)
    cmd, rest = argv[0], argv[1:]

    if cmd == "raw":
        return json.loads(rest[0])
    if cmd in ("ping", "state", "restart", "quit"):
        return {"cmd": cmd}
    if cmd == "screenshot":
        return {"cmd": "screenshot", "name": rest[0] if rest else "frame"}
    if cmd == "eval":
        return {"cmd": "eval", "expr": rest[0]}
    if cmd == "key":
        return {"cmd": "key", "name": rest[0], "action": rest[1] if len(rest) > 1 else "tap"}
    if cmd == "aim":
        return {"cmd": "aim", "dx": float(rest[0]), "dy": float(rest[1])}
    if cmd == "click":
        req = {"cmd": "click"}
        if len(rest) >= 2:
            req["x"], req["y"] = float(rest[0]), float(rest[1])
        if len(rest) >= 3:
            req["button"] = int(rest[2])
        return req
    if cmd == "wait":
        if rest and rest[0] in ("-s", "--seconds"):
            return {"cmd": "wait", "seconds": float(rest[1])}
        return {"cmd": "wait", "frames": int(rest[0]) if rest else 1}
    # unknown local alias -> pass through as a bare cmd
    return {"cmd": cmd}


def main() -> int:
    try:
        req = build_request(sys.argv[1:])
    except (IndexError, ValueError) as e:
        print(json.dumps({"ok": False, "error": f"bad args: {e}"}))
        return 2
    try:
        resp = send(req)
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        print(json.dumps({"ok": False, "error": f"server unreachable: {e}. Start it with tools/serve.ps1"}))
        return 3
    print(json.dumps(resp, indent=2))
    return 0 if resp.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
