class_name Resolver
extends RefCounted

## Deterministic, component-driven. Items carry the meaning; this maps their tags
## to a DELIVERY + composed EFFECTS so the parts actually change the result.
##
## Pass `base` to MODIFY an existing weapon (the junk augments it — Pringles add
## pierce, a magnet adds homing, CO2 adds speed) instead of building from scratch.

static func combine(items: Array, base: Gadget = null) -> Gadget:
	if items.is_empty():
		var d := Gadget.new()
		d.description = "Nothing on the bench."
		return d

	var tags := {}
	for it in items:
		for t in it.tags:
			tags[t] = true

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

	var armed: bool = tags.has("lethal") or tags.has("explosive") or tags.has("kinetic") or tags.has("pressure")

	# delivery-intrinsic behavior
	if g.delivery == Gadget.Delivery.MELEE:
		_ensure(g, Gadget.DAMAGE, 16.0)
		_ensure(g, Gadget.KNOCKBACK, 280.0)
	elif g.delivery == Gadget.Delivery.AURA:
		_ensure(g, Gadget.COLLECT, 0.0, 0.0, 180.0)

	# component contributions (these also augment a base weapon)
	if tags.has("lethal"): _boost(g, Gadget.DAMAGE, 12.0)
	if tags.has("kinetic"): _boost(g, Gadget.DAMAGE, 8.0)
	if tags.has("explosive"):
		_ensure(g, Gadget.EXPLODE, 16.0, 0.0, 90.0)
		_boost(g, Gadget.DAMAGE, 4.0)
	if tags.has("sticky"): _ensure(g, Gadget.SLOW, 55.0, 3.0)
	if tags.has("snare"): _ensure(g, Gadget.SNARE, 0.0, 2.2)
	if tags.has("electric"): _ensure(g, Gadget.BURN, 4.0, 3.0)
	if tags.has("swarm"):
		_ensure(g, Gadget.SPAWN, 0.0, 0.0, 0.0, 4)
		g.homing = true
	if tags.has("attract"): g.homing = true
	if tags.has("tube"):
		var pc := g.get_effect(Gadget.PIERCE)
		if pc.is_empty(): g.add(Gadget.PIERCE, 0, 0, 0, 2)
		else: pc["count"] = int(pc["count"]) + 1
	if tags.has("pressure"):
		g.projectile_speed = minf(g.projectile_speed * 1.4, 1200.0)
		_boost(g, Gadget.DAMAGE, 3.0)

	# building something NEW with no dangerous part -> a harmless contraption
	if base == null and not armed:
		g.harmless = true
		var d := g.get_effect(Gadget.DAMAGE)
		if not d.is_empty(): d["amount"] = 1.0

	# fire mode: ranged is semi-auto (one shot/click) unless automatic; melee grinds while held
	g.semi = true
	if g.delivery == Gadget.Delivery.MELEE:
		g.semi = false
	elif g.delivery == Gadget.Delivery.PROJECTILE and tags.has("automatic"):
		g.semi = false

	g.display_name = _name(items, base, g)
	g.description = _describe(g, base)
	return g

# --- helpers -----------------------------------------------------------------

static func _ensure(g: Gadget, kind: String, amount := 0.0, duration := 0.0, radius := 0.0, count := 0) -> void:
	if g.get_effect(kind).is_empty():
		g.add(kind, amount, duration, radius, count)

static func _boost(g: Gadget, kind: String, amount: float) -> void:
	var e := g.get_effect(kind)
	if e.is_empty(): g.add(kind, amount)
	else: e["amount"] = float(e["amount"]) + amount

static func _delivery_for(tags: Dictionary) -> Gadget.Delivery:
	if tags.has("gun_frame") or tags.has("ranged"): return Gadget.Delivery.PROJECTILE
	if tags.has("explosive") or tags.has("thrown"): return Gadget.Delivery.LOBBED
	if tags.has("kinetic") or tags.has("flat"): return Gadget.Delivery.MELEE
	if tags.has("snare"): return Gadget.Delivery.PLACED
	if tags.has("suction") or tags.has("storage"): return Gadget.Delivery.AURA
	return Gadget.Delivery.PROJECTILE  # improvised launcher

static func _delivery_word(d: Gadget.Delivery) -> String:
	match d:
		Gadget.Delivery.MELEE: return "Basher"
		Gadget.Delivery.LOBBED: return "Bomb"
		Gadget.Delivery.AURA: return "Field"
		Gadget.Delivery.PLACED: return "Trap"
		_: return "Gun"

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
