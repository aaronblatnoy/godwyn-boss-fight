extends SceneTree


const AI_SCRIPT := preload("res://scripts/bosses/godwyn_p1_ai.gd")
const BOSS_BASE_SCRIPT := preload("res://scripts/bosses/boss_base.gd")
const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const DISTRIBUTION_SEED := 5105 # TEST HARNESS VALUE -- deterministic regression seed.
const RUNTIME_SEED := 8128 # TEST HARNESS VALUE -- deterministic regression seed.
const DISTRIBUTION_SAMPLES := 1000 # TEST HARNESS VALUE -- stable statistical sample count.
const DISTRIBUTION_TOLERANCE := 0.06 # TEST HARNESS VALUE -- six percentage-point statistical tolerance.
const WEIGHT_EPSILON := 0.001 # TEST HARNESS VALUE -- float-comparison tolerance for literal SPEC weights.
const DAMAGE_TOLERANCE := 1 # TEST HARNESS VALUE -- permits natural integer rounding of the 1.25x buff.
const MOVEMENT_EPSILON := 0.001 # TEST HARNESS VALUE -- rejects a missing circling or closing component.
const FACING_DOT_MINIMUM := 0.999 # TEST HARNESS VALUE -- verifies -Z faces the planar player direction.
const SYNTHETIC_DELTA := 0.05 # TEST HARNESS VALUE -- deterministic manual simulation step.
const COUNTER_DELTA := 0.01 # TEST HARNESS VALUE -- resolves the SPEC 0.12s counter precisely.
const TIME_EPSILON := 0.051 # TEST HARNESS VALUE -- one synthetic step plus float tolerance.
const SIMULATED_SECONDS := 90.0 # TEST HARNESS VALUE -- enough for many complete attack cycles.
const BAND_SWITCH_SECONDS := 30.0 # TEST HARNESS VALUE -- equal coverage of all three bands.
const CONTROL_FRAME_CAP := 160 # TEST HARNESS VALUE -- safety cap for an uncountered Pause simulation.
const EXPECTED_WEIGHT_SLOT_COUNT := 6 # Phase 5 contract: six auditable slots per distance band.
const LATCH_PROBE_DAMAGE := 1 # TEST HARNESS VALUE -- damage below a crossed threshold must not retrigger it.
const MEMORY_COOLDOWN_SEED := 1447 # TEST HARNESS VALUE -- deterministic transition-time verification.
const CLOSE_DISTANCE := 3.0 # SPEC Section 6 representative close distance required by the plan.
const MID_DISTANCE := 7.0 # SPEC Section 6 representative mid distance required by the plan.
const FAR_DISTANCE := 12.0 # SPEC Section 6 representative far distance required by the plan.
const SPEC_SLOT_WEIGHTS := {
	# SPEC.txt line 407: literal close-band named weights.
	"close": {
		"Sovereign's Sequence": 45.0,
		"The Tide": 25.0,
		"Radiant Sequence": 20.0,
		"Dash Chain": 0.0,
		"Dragon's Memory": 0.0,
		"The Pause": 10.0,
	},
	# SPEC.txt lines 409-410: literal mid-band named weights.
	"mid": {
		"Sovereign's Sequence": 25.0,
		"Sacred Cleave": 15.0,
		"Radiant Sequence": 0.0,
		"Dash Chain": 35.0,
		"Dragon's Memory": 20.0,
		"The Pause": 5.0,
	},
	# SPEC.txt line 411: literal far-band named weights.
	"far": {
		"Sovereign's Sequence": 0.0,
		"The Tide": 0.0,
		"Radiant Sequence": 0.0,
		"Dash Chain": 55.0,
		"Dragon's Memory": 30.0,
		"The Pause": 15.0,
	},
} # SPEC.txt Section 6 literal named percentages, before resource mapping.


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var distribution_rig := await _make_rig(MID_DISTANCE)
	if not _test_weight_sums(distribution_rig):
		return
	if not _test_distributions(distribution_rig):
		return
	await _free_rig(distribution_rig)

	if not await _test_idle_circling_and_facing():
		return
	if not await _test_idle_time_cap():
		return
	if not await _test_pause_counter():
		return
	if not await _test_memory_fragment():
		return

	print("PASS test_boss_ai")
	quit(0)


