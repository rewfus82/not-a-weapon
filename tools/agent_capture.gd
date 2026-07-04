extends Node
## Non-invasive capture harness for agent-driven iteration.
##
## Instances the real game (scenes/Main.tscn) as a child, overrides Main's
## forced window-maximize so captures are a deterministic size, optionally
## holds down a set of keys to drive movement, warms up, saves one or more
## PNG screenshots of the rendered frame, then quits.
##
## It edits nothing in the game itself — launched only via tools/capture.ps1,
## so normal play is unaffected. All config comes from env vars:
##   NAW_OUT      absolute output dir for PNGs + status (default: res://tools/captures)
##   NAW_WARMUP   seconds to let the game run before the first capture (default 1.5)
##   NAW_DURATION extra seconds to run, then a second capture "frame_end" (default 0)
##   NAW_KEYS     comma list of keys to hold, e.g. "w,d" or "space" (default none)
##   NAW_SIZE     "WxH" window/capture size (default 1600x900)
##   NAW_FIRE     "1" to hold-fire toward NAW_AIM for a burst before the capture
##   NAW_AIM      "x,y" screen pos to aim the mouse at (default: right of center)
##   NAW_TOD      time-of-day override 0..1 (0=midnight/dark, 0.5=noon) for staged shots
##   NAW_TP       teleport the player to world "x,y" (stage a spot without editing the game)

const GAME := "res://scenes/Main.tscn"

var _out_dir := ""
var _errors: Array[String] = []
var _shots: Array[String] = []
var _game: Node = null

func _ready() -> void:
	_out_dir = _env("NAW_OUT", "res://tools/captures")
	var warmup := float(_env("NAW_WARMUP", "1.5"))
	var duration := float(_env("NAW_DURATION", "0"))
	var size := _parse_size(_env("NAW_SIZE", "1600x900"))

	# Load + instance the real game. A load failure here is the single most
	# useful signal for the agent, so report it loudly and bail.
	var packed: PackedScene = load(GAME)
	if packed == null:
		_errors.append("FAILED to load %s" % GAME)
		_finish(2)
		return
	_game = packed.instantiate()
	add_child(_game)

	# Main forces MODE_MAXIMIZED in its _ready (already run via add_child above);
	# override it so every capture is the same, predictable resolution.
	await get_tree().process_frame
	var win := get_window()
	win.mode = Window.MODE_WINDOWED
	win.size = size

	# Optional state overrides for staged shots (night, teleport) — capture-run only.
	_apply_overrides()
	# Optionally hold keys down for the whole run (drive the player so a capture
	# shows motion / combat rather than a frozen opening frame).
	_press_keys(_env("NAW_KEYS", ""))

	await _wait(warmup)
	await _fire_burst(size)   # optional hold-fire so shots are mid-flight at capture
	await _capture("frame")

	if duration > 0.0:
		await _wait(duration)
		await _capture("frame_end")

	_finish(0)

func _capture(shot_name: String) -> void:
	# The viewport texture is only valid after the frame has been drawn.
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	if img == null:
		_errors.append("null viewport image for %s" % shot_name)
		return
	var path := "%s/%s.png" % [_out_dir, shot_name]
	var err := img.save_png(path)
	if err != OK:
		_errors.append("save_png failed (%d) -> %s" % [err, path])
		return
	_shots.append(path)
	print("[CAPTURE] ", path)

# Poke the live game node for staged shots (night, a teleport) — reads env, non-invasive.
func _apply_overrides() -> void:
	if _game == null:
		return
	var tod := _env("NAW_TOD", "")
	if tod != "" and tod.is_valid_float():
		_game.set("_time_of_day", float(tod))
		print("[STATE] time_of_day=", tod)
	var tp := _env("NAW_TP", "")
	if tp != "":
		var v := _parse_vec2(tp, Vector2.ZERO)
		_game.set("_player", v)
		print("[STATE] teleport player -> ", v)

# Aim the mouse and hold-fire for ~0.6s so shots are visibly mid-flight at capture.
func _fire_burst(size: Vector2i) -> void:
	if _env("NAW_FIRE", "") != "1":
		return
	var aim := _parse_vec2(_env("NAW_AIM", ""), Vector2(size.x * 0.72, size.y * 0.5))
	Input.warp_mouse(aim)
	await get_tree().process_frame
	for i in range(36):
		var ev := InputEventMouseButton.new()
		ev.button_index = MOUSE_BUTTON_LEFT
		ev.pressed = true
		ev.position = aim
		Input.parse_input_event(ev)
		await get_tree().process_frame
	print("[FIRE] burst toward ", aim)

func _parse_vec2(s: String, fallback: Vector2) -> Vector2:
	var parts := s.split(",", false)
	if parts.size() == 2 and parts[0].strip_edges().is_valid_float() and parts[1].strip_edges().is_valid_float():
		return Vector2(float(parts[0]), float(parts[1]))
	return fallback

func _press_keys(spec: String) -> void:
	if spec.strip_edges() == "":
		return
	for raw in spec.split(",", false):
		var key_name := raw.strip_edges()
		var code := OS.find_keycode_from_string(key_name)
		if code == KEY_NONE:
			_errors.append("unknown key in NAW_KEYS: %s" % key_name)
			continue
		var ev := InputEventKey.new()
		ev.keycode = code
		ev.physical_keycode = code
		ev.pressed = true
		Input.parse_input_event(ev)
		print("[KEY] holding ", key_name)

func _finish(code: int) -> void:
	# One machine-readable status line the ps1 / agent keys off of.
	print("[HARNESS] shots=%d errors=%d" % [_shots.size(), _errors.size()])
	for e in _errors:
		printerr("[HARNESS-ERROR] ", e)
	get_tree().quit(code)

func _wait(seconds: float) -> void:
	if seconds > 0.0:
		await get_tree().create_timer(seconds).timeout

func _env(key: String, fallback: String) -> String:
	var v := OS.get_environment(key)
	return v if v != "" else fallback

func _parse_size(s: String) -> Vector2i:
	var parts := s.to_lower().split("x")
	if parts.size() == 2 and parts[0].is_valid_int() and parts[1].is_valid_int():
		return Vector2i(int(parts[0]), int(parts[1]))
	return Vector2i(1600, 900)
