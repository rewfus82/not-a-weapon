extends Node2D
## Zombie-wave survival graybox for "This Is Not A Weapon".
##
## The loop: SCAVENGE/BUILD phase (loot junk, combine at the bench, equip; a
## countdown ticks to the next wave — press SPACE to start early) -> WAVE phase
## (zombies pour in and chase you; fight with what you built; kills drop junk) ->
## repeat, harder. Die and you lose the run.
##
## Still squares + text, deterministic Resolver (no AI). Controls: WASD move,
## mouse aim, left-click use gadget, SPACE start wave early, R restart on death.

enum Phase { BUILD, WAVE, GAME_OVER }

const PANEL_W := 360.0
const PLAY_W := 1280.0 - PANEL_W
const PLAY_H := 720.0
const MARGIN := 14.0
const PLAYER_SPEED := 300.0
const PLAYER_RADIUS := 14.0
const FIRE_COOLDOWN := 0.16
const BUILD_TIME := 20.0
const PLAYER_MAX_HP := 100.0
const INVULN_TIME := 0.6
const DEBUG := true   # dev: auto-stocks every item each run; press G to top up (flip off for release)

# --- AI combine bridge (the Python brain served over HTTP; see combine/serve.py) ---
const AI_URL := "http://127.0.0.1:8777/resolve"
const SLOT_NAMES := ["DELIVERY", "DAMAGE", "UTILITY", "MODIFIER"]  # bench position -> slot
var _http: HTTPRequest
var _ai_busy := false
var _ai_pending: Array[String] = []
var _awakening := 1.0   # 0..1 lucidity/insight; 1.0 = full "try anything" for testing

var _db: Dictionary
var _phase: int = Phase.BUILD
var _phase_timer := 0.0
var _wave := 0
var _paused := false

# --- player ------------------------------------------------------------------
var _player := Vector2(PLAY_W * 0.5, PLAY_H * 0.5)
var _aim := Vector2.RIGHT
var _hp := PLAYER_MAX_HP
var _invuln := 0.0
var _hurt_flash := 0.0
var _fire_timer := 0.0
var _lmb_edge := false                # left-button pressed THIS frame (for semi-auto)
var _shield := 0.0                    # SELF gadgets: absorbs damage before HP
var _speed_mult := 1.0
var _speed_timer := 0.0

# --- crafting ----------------------------------------------------------------
var _inv: Dictionary = {}             # item_id -> count
var _pot: Array[String] = []
var _arsenal: Array[Gadget] = []      # crafted weapons you can hold + switch between
var _equipped_idx := 0
var _equipped: Gadget = null          # always points at _arsenal[_equipped_idx]

# --- world -------------------------------------------------------------------
var _zombies: Array[Dictionary] = []
var _pickups_root: Node2D             # container node for Pickup entities (dropped loot)
var _sites: Array[Dictionary] = []    # scavenge points: {rect, label, looted}
var _projectiles: Array[Dictionary] = []
var _traps: Array[Dictionary] = []    # placed traps: {pos, gadget, life}
var _melee_anim: Dictionary = {}      # transient swing visual
var _beam_anim: Dictionary = {}       # transient beam visual: {a, b, life, col}
var _arcs: Array[Dictionary] = []     # chain-lightning arcs: {a, b, life}
var _turrets: Array[Dictionary] = []  # deployed turrets: {pos, life, dmg, cd, color}
var _decoys: Array[Dictionary] = []   # deployed decoys: {pos, life, range}
var _dmg_nums: Array[Dictionary] = [] # {pos, text, life, col}
var _particles: Array[Dictionary] = []
var _rings: Array[Dictionary] = []    # expanding shockwave rings: {pos, r, max_r, life, life0, col, w}
var _muzzle: Dictionary = {}          # transient muzzle flash: {pos, life}
var _hitstop := 0.0                   # brief freeze-frame on impactful hits (game feel)
var _to_spawn := 0
var _spawn_timer := 0.0
var _shake := 0.0
var _log_lines: Array[String] = []

# --- ui ----------------------------------------------------------------------
var _font: Font
var _grid: GridContainer
var _pot_label: Label
var _arsenal_box: VBoxContainer
var _equipped_label: RichTextLabel
var _log_label: RichTextLabel
var _icons: Dictionary = {}   # item_id -> Texture2D (game-icons svg), cached

func _item_icon(id: String) -> Texture2D:
	if _icons.has(id):
		return _icons[id]
	var path := "res://assets/icons/%s.svg" % id
	var tex: Texture2D = load(path) if ResourceLoader.exists(path) else null
	_icons[id] = tex
	return tex

const TDS := "res://assets/kenney/topdown-shooter/PNG/"
# preload entity scripts by path (avoids relying on class_name global registration,
# which needs an editor rescan that external file edits don't trigger)
const PickupNode := preload("res://scripts/pickup.gd")
var _tex_player: Texture2D
var _tex_zombie: Texture2D
var _tex_ground: Texture2D
var _shake_off := Vector2.ZERO
var _glitch_mat: ShaderMaterial   # the full-screen simulation-glitch post-process
var _glitch := 0.0                # transient glitch pulse (decays); base from _awakening

func _ready() -> void:
	_font = ThemeDB.fallback_font
	_db = ItemDB.build()
	_tex_player = _tex(TDS + "Survivor 1/survivor1_gun.png")
	_tex_zombie = _tex(TDS + "Zombie 1/zoimbie1_hold.png")
	_tex_ground = _tex(TDS + "Tiles/tile_01.png")
	_spawn_sites()
	_build_ui()
	_pickups_root = Node2D.new()
	add_child(_pickups_root)
	_setup_atmosphere()
	_restart()

func _setup_atmosphere() -> void:
	# WorldEnvironment — 2D glow/bloom on the brightest pixels (muzzle, particles, FX)
	var env := Environment.new()
	env.background_mode = Environment.BG_CANVAS
	env.glow_enabled = true
	env.glow_intensity = 0.9
	env.glow_bloom = 0.25
	env.glow_hdr_threshold = 0.85
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	# full-screen simulation-glitch post-process (a ColorRect on a top CanvasLayer)
	var layer := CanvasLayer.new()
	layer.layer = 100
	add_child(layer)
	var rect := ColorRect.new()
	rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE   # let clicks pass to the UI below
	_glitch_mat = ShaderMaterial.new()
	_glitch_mat.shader = load("res://shaders/glitch.gdshader")
	rect.material = _glitch_mat
	layer.add_child(rect)

func _glitch_pulse(amount: float) -> void:
	_glitch = maxf(_glitch, amount)

func _tex(path: String) -> Texture2D:
	return load(path) if ResourceLoader.exists(path) else null

# draw a texture centered at pos, rotated, scaled to target_h, then restore the
# frame's shake transform (so following primitive draws stay aligned)
func _blit(t: Texture2D, pos: Vector2, rot: float, target_h: float, mod := Color.WHITE) -> void:
	if t == null:
		return
	var sz := t.get_size()
	var s := target_h / sz.y
	draw_set_transform(_shake_off + pos, rot, Vector2(s, s))
	draw_texture(t, -sz * 0.5, mod)
	draw_set_transform(_shake_off, 0.0, Vector2.ONE)

# =============================================================================
# LIFECYCLE
# =============================================================================

func _spawn_sites() -> void:
	_sites = [
		{"rect": Rect2(80, 70, 120, 80),   "label": "HOUSE",   "looted": false},
		{"rect": Rect2(PLAY_W - 220, 70, 130, 70), "label": "CAR", "looted": false},
		{"rect": Rect2(90, PLAY_H - 170, 110, 70), "label": "DUMPSTER", "looted": false},
		{"rect": Rect2(PLAY_W - 210, PLAY_H - 160, 120, 70), "label": "CORPSE PILE", "looted": false},
	]

func _restart() -> void:
	_wave = 0
	_hp = PLAYER_MAX_HP
	_player = Vector2(PLAY_W * 0.5, PLAY_H * 0.5)
	_zombies.clear(); _projectiles.clear()
	_clear_pickups()
	_dmg_nums.clear(); _particles.clear(); _pot.clear()
	_traps.clear(); _turrets.clear(); _decoys.clear(); _arcs.clear()
	_rings.clear(); _muzzle = {}; _hitstop = 0.0
	_invuln = 0.0; _hurt_flash = 0.0; _shake = 0.0; _paused = false
	_shield = 0.0; _speed_mult = 1.0; _speed_timer = 0.0
	_arsenal = [_starter_gadget()]
	_equipped_idx = 0
	_equipped = _arsenal[0]
	_inv = {"wire_hanger": 1, "pixie_stix": 1, "potato": 1, "zip_ties": 1,
			"ketchup": 1, "feathers": 1, "anchovies": 1, "pringles": 1}
	_log("You wake up. Something is very wrong. (WASD move, mouse aim, click to fire.)")
	_start_build()
	if DEBUG: _grant_all()
	_refresh_inventory_ui()
	_refresh_equipped()
	_refresh_arsenal_ui()

