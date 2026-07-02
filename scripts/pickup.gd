class_name Pickup
extends Node2D
## A dropped item lying on the ground — the first real scene-tree entity (replaces
## the old _loot dicts drawn in main._draw). Owns its own sprite; main.gd only
## moves it toward the player (loot magnet) and frees it on collect.

var id: String

func setup(item_id: String, icon: Texture2D) -> void:
	id = item_id
	var spr := Sprite2D.new()
	if icon != null:
		spr.texture = icon
		spr.scale = Vector2.ONE * (24.0 / maxf(icon.get_size().y, 1.0))
	spr.modulate = Color(0.98, 0.88, 0.4)
	add_child(spr)
