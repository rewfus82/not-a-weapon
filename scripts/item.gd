class_name Item
extends RefCounted

## A combinable junk object.
##
## The whole design rests on items carrying *functions*, not just materials.
## The resolver reads `slots` + `affordance` + `tags` to compose an effect, so a
## player can reason by analogy ("a Pringles can is a tube -> a barrel/scope")
## instead of brute-forcing recipes.

## Functional slots an item can fill in the gadget grammar (Delivery + Payload +
## Behavior/Targeting). An item may fill more than one.
const SLOT_DELIVERY := "delivery"
const SLOT_PAYLOAD := "payload"
const SLOT_BEHAVIOR := "behavior"

var id: String
var display_name: String
var slots: Array[String]      ## which of the SLOT_* this item can fill
var affordance: String        ## the human verb: "tube", "swarm", "attract", ...
var tags: Array[String]       ## material/effect tags: "metal", "lethal", "sticky"
var color: Color

func _init(p_id: String, p_name: String, p_slots: Array, p_affordance: String, p_tags: Array, p_color: Color) -> void:
	id = p_id
	display_name = p_name
	affordance = p_affordance
	color = p_color
	slots = []
	for s in p_slots:
		slots.append(String(s))
	tags = []
	for t in p_tags:
		tags.append(String(t))

func has_slot(slot: String) -> bool:
	return slots.has(slot)

func has_tag(tag: String) -> bool:
	return tags.has(tag)