func _equip(i: int) -> void:
	if i < 0 or i >= _arsenal.size():
		return
	_equipped_idx = i
	_equipped = _arsenal[i]
	_refresh_equipped()
	_refresh_arsenal_ui()

func _starter_gadget() -> Gadget:
	var g := Gadget.new()
	g.display_name = "Rusty Pistol"
	g.description = "Standard issue. Reliable, boring, yours."
	g.delivery = Gadget.Delivery.PROJECTILE
	g.add(Gadget.DAMAGE, 8.0)
	g.projectile_speed = 720.0
	g.uses_ammo = true
	g.ammo_max = 14
	g.color = Color(0.85, 0.82, 0.5)
	g.fill_plain()
	return g

func _start_build() -> void:
	_phase = Phase.BUILD
	_phase_timer = BUILD_TIME
	for s in _sites:
		s["looted"] = false
	_log("Scavenge & build. Next wave in %ds — or press SPACE." % int(BUILD_TIME))

func _start_wave() -> void:
	_wave += 1
	_phase = Phase.WAVE
	_to_spawn = 5 + _wave * 3
	_spawn_timer = 0.0
	_glitch_pulse(0.22)
	_log("WAVE %d. They're coming. (%d incoming)" % [_wave, _to_spawn])

func _game_over() -> void:
	_phase = Phase.GAME_OVER
	_log("You died on wave %d. Press R to wake up again." % _wave)

# =============================================================================
# UPDATE
# =============================================================================

func _process(delta: float) -> void:
	_fire_timer = maxf(0.0, _fire_timer - delta)
	_invuln = maxf(0.0, _invuln - delta)
	_hurt_flash = maxf(0.0, _hurt_flash - delta)
	_shake = maxf(0.0, _shake - delta * 22.0)
	_glitch = maxf(0.0, _glitch - delta * 2.5)
	if _glitch_mat != null:
		_glitch_mat.set_shader_parameter("glitch", clampf(lerpf(0.0, 0.05, _awakening) + _glitch, 0.0, 1.0))
	if _speed_timer > 0.0:
		_speed_timer -= delta
		if _speed_timer <= 0.0: _speed_mult = 1.0
	if not _melee_anim.is_empty():
		_melee_anim["life"] = float(_melee_anim["life"]) - delta
		if _melee_anim["life"] <= 0.0:
			_melee_anim = {}
	if not _beam_anim.is_empty():
		_beam_anim["life"] = float(_beam_anim["life"]) - delta
		if _beam_anim["life"] <= 0.0:
			_beam_anim = {}
	if not _muzzle.is_empty():
		_muzzle["life"] = float(_muzzle["life"]) - delta
		if _muzzle["life"] <= 0.0:
			_muzzle = {}
	_update_juice(delta)

	if _phase == Phase.GAME_OVER:
		if Input.is_key_pressed(KEY_R):
			_restart()
		queue_redraw()
		return

	if _paused:
		_lmb_edge = false   # don't queue a shot while paused
		queue_redraw()
		return

	# hit-stop: a few ms of frozen gameplay on impactful hits makes them land harder
	if _hitstop > 0.0:
		_hitstop = maxf(0.0, _hitstop - delta)
		queue_redraw()
		return

	_handle_input(delta)
	_update_loot(delta)
	_update_projectiles(delta)

	if _phase == Phase.BUILD:
		_update_build(delta)
	elif _phase == Phase.WAVE:
		_update_wave(delta)

	queue_redraw()

func _handle_input(delta: float) -> void:
	var move := Vector2.ZERO
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP): move.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN): move.y += 1.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT): move.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): move.x += 1.0
	if move != Vector2.ZERO:
		_player += move.normalized() * PLAYER_SPEED * _speed_mult * delta
	_player.x = clampf(_player.x, MARGIN + PLAYER_RADIUS, PLAY_W - MARGIN - PLAYER_RADIUS)
	_player.y = clampf(_player.y, MARGIN + PLAYER_RADIUS, PLAY_H - MARGIN - PLAYER_RADIUS)

	var mouse := get_global_mouse_position()
	if mouse.x < PLAY_W:
		_aim = (mouse - _player).normalized()
		var held := Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)
		var want := _lmb_edge if (_equipped != null and _equipped.semi) else held
		if want and _fire_timer <= 0.0:
			_fire()  # sets its own cooldown per delivery
	_lmb_edge = false  # consume the click edge each frame

	# switch weapons with the number keys
	for n in range(mini(9, _arsenal.size())):
		if Input.is_key_pressed(KEY_1 + n):
			_equip(n)

func _input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			_lmb_edge = true   # consumed in _handle_input; gated by play-area position
		elif event.button_index == MOUSE_BUTTON_WHEEL_UP and not _arsenal.is_empty():
			_equip((_equipped_idx - 1 + _arsenal.size()) % _arsenal.size())
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN and not _arsenal.is_empty():
			_equip((_equipped_idx + 1) % _arsenal.size())
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE and _phase != Phase.GAME_OVER:
			_paused = not _paused
			_log("[ PAUSED ]" if _paused else "[ unpaused ]")
		elif DEBUG and event.keycode == KEY_G:
			_grant_all()
		elif DEBUG and event.keycode == KEY_T:
			_spawn_all_specials()

func _grant_all() -> void:
	for id in _db:
		_inv[id] = maxi(int(_inv.get(id, 0)), 9)
	_log("[DEBUG] stocked every item x9. (G top up · T spawn all specials)")
	_refresh_inventory_ui()

func _spawn_all_specials() -> void:
	var n := 0
	for key in Resolver.special_recipes():
		var ids := String(key).split(",")
		var items: Array[Item] = []
		for id in ids:
			if _db.has(id): items.append(_db[id])
		if items.size() == ids.size() and not items.is_empty():
			_arsenal.append(Resolver.combine(items))
			n += 1
	if not _arsenal.is_empty(): _equip(_arsenal.size() - 1)
	_log("[DEBUG] added %d special weapons to your arsenal." % n)
	_refresh_arsenal_ui()

func _update_build(delta: float) -> void:
	_phase_timer -= delta
	# walk into a scavenge site to loot it (once per build phase)
	for s in _sites:
		if not s["looted"] and s["rect"].has_point(_player):
			s["looted"] = true
			var id: String = _db.keys().pick_random()
			_grant(id, "Scavenged %s from the %s." % [_db[id].display_name, s["label"]])
	if _phase_timer <= 0.0:
		_start_wave()

func _update_wave(delta: float) -> void:
	# spawn the wave over time from the edges
	if _to_spawn > 0:
		_spawn_timer -= delta
		if _spawn_timer <= 0.0:
			_spawn_zombie()
			_to_spawn -= 1
			_spawn_timer = maxf(0.25, 1.2 - _wave * 0.05)
	# update zombies
	var alive: Array[Dictionary] = []
	for z in _zombies:
		if z.get("dead", false):
			continue  # killed this frame — drop it (don't re-add)
		z["flash"] = maxf(0.0, z["flash"] - delta)
		z["slow"] = maxf(0.0, z["slow"] - delta)
		z["snare"] = maxf(0.0, z["snare"] - delta)
		z["freeze"] = maxf(0.0, float(z.get("freeze", 0.0)) - delta)
		z["scale"] = minf(1.0, float(z.get("scale", 1.0)) + delta * 5.0)      # spawn grow-in
		z["squash"] = maxf(0.0, float(z.get("squash", 0.0)) - delta * 5.0)    # hit-pop decay
		if float(z.get("burn_t", 0.0)) > 0.0:
			z["burn_t"] = float(z["burn_t"]) - delta
			z["hp"] = float(z["hp"]) - float(z.get("burn", 0.0)) * delta
			if z["hp"] <= 0.0:
				_on_zombie_death(z)
				continue
		var spd: float = z["speed"]
		if z["freeze"] > 0.0 or z["snare"] > 0.0: spd = 0.0
		elif z["slow"] > 0.0: spd *= 0.35
		var target: Vector2 = _player
		var bd := INF
		for d in _decoys:
			var dd: float = (z["pos"] as Vector2).distance_to(d["pos"])
			if dd < float(d["range"]) and dd < bd:
				bd = dd; target = d["pos"]
		var to_target: Vector2 = target - (z["pos"] as Vector2)
		z["pos"] += to_target.normalized() * spd * delta + z["knock"] * delta
		z["knock"] = z["knock"].lerp(Vector2.ZERO, 0.12)
		# contact damage
		if z["pos"].distance_to(_player) < PLAYER_RADIUS + 13.0 and _invuln <= 0.0:
			var dmg: float = z["dmg"]
			if _shield > 0.0:
				var ab := minf(_shield, dmg); _shield -= ab; dmg -= ab
			if dmg > 0.0: _hp -= dmg
			_invuln = INVULN_TIME
			_hurt_flash = 0.4
			_shake = 8.0
			_freeze(0.05)
			_glitch_pulse(0.3)
			_ring(_player, Color(0.9, 0.2, 0.2), 44.0, 3.0, 0.28)
			if _hp <= 0.0:
				_game_over()
				return
		alive.append(z)
	_zombies = alive
	_update_aura(delta)
	_update_traps(delta)
	_update_turrets(delta)
	_update_decoys(delta)
	# wave clear?
	if _to_spawn <= 0 and _zombies.is_empty():
		_log("Wave %d cleared." % _wave)
		_start_build()

