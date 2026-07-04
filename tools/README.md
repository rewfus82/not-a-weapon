# Godot capture harness — agent feedback loop

A one-shot tool that runs **This Is Not A Weapon**, screenshots the rendered
frame, captures all console + GDScript-error output, and reports PASS/FAIL.

Use it to *see* whether a change worked without opening the editor. It edits
nothing in the game (no `main.gd` / `project.godot` changes) and is safe to run
anytime.

## The loop

```
edit game code  ->  run capture.ps1  ->  read RESULT + view frame.png  ->  judge
```

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
| `-Size`     | `1600x900`  | Capture resolution                                  |
| `-OutDir`   | `tools/captures` | Where PNGs + `console.log` go                  |
| `-Godot`    | auto        | Override Godot exe path                             |

Held keys use the game's own bindings: `w a s d` move, `space` pause/start,
`f` flashlight, `r` reload, `tab` workbench. (Mouse aim defaults to facing
right; scripted mouse aim isn't supported yet.)

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

## Extending

- **Scripted input timeline** (press/release at set times) — extend
  `_press_keys` in `agent_capture.gd` into a parsed schedule.
- **Mouse aim / clicks** — `Input.warp_mouse()` + synthesized
  `InputEventMouseButton` in the harness.
- **Deep state assertions** — the harness holds a reference to the live game
  node; read fields off it (e.g. `game._hp`, `game._zombies.size()`) and print
  them for the agent to assert on.
