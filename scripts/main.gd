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

enum Phase { ALIVE, GAME_OVER }   # no more waves — a continuous day/night world

# zombie detection state (see _update_world). Awareness rises when you're detectable
# (near / lit / loud) and decays when you're not; the state is derived from it.
enum ZState { WANDER, ALERT, CHASE }
const ZOMBIE_LIGHT_RANGE := 360.0   # flashlight ON: this is how far you're spotted
const ZOMBIE_LOSE := 3.0            # ~seconds of lost contact before a chaser gives up
const NOISE_GUNSHOT := 430.0        # radius a loud shot alerts zombies

const PANEL_W := 400.0        # (legacy; used only for build-overlay caption widths)
const PLAY_W := 1600.0        # SCREEN/design size (HUD, workbench, screen overlays live here)
const PLAY_H := 900.0
# --- the world is a GRID of cells: a procgen town you explore. See _gen_town(). ---
const TILE := 16.0           # tile ≈ player footprint (PZ scale); world is finer + more tiles
const GW := 280              # grid width in cells  (× TILE ≈ same physical world as before)
const GH := 185              # grid height in cells
const WORLD_W := GW * TILE   # 4480
const WORLD_H := GH * TILE   # 2960
# cell types (stored in _grid as bytes)
const C_GRASS := 0
const C_ROAD := 1
const C_WALK := 2
const C_WALL := 3            # solid — blocks movement
const C_FLOOR := 4
const C_DOOR := 5
const C_CORN := 6
const C_DIRT := 7
const C_WEEDS := 8           # dead/overgrown grass — ground texture so it's not a flat sheet
const C_TREE := 9            # solid tree — blocks movement + shots, drawn as a canopy
const C_WINDOW := 10         # (legacy cell type — walls/windows are now EDGES; see below)
const C_FURN := 11           # furniture/fixture inside a building (solid cover)
const C_CONTAINER := 12      # searchable prop (dresser/cabinet/crate…): solid, E to search, 33% loot
const C_BENCH := 13          # workbench prop: solid; standing near one unlocks T4 BUILD / AI BUILD

# Walls live on tile EDGES, not in cells (PZ model — thin by construction). Two edge grids:
#   _ev[cy][cx] = edge on the WEST side of cell (cx,cy)   (cx in 0..GW, cy in 0..GH-1)
#   _eh[cy][cx] = edge on the NORTH side of cell (cx,cy)  (cx in 0..GW-1, cy in 0..GH)
# East edge of (cx,cy) = _ev[cy][cx+1]; south edge = _eh[cy+1][cx].
const E_NONE := 0
const E_WALL := 1            # blocks movement, sight, and shots
const E_WINDOW := 2          # blocks movement; lets sight + shots through (FOV step)
const E_DOOR := 3            # open gap you walk through
const WALL_PX := 3.0         # drawn wall thickness (thin, independent of tile size)

# building archetypes — drive footprint size, interior layout, and roof colour
const BT_HOUSE := 0
const BT_BARN := 1
const BT_STORE := 2
const BT_CHURCH := 3
const BT_SHED := 4
const ROOF_COL := [
	Color(0.26, 0.21, 0.20),   # house  — brown shingle
	Color(0.34, 0.13, 0.12),   # barn   — faded red
	Color(0.19, 0.20, 0.22),   # store  — grey flat
	Color(0.17, 0.16, 0.22),   # church — slate
	Color(0.24, 0.20, 0.14),   # shed   — rusty tin
]
const CAM_ZOOM := 1.1         # default (outdoors, on foot)
const ZOOM_INTERIOR := 2.2    # punch in for an intimate interior when you step inside
const ZOOM_OPTIC := 0.65      # pull out when glassing through a scope / binoculars
const MARGIN := 10.0
const PLAYER_SPEED := 230.0   # a small, vulnerable figure
const PLAYER_RADIUS := 9.0    # ≈ half a tile radius → player ~1 tile, dwarfed by buildings
const BOOMERANG_RANGE := 300.0   # how far out it flies before the apex
const BOOMERANG_SPEED := 600.0   # return speed toward the player
const BOOMERANG_CURVE := 260.0   # lateral accel — the narrow sideways bow of the arc
const FIRE_COOLDOWN := 0.16
const DAY_LENGTH := 90.0   # seconds for one full day->night->day cycle
const PLAYER_MAX_HP := 100.0
const INVULN_TIME := 0.6
var _debug := false   # NORMAL by default (scavenge for items). F1 toggles DEBUG (all items + G/T).

# --- AI combine bridge (the Python brain served over HTTP; see combine/serve.py) ---
const AI_URL := "http://127.0.0.1:8777/resolve"
const SLOT_NAMES := ["DELIVERY", "DAMAGE", "UTILITY", "MODIFIER"]  # bench position -> slot
var _http: HTTPRequest
var _ai_busy := false
var _ai_pending: Array[String] = []
var _awakening := 0.15  # 0..1 lucidity. Starts ASLEEP; rises as you wake up (debug: [ / ])
# The lucidity ladder (DESIGN.md §3) — each rung unlocks deeper crafting:
const LUCID_UNIVERSAL := 0.25   # T1: "all bullets fit all guns" — any ammo loads any gun
const LUCID_JUNK := 0.45        # T2: "reload with anything" — junk-as-ammo unlocks
const LUCID_ATTACH := 0.65      # T3: "parts change weapons" — bench ATTACH (bolt parts on)
const LUCID_BUILD := 0.85       # T4: "build anything from anything" — bench BUILD / AI BUILD

var _db: Dictionary
var _phase: int = Phase.ALIVE
var _paused := false

# --- player ------------------------------------------------------------------
var _player := Vector2(WORLD_W * 0.5, WORLD_H * 0.5)
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
var _equipped_idx := 0                # index into _arsenal, or -1 = a raw item is in hand
var _equipped: Gadget = null          # the gadget actually fired (arsenal weapon OR a wielded item's resolved gadget)
# --- equipment slots: HAND (weapon/item) + ARMOR (placeholder) ---------------
var _hand_item: Item = null           # the raw junk item in hand (null = a crafted gadget is equipped)
var _hand_hold := false               # true = held, not a weapon and not throwable → no attack
var _armor: Item = null               # ARMOR slot — no armor items yet, so always empty for now
var _item_gadgets: Dictionary = {}    # item_id -> resolved Gadget cache (stable ammo across re-equips)

# --- world -------------------------------------------------------------------
var _zombies: Array[Dictionary] = []
var _pickups_root: Node2D             # container node for Pickup entities (dropped loot)
var _sites: Array[Dictionary] = []    # scavenge points: {rect, label, looted}
var _cells: Array[PackedByteArray] = [] # the town cell grid [row][col] (cell types above)
var _ev: Array[PackedByteArray] = []    # vertical wall edges (west side of each cell), GW+1 wide
var _eh: Array[PackedByteArray] = []    # horizontal wall edges (north side of each cell), GH+1 tall
var _buildings: Array[Rect2] = []       # building footprints in world coords
var _containers: Array[Dictionary] = [] # searchable props: {pos, kind, searched}
var _benches: Array[Vector2] = []       # workbench prop positions (world)
var _at_bench := false                   # player is within reach of a workbench (gates T4 build)
var _roof_a: Array[float] = []          # per-building roof opacity (1=roofed/hidden, 0=you're inside)
var _btype: Array[int] = []             # per-building archetype (parallel to _buildings)
var _road_xs: Array = []                # vertical-road column indices (for door orientation)
var _road_ys: Array = []                # horizontal-road row indices
var _projectiles: Array[Dictionary] = []
var _dropped_boomerangs: Array[Dictionary] = []   # boomerangs on the floor: {pos, gadget, spin}
var _zones: Array[Dictionary] = []    # ground hazards (caltrops/puddles): {pos, radius, kind, dmg, slow, burn_amt, burn_dur, snare, life, life0, tick, color}
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
var _spawn_timer := 0.0
var _shake := 0.0
var _log_lines: Array[String] = []

# --- ui ----------------------------------------------------------------------
var _font: Font
var _grid: GridContainer
var _pot_label: Label
var _arsenal_box: VBoxContainer
var _equipped_label: RichTextLabel
var _hand_label: Label
var _armor_label: Label
var _btn_build: Button    # bench actions gated by lucidity (disabled until the tier unlocks)
var _btn_attach: Button
var _btn_ai: Button
var _log_label: RichTextLabel
var _icons: Dictionary = {}   # item_id -> Texture2D (game-icons svg), cached

# New items have no bespoke art yet — borrow a close existing game-icon so the
# inventory reads as a set instead of half text-only. (Real art is Phase 4.)
const ICON_ALIAS := {
	"hornet_nest": "beehive", "skillet": "frying_pan", "drain_cleaner": "oven_cleaner",
	"bleach": "oven_cleaner", "nails": "nail_gun", "pvc_pipe": "pringles",
	"sledgehammer": "crowbar", "road_flare": "fireworks", "air_horn": "boombox",
	"first_aid": "bandages", "painkillers": "caffeine_pills", "energy_drink": "caffeine_pills",
	"shop_vac": "vacuum", "barbed_wire": "wire_hanger", "motor_oil": "gasoline",
	"cooking_grease": "gasoline", "chain": "jumper_cables", "mason_jar": "glue",
	"gas_canister": "propane_tank", "rockets": "grenade",
}

func _item_icon(id: String) -> Texture2D:
	if _icons.has(id):
		return _icons[id]
	var aid := String(ICON_ALIAS.get(id, id))
	var path := "res://assets/icons/%s.svg" % aid
	var tex: Texture2D = load(path) if ResourceLoader.exists(path) else null
	_icons[id] = tex
	return tex

const TDS := "res://assets/kenney/topdown-shooter/PNG/"
# preload entity scripts by path (avoids relying on class_name global registration,
# which needs an editor rescan that external file edits don't trigger)
const PickupNode := preload("res://scripts/pickup.gd")
const HudNode := preload("res://scripts/hud.gd")
var _hud_node: Node2D
var _cam: Camera2D
var _inside_building := false    # set each frame from the roof-fade check; drives the interior zoom
var _optic_zoom := false         # scope/binoculars glassing (pull the camera out) — wired later
var _build_layer: CanvasLayer   # the pause-to-build overlay (hidden until TAB)
var _tex_player: Texture2D
var _tex_zombie: Texture2D
var _tex_ground: Texture2D
var _shake_off := Vector2.ZERO
var _glitch_mat: ShaderMaterial   # the full-screen simulation-glitch post-process
var _glitch := 0.0                # transient glitch pulse (decays); base from _awakening
var _flashlight: PointLight2D     # real 2D light — the flashlight cone (follows aim)
var _flashlight_on := true        # toggled with F — off = blind but harder to spot (stealth)
var _player_glow: PointLight2D    # soft glow right around the player
var _cm: CanvasModulate           # world ambient — lerps day<->night with _dark
var _fog_mat: ShaderMaterial      # fog density scales with _dark
var _dark := 0.0                  # 0 = daylight, 1 = pitch night (derived from the clock)
var _time_of_day := 0.35         # 0=midnight · 0.25=dawn · 0.5=noon · 0.75=dusk
var _day_count := 1              # which day you're on (survival counter)
var _last_day := 1               # detects day rollover to refill scavenge sites
var _light_pool: Array[PointLight2D] = []   # pooled transient flashes (muzzle/explosions/hits)
var _light_i := 0
var _flashes: Array[Dictionary] = []        # active fading flashes: {l, t, dur, e0}