func _spawn_zombie() -> void:
	var edge := randi() % 4
	var p := Vector2.ZERO
	match edge:
		0: p = Vector2(randf_range(MARGIN, PLAY_W - MARGIN), MARGIN + 6)
		1: p = Vector2(randf_range(MARGIN, PLAY_W - MARGIN), PLAY_H - MARGIN - 6)
		2: p = Vector2(MARGIN + 6, randf_range(MARGIN, PLAY_H - MARGIN))
		_: p = Vector2(PLAY_W - MARGIN - 6, randf_range(MARGIN, PLAY_H - MARGIN))
	var hp := 18.0 + _wave * 6.0
	_zombies.append({
		"pos": p, "hp": hp, "max_hp": hp,
		"speed": minf(70.0 + _wave * 4.0, 150.0),
		"dmg": 8.0 + _wave, "flash": 0.0, "slow": 0.0, "snare": 0.0,
		"knock": Vector2.ZERO, "dead": false, "burn": 0.0, "burn_t": 0.0, "freeze": 0.0,
		"scale": 0.0, "squash": 0.0,   # scale eases in on spawn; squash pops on hit
	})

# --- firing / projectiles ----------------------------------------------------

func _fire() -> void:
	if _equipped == null:
		return
	var round_prof: Dictionary = {}
	if _equipped.uses_ammo:
		if _equipped.ammo_count() <= 0:
			_log("%s — out of ammo. Load junk into it at the bench." % _equipped.display_name)
			_fire_timer = 0.4
			return
		round_prof = _equipped.next_round()
	match _equipped.delivery:
		Gadget.Delivery.PROJECTILE:
			_fire_ranged(_equipped, false, round_prof); _fire_timer = FIRE_COOLDOWN
		Gadget.Delivery.LOBBED:
			_fire_ranged(_equipped, true, round_prof); _fire_timer = 0.5
		Gadget.Delivery.MELEE:
			_melee_swing(_equipped); _fire_timer = 0.2  # fast = continuous grind while held
		Gadget.Delivery.PLACED:
			_place_trap(_equipped); _fire_timer = 0.6
		Gadget.Delivery.CONE:
			_fire_cone(_equipped, round_prof); _fire_timer = 0.4
		Gadget.Delivery.BEAM:
			_fire_beam(_equipped); _fire_timer = 0.08
		Gadget.Delivery.RETURN:
			_fire_return(_equipped); _fire_timer = 0.45
		Gadget.Delivery.SELF:
			_use_self(_equipped); _fire_timer = 0.5
		Gadget.Delivery.TURRET:
			_deploy_turret(_equipped); _fire_timer = 0.6
		Gadget.Delivery.DECOY:
			_deploy_decoy(_equipped); _fire_timer = 0.6
		Gadget.Delivery.AURA:
			_fire_timer = 0.2  # passive; aura ticks each frame

func _fire_ranged(g: Gadget, lobbed: bool, ap: Dictionary) -> void:
	_muzzle_kick(g.color)
	_projectiles.append(_make_proj(_aim, g, lobbed, false, ap))
	var se := g.get_effect(Gadget.SPAWN)
	if not se.is_empty():
		for i in range(int(se["count"])):
			var dir := Vector2.from_angle(_aim.angle() + randf_range(-0.5, 0.5))
			_projectiles.append(_make_proj(dir, g, false, true, ap))

# Builds the shot from weapon effects + the loaded round's profile (ap). The same
# gun fires differently per round — feathers drag, anchovies bounce, etc.
func _make_proj(dir: Vector2, g: Gadget, lobbed: bool, sub: bool, ap: Dictionary) -> Dictionary:
	var dmg := g.amount_of(Gadget.DAMAGE) * float(ap.get("dmg_mult", 1.0))
	if g.harmless: dmg = minf(dmg, 1.0)
	var spd := maxf(g.projectile_speed, 300.0) * (0.6 if sub else 1.0)
	var pe := g.get_effect(Gadget.PIERCE)
	var pierce := (int(pe["count"]) if not pe.is_empty() else 0) + int(ap.get("pierce", 0))
	var o := _shot_onhit(g)
	if float(ap.get("slow", 0.0)) > float(o["slow"]): o["slow"] = float(ap["slow"])
	if float(ap.get("burn_amt", 0.0)) > 0.0: o["burn_amt"] = float(ap["burn_amt"]); o["burn_dur"] = float(ap.get("burn_dur", 0.0))
	if float(ap.get("explode_r", 0.0)) > 0.0: o["explode_r"] = float(ap["explode_r"]); o["explode_dmg"] = float(ap.get("explode_dmg", 0.0))
	if float(ap.get("freeze", 0.0)) > float(o["freeze"]): o["freeze"] = float(ap["freeze"])
	if int(ap.get("chain_count", 0)) > 0:
		o["chain_count"] = int(ap["chain_count"]); o["chain_dmg"] = float(ap.get("chain_dmg", 0.0)); o["chain_range"] = float(ap.get("chain_range", 0.0))
	return {"pos": _player + dir * 24.0, "vel": dir * spd, "dmg": dmg,
		"drag": float(ap.get("drag", 0.0)), "bounce": int(ap.get("bounce", 0)),
		"homing": g.homing or bool(ap.get("homing", false)) or sub,
		"pierce": pierce, "hits": [], "lobbed": lobbed, "sub": sub, "trail": [],
		"onhit": o, "color": ap.get("color", g.color), "life": 0.85 if lobbed else 1.8}

func _shot_onhit(g: Gadget) -> Dictionary:
	var o := {"knockback": 0.0, "slow": 0.0, "snare": 0.0, "burn_amt": 0.0, "burn_dur": 0.0,
		"explode_r": 0.0, "explode_dmg": 0.0, "freeze": 0.0, "chain_count": 0, "chain_dmg": 0.0, "chain_range": 0.0}
	var kn := g.get_effect(Gadget.KNOCKBACK)
	if not kn.is_empty(): o["knockback"] = float(kn["amount"])
	var sl := g.get_effect(Gadget.SLOW)
	if not sl.is_empty(): o["slow"] = float(sl["duration"])
	var sn := g.get_effect(Gadget.SNARE)
	if not sn.is_empty(): o["snare"] = float(sn["duration"])
	var bn := g.get_effect(Gadget.BURN)
	if not bn.is_empty(): o["burn_amt"] = float(bn["amount"]); o["burn_dur"] = float(bn["duration"])
	var ex := g.get_effect(Gadget.EXPLODE)
	if not ex.is_empty(): o["explode_r"] = float(ex["radius"]); o["explode_dmg"] = float(ex["amount"])
	var fz := g.get_effect(Gadget.FREEZE)
	if not fz.is_empty(): o["freeze"] = float(fz["duration"])
	var ch := g.get_effect(Gadget.CHAIN)
	if not ch.is_empty(): o["chain_count"] = int(ch["count"]); o["chain_dmg"] = float(ch["amount"]); o["chain_range"] = float(ch["radius"])
	return o

func _status_fc(z: Dictionary, freeze: float, cc: int, cd: float, cr: float) -> void:
	if freeze > 0.0:
		z["freeze"] = maxf(float(z.get("freeze", 0.0)), freeze)
	if cc > 0:
		_chain(z, cc, cd, cr)

func _chain(from_z: Dictionary, count: int, dmg: float, rng: float) -> void:
	var hit: Array = [from_z]
	var cur := from_z
	for j in range(count):
		var best: Dictionary = {}
		var bd := rng
		for z in _zombies:
			if z.get("dead", false) or hit.has(z):
				continue
			var d: float = (z["pos"] as Vector2).distance_to(cur["pos"])
			if d < bd:
				bd = d; best = z
		if best.is_empty():
			break
		_apply_damage(best, dmg, best["pos"])
		best["flash"] = 0.1
		_arcs.append({"a": cur["pos"], "b": best["pos"], "life": 0.12})
		hit.append(best)
		cur = best

func _melee_swing(g: Gadget) -> void:
	_melee_anim = {"pos": _player, "aim": _aim, "life": 0.14}
	_shake = maxf(_shake, 3.0)
	for z in _zombies:
		if z.get("dead", false):
			continue
		var to_z: Vector2 = (z["pos"] as Vector2) - _player
		if to_z.length() < 77.0 and to_z.normalized().dot(_aim) > 0.35:
			_apply_onhit(g, z, z["pos"])

func _place_trap(g: Gadget) -> void:
	if _traps.size() >= 4:
		_traps.pop_front()
	_traps.append({"pos": _player, "gadget": g, "life": 25.0})
	_log("Placed %s." % g.display_name)

