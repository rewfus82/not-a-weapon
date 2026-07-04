"""Unit tests for the naw.py client's CLI-to-request mapping.

Pure and Godot-free: they pin the wire protocol the server relies on, so a
change to argument handling that would silently send the wrong command fails
here instead of mid-play-test.
"""
from __future__ import annotations

import pytest

import naw


def test_bare_commands_map_to_just_cmd():
    for cmd in ("ping", "state", "restart", "quit"):
        assert naw.build_request([cmd]) == {"cmd": cmd}


def test_screenshot_defaults_to_frame():
    assert naw.build_request(["screenshot"]) == {"cmd": "screenshot", "name": "frame"}


def test_screenshot_takes_a_name():
    assert naw.build_request(["screenshot", "fight"]) == {"cmd": "screenshot", "name": "fight"}


def test_eval_passes_expression_verbatim():
    expr = "_arsenal[0].display_name"
    assert naw.build_request(["eval", expr]) == {"cmd": "eval", "expr": expr}


def test_key_defaults_action_to_tap():
    assert naw.build_request(["key", "w"]) == {"cmd": "key", "name": "w", "action": "tap"}


def test_key_honors_explicit_action():
    assert naw.build_request(["key", "space", "down"]) == {
        "cmd": "key", "name": "space", "action": "down",
    }


def test_aim_parses_floats():
    assert naw.build_request(["aim", "1", "0"]) == {"cmd": "aim", "dx": 1.0, "dy": 0.0}
    assert naw.build_request(["aim", "-0.5", "0.5"]) == {"cmd": "aim", "dx": -0.5, "dy": 0.5}


def test_click_no_coords_is_bare():
    assert naw.build_request(["click"]) == {"cmd": "click"}


def test_click_with_coords_and_button():
    assert naw.build_request(["click", "800", "450", "2"]) == {
        "cmd": "click", "x": 800.0, "y": 450.0, "button": 2,
    }


def test_click_coords_without_button():
    assert naw.build_request(["click", "800", "450"]) == {
        "cmd": "click", "x": 800.0, "y": 450.0,
    }


def test_wait_defaults_to_one_frame():
    assert naw.build_request(["wait"]) == {"cmd": "wait", "frames": 1}


def test_wait_frames():
    assert naw.build_request(["wait", "30"]) == {"cmd": "wait", "frames": 30}


@pytest.mark.parametrize("flag", ["-s", "--seconds"])
def test_wait_seconds(flag):
    assert naw.build_request(["wait", flag, "2.5"]) == {"cmd": "wait", "seconds": 2.5}


def test_raw_passes_through_parsed_json():
    assert naw.build_request(["raw", '{"cmd":"key","name":"w","action":"up"}']) == {
        "cmd": "key", "name": "w", "action": "up",
    }


def test_empty_argv_raises():
    with pytest.raises(SystemExit):
        naw.build_request([])


def test_bad_numeric_arg_raises_valueerror():
    # main() catches this and exits 2; build_request itself surfaces it.
    with pytest.raises(ValueError):
        naw.build_request(["aim", "left", "0"])
