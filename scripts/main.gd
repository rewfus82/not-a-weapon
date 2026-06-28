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
var _loot: Array[Dictionary] = []     # ground pickups: {pos, id}
var _sites: Array[Dictionary] = []    # scavenge points: {rect, label, looted}
var _projectiles: Array[Dictionary] = []
var _traps: Array[Dictionary] = []    # placed traps: {pos, gadget, life}
var _melee_anim: Dictionary = {}      # transient swing visual
var _beam_anim: Dictionary = {}       # transient beam visual: {a, b, life, col}
var _arcs: Array[Dictionary] = []     # chain-lightning arcs: {a, b, life}
var _dmg_nums: Array[Dictionary] = [] # {pos, text, life, col}
var _particles: Array[Dictionary] = []
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

func _ready() -> void:
	_font = ThemeDB.fallback_font
	_db = ItemDB.build()
	_spawn_sites()
	_build_ui()
	_restart()

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
	_zombies.clear(); _loot.clear(); _projectiles.clear()
	_dmg_nums.clear(); _particles.clear(); _pot.clear()
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
		if float(z.get("burn_t", 0.0)) > 0.0:
			z["burn_t"] = float(z["burn_t"]) - delta
			z["hp"] = float(z["hp"]) - float(z.get("burn", 0.0)) * delta
			if z["hp"] <= 0.0:
				_on_zombie_death(z)
				continue
		var spd: float = z["speed"]
		if z["freeze"] > 0.0 or z["snare"] > 0.0: spd = 0.0
		elif z["slow"] > 0.0: spd *= 0.35
		var to_player: Vector2 = (_player as Vector2) - z["pos"]
		z["pos"] += to_player.normalized() * spd * delta + z["knock"] * delta
		z["knock"] = z["knock"].lerp(Vector2.ZERO, 0.12)
		# contact damage
		if z["pos"].distance_to(_player) < PLAYER_RADIUS + 13.0 and _invuln <= 0.0:
			var dmg: float = z["dmg"]
			if _shield > 0.0:
				var ab := minf(_shield, dmg); _shield -= ab; dmg -= ab
			if dmg > 0.0: _hp -= dmg
			_invuln = INVULN_TIME
			_hurt_flash = 0.4
			_shake = 6.0
			if _hp <= 0.0:
				_game_over()
				return
		alive.append(z)
	_zombies = alive
	_update_aura(delta)
	_update_traps(delta)
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
		Gadget.Delivery.AURA:
			_fire_timer = 0.2  # passive; aura ticks each frame

func _fire_ranged(g: Gadget, lobbed: bool, ap: Dictionary) -> void:
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
		"pierce": pierce, "hits": [], "lobbed": lobbed, "sub": sub,
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
	_shake = maxf(_shake, 6.0)
	_burst(at, Color(0.95, 0.6, 0.2))
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
	_shake = maxf(_shake, 6.0)
	_burst(at, Color(0.95, 0.6, 0.2))
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
	if float(z.get("freeze", 0.0)) > 0.0:
		dmg *= 1.8   # frozen enemies shatter
	z["hp"] = float(z["hp"]) - dmg
	z["flash"] = 0.12
	_dmg_num(z["pos"], str(int(dmg)), Color(1, 0.9, 0.5))
	if z["hp"] <= 0.0:
		_on_zombie_death(z)

func _on_zombie_death(z: Dictionary) -> void:
	# mark dead; the WAVE update drops it next pass (avoids mutating mid-iteration)
	z["dead"] = true
	_burst(z["pos"], Color(0.4, 0.7, 0.4))
	if randf() < 0.45:
		var id: String = _db.keys().pick_random()
		_loot.append({"pos": z["pos"], "id": id})

# --- loot --------------------------------------------------------------------

func _update_loot(_delta: float) -> void:
	var auto := _equipped != null and _equipped.has(Gadget.COLLECT)
	var ar := 200.0
	if auto:
		var ce := _equipped.get_effect(Gadget.COLLECT)
		if float(ce["radius"]) > 0.0: ar = float(ce["radius"])
	var keep: Array[Dictionary] = []
	for l in _loot:
		var d: float = l["pos"].distance_to(_player)
		if auto and d < ar:
			l["pos"] = (l["pos"] as Vector2).lerp(_player, 0.12)
			d = l["pos"].distance_to(_player)
		if d < 22.0:
			_grant(l["id"], "Picked up %s." % _db[l["id"]].display_name)
			continue
		keep.append(l)
	_loot = keep

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

func _dmg_num(pos: Vector2, text: String, col: Color) -> void:
	_dmg_nums.append({"pos": pos + Vector2(0, -16), "text": text, "life": 0.7, "col": col})

