# AGENT.md — how to see and drive the game

You are editing **This Is Not A Weapon** (Godot 4.7, GDScript). You cannot open
the editor. Use these tools to verify your changes actually run and look right.
Read this before your first capture, then follow the loop.

## Pick a mode

- **Smoke test after a change** → one-shot `capture.ps1`. Confirms it launches,
  renders, and has no script errors.
- **Play-test a mechanic over several steps** → interactive `serve.ps1` + `naw.py`.
  Keeps one game alive so your commands compose.

Default to the one-shot after any edit. Reach for interactive when you need to
*do* something (walk, fire, craft) and observe the result.

---

## One-shot: `capture.ps1`

```
./tools/capture.ps1                      # launch, screenshot, PASS/FAIL, exit
./tools/capture.ps1 -Keys "w,d" -Fire    # move + fire so the shot shows action
./tools/capture.ps1 -Night -Fire         # dark combat scene
```

Then **always do both**:
1. Check the printed `RESULT:` / exit code. Non-zero or `FAIL` = broken; the
   `errors:` block lists the `SCRIPT ERROR` lines. Fix before continuing.
2. Read `tools/captures/frame.png` to judge visuals. Full log:
   `tools/captures/console.log`.

Do not declare a change working on PASS alone — look at the screenshot.

---

## Interactive: `serve.ps1` + `naw.py`

### Start the server (do this once)

You are a Claude Code agent, so a normal tool call would let the server die when
the call ends. **Launch it in a background shell instead** (do NOT use
`serve.ps1` from a tool call):

```
NAW_PORT=8899 NAW_OUT="<ABS_PROJECT_DIR>/tools/captures" \
  "/c/Users/rewfu/Godot/Godot_v4.7-stable_win64_console.exe" \
  --path "<ABS_PROJECT_DIR>" res://tools/agent_server.tscn --resolution 1600x900
```

Then poll until ready: `python tools/naw.py ping` returns `"ok": true`.
Stop it when done: `python tools/naw.py quit`.

### Drive it

```
python tools/naw.py state                     # hp, day, player xy, zombies, inventory, arsenal
python tools/naw.py eval "_zombies.size()"     # any GDScript expression on the live game
python tools/naw.py key w down                 # hold a key (release with: key w up)
python tools/naw.py key space tap              # tap (pause/start-wave, etc.)
python tools/naw.py aim 1 0                     # aim right; click fires the weapon
python tools/naw.py click
python tools/naw.py wait 30                     # advance 30 frames
python tools/naw.py screenshot fight           # -> tools/captures/fight.png
python tools/naw.py restart                     # fresh run
```

Each call is one JSON response with `"ok"`; exit `0` ok, `1` failed, `3` server
down. State persists between calls — that's the point. Assert with `eval`/`state`
(numbers), confirm with `screenshot` (pixels).

Key bindings: `w a s d` move · `space` pause/start-wave · `f` flashlight ·
`r` reload · `tab` workbench · `1..9` switch weapon.

`eval` is expression-only (Godot `Expression`): no statements, no `func` lambdas.
For arsenal names use `state` (it precomputes them).

---

## Rules

- These tools edit nothing in the game. Never add capture/debug hooks to
  `main.gd` or `project.godot` to make them work — extend the harness in
  `tools/` instead.
- Screenshots + logs land in `tools/captures/` (gitignored). Don't commit them.
- One-shot clears old screenshots each run; interactive overwrites by name.
- If the server is unreachable, it isn't running — relaunch it (background
  shell), don't assume a code bug.

Full reference: `tools/README.md`.
