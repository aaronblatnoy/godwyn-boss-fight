extends SceneTree


const HUD_SCENE := preload("res://scenes/ui/hud.tscn")
const BOSS_UI_SCENE := preload("res://scenes/ui/boss_healthbar.tscn")
const DEATH_SCREEN_SCENE := preload("res://scenes/ui/death_screen.tscn")
const PLAYER_STATS_SCRIPT := preload("res://scripts/player/player_stats.gd")
const FLASK_SCRIPT := preload("res://scripts/player/flask.gd")
const BOSS_STATS_SCRIPT := preload("res://scripts/bosses/boss_stats.gd")
const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const FRAME_CAP := 720
const PLAYER_TEST_DAMAGE := 60 # Existing SPEC.txt Section 3 light-attack damage; test stimulus only.
const BOSS_TEST_DAMAGE := 110 # Existing SPEC.txt Section 3 heavy-attack damage; test stimulus only.

var _original_max_fps: int
var _restart_requested_received: bool = false


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_original_max_fps = Engine.max_fps
	Engine.max_fps = 120
	Engine.time_scale = 1.0
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	var hud := HUD_SCENE.instantiate() as CombatHud
	var boss_ui := BOSS_UI_SCENE.instantiate() as BossHealthbar
	var death_screen := DEATH_SCREEN_SCENE.instantiate() as DeathScreen
	var player_stats := PLAYER_STATS_SCRIPT.new() as PlayerStats
	var flask := FLASK_SCRIPT.new() as Flask
	var boss_stats := BOSS_STATS_SCRIPT.new() as BossStats
	root.add_child(hud)
	root.add_child(boss_ui)
	root.add_child(death_screen)
	root.add_child(player_stats)
	root.add_child(flask)
	root.add_child(boss_stats)
	await process_frame
	hud.bind_player_stats(player_stats)
	hud.bind_flask(flask)
	boss_ui.bind_boss_stats(boss_stats)
	death_screen.bind_player_stats(player_stats)
	if not _assert_spec_layout_and_colors(hud, boss_ui, death_screen, tunables):
		return

	var boss_name_font := boss_ui.get_boss_name_font()
	if boss_name_font == null or "Cinzel" not in boss_name_font.resource_path:
		_fail("boss name does not use the imported Cinzel font")
		return
	var boss_title_font := boss_ui.get_boss_title_font()
	if not boss_title_font is FontVariation:
		_fail("boss title does not use a FontVariation for italic and spacing")
		return
	var title_variation := boss_title_font as FontVariation
	if title_variation.base_font == null or "Cinzel" not in title_variation.base_font.resource_path:
		_fail("boss title FontVariation is not based on the imported Cinzel font")
		return
	var expected_italic_transform := Transform2D(
		Vector2(1.0, 0.0),
		Vector2(-tunables.ui_boss_name_line_2_italic_shear, 1.0),
		Vector2.ZERO
	)
	if title_variation.variation_transform != expected_italic_transform:
		_fail("boss title FontVariation does not use the configured italic shear")
		return
	if title_variation.spacing_glyph != tunables.ui_boss_name_line_2_glyph_spacing:
		_fail("boss title FontVariation does not use the configured glyph spacing")
		return
	if boss_ui.get_boss_name_color() != tunables.ui_boss_name_line_1_color:
		_fail("boss name does not use the configured gold-tinted font color")
		return
	var death_font := death_screen.get_death_label_font()
	if death_font == null or "Cinzel" not in death_font.resource_path:
		_fail("death label does not use the imported Cinzel font")
		return

	var dragon_bar := boss_ui.get_dragon_healthbar()
	if dragon_bar == null or dragon_bar.is_visible_bar():
		_fail("Dragon's Memory secondary HP bar did not start hidden")
		return
	dragon_bar.set_hp(50.0, 100.0)
	dragon_bar.show_bar()
	if not dragon_bar.is_visible_bar() or not is_equal_approx(dragon_bar.get_bar_value(), 50.0):
		_fail("Dragon's Memory secondary HP bar did not show and update")
		return
	dragon_bar.hide_bar()
	if dragon_bar.is_visible_bar():
		_fail("Dragon's Memory secondary HP bar did not hide")
		return

	player_stats.take_damage(PLAYER_TEST_DAMAGE)
	if not await _wait_until(func() -> bool: return is_equal_approx(hud.get_hp_bar_value(), float(player_stats.hp))):
		_fail("player HP bar did not track hp_changed")
		return
	if not player_stats.spend_stamina(float(tunables.stamina_cost_light_attack)):
		_fail("test setup could not spend player stamina")
		return
	if not await _wait_until(func() -> bool: return is_equal_approx(hud.get_stamina_bar_value(), player_stats.stamina)):
		_fail("player stamina bar did not track stamina_changed")
		return
	if not is_equal_approx(hud.get_fp_bar_value(), float(player_stats.fp)):
		_fail("static FP display did not read PlayerStats.fp")
		return
	if hud.get_flask_count() != flask.charges or hud.get_flask_icon_alpha() < 0.99:
		_fail("flask display did not bind at full count and brightness")
		return
	for _charge: int in tunables.flask_count:
		if not flask.begin_drink():
			_fail("test setup could not consume a real flask charge")
			return
		flask.cancel_drink()
	if hud.get_flask_count() != 0 or hud.get_flask_icon_alpha() >= 1.0:
		_fail("flask_changed did not dim the icon at zero charges")
		return
	flask.refill()
	if hud.get_flask_count() != tunables.flask_count or hud.get_flask_icon_alpha() < 0.99:
		_fail("flask_changed did not restore full count and brightness")
		return

	boss_stats.take_damage(BOSS_TEST_DAMAGE, DamageTypes.Type.PHYSICAL)
	if not await _wait_until(func() -> bool: return is_equal_approx(boss_ui.get_bar_value(), float(boss_stats.hp))):
		_fail("boss HP bar did not track hp_changed")
		return

	Engine.time_scale = 0.0
	boss_ui.start_intro()
	if boss_ui.get_name_card_alpha() > 0.0 or boss_ui.get_bar_alpha() > 0.0:
		_fail("boss intro did not begin fully hidden")
		return
	if not await _wait_until(func() -> bool: return boss_ui.get_name_card_alpha() > 0.05):
		_fail("boss name card did not begin fading after its SPEC delay")
		return
	if boss_ui.get_bar_alpha() > 0.0:
		_fail("boss HP bar began fading before the name card completed")
		return
	if not await _wait_until(func() -> bool: return boss_ui.is_name_card_visible()):
		_fail("boss name-card intro stalled at time_scale=0")
		return
	if not await _wait_until(func() -> bool: return boss_ui.is_bar_visible()):
		_fail("boss HP bar fade stalled at time_scale=0")
		return

	_restart_requested_received = false
	death_screen.restart_requested.connect(_on_restart_requested)
	player_stats.take_damage(player_stats.hp, DamageTypes.Type.PHYSICAL)
	if not death_screen.visible:
		_fail("player died signal did not make the death screen visible")
		return
	if not await _wait_until(func() -> bool: return death_screen.get_is_death_text_visible()):
		_fail("death screen did not reach visible text at time_scale=0")
		return
	if death_screen.get_black_overlay_alpha() < 0.99:
		_fail("death screen text appeared before the black fade completed")
		return
	if not await _wait_until(func() -> bool: return _restart_requested_received):
		_fail("death screen did not request a current-phase restart after its hold")
		return

	Engine.time_scale = 1.0
	hud.queue_free()
	boss_ui.queue_free()
	death_screen.queue_free()
	player_stats.queue_free()
	flask.queue_free()
	boss_stats.queue_free()
	Engine.max_fps = _original_max_fps
	print("PASS test_hud")
	quit(0)