func _ready() -> void:
	# maximize to fit the actual screen; stretch(keep) scales the 1600x900 design down
	get_window().mode = Window.MODE_MAXIMIZED
	RenderingServer.set_default_clear_color(Color(0.02, 0.02, 0.03))   # dark void, not gray
	_font = load("res://assets/fonts/ShareTechMono-Regular.ttf")
	if _font == null:
		_font = ThemeDB.fallback_font
	_db = ItemDB.build()
	_tex_player = _tex(TDS + "Survivor 1/survivor1_gun.png")
	_tex_zombie = _tex(TDS + "Zombie 1/zoimbie1_hold.png")
	_tex_ground = _tex(TDS + "Tiles/tile_01.png")
	_gen_town()
	_build_occluders()
	_build_ui()
	_pickups_root = Node2D.new()
	add_child(_pickups_root)
	_setup_atmosphere()
	var hud_layer := CanvasLayer.new()   # HUD on its own bright layer (immune to world darkness)
	hud_layer.layer = 2
	add_child(hud_layer)
	_hud_node = HudNode.new()
	_hud_node.main = self
	hud_layer.add_child(_hud_node)
	_cam = Camera2D.new()
	_cam.zoom = Vector2(CAM_ZOOM, CAM_ZOOM)
	_cam.position_smoothing_enabled = true
	_cam.position_smoothing_speed = 9.0
	_cam.limit_left = 0
	_cam.limit_top = 0
	_cam.limit_right = int(WORLD_W)
	_cam.limit_bottom = int(WORLD_H)
	add_child(_cam)
	_cam.make_current()
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

	# real 2D lighting: a world whose ambient rides day<->night with the wave (see _apply_darkness)
	_cm = CanvasModulate.new()
	add_child(_cm)
	_player_glow = PointLight2D.new()
	_player_glow.texture = _radial_tex(256)
	_player_glow.color = Color(1.0, 0.84, 0.6)   # warm
	_player_glow.energy = 0.7
	_player_glow.texture_scale = 0.9
	_player_glow.shadow_enabled = true            # walls block your light
	_player_glow.shadow_filter = Light2D.SHADOW_FILTER_PCF5
	add_child(_player_glow)
	_flashlight = PointLight2D.new()
	_flashlight.texture = _cone_tex(256)
	_flashlight.color = Color(1.0, 0.9, 0.72)     # warm flashlight vs cold dark
	_flashlight.energy = 1.6
	_flashlight.texture_scale = 3.2
	_flashlight.shadow_enabled = true             # the cone is cut by walls — no seeing through buildings
	_flashlight.shadow_filter = Light2D.SHADOW_FILTER_PCF5
	add_child(_flashlight)
	for i in range(16):
		var fx := PointLight2D.new()
		fx.texture = _radial_tex(128)
		fx.energy = 0.0
		add_child(fx)
		_light_pool.append(fx)

	# drifting fog (screen-space, above the world, below the HUD)
	var fog_layer := CanvasLayer.new()
	fog_layer.layer = 1
	add_child(fog_layer)
	var fog := ColorRect.new()
	fog.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	fog.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fog_mat = ShaderMaterial.new()
	_fog_mat.shader = load("res://shaders/fog.gdshader")
	fog.material = _fog_mat
	fog_layer.add_child(fog)
	_apply_darkness()   # start in daylight (_dark = 0) so BUILD isn't a permanent night

func _radial_tex(size: int) -> Texture2D:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.5, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.45), Color(1, 1, 1, 0)])
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	gt.width = size
	gt.height = size
	return gt

# a cone light pointing +x (apex at texture center); the node is rotated to aim
func _cone_tex(size: int) -> Texture2D:
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var c := float(size) * 0.5
	var maxd := float(size) * 0.5
	var half := 0.55
	for yy in size:
		for xx in size:
			var dx := float(xx) - c
			var dy := float(yy) - c
			var a := 0.0
			if dx > 0.0:
				var dist := sqrt(dx * dx + dy * dy)
				var ang: float = atan2(dy, dx)
				var angf := clampf(1.0 - absf(ang) / half, 0.0, 1.0)
				var distf := clampf(1.0 - dist / maxd, 0.0, 1.0)
				a = angf * angf * distf * distf
			img.set_pixel(xx, yy, Color(1, 1, 1, a))
	return ImageTexture.create_from_image(img)

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

# --- procgen town: a grid of grass/roads/buildings/cornfields --------------------
# Built once at startup; the real scalable world layer (a county is just a bigger grid).

func _cell(x: int, y: int) -> int:
	if x < 0 or y < 0 or x >= GW or y >= GH:
		return C_WALL   # off-map reads as solid
	return _cells[y][x]

func _set_cell(x: int, y: int, c: int) -> void:
	if x >= 0 and y >= 0 and x < GW and y < GH:
		_cells[y][x] = c

# --- wall EDGES (thin walls on tile boundaries) ---
func _ev_at(cx: int, cy: int) -> int:        # vertical edge on the west side of cell (cx,cy)
	if cy < 0 or cy >= GH or cx < 0 or cx > GW: return E_WALL   # off-map = solid border
	return _ev[cy][cx]

func _eh_at(cx: int, cy: int) -> int:        # horizontal edge on the north side of cell (cx,cy)
	if cx < 0 or cx >= GW or cy < 0 or cy > GH: return E_WALL
	return _eh[cy][cx]

func _set_ev(cx: int, cy: int, t: int) -> void:
	if cy >= 0 and cy < GH and cx >= 0 and cx <= GW: _ev[cy][cx] = t

func _set_eh(cx: int, cy: int, t: int) -> void:
	if cx >= 0 and cx < GW and cy >= 0 and cy <= GH: _eh[cy][cx] = t

func _alloc_edges() -> void:
	_ev = []
	for cy in range(GH):
		var r := PackedByteArray(); r.resize(GW + 1); r.fill(E_NONE); _ev.append(r)
	_eh = []
	for cy in range(GH + 1):
		var r := PackedByteArray(); r.resize(GW); r.fill(E_NONE); _eh.append(r)

func _cell_color(c: int) -> Color:
	match c:
		C_ROAD:  return Color(0.11, 0.11, 0.13)
		C_WALK:  return Color(0.26, 0.26, 0.28)
		C_WALL:  return Color(0.34, 0.28, 0.25)
		C_FLOOR: return Color(0.17, 0.16, 0.19)
		C_DOOR:  return Color(0.42, 0.31, 0.18)
		C_CORN:  return Color(0.30, 0.32, 0.14)
		C_DIRT:  return Color(0.23, 0.19, 0.15)
		C_WEEDS:  return Color(0.21, 0.23, 0.11)   # dead/overgrown grass patch
		C_WINDOW: return Color(0.32, 0.40, 0.44)   # glass set in a wall
		C_FURN:   return Color(0.30, 0.24, 0.18)   # furniture / fixtures
		C_CONTAINER: return Color(0.17, 0.16, 0.19)  # floor base; the box is drawn in its own pass
		C_BENCH:  return Color(0.17, 0.16, 0.19)     # floor base; the bench is drawn in its own pass
		_:       return Color(0.17, 0.21, 0.14)   # grass

func _road_v(rx: int) -> void:                       # ~5-cell carriageway + a walk on each side
	for y in range(8, GH - 8):
		for dx in range(-2, 3): _set_cell(rx + dx, y, C_ROAD)
		_set_cell(rx - 3, y, C_WALK); _set_cell(rx + 3, y, C_WALK)

func _road_h(ry: int) -> void:
	for x in range(8, GW - 8):
		for dy in range(-2, 3): _set_cell(x, ry + dy, C_ROAD)
		_set_cell(x, ry - 3, C_WALK); _set_cell(x, ry + 3, C_WALK)

func _place_building(x: int, y: int, w: int, h: int, t: int) -> void:
	if x < 5 or y < 5 or x + w >= GW - 5 or y + h >= GH - 5:
		return
	for yy in range(y - 1, y + h + 1):          # need a clear grass lot (no roads/buildings)
		for xx in range(x - 1, x + w + 1):
			var c := _cell(xx, yy)
			if c != C_GRASS and c != C_DIRT and c != C_WEEDS:
				return
	for yy in range(y, y + h):                       # whole footprint is interior floor now
		for xx in range(x, x + w):
			_set_cell(xx, yy, C_FLOOR)
	for xx in range(x, x + w):                        # perimeter walls live on the edges
		_set_eh(xx, y, E_WALL)                        # north
		_set_eh(xx, y + h, E_WALL)                    # south
	for yy in range(y, y + h):
		_set_ev(x, yy, E_WALL)                        # west
		_set_ev(x + w, yy, E_WALL)                    # east
	_place_door(x, y, w, h)                           # doorway edge facing the nearest road
	_add_windows(x, y, w, h)                          # window edges in the remaining walls
	_furnish(t, x, y, w, h)                           # partitions + fixtures by archetype
	_buildings.append(Rect2(x * TILE, y * TILE, w * TILE, h * TILE))
	_btype.append(t)

# is this cell part of a building interior (walkable/furnished)? used to draw thin walls
func _is_inside(cx: int, cy: int) -> bool:
	var c := _cell(cx, cy)
	return c == C_FLOOR or c == C_FURN or c == C_DOOR

# only drop furniture onto open floor (never over walls/doors/windows)
func _furn(xx: int, yy: int) -> void:
	if _cell(xx, yy) == C_FLOOR: _set_cell(xx, yy, C_FURN)

# a searchable container prop on open floor (solid, E to search, registered for looting)
func _container(xx: int, yy: int, kind: String) -> void:
	if _cell(xx, yy) != C_FLOOR: return
	_set_cell(xx, yy, C_CONTAINER)
	_containers.append({
		"pos": Vector2(xx * TILE + TILE * 0.5, yy * TILE + TILE * 0.5),
		"kind": kind, "searched": false})

# a workbench prop on open floor (solid; being near it unlocks the T4 build actions)
func _bench(xx: int, yy: int) -> void:
	if _cell(xx, yy) != C_FLOOR: return
	_set_cell(xx, yy, C_BENCH)
	_benches.append(Vector2(xx * TILE + TILE * 0.5, yy * TILE + TILE * 0.5))

func _add_windows(x: int, y: int, w: int, h: int) -> void:
	var step := 4                                     # a window roughly every 4 cells
	for xx in range(x + 2, x + w - 2):
		if (xx - x) % step == 0:
			if _eh_at(xx, y) == E_WALL and randf() < 0.7: _set_eh(xx, y, E_WINDOW)
			if _eh_at(xx, y + h) == E_WALL and randf() < 0.7: _set_eh(xx, y + h, E_WINDOW)
	for yy in range(y + 2, y + h - 2):
		if (yy - y) % step == 0:
			if _ev_at(x, yy) == E_WALL and randf() < 0.7: _set_ev(x, yy, E_WINDOW)
			if _ev_at(x + w, yy) == E_WALL and randf() < 0.7: _set_ev(x + w, yy, E_WINDOW)

func _furnish(t: int, x: int, y: int, w: int, h: int) -> void:
	if w < 4 or h < 4:                               # too small for a layout — a stray crate
		_container(x + 1, y + 1, "box"); return
	match t:
		BT_STORE:  _furnish_store(x, y, w, h)
		BT_CHURCH: _furnish_church(x, y, w, h)
		BT_BARN:   _furnish_barn(x, y, w, h)
		BT_SHED:   _furn(x + 1, y + 1); _furn(x + w - 2, y + h - 2)
		_:         _furnish_house(x, y, w, h)
	# dedicated searchable containers — plenty of them (search-once, ~33% each), scattered on
	# whatever floor the fixtures left open
	var n := maxi(2, int(w * h / 30.0))
	for _i in range(n):
		_container(randi_range(x, x + w - 1), randi_range(y, y + h - 1), _container_kind(t))
	# ~1 in 3 buildings has a workbench (T4 crafting is anchored to them, not TAB-anywhere)
	if randf() < 0.35:
		_bench(randi_range(x, x + w - 1), randi_range(y, y + h - 1))

func _container_kind(t: int) -> String:
	match t:
		BT_STORE:  return ["shelf", "cooler", "cabinet", "register"].pick_random()
		BT_BARN:   return ["crate", "toolbox", "locker", "feed bin"].pick_random()
		BT_CHURCH: return ["cabinet", "donation box"].pick_random()
		BT_SHED:   return ["crate", "toolbox", "box"].pick_random()
		_:         return ["dresser", "cabinet", "wardrobe", "nightstand", "cupboard"].pick_random()

func _furnish_house(x: int, y: int, w: int, h: int) -> void:
	if w >= h:                                       # a partition wall (edge) -> two rooms
		var px := x + int(w / 2.0)
		for yy in range(y, y + h): _set_ev(px, yy, E_WALL)
		var gap := y + randi_range(1, h - 3)
		_set_ev(px, gap, E_DOOR); _set_ev(px, gap + 1, E_DOOR)   # inner doorway (2 tall)
	else:
		var py := y + int(h / 2.0)
		for xx in range(x, x + w): _set_eh(xx, py, E_WALL)
		var gap := x + randi_range(1, w - 3)
		_set_eh(gap, py, E_DOOR); _set_eh(gap + 1, py, E_DOOR)
	_furn(x + 1, y + 1); _furn(x + 1, y + 2)         # a bed against the wall
	_furn(x + w - 2, y + 1)                          # a dresser
	_furn(x + w - 2, y + h - 2)                      # a table

func _furnish_store(x: int, y: int, w: int, h: int) -> void:
	for ax in range(x + 2, x + w - 2, 2):            # shelf aisles
		for yy in range(y + 2, y + h - 2):
			if randf() < 0.85: _furn(ax, yy)
	for xx in range(x + 1, x + w - 1):               # a checkout counter along the back wall
		if randf() < 0.7: _furn(xx, y + 1)

func _furnish_church(x: int, y: int, w: int, h: int) -> void:
	var aisle := x + int(w / 2.0)
	for ry in range(y + 2, y + h - 1, 2):            # pew rows split by a centre aisle
		for xx in range(x + 1, x + w - 1):
			if xx != aisle: _furn(xx, ry)
	_furn(aisle, y + 1)                              # the altar

func _furnish_barn(x: int, y: int, w: int, h: int) -> void:
	for yy in range(y + 1, y + h - 1, 2):            # stalls down one side
		_furn(x + 1, yy); _furn(x + 2, yy)
	_furn(x + w - 2, y + 1); _furn(x + w - 3, y + 1) # hay bales
	_furn(x + w - 2, y + h - 2)

