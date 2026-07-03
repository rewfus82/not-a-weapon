class_name Item
extends RefCounted

## A scavenged object. See DESIGN.md §5.
##
## HYBRID model (decided 2026-07-03): items carry TWO descriptions of themselves, one
## per crafting layer, so the deterministic game and the AI workbench each read what fits:
##   tags[]         - flat vocabulary the DETERMINISTIC resolver + field crafting run on
##                    (delivery routing, effect composition, ammo profiles). Keep these in
##                    the vocabulary resolver.gd keys off, or they do nothing.
##   associations[] - richer real-world "reads" (what a player intuitively thinks the thing
##                    does) for the WORKBENCH AI layer. Optional, enriches over time.
##
## `category` buckets the item in the taxonomy. Everything below `Item.JUNK` here is the
## glitch-fuel scavenge; real WEAPON/AMMO/THROWN/MELEE/ADDON items arrive in Phase 1.
##
## (The old `slots`/`affordance` fields were dropped — nothing read them.)

const JUNK := "junk"
const WEAPON := "weapon"
const AMMO := "ammo"
const THROWN := "thrown"
const MELEE := "melee"
const ADDON := "addon"

## Standalone USE ARCHETYPE — how this item behaves when wielded ALONE (DESIGN.md §5).
## This is the honest physical affordance, decided by declaration (NOT tag-mashing).
## An item's standalone use is distinct from what it contributes in a combine.
##   swing / thrust / grind  → melee    · lob → thrown-impact    · scatter → caltrops field
##   pour → liquid puddle     · return → boomerang · projectile/beam/spray → ranged
##   self → use-on-self       · field → aura       · trap/turret/decoy → placeable
##   inert → held; no standalone use (pure combine fuel / modifier)
const ARCH_INERT := "inert"

var id: String
var display_name: String
var category: String
var archetype: String             ## standalone use (see const block above)
var tags: Array[String]           ## flat vocab — the resolver + field-crafting interface
var associations: Array[String]   ## richer reads for the AI workbench layer (hybrid)
var color: Color

func _init(p_id: String, p_name: String, p_category: String, p_arch: String, p_tags: Array, p_assoc: Array, p_color: Color) -> void:
	id = p_id
	display_name = p_name
	category = p_category
	archetype = p_arch
	color = p_color
	tags = []
	for t in p_tags:
		tags.append(String(t))
	associations = []
	for a in p_assoc:
		associations.append(String(a))

func has_tag(tag: String) -> bool:
	return tags.has(tag)

## Can be thrown when it isn't used as a weapon (grenade, boomerang, molotov, ...).
func is_throwable() -> bool:
	return has_tag("thrown") or has_tag("explosive") or has_tag("return")

## Routes to the ARMOR slot instead of HAND. No armor items exist yet — the routing is here.
func is_armor() -> bool:
	return has_tag("armor")
