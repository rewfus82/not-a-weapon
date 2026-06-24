class_name Gadget
extends RefCounted

## The resolved output of a combine: an *effect profile*, not necessarily a weapon.
##
## A weapon is just one possible effect. Duds, control tools, and utility gadgets
## are first-class results so "combine anything and see what happens" stays true.

enum Category { DAMAGE, CONTROL, MOBILITY, UTILITY, CONSUMABLE, DUD }

var display_name: String = "Nothing"
var category: Category = Category.DUD
var description: String = ""

# --- effect parameters (only the ones relevant to the category are used) ---
var damage: float = 0.0
var control: String = "none"        ## "slow", "snare", or "none"
var projectile_speed: float = 600.0
var homing: bool = false
var aoe: float = 0.0                 ## splash radius; 0 = single target
var auto_collect: bool = false      ## passive: pulls loot in a radius (Harvester)
var harmless: bool = false          ## it fires, but does ~nothing (pixie-stix crossbow)

var color: Color = Color(0.6, 0.6, 0.6)

func category_name() -> String:
	match category:
		Category.DAMAGE: return "DAMAGE"
		Category.CONTROL: return "CONTROL"
		Category.MOBILITY: return "MOBILITY"
		Category.UTILITY: return "UTILITY"
		Category.CONSUMABLE: return "CONSUMABLE"
		_: return "DUD"

## True if firing should spawn a projectile (vs. passive/no-op gadgets).
func is_projectile() -> bool:
	return category == Category.DAMAGE or category == Category.CONTROL