func _pick_btype() -> int:
	var r := randf()
	if r < 0.12: return BT_SHED
	if r < 0.24: return BT_STORE
	if r < 0.32: return BT_BARN
	if r < 0.36: return BT_CHURCH
	return BT_HOUSE

func _btype_size(t: int) -> Vector2i:
	match t:
		BT_BARN:   return Vector2i(randi_range(20, 30), randi_range(15, 22))
		BT_STORE:  return Vector2i(randi_range(18, 28), randi_range(13, 20))
		BT_CHURCH: return Vector2i(randi_range(13, 18), randi_range(15, 22))
		BT_SHED:   return Vector2i(randi_range(8, 10), randi_range(8, 10))
		_:         return Vector2i(randi_range(13, 20), randi_range(10, 15))   # house

func _btype_label(t: int) -> String:
	match t:
		BT_BARN:   return ["BARN", "GRAIN SILO"].pick_random()
		BT_STORE:  return ["FEED STORE", "GAS STATION", "BIG-BOX HUSK", "BAIT SHOP", "DINER"].pick_random()
		BT_CHURCH: return "CHURCH"
		BT_SHED:   return ["TOOL SHED", "PUMP HOUSE"].pick_random()
		_:         return ["FARMHOUSE", "TRAILER", "MOTEL"].pick_random()

func _nearest(vals: Array, v: int) -> int:
	var best: int = v; var bd := 1 << 30
	for a in vals:
		var d: int = absi(int(a) - v)
		if d < bd: bd = d; best = int(a)
	return best

# Put the doorway (a 2-wide gap in the wall edge) on whichever wall faces the nearest road.
func _place_door(x: int, y: int, w: int, h: int) -> void:
	var bxc := x + int(w / 2.0)
	var byc := y + int(h / 2.0)
	var nvx := _nearest(_road_xs, bxc)   # nearest vertical road
	var nhy := _nearest(_road_ys, byc)   # nearest horizontal road
	if absi(nvx - bxc) <= absi(nhy - byc):
		var ex := (x + w) if nvx >= bxc else x       # east or west wall (vertical edges)
		_set_ev(ex, byc, E_DOOR); _set_ev(ex, byc + 1, E_DOOR)
	else:
		var ey := (y + h) if nhy >= byc else y       # south or north wall (horizontal edges)
		_set_eh(bxc, ey, E_DOOR); _set_eh(bxc + 1, ey, E_DOOR)

func _gen_town() -> void:
	_cells = []
	for y in range(GH):
		var row := PackedByteArray(); row.resize(GW); row.fill(C_GRASS)
		_cells.append(row)
	_alloc_edges()
	for y in range(GH):                          # cornfield ring around the town
		for x in range(GW):
			if x < 8 or x >= GW - 8 or y < 8 or y >= GH - 8:
				_set_cell(x, y, C_CORN)
	_road_xs = [int(GW * 0.25), int(GW * 0.5), int(GW * 0.75)]
	_road_ys = [int(GH * 0.34), int(GH * 0.66)]
	for rx in _road_xs:
		_road_v(rx)
	for ry in _road_ys:
		_road_h(ry)
	_buildings = []
	_btype = []
	_containers = []
	_benches = []
	for by in range(16, GH - 16, 26):            # buildings on a lattice (finer grid → wider steps)
		for bx in range(16, GW - 16, 32):
			if randf() < 0.82:
				var t := _pick_btype()
				var sz := _btype_size(t)
				_place_building(bx + randi_range(-1, 2), by + randi_range(-1, 2), sz.x, sz.y, t)
	_scatter_ground()                            # dirt/weed patches so grass isn't a flat sheet
	_scatter_trees()                             # solid trees: a treeline by the corn + sparse in town
	# scavenge sites = a scatter of the buildings, labelled by archetype (keep _btype aligned:
	# shuffle an index list, don't reorder _buildings)
	var order := []
	for i in range(_buildings.size()): order.append(i)
	order.shuffle()
	_sites = []
	for i in range(mini(10, order.size())):
		var bi: int = order[i]
		_sites.append({"rect": _buildings[bi].grow(-TILE), "label": _btype_label(_btype[bi]), "looted": false})
	_roof_a.resize(_buildings.size()); _roof_a.fill(1.0)   # start every roof closed

# Break up the flat green with soft-edged dirt/weed blobs, only over open grass
# (never roads/buildings/corn). Blobs, not salt-and-pepper noise, so it reads as terrain.
func _scatter_ground() -> void:
	var patches := int(GW * GH / 220.0)
	for _i in range(patches):
		var cx := randi_range(4, GW - 5)
		var cy := randi_range(4, GH - 5)
		var kind := C_WEEDS if randf() < 0.62 else C_DIRT
		var rad := randi_range(2, 6)
		for yy in range(cy - rad, cy + rad + 1):
			for xx in range(cx - rad, cx + rad + 1):
				if Vector2(xx - cx, yy - cy).length() <= float(rad) + randf() * 0.6:
					if _cell(xx, yy) == C_GRASS:
						_set_cell(xx, yy, kind)

# Solid trees: a dense treeline hugging the cornfield, thinning to the odd yard tree in
# town. Only over open ground, and never boxing in the player's central spawn.
func _scatter_trees() -> void:
	var mid := Vector2i(int(GW / 2.0), int(GH / 2.0))
	for y in range(4, GH - 4):
		for x in range(4, GW - 4):
			var c := _cell(x, y)
			if c != C_GRASS and c != C_WEEDS: continue
			if Vector2(x - mid.x, y - mid.y).length() < 10.0: continue   # keep spawn clear
			var edge := x < 18 or x >= GW - 18 or y < 18 or y >= GH - 18
			if randf() < (0.05 if edge else 0.006):
				_set_cell(x, y, C_TREE)

# Give each building a light occluder so the flashlight/glow are BLOCKED by walls
# (no shining through buildings). A rectangle at the footprint = the building is opaque
# to light; the near wall is lit, everything behind/inside falls into shadow.
func _build_occluders() -> void:
	for b in _buildings:
		var occ := LightOccluder2D.new()
		var poly := OccluderPolygon2D.new()
		poly.polygon = PackedVector2Array([
			b.position, Vector2(b.end.x, b.position.y), b.end, Vector2(b.position.x, b.end.y)])
		occ.occluder = poly
		add_child(occ)

# solid AREAS (trees, furniture, off-map border). Walls are edges, tested separately.
func _cell_solid(px: float, py: float, r: float) -> bool:
	for off in [Vector2(-r, -r), Vector2(r, -r), Vector2(-r, r), Vector2(r, r)]:
		var c := _cell(int((px + off.x) / TILE), int((py + off.y) / TILE))
		if c == C_TREE or c == C_FURN or c == C_CONTAINER or c == C_BENCH or c == C_WALL:
			return true
	return false

# a solid vertical edge overlapping the circle blocks horizontal movement
func _hits_v_edge(px: float, py: float, r: float) -> bool:
	var cy0 := int((py - r) / TILE); var cy1 := int((py + r) / TILE)
	for ecx in range(int((px - r) / TILE), int((px + r) / TILE) + 2):
		if absf(px - ecx * TILE) < r:
			for ecy in range(cy0, cy1 + 1):
				var e := _ev_at(ecx, ecy)
				if e == E_WALL or e == E_WINDOW: return true
	return false

# a solid horizontal edge overlapping the circle blocks vertical movement
func _hits_h_edge(px: float, py: float, r: float) -> bool:
	var cx0 := int((px - r) / TILE); var cx1 := int((px + r) / TILE)
	for ecy in range(int((py - r) / TILE), int((py + r) / TILE) + 2):
		if absf(py - ecy * TILE) < r:
			for ecx in range(cx0, cx1 + 1):
				var e := _eh_at(ecx, ecy)
				if e == E_WALL or e == E_WINDOW: return true
	return false

func _blocked_x(px: float, py: float, r: float) -> bool:
	return _cell_solid(px, py, r) or _hits_v_edge(px, py, r)

func _blocked_y(px: float, py: float, r: float) -> bool:
	return _cell_solid(px, py, r) or _hits_h_edge(px, py, r)

# general "is this circle overlapping anything solid" — used for spawn placement
func _solid_circle(p: Vector2, r: float) -> bool:
	return _cell_solid(p.x, p.y, r) or _hits_v_edge(p.x, p.y, r) or _hits_h_edge(p.x, p.y, r)

func _restart() -> void:
	_phase = Phase.ALIVE
	_spawn_timer = 0.0
	_hp = PLAYER_MAX_HP
	_player = Vector2(WORLD_W * 0.5, WORLD_H * 0.5)
	_zombies.clear(); _projectiles.clear(); _dropped_boomerangs.clear(); _zones.clear()
	_clear_pickups()
	_dmg_nums.clear(); _particles.clear(); _pot.clear()
	_traps.clear(); _turrets.clear(); _decoys.clear(); _arcs.clear()
	_rings.clear(); _muzzle = {}; _hitstop = 0.0
	_invuln = 0.0; _hurt_flash = 0.0; _shake = 0.0; _paused = false
	_shield = 0.0; _speed_mult = 1.0; _speed_timer = 0.0
	_dark = 0.0; _time_of_day = 0.35; _day_count = 1; _last_day = 1   # every run opens on a bright morning
	_flashlight_on = true
	_arsenal = [_starter_gadget()]
	_equipped_idx = 0
	_equipped = _arsenal[0]
	_hand_item = null; _hand_hold = false; _armor = null; _item_gadgets.clear()
	# a handful of bullets to start (the thing you scavenge for), a stray ammo type to
	# reveal universal-ammo once lucid, and some junk for junk-as-ammo later.
	_inv = {"bullets": 2, "arrows": 1, "duct_tape": 1, "road_flare": 1,
			"brick": 1, "nails": 1, "motor_oil": 1, "first_aid": 1}
	_log("You wake up. Something is very wrong. (WASD move · mouse aim · click fire · F light · R reload)")
	for s in _sites: s["looted"] = false
	if _debug: _grant_all()
	_refresh_inventory_ui()
	_refresh_equipped()
	_refresh_arsenal_ui()
	_refresh_equipment()
	_refresh_bench_locks()

func _equip(i: int) -> void:
	if i < 0 or i >= _arsenal.size():
		return
	_equipped_idx = i
	_equipped = _arsenal[i]
	_hand_item = null      # a crafted gadget is in hand now, not a raw item
	_hand_hold = false
	_refresh_equipped()
	_refresh_arsenal_ui()
	_refresh_equipment()

# --- single-item wielding (equip a raw junk item into the HAND slot) ----------
# Non-consuming: slotting in/out never uses the item up (unlike the combine bench).
# Behavior is resolved from the item itself: weapon fires, throwable throws, else held.

## Resolve one item to its gadget, cached so ammo/state survive re-equipping.
func _item_gadget(id: String) -> Gadget:
	if _item_gadgets.has(id):
		return _item_gadgets[id]
	var g := Resolver.wield(_db[id])   # delivery from the item's ARCHETYPE, not tag-mashing
	_item_gadgets[id] = g
	return g

func _wield_item(id: String) -> void:
	var it: Item = _db[id]
	if it.is_armor():
		_equip_armor(id); return
	var g := _item_gadget(id)
	_equipped = g
	_equipped_idx = -1
	_hand_item = it
	_hand_hold = it.archetype == Item.ARCH_INERT   # inert = no standalone use, just held
	_log("Wielding [b]%s[/b] — %s" % [it.display_name, _archetype_label(it.archetype)])
	_refresh_equipped(); _refresh_arsenal_ui(); _refresh_equipment()

func _equip_armor(id: String) -> void:
	_armor = _db[id]
	_log("Equipped armor: [b]%s[/b]  (armor has no effect yet)" % _armor.display_name)
	_refresh_equipment()

func _unequip_hand() -> void:
	if _arsenal.is_empty():
		return
	_equip(0)   # back to the starter weapon (empty-handed has no fists yet)
	_log("Stowed. Back to %s." % _equipped.display_name)

func _unequip_armor() -> void:
	if _armor == null:
		return
	_log("Removed armor: %s." % _armor.display_name)
	_armor = null
	_refresh_equipment()

## Short role label for a wielded item, driven by its declared archetype.
func _archetype_label(arch: String) -> String:
	match arch:
		"swing", "thrust", "grind": return "MELEE"
		"lob", "return": return "THROW"
		"scatter": return "CALTROPS"
		"pour": return "POUR"
		"projectile", "beam": return "SHOOT"
		"spray": return "SPRAY"
		"self": return "USE"
		"field": return "AURA"
		"trap": return "TRAP"
		"turret": return "TURRET"
		"decoy": return "LURE"
		_: return "HELD"   # inert

func _starter_gadget() -> Gadget:
	var g := Gadget.new()
	g.display_name = "Rusty Pistol"
	g.description = "Standard issue. Reliable, boring, yours."
	g.delivery = Gadget.Delivery.PROJECTILE
	g.add(Gadget.DAMAGE, 8.0)
	g.projectile_speed = 720.0
	g.uses_ammo = true
	g.ammo_max = 14
	g.native_ammo = "bullets"
	g.color = Color(0.85, 0.82, 0.5)
	g.fill_plain()
	return g

