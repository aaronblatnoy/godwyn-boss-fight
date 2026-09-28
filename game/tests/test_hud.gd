extends SceneTree


const HUD_SCENE := preload("res://scenes/ui/hud.tscn")
const BOSS_UI_SCENE := preload("res://scenes/ui/boss_healthbar.tscn")
const DEATH_SCREEN_SCENE := preload("res://scenes/ui/death_screen.tscn")
const PLAYER_STATS_SCRIPT := preload("res://scripts/player/player_stats.gd")
const BOSS_STATS_SCRIPT := preload("res://scripts/bosses/boss_stats.gd")
const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const FRAME_CAP := 600
const PLAYER_TEST_DAMAGE := 60 # Existing SPEC.txt Section 3 light-attack damage; test stimulus only.
const BOSS_TEST_DAMAGE := 110 # Existing SPEC.txt Section 3 heavy-attack damage; test stimulus only.

var _original_max_fps: int


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
	var boss_stats := BOSS_STATS_SCRIPT.new() as BossStats
	root.add_child(hud)
	root.add_child(boss_ui)
	root.add_child(death_screen)
	root.add_child(player_stats)
	root.add_child(boss_stats)
	await process_frame
	hud.bind_player_stats(player_stats)
	boss_ui.bind_boss_stats(boss_stats)
	death_screen.bind_player_stats(player_stats)

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
	if hud.get_flask_count() != tunables.flask_count or hud.get_flask_icon_alpha() < 0.99:
		_fail("static flask display did not initialize at full count and brightness")
		return
	hud.set_flask_count(0)
	if hud.get_flask_count() != 0 or hud.get_flask_icon_alpha() >= 1.0:
		_fail("flask placeholder icon did not dim at zero")
		return
	hud.set_flask_count(tunables.flask_count)

	boss_stats.take_damage(BOSS_TEST_DAMAGE, DamageTypes.Type.PHYSICAL)
	if not await _wait_until(func() -> bool: return is_equal_approx(boss_ui.get_bar_value(), float(boss_stats.hp))):
		_fail("boss HP bar did not track hp_changed")
		return

	Engine.time_scale = tunables.hitstop_time_scale
	boss_ui.start_intro()
	if not await _wait_until(func() -> bool: return boss_ui.is_name_card_visible()):
		_fail("boss name-card intro stalled during simulated hitstop")
		return
	if not await _wait_until(func() -> bool: return boss_ui.is_bar_visible()):
		_fail("boss HP bar fade stalled during simulated hitstop")
		return

	player_stats.take_damage(player_stats.hp, DamageTypes.Type.PHYSICAL)
	if not await _wait_until(func() -> bool: return death_screen.get_is_death_text_visible()):
		_fail("death screen did not reach visible text during simulated hitstop")
		return
	if death_screen.get_black_overlay_alpha() < 0.99:
		_fail("death screen text appeared before the black fade completed")
		return

	Engine.time_scale = 1.0
	hud.queue_free()
	boss_ui.queue_free()
	death_screen.queue_free()
	player_stats.queue_free()
	boss_stats.queue_free()
	Engine.max_fps = _original_max_fps
	print("PASS test_hud")
	quit(0)


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
