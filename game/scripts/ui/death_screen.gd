class_name DeathScreen
extends Control


signal restart_requested

const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const CINZEL_FONT: FontFile = preload("res://assets/fonts/Cinzel-VariableFont_wght.ttf")

@onready var black_overlay: ColorRect = %BlackOverlay
@onready var death_label: Label = %DeathLabel
@onready var death_delay_timer: Timer = %DeathDelay
@onready var hold_timer: Timer = %HoldTimer

var tunables: Tunables = TUNABLES_SCRIPT.new()
var _player_stats: PlayerStats
var _sequence_running: bool = false


func _ready() -> void:
	death_label.add_theme_font_override("font", CINZEL_FONT)
	death_label.add_theme_color_override("font_color", tunables.ui_death_text_color)
	death_label.add_theme_font_size_override("font_size", tunables.ui_death_text_size)
	visible = false
	black_overlay.modulate.a = 0.0
	death_label.modulate.a = 0.0


func bind_player_stats(stats: PlayerStats) -> void:
	if _player_stats != null and _player_stats.died.is_connected(_on_player_died):
		_player_stats.died.disconnect(_on_player_died)
	_player_stats = stats
	if _player_stats != null:
		_player_stats.died.connect(_on_player_died)


func get_is_death_text_visible() -> bool:
	return visible and death_label.modulate.a >= 0.99


func get_black_overlay_alpha() -> float:
	return black_overlay.modulate.a


func get_death_label_font() -> Font:
	return death_label.get_theme_font("font")


func _on_player_died() -> void:
	if not _sequence_running:
		_run_death_sequence()


func _run_death_sequence() -> void:
	_sequence_running = true
	visible = true
	black_overlay.modulate.a = 0.0
	death_label.modulate.a = 0.0
	death_delay_timer.start(tunables.death_delay)
	await death_delay_timer.timeout
	if not is_inside_tree():
		return
	var black_tween := create_tween().set_ignore_time_scale(true)
	black_tween.tween_property(black_overlay, "modulate:a", 1.0, tunables.death_screen_fade_duration)
	await black_tween.finished
	if not is_inside_tree():
		return
	var text_tween := create_tween().set_ignore_time_scale(true)
	text_tween.tween_property(death_label, "modulate:a", 1.0, tunables.death_text_fade_duration)
	await text_tween.finished
	if not is_inside_tree():
		return
	hold_timer.start(tunables.death_text_hold_duration)
	await hold_timer.timeout
	if is_inside_tree():
		# No restart hook exists yet in game_state/game_manager; the owner performs
		# the current-phase restart when it receives this Phase 7 boundary signal.
		restart_requested.emit()