func _game_over() -> void:
	_phase = Phase.GAME_OVER
	_log("You died on day %d. Press R to wake up again." % _day_count)

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
	if _flashlight != null:
		_flashlight.position = _player
		_flashlight.rotation = _aim.angle()
	if _player_glow != null:
		_player_glow.position = _player
	if _cam != null:
		_cam.position = _player
		var tz := _target_zoom()                       # dynamic camera: pull in indoors, out for optics
		_cam.zoom = _cam.zoom.lerp(Vector2(tz, tz), clampf(delta * 4.0, 0.0, 1.0))
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
	_update_atmosphere(delta)

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
	_update_dropped_boomerangs(delta)
	_update_zones(delta)
	_update_world(delta)

	queue_redraw()

func _handle_input(delta: float) -> void:
	var move := Vector2.ZERO
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP): move.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN): move.y += 1.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT): move.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): move.x += 1.0
	if move != Vector2.ZERO:
		var step := move.normalized() * PLAYER_SPEED * _speed_mult * delta
		var r := float(PLAYER_RADIUS)
		if not _blocked_x(_player.x + step.x, _player.y, r):   # per-axis = slide on walls
			_player.x += step.x
		if not _blocked_y(_player.x, _player.y + step.y, r):
			_player.y += step.y
	_player.x = clampf(_player.x, PLAYER_RADIUS, WORLD_W - PLAYER_RADIUS)
	_player.y = clampf(_player.y, PLAYER_RADIUS, WORLD_H - PLAYER_RADIUS)

	var mouse := get_global_mouse_position()
	_aim = (mouse - _player).normalized()
	var held := Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT)
	var want := _lmb_edge if (_equipped != null and _equipped.semi) else held
	if want and _fire_timer <= 0.0 and not _hand_hold:
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
		if event.keycode == KEY_TAB:
			_toggle_build()
		elif event.keycode == KEY_SPACE and _phase != Phase.GAME_OVER:
			_paused = not _paused
			_log("[ PAUSED ]" if _paused else "[ unpaused ]")
		elif event.keycode == KEY_R and _phase != Phase.GAME_OVER:
			_reload()
		elif event.keycode == KEY_F and _phase != Phase.GAME_OVER:
			_flashlight_on = not _flashlight_on
			_apply_darkness()
			_log("Flashlight %s." % ("ON" if _flashlight_on else "OFF — you're harder to see, and blind"))
		elif event.keycode == KEY_E and _phase != Phase.GAME_OVER:
			_interact()
		elif event.keycode == KEY_BRACKETRIGHT:
			_awakening = clampf(_awakening + 0.2, 0.0, 1.0)
			_log("[lucidity] %.2f — %s" % [_awakening, _lucid_tier()])
			_refresh_bench_locks()
		elif event.keycode == KEY_BRACKETLEFT:
			_awakening = clampf(_awakening - 0.2, 0.0, 1.0)
			_log("[lucidity] %.2f — %s" % [_awakening, _lucid_tier()])
			_refresh_bench_locks()
		elif event.keycode == KEY_F1:
			_debug = not _debug
			_awakening = 1.0 if _debug else 0.15   # debug = fully lucid; normal starts asleep
			_log("[MODE] %s" % ("DEBUG — all items stocked (G top-up · T specials)" if _debug else "NORMAL — scavenge for your items"))
			_restart()
		elif _debug and event.keycode == KEY_G:
			_grant_all()
		elif _debug and event.keycode == KEY_T:
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

# The continuous world: scavenge anytime, spawn scaled by night, zombies that
# detect / hunt / disengage. No waves. See DESIGN.md §6.
# context-driven camera zoom target: intimate indoors, wide through optics, default on foot
func _target_zoom() -> float:
	if _optic_zoom: return ZOOM_OPTIC
	if _inside_building: return ZOOM_INTERIOR
	return CAM_ZOOM

func _update_world(delta: float) -> void:
	# roofs fade open for the building you're standing in, closed for the rest
	_inside_building = false
	for i in range(_buildings.size()):
		var here := (_buildings[i] as Rect2).grow(6.0).has_point(_player)
		if here: _inside_building = true
		_roof_a[i] = lerpf(_roof_a[i], 0.0 if here else 1.0, 0.18)

	# near a workbench? (unlocks the T4 build actions; refresh the bench panel if it changed)
	var was_at := _at_bench
	_at_bench = false
	for b in _benches:
		if b.distance_to(_player) < BENCH_RANGE:
			_at_bench = true; break
	if _at_bench != was_at: _refresh_bench_locks()

	# (looting is now E-to-search containers inside buildings — no more walk-in auto-loot)
	var night := _night()   # 0 = full day, 1 = deepest night — the threat driver

	# continuous spawning: a few shufflers by day, a mounting horde at night
	var cap := int(3.0 + night * 26.0 + float(_day_count - 1) * 3.0)
	if _zombies.size() < cap:
		_spawn_timer -= delta
		if _spawn_timer <= 0.0:
			_spawn_zombie()
			_spawn_timer = lerpf(2.6, 0.4, clampf(night, 0.0, 1.0))

	# senses: dull and short-sighted by day (lethargic), keen at night
	var perceive := lerpf(90.0, 270.0, clampf(night, 0.0, 1.0))
	var day_speed := lerpf(0.4, 1.0, clampf(night, 0.0, 1.0))

	var alive: Array[Dictionary] = []
	for z in _zombies:
		if z.get("dead", false):
			continue
		z["flash"] = maxf(0.0, z["flash"] - delta)
		z["slow"] = maxf(0.0, z["slow"] - delta)
		z["snare"] = maxf(0.0, z["snare"] - delta)
		z["freeze"] = maxf(0.0, float(z.get("freeze", 0.0)) - delta)
		z["scale"] = minf(1.0, float(z.get("scale", 1.0)) + delta * 5.0)
		z["squash"] = maxf(0.0, float(z.get("squash", 0.0)) - delta * 5.0)
		if float(z.get("burn_t", 0.0)) > 0.0:
			z["burn_t"] = float(z["burn_t"]) - delta
			z["hp"] = float(z["hp"]) - float(z.get("burn", 0.0)) * delta
			if z["hp"] <= 0.0:
				_on_zombie_death(z); continue

		# --- detection: am I detectable to this one right now? ---
		var zpos: Vector2 = z["pos"]
		var dist := zpos.distance_to(_player)
		var detect := dist < perceive
		if _flashlight_on and _dark > 0.2 and dist < ZOMBIE_LIGHT_RANGE:
			detect = true                                   # a lit flashlight (dusk on) gives you away
		if detect:
			z["alert"] = minf(1.0, float(z["alert"]) + delta * 2.5)   # awareness rises fast
			z["known"] = _player                            # remember where you are
		else:
			z["alert"] = maxf(0.0, float(z["alert"]) - delta / ZOMBIE_LOSE)  # ...decays slowly
		var st := ZState.WANDER
		if float(z["alert"]) >= 0.6: st = ZState.CHASE
		elif float(z["alert"]) >= 0.15: st = ZState.ALERT
		z["state"] = st

		# --- movement per state ---
		var spd: float = float(z["speed"]) * day_speed
		if z["freeze"] > 0.0 or z["snare"] > 0.0: spd = 0.0
		elif z["slow"] > 0.0: spd *= 0.35
		var target: Vector2
		if st == ZState.WANDER:
			spd *= 0.35                                     # an aimless shuffle
			var w: Vector2 = z.get("wander", zpos)
			if zpos.distance_to(w) < 24.0 or randf() < delta * 0.4:
				w = zpos + Vector2(randf_range(-1, 1), randf_range(-1, 1)).normalized() * randf_range(70.0, 200.0)
				z["wander"] = w
			target = w
		else:
			target = z["known"]                             # ALERT -> last-known · CHASE -> you
			if st == ZState.ALERT: spd *= 0.7
		# a decoy nearby is louder than you — it steals the target
		var bd := INF
		for d in _decoys:
			var dd: float = zpos.distance_to(d["pos"])
			if dd < float(d["range"]) and dd < bd:
				bd = dd; target = d["pos"]; z["alert"] = maxf(float(z["alert"]), 0.7)
		var to_target := target - zpos
		var vel := Vector2.ZERO
		if to_target.length() > 2.0:
			vel = to_target.normalized() * spd
		var step := vel * delta + (z["knock"] as Vector2) * delta
		# per-axis wall collision — zombies slide along buildings instead of phasing through
		var zr := 8.0
		var pre := zpos
		if not _blocked_x(zpos.x + step.x, zpos.y, zr):
			zpos.x += step.x
		if not _blocked_y(zpos.x, zpos.y + step.y, zr):
			zpos.y += step.y
		# stuck against a wall while hunting -> wall-follow toward a way around (door/corner)
		if st != ZState.WANDER and vel.length() > 1.0 and (zpos - pre).length() < spd * delta * 0.5:
			if not z.has("detour"): z["detour"] = 1.0 if randf() < 0.5 else -1.0
			var tan := Vector2(-vel.y, vel.x).normalized() * float(z["detour"]) * spd * delta
			if not _blocked_x(zpos.x + tan.x, zpos.y, zr): zpos.x += tan.x
			if not _blocked_y(zpos.x, zpos.y + tan.y, zr): zpos.y += tan.y
		z["pos"] = zpos
		z["knock"] = z["knock"].lerp(Vector2.ZERO, 0.12)

		# contact damage
		if (z["pos"] as Vector2).distance_to(_player) < PLAYER_RADIUS + 8.0 and _invuln <= 0.0:
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
				_game_over(); return
		alive.append(z)
	_zombies = alive
	_update_aura(delta)
	_update_traps(delta)
	_update_turrets(delta)
	_update_decoys(delta)

	# sites refill each new dawn (dawn ~ time-of-day 0.25); tracked via _last_day
	if _day_count != _last_day:
		_last_day = _day_count
		for s in _sites: s["looted"] = false
		_log("A new day. Day %d. The scavenge is fresh." % _day_count)

# alert every zombie within `radius` of `pos` — gunfire and explosions draw them
func _alert_zombies(pos: Vector2, radius: float, amount: float) -> void:
	for z in _zombies:
		if z.get("dead", false):
			continue
		if (z["pos"] as Vector2).distance_to(pos) < radius:
			z["alert"] = minf(1.0, float(z.get("alert", 0.0)) + amount)
			z["known"] = _player

func _spawn_zombie() -> void:
	# spawn in a ring just beyond view — they emerge from the dark around you, not at map edges
	var p := _player
	for _try in range(8):                                  # retry until we find an open (non-wall) spot
		var ang := randf() * TAU
		p = _player + Vector2(cos(ang), sin(ang)) * randf_range(950.0, 1300.0)  # beyond the wider view
		p.x = clampf(p.x, MARGIN, WORLD_W - MARGIN)
		p.y = clampf(p.y, MARGIN, WORLD_H - MARGIN)
		if not _solid_circle(p, 8.0):
			break
	var dc := float(_day_count - 1)                        # difficulty ramps with days survived
	var hp := 18.0 + dc * 8.0
	_zombies.append({
		"pos": p, "hp": hp, "max_hp": hp,
		"speed": minf(64.0 + dc * 6.0, 150.0),
		"dmg": 8.0 + dc, "flash": 0.0, "slow": 0.0, "snare": 0.0,
		"knock": Vector2.ZERO, "dead": false, "burn": 0.0, "burn_t": 0.0, "freeze": 0.0,
		"scale": 0.0, "squash": 0.0,
		"state": ZState.WANDER, "alert": 0.0, "known": p, "wander": p,   # detection AI
	})

# --- firing / projectiles ----------------------------------------------------

func _fire() -> void:
	if _equipped == null:
		return
	var round_prof: Dictionary = {}
	if _equipped.uses_ammo:
		if _equipped.ammo_count() <= 0:
			if _equipped.delivery == Gadget.Delivery.RETURN:
				_log("%s is still out there — catch it or go pick it up." % _equipped.display_name)
			else:
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
		Gadget.Delivery.CALTROPS:
			_throw_ground(_equipped, "caltrops"); _fire_timer = 0.5
		Gadget.Delivery.PUDDLE:
			_throw_ground(_equipped, "puddle"); _fire_timer = 0.5
		Gadget.Delivery.SELF:
			_use_self(_equipped); _fire_timer = 0.5
		Gadget.Delivery.TURRET:
			_deploy_turret(_equipped); _fire_timer = 0.6
		Gadget.Delivery.DECOY:
			_deploy_decoy(_equipped); _fire_timer = 0.6
		Gadget.Delivery.AURA:
			_fire_timer = 0.2  # passive; aura ticks each frame
	# loud weapons make noise — the horde hears gunfire and converges (stealth matters)
	if _equipped.delivery in [Gadget.Delivery.PROJECTILE, Gadget.Delivery.LOBBED, Gadget.Delivery.CONE, Gadget.Delivery.BEAM]:
		_alert_zombies(_player, NOISE_GUNSHOT, 0.6)

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
		if to_z.length() < 38.0 and to_z.normalized().dot(_aim) > 0.35:   # melee reach (rescaled)
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