func _burst(pos: Vector2, col: Color) -> void:
	for i in range(8):
		var a := randf() * TAU
		_particles.append({"pos": pos, "vel": Vector2(cos(a), sin(a)) * randf_range(40, 160),
			"life": randf_range(0.3, 0.6), "col": col})

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
	draw_set_transform(shake, 0.0, Vector2.ONE)

	draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0.09, 0.10, 0.12))
	draw_rect(Rect2(MARGIN, MARGIN, PLAY_W - MARGIN * 2, PLAY_H - MARGIN * 2), Color(0.14, 0.15, 0.18))

	# scavenge sites
	for s in _sites:
		var looted: bool = s["looted"]
		draw_rect(s["rect"], Color(0.22, 0.24, 0.30) if not looted else Color(0.16, 0.16, 0.18))
		var col := Color(0.6, 0.65, 0.7) if not looted else Color(0.35, 0.35, 0.4)
		_text(s["rect"].position + Vector2(6, 18), s["label"], col, 13)

	# loot
	for l in _loot:
		draw_rect(Rect2(l["pos"] - Vector2(5, 5), Vector2(10, 10)), Color(0.95, 0.82, 0.25))

	# zombies
	for z in _zombies:
		var zc := Color(0.40, 0.65, 0.38)
		if z["snare"] > 0.0: zc = Color(0.6, 0.4, 0.75)
		elif z["slow"] > 0.0: zc = Color(0.4, 0.55, 0.8)
		if float(z.get("freeze", 0.0)) > 0.0: zc = Color(0.6, 0.85, 1.0)
		if z["flash"] > 0.0: zc = Color(1, 1, 1)
		draw_circle(z["pos"], 13.0, zc)
		var f: float = clampf(z["hp"] / z["max_hp"], 0.0, 1.0)
		draw_rect(Rect2(z["pos"] + Vector2(-13, -20), Vector2(26.0 * f, 4)), Color(0.8, 0.3, 0.3))

	# traps
	for t in _traps:
		draw_rect(Rect2((t["pos"] as Vector2) - Vector2(8, 8), Vector2(16, 16)), Color(0.8, 0.5, 0.2))
		draw_arc(t["pos"], 42.0, 0.0, TAU, 24, Color(0.8, 0.5, 0.2, 0.25), 1.0)

	# projectiles
	for p in _projectiles:
		draw_circle(p["pos"], 6.0 if not p["homing"] else 8.0, p["color"])

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

	# particles
	for pt in _particles:
		var c: Color = pt["col"]
		c.a = clampf(pt["life"] * 2.0, 0.0, 1.0)
		draw_rect(Rect2(pt["pos"] - Vector2(2, 2), Vector2(4, 4)), c)

	# player
	var pc := Color(0.88, 0.88, 0.92)
	if _invuln > 0.0 and int(_invuln * 20.0) % 2 == 0: pc = Color(1, 0.5, 0.5)
	draw_circle(_player, PLAYER_RADIUS, pc)
	if _shield > 0.0:
		draw_arc(_player, PLAYER_RADIUS + 5.0, 0.0, TAU, 28, Color(0.4, 0.7, 1.0, 0.85), 2.5)
	draw_line(_player, _player + _aim * 28.0, Color(0.9, 0.9, 0.5), 3.0)

	# damage numbers
	for n in _dmg_nums:
		var nc: Color = n["col"]
		nc.a = clampf(n["life"] * 1.6, 0.0, 1.0)
		_text(n["pos"], n["text"], nc, 14)

	# hurt vignette
	if _hurt_flash > 0.0:
		var hc := Color(0.8, 0.1, 0.1, _hurt_flash * 0.6)
		draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), hc)

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

	_caption(root, "BENCH  (max 3, consumes junk)")
	_pot_label = Label.new()
	_pot_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pot_label.text = "(empty)"
	root.add_child(_pot_label)
	var row := HBoxContainer.new()
	root.add_child(row)
	var cb := Button.new(); cb.text = " BUILD "; cb.tooltip_text = "build a NEW weapon from the bench junk"; cb.pressed.connect(_on_combine); row.add_child(cb)
	var mb := Button.new(); mb.text = " MOD "; mb.tooltip_text = "modify the EQUIPPED weapon with the bench junk"; mb.pressed.connect(_on_modify); row.add_child(mb)
	var row2 := HBoxContainer.new()
	root.add_child(row2)
	var lb := Button.new(); lb.text = " LOAD "; lb.tooltip_text = "load the bench junk into the equipped weapon as AMMO"; lb.pressed.connect(_on_load); row2.add_child(lb)
	var cl := Button.new(); cl.text = " Clear "; cl.pressed.connect(_on_clear); row2.add_child(cl)

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
		b.pressed.connect(_on_item_pressed.bind(id))
		_grid.add_child(b)
	if _grid.get_child_count() == 0:
		var l := Label.new(); l.text = "(empty — go scavenge)"
		l.add_theme_color_override("font_color", Color(0.5, 0.5, 0.55))
		_grid.add_child(l)

func _on_item_pressed(id: String) -> void:
	if _pot.size() >= 3:
		_log("Bench is full (3)."); return
	var used := _pot.count(id)
	if int(_inv.get(id, 0)) - used <= 0:
		_log("You don't have another %s." % _db[id].display_name); return
	_pot.append(id)
	_refresh_pot()

func _on_clear() -> void:
	_pot.clear(); _refresh_pot()

func _on_combine() -> void:
	if _pot.is_empty():
		_log("Nothing on the bench."); return
	var items: Array[Item] = []
	var names: Array[String] = []
	for id in _pot:
		items.append(_db[id]); names.append(_db[id].display_name)
	var result := Resolver.combine(items)
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
		_pot_label.text = "(empty)"; return
	var names: Array[String] = []
	for id in _pot: names.append(_db[id].display_name)
	_pot_label.text = " + ".join(names)

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