func _fire_cone(g: Gadget, ap: Dictionary) -> void:
	_shake = maxf(_shake, 2.0)
	_muzzle_kick(g.color)
	for i in range(6):
		var ang := _aim.angle() + randf_range(-0.38, 0.38)
		var p := _make_proj(Vector2.from_angle(ang), g, false, false, ap)
		p["life"] = 0.32                  # short range = a spray, not a volley
		p["dmg"] = float(p["dmg"]) * 0.6  # many weak pellets
		_projectiles.append(p)

func _fire_beam(g: Gadget) -> void:
	var endp: Vector2 = _player + _aim * 360.0
	var o := _shot_onhit(g)
	var dmg := g.amount_of(Gadget.DAMAGE)
	if g.harmless: dmg = minf(dmg, 1.0)
	for z in _zombies:
		if z.get("dead", false):
			continue
		if _point_seg_dist(z["pos"], _player, endp) < 16.0:
			z["flash"] = 0.1
			if dmg > 0.0: _apply_damage(z, dmg, z["pos"])
			if float(o["slow"]) > 0.0: z["slow"] = maxf(z["slow"], float(o["slow"]))
			if float(o["burn_amt"]) > 0.0: z["burn"] = float(o["burn_amt"]); z["burn_t"] = float(o["burn_dur"])
			if float(o["freeze"]) > 0.0: z["freeze"] = maxf(float(z.get("freeze", 0.0)), float(o["freeze"]))
	_beam_anim = {"a": _player, "b": endp, "life": 0.09, "col": g.color}

func _point_seg_dist(p: Vector2, a: Vector2, b: Vector2) -> float:
	var ab := b - a
	var denom := ab.length_squared()
	var t := 0.0
	if denom > 0.0:
		t = clampf((p - a).dot(ab) / denom, 0.0, 1.0)
	return p.distance_to(a + ab * t)

func _fire_return(g: Gadget) -> void:
	var p := _make_proj(_aim, g, false, false, {})
	p["return"] = true
	p["returning"] = false
	p["origin"] = _player
	p["pierce"] = 99     # passes through everything, and re-hits on the way back
	p["life"] = 3.0
	_projectiles.append(p)

func _use_self(g: Gadget) -> void:
	var h := g.amount_of(Gadget.HEAL)
	if h > 0.0:
		_hp = minf(_hp + h, PLAYER_MAX_HP)
		_burst(_player, Color(0.4, 0.9, 0.4)); _log("Patched up (+%d HP)." % int(h))
	var s := g.amount_of(Gadget.SHIELD)
	if s > 0.0:
		_shield = maxf(_shield, s); _log("Shield up (%d)." % int(s))
	var sp := g.get_effect(Gadget.SPEED)
	if not sp.is_empty():
		_speed_mult = float(sp["amount"]); _speed_timer = float(sp["duration"]); _log("Speed boost.")

func _deploy_turret(g: Gadget) -> void:
	if _turrets.size() >= 4: _turrets.pop_front()
	_turrets.append({"pos": _player, "life": 14.0, "dmg": maxf(g.amount_of(Gadget.DAMAGE), 6.0), "cd": 0.0, "color": g.color})
	_log("Deployed %s." % g.display_name)

func _deploy_decoy(g: Gadget) -> void:
	if _decoys.size() >= 3: _decoys.pop_front()
	_decoys.append({"pos": _player, "life": 12.0, "range": 320.0})
	_log("Dropped %s. The horde turns to look." % g.display_name)

func _update_turrets(delta: float) -> void:
	var live: Array[Dictionary] = []
	for t in _turrets:
		t["life"] = float(t["life"]) - delta
		t["cd"] = float(t["cd"]) - delta
		if float(t["cd"]) <= 0.0:
			var target := _nearest_zombie(t["pos"])
			if target != Vector2.INF and (t["pos"] as Vector2).distance_to(target) < 260.0:
				var dir: Vector2 = (target - (t["pos"] as Vector2)).normalized()
				_projectiles.append({"pos": t["pos"], "vel": dir * 720.0, "dmg": float(t["dmg"]),
					"drag": 0.0, "bounce": 0, "homing": false, "pierce": 0, "hits": [], "lobbed": false,
					"sub": false, "onhit": _empty_onhit(), "color": t["color"], "life": 1.2})
				t["cd"] = 0.35
		if float(t["life"]) > 0.0: live.append(t)
	_turrets = live

func _update_decoys(delta: float) -> void:
	var live: Array[Dictionary] = []
	for d in _decoys:
		d["life"] = float(d["life"]) - delta
		if float(d["life"]) > 0.0: live.append(d)
	_decoys = live

func _empty_onhit() -> Dictionary:
	return {"knockback": 0.0, "slow": 0.0, "snare": 0.0, "burn_amt": 0.0, "burn_dur": 0.0,
		"explode_r": 0.0, "explode_dmg": 0.0, "freeze": 0.0, "chain_count": 0, "chain_dmg": 0.0, "chain_range": 0.0}

func _update_projectiles(delta: float) -> void:
	var live: Array[Dictionary] = []
	for p in _projectiles:
		if p["homing"] and not p["lobbed"] and not p.get("return", false):
			var t := _nearest_zombie(p["pos"])
			if t != Vector2.INF:
				var hv: Vector2 = p["vel"]
				p["vel"] = hv.lerp((t - p["pos"]).normalized() * hv.length(), 0.14)
		if p.get("return", false):
			var rpos: Vector2 = p["pos"]
			if not p["returning"]:
				if (rpos - (p["origin"] as Vector2)).length() > 280.0:
					p["returning"] = true
					p["hits"].clear()   # let it cut the crowd again on the way back
			else:
				var rv: Vector2 = p["vel"]
				p["vel"] = rv.lerp((_player - rpos).normalized() * rv.length(), 0.2)
				if rpos.distance_to(_player) < 22.0:
					continue  # caught it
		if float(p["drag"]) > 0.0:                       # feather rounds: fast, then float to a stop
			p["vel"] = (p["vel"] as Vector2) * maxf(0.0, 1.0 - float(p["drag"]) * delta)
		p["pos"] += p["vel"] * delta
		p["life"] -= delta
		var tr: Array = p.get("trail", [])              # motion trail for readability + feel
		tr.append(p["pos"])
		if tr.size() > 6: tr.pop_front()
		p["trail"] = tr
		# walls: ricochet if the round has bounces left, otherwise it's absorbed
		if int(p["bounce"]) > 0:
			var pos: Vector2 = p["pos"]
			var v: Vector2 = p["vel"]
			var b := false
			if pos.x < MARGIN or pos.x > PLAY_W - MARGIN:
				v.x = -v.x; pos.x = clampf(pos.x, MARGIN, PLAY_W - MARGIN); b = true
			if pos.y < MARGIN or pos.y > PLAY_H - MARGIN:
				v.y = -v.y; pos.y = clampf(pos.y, MARGIN, PLAY_H - MARGIN); b = true
			if b:
				p["vel"] = v; p["pos"] = pos; p["bounce"] = int(p["bounce"]) - 1
		elif _out_of_play(p["pos"]) and not p.get("return", false):
			if p["lobbed"]: _explode_at(p["pos"], p["onhit"])
			continue
		var spent := false
		for z in _zombies:
			if z.get("dead", false) or p["hits"].has(z):
				continue
			if (p["pos"] as Vector2).distance_to(z["pos"]) < 15.0:
				if p["lobbed"]:
					_explode_at(p["pos"], p["onhit"]); spent = true; break
				_apply_proj_hit(p, z)
				p["hits"].append(z)
				if int(p["pierce"]) <= 0:
					spent = true; break
				p["pierce"] = int(p["pierce"]) - 1
		if spent:
			continue
		if p["life"] <= 0.0:
			if p["lobbed"]: _explode_at(p["pos"], p["onhit"])
			continue
		live.append(p)
	_projectiles = live

func _apply_proj_hit(p: Dictionary, z: Dictionary) -> void:
	var o: Dictionary = p["onhit"]
	if float(o["explode_r"]) > 0.0:
		_explode_at(p["pos"], o); return
	z["flash"] = 0.1
	var dmg := float(p["dmg"])
	if dmg > 0.0: _apply_damage(z, dmg, p["pos"])
	if float(o["knockback"]) > 0.0: z["knock"] = ((z["pos"] as Vector2) - (p["pos"] as Vector2)).normalized() * float(o["knockback"])
	if float(o["slow"]) > 0.0: z["slow"] = maxf(z["slow"], float(o["slow"]))
	if float(o["snare"]) > 0.0: z["snare"] = maxf(z["snare"], float(o["snare"]))
	if float(o["burn_amt"]) > 0.0: z["burn"] = float(o["burn_amt"]); z["burn_t"] = float(o["burn_dur"])
	_status_fc(z, float(o["freeze"]), int(o["chain_count"]), float(o["chain_dmg"]), float(o["chain_range"]))

