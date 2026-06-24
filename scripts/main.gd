extends Node2D
## Graybox test chamber for "This Is Not A Weapon".
##
## Everything is squares + text on purpose. The point is to feel whether the
## combine verb is fun BEFORE any art exists. World state is plain data updated
## in _process and drawn in _draw; the UI is built in code in _build_ui().
##
## Controls:  WASD / arrows = move   ·   mouse = aim   ·   left-click = use gadget
##   Inventory (right) -> click items into the pot (max 3) -> Combine -> it equips.
##   Tier buttons gate which slots the "simulation" lets you edit (1 -> 3).

const PANEL_W := 360.0
const PLAY_W := 1280.0 - PANEL_W
const PLAY_H := 720.0
const MARGIN := 14.0
const PLAYER_SPEED := 330.0
const FIRE_COOLDOWN := 0.18

var _db: Dictionary               # id -> Item
var _tier: int = 1
var _pot: Array[Item] = []        # current combine selection (max 3)
var _equipped: Gadget = null
var _loot_collected: int = 0

# --- world state -------------------------------------------------------------
var _player := Vector2(PLAY_W * 0.5, PLAY_H * 0.5)
var _aim := Vector2.RIGHT
var _fire_timer := 0.0
var _targets: Array[Dictionary] = []
var _dummy: Dictionary = {}
var _loot: Array[Dictionary] = []
var _projectiles: Array[Dictionary] = []
var _log_lines: Array[String] = []

# --- UI refs -----------------------------------------------------------------
var _pot_label: Label
var _equipped_label: RichTextLabel
var _log_label: RichTextLabel
var _tier_buttons: Array[Button] = []
var _font: Font

func _ready() -> void:
	_font = ThemeDB.fallback_font
	_db = ItemDB.build()
	_equipped = Resolver.combine([], _tier)  # empty: harmless placeholder
	_spawn_chamber()
	_build_ui()
	_log("Welcome. You are a soldier on a real mission. Probably. (Tier 1)")
	_log("Try: M16 + Can of Anchovies -> Combine -> click to fire.")

# =============================================================================
# WORLD
# =============================================================================

func _spawn_chamber() -> void:
	_targets.clear()
	for i in range(5):
		var x := 120.0 + i * 150.0
		_targets.append({
			"rect": Rect2(x, 80.0, 70.0, 70.0),
			"hp": 30.0, "max_hp": 30.0, "alive": true, "respawn": 0.0,
		})
	_dummy = {
		"pos": Vector2(PLAY_W * 0.5, 260.0),
		"dir": 1.0, "hp": 60.0, "max_hp": 60.0,
		"slow": 0.0, "snare": 0.0, "alive": true, "respawn": 0.0,
	}
	_loot.clear()
	for i in range(10):
		_loot.append({
			"pos": Vector2(80.0 + randf() * (PLAY_W - 160.0), 420.0 + randf() * 240.0),
			"collected": false,
		})

func _process(delta: float) -> void:
	_handle_input(delta)
	_update_dummy(delta)
	_update_targets(delta)
	_update_projectiles(delta)
	_update_loot(delta)
	if _fire_timer > 0.0:
		_fire_timer -= delta
	queue_redraw()

func _handle_input(delta: float) -> void:
	var move := Vector2.ZERO
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP): move.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN): move.y += 1.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT): move.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): move.x += 1.0
	if move != Vector2.ZERO:
		_player += move.normalized() * PLAYER_SPEED * delta
	_player.x = clampf(_player.x, MARGIN + 10.0, PLAY_W - MARGIN - 10.0)
	_player.y = clampf(_player.y, MARGIN + 10.0, PLAY_H - MARGIN - 10.0)

	var mouse := get_global_mouse_position()
	if mouse.x < PLAY_W:
		_aim = (mouse - _player).normalized()
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) and _fire_timer <= 0.0:
			_fire()
			_fire_timer = FIRE_COOLDOWN

func _fire() -> void:
	if _equipped == null:
		return
	match _equipped.category:
		Gadget.Category.DUD:
			_log("*click* %s does nothing. As expected." % _equipped.display_name)
		Gadget.Category.UTILITY:
			_log("%s is passive — loot vacuums up on its own. Just walk near it." % _equipped.display_name)
		_:
			_projectiles.append({
				"pos": _player + _aim * 26.0,
				"vel": _aim * _equipped.projectile_speed,
				"gadget": _equipped,
				"life": 2.2,
			})