func _test_weight_sums(rig: Dictionary) -> bool:
	var ai := rig.ai as GodwynP1AI
	var boss := rig.boss as BossBase
	var player := rig.player as Node3D
	var cases: Array[Dictionary] = [
		{"band": "close", "distance": CLOSE_DISTANCE},
		{"band": "mid", "distance": MID_DISTANCE},
		{"band": "far", "distance": FAR_DISTANCE},
	]
	for case_data: Dictionary in cases:
		var band: String = str(case_data.band)
		var distance: float = float(case_data.distance)
		player.global_position = boss.global_position + Vector3(distance, 0.0, 0.0)
		var actual_distance := boss.global_position.distance_to(player.global_position)
		var table := ai.build_weight_table(actual_distance)
		var total := 0.0
		if table.size() != EXPECTED_WEIGHT_SLOT_COUNT:
			_fail("distance %.1f did not produce all six SPEC weight slots" % distance)
			return false
		var actual_spec_weights := {}
		for entry: Dictionary in table:
			total += float(entry.get("weight", 0.0))
			var spec_name := str(entry.get("spec_name", ""))
			if actual_spec_weights.has(spec_name):
				_fail("distance %.1f duplicated SPEC slot %s" % [distance, spec_name])
				return false
			actual_spec_weights[spec_name] = float(entry.get("weight", 0.0))
		if absf(total - 100.0) > WEIGHT_EPSILON:
			_fail("distance %.1f weights sum to %.3f instead of 100.0" % [distance, total])
			return false
		var expected: Dictionary = SPEC_SLOT_WEIGHTS[band]
		for spec_name: String in expected:
			if not actual_spec_weights.has(spec_name):
				_fail("distance %.1f omitted SPEC slot %s" % [distance, spec_name])
				return false
			var actual_weight := float(actual_spec_weights[spec_name])
			var expected_weight := float(expected[spec_name])
			if absf(actual_weight - expected_weight) > WEIGHT_EPSILON:
				_fail(
					"distance %.1f %s weight %.3f did not match SPEC %.3f" % [
						distance,
						spec_name,
						actual_weight,
						expected_weight,
					]
				)
				return false
	return true


func _test_distributions(rig: Dictionary) -> bool:
	var ai := rig.ai as GodwynP1AI
	var boss := rig.boss as BossBase
	var player := rig.player as Node3D
	# SPEC Sections 6/7 resolved onto Phase 4's five canonical initiators.
	var cases: Array[Dictionary] = [
		{
			"distance": CLOSE_DISTANCE,
			"expected": {
				"x_combo": 0.65,
				"horizontal_sweep": 0.25,
				"jump_lunge": 0.0,
				"dragons_memory": 0.0,
				"the_pause": 0.10,
			},
		},
		{
			"distance": MID_DISTANCE,
			"expected": {
				"x_combo": 0.25,
				"horizontal_sweep": 0.15,
				"jump_lunge": 0.35,
				"dragons_memory": 0.20,
				"the_pause": 0.05,
			},
		},
		{
			"distance": FAR_DISTANCE,
			"expected": {
				"x_combo": 0.0,
				"horizontal_sweep": 0.0,
				"jump_lunge": 0.55,
				"dragons_memory": 0.30,
				"the_pause": 0.15,
			},
		},
	]
	for case_data: Dictionary in cases:
		var distance: float = float(case_data.distance)
		player.global_position = boss.global_position + Vector3(distance, 0.0, 0.0)
		var actual_distance := boss.global_position.distance_to(player.global_position)
		var expected: Dictionary = case_data.expected
		var counts := {
			"x_combo": 0,
			"horizontal_sweep": 0,
			"jump_lunge": 0,
			"dragons_memory": 0,
			"the_pause": 0,
		}
		var rng := RandomNumberGenerator.new()
		rng.seed = DISTRIBUTION_SEED
		for _sample: int in DISTRIBUTION_SAMPLES:
			var attack_id := ai.pick_weighted_initiator(actual_distance, rng)
			if not counts.has(attack_id):
				_fail("distance %.1f selected non-canonical initiator %s" % [distance, attack_id])
				return false
			counts[attack_id] = int(counts[attack_id]) + 1
		for attack_id: String in counts:
			var observed := float(counts[attack_id]) / float(DISTRIBUTION_SAMPLES)
			var target := float(expected[attack_id])
			if absf(observed - target) > DISTRIBUTION_TOLERANCE:
				_fail(
					"distance %.1f %s frequency %.3f missed expected %.3f" % [
						distance,
						attack_id,
						observed,
						target,
					]
				)
				return false
	return true


