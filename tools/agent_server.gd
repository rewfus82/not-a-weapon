extends Node
## Interactive control server for agent-driven play.
##
## Instances the real game (scenes/Main.tscn) and keeps it running, hosting a
## line-delimited-JSON TCP server on 127.0.0.1. An external client (tools/naw.py)
## sends one command per connection and reads one JSON response; game state
## persists in this process between commands, so the agent can drive the game
## step by step: press keys, click, wait, screenshot, and query live state.
##
## Edits nothing in the game. `state`/`eval` read fields reflectively off the
## live game node, so no game-side hooks are needed. Launched via tools/serve.ps1.
##   NAW_PORT  TCP port (default 8899)
##   NAW_OUT   absolute dir for screenshots (default res://tools/captures)
##   NAW_SIZE  "WxH" window size (default 1600x900)

const GAME := "res://scenes/Main.tscn"

var _game: Node
var _server := TCPServer.new()
var _out_dir := ""
var _held: Dictionary = {}   # keycode -> true, for a clean release-all on restart

func _ready() -> void:
	var port := int(_env("NAW_PORT", "8899"))
	_out_dir = _env("NAW_OUT", "res://tools/captures")
	var size := _parse_size(_env("NAW_SIZE", "1600x900"))

	var packed: PackedScene = load(GAME)
	if packed == null:
		push_error("[SERVER] failed to load %s" % GAME)
		get_tree().quit(2)
		return
	_game = packed.instantiate()
	add_child(_game)

	await get_tree().process_frame
	var win := get_window()
	win.mode = Window.MODE_WINDOWED
	win.size = size

	var err := _server.listen(port, "127.0.0.1")
	if err != OK:
		push_error("[SERVER] listen failed on %d (%d)" % [port, err])
		get_tree().quit(3)
		return
	print("[SERVER] listening on 127.0.0.1:%d  game=%s" % [port, GAME])

func _process(_dt: float) -> void:
	if _server.is_connection_available():
		# fire-and-forget coroutine: it awaits its own I/O without blocking _process
		_handle(_server.take_connection())

# --- one request/response per connection ------------------------------------
func _handle(peer: StreamPeerTCP) -> void:
	var line := await _read_line(peer)
	var resp: Dictionary
	if line == "":
		resp = {"ok": false, "error": "empty request"}
	else:
		var req = JSON.parse_string(line)
		if typeof(req) != TYPE_DICTIONARY:
			resp = {"ok": false, "error": "bad json: %s" % line}
		else:
			resp = await _dispatch(req)
	peer.put_data((JSON.stringify(resp) + "\n").to_utf8_buffer())
	# let the bytes flush before we drop the socket
	await get_tree().process_frame
	peer.disconnect_from_host()

func _read_line(peer: StreamPeerTCP) -> String:
	var buf := PackedByteArray()
	var deadline := Time.get_ticks_msec() + 5000
	while Time.get_ticks_msec() < deadline:
		peer.poll()
		var st := peer.get_status()
		if st != StreamPeerTCP.STATUS_CONNECTED and st != StreamPeerTCP.STATUS_CONNECTING:
			break
		var n := peer.get_available_bytes()
		if n > 0:
			var got := peer.get_data(n)  # [err, PackedByteArray]
			if got[0] == OK:
				buf.append_array(got[1])
				var idx := buf.find(10)  # '\n'
				if idx != -1:
					return buf.slice(0, idx).get_string_from_utf8()
		await get_tree().process_frame
	return buf.get_string_from_utf8()

# --- command dispatch -------------------------------------------------------
func _dispatch(req: Dictionary) -> Dictionary:
	var cmd := String(req.get("cmd", ""))
	match cmd:
		"ping":
			return {"ok": true, "pong": true, "frame": Engine.get_process_frames()}
		"screenshot":
			return await _cmd_screenshot(req)
		"key":
			return await _cmd_key(req)
		"click":
			return await _cmd_click(req)
		"aim":
			return _cmd_aim(req)
		"wait":
			return await _cmd_wait(req)
		"state":
			return _cmd_state(req)
		"eval":
			return _cmd_eval(req)
		"restart":
			_release_all()
			if _game.has_method("_restart"):
				_game._restart()
			return {"ok": true, "restarted": true}
		"quit":
			get_tree().quit(0)
			return {"ok": true, "quitting": true}
		_:
			return {"ok": false, "error": "unknown cmd: %s" % cmd}

func _cmd_screenshot(req: Dictionary) -> Dictionary:
	var shot_name := String(req.get("name", "frame"))
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	if img == null:
		return {"ok": false, "error": "null viewport image"}
	var path := "%s/%s.png" % [_out_dir, shot_name]
	var err := img.save_png(path)
	if err != OK:
		return {"ok": false, "error": "save_png failed (%d)" % err}
	return {"ok": true, "path": ProjectSettings.globalize_path(path), "size": [img.get_width(), img.get_height()]}