func _update_dummy(delta: float) -> void:
	if not _dummy["alive"]:
		_dummy["respawn"] -= delta
		if _dummy["respawn"] <= 0.0:
			_dummy["alive"] = true
			_dummy["hp"] = _dummy["max_hp"]
		return
	_dummy["slow"] = maxf(0.0, _dummy["slow"] - delta)
	_dummy["snare"] = maxf(0.0, _dummy["snare"] - delta)
	var speed := 140.0
	if _dummy["snare"] > 0.0:
		speed = 0.0
	elif _dummy["slow"] > 0.0:
		speed = 40.0
	_dummy["pos"].x += _dummy["dir"] * speed * delta
	if _dummy["pos"].x < 120.0:
		_dummy["pos"].x = 120.0; _dummy["dir"] = 1.0
	elif _dummy["pos"].x > PLAY_W - 120.0:
		_dummy["pos"].x = PLAY_W - 120.0; _dummy["dir"] = -1.0

func _update_targets(delta: float) -> void:
	for t in _targets:
		if not t["alive"]:
			t["respawn"] -= delta
			if t["respawn"] <= 0.0:
				t["alive"] = true
				t["hp"] = t["max_hp"]

func _update_projectiles(delta: float) -> void:
	var survivors: Array[Dictionary] = []
	for p in _projectiles:
		var g: Gadget = p["gadget"]
		if g.homing:
			var target_pos := _nearest_enemy_pos(p["pos"])
			if target_pos != Vector2.INF:
				var desired := (target_pos - p["pos"]).normalized() * g.projectile_speed
				p["vel"] = p["vel"].lerp(desired, 0.12)
		p["pos"] += p["vel"] * delta
		p["life"] -= delta

		var hit := _resolve_projectile_hit(p, g)
		if hit:
			continue
		if p["life"] <= 0.0 or _out_of_play(p["pos"]):
			continue
		survivors.append(p)
	_projectiles = survivors

func _resolve_projectile_hit(p: Dictionary, g: Gadget) -> bool:
	# Targets
	for t in _targets:
		if t["alive"] and t["rect"].has_point(p["pos"]):
			_apply_hit(p["pos"], g)
			return true
	# Dummy
	if _dummy["alive"] and p["pos"].distance_to(_dummy["pos"]) < 24.0:
		_apply_hit(p["pos"], g)
		return true
	return false

func _apply_hit(at: Vector2, g: Gadget) -> void:
	if g.harmless and g.category == Gadget.Category.DAMAGE:
		_log("%s connects. The target is unharmed but visibly unsettled." % g.display_name)
		return

	if g.category == Gadget.Category.CONTROL:
		if _dummy["alive"] and at.distance_to(_dummy["pos"]) < 60.0:
			if g.control == "snare":
				_dummy["snare"] = 2.2
				_log("%s snares the dummy in place." % g.display_name)
			else:
				_dummy["slow"] = 3.0
				_log("%s slows the dummy to a crawl." % g.display_name)
		if g.damage > 0.0:
			_damage_at(at, g.damage, g.aoe)
		return

	# DAMAGE
	_damage_at(at, g.damage, g.aoe)
	if g.aoe > 0.0:
		_log("%s detonates (%d dmg, splash)." % [g.display_name, int(g.damage)])

func _damage_at(at: Vector2, dmg: float, aoe: float) -> void:
	for t in _targets:
		if not t["alive"]:
			continue
		var center := t["rect"].position + t["rect"].size * 0.5
		if t["rect"].has_point(at) or (aoe > 0.0 and center.distance_to(at) < aoe):
			t["hp"] -= dmg
			if t["hp"] <= 0.0:
				t["alive"] = false
				t["respawn"] = 3.0
	if _dummy["alive"]:
		if _dummy["pos"].distance_to(at) < (24.0 if aoe <= 0.0 else aoe):
			_dummy["hp"] -= dmg
			if _dummy["hp"] <= 0.0:
				_dummy["alive"] = false
				_dummy["respawn"] = 2.5
				_log("The dummy gives up the ghost. (It'll be back.)")

func _update_loot(delta: float) -> void:
	if _equipped == null or not _equipped.auto_collect:
		return
	for l in _loot:
		if l["collected"]:
			continue
		var d := l["pos"].distance_to(_player)
		if d < 230.0:
			l["pos"] = l["pos"].lerp(_player, 0.10)
			if d < 26.0:
				l["collected"] = true
				_loot_collected += 1

