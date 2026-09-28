class_name DragonHealthbar
extends Control


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

@onready var hp_bar: ProgressBar = %DragonHPBar

var tunables: Tunables = TUNABLES_SCRIPT.new()


func _ready() -> void:
	_apply_placeholder_layout()
	hide_bar()


func set_hp(current: float, max_hp: float) -> void:
	hp_bar.max_value = maxf(max_hp, 0.0)
	hp_bar.value = clampf(current, 0.0, hp_bar.max_value)


func show_bar() -> void:
	visible = true
	modulate.a = 1.0


func hide_bar() -> void:
	visible = false
	modulate.a = 0.0


func get_bar_value() -> float:
	return hp_bar.value


func is_visible_bar() -> bool:
	return visible and modulate.a >= 0.99


func _apply_placeholder_layout() -> void:
	offset_left = -tunables.ui_dragon_hp_size.x * 0.5
	offset_right = tunables.ui_dragon_hp_size.x * 0.5
	offset_top = -tunables.ui_dragon_hp_bottom_offset - tunables.ui_dragon_hp_size.y
	offset_bottom = -tunables.ui_dragon_hp_bottom_offset
	var background := hp_bar.get_theme_stylebox("background").duplicate() as StyleBoxFlat
	background.bg_color = tunables.ui_dragon_hp_background_color
	hp_bar.add_theme_stylebox_override("background", background)
	var fill := hp_bar.get_theme_stylebox("fill").duplicate() as StyleBoxFlat
	fill.bg_color = tunables.ui_dragon_hp_color
	hp_bar.add_theme_stylebox_override("fill", fill)
