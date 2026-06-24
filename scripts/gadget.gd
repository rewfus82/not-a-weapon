class_name Gadget
extends RefCounted

## The resolved output of a combine: a DELIVERY (how it's applied) + a list of
## EFFECT primitives (what it does). The engine reads both, so components compose
## into mechanically distinct weapons instead of recolored projectiles.

enum Delivery { PROJECTILE, MELEE, LOBBED, AURA, PLACED }

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

var display_name := "Nothing"
var description := ""
var delivery: Delivery = Delivery.PROJECTILE
var effects: Array[Dictionary] = []   # each {kind, amount, duration, radius, count}
var projectile_speed := 700.0
var homing := false
var semi := true        # true = one shot per click; false = acts while held (auto / chainsaw grind)
var harmless := false
var color := Color(0.7, 0.7, 0.7)

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
		_: return "RANGED"

func category_name() -> String:
	# a short label for the HUD / arsenal, derived from what it does
	if effects.is_empty(): return "DUD"
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