func _nearest_enemy_pos(from: Vector2) -> Vector2:
	var best := Vector2.INF
	var best_d := INF
	if _dummy["alive"]:
		best = _dummy["pos"]; best_d = from.distance_to(_dummy["pos"])
	for t in _targets:
		if not t["alive"]:
			continue
		var c := t["rect"].position + t["rect"].size * 0.5
		var d := from.distance_to(c)
		if d < best_d:
			best_d = d; best = c
	return best

func _out_of_play(pos: Vector2) -> bool:
	return pos.x < 0.0 or pos.x > PLAY_W or pos.y < 0.0 or pos.y > PLAY_H

# =============================================================================
# DRAW
# =============================================================================

func _draw() -> void:
	# Play area
	draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0.10, 0.11, 0.14))
	draw_rect(Rect2(MARGIN, MARGIN, PLAY_W - MARGIN * 2, PLAY_H - MARGIN * 2), Color(0.16, 0.17, 0.21))
	# Section captions
	_text(Vector2(MARGIN + 6, MARGIN + 22), "TARGETS", Color(0.5, 0.55, 0.6), 14)
	_text(Vector2(MARGIN + 6, 230), "MOVING DUMMY (slow / snare it)", Color(0.5, 0.55, 0.6), 14)
	_text(Vector2(MARGIN + 6, 408), "LOOT (equip Harvester to auto-collect)", Color(0.5, 0.55, 0.6), 14)

	# Loot
	for l in _loot:
		if not l["collected"]:
			draw_rect(Rect2(l["pos"] - Vector2(5, 5), Vector2(10, 10)), Color(0.95, 0.82, 0.25))

	# Targets
	for t in _targets:
		if t["alive"]:
			draw_rect(t["rect"], Color(0.55, 0.30, 0.30))
			var frac: float = clampf(t["hp"] / t["max_hp"], 0.0, 1.0)
			draw_rect(Rect2(t["rect"].position + Vector2(0, -8), Vector2(t["rect"].size.x * frac, 5)), Color(0.4, 0.8, 0.4))
		else:
			draw_rect(t["rect"], Color(0.20, 0.20, 0.24))

	# Dummy
	if _dummy["alive"]:
		var col := Color(0.70, 0.65, 0.45)
		if _dummy["snare"] > 0.0: col = Color(0.65, 0.40, 0.80)
		elif _dummy["slow"] > 0.0: col = Color(0.40, 0.60, 0.85)
		draw_circle(_dummy["pos"], 22.0, col)
		var hp_frac: float = clampf(_dummy["hp"] / _dummy["max_hp"], 0.0, 1.0)
		draw_rect(Rect2(_dummy["pos"] + Vector2(-22, -34), Vector2(44.0 * hp_frac, 5)), Color(0.4, 0.8, 0.4))

	# Projectiles
	for p in _projectiles:
		var g: Gadget = p["gadget"]
		var r := 6.0 if not g.homing else 8.0
		draw_circle(p["pos"], r, g.color)

	# Player + aim
	draw_circle(_player, 14.0, Color(0.85, 0.85, 0.9))
	draw_line(_player, _player + _aim * 30.0, Color(0.9, 0.9, 0.5), 3.0)

	# In-world HUD
	var hud := "TIER %d   ·   Equipped: %s [%s]   ·   Loot: %d" % [
		_tier, _equipped.display_name, _equipped.category_name(), _loot_collected]
	_text(Vector2(MARGIN + 6, PLAY_H - 18), hud, Color(0.8, 0.82, 0.85), 15)
	_text(Vector2(MARGIN + 6, PLAY_H - 40), "WASD move · mouse aim · click to use", Color(0.5, 0.52, 0.55), 13)

