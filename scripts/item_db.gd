class_name ItemDB
extends RefCounted

## The scavenge library — Phase 0 seed set of 32 JUNK items (DESIGN.md §5).
## Junk is the glitch fuel: mundane Midwest objects the combine brain turns into weapons,
## tools, traps, and armor. Real WEAPON/AMMO/THROWN/MELEE/ADDON items land in Phase 1.
##
## Row = [id, display_name, category, archetype, tags[], associations[], color].
##
## archetype = the STANDALONE use when wielded alone (DESIGN.md §5 delivery model):
##   swing/thrust/grind (melee) · lob (thrown-impact) · scatter (caltrops field) ·
##   pour (liquid puddle) · return (boomerang) · projectile/beam/spray (ranged) ·
##   self (use-on-self) · field (aura) · trap/turret/decoy (placeable) · inert (held).
## Declared, NOT tag-derived — a box of nails is caltrops thrown, a spread shot combined.
##
## tags[] = the DETERMINISTIC interface (resolver.gd composes EFFECTS/payload off these).
## Vocabulary that does something: flammable, explosive, electric, conductive, caustic,
## poison, sticky, sharp, blunt, heavy, dense, kinetic, cold, pressure, aerosol, gas,
## snare, bind, attract, suction, storage, swarm, heal, shield, buff, lure, tube, light,
## + materials (metal/wood/plastic/liquid/fabric). Unknown tags are harmless flavor.
## associations[] = richer reads for the AI workbench layer.