func _explode_at(at: Vector2, o: Dictionary) -> void:
	var r := float(o["explode_r"])
	if r <= 0.0: r = 80.0
	var dmg := float(o["explode_dmg"])
	_shake = maxf(_shake, 8.0)
	_burst(at, Color(0.98, 0.7, 0.25), 20, 300.0)
	_ring(at, Color(0.98, 0.65, 0.25), r, 4.0, 0.4)
	_freeze(0.06)
	for z in _zombies:
		if z.get("dead", false):
			continue
		if (z["pos"] as Vector2).distance_to(at) < r:
			if dmg > 0.0: _apply_damage(z, dmg, at)
			z["knock"] = ((z["pos"] as Vector2) - at).normalized() * 200.0
			if float(o["slow"]) > 0.0: z["slow"] = maxf(z["slow"], float(o["slow"]))
			if float(o["burn_amt"]) > 0.0: z["burn"] = float(o["burn_amt"]); z["burn_t"] = float(o["burn_dur"])
			if float(o.get("freeze", 0.0)) > 0.0: z["freeze"] = maxf(float(z.get("freeze", 0.0)), float(o["freeze"]))

func _apply_onhit(g: Gadget, z: Dictionary, at: Vector2) -> void:
	if g.has(Gadget.EXPLODE):
		_explode(at, g)
	else:
		_apply_payload(g, z, at)

func _apply_payload(g: Gadget, z: Dictionary, at: Vector2) -> void:
	z["flash"] = 0.1
	var dmg := g.amount_of(Gadget.DAMAGE)
	if g.harmless:
		dmg = minf(dmg, 1.0)
	if dmg > 0.0:
		_apply_damage(z, dmg, at)
	var kn := g.get_effect(Gadget.KNOCKBACK)
	if not kn.is_empty():
		z["knock"] = ((z["pos"] as Vector2) - at).normalized() * float(kn["amount"])
	var sl := g.get_effect(Gadget.SLOW)
	if not sl.is_empty():
		z["slow"] = maxf(z["slow"], float(sl["duration"]))
	var sn := g.get_effect(Gadget.SNARE)
	if not sn.is_empty():
		z["snare"] = maxf(z["snare"], float(sn["duration"]))
	var bn := g.get_effect(Gadget.BURN)
	if not bn.is_empty():
		z["burn"] = float(bn["amount"]); z["burn_t"] = float(bn["duration"])
	var fz := g.get_effect(Gadget.FREEZE)
	var ch := g.get_effect(Gadget.CHAIN)
	_status_fc(z,
		(float(fz["duration"]) if not fz.is_empty() else 0.0),
		(int(ch["count"]) if not ch.is_empty() else 0),
		(float(ch["amount"]) if not ch.is_empty() else 0.0),
		(float(ch["radius"]) if not ch.is_empty() else 0.0))

func _explode(at: Vector2, g: Gadget) -> void:
	var ex := g.get_effect(Gadget.EXPLODE)
	var r := float(ex["radius"]) if not ex.is_empty() else 80.0
	var dmg := float(ex["amount"]) if not ex.is_empty() else g.amount_of(Gadget.DAMAGE)
	_shake = maxf(_shake, 8.0)
	_burst(at, Color(0.98, 0.7, 0.25), 20, 300.0)
	_ring(at, Color(0.98, 0.65, 0.25), r, 4.0, 0.4)
	_freeze(0.06)
	for z in _zombies:
		if z.get("dead", false):
			continue
		if (z["pos"] as Vector2).distance_to(at) < r:
			if dmg > 0.0:
				_apply_damage(z, dmg, at)
			z["knock"] = ((z["pos"] as Vector2) - at).normalized() * 200.0
			var sl := g.get_effect(Gadget.SLOW)
			if not sl.is_empty(): z["slow"] = maxf(z["slow"], float(sl["duration"]))
			var sn := g.get_effect(Gadget.SNARE)
			if not sn.is_empty(): z["snare"] = maxf(z["snare"], float(sn["duration"]))
			var bn := g.get_effect(Gadget.BURN)
			if not bn.is_empty(): z["burn"] = float(bn["amount"]); z["burn_t"] = float(bn["duration"])

func _update_aura(delta: float) -> void:
	if _equipped == null or _equipped.delivery != Gadget.Delivery.AURA:
		return
	var ar := 150.0
	var ce := _equipped.get_effect(Gadget.COLLECT)
	if not ce.is_empty() and float(ce["radius"]) > 0.0:
		ar = float(ce["radius"])
	var dps := _equipped.amount_of(Gadget.DAMAGE) * 4.0
	var has_slow := _equipped.has(Gadget.SLOW)
	for z in _zombies:
		if z.get("dead", false):
			continue
		if (z["pos"] as Vector2).distance_to(_player) < ar:
			if dps > 0.0:
				z["hp"] = float(z["hp"]) - dps * delta
				z["flash"] = maxf(float(z.get("flash", 0.0)), 0.05)
				if z["hp"] <= 0.0:
					_on_zombie_death(z)
			if has_slow:
				z["slow"] = maxf(float(z["slow"]), 0.25)

func _update_traps(delta: float) -> void:
	var live: Array[Dictionary] = []
	for t in _traps:
		t["life"] = float(t["life"]) - delta
		var tg: Gadget = t["gadget"]
		var triggered := false
		for z in _zombies:
			if not z.get("dead", false) and (z["pos"] as Vector2).distance_to(t["pos"]) < 42.0:
				triggered = true; break
		if triggered:
			_burst(t["pos"], Color(0.8, 0.5, 0.3))
			_shake = maxf(_shake, 4.0)
			var r := 70.0
			var ex := tg.get_effect(Gadget.EXPLODE)
			if not ex.is_empty(): r = float(ex["radius"])
			for z in _zombies:
				if not z.get("dead", false) and (z["pos"] as Vector2).distance_to(t["pos"]) < r:
					_apply_payload(tg, z, t["pos"])
			continue  # consumed
		if float(t["life"]) > 0.0:
			live.append(t)
	_traps = live

func _apply_damage(z: Dictionary, dmg: float, _from: Vector2) -> void:
	if z.get("dead", false):
		return
	var shatter := float(z.get("freeze", 0.0)) > 0.0
	if shatter:
		dmg *= 1.8   # frozen enemies shatter
	z["hp"] = float(z["hp"]) - dmg
	z["flash"] = 0.12
	z["squash"] = 1.0   # pop on hit
	_dmg_num(z["pos"], str(int(dmg)), Color(0.6, 0.9, 1.0) if shatter else Color(1, 0.9, 0.5))
	if z["hp"] <= 0.0:
		_on_zombie_death(z)

func _on_zombie_death(z: Dictionary) -> void:
	# mark dead; the WAVE update drops it next pass (avoids mutating mid-iteration)
	z["dead"] = true
	_burst(z["pos"], Color(0.5, 0.8, 0.45), 14, 240.0)
	_ring(z["pos"], Color(0.6, 0.9, 0.5), 34.0, 3.0, 0.28)
	_shake = maxf(_shake, 4.0)
	_freeze(0.045)   # brief hit-stop so a kill lands
	if randf() < 0.45:
		var id: String = _db.keys().pick_random()
		_spawn_pickup(z["pos"], id)

# --- loot (Pickup nodes) -----------------------------------------------------

func _spawn_pickup(pos: Vector2, id: String) -> void:
	var pk := PickupNode.new()
	pk.position = pos
	pk.setup(id, _item_icon(id))
	_pickups_root.add_child(pk)

func _clear_pickups() -> void:
	if _pickups_root != null:
		for c in _pickups_root.get_children():
			c.queue_free()

func _update_loot(_delta: float) -> void:
	var auto := _equipped != null and _equipped.has(Gadget.COLLECT)
	var ar := 200.0
	if auto:
		var ce := _equipped.get_effect(Gadget.COLLECT)
		if float(ce["radius"]) > 0.0: ar = float(ce["radius"])
	for node in _pickups_root.get_children():
		var p := node as PickupNode
		if p == null:
			continue
		var d: float = p.position.distance_to(_player)
		if auto and d < ar:
			p.position = p.position.lerp(_player, 0.12)
			d = p.position.distance_to(_player)
		if d < 22.0:
			_grant(p.id, "Picked up %s." % _db[p.id].display_name)
			p.queue_free()

func _grant(id: String, msg: String) -> void:
	_inv[id] = int(_inv.get(id, 0)) + 1
	_log(msg)
	_burst(_player, Color(0.95, 0.85, 0.3))
	_refresh_inventory_ui()

# --- juice -------------------------------------------------------------------