func _test_idle_circling_and_facing() -> bool:
	var rig := await _make_rig(MID_DISTANCE)
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var player := rig.player as Node3D
	boss.set_process(false)
	ai.set_process(false)
	ai.set_physics_process(false)
	var start_position := boss.global_position
	ai._physics_process(SYNTHETIC_DELTA)
	var displacement := boss.global_position - start_position
	if displacement.x <= MOVEMENT_EPSILON:
		_fail("IDLE mobility did not close distance toward the player")
		return false
	if absf(displacement.z) <= MOVEMENT_EPSILON:
		_fail("IDLE mobility beelined instead of adding a circling component")
		return false
	if is_zero_approx(ai._last_angle_to_player):
		_fail("perception did not retain the signed angle to the player")
		return false
	var forward_3d := -boss.global_transform.basis.z
	var forward := Vector2(forward_3d.x, forward_3d.z).normalized()
	var player_offset := player.global_position - boss.global_position
	var toward_player := Vector2(player_offset.x, player_offset.z).normalized()
	if forward.dot(toward_player) < FACING_DOT_MINIMUM:
		_fail("boss did not face the player after IDLE circling movement")
		return false
	await _free_rig(rig)
	return true


func _test_idle_time_cap() -> bool:
	var rig := await _make_rig(CLOSE_DISTANCE)
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var player := rig.player as Node3D
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	boss._rng.seed = RUNTIME_SEED
	boss.set_process(false)
	ai.set_process(false)
	ai.set_physics_process(false)

	var clock := {"seconds": 0.0}
	var idle_tracker := {"entered_at": 0.0, "maximum": 0.0}
	var pause_seen := {"value": false}
	var attack_count := {"value": 0}
	boss.state_changed.connect(func(old_state: BossBase.State, new_state: BossBase.State) -> void:
		if old_state == BossBase.State.IDLE:
			idle_tracker.maximum = maxf(
				float(idle_tracker.maximum),
				float(clock.seconds) - float(idle_tracker.entered_at)
			)
		if new_state == BossBase.State.IDLE:
			idle_tracker.entered_at = float(clock.seconds)
	)
	boss.attack_started.connect(func(attack_id: String) -> void:
		attack_count.value = int(attack_count.value) + 1
		if attack_id == "the_pause":
			pause_seen.value = true
	)

	# Force one Pause into the otherwise seeded multi-cycle simulation so the
	# documented stillness exception is exercised rather than left to chance.
	boss.run_attack(boss.attack_library.get_attack("the_pause"))
	while float(clock.seconds) < SIMULATED_SECONDS:
		var band_index := mini(
			int(float(clock.seconds) / BAND_SWITCH_SECONDS),
			2
		)
		var distance: float = [CLOSE_DISTANCE, MID_DISTANCE, FAR_DISTANCE][band_index]
		player.global_position = boss.global_position + Vector3(distance, 0.0, 0.0)
		ai._physics_process(SYNTHETIC_DELTA)
		boss.animation_player.advance(SYNTHETIC_DELTA)
		boss._process(SYNTHETIC_DELTA)
		ai._process(SYNTHETIC_DELTA)
		clock.seconds = float(clock.seconds) + SYNTHETIC_DELTA
	if boss.current_state == BossBase.State.IDLE:
		idle_tracker.maximum = maxf(
			float(idle_tracker.maximum),
			float(clock.seconds) - float(idle_tracker.entered_at)
		)
	if float(idle_tracker.maximum) > tunables.boss_max_stillness_seconds + TIME_EPSILON:
		_fail("IDLE dwell reached %.3fs" % float(idle_tracker.maximum))
		return false
	if not bool(pause_seen.value):
		_fail("manual attack-cycle simulation never exercised The Pause exception")
		return false
	if int(attack_count.value) < 10:
		_fail("manual simulation completed too few attack cycles: %d" % int(attack_count.value))
		return false
	await _free_rig(rig)
	return true


