class_name Resolver
extends RefCounted

## Deterministic, component-driven, DATA-TABLE-DRIVEN. Items carry the meaning;
## the tables below map their tags to a DELIVERY + composed EFFECTS + AMMO behavior.
## Adding content = editing a table row (and the AI can emit table rows later).
##
##   _delivery_rules()  tag -> delivery (first match wins)
##   _tag_effects()     tag -> [effect ops] for weapon composition
##   _tag_ammo()        tag -> ammo-profile deltas (how a loaded round alters the shot)
##   _specials()        sorted-item-id key -> a curated, named "joke" gadget override
##
## Pass `base` to MODIFY an existing weapon (junk augments it) instead of building new.
## SPECIALS only fire on a fresh build (base == null), and only on an exact combo.

# =============================================================================
# ENTRY
# =============================================================================

static func combine(items: Array, base: Gadget = null) -> Gadget:
	if items.is_empty():
		var d := Gadget.new()
		d.description = "Nothing on the bench."
		return d

	var tags := _tagset(items)
	var g: Gadget = null
	if base == null:
		var sp := _specials()
		var key := _key(items)
		if sp.has(key):
			g = _build_special(sp[key], items)
	if g == null:
		g = _build_generic(items, base, tags)

	_finalize(g, tags)   # fire mode + ammo capacity (depends on delivery/damage)
	return g

# =============================================================================
# DATA TABLES  (edit these to add content)
# =============================================================================

## Tag -> delivery. First matching tag (in order) wins.
static func _delivery_rules() -> Array:
	return [
		["gun_frame", Gadget.Delivery.PROJECTILE],
		["ranged",    Gadget.Delivery.PROJECTILE],
		["explosive", Gadget.Delivery.LOBBED],
		["thrown",    Gadget.Delivery.LOBBED],
		["kinetic",   Gadget.Delivery.MELEE],
		["flat",      Gadget.Delivery.MELEE],
		["snare",     Gadget.Delivery.PLACED],
		["suction",   Gadget.Delivery.AURA],
		["storage",   Gadget.Delivery.AURA],
	]

## Tag -> list of effect ops applied during weapon composition.
## Op kinds: {"op":"boost", kind, amount}            add to (or create) an effect's amount
##           {"op":"ensure", kind, amount,dur,radius,count}  add the effect if absent
##           {"op":"homing"}                          set the homing flag
##           {"op":"pierce", count}                   ensure pierce (count), else +1
##           {"op":"speed", mult}                     multiply projectile speed (cap 1200)
static func _tag_effects() -> Dictionary:
	return {
		"lethal":    [{"op": "boost", "kind": Gadget.DAMAGE, "amount": 12.0}],
		"kinetic":   [{"op": "boost", "kind": Gadget.DAMAGE, "amount": 8.0}],
		"explosive": [{"op": "ensure", "kind": Gadget.EXPLODE, "amount": 16.0, "radius": 90.0},
					  {"op": "boost", "kind": Gadget.DAMAGE, "amount": 4.0}],
		"sticky":    [{"op": "ensure", "kind": Gadget.SLOW, "amount": 55.0, "duration": 3.0}],
		"snare":     [{"op": "ensure", "kind": Gadget.SNARE, "duration": 2.2}],
		"electric":  [{"op": "ensure", "kind": Gadget.BURN, "amount": 4.0, "duration": 3.0}],
		"swarm":     [{"op": "ensure", "kind": Gadget.SPAWN, "count": 4}, {"op": "homing"}],
		"attract":   [{"op": "homing"}],
		"tube":      [{"op": "pierce", "count": 2}],
		"pressure":  [{"op": "speed", "mult": 1.4}, {"op": "boost", "kind": Gadget.DAMAGE, "amount": 3.0}],
		"sharp":     [{"op": "pierce", "count": 2}, {"op": "boost", "kind": Gadget.DAMAGE, "amount": 4.0}],
		"blunt":     [{"op": "ensure", "kind": Gadget.KNOCKBACK, "amount": 240.0}, {"op": "boost", "kind": Gadget.DAMAGE, "amount": 4.0}],
		"flammable": [{"op": "ensure", "kind": Gadget.BURN, "amount": 5.0, "duration": 3.0}],
		"caustic":   [{"op": "ensure", "kind": Gadget.BURN, "amount": 6.0, "duration": 3.0}, {"op": "boost", "kind": Gadget.DAMAGE, "amount": 3.0}],
		"spicy":     [{"op": "ensure", "kind": Gadget.BURN, "amount": 3.0, "duration": 2.0}],
		"heavy":     [{"op": "boost", "kind": Gadget.DAMAGE, "amount": 6.0}],
	}