func _draw_boomerang(pos: Vector2, angle: float, col: Color, s := 1.0) -> void:
	var arm := 11.0 * s
	var a := pos + Vector2(cos(angle), sin(angle)) * arm
	var b := pos + Vector2(cos(angle + 2.1), sin(angle + 2.1)) * arm
	draw_line(a, pos, col, 3.0)
	draw_line(pos, b, col, 3.0)

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
	p["target"] = _player                                 # set for real at the apex (where you stood then)
	p["gadget"] = g                                       # to refund the throw on catch / pickup
	p["pierce"] = 99                                      # cuts through the crowd, both ways
	p["perp"] = Vector2(-_aim.y, _aim.x) * (1.0 if randf() > 0.5 else -1.0)  # which way it bows
	p["spin"] = 0.0
	p["life"] = 4.0                                       # if never caught, it drops to the floor
	# per-gadget flight tuning (set by a resolver/AI); fall back to the global defaults
	p["b_range"] = float(g.params.get("range", BOOMERANG_RANGE))
	p["b_curve"] = float(g.params.get("curve", BOOMERANG_CURVE))
	p["b_speed"] = float(g.params.get("return_speed", BOOMERANG_SPEED))
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
	_decoys.append({"pos": _player, "life": 12.0, "range": 150.0})
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
			var v: Vector2 = p["vel"]
			var perp: Vector2 = p["perp"]
			var b_curve: float = float(p["b_curve"])
			if not p["returning"]:
				v = v * maxf(0.0, 1.0 - 1.7 * delta)              # decelerate toward the apex
				v += perp * b_curve * delta                       # narrow sideways bow on the way out
				if (rpos - (p["origin"] as Vector2)).length() > float(p["b_range"]) or v.length() < 140.0:
					p["returning"] = true
					p["target"] = _player                         # where you stood at the apex — it comes back to HERE
					p["hits"].clear()                             # let it cut the crowd again coming back
			else:
				var tgt: Vector2 = p["target"]
				v = v.lerp((tgt - rpos).normalized() * float(p["b_speed"]), 0.12)  # curve back to that spot
				v += perp * b_curve * 0.4 * delta
				if rpos.distance_to(_player) < 26.0:
					_catch_boomerang(p); continue                 # you were there to catch it → refund
				elif rpos.distance_to(tgt) < 22.0:
					_drop_boomerang(p); continue                  # you'd moved on → it lands where you were
			p["vel"] = v
			p["spin"] = float(p.get("spin", 0.0)) + delta * 22.0
		if float(p["drag"]) > 0.0:                       # feather rounds: fast, then float to a stop
			p["vel"] = (p["vel"] as Vector2) * maxf(0.0, 1.0 - float(p["drag"]) * delta)
		p["pos"] += p["vel"] * delta
		p["life"] -= delta
		var tr: Array = p.get("trail", [])              # motion trail for readability + feel
		tr.append(p["pos"])
		if tr.size() > 6: tr.pop_front()
		p["trail"] = tr
		# walls stop shots; windows + doors let them through (boomerangs excepted)
		var cxp := int((p["pos"] as Vector2).x / TILE)
		var cyp := int((p["pos"] as Vector2).y / TILE)
		var hit_cell := _cell(cxp, cyp)
		var stop := hit_cell == C_TREE or hit_cell == C_FURN or hit_cell == C_CONTAINER or hit_cell == C_BENCH or hit_cell == C_WALL
		if not stop:                                    # did it cross a solid wall edge this frame?
			var pcx: int = p.get("pcx", cxp)
			var pcy: int = p.get("pcy", cyp)
			if cxp != pcx and _ev_at(maxi(cxp, pcx), cyp) == E_WALL: stop = true
			if cyp != pcy and _eh_at(cxp, maxi(cyp, pcy)) == E_WALL: stop = true
		p["pcx"] = cxp; p["pcy"] = cyp
		if not p.get("return", false) and stop:
			if p["lobbed"]: _lob_land(p)   # a thrown thing lands/detonates against the wall
			else: _burst(p["pos"], Color(0.75, 0.75, 0.8), 4, 150.0)   # bullet spark on the wall
			continue
		# world edge: ricochet if the round has bounces left, otherwise it's absorbed
		if int(p["bounce"]) > 0:
			var pos: Vector2 = p["pos"]
			var v: Vector2 = p["vel"]
			var b := false
			if pos.x < MARGIN or pos.x > WORLD_W - MARGIN:
				v.x = -v.x; pos.x = clampf(pos.x, MARGIN, WORLD_W - MARGIN); b = true
			if pos.y < MARGIN or pos.y > WORLD_H - MARGIN:
				v.y = -v.y; pos.y = clampf(pos.y, MARGIN, WORLD_H - MARGIN); b = true
			if b:
				p["vel"] = v; p["pos"] = pos; p["bounce"] = int(p["bounce"]) - 1
		elif _out_of_play(p["pos"]) and not p.get("return", false):
			if p["lobbed"]: _lob_land(p)
			continue
		var spent := false
		for z in _zombies:
			if z.get("dead", false) or p["hits"].has(z):
				continue
			if (p["pos"] as Vector2).distance_to(z["pos"]) < 15.0:
				if p["lobbed"]:
					_lob_land(p); spent = true; break
				_apply_proj_hit(p, z)
				p["hits"].append(z)
				if int(p["pierce"]) <= 0:
					spent = true; break
				p["pierce"] = int(p["pierce"]) - 1
		if spent:
			continue
		if p["life"] <= 0.0:
			if p["lobbed"]: _lob_land(p)
			elif p.get("return", false): _drop_boomerang(p)   # never caught → it falls to the floor
			continue
		live.append(p)
	_projectiles = live

func _catch_boomerang(p: Dictionary) -> void:
	var g = p.get("gadget", null)
	if g != null and g is Gadget:
		(g as Gadget).fill_plain()   # ammo 0/1 -> 1/1
	_burst(_player, Color(0.8, 0.9, 1.0), 6, 120.0)

func _drop_boomerang(p: Dictionary) -> void:
	_dropped_boomerangs.append({"pos": p["pos"], "gadget": p.get("gadget", null), "spin": 0.0})

# walk over a grounded boomerang to retrieve it — refunds the throw (0/1 -> 1/1)
func _update_dropped_boomerangs(delta: float) -> void:
	if _dropped_boomerangs.is_empty():
		return
	var live: Array[Dictionary] = []
	for d in _dropped_boomerangs:
		d["spin"] = float(d.get("spin", 0.0)) + delta * 5.0
		if _player.distance_to(d["pos"]) < 30.0:
			var g = d.get("gadget", null)
			if g != null and g is Gadget: (g as Gadget).fill_plain()
			_burst(d["pos"], Color(0.8, 0.9, 1.0), 6, 120.0)
			_log("Retrieved %s." % ((g as Gadget).display_name if g is Gadget else "boomerang"))
			continue
		live.append(d)
	_dropped_boomerangs = live

# --- ground hazards: caltrops (scatter) + puddles (pour) ----------------------
# Thrown short; on landing they drop a persistent zone that afflicts anything on it.

func _throw_ground(g: Gadget, kind: String) -> void:
	var p := _make_proj(_aim, g, true, false, {})   # arcs out like a lobbed throw, then lands
	p["life"] = 0.42                                  # short toss, not a long-range shot
	p["zone"] = {
		"kind": kind,
		"radius": 74.0 if kind == "caltrops" else 66.0,
		"dmg": g.amount_of(Gadget.DAMAGE),
		"slow": g.get_effect(Gadget.SLOW).get("duration", 0.0),
		"burn_amt": g.get_effect(Gadget.BURN).get("amount", 0.0),
		"burn_dur": g.get_effect(Gadget.BURN).get("duration", 0.0),
		"snare": g.get_effect(Gadget.SNARE).get("duration", 0.0),
		"life": 9.0 if kind == "caltrops" else 6.0,
		"color": g.color,
	}
	_projectiles.append(p)

# a lobbed projectile reached the ground — drop its zone, or detonate (old behavior)
func _lob_land(p: Dictionary) -> void:
	if p.has("zone"):
		_drop_zone(p["pos"], p["zone"])
	else:
		_explode_at(p["pos"], p["onhit"])

func _drop_zone(pos: Vector2, spec: Dictionary) -> void:
	var z := spec.duplicate()
	z["pos"] = pos
	z["life0"] = float(z["life"])
	z["tick"] = 0.0
	_zones.append(z)
	if String(z["kind"]) == "caltrops":
		_burst(pos, Color(0.72, 0.72, 0.78), 12, 200.0)   # nails scatter out
	else:
		_ring(pos, z["color"], float(z["radius"]), 3.0, 0.35)   # a spreading puddle

func _update_zones(delta: float) -> void:
	if _zones.is_empty():
		return
	var live: Array[Dictionary] = []
	for z in _zones:
		z["life"] = float(z["life"]) - delta
		z["tick"] = float(z["tick"]) - delta
		var do_dmg := float(z["tick"]) <= 0.0
		if do_dmg:
			z["tick"] = 0.35   # damage/burn tick interval
		var r: float = float(z["radius"])
		for zo in _zombies:
			if zo.get("dead", false):
				continue
			if (zo["pos"] as Vector2).distance_to(z["pos"]) >= r:
				continue
			if float(z["slow"]) > 0.0:
				zo["slow"] = maxf(float(zo.get("slow", 0.0)), 0.5)   # stays slowed while on it
			if float(z["snare"]) > 0.0:
				zo["snare"] = maxf(float(zo.get("snare", 0.0)), 0.4)
			if do_dmg:
				if float(z["dmg"]) > 0.0:
					_apply_damage(zo, float(z["dmg"]), z["pos"])
				if float(z["burn_amt"]) > 0.0:
					zo["burn"] = float(z["burn_amt"]); zo["burn_t"] = float(z["burn_dur"])
		if float(z["life"]) > 0.0:
			live.append(z)
	_zones = live

func _apply_proj_hit(p: Dictionary, z: Dictionary) -> void:
	var o: Dictionary = p["onhit"]
	if float(o["explode_r"]) > 0.0:
		_explode_at(p["pos"], o); return
	z["flash"] = 0.1
	_burst(p["pos"], Color(1.0, 0.9, 0.65), 4, 210.0)   # impact sparks
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
	_flash(at, Color(1.0, 0.55, 0.2), 2.6, 2.6, 0.25)   # explosion lights the whole area
	_alert_zombies(at, 560.0, 0.9)                       # a blast is heard far and wide
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
	_flash(at, Color(1.0, 0.55, 0.2), 2.6, 2.6, 0.25)   # explosion lights the whole area
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
			if not z.get("dead", false) and (z["pos"] as Vector2).distance_to(t["pos"]) < 18.0:
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
	_blood(z["pos"], 5)
	_dmg_num(z["pos"], str(int(dmg)), Color(0.6, 0.9, 1.0) if shatter else Color(1, 0.9, 0.5))
	if z["hp"] <= 0.0:
		_on_zombie_death(z)

func _on_zombie_death(z: Dictionary) -> void:
	# mark dead; the WAVE update drops it next pass (avoids mutating mid-iteration)
	z["dead"] = true
	_blood(z["pos"], 20)
	_ring(z["pos"], Color(0.7, 0.2, 0.15), 32.0, 3.0, 0.26)
	_flash(z["pos"], Color(0.9, 0.3, 0.2), 0.5, 0.7, 0.1)
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

# E — search the nearest container in reach. Search-once, ~33% payout.
const INTERACT_RANGE := 26.0
const BENCH_RANGE := 34.0   # how close to a workbench you must be for T4 build actions
func _interact() -> void:
	var best := -1
	var bd := INTERACT_RANGE
	for i in range(_containers.size()):
		if _containers[i]["searched"]: continue
		var d: float = (_containers[i]["pos"] as Vector2).distance_to(_player)
		if d < bd: bd = d; best = i
	if best < 0:
		return
	var c: Dictionary = _containers[best]
	c["searched"] = true
	if randf() < 0.33:
		var iid: String = _db.keys().pick_random()
		_grant(iid, "You search the %s — %s." % [c["kind"], (_db[iid] as Item).display_name])
	else:
		_log("You search the %s. Nothing." % c["kind"])

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
	var fl: Array[Dictionary] = []
	for f in _flashes:
		f["t"] = float(f["t"]) - delta
		var lt: PointLight2D = f["l"]
		if float(f["t"]) <= 0.0:
			lt.energy = 0.0
		else:
			lt.energy = float(f["e0"]) * (float(f["t"]) / float(f["dur"]))
			fl.append(f)
	_flashes = fl

# The DAY/NIGHT CLOCK drives the darkness now (replaces the old wave-progress curve).
# Time advances while you play; darkness = 0 at noon, 1 at midnight, with day & night
# plateaus and quicker dawn/dusk transitions. The clock holds while paused / game over.
func _update_atmosphere(delta: float) -> void:
	if _phase != Phase.GAME_OVER and not _paused:
		_time_of_day += delta / DAY_LENGTH
		while _time_of_day >= 1.0:
			_time_of_day -= 1.0
			_day_count += 1
	var night := (cos(TAU * _time_of_day) + 1.0) * 0.5   # 1 at midnight, 0 at noon
	_dark = smoothstep(0.12, 0.88, night)                # flat day/night, snappy dawn/dusk
	_apply_darkness()