func _test_pause_counter() -> bool:
	var control_rig := await _make_rig(MID_DISTANCE)
	var control_boss := control_rig.boss as BossBase
	var control_ai := control_rig.ai as GodwynP1AI
	control_boss.set_process(false)
	control_ai.set_process(false)
	control_ai.set_physics_process(false)
	control_boss.run_attack(control_boss.attack_library.get_attack("the_pause"))
	control_boss._process(0.0)
	var control_duration := control_boss.get_current_attack().recovery_time
	if control_duration <= TUNABLES_SCRIPT.new().boss_pause_counter_delay:
		_fail("seeded Pause duration was not longer than its counter delay")
		return false
	var control_elapsed := 0.0
	for _frame: int in CONTROL_FRAME_CAP:
		control_boss.animation_player.advance(SYNTHETIC_DELTA)
		control_boss._process(SYNTHETIC_DELTA)
		control_ai._process(SYNTHETIC_DELTA)
		control_elapsed += SYNTHETIC_DELTA
		var current_control_attack := control_boss.get_current_attack()
		if current_control_attack == null or current_control_attack.id != "the_pause":
			break
	if control_boss.get_current_attack() != null and control_boss.get_current_attack().id == "the_pause":
		_fail("uncountered Pause did not complete within the deterministic safety cap")
		return false
	if control_elapsed < control_duration:
		_fail("uncountered Pause ended before its randomized duration")
		return false
	await _free_rig(control_rig)

	var counter_rig := await _make_rig(MID_DISTANCE)
	var counter_boss := counter_rig.boss as BossBase
	var counter_ai := counter_rig.ai as GodwynP1AI
	counter_boss.set_process(false)
	counter_ai.set_process(false)
	counter_ai.set_physics_process(false)
	counter_boss.run_attack(counter_boss.attack_library.get_attack("the_pause"))
	counter_boss._process(0.0)
	var position_before_counter := counter_boss.global_position
	counter_ai.report_player_attack()
	var counter_elapsed := 0.0
	while counter_elapsed < TUNABLES_SCRIPT.new().boss_pause_counter_delay + COUNTER_DELTA:
		counter_ai._process(COUNTER_DELTA)
		counter_elapsed += COUNTER_DELTA
		var current_attack := counter_boss.get_current_attack()
		if current_attack != null and current_attack.id != "the_pause":
			break
	var counter_attack := counter_boss.get_current_attack()
	if counter_attack == null or counter_attack.id == "the_pause":
		_fail("report_player_attack did not cut The Pause within the 0.12s counter window")
		return false
	if counter_elapsed >= control_elapsed:
		_fail("countered Pause was not measurably shorter than the full wait")
		return false
	if counter_elapsed > TUNABLES_SCRIPT.new().boss_pause_counter_delay + COUNTER_DELTA:
		_fail("Pause counter took %.3fs" % counter_elapsed)
		return false
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	var offline_distance := counter_boss.global_position.distance_to(position_before_counter)
	if absf(offline_distance - tunables.boss_pause_counter_step_distance) > MOVEMENT_EPSILON:
		_fail("Pause counter did not take its offline reposition step")
		return false
	if absf(counter_boss.state_timer) > WEIGHT_EPSILON:
		_fail("Pause counter retained a telegraph instead of beginning immediately")
		return false
	if counter_attack.telegraph_time <= 0.0:
		_fail("Pause counter did not restore the shared AttackData telegraph")
		return false
	await _free_rig(counter_rig)
	return true


func _test_memory_fragment() -> bool:
	var rig := await _make_rig(MID_DISTANCE)
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	boss.set_process(false)
	ai.set_process(false)
	ai.set_physics_process(false)
	boss.auto_select_attacks = false
	var attack := boss.attack_library.get_attack("x_combo")
	if attack == null:
		_fail("Memory Fragment test could not resolve x_combo")
		return false
	var thresholds: Array[float] = [
		tunables.boss_memory_fragment_threshold_75,
		tunables.boss_memory_fragment_threshold_50,
		tunables.boss_memory_fragment_threshold_25,
	]
	for threshold_index: int in thresholds.size():
		# Begin an unbuffed attack first so crossing happens mid-cycle and the
		# immediately following attack can be compared against its own base hit.
		boss.run_attack(attack)
		var damage_before_threshold := boss.boss_hitbox.damage
		if damage_before_threshold != attack.damage:
			_fail("pre-threshold attack damage was not the AttackData base value")
			return false
		var target_hp := roundi(float(boss.boss_stats.max_hp) * thresholds[threshold_index])
		boss.boss_stats.take_damage(
			boss.boss_stats.hp - target_hp,
			DamageTypes.Type.PHYSICAL
		)
		if not ai.is_memory_fragment_active():
			_fail("Memory Fragment did not activate at threshold index %d" % threshold_index)
			return false
		if ai.get_memory_fragment_trigger_count() != threshold_index + 1:
			_fail("Memory Fragment threshold did not latch exactly once")
			return false
		boss.run_attack(attack)
		var expected_damage := roundi(
			float(attack.damage) * tunables.boss_memory_fragment_damage_multiplier
		)
		if absi(boss.boss_hitbox.damage - expected_damage) > DAMAGE_TOLERANCE:
			_fail(
				"post-threshold hit %d was not approximately 25%% above base %d" % [
					boss.boss_hitbox.damage,
					attack.damage,
				]
			)
			return false
		if boss.boss_hitbox.damage <= damage_before_threshold:
			_fail("post-threshold hit was not heavier than the preceding hit")
			return false
		var elapsed := 0.0
		while elapsed + SYNTHETIC_DELTA < tunables.boss_memory_fragment_duration:
			ai._process(SYNTHETIC_DELTA)
			elapsed += SYNTHETIC_DELTA
		if not ai.is_memory_fragment_active():
			_fail("Memory Fragment expired before its SPEC 10.0s duration")
			return false
		ai._process(SYNTHETIC_DELTA + TIME_EPSILON)
		if ai.is_memory_fragment_active():
			_fail("Memory Fragment remained active after its SPEC 10.0s duration")
			return false
		var trigger_count_before_probe := ai.get_memory_fragment_trigger_count()
		boss.boss_stats.take_damage(LATCH_PROBE_DAMAGE, DamageTypes.Type.PHYSICAL)
		if ai.is_memory_fragment_active():
			_fail("crossed Memory Fragment threshold retriggered after expiry")
			return false
		if ai.get_memory_fragment_trigger_count() != trigger_count_before_probe:
			_fail("crossed Memory Fragment threshold incremented twice")
			return false
	await _free_rig(rig)

	if not await _test_memory_fragment_transition_multiplier():
		return false
	return true