func _assert_spec_layout_and_colors(hud: CombatHud, boss_ui: BossHealthbar, death_screen: DeathScreen, tunables: Tunables) -> bool:
	if not is_equal_approx(tunables.ui_boss_name_delay, 0.5) or not is_equal_approx(tunables.ui_boss_name_fade_duration, 0.6):
		return _fail_check("boss intro timing does not match SPEC 0.5s delay/0.6s fade")
	if not is_equal_approx(tunables.death_delay, 0.8) or not is_equal_approx(tunables.death_screen_fade_duration, 0.5) or not is_equal_approx(tunables.death_text_fade_duration, 0.5) or not is_equal_approx(tunables.death_text_hold_duration, 2.5):
		return _fail_check("death timeline tunables do not match SPEC 0.8/0.5/0.5/2.5s")
	if tunables.ui_player_hp_color != Color("c00000") or tunables.ui_player_hp_background_color != Color("1a0000") or tunables.ui_player_hp_border_color != Color("000000"):
		return _fail_check("player HP colors do not match SPEC #C00000/#1A0000/#000000")
	if tunables.ui_player_fp_color != Color("0050a0") or tunables.ui_player_stamina_color != Color("7a9a20") or tunables.ui_boss_hp_color != Color("c00000"):
		return _fail_check("FP/stamina/boss fill colors do not match SPEC #0050A0/#7A9A20/#C00000")
	if tunables.ui_death_text_color != Color("c8986e"):
		return _fail_check("death text color does not match SPEC #C8986E")
	if not _assert_unscaled_nodes(boss_ui, death_screen):
		return false
	var hp_bar := hud.get_node("HPBar") as ProgressBar
	var fp_bar := hud.get_node("FPBar") as ProgressBar
	var stamina_bar := hud.get_node("StaminaBar") as ProgressBar
	var flask_display := hud.get_node("FlaskDisplay") as Control
	if not _control_offsets_match(hp_bar, 40.0, -94.0, 320.0, -80.0):
		return _fail_check("player HP bar does not match SPEC 40px/80px/280x14 layout")
	if not _control_offsets_match(fp_bar, 40.0, -72.0, 240.0, -62.0):
		return _fail_check("player FP bar does not match SPEC 8px gap/200x10 layout")
	if not _control_offsets_match(stamina_bar, 40.0, -54.0, 280.0, -44.0):
		return _fail_check("player stamina bar does not match SPEC 8px gap/240x10 layout")
	if not is_equal_approx(flask_display.offset_left, 40.0) or not is_equal_approx(flask_display.offset_top, -32.0):
		return _fail_check("flask display does not begin 12px below stamina")
	if not _bar_colors_match(hp_bar, tunables.ui_player_hp_background_color, tunables.ui_player_hp_color):
		return _fail_check("player HP colors do not match SPEC Section 14")
	var hp_background := hp_bar.get_theme_stylebox("background") as StyleBoxFlat
	if hp_background.border_color != tunables.ui_player_hp_border_color:
		return _fail_check("player HP border is not SPEC black")
	if not _bar_colors_match(fp_bar, tunables.ui_player_secondary_bar_background_color, tunables.ui_player_fp_color):
		return _fail_check("player FP fill color does not match SPEC Section 14")
	if not _bar_colors_match(stamina_bar, tunables.ui_player_secondary_bar_background_color, tunables.ui_player_stamina_color):
		return _fail_check("player stamina fill color does not match SPEC Section 14")
	var boss_bar := boss_ui.get_node("BossHPBar") as ProgressBar
	if not _control_offsets_match(boss_bar, -300.0, -54.0, 300.0, -40.0):
		return _fail_check("boss HP bar does not match SPEC center/40px/600x14 layout")
	if not _bar_colors_match(boss_bar, tunables.ui_boss_hp_background_color, tunables.ui_boss_hp_color):
		return _fail_check("boss HP fill color does not match SPEC Section 14")
	if (boss_ui.get_node("NameCard/BossName") as Label).text != "GODWYN THE GOLDEN":
		return _fail_check("boss name card line 1 is not the exact SPEC string")
	if (boss_ui.get_node("NameCard/BossTitle") as Label).text != "Prince of Gold":
		return _fail_check("boss name card line 2 is not the exact SPEC string")
	if (boss_ui.get_node("NameCard/BossName") as Label).get_theme_font_size("font_size") != 28 or (boss_ui.get_node("NameCard/BossTitle") as Label).get_theme_font_size("font_size") != 16:
		return _fail_check("boss name card does not use the SPEC 28pt/16pt sizes")
	var death_label := death_screen.get_node("DeathLabel") as Label
	if death_label.text != "YOU DIED" or death_label.get_theme_color("font_color") != tunables.ui_death_text_color:
		return _fail_check("death text or #C8986E color does not match SPEC")
	if death_label.horizontal_alignment != HORIZONTAL_ALIGNMENT_CENTER or death_label.vertical_alignment != VERTICAL_ALIGNMENT_CENTER:
		return _fail_check("death text is not centered")
	return true