func _update_juice(delta: float) -> void:
	var dn: Array[Dictionary] = []
	for n in _dmg_nums:
		n["life"] -= delta
		n["pos"].y -= 30.0 * delta
		if n["life"] > 0.0: dn.append(n)
	_dmg_nums = dn
	var pp: Array[Dictionary] = []
	for pt in _particles:
		pt["life"] -= delta
		pt["pos"] += pt["vel"] * delta
		pt["vel"] *= 0.92
		if pt["life"] > 0.0: pp.append(pt)
	_particles = pp
	var ar: Array[Dictionary] = []
	for a in _arcs:
		a["life"] = float(a["life"]) - delta
		if a["life"] > 0.0: ar.append(a)
	_arcs = ar
	var rr: Array[Dictionary] = []
	for r in _rings:
		r["life"] = float(r["life"]) - delta
		var t: float = 1.0 - clampf(float(r["life"]) / float(r["life0"]), 0.0, 1.0)
		r["r"] = lerpf(6.0, float(r["max_r"]), t)
		if r["life"] > 0.0: rr.append(r)
	_rings = rr

func _dmg_num(pos: Vector2, text: String, col: Color) -> void:
	_dmg_nums.append({"pos": pos + Vector2(0, -16), "text": text, "life": 0.7, "col": col})

func _burst(pos: Vector2, col: Color, count := 8, speed := 160.0) -> void:
	for i in range(count):
		var a := randf() * TAU
		_particles.append({"pos": pos, "vel": Vector2(cos(a), sin(a)) * randf_range(40, speed),
			"life": randf_range(0.3, 0.6), "col": col})

# an expanding shockwave ring — cheap, high-impact feedback for hits/explosions/deaths
func _ring(pos: Vector2, col: Color, max_r: float, w := 3.0, life := 0.32) -> void:
	_rings.append({"pos": pos, "r": 6.0, "max_r": max_r, "life": life, "life0": life, "col": col, "w": w})

func _freeze(t: float) -> void:
	_hitstop = maxf(_hitstop, t)

func _muzzle_kick(col: Color) -> void:
	_muzzle = {"pos": _player + _aim * 22.0, "life": 0.06, "col": col}

func _nearest_zombie(from: Vector2) -> Vector2:
	var best := Vector2.INF
	var bd := INF
	for z in _zombies:
		if z.get("dead", false):
			continue
		var d := from.distance_to(z["pos"])
		if d < bd: bd = d; best = z["pos"]
	return best

func _out_of_play(p: Vector2) -> bool:
	return p.x < 0.0 or p.x > PLAY_W or p.y < 0.0 or p.y > PLAY_H

# =============================================================================
# DRAW
# =============================================================================

func _draw() -> void:
	var shake := Vector2(randf_range(-1, 1), randf_range(-1, 1)) * _shake
	_shake_off = shake
	draw_set_transform(shake, 0.0, Vector2.ONE)

	draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0.09, 0.10, 0.12))
	if _tex_ground != null:
		draw_texture_rect(_tex_ground, Rect2(0, 0, PLAY_W, PLAY_H), true, Color(0.72, 0.74, 0.7))
	else:
		draw_rect(Rect2(MARGIN, MARGIN, PLAY_W - MARGIN * 2, PLAY_H - MARGIN * 2), Color(0.14, 0.15, 0.18))

	# scavenge sites
	for s in _sites:
		var looted: bool = s["looted"]
		draw_rect(s["rect"], Color(0.22, 0.24, 0.30) if not looted else Color(0.16, 0.16, 0.18))
		var col := Color(0.6, 0.65, 0.7) if not looted else Color(0.35, 0.35, 0.4)
		_text(s["rect"].position + Vector2(6, 18), s["label"], col, 13)

	# (loot now renders as Pickup nodes in _pickups_root)

	# zombies — sprite, rotated to face the player, tinted by status
	for z in _zombies:
		var tint := Color(1, 1, 1)
		if z["snare"] > 0.0: tint = Color(0.8, 0.6, 1.0)
		elif z["slow"] > 0.0: tint = Color(0.7, 0.8, 1.0)
		if float(z.get("freeze", 0.0)) > 0.0: tint = Color(0.6, 0.85, 1.0)
		if z["flash"] > 0.0: tint = Color(1.7, 1.7, 1.7)
		var sc: float = float(z.get("scale", 1.0)) * (1.0 + 0.3 * float(z.get("squash", 0.0)))
		var zrot: float = (_player - (z["pos"] as Vector2)).angle()
		if _tex_zombie != null:
			_blit(_tex_zombie, z["pos"], zrot, 42.0 * sc, tint)
		else:
			draw_circle(z["pos"], 13.0 * sc, Color(0.4, 0.65, 0.38))
		var f: float = clampf(z["hp"] / z["max_hp"], 0.0, 1.0)
		if f < 1.0:
			draw_rect(Rect2(z["pos"] + Vector2(-16, -26), Vector2(32.0 * f, 4)), Color(0.85, 0.3, 0.3))

	# traps
	for t in _traps:
		draw_rect(Rect2((t["pos"] as Vector2) - Vector2(8, 8), Vector2(16, 16)), Color(0.8, 0.5, 0.2))
		draw_arc(t["pos"], 42.0, 0.0, TAU, 24, Color(0.8, 0.5, 0.2, 0.25), 1.0)

	# turrets
	for tu in _turrets:
		draw_rect(Rect2((tu["pos"] as Vector2) - Vector2(9, 9), Vector2(18, 18)), tu["color"])
		draw_circle(tu["pos"], 4.0, Color(0.1, 0.1, 0.12))

	# decoys
	for dc in _decoys:
		var dl := clampf(float(dc["life"]) / 12.0, 0.25, 1.0)
		draw_circle(dc["pos"], 10.0, Color(0.95, 0.5, 0.2, dl))
		draw_arc(dc["pos"], float(dc["range"]), 0.0, TAU, 32, Color(0.95, 0.5, 0.2, 0.10), 1.0)

	# projectiles (with fading motion trails)
	for p in _projectiles:
		var pr: float = 6.0 if not p["homing"] else 8.0
		var tr: Array = p.get("trail", [])
		for i in range(tr.size()):
			var ta := (float(i) + 1.0) / float(tr.size() + 1)
			var tc: Color = p["color"]; tc.a = ta * 0.45
			draw_circle(tr[i], pr * ta * 0.85, tc)
		draw_circle(p["pos"], pr, p["color"])

	# melee swing
	if not _melee_anim.is_empty():
		var ma: Vector2 = _melee_anim["aim"]
		var mc := Color(0.95, 0.95, 0.7, clampf(float(_melee_anim["life"]) * 6.0, 0.0, 1.0))
		draw_arc(_melee_anim["pos"], 60.0, ma.angle() - 0.6, ma.angle() + 0.6, 16, mc, 4.0)

	# beam
	if not _beam_anim.is_empty():
		var bc: Color = _beam_anim["col"]
		bc.a = clampf(float(_beam_anim["life"]) * 10.0, 0.3, 1.0)
		draw_line(_beam_anim["a"], _beam_anim["b"], bc, 4.0)
		draw_line(_beam_anim["a"], _beam_anim["b"], Color(1, 1, 1, bc.a * 0.5), 1.5)

	# chain-lightning arcs
	for a in _arcs:
		var aa := clampf(float(a["life"]) * 8.0, 0.2, 1.0)
		draw_line(a["a"], a["b"], Color(0.7, 0.85, 1.0, aa), 2.5)

	# shockwave rings
	for r in _rings:
		var ra := clampf(float(r["life"]) / float(r["life0"]), 0.0, 1.0)
		var rc: Color = r["col"]; rc.a = ra * 0.8
		draw_arc(r["pos"], float(r["r"]), 0.0, TAU, 32, rc, float(r["w"]))

	# muzzle flash
	if not _muzzle.is_empty():
		var mf := clampf(float(_muzzle["life"]) * 16.0, 0.0, 1.0)
		draw_circle(_muzzle["pos"], 8.0 * mf, Color(1.0, 0.95, 0.65, mf))

	# particles
	for pt in _particles:
		var c: Color = pt["col"]
		c.a = clampf(pt["life"] * 2.0, 0.0, 1.0)
		draw_rect(Rect2(pt["pos"] - Vector2(2, 2), Vector2(4, 4)), c)

	# player — survivor sprite, rotated to aim
	var ptint := Color(1, 1, 1)
	if _invuln > 0.0 and int(_invuln * 20.0) % 2 == 0: ptint = Color(1.6, 0.6, 0.6)
	if _tex_player != null:
		_blit(_tex_player, _player, _aim.angle(), 46.0, ptint)
	else:
		draw_circle(_player, PLAYER_RADIUS, Color(0.88, 0.88, 0.92))
	if _shield > 0.0:
		draw_arc(_player, PLAYER_RADIUS + 8.0, 0.0, TAU, 28, Color(0.4, 0.7, 1.0, 0.85), 2.5)

	# damage numbers (pop big, then settle + fade)
	for n in _dmg_nums:
		var nc: Color = n["col"]
		nc.a = clampf(n["life"] * 1.6, 0.0, 1.0)
		var nsz := int(13 + 9 * clampf(float(n["life"]) / 0.7, 0.0, 1.0))
		_text(n["pos"], n["text"], nc, nsz)

	# hurt vignette
	if _hurt_flash > 0.0:
		var hc := Color(0.8, 0.1, 0.1, _hurt_flash * 0.6)
		draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), hc)

	# low-HP danger pulse
	if _hp > 0.0 and _hp < PLAYER_MAX_HP * 0.3:
		var pulse := 0.12 + 0.10 * sin(Time.get_ticks_msec() * 0.008)
		draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0.7, 0.05, 0.05, pulse))

	_draw_hud()

	if _paused:
		draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0, 0, 0, 0.45))
		_text(Vector2(PLAY_W * 0.5 - 90, PLAY_H * 0.5), "PAUSED  —  SPACE to resume", Color(1, 1, 1), 22)

