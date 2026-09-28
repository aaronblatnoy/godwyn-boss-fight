extends SceneTree


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene_resource: Resource = load("res://scenes/main.tscn")
	if not packed_scene_resource is PackedScene:
		_fail("main scene did not load as PackedScene")
		return

	var packed_scene: PackedScene = packed_scene_resource as PackedScene
	var instance: Node = packed_scene.instantiate()
	if instance == null or not instance is Node3D:
		_fail("main scene root is not a valid Node3D")
		return

	root.add_child(instance)
	await process_frame

	var world_environment := instance.get_node_or_null("WorldEnvironment") as WorldEnvironment
	if world_environment == null or world_environment.environment == null:
		_fail("main scene is missing its WorldEnvironment resource")
		return
	var environment := world_environment.environment
	var environment_expected := {
		"glow_enabled": true,
		"glow_intensity": 0.6,
		"glow_hdr_threshold": 0.85,
		"glow_levels/3": 1.0,
		"adjustment_enabled": true,
		"adjustment_brightness": 0.95,
		"adjustment_contrast": 1.1,
		"adjustment_saturation": 0.8,
	}
	for property_name: String in environment_expected:
		var actual: Variant = environment.get(property_name)
		var wanted: Variant = environment_expected[property_name]
		if wanted is float:
			if not is_equal_approx(actual, wanted):
				_fail("Environment %s expected %s, got %s" % [property_name, wanted, actual])
				return
		elif actual != wanted:
			_fail("Environment %s expected %s, got %s" % [property_name, wanted, actual])
			return

	var tunables_script := load("res://scripts/systems/tunables.gd")
	if not tunables_script is GDScript:
		_fail("tunables.gd did not load as GDScript")
		return

	var tunables: Resource = tunables_script.new()
	var expected := {
		"player_max_hp": 500,
		"player_max_stamina": 100,
		"player_max_fp": 80,
		"player_walk_speed": 3.5,
		"player_sprint_speed": 6.5,
		"player_rotation_speed_degrees": 720.0,
		"player_lockon_strafe_speed": 3.5,
		"player_mouse_sensitivity": 0.3,
		"flask_count": 5,
		"flask_heal": 180,
		"flask_animation_duration": 0.6,
		"flask_roll_cancel_time": 0.3,
		"death_delay": 0.8,
		"death_screen_fade_duration": 0.5,
		"death_text_fade_duration": 0.5,
		"death_text_hold_duration": 2.5,
		"stamina_cost_light_attack": 12,
		"stamina_cost_heavy_attack": 22,
		"stamina_cost_roll": 12,
		"stamina_cost_sprint_per_second": 5.0,
		"stamina_recovery_delay": 0.8,
		"stamina_recovery_rate": 25.0,
		"roll_distance": 3.5,
		"roll_duration": 0.65,
		"roll_iframe_start_frame": 4,
		"roll_iframe_end_frame": 16,
		"roll_iframe_start_seconds": 0.2,
		"roll_iframe_end_seconds": 0.4,
		"light_attack_damage": 60,
		"light_attack_active_start": 0.15,
		"light_attack_active_end": 0.35,
		"light_attack_recovery": 0.4,
		"light_attack_hitstop": 0.06,
		"light_attack_poise_damage": 15.0,
		"heavy_attack_damage": 110,
		"heavy_attack_telegraph": 0.4,
		"heavy_attack_active_start": 0.2,
		"heavy_attack_active_end": 0.55,
		"heavy_attack_recovery": 0.7,
		"heavy_attack_hitstop": 0.1,
		"heavy_attack_poise_damage_multiplier": 2.0,
		"lockon_max_range": 25.0,
		"lockon_break_range": 35.0,
		"lockon_break_grace_seconds": 2.0,
		"lockon_camera_lerp": 8.0,
		"boss_max_hp": 3000,
		"boss_poise": 80,
		"boss_stagger_duration": 0.8,
		"lightning_unlock_hp_percent": 0.5,
		"lightning_threshold_tell_duration": 1.5,
		"lightning_pattern_marker_warning": 0.6,
		"lightning_pattern_strike_interval": 0.2,
		"lightning_targeted_strike_count_min": 3,
		"lightning_targeted_strike_count_max": 5,
		"lightning_targeted_strike_interval": 0.4,
		"lightning_mid_melee_warning": 0.25,
		"lightning_stationary_trigger_time": 0.5,
		"lightning_horizontal_sweep_tell": 0.5,
		"lightning_shrinking_circle_warning": 0.8,
		"lightning_shrinking_circle_hold": 2.0,
		"lightning_shrinking_circle_start_radius": 15.0,
		"lightning_shrinking_circle_end_radius": 4.0,
		"lightning_shrinking_circle_contraction_speed": 1.5,
		"lightning_shrinking_circle_contraction_duration": 7.0,
		"lightning_dragons_charge_fire_line_width": 4.0,
		"lightning_slam_aoe_radius": 8.0,
		"hitstop_time_scale": 0.05,
	}

	for property_name: String in expected:
		var actual: Variant = tunables.get(property_name)
		var wanted: Variant = expected[property_name]
		if wanted is float:
			if not is_equal_approx(actual, wanted):
				_fail("%s expected %s, got %s" % [property_name, wanted, actual])
				return
		elif actual != wanted:
			_fail("%s expected %s, got %s" % [property_name, wanted, actual])
			return

	instance.queue_free()
	print("PASS test_boot")
	quit(0)


func _fail(reason: String) -> void:
	print("FAIL test_boot: %s" % reason)
	quit(1)