func _test_memory_fragment_transition_multiplier() -> bool:
	var rig := await _make_rig(MID_DISTANCE)
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	boss.set_process(false)
	ai.set_process(false)
	ai.set_physics_process(false)
	boss.auto_select_attacks = false
	var threshold_hp := roundi(
		float(boss.boss_stats.max_hp) * tunables.boss_memory_fragment_threshold_75
	)
	boss.boss_stats.take_damage(
		boss.boss_stats.hp - threshold_hp,
		DamageTypes.Type.PHYSICAL
	)
	var cooldown_rng := RandomNumberGenerator.new()
	cooldown_rng.seed = MEMORY_COOLDOWN_SEED
	boss._rng.seed = MEMORY_COOLDOWN_SEED
	var expected_unscaled_cooldown := cooldown_rng.randf_range(
		tunables.boss_global_cooldown_min,
		tunables.boss_global_cooldown_max
	)
	# Dragon's Memory is a canonical initiator with an authored IDLE exit, so
	# disabling auto-selection isolates exactly one cycle and its cooldown.
	boss.run_attack(boss.attack_library.get_attack("dragons_memory"))
	var frames := 0
	while boss.current_state != BossBase.State.IDLE and frames < CONTROL_FRAME_CAP:
		boss.animation_player.advance(SYNTHETIC_DELTA)
		boss._process(SYNTHETIC_DELTA)
		ai._process(SYNTHETIC_DELTA)
		frames += 1
	if boss.current_state != BossBase.State.IDLE:
		_fail("Memory Fragment transition test did not return to IDLE")
		return false
	var expected_scaled_cooldown := (
		expected_unscaled_cooldown
		* tunables.boss_memory_fragment_transition_time_multiplier
	)
	if absf(boss.state_timer - expected_scaled_cooldown) > WEIGHT_EPSILON:
		_fail(
			"Memory Fragment IDLE cooldown %.3f did not match scaled %.3f" % [
				boss.state_timer,
				expected_scaled_cooldown,
			]
		)
		return false
	await _free_rig(rig)
	return true


func _make_rig(player_distance: float) -> Dictionary:
	var boss := BOSS_BASE_SCRIPT.new() as BossBase
	root.add_child(boss)
	await process_frame
	var player := Node3D.new()
	player.name = "BossAITestPlayer"
	root.add_child(player)
	player.global_position = Vector3(player_distance, 0.0, 0.0)
	var ai := AI_SCRIPT.new() as GodwynP1AI
	ai.name = "GodwynP1AI"
	ai.boss = boss
	ai.player_target = player
	root.add_child(ai)
	await process_frame
	return {"boss": boss, "player": player, "ai": ai}


func _free_rig(rig: Dictionary) -> void:
	(rig.ai as Node).queue_free()
	(rig.player as Node).queue_free()
	(rig.boss as Node).queue_free()
	await process_frame


func _fail(reason: String) -> void:
	print("FAIL test_boss_ai: %s" % reason)
	quit(1)
