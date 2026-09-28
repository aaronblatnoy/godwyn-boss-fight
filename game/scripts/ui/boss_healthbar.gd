class_name BossHealthbar
extends Control


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const CINZEL_FONT: FontFile = preload("res://assets/fonts/Cinzel-VariableFont_wght.ttf")

@onready var hp_bar: ProgressBar = %BossHPBar
@onready var boss_name_label: Label = %BossName
@onready var boss_title_label: Label = %BossTitle
@onready var dragon_healthbar: DragonHealthbar = %DragonHealthbar
@onready var intro_delay: Timer = %IntroDelay

var tunables: Tunables = TUNABLES_SCRIPT.new()
var _boss_stats: BossStats
var _intro_generation: int = 0
var _active_tween: Tween


func _ready() -> void:
	_apply_spec_layout()
	_apply_spec_styles()
	boss_name_label.modulate.a = 0.0
	boss_title_label.modulate.a = 0.0
	hp_bar.modulate.a = 0.0


func bind_boss_stats(stats: BossStats) -> void:
	if _boss_stats != null and _boss_stats.hp_changed.is_connected(_on_hp_changed):
		_boss_stats.hp_changed.disconnect(_on_hp_changed)
	_boss_stats = stats
	if _boss_stats == null:
		return
	_boss_stats.hp_changed.connect(_on_hp_changed)
	_on_hp_changed(_boss_stats.hp, _boss_stats.max_hp)


func start_intro() -> void:
	_intro_generation += 1
	var generation := _intro_generation
	if _active_tween != null and _active_tween.is_valid():
		_active_tween.kill()
	intro_delay.stop()
	boss_name_label.modulate.a = 0.0
	boss_title_label.modulate.a = 0.0
	hp_bar.modulate.a = 0.0
	_run_intro(generation)


func get_bar_value() -> float:
	return hp_bar.value


func get_name_card_alpha() -> float:
	return minf(boss_name_label.modulate.a, boss_title_label.modulate.a)


func get_bar_alpha() -> float:
	return hp_bar.modulate.a


func get_boss_name_font() -> Font:
	return boss_name_label.get_theme_font("font")


func get_boss_title_font() -> Font:
	return boss_title_label.get_theme_font("font")


func get_boss_name_color() -> Color:
	return boss_name_label.get_theme_color("font_color")


func get_dragon_healthbar() -> DragonHealthbar:
	return dragon_healthbar


func is_name_card_visible() -> bool:
	return get_name_card_alpha() >= 0.99


func is_bar_visible() -> bool:
	return get_bar_alpha() >= 0.99


func _run_intro(generation: int) -> void:
	intro_delay.start(tunables.ui_boss_name_delay)
	await intro_delay.timeout
	if generation != _intro_generation or not is_inside_tree():
		return
	_active_tween = create_tween().set_parallel(true).set_ignore_time_scale(true)
	_active_tween.tween_property(boss_name_label, "modulate:a", 1.0, tunables.ui_boss_name_fade_duration)
	_active_tween.tween_property(boss_title_label, "modulate:a", 1.0, tunables.ui_boss_name_fade_duration)
	await _active_tween.finished
	if generation != _intro_generation or not is_inside_tree():
		return
	# PLACEHOLDER -- SPEC.txt Section 14 does not specify a separate boss-bar fade
	# duration; reuse the sourced 0.6s name-card fade. Replace when real timing lands.
	_active_tween = create_tween().set_ignore_time_scale(true)
	_active_tween.tween_property(hp_bar, "modulate:a", 1.0, tunables.ui_boss_name_fade_duration)


func _on_hp_changed(new_hp: int, max_hp: int) -> void:
	hp_bar.max_value = float(max_hp)
	hp_bar.value = float(new_hp)


func _apply_spec_layout() -> void:
	hp_bar.offset_left = -tunables.ui_boss_hp_size.x * 0.5
	hp_bar.offset_right = tunables.ui_boss_hp_size.x * 0.5
	hp_bar.offset_top = -tunables.ui_boss_bottom_offset - tunables.ui_boss_hp_size.y
	hp_bar.offset_bottom = -tunables.ui_boss_bottom_offset
	boss_name_label.add_theme_font_size_override("font_size", tunables.ui_boss_name_line_1_size)
	boss_title_label.add_theme_font_size_override("font_size", tunables.ui_boss_name_line_2_size)
	boss_name_label.add_theme_font_override("font", CINZEL_FONT)
	boss_name_label.add_theme_color_override("font_color", tunables.ui_boss_name_line_1_color)
	var italic_font := FontVariation.new()
	italic_font.base_font = CINZEL_FONT
	italic_font.variation_transform = Transform2D(
		Vector2(1.0, 0.0),
		Vector2(-tunables.ui_boss_name_line_2_italic_shear, 1.0),
		Vector2.ZERO
	)
	italic_font.spacing_glyph = tunables.ui_boss_name_line_2_glyph_spacing
	boss_title_label.add_theme_font_override("font", italic_font)


func _apply_spec_styles() -> void:
	var background := hp_bar.get_theme_stylebox("background").duplicate() as StyleBoxFlat
	background.bg_color = tunables.ui_boss_hp_background_color
	hp_bar.add_theme_stylebox_override("background", background)
	var fill := hp_bar.get_theme_stylebox("fill").duplicate() as StyleBoxFlat
	fill.bg_color = tunables.ui_boss_hp_color
	hp_bar.add_theme_stylebox_override("fill", fill)
