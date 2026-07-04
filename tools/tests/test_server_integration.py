"""End-to-end tests for the interactive control server.

Launches a real Godot process running tools/agent_server.tscn, drives it over
the socket, and asserts the command contract holds — including that state
persists across commands. Skipped automatically when no Godot binary is found
(e.g. headless CI), so it never produces false failures.

Run just these:  pytest tools/tests/test_server_integration.py -v
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

import naw

PROJECT_DIR = Path(__file__).resolve().parents[2]
PORT = 8917  # distinct from the default 8899 so a live dev server won't clash

GODOT_CANDIDATES = [
    os.environ.get("NAW_GODOT", ""),
    r"C:\Users\rewfu\Godot\Godot_v4.7-stable_win64_console.exe",
    r"C:\Users\rewfu\Godot\Godot_v4.7-stable_win64.exe",
]


def _find_godot() -> str | None:
    for path in GODOT_CANDIDATES:
        if path and Path(path).exists():
            return path
    return None


GODOT = _find_godot()
pytestmark = pytest.mark.skipif(GODOT is None, reason="Godot binary not found")


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("captures")
    env = {**os.environ, "NAW_PORT": str(PORT), "NAW_OUT": str(out_dir), "NAW_SIZE": "800x600"}
    # Redirect Godot's output to files, not PIPE: an undrained PIPE fills and
    # deadlocks the engine before it can service connections.
    log_path = out_dir / "server.log"
    err_path = out_dir / "server.err"

    def _diag() -> str:
        parts = []
        for p in (log_path, err_path):
            if p.exists():
                parts.append(f"--- {p.name} ---\n{p.read_text(errors='replace')[-2000:]}")
        return "\n".join(parts)

    with open(log_path, "w") as log, open(err_path, "w") as err:
        proc = subprocess.Popen(
            [GODOT, "--path", str(PROJECT_DIR), "res://tools/agent_server.tscn", "--resolution", "800x600"],
            env=env,
            stdout=log,
            stderr=err,
        )
        try:
            deadline = time.time() + 30
            while time.time() < deadline:
                if proc.poll() is not None:
                    pytest.fail(f"server exited early ({proc.returncode}):\n{_diag()}")
                if _port_open(PORT):
                    break
                time.sleep(0.3)
            else:
                pytest.fail(f"server did not open its port within 30s:\n{_diag()}")
            yield {"port": PORT, "out_dir": out_dir}
        finally:
            try:
                naw.send({"cmd": "quit"}, port=PORT, timeout=3)
            except OSError:
                pass
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()


def call(server, req: dict) -> dict:
    return naw.send(req, port=server["port"])


def test_ping(server):
    resp = call(server, {"cmd": "ping"})
    assert resp["ok"] is True
    assert resp["pong"] is True
    assert isinstance(resp["frame"], int)


def test_state_has_expected_shape(server):
    resp = call(server, {"cmd": "state"})
    assert resp["ok"] is True
    st = resp["state"]
    for key in ("hp", "day", "phase", "player", "zombies", "inventory", "arsenal", "equipped"):
        assert key in st, f"missing state key: {key}"
    assert isinstance(st["hp"], (int, float))
    assert isinstance(st["player"], list) and len(st["player"]) == 2
    assert "Rusty Pistol" in st["arsenal"]


def test_eval_returns_live_values(server):
    assert call(server, {"cmd": "eval", "expr": "_hp"})["result"] > 0
    assert isinstance(call(server, {"cmd": "eval", "expr": "_zombies.size()"})["result"], int)
    assert call(server, {"cmd": "eval", "expr": "1 + 2"})["result"] == 3


def test_eval_parse_error_is_reported_not_crashed(server):
    resp = call(server, {"cmd": "eval", "expr": "_arsenal.map(func(g): return g)"})
    assert resp["ok"] is False
    assert "parse error" in resp["error"].lower()


def test_unknown_command_fails_cleanly(server):
    resp = call(server, {"cmd": "banana"})
    assert resp["ok"] is False
    assert "unknown cmd" in resp["error"]


def test_key_down_and_up(server):
    assert call(server, {"cmd": "key", "name": "w", "action": "down"})["ok"] is True
    assert call(server, {"cmd": "key", "name": "w", "action": "up"})["ok"] is True


def test_bad_key_is_rejected(server):
    resp = call(server, {"cmd": "key", "name": "notarealkey", "action": "tap"})
    assert resp["ok"] is False


def test_state_persists_across_commands(server):
    """Holding W between two state reads should change the player's Y."""
    call(server, {"cmd": "restart"})
    y0 = call(server, {"cmd": "state"})["state"]["player"][1]
    call(server, {"cmd": "key", "name": "w", "action": "down"})
    call(server, {"cmd": "wait", "frames": 45})
    call(server, {"cmd": "key", "name": "w", "action": "up"})
    y1 = call(server, {"cmd": "state"})["state"]["player"][1]
    assert y1 < y0 - 20, f"expected player to move up; y0={y0} y1={y1}"


def test_screenshot_writes_a_png(server):
    resp = call(server, {"cmd": "screenshot", "name": "test_shot"})
    assert resp["ok"] is True
    path = Path(resp["path"])
    assert path.exists() and path.stat().st_size > 0
    # Height follows the game's keep-aspect letterboxing, so pin width only.
    w, h = resp["size"]
    assert w == 800 and h > 0
