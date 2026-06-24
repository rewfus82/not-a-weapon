class_name ItemDB
extends RefCounted

## The junk library. Breadth over fidelity — a combine game needs lots of mundane
## items. Each row is: id, name, slots, affordance, tags, color.
##
## Tags worth knowing (the resolver keys off these):
##   gun_frame  - a real weapon; Tiers 1-2 require one to be present
##   lethal     - can actually hurt; absence => harmless contraption
##   explosive  - big damage + splash
##   sticky     - resolves to a slow
##   snare      - resolves to a snare/root
##   suction / storage - resolves to passive loot collection
##   sugar / toy / light - the "adorable but useless" signals
##   pressure   - propellant: boosts speed + a little damage
##   attract    - magnet: makes a projectile home on metal

static func build() -> Dictionary:
	var defs := [
		["m16",          "M16 Rifle",          ["delivery", "behavior"], "fire_projectile", ["ranged", "lethal", "gun_frame", "metal"],            Color(0.45, 0.45, 0.50)],
		["nerf_gun",     "Nerf Blaster",       ["delivery", "behavior"], "fire_projectile", ["ranged", "toy", "plastic"],                          Color(0.95, 0.55, 0.15)],
		["grenade",      "Frag Grenade",       ["delivery", "payload"],  "throw",           ["explosive", "lethal", "thrown", "metal"],            Color(0.40, 0.45, 0.30)],
		["chainsaw",     "Chainsaw",           ["payload"],              "rend",            ["lethal", "kinetic", "metal", "electric"],            Color(0.90, 0.40, 0.20)],
		["bear_trap",    "Bear Trap",          ["payload"],              "snap",            ["metal", "lethal", "snare"],                          Color(0.55, 0.55, 0.58)],
		["anchovies",    "Can of Anchovies",   ["payload"],              "fluid_payload",   ["organic", "salty", "canned", "liquid"],              Color(0.55, 0.40, 0.25)],
		["ketchup",      "Ketchup Bottle",     ["payload"],              "squirt",          ["liquid", "sticky", "organic"],                       Color(0.80, 0.15, 0.15)],
		["spaghetti",    "Plate of Spaghetti", ["payload"],              "noodle_mess",     ["organic", "sticky", "food"],                         Color(0.90, 0.80, 0.30)],
		["feathers",     "Handful of Feathers",["payload"],              "flutter",         ["light", "organic", "fluffy"],                        Color(0.95, 0.95, 0.95)],
		["pixie_stix",   "Pixie Stix",         ["payload"],              "sugar_dust",      ["sugar", "light", "powder"],                          Color(0.95, 0.55, 0.80)],
		["potato",       "Potato",             ["payload", "behavior"],  "muffle",          ["organic", "soft", "dense"],                          Color(0.75, 0.60, 0.40)],
		["beehive",      "Beehive",            ["payload"],              "swarm",           ["organic", "swarm", "living"],                        Color(0.80, 0.65, 0.35)],
		["magnet",       "Horseshoe Magnet",   ["behavior"],             "attract",         ["metal", "attract"],                                  Color(0.85, 0.25, 0.25)],
		["boomerang",    "Boomerang",          ["behavior"],             "return",          ["thrown", "return", "wood"],                          Color(0.70, 0.55, 0.30)],
		["fishing_rod",  "Fishing Rod",        ["delivery", "behavior"], "cast_reel",       ["reach", "reel"],                                     Color(0.50, 0.60, 0.45)],
		["pringles",     "Pringles Can",       ["behavior"],             "tube",            ["tube", "cardboard"],                                 Color(0.85, 0.20, 0.20)],
		["co2_canister", "CO2 Canister",       ["payload", "behavior"],  "pressurize",      ["pressure", "gas", "metal"],                          Color(0.75, 0.78, 0.82)],
		["vacuum",       "Shop Vacuum",        ["delivery"],             "suction",         ["suction", "electric"],                               Color(0.30, 0.55, 0.80)],
		["backpack",     "Backpack",           ["behavior"],             "store",           ["storage", "fabric"],                                 Color(0.35, 0.60, 0.35)],
		["wire_hanger",  "Wire Hanger",        ["delivery", "behavior"], "springy_frame",   ["metal", "springy"],                                  Color(0.60, 0.62, 0.65)],
		["zip_ties",     "Zip Ties",           ["behavior"],             "fasten",          ["plastic", "bind"],                                   Color(0.20, 0.20, 0.22)],
	]
	var db := {}
	for d in defs:
		var it := Item.new(d[0], d[1], d[2], d[3], d[4], d[5])
		db[it.id] = it
	return db