func _draw_hud() -> void:
	# hp bar
	draw_rect(Rect2(MARGIN + 6, PLAY_H - 30, 220, 16), Color(0.2, 0.2, 0.22))
	var hpf: float = clampf(_hp / PLAYER_MAX_HP, 0.0, 1.0)
	draw_rect(Rect2(MARGIN + 6, PLAY_H - 30, 220 * hpf, 16), Color(0.75, 0.3, 0.3))
	_text(Vector2(MARGIN + 10, PLAY_H - 17), "HP %d" % int(maxf(_hp, 0.0)), Color(1, 1, 1), 13)
	if _shield > 0.0:
		_text(Vector2(MARGIN + 235, PLAY_H - 27), "SHIELD %d" % int(_shield), Color(0.5, 0.8, 1.0), 13)
	if _speed_mult > 1.0:
		_text(Vector2(MARGIN + 235, PLAY_H - 11), "SPEED x%.1f" % _speed_mult, Color(0.6, 0.95, 0.6), 12)

	var status := ""
	match _phase:
		Phase.BUILD:
			status = "BUILD  ·  next wave in %ds  (SPACE = pause)" % int(ceil(_phase_timer))
			if DEBUG: status += "   ·   G = all items"
		Phase.WAVE:  status = "WAVE %d  ·  %d left" % [_wave, _zombies.size() + _to_spawn]
		Phase.GAME_OVER: status = "DEAD on wave %d  ·  press R" % _wave
	_text(Vector2(MARGIN + 6, MARGIN + 20), status, Color(0.85, 0.87, 0.9), 16)
	var eq := "(nothing)"
	if _equipped != null:
		eq = "%s  [%d/%d]" % [_equipped.display_name, _equipped_idx + 1, _arsenal.size()]
		if _equipped.uses_ammo:
			var cnt := _equipped.ammo_count()
			var ac := Color(0.6, 0.65, 0.7) if cnt > 0 else Color(0.85, 0.35, 0.35)
			var s := "Ammo: %d / %d" % [cnt, _equipped.ammo_max]
			var nm := _equipped.next_name()
			if nm != "" and nm != "Scrap": s += "   next: %s" % nm
			_text(Vector2(MARGIN + 6, MARGIN + 60), s, ac, 14)
	_text(Vector2(MARGIN + 6, MARGIN + 42), "Equipped: %s" % eq, Color(0.6, 0.65, 0.7), 14)

func _text(pos: Vector2, s: String, col: Color, size: int) -> void:
	draw_string(_font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

# =============================================================================
# UI (right panel: inventory -> pot -> combine -> equipped -> log)
# =============================================================================

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var bg := ColorRect.new()
	bg.color = Color(0.12, 0.13, 0.16)
	bg.position = Vector2(PLAY_W, 0)
	bg.size = Vector2(PANEL_W, PLAY_H)
	layer.add_child(bg)

	var root := VBoxContainer.new()
	root.position = Vector2(PLAY_W + 12, 10)
	root.size = Vector2(PANEL_W - 24, PLAY_H - 20)
	root.add_theme_constant_override("separation", 6)
	layer.add_child(root)

	_title(root, "THIS IS NOT A WEAPON")
	_caption(root, "scavenge / build / survive")

	_caption(root, "INVENTORY  (click to add to pot)")
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(0, 240)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	_grid = GridContainer.new()
	_grid.columns = 2
	_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_grid)

	_caption(root, "BENCH  (slots by order: delivery / damage / utility / modifier)")
	_pot_label = Label.new()
	_pot_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pot_label.text = "(empty)"
	root.add_child(_pot_label)
	var airow := HBoxContainer.new()
	root.add_child(airow)
	var aib := Button.new(); aib.text = "  AI BUILD  "; aib.tooltip_text = "build with the AI brain (needs combine/serve.py running)"; aib.pressed.connect(_on_ai_build); airow.add_child(aib)
	var cl := Button.new(); cl.text = " Clear "; cl.pressed.connect(_on_clear); airow.add_child(cl)
	var row := HBoxContainer.new()
	root.add_child(row)
	var cb := Button.new(); cb.text = " old BUILD "; cb.tooltip_text = "deterministic tag-vote build (legacy, for comparison)"; cb.pressed.connect(_on_combine); row.add_child(cb)
	var mb := Button.new(); mb.text = " MOD "; mb.tooltip_text = "modify the EQUIPPED weapon with the bench junk"; mb.pressed.connect(_on_modify); row.add_child(mb)
	var lb := Button.new(); lb.text = " LOAD "; lb.tooltip_text = "load the bench junk into the equipped weapon as AMMO"; lb.pressed.connect(_on_load); row.add_child(lb)

	_http = HTTPRequest.new()
	add_child(_http)
	_http.request_completed.connect(_on_ai_response)

	_caption(root, "ARSENAL  (1-9 / wheel to switch)")
	var ascroll := ScrollContainer.new()
	ascroll.custom_minimum_size = Vector2(0, 130)
	root.add_child(ascroll)
	_arsenal_box = VBoxContainer.new()
	_arsenal_box.add_theme_constant_override("separation", 2)
	_arsenal_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ascroll.add_child(_arsenal_box)

	_caption(root, "EQUIPPED")
	_equipped_label = RichTextLabel.new()
	_equipped_label.bbcode_enabled = true
	_equipped_label.fit_content = true
	_equipped_label.custom_minimum_size = Vector2(0, 96)
	root.add_child(_equipped_label)

	_caption(root, "LOG")
	_log_label = RichTextLabel.new()
	_log_label.bbcode_enabled = true
	_log_label.scroll_following = true
	_log_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_log_label.custom_minimum_size = Vector2(0, 110)
	root.add_child(_log_label)

func _title(parent: Node, s: String) -> void:
	var l := Label.new(); l.text = s
	l.add_theme_font_size_override("font_size", 20)
	parent.add_child(l)

func _caption(parent: Node, s: String) -> void:
	var l := Label.new(); l.text = s
	l.add_theme_color_override("font_color", Color(0.55, 0.6, 0.68))
	l.add_theme_font_size_override("font_size", 13)
	parent.add_child(l)

func _refresh_inventory_ui() -> void:
	if _grid == null:
		return
	for c in _grid.get_children():
		c.queue_free()
	var ids := _inv.keys()
	ids.sort()
	for id in ids:
		var count: int = _inv[id]
		if count <= 0:
			continue
		var it: Item = _db[id]
		var b := Button.new()
		b.text = "%s x%d" % [it.display_name, count]
		b.tooltip_text = "tags: %s" % ", ".join(it.tags)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.add_theme_font_size_override("font_size", 11)
		var tex := _item_icon(id)
		if tex != null:
			b.icon = tex
			b.expand_icon = true
			b.add_theme_color_override("icon_normal_color", it.color)   # tint the white glyph
			b.add_theme_color_override("icon_hover_color", Color(1, 1, 1))
			b.custom_minimum_size = Vector2(0, 40)
		b.pressed.connect(_on_item_pressed.bind(id))
		_grid.add_child(b)
	if _grid.get_child_count() == 0:
		var l := Label.new(); l.text = "(empty — go scavenge)"
		l.add_theme_color_override("font_color", Color(0.5, 0.5, 0.55))
		_grid.add_child(l)

func _on_item_pressed(id: String) -> void:
	if _pot.size() >= 4:
		_log("All four slots are full."); return
	var used := _pot.count(id)
	if int(_inv.get(id, 0)) - used <= 0:
		_log("You don't have another %s." % _db[id].display_name); return
	_pot.append(id)
	_log("%s -> %s slot" % [_db[id].display_name, SLOT_NAMES[_pot.size() - 1]])
	_refresh_pot()

func _on_clear() -> void:
	_pot.clear(); _refresh_pot()

# --- AI build (calls the Python combine brain over HTTP) ---------------------

func _on_ai_build() -> void:
	if _ai_busy:
		_log("The AI is still thinking..."); return
	if _pot.is_empty():
		_log("Fill the bench slots first (click junk; order = delivery/damage/utility/modifier)."); return
	var req := {"awakening": _awakening}
	for i in range(_pot.size()):
		req[String(SLOT_NAMES[i]).to_lower()] = _pot[i]
	var err := _http.request(AI_URL, PackedStringArray(["Content-Type: application/json"]),
		HTTPClient.METHOD_POST, JSON.stringify(req))
	if err != OK:
		_log("Can't reach the AI bridge — is combine/serve.py running?  (err %d)" % err); return
	_ai_pending = _pot.duplicate()
	_ai_busy = true
	_log("[i]Reality is recalculating...[/i]")