## Tag -> ammo-profile deltas. This is what makes the LOADED ROUND alter the shot.
## Keys: dmg_mult/drag/bounce/slow/explode_r/explode_dmg/burn_amt/burn_dur/homing (override),
##       dmg_add (additive to dmg_mult). Order matters only for set-vs-add interplay.
static func _tag_ammo() -> Dictionary:
	return {
		"light":     {"dmg_mult": 0.0, "drag": 3.5},   # fast, then floats to a stop
		"fluffy":    {"dmg_mult": 0.0, "drag": 3.5},
		"powder":    {"dmg_mult": 0.0, "drag": 3.5},
		"sugar":     {"dmg_mult": 0.0},
		"canned":    {"bounce": 3},                     # ricochets off walls
		"metal":     {"bounce": 3},
		"lethal":    {"dmg_add": 0.5},
		"dense":     {"dmg_add": 0.3},
		"sticky":    {"slow": 2.5},
		"explosive": {"explode_r": 80.0, "explode_dmg": 14.0},
		"electric":  {"burn_amt": 4.0, "burn_dur": 3.0},
		"attract":   {"homing": true},
		"rubber":    {"bounce": 4},
		"flammable": {"burn_amt": 4.0, "burn_dur": 3.0},
		"caustic":   {"burn_amt": 5.0, "burn_dur": 3.0},
		"spicy":     {"burn_amt": 3.0, "burn_dur": 2.0},
		"heavy":     {"dmg_add": 0.4},
		"sharp":     {"pierce": 1},
	}

## Exact-combo overrides — the authored "jokes". Key = sorted item ids joined by ",".
## A spec is: {name, desc, delivery, effects:[{kind,amount,duration,radius,count}],
##             homing?, harmless?, speed?, color?}. Seeded with a couple; big batch is Phase 2.
static func _specials() -> Dictionary:
	return {
		"anchovies,m16": {
			"name": "Anchovy Rifle", "desc": "It fires. It reeks. The simulation flinched — and you noticed.",
			"delivery": Gadget.Delivery.PROJECTILE, "speed": 720.0,
			"effects": [{"kind": Gadget.DAMAGE, "amount": 12.0}],
		},
		"beehive,grenade,magnet": {
			"name": "Swarm Mine", "desc": "Magnetized explosive bees seek the nearest metal. Reality did not sign off on this.",
			"delivery": Gadget.Delivery.PLACED, "homing": true,
			"effects": [{"kind": Gadget.SPAWN, "count": 4}, {"kind": Gadget.EXPLODE, "amount": 16.0, "radius": 90.0}],
		},
		"co2_canister,nerf_gun,spaghetti": {
			"name": "Meatball Launcher", "desc": "Pressurized spaghetti rounds. Sticky, fast, and deeply upsetting to all involved.",
			"delivery": Gadget.Delivery.PROJECTILE, "speed": 820.0,
			"effects": [{"kind": Gadget.DAMAGE, "amount": 10.0}, {"kind": Gadget.SLOW, "amount": 50.0, "duration": 2.5}],
		},
		"backpack,chainsaw,vacuum": {
			"name": "Harvester", "desc": "Vacuums up loot in a wide radius and quietly shreds anything that wanders too close.",
			"delivery": Gadget.Delivery.AURA,
			"effects": [{"kind": Gadget.COLLECT, "radius": 190.0}, {"kind": Gadget.DAMAGE, "amount": 5.0}],
		},
		"bear_trap,boomerang,fishing_rod": {
			"name": "Retriever", "desc": "Casts a snare. Misses come back; hits don't get to leave.",
			"delivery": Gadget.Delivery.PLACED,
			"effects": [{"kind": Gadget.SNARE, "duration": 2.6}, {"kind": Gadget.DAMAGE, "amount": 8.0}],
		},
		"fireworks,pringles": {
			"name": "Roman Candle", "desc": "A festive tube of mistakes. Spits flaming sparks downrange.",
			"delivery": Gadget.Delivery.PROJECTILE, "speed": 900.0,
			"effects": [{"kind": Gadget.SPAWN, "count": 4}, {"kind": Gadget.BURN, "amount": 4.0, "duration": 3.0}],
		},
		"glue,grenade": {
			"name": "Sticky Bomb", "desc": "It adheres. Then it does not.",
			"delivery": Gadget.Delivery.LOBBED,
			"effects": [{"kind": Gadget.EXPLODE, "amount": 18.0, "radius": 95.0}, {"kind": Gadget.SLOW, "amount": 50.0, "duration": 2.5}],
		},
		"beehive,co2_canister": {
			"name": "Bee Cannon", "desc": "Pressurized apiary. The bees are furious and aerodynamic.",
			"delivery": Gadget.Delivery.PROJECTILE, "speed": 950.0, "homing": true,
			"effects": [{"kind": Gadget.SPAWN, "count": 5}],
		},
		"anchovies,beehive": {
			"name": "Chum Swarm", "desc": "Fish-scented bees seek the nearest warm body. Nobody is okay.",
			"delivery": Gadget.Delivery.PROJECTILE, "homing": true,
			"effects": [{"kind": Gadget.SPAWN, "count": 4}, {"kind": Gadget.DAMAGE, "amount": 6.0}],
		},
		"magnet,marbles": {
			"name": "Bearing Storm", "desc": "Magnetized steel marbles that punch clean through a crowd.",
			"delivery": Gadget.Delivery.PROJECTILE, "speed": 1000.0, "homing": true,
			"effects": [{"kind": Gadget.DAMAGE, "amount": 11.0}, {"kind": Gadget.PIERCE, "count": 2}],
		},
		"propane_tank,wire_hanger": {
			"name": "Bottle Rocket", "desc": "A propane tank with delusions of flight. Stand back. Further.",
			"delivery": Gadget.Delivery.LOBBED, "speed": 700.0,
			"effects": [{"kind": Gadget.EXPLODE, "amount": 26.0, "radius": 120.0}],
		},
		"chainsaw,co2_canister": {
			"name": "Buzzsaw Launcher", "desc": "It fires the chainsaw. The whole chainsaw. Repeatedly.",
			"delivery": Gadget.Delivery.PROJECTILE, "speed": 760.0,
			"effects": [{"kind": Gadget.DAMAGE, "amount": 20.0}, {"kind": Gadget.PIERCE, "count": 3}],
		},
	}