func _text(pos: Vector2, s: String, col: Color, size: int) -> void:
	draw_string(_font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

# =============================================================================
# UI
# =============================================================================

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)

	var bg := ColorRect.new()
	bg.color = Color(0.13, 0.14, 0.17)
	bg.position = Vector2(PLAY_W, 0)
	bg.size = Vector2(PANEL_W, PLAY_H)
	layer.add_child(bg)

	var root := VBoxContainer.new()
	root.position = Vector2(PLAY_W + 12, 10)
	root.size = Vector2(PANEL_W - 24, PLAY_H - 20)
	root.add_theme_constant_override("separation", 6)
	layer.add_child(root)

	_add_title(root, "THIS IS NOT A WEAPON")
	_add_caption(root, "graybox · prove the combine verb is fun")

	# Tier selector
	_add_caption(root, "SIMULATION INTEGRITY (tier):")
	var tier_row := HBoxContainer.new()
	root.add_child(tier_row)
	for i in range(1, 4):
		var b := Button.new()
		b.text = "Tier %d" % i
		b.toggle_mode = true
		b.pressed.connect(_on_tier_pressed.bind(i))
		tier_row.add_child(b)
		_tier_buttons.append(b)
	_refresh_tier_buttons()

	# Inventory
	_add_caption(root, "INVENTORY  (click to add to pot)")
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(0, 250)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(grid)
	var ids := _db.keys()
	ids.sort()
	for id in ids:
		var it: Item = _db[id]
		var b := Button.new()
		b.text = it.display_name
		b.tooltip_text = "slots: %s\ntags: %s" % [", ".join(it.slots), ", ".join(it.tags)]
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(_on_item_pressed.bind(it))
		grid.add_child(b)

	# Pot
	_add_caption(root, "COMBINE POT  (max 3)")
	_pot_label = Label.new()
	_pot_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pot_label.text = "(empty)"
	root.add_child(_pot_label)
	var pot_row := HBoxContainer.new()
	root.add_child(pot_row)
	var combine_btn := Button.new()
	combine_btn.text = "  COMBINE  "
	combine_btn.pressed.connect(_on_combine_pressed)
	pot_row.add_child(combine_btn)
	var clear_btn := Button.new()
	clear_btn.text = "Clear"
	clear_btn.pressed.connect(_on_clear_pressed)
	pot_row.add_child(clear_btn)

	# Equipped
	_add_caption(root, "EQUIPPED")
	_equipped_label = RichTextLabel.new()
	_equipped_label.fit_content = true
	_equipped_label.custom_minimum_size = Vector2(0, 76)
	_equipped_label.bbcode_enabled = true
	root.add_child(_equipped_label)
	_refresh_equipped()

	# Log
	_add_caption(root, "LOG")
	_log_label = RichTextLabel.new()
	_log_label.bbcode_enabled = true
	_log_label.scroll_following = true
	_log_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_log_label.custom_minimum_size = Vector2(0, 120)
	root.add_child(_log_label)

func _add_title(parent: Node, s: String) -> void:
	var l := Label.new()
	l.text = s
	l.add_theme_font_size_override("font_size", 20)
	parent.add_child(l)

func _add_caption(parent: Node, s: String) -> void:
	var l := Label.new()
	l.text = s
	l.add_theme_color_override("font_color", Color(0.55, 0.6, 0.68))
	l.add_theme_font_size_override("font_size", 13)
	parent.add_child(l)

# --- UI callbacks ------------------------------------------------------------

func _on_tier_pressed(tier: int) -> void:
	_tier = tier
	_refresh_tier_buttons()
	match tier:
		1: _log("Tier 1: reality is firm. You can only swap ammo in a real gun.")
		2: _log("Tier 2: the seams show. You can bolt weird modifiers onto weapons.")
		3: _log("Tier 3: the rules are gone. Build anything from anything.")

func _refresh_tier_buttons() -> void:
	for i in range(_tier_buttons.size()):
		_tier_buttons[i].button_pressed = (i + 1 == _tier)

func _on_item_pressed(it: Item) -> void:
	if _pot.size() >= 3:
		_log("Pot is full (3). Combine or clear it first.")
		return
	_pot.append(it)
	_refresh_pot()

func _on_clear_pressed() -> void:
	_pot.clear()
	_refresh_pot()

func _on_combine_pressed() -> void:
	if _pot.is_empty():
		_log("Nothing in the pot.")
		return
	var names: Array[String] = []
	for it in _pot:
		names.append(it.display_name)
	var result := Resolver.combine(_pot, _tier)
	_equipped = result
	_refresh_equipped()
	_log("[b]%s[/b] + ... -> [b]%s[/b]" % [" + ".join(names), result.display_name])
	_log("  \"%s\"" % result.description)
	_pot.clear()
	_refresh_pot()

func _refresh_pot() -> void:
	if _pot.is_empty():
		_pot_label.text = "(empty)"
		return
	var names: Array[String] = []
	for it in _pot:
		names.append(it.display_name)
	_pot_label.text = " + ".join(names)

func _refresh_equipped() -> void:
	if _equipped == null:
		_equipped_label.text = "(nothing)"
		return
	_equipped_label.text = "[b]%s[/b]  [%s]\n[color=#9aa]%s[/color]" % [
		_equipped.display_name, _equipped.category_name(), _equipped.description]

func _log(s: String) -> void:
	_log_lines.append(s)
	if _log_lines.size() > 40:
		_log_lines.pop_front()
	if _log_label != null:
		_log_label.text = "\n".join(_log_lines)