func _on_ai_response(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_ai_busy = false
	var text := body.get_string_from_utf8()
	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		_log("AI bridge failed (net %d / http %d). Is the server up?" % [result, response_code])
		if text != "": _log("  %s" % text)
		return
	var data: Variant = JSON.parse_string(text)
	if typeof(data) != TYPE_DICTIONARY:
		_log("AI returned something unparseable."); return
	if data.has("error"):
		_log("AI error: %s" % str(data["error"])); return
	var g := _gadget_from_dict(data)
	# consume the junk we actually sent (pot may have changed while we waited)
	for id in _ai_pending:
		if _inv.has(id):
			_inv[id] = int(_inv[id]) - 1
			if _inv[id] <= 0: _inv.erase(id)
	_ai_pending.clear()
	_glitch_pulse(0.5)
	_arsenal.append(g)
	_equip(_arsenal.size() - 1)
	_log("[b]%s[/b]  [%s]" % [g.display_name, g.category_name()])
	_log("  \"%s\"" % g.description)
	if data.has("logic"): _log("  [color=#889]why: %s[/color]" % str(data["logic"]))
	_pot.clear()
	_refresh_pot(); _refresh_inventory_ui()

func _gadget_from_dict(d: Dictionary) -> Gadget:
	var g := Gadget.new()
	g.display_name = str(d.get("name", "Contraption"))
	g.description = str(d.get("description", ""))
	g.delivery = _delivery_from_name(str(d.get("delivery", "PROJECTILE")))
	g.homing = bool(d.get("homing", false))
	g.harmless = bool(d.get("harmless", false))
	g.projectile_speed = float(d.get("projectile_speed", 700.0))
	g.color = Color.from_string(str(d.get("color", "#b0b0b0")), Color(0.7, 0.7, 0.7))
	for e in d.get("effects", []):
		g.add(str(e.get("kind", "damage")), float(e.get("amount", 0.0)),
			float(e.get("duration", 0.0)), float(e.get("radius", 0.0)), int(e.get("count", 0)))
	_finalize_ai_gadget(g)
	return g

func _delivery_from_name(n: String) -> Gadget.Delivery:
	match n:
		"MELEE": return Gadget.Delivery.MELEE
		"LOBBED": return Gadget.Delivery.LOBBED
		"AURA": return Gadget.Delivery.AURA
		"PLACED": return Gadget.Delivery.PLACED
		"CONE": return Gadget.Delivery.CONE
		"BEAM": return Gadget.Delivery.BEAM
		"RETURN": return Gadget.Delivery.RETURN
		"SELF": return Gadget.Delivery.SELF
		"TURRET": return Gadget.Delivery.TURRET
		"DECOY": return Gadget.Delivery.DECOY
		_: return Gadget.Delivery.PROJECTILE

# mirrors Resolver._finalize: fire mode + ammo capacity from delivery/power
func _finalize_ai_gadget(g: Gadget) -> void:
	g.semi = true
	if g.delivery == Gadget.Delivery.MELEE or g.delivery == Gadget.Delivery.BEAM:
		g.semi = false
	g.uses_ammo = g.delivery in [Gadget.Delivery.PROJECTILE, Gadget.Delivery.LOBBED,
		Gadget.Delivery.PLACED, Gadget.Delivery.CONE, Gadget.Delivery.SELF,
		Gadget.Delivery.TURRET, Gadget.Delivery.DECOY]
	if g.uses_ammo:
		var pwr: float = maxf(g.amount_of(Gadget.DAMAGE), g.amount_of(Gadget.EXPLODE))
		pwr = maxf(pwr, 4.0)
		match g.delivery:
			Gadget.Delivery.SELF, Gadget.Delivery.TURRET, Gadget.Delivery.DECOY:
				g.ammo_max = 3
			Gadget.Delivery.LOBBED, Gadget.Delivery.PLACED:
				g.ammo_max = clampi(int(round(60.0 / pwr)), 3, 8)
			_:
				g.ammo_max = clampi(int(round(90.0 / pwr)), 6, 30)
				if not g.semi: g.ammo_max = int(g.ammo_max * 1.5)
		g.fill_plain()

func _on_combine() -> void:
	if _pot.is_empty():
		_log("Nothing on the bench."); return
	var items: Array[Item] = []
	var names: Array[String] = []
	for id in _pot:
		items.append(_db[id]); names.append(_db[id].display_name)
	var result := Resolver.combine(items)
	_glitch_pulse(0.4)
	_consume_pot()
	_arsenal.append(result)
	_equip(_arsenal.size() - 1)
	_log("[b]%s[/b] -> [b]%s[/b]" % [" + ".join(names), result.display_name])
	_log("  \"%s\"" % result.description)
	_pot.clear()
	_refresh_pot(); _refresh_inventory_ui()

func _on_modify() -> void:
	if _equipped == null:
		_log("Nothing equipped to modify."); return
	if _pot.is_empty():
		_log("Put some junk on the bench to modify with."); return
	var names: Array[String] = []
	var items: Array[Item] = []
	for id in _pot:
		items.append(_db[id]); names.append(_db[id].display_name)
	var old_name := _equipped.display_name
	var result := Resolver.combine(items, _equipped)
	if result.uses_ammo and _equipped.uses_ammo:
		result.mag = _equipped.mag.duplicate(true)  # carry the loaded magazine over
		while result.ammo_count() > result.ammo_max and not result.mag.is_empty():
			result.mag[0]["count"] = int(result.mag[0]["count"]) - 1
			if int(result.mag[0]["count"]) <= 0: result.mag.pop_front()
	_consume_pot()
	_arsenal[_equipped_idx] = result   # replace in place
	_equipped = result
	_log("Modified [b]%s[/b] with %s -> [b]%s[/b]" % [old_name, " + ".join(names), result.display_name])
	_pot.clear()
	_refresh_pot(); _refresh_inventory_ui(); _refresh_equipped(); _refresh_arsenal_ui()

func _consume_pot() -> void:
	for id in _pot:
		_inv[id] = int(_inv[id]) - 1
		if _inv[id] <= 0: _inv.erase(id)

func _on_load() -> void:
	if _equipped == null or not _equipped.uses_ammo:
		_log("That weapon doesn't take ammo."); return
	if _pot.is_empty():
		_log("Put junk on the bench to load as ammo."); return
	var items: Array[Item] = []
	for id in _pot:
		items.append(_db[id])
	var rounds := 0
	for it in items:
		rounds += _ammo_value(it)
	var prof := Resolver.ammo_profile(items)
	var loaded := _equipped.load_rounds(prof["name"], prof, prof["color"], rounds)
	_consume_pot()
	if loaded <= 0:
		_log("%s is already full." % _equipped.display_name)
	else:
		_log("Loaded [b]%s[/b]: +%d  (now %d/%d)" % [prof["name"], loaded, _equipped.ammo_count(), _equipped.ammo_max])
	_pot.clear()
	_refresh_pot(); _refresh_inventory_ui()

func _ammo_value(it: Item) -> int:
	var v := 4
	if it.has_tag("explosive") or it.has_tag("lethal"):
		v += 6
	elif it.has_tag("metal") or it.has_tag("canned") or it.has_tag("pressure") or it.has_tag("dense"):
		v += 4
	return v

func _refresh_pot() -> void:
	if _pot.is_empty():
		_pot_label.text = "(empty — click junk to fill slots)"; return
	var lines: Array[String] = []
	for i in range(_pot.size()):
		lines.append("%s: %s" % [SLOT_NAMES[i], _db[_pot[i]].display_name])
	_pot_label.text = "\n".join(lines)

func _refresh_arsenal_ui() -> void:
	if _arsenal_box == null:
		return
	for c in _arsenal_box.get_children():
		c.queue_free()
	for i in range(_arsenal.size()):
		var g: Gadget = _arsenal[i]
		var b := Button.new()
		b.text = "%s%d. %s [%s]" % ["> " if i == _equipped_idx else "   ", i + 1, g.display_name, g.category_name()]
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.pressed.connect(_equip.bind(i))
		_arsenal_box.add_child(b)

func _refresh_equipped() -> void:
	if _equipped == null:
		_equipped_label.text = "(nothing)"; return
	_equipped_label.text = "[b]%s[/b]  [%s]\n[color=#9aa]%s[/color]\n[color=#778]%s[/color]" % [
		_equipped.display_name, _equipped.category_name(), _equipped.description, _equipped.summary()]

func _log(s: String) -> void:
	_log_lines.append(s)
	if _log_lines.size() > 40: _log_lines.pop_front()
	if _log_label != null:
		_log_label.text = "\n".join(_log_lines)