## How far into the night we are (0 = full day, 1 = deepest night) — the threat driver.
func _night() -> float:
	return _dark

func _time_label() -> String:
	if _time_of_day < 0.22 or _time_of_day >= 0.80: return "NIGHT"
	if _time_of_day < 0.34: return "DAWN"
	if _time_of_day < 0.66: return "DAY"
	return "DUSK"

func _apply_darkness() -> void:
	const DAY := Color(0.98, 0.98, 1.0)
	const NIGHT := Color(0.12, 0.13, 0.18)
	var lit := _dark > 0.02   # daylight kills the flashlight/glow entirely (no washed-out day)
	if _cm != null:
		_cm.color = DAY.lerp(NIGHT, _dark)
	if _flashlight != null:
		_flashlight.energy = 1.6 * _dark if _flashlight_on else 0.0
		_flashlight.visible = lit and _flashlight_on
	if _player_glow != null:
		_player_glow.energy = 0.7 * _dark if _flashlight_on else 0.0
		_player_glow.visible = lit and _flashlight_on
	if _fog_mat != null:
		_fog_mat.set_shader_parameter("density", 0.16 * _dark)

func _dmg_num(pos: Vector2, text: String, col: Color) -> void:
	_dmg_nums.append({"pos": pos + Vector2(0, -16), "text": text, "life": 0.7, "col": col})

func _burst(pos: Vector2, col: Color, count := 8, speed := 160.0) -> void:
	for i in range(count):
		var a := randf() * TAU
		_particles.append({"pos": pos, "vel": Vector2(cos(a), sin(a)) * randf_range(40, speed),
			"life": randf_range(0.3, 0.6), "col": col})

func _blood(pos: Vector2, amt := 10) -> void:
	for i in range(amt):
		var a := randf() * TAU
		_particles.append({"pos": pos, "vel": Vector2(cos(a), sin(a)) * randf_range(30.0, 200.0),
			"life": randf_range(0.25, 0.55), "col": Color(0.5, 0.05, 0.06)})

# a brief transient light (muzzle flash, explosion, spark) — punches through the dark
func _flash(pos: Vector2, col: Color, energy: float, scale: float, dur: float) -> void:
	if _light_pool.is_empty():
		return
	var l := _light_pool[_light_i]
	_light_i = (_light_i + 1) % _light_pool.size()
	l.position = pos
	l.color = col
	l.texture_scale = scale
	l.energy = energy
	_flashes.append({"l": l, "t": dur, "dur": dur, "e0": energy})

# an expanding shockwave ring — cheap, high-impact feedback for hits/explosions/deaths
func _ring(pos: Vector2, col: Color, max_r: float, w := 3.0, life := 0.32) -> void:
	_rings.append({"pos": pos, "r": 6.0, "max_r": max_r, "life": life, "life0": life, "col": col, "w": w})

func _freeze(t: float) -> void:
	_hitstop = maxf(_hitstop, t)

func _muzzle_kick(col: Color) -> void:
	_muzzle = {"pos": _player + _aim * 22.0, "life": 0.06, "col": col}
	_flash(_player + _aim * 24.0, Color(1.0, 0.82, 0.45), 1.5, 1.1, 0.09)   # muzzle throws light
	var perp := Vector2(-_aim.y, _aim.x) * (1.0 if randf() > 0.5 else -1.0)
	_particles.append({"pos": _player + _aim * 8.0, "vel": perp * randf_range(70.0, 130.0) - _aim * 30.0,
		"life": 0.7, "col": Color(0.85, 0.72, 0.32)})   # ejected casing

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
	return p.x < 0.0 or p.x > WORLD_W or p.y < 0.0 or p.y > WORLD_H

# =============================================================================
# DRAW
# =============================================================================

# thin wall/window lines on tile edges (PZ-style). Drawn after the ground cells,
# under entities; roofs (drawn last) hide them from outside.
func _draw_wall_edges(x0: int, x1: int, y0: int, y1: int) -> void:
	var wall_col := Color(0.42, 0.35, 0.30)
	var win_col := Color(0.45, 0.60, 0.66)
	for ecy in range(y0, y1):                         # vertical edges (west side of each cell)
		for ecx in range(x0, x1 + 1):
			var ev: int = _ev[ecy][ecx]
			if ev == E_WALL or ev == E_WINDOW:
				var ex := ecx * TILE
				draw_line(Vector2(ex, ecy * TILE), Vector2(ex, (ecy + 1) * TILE),
					win_col if ev == E_WINDOW else wall_col, WALL_PX)
	for ecy in range(y0, y1 + 1):                     # horizontal edges (north side of each cell)
		for ecx in range(x0, x1):
			var eh: int = _eh[ecy][ecx]
			if eh == E_WALL or eh == E_WINDOW:
				var ey := ecy * TILE
				draw_line(Vector2(ecx * TILE, ey), Vector2((ecx + 1) * TILE, ey),
					win_col if eh == E_WINDOW else wall_col, WALL_PX)

func _draw() -> void:
	var shake := Vector2(randf_range(-1, 1), randf_range(-1, 1)) * _shake
	_shake_off = shake
	draw_set_transform(shake, 0.0, Vector2.ONE)

	# --- the town grid: draw only the cells in view (cheap even for a huge world) ---
	# cull around the CAMERA center, not the player — near map edges the camera clamps
	# and stops centering on you, so player-centered culling leaves black gaps.
	var cam_c := _cam.get_screen_center_position() if _cam != null else _player
	var vh := Vector2(PLAY_W, PLAY_H) * (0.5 / CAM_ZOOM) + Vector2(TILE * 2.0, TILE * 2.0)
	var x0 := maxi(0, int((cam_c.x - vh.x) / TILE))
	var x1 := mini(GW, int((cam_c.x + vh.x) / TILE) + 1)
	var y0 := maxi(0, int((cam_c.y - vh.y) / TILE))
	var y1 := mini(GH, int((cam_c.y + vh.y) / TILE) + 1)
	for cy in range(y0, y1):
		var row := _cells[cy]
		for cx in range(x0, x1):
			var c := row[cx]
			var rr := Rect2(cx * TILE, cy * TILE, TILE, TILE)
			if c == C_TREE:
				var ctr := rr.position + Vector2(TILE * 0.5, TILE * 0.5)
				draw_circle(ctr, TILE * 1.5, Color(0.08, 0.13, 0.07))           # canopy (spans ~3 cells)
				draw_circle(ctr, TILE * 1.0, Color(0.12, 0.20, 0.10))           # lit crown
			else:
				draw_rect(rr, _cell_color(c))
	_draw_wall_edges(x0, x1, y0, y1)

	# searchable containers — a little chest; dims once you've searched it
	var vx0 := (x0 - 1) * TILE; var vx1 := (x1 + 1) * TILE
	var vy0 := (y0 - 1) * TILE; var vy1 := (y1 + 1) * TILE
	for c in _containers:
		var cp: Vector2 = c["pos"]
		if cp.x < vx0 or cp.x > vx1 or cp.y < vy0 or cp.y > vy1: continue
		var done: bool = c["searched"]
		var body := Color(0.20, 0.19, 0.18) if done else Color(0.44, 0.31, 0.17)
		var lid := Color(0.24, 0.23, 0.22) if done else Color(0.58, 0.42, 0.23)
		var r := Rect2(cp - Vector2(TILE * 0.42, TILE * 0.42), Vector2(TILE * 0.84, TILE * 0.84))
		draw_rect(r, body)
		draw_rect(Rect2(r.position, Vector2(r.size.x, TILE * 0.3)), lid)   # lid band
		draw_rect(r, Color(0, 0, 0, 0.5), false, 1.0)

	# workbenches — a table with a teal "you can craft here" accent
	for bp in _benches:
		if bp.x < vx0 or bp.x > vx1 or bp.y < vy0 or bp.y > vy1: continue
		var br := Rect2(bp - Vector2(TILE * 0.46, TILE * 0.34), Vector2(TILE * 0.92, TILE * 0.68))
		draw_rect(br, Color(0.30, 0.26, 0.22))
		draw_rect(br, Color(0.5, 0.45, 0.38), false, 1.0)
		draw_rect(Rect2(bp - Vector2(TILE * 0.16, TILE * 0.16), Vector2(TILE * 0.32, TILE * 0.32)), Color(0.35, 0.78, 0.72))

	# (scavenge-site labels ride on top of the roofs — drawn at the end of the world pass)

	# (loot now renders as Pickup nodes in _pickups_root)

	# ground hazards — caltrops / puddles, drawn low under the entities
	for gz in _zones:
		var zr: float = float(gz["radius"])
		var za: float = clampf(float(gz["life"]) / float(gz["life0"]), 0.0, 1.0)
		if String(gz["kind"]) == "puddle":
			var pc: Color = gz["color"]; pc.a = 0.28 * za
			draw_circle(gz["pos"], zr, pc)
			var rim: Color = gz["color"]; rim.a = 0.5 * za
			draw_arc(gz["pos"], zr, 0.0, TAU, 24, rim, 1.5)
		else:   # caltrops — a stable scatter of little spikes (phyllotaxis, no per-frame jitter)
			var cc := Color(0.78, 0.78, 0.82, 0.9 * za)
			for i in range(16):
				var ang := float(i) * 2.399963
				var rad := zr * sqrt(float(i) / 16.0)
				var pt: Vector2 = (gz["pos"] as Vector2) + Vector2(cos(ang), sin(ang)) * rad
				draw_line(pt - Vector2(3, 0), pt + Vector2(3, 0), cc, 1.5)
				draw_line(pt - Vector2(0, 3), pt + Vector2(0, 3), cc, 1.5)

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
			_blit(_tex_zombie, z["pos"], zrot, 22.0 * sc, tint)
		else:
			draw_circle(z["pos"], 8.0 * sc, Color(0.4, 0.65, 0.38))
		var f: float = clampf(z["hp"] / z["max_hp"], 0.0, 1.0)
		if f < 1.0:
			draw_rect(Rect2(z["pos"] + Vector2(-8, -14), Vector2(16.0 * f, 3)), Color(0.85, 0.3, 0.3))

	# traps
	for t in _traps:
		draw_rect(Rect2((t["pos"] as Vector2) - Vector2(8, 8), Vector2(16, 16)), Color(0.8, 0.5, 0.2))
		draw_arc(t["pos"], 18.0, 0.0, TAU, 24, Color(0.8, 0.5, 0.2, 0.25), 1.0)

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
		var pr: float = 2.5 if not p["homing"] else 3.5
		var tr: Array = p.get("trail", [])
		for i in range(tr.size()):
			var ta := (float(i) + 1.0) / float(tr.size() + 1)
			var tc: Color = p["color"]; tc.a = ta * 0.45
			draw_circle(tr[i], pr * ta * 0.85, tc)
		if p.get("return", false):
			_draw_boomerang(p["pos"], float(p.get("spin", 0.0)), p["color"], 1.0)
		else:
			draw_circle(p["pos"], pr, p["color"])

	# boomerangs resting on the floor (walk over to retrieve)
	for d in _dropped_boomerangs:
		draw_arc(d["pos"], 16.0, 0.0, TAU, 20, Color(0.6, 0.8, 1.0, 0.30), 1.5)
		_draw_boomerang(d["pos"], float(d.get("spin", 0.0)), Color(0.85, 0.9, 1.0), 0.9)

	# melee swing
	if not _melee_anim.is_empty():
		var ma: Vector2 = _melee_anim["aim"]
		var mc := Color(0.95, 0.95, 0.7, clampf(float(_melee_anim["life"]) * 6.0, 0.0, 1.0))
		draw_arc(_melee_anim["pos"], 30.0, ma.angle() - 0.6, ma.angle() + 0.6, 16, mc, 3.0)

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
		draw_circle(_muzzle["pos"], 4.0 * mf, Color(1.0, 0.95, 0.65, mf))

	# particles
	for pt in _particles:
		var c: Color = pt["col"]
		c.a = clampf(pt["life"] * 2.0, 0.0, 1.0)
		draw_rect(Rect2(pt["pos"] - Vector2(2, 2), Vector2(4, 4)), c)

	# player — survivor sprite, rotated to aim
	var ptint := Color(1, 1, 1)
	if _invuln > 0.0 and int(_invuln * 20.0) % 2 == 0: ptint = Color(1.6, 0.6, 0.6)
	if _tex_player != null:
		_blit(_tex_player, _player, _aim.angle(), 22.0, ptint)
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

	# roofs — hide each building's interior + any horde lurking inside until you step in.
	# The building you're standing in fades its roof away, revealing the room.
	for i in range(_buildings.size()):
		var ra: float = _roof_a[i]
		if ra <= 0.02: continue
		var rb: Rect2 = _buildings[i]
		var rc: Color = ROOF_COL[_btype[i]]; rc.a = ra
		draw_rect(rb, rc)
		var dk := Color(rc.r * 0.55, rc.g * 0.55, rc.b * 0.55, ra)   # ridge + eave shading
		if rb.size.x >= rb.size.y:                                   # gable ridge along the long axis
			draw_line(rb.position + Vector2(0, rb.size.y * 0.5), rb.position + Vector2(rb.size.x, rb.size.y * 0.5), dk, 2.0)
		else:
			draw_line(rb.position + Vector2(rb.size.x * 0.5, 0), rb.position + Vector2(rb.size.x * 0.5, rb.size.y), dk, 2.0)
		draw_rect(rb, dk, false, 1.5)
	# scavenge-site labels sit on top of the roofs so you can read a building from outside
	for s in _sites:
		var s_looted: bool = s["looted"]
		var lcol := Color(0.62, 0.67, 0.72) if not s_looted else Color(0.36, 0.36, 0.41)
		_text((s["rect"] as Rect2).position + Vector2(6, 18), s["label"], lcol, 12)

	# (full-screen overlays — hurt/danger/pause — now render on the HUD CanvasLayer in
	#  _draw_hud, so they cover the viewport regardless of where the camera is in the world)

