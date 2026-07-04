# Godot agent harness — feedback loops for "This Is Not A Weapon"

Two ways for an agent to *see and drive* the game without opening the editor.
Both edit nothing in the game (no `main.gd` / `project.godot` changes) and are
safe to run anytime.

- **One-shot capture** (`capture.ps1`) — launch, screenshot, report PASS/FAIL,
  exit. Best as a quick smoke test after a change: "does it run and look right?"
- **Interactive session** (`serve.ps1` + `naw.py`) — keep the game running and
  drive it command by command: press keys, click, wait, screenshot, and query
  live state. Best for play-testing a mechanic across many steps.

```
one-shot:     edit code -> capture.ps1 -> read RESULT + frame.png -> judge
interactive:  serve.ps1 (once) -> naw.py <cmd> ... -> screenshot/state -> judge -> repeat
```

---

# One-shot capture

## Run it

```powershell
# from the project root
./tools/capture.ps1                          # 1.5s warmup, one screenshot
./tools/capture.ps1 -Keys "w,d" -Warmup 2.5  # hold W+D so the shot shows motion
./tools/capture.ps1 -Duration 3              # also grab a second shot 3s later
```

Parameters:

| Param       | Default     | Meaning                                             |
|-------------|-------------|-----------------------------------------------------|
| `-Keys`     | (none)      | Keys to hold, comma list: `w,d`, `space`, `w,space` |
| `-Warmup`   | `1.5`       | Seconds to run before the first capture             |
| `-Duration` | `0`         | Extra seconds, then a second `frame_end.png`        |
| `-Fire`     | off         | Hold-fire toward `-Aim` for ~0.6s before the shot   |
| `-Aim`      | right-of-center | Mouse screen `x,y` to aim at (e.g. `1200,450`)  |
| `-Night`    | off         | Force time-of-day to midnight (dark)                |
| `-Tod`      | (none)      | Explicit time-of-day `0..1` (0=midnight, 0.5=noon)  |
| `-Teleport` | (none)      | Teleport the player to world `x,y` to stage a spot  |
| `-Size`     | `1600x900`  | Capture resolution                                  |
| `-OutDir`   | `tools/captures` | Where PNGs + `console.log` go                  |
| `-Godot`    | auto        | Override Godot exe path                             |

```powershell
./tools/capture.ps1 -Fire                         # aim right, fire a burst
./tools/capture.ps1 -Night -Fire                  # night combat scene
./tools/capture.ps1 -Teleport "2200,1500" -Night  # stage a spot at night
```

Held keys use the game's own bindings: `w a s d` move, `space` pause/start,
`f` flashlight, `r` reload, `tab` workbench. For scripted mouse aim/fire in a
one-shot, use `-Fire`/`-Aim`; for full step-by-step control use the interactive
session below.

## What you get back

- **`RESULT: PASS` / `FAIL`** printed to stdout, and the process exit code
  (`0` pass, non-zero fail) — key off either.
- **`tools/captures/frame.png`** — the rendered frame. Read it to judge visuals.
  (`frame_end.png` too when `-Duration > 0`.)
- **`tools/captures/console.log`** — full stdout+stderr, including every
  `print()` and Godot error.

FAIL means one of: Godot exited non-zero, no screenshot was produced, or the log
contained `SCRIPT ERROR` / `Parse Error` / a harness error. Those lines are
echoed under `errors:` in the summary.

## How it works

`capture.ps1` launches the `_console` Godot build against
`tools/agent_capture.tscn` (a wrapper scene). The wrapper instances the real
`scenes/Main.tscn`, forces a deterministic window size, holds any requested
keys, waits `-Warmup` seconds, saves the viewport texture as PNG, then quits.
`--quit-after` is a hard frame-count backstop so a hang can't wedge the loop.

---

# Interactive session

Keeps one game process alive and lets the agent drive it command by command.
State persists between commands, so calls compose: move, then check where you
ended up; fire, then count remaining ammo; screenshot the exact moment you want.

## Start / stop

```powershell
./tools/serve.ps1                 # launch the game + control server on 127.0.0.1:8899
python tools/naw.py quit          # stop it (or just close the game window)
```

`serve.ps1` waits until the port is accepting connections before returning, then
leaves the game running in the background.

> **Launching from inside a Claude Code agent:** the harness reaps child
> processes when a tool call ends, so `serve.ps1` started via the tool won't
> survive. Instead launch the server through a **background shell** so it lives
> across turns, e.g.:
> ```
> NAW_PORT=8899 NAW_OUT="<abs>/tools/captures" \
>   "/c/Users/rewfu/Godot/Godot_v4.7-stable_win64_console.exe" \
>   --path "<abs>" res://tools/agent_server.tscn --resolution 1600x900
> ```
> A human running `serve.ps1` in a normal terminal is fine.

## Commands (`python tools/naw.py <cmd>`)

| Command | Example | Returns |
|---|---|---|
| `ping` | `ping` | liveness + frame number |
| `state` | `state` | hp, day, phase, player xy, zombie count, inventory, arsenal, equipped, flashlight |
| `eval "<expr>"` | `eval "_zombies.size()"` | value of a GDScript **expression** against the live game node |
| `key <name> <down\|up\|tap>` | `key w down` | holds/releases/taps a key (game bindings) |
| `aim <dx> <dy>` | `aim 1 0` | points aim in a world-space direction |
| `click [x y] [button]` | `click` | one mouse click (fires the equipped weapon) |
| `wait <frames>` / `wait -s <sec>` | `wait 30` | advances the game, then replies |
| `screenshot [name]` | `screenshot fight` | saves `tools/captures/<name>.png`, returns its path |
| `restart` | `restart` | releases held keys + calls the game's `_restart()` |
| `quit` | `quit` | shuts the server down |
| `raw '<json>'` | `raw '{"cmd":"key","name":"space","action":"tap"}'` | send any request verbatim |

Every response is one JSON line with `"ok": true|false`; `naw.py` exits `0` on
success, `1` on `ok:false`, `3` if the server is unreachable.

## Example: drive a fight

```bash
python tools/naw.py restart
python tools/naw.py key w down    # walk into the horde
python tools/naw.py wait 60
python tools/naw.py key w up
python tools/naw.py aim 1 0       # face right
python tools/naw.py click         # fire
python tools/naw.py eval "_equipped.ammo_count()"   # assert ammo dropped
python tools/naw.py screenshot after_shot           # then read the PNG
```

## `eval` scope

`eval` uses Godot's `Expression` class with the game node as base instance, so
any field/method resolves: `_hp`, `_zombies.size()`, `_arsenal[0].display_name`,
`_player.distance_to(Vector2(1600,1000))`. It evaluates a **single expression** —
no statements, no `func` lambdas. For lists of gadget names etc., prefer the
`state` command (it pre-computes `arsenal`).

## Extending

- **Scripted mouse targeting** — `aim` warps to screen-center + direction
  (works because the camera tracks the player). For an exact world point, add a
  command that projects through `_game._cam`.
- **New state fields** — add them to `_cmd_state` in `agent_server.gd`, or just
  `eval` them ad hoc.
- **Assertions** — the server holds the live game node; anything readable in
  GDScript is reachable via `eval`/`state`.
