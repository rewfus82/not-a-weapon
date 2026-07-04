class_name Gadget
extends RefCounted

## The resolved output of a combine: a DELIVERY (how it's applied) + a list of
## EFFECT primitives (what it does). The engine reads both, so components compose
## into mechanically distinct weapons instead of recolored projectiles.

enum Delivery { PROJECTILE, MELEE, LOBBED, AURA, PLACED, CONE, BEAM, RETURN, SELF, TURRET, DECOY, CALTROPS, PUDDLE }

# Implemented effect kinds (a subset of the harness vocabulary — keep this in
# sync with what main.gd can actually execute: the engine capability contract).
const DAMAGE := "damage"
const SLOW := "slow"         # duration secs; amount = strength 0-100
const SNARE := "snare"       # duration secs (rooted)
const KNOCKBACK := "knockback"  # amount = force
const EXPLODE := "explode"   # radius; amount = splash damage
const BURN := "burn"         # duration; amount = damage/sec
const PIERCE := "pierce"     # count = extra targets a shot passes through
const SPAWN := "spawn"       # count = homing sub-projectiles
const COLLECT := "collect"   # radius = loot-vacuum range (AURA)
const FREEZE := "freeze"     # duration secs (near-stop; frozen enemies take bonus damage)
const CHAIN := "chain"       # count = jumps, amount = jump damage, radius = jump range
const HEAL := "heal"         # amount = HP restored to the player (SELF)
const SHIELD := "shield"     # amount = damage-absorbing shield given to the player (SELF)
const SPEED := "speed_buff"  # amount = move-speed multiplier, duration secs (SELF)

var display_name := "Nothing"
var description := ""
var delivery: Delivery = Delivery.PROJECTILE
var effects: Array[Dictionary] = []   # each {kind, amount, duration, radius, count}
var projectile_speed := 700.0
var homing := false
var semi := true        # true = one shot per click; false = acts while held (auto / chainsaw grind)
var uses_ammo := false  # ranged/lobbed/placed consume ammo; melee/aura don't
var ammo_max := 0
var mag: Array[Dictionary] = []  # magazine: stack of {name, profile, color, count}; fires the top (last loaded) first
var harmless := false
var color := Color(0.7, 0.7, 0.7)
var native_ammo := ""   # the ammo id this gun "wants" (asleep, only this loads; lucid, anything fits)
var max_attach := 2               # how many parts can be bolted on at the bench (ATTACH)
var attached: Array[String] = []  # names of the parts currently attached (limited by max_attach)
# per-DELIVERY behavior tuning the engine reads (distinct from payload effects). Any
# resolver (wield/combine/AI) may set these; the engine falls back to its defaults.
# Boomerang (RETURN) is the worked example: {range, curve, return_speed}. See DESIGN.md §10.
var params: Dictionary = {}

func add(kind: String, amount := 0.0, duration := 0.0, radius := 0.0, count := 0) -> void:
	effects.append({"kind": kind, "amount": amount, "duration": duration, "radius": radius, "count": count})

func get_effect(kind: String) -> Dictionary:
	for e in effects:
		if e["kind"] == kind:
			return e          # dictionaries are by-reference, so callers can mutate it
	return {}

func has(kind: String) -> bool:
	return not get_effect(kind).is_empty()

func amount_of(kind: String) -> float:
	var e := get_effect(kind)
	return float(e["amount"]) if not e.is_empty() else 0.0

func delivery_name() -> String:
	match delivery:
		Delivery.MELEE: return "MELEE"
		Delivery.LOBBED: return "LOBBED"
		Delivery.AURA: return "AURA"
		Delivery.PLACED: return "TRAP"
		Delivery.CONE: return "SPRAY"
		Delivery.BEAM: return "BEAM"
		Delivery.RETURN: return "BOOMERANG"
		Delivery.SELF: return "SELF"
		Delivery.TURRET: return "TURRET"
		Delivery.DECOY: return "DECOY"
		Delivery.CALTROPS: return "CALTROPS"
		Delivery.PUDDLE: return "PUDDLE"
		_: return "RANGED"

func category_name() -> String:
	# a short label for the HUD / arsenal, derived from what it does
	if delivery == Delivery.TURRET: return "TURRET"
	if delivery == Delivery.DECOY: return "DECOY"
	if effects.is_empty(): return "DUD"
	if has(HEAL) or has(SHIELD) or has(SPEED): return "SUPPORT"
	if harmless: return "TRINKET"
	if (has(SNARE) or has(SLOW)) and not has(DAMAGE) and not has(EXPLODE): return "CONTROL"
	if has(COLLECT) and not has(DAMAGE): return "UTILITY"
	return delivery_name()

func summary() -> String:
	var parts: Array[String] = []
	for e in effects:
		var s: String = e["kind"]
		if e["amount"]: s += " %d" % int(e["amount"])
		if e["count"]: s += " x%d" % int(e["count"])
		parts.append(s)
	if parts.is_empty(): return "nothing"
	return ", ".join(parts)

# --- magazine (mixed ammo) ---------------------------------------------------

func ammo_count() -> int:
	var n := 0
	for s in mag: n += int(s["count"])
	return n

func next_name() -> String:
	if mag.is_empty(): return ""
	return String(mag[mag.size() - 1]["name"])

## Consume one round from the top of the magazine; returns its behavior profile
## ({} = plain). Last loaded fires first.
func next_round() -> Dictionary:
	while not mag.is_empty() and int(mag[mag.size() - 1]["count"]) <= 0:
		mag.pop_back()
	if mag.is_empty(): return {}
	var top: Dictionary = mag[mag.size() - 1]
	top["count"] = int(top["count"]) - 1
	var prof: Dictionary = top["profile"]
	if int(top["count"]) <= 0: mag.pop_back()
	return prof

## Load `count` rounds of a type onto the top of the magazine (capped at ammo_max).
func load_rounds(nm: String, profile: Dictionary, col: Color, count: int) -> int:
	var n := mini(count, ammo_max - ammo_count())
	if n <= 0: return 0
	mag.append({"name": nm, "profile": profile, "color": col, "count": n})
	return n

func fill_plain() -> void:
	mag = [{"name": "Scrap", "profile": {}, "color": color, "count": ammo_max}]
