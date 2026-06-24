class_name Resolver
extends RefCounted

## Turns a set of items into a Gadget (effect profile).
##
## Two layers:
##   1. SPECIALS  - hand-authored combos (the jokes + story-critical weapons).
##                  Looked up first so designed moments always land.
##   2. compose() - the generic composition engine. Reads slots/tags so ANY
##                  combination still responds. This is what keeps "combine
##                  anything" honest and lets players invent things we never
##                  authored.
##
## Tier gates which slots the simulation lets you edit — the matrix loosening:
##   Tier 1: you may only swap a PAYLOAD into a real gun (gun_frame required).
##   Tier 2: you may also bolt on BEHAVIOR modifiers (gun_frame still required).
##   Tier 3: free-form. No gun frame needed. Anything goes.

## Authored combos. Key = sorted item ids joined by ",". `min_tier` is the point
## in the reality-shatter where the simulation will allow it.
const SPECIALS := {
	"anchovies,m16": {
		"name": "Anchovy Rifle", "cat": "DAMAGE", "min_tier": 1,
		"damage": 12.0, "speed": 720.0,
		"desc": "You chambered a can of anchovies. It fires. It reeks. The simulation flinched — and you noticed.",
		"color": [0.55, 0.40, 0.25],
	},
	"m16,pringles": {
		"name": "Scoped M16", "cat": "DAMAGE", "min_tier": 2,
		"damage": 16.0, "speed": 1000.0,
		"desc": "A Pringles can makes a serviceable scope. Tighter, faster shots. (Tier 2: you're modifying the weapon now, not just feeding it.)",
		"color": [0.50, 0.50, 0.55],
	},
	"m16,potato": {
		"name": "Suppressed M16", "cat": "DAMAGE", "min_tier": 2,
		"damage": 14.0, "speed": 720.0,
		"desc": "A potato suppressor. Quieter. Somewhere, a guard you imagined relaxes.",
		"color": [0.50, 0.50, 0.55],
	},
	"feathers,ketchup,spatula": {
		"name": "Gunk Lobber", "cat": "CONTROL", "min_tier": 2, "control": "slow",
		"damage": 0.0, "speed": 440.0, "harmless": true,
		"desc": "Lobs a feathered ketchup glob. It will not hurt anyone. They will, however, slow way down to process what just happened.",
		"color": [0.80, 0.30, 0.25],
	},
	"beehive,grenade,magnet": {
		"name": "Swarm Mine", "cat": "DAMAGE", "min_tier": 3,
		"damage": 18.0, "speed": 360.0, "aoe": 120.0, "homing": true,
		"desc": "Magnetized explosive bees seek the nearest metal. Reality did not sign off on this.",
		"color": [0.85, 0.70, 0.25],
	},
	"bear_trap,boomerang,fishing_rod": {
		"name": "Retriever", "cat": "CONTROL", "min_tier": 3, "control": "snare",
		"damage": 8.0, "speed": 680.0,
		"desc": "Casts a snare. Misses come back; hits drag the victim to you. The simulation is openly improvising now.",
		"color": [0.55, 0.60, 0.45],
	},
	"backpack,chainsaw,vacuum": {
		"name": "Harvester", "cat": "UTILITY", "min_tier": 3, "auto_collect": true,
		"desc": "Passively vacuums up loot in a wide radius. Your ARPG brain feels a deep, calm joy.",
		"color": [0.30, 0.55, 0.80],
	},
	"co2_canister,nerf_gun,spaghetti": {
		"name": "Meatball Launcher", "cat": "DAMAGE", "min_tier": 3, "control": "slow",
		"damage": 10.0, "speed": 820.0, "aoe": 70.0,
		"desc": "Pressurized spaghetti rounds. Sticky, fast, and deeply upsetting to everyone involved.",
		"color": [0.90, 0.75, 0.30],
	},
}

## Main entry. `items` is an Array[Item]; returns a Gadget.
static func combine(items: Array, tier: int) -> Gadget:
	if items.is_empty():
		var g := Gadget.new()
		g.description = "Nothing selected. Drop some junk in the pot."
		return g

	# Layer 1: authored specials win, if the tier allows them yet.
	var key := _key(items)
	if SPECIALS.has(key):
		var spec: Dictionary = SPECIALS[key]
		if tier < int(spec["min_tier"]):
			return _locked(int(spec["min_tier"]))
		return _from_special(spec)

	# Layer 2: generic composition.
	return _compose(items, tier)

# --- helpers -----------------------------------------------------------------

static func _key(items: Array) -> String:
	var ids: Array[String] = []
	for it in items:
		ids.append(it.id)
	ids.sort()
	return ",".join(ids)

static func _any_tag(items: Array, tag: String) -> bool:
	for it in items:
		if it.has_tag(tag):
			return true
	return false

static func _any_slot(items: Array, slot: String) -> bool:
	for it in items:
		if it.has_slot(slot):
			return true
	return false

static func _first_payload(items: Array) -> Item:
	for it in items:
		if it.has_slot(Item.SLOT_PAYLOAD):
			return it
	return items[0]