func _hud_panel(ci: CanvasItem, r: Rect2, border: Color) -> void:
	ci.draw_rect(r, Color(0.04, 0.06, 0.07, 0.86))
	ci.draw_rect(r, Color(border.r, border.g, border.b, 0.45), false, 1.0)

func _text_on(ci: CanvasItem, pos: Vector2, s: String, col: Color, size: int) -> void:
	ci.draw_string(_font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

# drawn onto a dedicated HUD CanvasLayer node so CanvasModulate (world darkness) can't dim it
func _draw_hud(ci: CanvasItem) -> void:
	var accent := Color(0.35, 0.85, 0.78)
	var dim := Color(0.55, 0.62, 0.64)

	# full-screen overlays (screen space, so they cover the viewport at any camera pos)
	if _hurt_flash > 0.0:
		ci.draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0.8, 0.1, 0.1, _hurt_flash * 0.6))
	if _hp > 0.0 and _hp < PLAYER_MAX_HP * 0.3:
		var pulse := 0.12 + 0.10 * sin(Time.get_ticks_msec() * 0.008)
		ci.draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0.7, 0.05, 0.05, pulse))
	if _paused:
		ci.draw_rect(Rect2(0, 0, PLAY_W, PLAY_H), Color(0, 0, 0, 0.45))
		_text_on(ci, Vector2(PLAY_W * 0.5 - 90, PLAY_H * 0.5), "PAUSED  —  SPACE to resume", Color(1, 1, 1), 22)

	# --- top-left: mode badge + phase/wave status ---
	var mode_col := Color(0.95, 0.6, 0.3) if _debug else accent
	var lucid_col := Color(0.55, 0.6, 0.7) if _awakening < LUCID_UNIVERSAL else (Color(0.7, 0.8, 0.5) if _awakening < LUCID_JUNK else Color(0.6, 0.9, 1.0))
	_text_on(ci, Vector2(MARGIN + 6, MARGIN + 16), ("[ DEBUG ]" if _debug else "[ NORMAL ]") + "  F1", mode_col, 13)
	_text_on(ci, Vector2(MARGIN + 130, MARGIN + 16), "lucidity: %s" % _lucid_tier(), lucid_col, 13)
	var tod := _time_label()
	var tod_col := Color(0.55, 0.7, 0.95) if tod == "NIGHT" else (Color(0.95, 0.85, 0.55) if tod == "DAY" else Color(0.9, 0.65, 0.5))
	_text_on(ci, Vector2(MARGIN + 320, MARGIN + 16), "DAY %d · %s" % [_day_count, tod], tod_col, 13)
	var status := ""
	if _phase == Phase.GAME_OVER:
		status = "TERMINATED  /  day %d  /  press R" % _day_count
	else:
		var threat := "calm" if _night() < 0.25 else ("stirring" if _night() < 0.7 else "HUNTING")
		status = "%d nearby  ·  %s" % [_zombies.size(), threat]
	_text_on(ci, Vector2(MARGIN + 6, MARGIN + 44), status, Color(0.9, 0.94, 0.96), 24)
	_text_on(ci, Vector2(MARGIN + 6, MARGIN + 66), "E search   ·   TAB workbench   ·   R reload   ·   F light", dim, 12)

	# --- bottom-left console: equipped weapon + ammo + HP ---
	var bx := MARGIN + 12.0
	var top := PLAY_H - 96.0
	_hud_panel(ci, Rect2(bx - 8, top - 10, 320, 96), accent)
	if _equipped != null:
		_text_on(ci, Vector2(bx, top + 8), _equipped.display_name, accent, 16)
		var slot_txt := "WIELD" if _equipped_idx < 0 else "%d/%d" % [_equipped_idx + 1, _arsenal.size()]
		_text_on(ci, Vector2(bx + 250, top + 8), slot_txt, dim, 12)
		if _hand_hold:
			_text_on(ci, Vector2(bx, top + 28), "HELD — not a weapon", dim, 12)
		elif _equipped.uses_ammo:
			var cnt := _equipped.ammo_count()
			var ac := dim if cnt > 0 else Color(0.9, 0.4, 0.4)
			var s := "AMMO %d / %d" % [cnt, _equipped.ammo_max]
			var nm := _equipped.next_name()
			if nm != "" and nm != "Scrap": s += "   next: %s" % nm
			_text_on(ci, Vector2(bx, top + 28), s, ac, 12)
		else:
			_text_on(ci, Vector2(bx, top + 28), _equipped.category_name(), dim, 12)
	else:
		_text_on(ci, Vector2(bx, top + 8), "(nothing equipped)", dim, 15)
	# hp bar
	var hpw := 300.0
	var hpy := top + 44.0
	var hpf: float = clampf(_hp / PLAYER_MAX_HP, 0.0, 1.0)
	ci.draw_rect(Rect2(bx, hpy, hpw, 20), Color(0.14, 0.05, 0.06))
	ci.draw_rect(Rect2(bx, hpy, hpw * hpf, 20), Color(0.82, 0.28, 0.32))
	ci.draw_rect(Rect2(bx, hpy, hpw, 20), Color(accent.r, accent.g, accent.b, 0.4), false, 1.0)
	_text_on(ci, Vector2(bx + 8, hpy + 15), "HP  %d" % int(maxf(_hp, 0.0)), Color(1, 1, 1), 12)
	var badge := bx + hpw + 12.0
	if _shield > 0.0:
		_text_on(ci, Vector2(badge, hpy + 4), "SHLD %d" % int(_shield), Color(0.5, 0.8, 1.0), 12)
	if _speed_mult > 1.0:
		_text_on(ci, Vector2(badge, hpy + 20), "SPD x%.1f" % _speed_mult, Color(0.6, 0.95, 0.6), 12)

func _text(pos: Vector2, s: String, col: Color, size: int) -> void:
	draw_string(_font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

# =============================================================================
# UI (right panel: inventory -> pot -> combine -> equipped -> log)
# =============================================================================

func _toggle_build() -> void:
	if _build_layer == null:
		return
	_build_layer.visible = not _build_layer.visible
	_paused = _build_layer.visible   # opening the workbench pauses the game
	_lmb_edge = false
	if _build_layer.visible:
		_refresh_bench_locks()

# grey out bench actions that the current lucidity hasn't unlocked (the ladder made visible)
func _refresh_bench_locks() -> void:
	if _btn_attach == null:
		return
	var can_attach := _awakening >= LUCID_ATTACH
	var can_build := _awakening >= LUCID_BUILD and _at_bench   # T4 build is anchored to a workbench
	_btn_attach.disabled = not can_attach
	_btn_build.disabled = not can_build
	_btn_ai.disabled = not can_build
	_btn_attach.tooltip_text = "bolt the bench parts onto your equipped weapon" if can_attach else "🔒 locked — reach LUCID (T3) to attach parts"
	if _awakening < LUCID_BUILD:
		_btn_build.tooltip_text = "🔒 locked — reach AWAKE (T4) to build from scratch"
		_btn_ai.tooltip_text = "🔒 locked — reach AWAKE (T4) for AI builds"
	elif not _at_bench:
		_btn_build.tooltip_text = "🔧 stand at a workbench to build from scratch"
		_btn_ai.tooltip_text = "🔧 stand at a workbench for AI builds"
	else:
		_btn_build.tooltip_text = "assemble the bench parts into a NEW weapon/tool"
		_btn_ai.tooltip_text = "AI freeform build (needs combine/serve.py)"

func _make_ui_theme() -> Theme:
	var theme := Theme.new()
	theme.default_font = _font
	theme.default_font_size = 14
	var accent := Color(0.35, 0.85, 0.78)
	var accent_dim := Color(0.2, 0.42, 0.4)
	theme.set_stylebox("normal", "Button", _stylebox(Color(0.09, 0.11, 0.13), accent_dim))
	theme.set_stylebox("hover", "Button", _stylebox(Color(0.12, 0.2, 0.22), accent))
	theme.set_stylebox("pressed", "Button", _stylebox(Color(0.16, 0.32, 0.3), accent))
	theme.set_stylebox("focus", "Button", _stylebox(Color(0.12, 0.2, 0.22), accent))
	theme.set_color("font_color", "Button", Color(0.78, 0.88, 0.88))
	theme.set_color("font_hover_color", "Button", accent)
	theme.set_color("font_pressed_color", "Button", Color(0.95, 1.0, 1.0))
	theme.set_color("font_color", "Label", Color(0.72, 0.8, 0.82))
	theme.set_color("default_color", "RichTextLabel", Color(0.72, 0.8, 0.82))
	return theme

func _stylebox(fill: Color, border: Color) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = fill
	sb.border_color = border
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(2)
	sb.content_margin_left = 6
	sb.content_margin_right = 6
	sb.content_margin_top = 3
	sb.content_margin_bottom = 3
	return sb

func _build_ui() -> void:
	# the WORKBENCH: a full-screen overlay that pauses the game (toggle with TAB)
	_build_layer = CanvasLayer.new()
	_build_layer.layer = 3
	_build_layer.visible = false
	add_child(_build_layer)
	var dim := ColorRect.new()
	dim.color = Color(0.02, 0.03, 0.04, 0.85)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_build_layer.add_child(dim)
	var pw := 780.0
	var ph := 820.0
	var px := (PLAY_W - pw) * 0.5
	var py := (PLAY_H - ph) * 0.5
	var panelbg := ColorRect.new()
	panelbg.color = Color(0.05, 0.06, 0.08)
	panelbg.position = Vector2(px, py)
	panelbg.size = Vector2(pw, ph)
	_build_layer.add_child(panelbg)
	var seam := ColorRect.new()
	seam.color = Color(0.35, 0.85, 0.78, 0.55)
	seam.position = Vector2(px, py)
	seam.size = Vector2(pw, 2)
	_build_layer.add_child(seam)

	var root := VBoxContainer.new()
	root.position = Vector2(px + 18, py + 14)
	root.size = Vector2(pw - 36, ph - 28)
	root.add_theme_constant_override("separation", 6)
	root.theme = _make_ui_theme()
	_build_layer.add_child(root)

	_title(root, "WORKBENCH")
	_caption(root, "assemble junk into gear  ·  TAB to close")

	_caption(root, "EQUIPMENT")
	var handrow := HBoxContainer.new(); root.add_child(handrow)
	_hand_label = Label.new(); _hand_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	handrow.add_child(_hand_label)
	var hunb := Button.new(); hunb.text = " stow "; hunb.tooltip_text = "unequip — back to the starter weapon"
	hunb.pressed.connect(_unequip_hand); handrow.add_child(hunb)
	var armrow := HBoxContainer.new(); root.add_child(armrow)
	_armor_label = Label.new(); _armor_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	armrow.add_child(_armor_label)
	var aunb := Button.new(); aunb.text = " remove "; aunb.tooltip_text = "unequip armor"
	aunb.pressed.connect(_unequip_armor); armrow.add_child(aunb)

	_caption(root, "INVENTORY  (name → bench slot · EQUIP → wield it)")
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(0, 220)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	_grid = GridContainer.new()
	_grid.columns = 2
	_grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_grid)

	_caption(root, "BENCH  (click items above to fill the slots: delivery · damage · utility · modifier)")
	_pot_label = Label.new()
	_pot_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pot_label.text = "(empty)"
	root.add_child(_pot_label)
	# primitive build — deterministic, you choose the parts
	var row := HBoxContainer.new()
	root.add_child(row)
	_btn_build = Button.new(); _btn_build.text = "  BUILD  "; _btn_build.tooltip_text = "assemble the bench parts into a NEW weapon/tool (deterministic)"; _btn_build.pressed.connect(_on_combine); row.add_child(_btn_build)
	_btn_attach = Button.new(); _btn_attach.text = "  ATTACH  "; _btn_attach.tooltip_text = "bolt the bench parts onto your EQUIPPED weapon (uses attachment slots)"; _btn_attach.pressed.connect(_on_modify); row.add_child(_btn_attach)
	var lb := Button.new(); lb.text = "  LOAD  "; lb.tooltip_text = "load the bench parts into the equipped weapon as AMMO"; lb.pressed.connect(_on_load); row.add_child(lb)
	var cl := Button.new(); cl.text = " Clear "; cl.pressed.connect(_on_clear); row.add_child(cl)
	# advanced — the AI brain (Tier-4 freeform)
	_caption(root, "ADVANCED  (freeform build — needs a WORKBENCH + the combine server)")
	var airow := HBoxContainer.new()
	root.add_child(airow)
	_btn_ai = Button.new(); _btn_ai.text = "  AI BUILD  "; _btn_ai.tooltip_text = "let the AI brain compose something wild from the bench parts (Tier-4; needs combine/serve.py)"; _btn_ai.pressed.connect(_on_ai_build); airow.add_child(_btn_ai)
	_refresh_bench_locks()

	_http = HTTPRequest.new()
	add_child(_http)
	_http.request_completed.connect(_on_ai_response)

	_caption(root, "ARSENAL  (1-9 / wheel to switch)")
	var ascroll := ScrollContainer.new()
	ascroll.custom_minimum_size = Vector2(0, 90)
	root.add_child(ascroll)
	_arsenal_box = VBoxContainer.new()
	_arsenal_box.add_theme_constant_override("separation", 2)
	_arsenal_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ascroll.add_child(_arsenal_box)

	_caption(root, "EQUIPPED")
	_equipped_label = RichTextLabel.new()
	_equipped_label.bbcode_enabled = true
	_equipped_label.fit_content = true
	_equipped_label.custom_minimum_size = Vector2(0, 58)
	root.add_child(_equipped_label)

	_caption(root, "LOG")
	_log_label = RichTextLabel.new()
	_log_label.bbcode_enabled = true
	_log_label.scroll_following = true
	_log_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_log_label.custom_minimum_size = Vector2(0, 70)
	root.add_child(_log_label)