# =============================================================================
# BUILDERS
# =============================================================================

static func _build_generic(items: Array, base: Gadget, tags: Dictionary) -> Gadget:
	var g := Gadget.new()
	if base != null:
		g.delivery = base.delivery
		g.effects = base.effects.duplicate(true)
		g.projectile_speed = base.projectile_speed
		g.homing = base.homing
		g.harmless = base.harmless
		g.color = base.color
	else:
		g.delivery = _delivery_for(tags)
		g.color = items[0].color

	# delivery-intrinsic behavior
	if g.delivery == Gadget.Delivery.MELEE:
		_ensure(g, Gadget.DAMAGE, 16.0)
		_ensure(g, Gadget.KNOCKBACK, 280.0)
	elif g.delivery == Gadget.Delivery.AURA:
		_ensure(g, Gadget.COLLECT, 0.0, 0.0, 180.0)

	# component contributions, from the table (also augment a base weapon)
	var te := _tag_effects()
	for tag in te:
		if tags.has(tag):
			_apply_ops(g, te[tag])

	# building something NEW with no dangerous part -> a harmless contraption
	var armed := _armed(tags)
	if base == null and not armed:
		g.harmless = true
		var d := g.get_effect(Gadget.DAMAGE)
		if not d.is_empty(): d["amount"] = 1.0

	g.display_name = _name(items, base, g)
	g.description = _describe(g, base)
	return g

static func _build_special(spec: Dictionary, items: Array) -> Gadget:
	var g := Gadget.new()
	g.display_name = spec.get("name", "Special")
	g.description = spec.get("desc", "")
	g.delivery = spec.get("delivery", Gadget.Delivery.PROJECTILE)
	g.homing = spec.get("homing", false)
	g.harmless = spec.get("harmless", false)
	g.projectile_speed = spec.get("speed", 700.0)
	g.color = spec.get("color", items[0].color)
	for e in spec.get("effects", []):
		g.add(e["kind"], float(e.get("amount", 0.0)), float(e.get("duration", 0.0)),
			float(e.get("radius", 0.0)), int(e.get("count", 0)))
	return g

## Fire mode + ammo capacity. Runs for both generic and special gadgets.
static func _finalize(g: Gadget, tags: Dictionary) -> void:
	g.semi = true
	if g.delivery == Gadget.Delivery.MELEE:
		g.semi = false
	elif g.delivery == Gadget.Delivery.PROJECTILE and tags.has("automatic"):
		g.semi = false

	g.uses_ammo = g.delivery in [Gadget.Delivery.PROJECTILE, Gadget.Delivery.LOBBED, Gadget.Delivery.PLACED]
	if g.uses_ammo:
		var pwr := maxf(g.amount_of(Gadget.DAMAGE), g.amount_of(Gadget.EXPLODE))
		pwr = maxf(pwr, 4.0)
		match g.delivery:
			Gadget.Delivery.LOBBED, Gadget.Delivery.PLACED:
				g.ammo_max = clampi(int(round(60.0 / pwr)), 3, 8)
			_:
				g.ammo_max = clampi(int(round(90.0 / pwr)), 6, 30)
				if not g.semi: g.ammo_max = int(g.ammo_max * 1.5)
		g.fill_plain()

# =============================================================================
# AMMO PROFILE  (loaded round behavior)
# =============================================================================

