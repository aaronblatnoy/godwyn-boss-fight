class_name CombatHud
extends Control


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

@onready var hp_bar: ProgressBar = %HPBar
@onready var fp_bar: ProgressBar = %FPBar
@onready var stamina_bar: ProgressBar = %StaminaBar
@onready var flask_icon: Label = %FlaskIcon
@onready var flask_count_label: Label = %FlaskCount

var tunables: Tunables = TUNABLES_SCRIPT.new()
var _player_stats: PlayerStats


func _ready() -> void:
	_apply_spec_layout()
	_set_flask_count(tunables.flask_count)


func bind_player_stats(stats: PlayerStats) -> void:
	if _player_stats != null:
		if _player_stats.hp_changed.is_connected(_on_hp_changed):
			_player_stats.hp_changed.disconnect(_on_hp_changed)
		if _player_stats.stamina_changed.is_connected(_on_stamina_changed):
			_player_stats.stamina_changed.disconnect(_on_stamina_changed)
	_player_stats = stats
	if _player_stats == null:
		return
	_player_stats.hp_changed.connect(_on_hp_changed)
	_player_stats.stamina_changed.connect(_on_stamina_changed)
	_on_hp_changed(_player_stats.hp, _player_stats.tunables.player_max_hp)
	_on_stamina_changed(_player_stats.stamina, float(_player_stats.tunables.player_max_stamina))
	# FP is display-only in this plan and has no change signal.
	fp_bar.max_value = float(_player_stats.tunables.player_max_fp)
	fp_bar.value = float(_player_stats.fp)


func get_hp_bar_value() -> float:
	return hp_bar.value


func get_fp_bar_value() -> float:
	return fp_bar.value


func get_stamina_bar_value() -> float:
	return stamina_bar.value


func get_flask_count() -> int:
	return int(flask_count_label.text)


func get_flask_icon_alpha() -> float:
	return flask_icon.modulate.a


func set_flask_count(count: int) -> void:
	# TODO(later phase): bind to a real flask-consumed signal when the flask system lands
	_set_flask_count(count)


func _on_hp_changed(new_hp: int, max_hp: int) -> void:
	hp_bar.max_value = float(max_hp)
	hp_bar.value = float(new_hp)


func _on_stamina_changed(new_stamina: float, max_stamina: float) -> void:
	stamina_bar.max_value = max_stamina
	stamina_bar.value = new_stamina


func _set_flask_count(count: int) -> void:
	flask_count_label.text = str(maxi(count, 0))
	flask_icon.modulate.a = 0.35 if count <= 0 else 1.0


func _apply_spec_layout() -> void:
	var hp_top := -tunables.ui_player_hp_bottom_offset - tunables.ui_player_hp_size.y
	_set_bar_layout(hp_bar, tunables.ui_player_left_margin, hp_top, tunables.ui_player_hp_size)
	var fp_top := -tunables.ui_player_hp_bottom_offset + tunables.ui_player_fp_gap
	_set_bar_layout(fp_bar, tunables.ui_player_left_margin, fp_top, tunables.ui_player_fp_size)
	var stamina_top := fp_top + tunables.ui_player_fp_size.y + tunables.ui_player_stamina_gap
	_set_bar_layout(stamina_bar, tunables.ui_player_left_margin, stamina_top, tunables.ui_player_stamina_size)
	%FlaskDisplay.offset_left = tunables.ui_player_left_margin
	%FlaskDisplay.offset_top = stamina_top + tunables.ui_player_stamina_size.y + tunables.ui_player_flask_gap


func _set_bar_layout(bar: ProgressBar, left: float, top: float, size: Vector2) -> void:
	bar.offset_left = left
	bar.offset_top = top
	bar.offset_right = left + size.x
	bar.offset_bottom = top + size.y
