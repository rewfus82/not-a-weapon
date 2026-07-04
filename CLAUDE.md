# This Is Not A Weapon — project guide

2D top-down zombie-survival graybox in Godot 4.7 (GDScript). Combine scavenged
junk into weapons/tools; a deterministic Resolver (with an optional Python AI
brain in `combine/`) turns items into gadgets. Most gameplay lives in the single
immediate-mode script `scripts/main.gd` (custom `_draw`), rendered procedurally.

## Verifying your changes — READ THIS

You cannot open the Godot editor. After any change to game code, **see it run**
before claiming it works. A dedicated harness in `tools/` does this:

- Quick smoke test → `./tools/capture.ps1` (launch, screenshot, PASS/FAIL).
- Step-by-step play-testing → interactive server, `tools/serve.ps1` + `tools/naw.py`.

**Full instructions: [`tools/AGENT.md`](tools/AGENT.md). Read it before your
first run.** Always check the `RESULT`/exit code *and* look at the screenshot in
`tools/captures/` — PASS alone doesn't mean it looks right.

## Rules

- The harness edits nothing in the game. Never add capture/debug hooks to
  `main.gd` or `project.godot` to make tooling work — extend `tools/` instead.
- Match the surrounding code's style; `main.gd` is dense and idiomatic.
- `tools/captures/` and `screenshots/` are gitignored; don't commit them.