static func _locked(min_tier: int) -> Gadget:
	var g := Gadget.new()
	g.display_name = "Reality Refuses"
	g.description = "The simulation won't allow that yet. It would take a looser grip on reality. (Needs Tier %d.)" % min_tier
	g.color = Color(0.5, 0.2, 0.2)
	return g

static func _from_special(spec: Dictionary) -> Gadget:
	var g := Gadget.new()
	g.display_name = spec["name"]
	g.description = spec["desc"]
	g.category = _cat_from_string(spec.get("cat", "DUD"))
	g.damage = float(spec.get("damage", 0.0))
	g.control = spec.get("control", "none")
	g.projectile_speed = float(spec.get("speed", 600.0))
	g.homing = bool(spec.get("homing", false))
	g.aoe = float(spec.get("aoe", 0.0))
	g.auto_collect = bool(spec.get("auto_collect", false))
	g.harmless = bool(spec.get("harmless", false))
	var c = spec.get("color", [0.6, 0.6, 0.6])
	g.color = Color(c[0], c[1], c[2])
	return g

static func _cat_from_string(s: String) -> Gadget.Category:
	match s:
		"DAMAGE": return Gadget.Category.DAMAGE
		"CONTROL": return Gadget.Category.CONTROL
		"MOBILITY": return Gadget.Category.MOBILITY
		"UTILITY": return Gadget.Category.UTILITY
		"CONSUMABLE": return Gadget.Category.CONSUMABLE
		_: return Gadget.Category.DUD

## The generic composition engine: no authored recipe, so read the parts.
static func _compose(items: Array, tier: int) -> Gadget:
	var has_frame := _any_tag(items, "gun_frame")

	# Tier gating = the matrix deciding which slots you may edit.
	if tier <= 2 and not has_frame:
		var blocked := Gadget.new()
		blocked.display_name = "Reality Still Has Rules"
		if tier == 1:
			blocked.description = "Tier 1: you can only feed a payload into a real weapon. Add a gun to the pot."
		else:
			blocked.description = "Tier 2: you can modify real weapons, but not yet build one from scratch. Add a gun frame."
		blocked.color = Color(0.45, 0.25, 0.25)
		return blocked

	var lethal := _any_tag(items, "lethal")
	var explosive := _any_tag(items, "explosive")
	var sticky := _any_tag(items, "sticky")
	var snare := _any_tag(items, "snare")
	var suction := _any_tag(items, "suction") or _any_tag(items, "storage")
	var pressure := _any_tag(items, "pressure")
	var attract := _any_tag(items, "attract")
	var has_delivery := _any_slot(items, Item.SLOT_DELIVERY)

	var g := Gadget.new()
	g.color = _first_payload(items).color
	g.homing = attract

	# Resolve the dominant effect. Order matters: most "intentful" wins.
	if suction and not lethal:
		g.category = Gadget.Category.UTILITY
		g.auto_collect = true
		g.display_name = _name(items, "Harvester")
		g.description = "It passively pulls loot in. Not a weapon — a quality-of-life heresy."
	elif snare:
		g.category = Gadget.Category.CONTROL
		g.control = "snare"
		g.damage = 6.0
		g.display_name = _name(items, "Snare Rig")
		g.description = "Whatever it hits, it pins in place. Briefly."
	elif explosive:
		g.category = Gadget.Category.DAMAGE
		g.damage = 22.0
		g.aoe = 110.0
		g.display_name = _name(items, "Boom Device")
		g.description = "It goes bang in a radius. The radius is the point."
	elif lethal:
		g.category = Gadget.Category.DAMAGE
		g.damage = 14.0
		g.display_name = _name(items, "Improvised Weapon")
		g.description = "It is, regrettably for someone, an actual weapon."
	elif sticky:
		g.category = Gadget.Category.CONTROL
		g.control = "slow"
		g.harmless = true
		g.display_name = _name(items, "Gunk Sprayer")
		g.description = "Harmless, but sticky. Things bog down in it."
	elif has_delivery:
		# It launches something, but nothing dangerous. The pixie-stix crossbow.
		g.category = Gadget.Category.DAMAGE
		g.damage = 3.0
		g.harmless = true
		g.display_name = _name(items, "Contraption")
		g.description = "It fires! It is also completely harmless. Genuinely impressive, in a sad way."
	else:
		# No delivery, no effect. A dud — but an acknowledged one.
		g.category = Gadget.Category.DUD
		g.display_name = _name(items, "Whatsit")
		g.description = "You made... a thing. It does nothing. The simulation has no rule for it — which is itself a clue."
		return g

	# Modifiers stack on top of whatever resolved.
	g.projectile_speed = 600.0
	if pressure:
		g.projectile_speed *= 1.4
		g.damage += 6.0
	if _any_tag(items, "salty") or _any_tag(items, "organic"):
		g.damage += 2.0
	return g

## Build a deadpan generated name from the ingredients + an archetype word.
static func _name(items: Array, archetype: String) -> String:
	var payload := _first_payload(items)
	var word := payload.display_name
	# Trim a leading article-y prefix for snappier names.
	for prefix in ["Can of ", "Handful of ", "Plate of ", "Bottle of "]:
		if word.begins_with(prefix):
			word = word.substr(prefix.length())
			break
	return "%s %s" % [word, archetype]