static func ammo_profile(items: Array) -> Dictionary:
	var tags := _tagset(items)
	var p := {
		"name": _ammo_name(items), "color": items[0].color,
		"dmg_mult": 1.0, "drag": 0.0, "bounce": 0, "homing": false, "pierce": 0,
		"slow": 0.0, "burn_amt": 0.0, "burn_dur": 0.0, "explode_r": 0.0, "explode_dmg": 0.0,
	}
	var table := _tag_ammo()
	for tag in table:
		if not tags.has(tag):
			continue
		var d: Dictionary = table[tag]
		for k in d:
			match k:
				"dmg_add": p["dmg_mult"] = float(p["dmg_mult"]) + float(d[k])
				"slow": p["slow"] = maxf(float(p["slow"]), float(d[k]))
				"bounce": p["bounce"] = maxi(int(p["bounce"]), int(d[k]))
				_: p[k] = d[k]
	return p

# =============================================================================
# HELPERS
# =============================================================================

static func _tagset(items: Array) -> Dictionary:
	var tags := {}
	for it in items:
		for t in it.tags:
			tags[t] = true
	return tags

## A WEAPON needs at least one genuinely dangerous component, or it's a harmless contraption.
static func _armed(tags: Dictionary) -> bool:
	for t in ["lethal", "explosive", "kinetic", "pressure", "electric", "flammable", "caustic", "spicy", "sharp", "heavy"]:
		if tags.has(t):
			return true
	return false

static func _key(items: Array) -> String:
	var ids: Array[String] = []
	for it in items:
		ids.append(it.id)
	ids.sort()
	return ",".join(ids)

static func _apply_ops(g: Gadget, ops: Array) -> void:
	for op in ops:
		match op["op"]:
			"boost":
				_boost(g, op["kind"], float(op["amount"]))
			"ensure":
				_ensure(g, op["kind"], float(op.get("amount", 0.0)), float(op.get("duration", 0.0)),
					float(op.get("radius", 0.0)), int(op.get("count", 0)))
			"homing":
				g.homing = true
			"pierce":
				var pc := g.get_effect(Gadget.PIERCE)
				if pc.is_empty(): g.add(Gadget.PIERCE, 0, 0, 0, int(op.get("count", 1)))
				else: pc["count"] = int(pc["count"]) + 1
			"speed":
				g.projectile_speed = minf(g.projectile_speed * float(op.get("mult", 1.0)), 1200.0)

static func _ensure(g: Gadget, kind: String, amount := 0.0, duration := 0.0, radius := 0.0, count := 0) -> void:
	if g.get_effect(kind).is_empty():
		g.add(kind, amount, duration, radius, count)

static func _boost(g: Gadget, kind: String, amount: float) -> void:
	var e := g.get_effect(kind)
	if e.is_empty(): g.add(kind, amount)
	else: e["amount"] = float(e["amount"]) + amount

static func _delivery_for(tags: Dictionary) -> Gadget.Delivery:
	for rule in _delivery_rules():
		if tags.has(rule[0]):
			return rule[1]
	return Gadget.Delivery.PROJECTILE  # improvised launcher

static func _delivery_word(d: Gadget.Delivery) -> String:
	match d:
		Gadget.Delivery.MELEE: return "Basher"
		Gadget.Delivery.LOBBED: return "Bomb"
		Gadget.Delivery.AURA: return "Field"
		Gadget.Delivery.PLACED: return "Trap"
		_: return "Gun"

static func _ammo_name(items: Array) -> String:
	var parts := String(items[0].display_name).split(" ")
	return "%s Rounds" % parts[parts.size() - 1]

static func _name(items: Array, base: Gadget, g: Gadget) -> String:
	if base != null:
		var parts := String(items[0].display_name).split(" ")
		return "%s +%s" % [base.display_name, parts[parts.size() - 1]]
	var word := "Contraption" if g.harmless else _delivery_word(g.delivery)
	var frame: String = items[0].display_name
	for pre in ["Can of ", "Handful of ", "Plate of ", "Bottle of "]:
		if frame.begins_with(pre):
			frame = frame.substr(pre.length()); break
	return "%s %s" % [frame, word]

static func _describe(g: Gadget, base: Gadget) -> String:
	if g.effects.is_empty(): return "It does... nothing. A monument to wasted potential."
	if g.harmless: return "It works. It is not a weapon. It is barely an opinion."
	var d := ""
	match g.delivery:
		Gadget.Delivery.MELEE: d = "Get close. Swing. Regret nothing."
		Gadget.Delivery.LOBBED: d = "Throw it. Stand well back."
		Gadget.Delivery.AURA: d = "It hums. Things nearby suffer."
		Gadget.Delivery.PLACED: d = "Drop it. Wait. Smile."
		_: d = "Point. Click. Disagree."
	return ("Modified. " + d) if base != null else d