func _cmd_key(req: Dictionary) -> Dictionary:
	var key_name := String(req.get("name", ""))
	var action := String(req.get("action", "tap"))
	var code := OS.find_keycode_from_string(key_name)
	if code == KEY_NONE:
		return {"ok": false, "error": "unknown key: %s" % key_name}
	match action:
		"down":
			_emit_key(code, true); _held[code] = true
		"up":
			_emit_key(code, false); _held.erase(code)
		"tap":
			_emit_key(code, true)
			await get_tree().process_frame
			await get_tree().process_frame
			_emit_key(code, false)
		_:
			return {"ok": false, "error": "action must be down|up|tap"}
	return {"ok": true, "key": key_name, "action": action}

func _emit_key(code: int, pressed: bool) -> void:
	var ev := InputEventKey.new()
	ev.keycode = code
	ev.physical_keycode = code
	ev.pressed = pressed
	Input.parse_input_event(ev)

func _cmd_click(req: Dictionary) -> Dictionary:
	var button := int(req.get("button", MOUSE_BUTTON_LEFT))
	var pos: Vector2 = get_viewport().get_mouse_position()
	if req.has("x") and req.has("y"):
		pos = Vector2(float(req["x"]), float(req["y"]))
		Input.warp_mouse(pos)
		await get_tree().process_frame
	_emit_click(button, pos, true)
	await get_tree().process_frame
	_emit_click(button, pos, false)
	return {"ok": true, "button": button, "pos": [pos.x, pos.y]}

func _emit_click(button: int, pos: Vector2, pressed: bool) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	ev.pressed = pressed
	ev.position = pos
	ev.global_position = pos
	Input.parse_input_event(ev)

# Aim in a world-space direction. The camera tracks the player, so the player
# sits ~screen-center; warping the mouse to center + dir gives that aim.
func _cmd_aim(req: Dictionary) -> Dictionary:
	var dir := Vector2(float(req.get("dx", 1.0)), float(req.get("dy", 0.0)))
	if dir.length() < 0.001:
		return {"ok": false, "error": "aim direction is zero"}
	var center := Vector2(get_viewport().get_visible_rect().size) * 0.5
	var target := center + dir.normalized() * 220.0
	Input.warp_mouse(target)
	return {"ok": true, "aim": [dir.x, dir.y], "mouse": [target.x, target.y]}

func _cmd_wait(req: Dictionary) -> Dictionary:
	if req.has("seconds"):
		await get_tree().create_timer(float(req["seconds"])).timeout
		return {"ok": true, "waited_seconds": float(req["seconds"])}
	var frames := int(req.get("frames", 1))
	for i in range(maxi(1, frames)):
		await get_tree().process_frame
	return {"ok": true, "waited_frames": frames}

# Curated snapshot of the fields an agent most often wants to assert on.
func _cmd_state(_req: Dictionary) -> Dictionary:
	var g := _game
	var arsenal_names: Array = []
	for gadget in g.get("_arsenal"):
		arsenal_names.append(gadget.display_name)
	var equipped = g.get("_equipped")
	return {
		"ok": true,
		"state": {
			"phase": g.get("_phase"),
			"hp": g.get("_hp"),
			"day": g.get("_day_count"),
			"awakening": g.get("_awakening"),
			"paused": g.get("_paused"),
			"player": [(g.get("_player") as Vector2).x, (g.get("_player") as Vector2).y],
			"zombies": (g.get("_zombies") as Array).size(),
			"pickups": (g.get("_pickups_root") as Node).get_child_count() if g.get("_pickups_root") != null else 0,
			"inventory": g.get("_inv"),
			"arsenal": arsenal_names,
			"equipped": equipped.display_name if equipped != null else null,
			"flashlight_on": g.get("_flashlight_on"),
		}
	}

# Evaluate a GDScript expression against the live game node as base instance,
# so `_hp`, `_zombies.size()`, `_arsenal[0].display_name`, etc. all resolve.
func _cmd_eval(req: Dictionary) -> Dictionary:
	var expr_str := String(req.get("expr", ""))
	if expr_str == "":
		return {"ok": false, "error": "missing expr"}
	var e := Expression.new()
	var perr := e.parse(expr_str, [])
	if perr != OK:
		return {"ok": false, "error": "parse error: %s" % e.get_error_text()}
	var result = e.execute([], _game, true)
	if e.has_execute_failed():
		return {"ok": false, "error": "execute failed: %s" % e.get_error_text()}
	return {"ok": true, "expr": expr_str, "result": _jsonable(result)}

func _release_all() -> void:
	for code in _held.keys():
		_emit_key(int(code), false)
	_held.clear()

# Coerce Godot types the JSON encoder can't handle (Vector2, Object, ...).
func _jsonable(v: Variant) -> Variant:
	match typeof(v):
		TYPE_VECTOR2, TYPE_VECTOR2I:
			return [v.x, v.y]
		TYPE_OBJECT:
			return str(v) if v != null else null
		TYPE_ARRAY:
			var out: Array = []
			for x in v:
				out.append(_jsonable(x))
			return out
		_:
			return v

func _env(key: String, fallback: String) -> String:
	var val := OS.get_environment(key)
	return val if val != "" else fallback

func _parse_size(s: String) -> Vector2i:
	var parts := s.to_lower().split("x")
	if parts.size() == 2 and parts[0].is_valid_int() and parts[1].is_valid_int():
		return Vector2i(int(parts[0]), int(parts[1]))
	return Vector2i(1600, 900)
