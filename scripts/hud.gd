extends Node2D
## Renders the in-world HUD on its own CanvasLayer, so the world's CanvasModulate
## (darkness) never dims it. main.gd does the actual drawing via _draw_hud(self).

var main: Node

func _process(_delta: float) -> void:
	queue_redraw()

func _draw() -> void:
	if main != null:
		main._draw_hud(self)