func _title(parent: Node, s: String) -> void:
	var l := Label.new(); l.text = s
	l.add_theme_font_size_override("font_size", 20)
	parent.add_child(l)

func _caption(parent: Node, s: String) -> void:
	var l := Label.new(); l.text = s
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(PANEL_W - 28, 0)
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
		var cell := HBoxContainer.new()
		cell.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var b := Button.new()
		b.text = "%s x%d" % [it.display_name, count]
		b.tooltip_text = "tags: %s" % ", ".join(it.tags)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		b.clip_text = true
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.add_theme_font_size_override("font_size", 12)
		var tex := _item_icon(id)
		if tex != null:
			b.icon = tex
			b.expand_icon = true
			b.add_theme_color_override("icon_normal_color", it.color)   # tint the white glyph
			b.add_theme_color_override("icon_hover_color", Color(1, 1, 1))
			b.custom_minimum_size = Vector2(0, 40)
		b.pressed.connect(_on_item_pressed.bind(id))
		cell.add_child(b)
		var eq := Button.new()
		eq.text = _preview_role(id)   # WEAPON / THROW / HELD / ARMOR
		eq.tooltip_text = "wield %s in the HAND slot" % it.display_name
		eq.add_theme_font_size_override("font_size", 11)
		eq.pressed.connect(_wield_item.bind(id))
		cell.add_child(eq)
		_grid.add_child(cell)
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
	if _awakening < LUCID_BUILD:
		_log("The deeper builds are still beyond you — not lucid enough."); return
	if not _at_bench:
		_log("You need a workbench for that. Find one out in the world."); return
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
	var ps: Variant = d.get("params", {})   # per-delivery behavior tuning (e.g. boomerang arc)
	if typeof(ps) == TYPE_DICTIONARY:
		for k in ps:
			g.params[String(k)] = float(ps[k])
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
		"CALTROPS": return Gadget.Delivery.CALTROPS
		"PUDDLE": return Gadget.Delivery.PUDDLE
		_: return Gadget.Delivery.PROJECTILE

# mirrors Resolver._finalize: fire mode + ammo capacity from delivery/power
func _finalize_ai_gadget(g: Gadget) -> void:
	g.semi = true
	if g.delivery == Gadget.Delivery.MELEE or g.delivery == Gadget.Delivery.BEAM:
		g.semi = false
	g.uses_ammo = g.delivery in [Gadget.Delivery.PROJECTILE, Gadget.Delivery.LOBBED,
		Gadget.Delivery.PLACED, Gadget.Delivery.CONE, Gadget.Delivery.SELF,
		Gadget.Delivery.TURRET, Gadget.Delivery.DECOY, Gadget.Delivery.RETURN,
		Gadget.Delivery.CALTROPS, Gadget.Delivery.PUDDLE]
	if g.uses_ammo:
		var pwr: float = maxf(g.amount_of(Gadget.DAMAGE), g.amount_of(Gadget.EXPLODE))
		pwr = maxf(pwr, 4.0)
		match g.delivery:
			Gadget.Delivery.RETURN:
				g.ammo_max = 1
			Gadget.Delivery.SELF, Gadget.Delivery.TURRET, Gadget.Delivery.DECOY:
				g.ammo_max = 3
			Gadget.Delivery.LOBBED, Gadget.Delivery.PLACED, Gadget.Delivery.CALTROPS, Gadget.Delivery.PUDDLE:
				g.ammo_max = clampi(int(round(60.0 / pwr)), 3, 8)
			_:
				g.ammo_max = clampi(int(round(90.0 / pwr)), 6, 30)
				if not g.semi: g.ammo_max = int(g.ammo_max * 1.5)
		g.fill_plain()

func _on_combine() -> void:
	if _awakening < LUCID_BUILD:
		_log("You can't picture building something new yet — you're not lucid enough."); return
	if not _at_bench:
		_log("You need a workbench to build from scratch. Find one out in the world."); return
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

# ATTACH the bench parts onto the equipped weapon — limited by its attachment slots.
func _on_modify() -> void:
	if _equipped == null:
		_log("Nothing equipped to attach to."); return
	if _equipped_idx < 0:
		_log("You're wielding a raw item — equip a built weapon to attach parts to it."); return
	if _awakening < LUCID_ATTACH:
		_log("You can't make parts stick yet — you're not lucid enough."); return
	if _pot.is_empty():
		_log("Put parts on the bench to attach."); return
	var free := _equipped.max_attach - _equipped.attached.size()
	if _pot.size() > free:
		_log("Not enough attachment slots — %s has %d/%d used. Remove a part or use fewer." % [_equipped.display_name, _equipped.attached.size(), _equipped.max_attach]); return
	var names: Array[String] = []
	var items: Array[Item] = []
	for id in _pot:
		items.append(_db[id]); names.append(_db[id].display_name)
	var old_name := _equipped.display_name
	var result := Resolver.combine(items, _equipped)
	result.attached.append_array(names)   # record what's bolted on (base attachments carried by resolver)
	if result.uses_ammo and _equipped.uses_ammo:
		result.mag = _equipped.mag.duplicate(true)  # carry the loaded magazine over
		while result.ammo_count() > result.ammo_max and not result.mag.is_empty():
			result.mag[0]["count"] = int(result.mag[0]["count"]) - 1
			if int(result.mag[0]["count"]) <= 0: result.mag.pop_front()
	_consume_pot()
	_arsenal[_equipped_idx] = result   # replace in place
	_equipped = result
	_log("Attached %s to [b]%s[/b] -> [b]%s[/b]  (%d/%d slots)" % [" + ".join(names), old_name, result.display_name, result.attached.size(), result.max_attach])
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
		_log("Put ammo or junk on the bench to load."); return
	# lucidity gate — same ladder as field reload: native ammo always; other ammo at
	# T1 (universal); junk at T2 (junk-as-ammo). LOAD must not bypass what R enforces.
	for id in _pot:
		var pit: Item = _db[id]
		if id == _equipped.native_ammo:
			continue
		if pit.category == Item.AMMO:
			if _awakening < LUCID_UNIVERSAL:
				_log("Only its own ammo fits this gun right now — you're not lucid enough for other rounds."); return
		elif _awakening < LUCID_JUNK:
			_log("Junk won't chamber yet — you're not lucid enough."); return
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

# --- field RELOAD (R) — the lucidity ladder, T1 (universal ammo) + T2 (junk-as-ammo) ---

func _lucid_tier() -> String:
	if _awakening >= LUCID_BUILD: return "AWAKE"
	if _awakening >= LUCID_ATTACH: return "LUCID"
	if _awakening >= LUCID_JUNK: return "WAKING"
	if _awakening >= LUCID_UNIVERSAL: return "STIRRING"
	return "ASLEEP"

func _reload() -> void:
	if _equipped == null or not _equipped.uses_ammo:
		_log("Nothing here takes ammo."); return
	if _equipped.ammo_count() >= _equipped.ammo_max:
		_log("%s is already full." % _equipped.display_name); return
	var id := _pick_reload_item()
	if id == "":
		_log(_reload_fail_msg()); return
	var it: Item = _db[id]
	var prof := Resolver.ammo_profile([it])
	var loaded := _equipped.load_rounds(prof["name"], prof, prof["color"], _ammo_value(it))
	if loaded <= 0:
		_log("%s is already full." % _equipped.display_name); return
	_inv[id] = int(_inv[id]) - 1
	if _inv[id] <= 0: _inv.erase(id)
	var flavor := ""
	if it.category == Item.JUNK: flavor = "  — you jam it in. It fits. It shouldn't."
	elif _equipped.native_ammo != "" and id != _equipped.native_ammo: flavor = "  — wrong caliber. Doesn't matter anymore."
	_log("Reloaded [b]%s[/b] with %s (+%d → %d/%d)%s" % [_equipped.display_name, it.display_name, loaded, _equipped.ammo_count(), _equipped.ammo_max, flavor])
	_refresh_inventory_ui()

## Pick what to load, gated by lucidity. Native ammo always preferred when present.
func _pick_reload_item() -> String:
	var native := _equipped.native_ammo
	if native != "" and int(_inv.get(native, 0)) > 0:
		return native
	if _awakening < LUCID_UNIVERSAL:
		return ""   # ASLEEP: only the gun's own ammo works
	var ammo: Array[String] = []
	var junk: Array[String] = []
	for id in _inv:
		if int(_inv[id]) <= 0:
			continue
		var cat := (_db[id] as Item).category
		if cat == Item.AMMO: ammo.append(id)
		elif cat == Item.JUNK: junk.append(id)
	if not ammo.is_empty():
		return ammo[0]                                   # T1: any ammo fits any gun
	if _awakening >= LUCID_JUNK and not junk.is_empty():
		return junk[0]                                   # T2: junk-as-ammo
	return ""

func _reload_fail_msg() -> String:
	var native := _equipped.native_ammo if _equipped != null else ""
	var nm: String = (_db[native] as Item).display_name if native != "" and _db.has(native) else "ammo"
	if _awakening < LUCID_UNIVERSAL:
		return "Out of %s. (Other things might fit… if you were thinking clearly.)" % nm
	if _awakening < LUCID_JUNK:
		return "No ammo left. (Junk won't chamber… yet.)"
	return "Nothing left to load — not even junk."

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
		b.clip_text = true
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.pressed.connect(_equip.bind(i))
		_arsenal_box.add_child(b)

func _refresh_equipped() -> void:
	if _equipped == null:
		_equipped_label.text = "(nothing)"; return
	var att := ""
	if _equipped.uses_ammo or not _equipped.attached.is_empty():
		att = "\n[color=#678]attachments %d/%d%s[/color]" % [_equipped.attached.size(), _equipped.max_attach,
			("  ·  " + ", ".join(_equipped.attached)) if not _equipped.attached.is_empty() else ""]
	_equipped_label.text = "[b]%s[/b]  [%s]\n[color=#9aa]%s[/color]\n[color=#778]%s[/color]%s" % [
		_equipped.display_name, _equipped.category_name(), _equipped.description, _equipped.summary(), att]

func _refresh_equipment() -> void:
	if _hand_label != null:
		if _equipped == null:
			_hand_label.text = "HAND:  (empty)"
		elif _hand_item != null:
			_hand_label.text = "HAND:  %s  [%s]" % [_hand_item.display_name, _archetype_label(_hand_item.archetype)]
		else:
			_hand_label.text = "HAND:  %s  [%s]" % [_equipped.display_name, _equipped.category_name()]
	if _armor_label != null:
		_armor_label.text = "ARMOR: %s" % (_armor.display_name if _armor != null else "(empty)")

## Short role label for the inventory EQUIP button — the item's standalone archetype.
func _preview_role(id: String) -> String:
	var it: Item = _db[id]
	if it.is_armor(): return "ARMOR"
	if it.category == Item.AMMO: return "AMMO"
	return _archetype_label(it.archetype)

func _log(s: String) -> void:
	_log_lines.append(s)
	if _log_lines.size() > 40: _log_lines.pop_front()
	if _log_label != null:
		_log_label.text = "\n".join(_log_lines)