func _assert_unscaled_nodes(boss_ui: BossHealthbar, death_screen: DeathScreen) -> bool:
	if boss_ui.process_mode != Node.PROCESS_MODE_ALWAYS or death_screen.process_mode != Node.PROCESS_MODE_ALWAYS:
		return _fail_check("boss/death UI roots are not PROCESS_MODE_ALWAYS")
	var intro_delay := boss_ui.get_node("IntroDelay") as Timer
	var death_delay := death_screen.get_node("DeathDelay") as Timer
	var hold_timer := death_screen.get_node("HoldTimer") as Timer
	for timer: Timer in [intro_delay, death_delay, hold_timer]:
		if timer.process_mode != Node.PROCESS_MODE_ALWAYS or not timer.ignore_time_scale:
			return _fail_check("UI sequence timer is not PROCESS_MODE_ALWAYS with ignore_time_scale")
	return true


func _control_offsets_match(control: Control, left: float, top: float, right: float, bottom: float) -> bool:
	return is_equal_approx(control.offset_left, left) and is_equal_approx(control.offset_top, top) and is_equal_approx(control.offset_right, right) and is_equal_approx(control.offset_bottom, bottom)


func _bar_colors_match(bar: ProgressBar, background_color: Color, fill_color: Color) -> bool:
	var background := bar.get_theme_stylebox("background") as StyleBoxFlat
	var fill := bar.get_theme_stylebox("fill") as StyleBoxFlat
	return background != null and fill != null and background.bg_color == background_color and fill.bg_color == fill_color


func _fail_check(reason: String) -> bool:
	_fail(reason)
	return false


func _on_restart_requested() -> void:
	_restart_requested_received = true


func _wait_until(predicate: Callable) -> bool:
	for _frame: int in FRAME_CAP:
		if predicate.call():
			return true
		await process_frame
	return predicate.call()


func _fail(reason: String) -> void:
	Engine.time_scale = 1.0
	Engine.max_fps = _original_max_fps
	print("FAIL test_hud: %s" % reason)
	quit(1)