static func build() -> Dictionary:
	var defs := [
		# --- 🔧 Garage & Truck ---
		["motor_oil",     "Motor Oil",         Item.JUNK, "pour",    ["liquid","slick","sticky","flammable"],            ["a slick nobody keeps their feet on","one spark from a fire","the black blood of an engine"],       Color(0.10,0.09,0.07)],
		["gasoline",      "Jerry Can of Gas",  Item.JUNK, "pour",    ["liquid","flammable"],                              ["accelerant","the smell before a bad decision","soaks in and spreads"],                             Color(0.80,0.68,0.20)],
		["car_battery",   "Car Battery",       Item.JUNK, "inert",   ["electric","conductive","caustic","heavy","metal"], ["twelve volts of bad idea","leaks acid","a power source waiting for a use"],                         Color(0.18,0.19,0.24)],
		["jumper_cables", "Jumper Cables",     Item.JUNK, "inert",   ["electric","conductive","metal","reach"],           ["arcs from one poor soul to the next","needs a source","reach out and shock someone"],              Color(0.85,0.20,0.20)],

		# --- 🌾 Barn & Field ---
		["fertilizer",    "Bag of Fertilizer", Item.JUNK, "inert",   ["explosive","powder","chemical","heavy"],           ["ammonium nitrate — inert until it isn't","needs fuel and a spark","a Ryder truck's worth of trouble"], Color(0.55,0.50,0.35)],
		["pitchfork",     "Pitchfork",         Item.JUNK, "thrust",  ["sharp","metal","kinetic","reach"],                 ["three points of keep-away","American Gothic","spears at a distance"],                              Color(0.60,0.55,0.45)],
		["barbed_wire",   "Barbed Wire",       Item.JUNK, "scatter", ["snare","sharp","metal","bind"],                    ["snags and tears","a tangle strung across the floor","the fence that hates you"],                   Color(0.55,0.55,0.58)],
		["hornet_nest",   "Hornet Nest",       Item.JUNK, "projectile",["swarm","living","organic"],                      ["hurl it and the cloud pours out","do NOT disturb","a furious swarm that hunts warmth"],            Color(0.75,0.62,0.35)],

		# --- 🍳 Kitchen & House ---
		["skillet",       "Cast Iron Skillet", Item.JUNK, "swing",   ["blunt","heavy","metal","flat"],                    ["a frying pan that rings like a bell","grandma's blunt instrument","heavy enough to matter"],       Color(0.16,0.16,0.18)],
		["cooking_grease","Bucket of Grease",  Item.JUNK, "pour",    ["liquid","slick","sticky","flammable"],             ["slip-and-fall in a bucket","catches fire in a heartbeat","coats everything it touches"],           Color(0.85,0.80,0.55)],
		["drain_cleaner", "Drain Cleaner",     Item.JUNK, "pour",    ["liquid","caustic","poison","chemical"],            ["lye that eats flesh","the stuff under every sink","burns going down"],                              Color(0.55,0.75,0.20)],
		["mason_jar",     "Mason Jar",         Item.JUNK, "lob",     ["thrown","glass","fragile"],                        ["shatters on impact","a sealed vessel waiting for a payload","half a molotov"],                     Color(0.70,0.85,0.80)],

		# --- 🪚 Shed & Hardware ---
		["nails",         "Box of Nails",      Item.JUNK, "scatter", ["sharp","metal","small"],                           ["scatter them like caltrops","rusty and everywhere","load them and they spray"],                    Color(0.55,0.52,0.48)],
		["pvc_pipe",      "PVC Pipe",          Item.JUNK, "inert",   ["tube","plastic","reach"],                          ["a barrel for anything","hollow and straight","aims the mess downrange"],                           Color(0.90,0.90,0.86)],
		["propane_tank",  "Propane Tank",      Item.JUNK, "lob",     ["explosive","pressure","gas","metal","heavy","cold"],["a bomb with a handle","stand back, further","vents cold when it ruptures"],                        Color(0.85,0.55,0.25)],
		["garage_spring", "Garage-Door Spring",Item.JUNK, "inert",   ["return","springy","metal","kinetic"],              ["stored violence, coiled","launches and snaps back","the thing you're warned not to touch"],        Color(0.45,0.46,0.50)],
		["sledgehammer",  "Sledgehammer",      Item.JUNK, "swing",   ["blunt","heavy","metal","kinetic"],                 ["swing for the fences","caves things in","two-handed authority"],                                   Color(0.40,0.30,0.22)],

		# --- 🧪 Cleaning & Chemical ---
		["bug_spray",     "Aerosol Bug Spray", Item.JUNK, "spray",   ["aerosol","flammable","poison","liquid","chemical"],["a flamethrower with a lighter","kills on contact","jet of poison"],                                Color(0.30,0.70,0.35)],
		["fire_extinguisher","Fire Extinguisher",Item.JUNK,"spray",  ["aerosol","pressure","cold","gas","metal"],         ["a blast of freezing fog","blows things back","chokes out fire — and sight"],                       Color(0.80,0.20,0.20)],
		["bleach",        "Bleach",            Item.JUNK, "pour",    ["liquid","caustic","poison","chemical"],            ["do not mix with ammonia","toxic fumes","burns the eyes"],                                          Color(0.92,0.94,0.90)],

		# --- ⛽ Gas Station & Store ---
		["road_flare",    "Road Flare",        Item.JUNK, "lob",     ["flammable","light","thrown"],                      ["burns like a tiny sun","light in the dark","draws the eye — and the horde"],                       Color(0.95,0.35,0.25)],
		["glow_sticks",   "Glow Sticks",       Item.JUNK, "lob",     ["light","chemical","thrown"],                       ["cold light you can toss","marks a spot","a decoy that glows"],                                     Color(0.45,0.95,0.55)],
		["air_horn",      "Air Horn",          Item.JUNK, "decoy",   ["lure","sound","pressure","gas"],                   ["deafening in a can","noise pulls the crowd","a distraction on demand"],                            Color(0.85,0.30,0.55)],
		["energy_drink",  "Energy Drink",      Item.JUNK, "self",    ["buff","liquid","sugar"],                           ["jittery superhuman speed","tastes like battery","the crash comes later"],                          Color(0.50,0.85,0.20)],

		# --- 💊 Medicine & Home ---
		["first_aid",     "First Aid Kit",     Item.JUNK, "self",    ["heal","fabric","medical"],                         ["patch yourself up","gauze and hope","the difference between limping and dying"],                   Color(0.95,0.95,0.92)],
		["duct_tape",     "Duct Tape",         Item.JUNK, "inert",   ["sticky","bind","fabric","snare"],                  ["fixes anything, attaches everything","the universal modifier","binds it shut"],                    Color(0.60,0.60,0.62)],
		["painkillers",   "Painkillers",       Item.JUNK, "self",    ["heal","buff","powder","medical"],                  ["numbs it away","ignore the wound for a while","rattle of a bottle"],                                Color(0.90,0.85,0.80)],

		# --- 📦 Odds & Ends ---
		["magnet",        "Horseshoe Magnet",  Item.JUNK, "inert",   ["attract","metal"],                                 ["pulls metal toward it","makes things seek","cartoonishly strong"],                                 Color(0.85,0.25,0.25)],
		["shop_vac",      "Shop Vac",          Item.JUNK, "field",   ["suction","storage","electric"],                    ["inhales everything nearby","a loot vacuum","industrial lungs"],                                    Color(0.30,0.55,0.80)],
		["feathers",      "Handful of Feathers",Item.JUNK,"inert",   ["light","fluffy","organic"],                        ["drifts on the air","weightless — changes how a thing flies","useless until stuck to something"],   Color(0.95,0.95,0.95)],
		["chain",         "Length of Chain",   Item.JUNK, "swing",   ["heavy","metal","kinetic","conductive","bind"],     ["swings with weight","links jump the current","wrap, drag, throttle"],                              Color(0.50,0.50,0.54)],
		["brick",         "Brick",             Item.JUNK, "lob",     ["blunt","heavy","dense","kinetic"],                 ["through a window or a skull","a fist-sized argument","dead simple, dead effective"],               Color(0.60,0.30,0.25)],
	]
	var db := {}
	for d in defs:
		var it := Item.new(d[0], d[1], d[2], d[3], d[4], d[5], d[6])
		db[it.id] = it
	return db
