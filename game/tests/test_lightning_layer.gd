extends SceneTree


const AI_SCRIPT := preload("res://scripts/bosses/godwyn_p1_ai.gd")
const BOSS_BASE_SCRIPT := preload("res://scripts/bosses/boss_base.gd")
const LIGHTNING_LAYER_SCRIPT := preload("res://scripts/bosses/lightning_layer.gd")
const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const SYNTHETIC_DELTA := 0.05 # TEST HARNESS VALUE -- deterministic manual physics step.
const PLAYER_DISTANCE := 7.0 # SPEC Section 6 representative mid-band distance.
const ABOVE_THRESHOLD_RATIO := 0.60 # TEST HARNESS VALUE -- independently above the 50% gate.
const BELOW_THRESHOLD_RATIO := 0.49 # TEST HARNESS VALUE -- exactly requested post-damage ratio.
const FLOAT_EPSILON := 0.0001 # TEST HARNESS VALUE -- resource/tunable float comparison.
const IDLE_LIGHTNING_IDS: Array[String] = [
	"lightning_placidusax_call",
	"lightning_targeted_strikes_standalone",
	"lightning_horizontal_sweep",
	"lightning_shrinking_circle",
	"lightning_dragons_charge",
]
const ALL_LIGHTNING_IDS: Array[String] = [
	"lightning_placidusax_call",
	"lightning_targeted_strikes_standalone",
	"lightning_targeted_strikes_mid_melee",
	"lightning_horizontal_sweep",
	"lightning_shrinking_circle",
	"lightning_dragons_charge",
	"lightning_slam_aoe",
]
const SMALL_STRIKE_IDS: Array[String] = [
	"lightning_placidusax_call",
	"lightning_targeted_strikes_standalone",
	"lightning_targeted_strikes_mid_melee",
]


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var rig := await _make_rig()
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var layer := rig.layer as LightningLayer
	var threshold_count := {"value": 0}
	layer.threshold_crossed.connect(func() -> void:
		threshold_count.value = int(threshold_count.value) + 1
	)

	ai._physics_process(SYNTHETIC_DELTA)
	var expected_melee_ids: Array[String] = []
	for attack_id: String in boss.moveset_tree.get_exits_for_state("IDLE"):
		if attack_id not in expected_melee_ids:
			expected_melee_ids.append(attack_id)
	layer.merge_runtime_initiators()
	if layer.is_unlocked():
		_fail("fresh full-HP rig unlocked lightning")
		return
	if not _assert_ids_absent(boss, IDLE_LIGHTNING_IDS, "full-HP pool"):
		return
	if not _assert_authored_and_locked_overhead_exits(boss):
		return

	var target_hp := roundi(float(boss.boss_stats.max_hp) * BELOW_THRESHOLD_RATIO)
	boss.boss_stats.take_damage(
		boss.boss_stats.hp - target_hp,
		DamageTypes.Type.PHYSICAL
	)
	if not layer.is_unlocked():
		_fail("49%-HP damage did not unlock lightning")
		return
	if not layer.is_threshold_tell_active():
		_fail("threshold-cross tell was not active at unlock")
		return
	if int(threshold_count.value) != 1:
		_fail("threshold-cross tell did not fire exactly once")
		return
	ai._physics_process(SYNTHETIC_DELTA)
	layer.merge_runtime_initiators()
	if not _assert_ids_present(boss, IDLE_LIGHTNING_IDS, "unlocked pool"):
		return
	if not _assert_ids_present(boss, expected_melee_ids, "unlocked melee pool"):
		return
	if not _assert_no_duplicates(boss):
		return

	var overhead := boss.attack_library.get_attack("overhead_slam")
	if overhead == null:
		_fail("runtime overhead_slam did not resolve")
		return
	var overhead_ids: Array[String] = []
	for option: Dictionary in overhead.exit_options:
		overhead_ids.append(str(option.get("attack_id", "")))
	if "flow_into_x" not in overhead_ids or "lightning_slam_aoe" not in overhead_ids:
		_fail("unlocked overhead_slam did not retain both ambiguous exits")
		return

	var tunables: Tunables = TUNABLES_SCRIPT.new()
	var placidusax := boss.attack_library.get_attack("lightning_placidusax_call")
	if placidusax == null:
		_fail("AttackLibrary did not load lightning_placidusax_call")
		return
	if placidusax.damage_type != DamageTypes.Type.LIGHT:
		_fail("Placidusax Call damage type was not LIGHT")
		return
	if absf(placidusax.telegraph_time - tunables.lightning_pattern_marker_warning) > FLOAT_EPSILON:
		_fail("Placidusax Call telegraph did not match its tunable marker warning")
		return
	var slam := boss.attack_library.get_attack("lightning_slam_aoe")
	if slam == null or slam.active_windows.is_empty():
		_fail("lightning_slam_aoe did not expose its ground-strike window")
		return
	if absf(
		float(slam.active_windows.front().get("radius", 0.0))
		- tunables.lightning_slam_aoe_radius
	) > FLOAT_EPSILON:
		_fail("slam AoE window radius did not match its tunable")
		return
	if not _assert_lightning_damage_contract(boss):
		return

	# Re-running both writers in one frame must retain one copy of each lightning
	# entry while leaving the SPEC-derived melee entries selectable.
	ai._physics_process(SYNTHETIC_DELTA)
	layer.merge_runtime_initiators()
	layer.merge_runtime_initiators()
	if not _assert_no_duplicates(boss):
		return
	boss.boss_stats.take_damage(1, DamageTypes.Type.PHYSICAL)
	if int(threshold_count.value) != 1:
		_fail("latched threshold-cross tell fired more than once")
		return

	await _free_rig(rig)

	var independent_rig := await _make_rig()
	var independent_boss := independent_rig.boss as BossBase
	var independent_ai := independent_rig.ai as GodwynP1AI
	var independent_layer := independent_rig.layer as LightningLayer
	var independent_target_hp := roundi(
		float(independent_boss.boss_stats.max_hp) * ABOVE_THRESHOLD_RATIO
	)
	independent_boss.boss_stats.take_damage(
		independent_boss.boss_stats.hp - independent_target_hp,
		DamageTypes.Type.PHYSICAL
	)
	independent_ai._physics_process(SYNTHETIC_DELTA)
	independent_layer.merge_runtime_initiators()
	if independent_layer.is_unlocked():
		_fail("independent 60%-HP rig inherited the first rig's unlock")
		return
	if not _assert_ids_absent(
		independent_boss,
		IDLE_LIGHTNING_IDS,
		"independent above-threshold pool"
	):
		return
	var independent_overhead := independent_boss.attack_library.get_attack("overhead_slam")
	if independent_overhead.exit_options.size() != 1:
		_fail("independent locked rig did not retain exactly one overhead exit")
		return
	for option: Dictionary in independent_overhead.exit_options:
		if str(option.get("attack_id", "")) == "lightning_slam_aoe":
			_fail("independent locked rig inherited the overhead lightning exit")
			return
	await _free_rig(independent_rig)

	if not await _assert_marker_lead_times_and_pruning():
		return
	if not await _assert_shrinking_circle_ring_geometry():
		return
	if not await _assert_horizontal_sweep_gap_geometry():
		return
	if not await _assert_dragons_charge_staging():
		return
	if not await _assert_lightning_followup_pools():
		return
	if not await _assert_small_strike_geometry():
		return
	if not await _assert_empty_clip_active_cycle():
		return

	print("PASS test_lightning_layer")
	quit(0)


func _assert_ids_present(boss: BossBase, expected: Array[String], context: String) -> bool:
	var actual := boss.moveset_tree.get_exits_for_state("IDLE")
	for attack_id: String in expected:
		if attack_id not in actual:
			_fail("%s omitted %s" % [context, attack_id])
			return false
	return true


func _assert_ids_absent(boss: BossBase, rejected: Array[String], context: String) -> bool:
	var actual := boss.moveset_tree.get_exits_for_state("IDLE")
	for attack_id: String in rejected:
		if attack_id in actual:
			_fail("%s unexpectedly contained %s" % [context, attack_id])
			return false
	return true


func _assert_no_duplicates(boss: BossBase) -> bool:
	var counts: Dictionary = {}
	for attack_id: String in boss.moveset_tree.get_exits_for_state("IDLE"):
		counts[attack_id] = int(counts.get(attack_id, 0)) + 1
	for attack_id: String in IDLE_LIGHTNING_IDS:
		if int(counts.get(attack_id, 0)) != 1:
			_fail("runtime merge left %d copies of %s" % [counts.get(attack_id, 0), attack_id])
			return false
	return true


func _assert_authored_and_locked_overhead_exits(boss: BossBase) -> bool:
	var authored := ResourceLoader.load(
		"res://resources/attacks/overhead_slam.tres"
	) as AttackData
	if authored == null:
		_fail("authored overhead_slam.tres did not load")
		return false
	var authored_ids := _attack_exit_ids(authored)
	if (
		"flow_into_x" not in authored_ids
		or "lightning_slam_aoe" not in authored_ids
		or authored_ids.size() != 2
	):
		_fail("authored overhead_slam.tres did not contain both Phase 1/1.5 exits")
		return false
	var locked := boss.attack_library.get_attack("overhead_slam")
	if locked == null:
		_fail("locked runtime overhead_slam did not resolve")
		return false
	var locked_ids := _attack_exit_ids(locked)
	if locked_ids != ["flow_into_x"]:
		_fail("locked runtime overhead_slam did not contain exactly flow_into_x")
		return false
	return true


func _assert_marker_lead_times_and_pruning() -> bool:
	var rig := await _make_rig()
	_unlock_rig(rig)
	var boss := rig.boss as BossBase
	var layer := rig.layer as LightningLayer
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	var markers: Dictionary = {}
	layer.marker_created.connect(func(attack_id: String, marker_data: Dictionary) -> void:
		markers[attack_id] = marker_data.duplicate(true)
	)
	layer._create_placidusax_marker(boss.global_position)
	layer._start_mid_melee_bolt()
	layer._start_shrinking_circle()
	var expected_leads := {
		"lightning_placidusax_call": tunables.lightning_pattern_marker_warning,
		"lightning_targeted_strikes_mid_melee": tunables.lightning_mid_melee_warning,
		"lightning_shrinking_circle": tunables.lightning_shrinking_circle_warning,
	}
	for attack_id: String in expected_leads:
		if not markers.has(attack_id):
			_fail("%s did not emit a marker" % attack_id)
			return false
		var marker: Dictionary = markers[attack_id]
		if absf(
			float(marker.get("lead_time", -1.0))
			- float(expected_leads[attack_id])
		) > FLOAT_EPSILON:
			_fail("%s marker lead time did not match its tunable" % attack_id)
			return false
	var placidusax_marker: Dictionary = markers["lightning_placidusax_call"]
	var placidusax_id := int(placidusax_marker.get("marker_id", -1))
	if not _marker_id_is_active(layer, placidusax_id):
		_fail("Placidusax marker was not active during its warning")
		return false
	await _advance_layer(layer, tunables.lightning_pattern_marker_warning + 0.1)
	if _marker_id_is_active(layer, placidusax_id):
		_fail("Placidusax marker remained active after its strike landed")
		return false
	await _free_rig(rig)
	return true


func _assert_shrinking_circle_ring_geometry() -> bool:
	var rig := await _make_rig()
	_unlock_rig(rig)
	var layer := rig.layer as LightningLayer
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	var segments: Array[Hitbox] = []
	layer.strike_activated.connect(func(attack_id: String, hitbox: Hitbox) -> void:
		if attack_id == "lightning_shrinking_circle":
			segments.append(hitbox)
	)
	layer._start_shrinking_circle()
	await _advance_layer(layer, tunables.lightning_shrinking_circle_warning + 0.1)
	if segments.size() != tunables.lightning_shrinking_circle_ring_segment_count:
		_fail(
			"shrinking circle created %d segments instead of %d"
			% [segments.size(), tunables.lightning_shrinking_circle_ring_segment_count]
		)
		return false
	var radius_before := layer.get_shrinking_circle_radius()
	await _advance_layer(layer, 0.5)
	var radius_after := layer.get_shrinking_circle_radius()
	if radius_after >= radius_before:
		_fail("shrinking circle radius did not decrease over time")
		return false
	if radius_after < tunables.lightning_shrinking_circle_end_radius:
		_fail("shrinking circle radius contracted below its authored end radius")
		return false
	for segment: Hitbox in segments:
		var collision_shape := segment.get_node_or_null("CollisionShape3D") as CollisionShape3D
		if (
			collision_shape == null
			or collision_shape.shape == null
			or not (collision_shape.shape is Shape3D)
		):
			_fail("shrinking-circle ring segment lacked valid Shape3D geometry")
			return false
	# Every segment occupies only the radial band around radius. A positive inner
	# edge proves the circle center remains strictly outside all segment boxes.
	if radius_after - tunables.lightning_shrinking_circle_ring_thickness / 2.0 <= 0.0:
		_fail("shrinking-circle radial band reached its own safe center")
		return false
	await _free_rig(rig)
	return true


func _assert_horizontal_sweep_gap_geometry() -> bool:
	var rig := await _make_rig()
	_unlock_rig(rig)
	var layer := rig.layer as LightningLayer
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	layer._start_horizontal_sweep()
	await _advance_layer(layer, tunables.lightning_horizontal_sweep_tell + 0.1)
	var offsets := layer.get_horizontal_sweep_line_offsets()
	if offsets.size() != tunables.lightning_horizontal_sweep_line_count:
		_fail("horizontal sweep did not create the configured parallel line count")
		return false
	var expected_spacing := (
		tunables.lightning_horizontal_sweep_line_thickness
		+ tunables.lightning_horizontal_sweep_gap_width
	)
	for index: int in range(offsets.size() - 1):
		if absf(absf(offsets[index + 1] - offsets[index]) - expected_spacing) > FLOAT_EPSILON:
			_fail("horizontal sweep lines did not preserve thickness-plus-gap spacing")
			return false
	var offsets_after_motion := layer.get_horizontal_sweep_line_offsets()
	layer._process(0.25)
	if offsets_after_motion != layer.get_horizontal_sweep_line_offsets():
		_fail("horizontal sweep line gaps changed while the formation moved")
		return false
	await _free_rig(rig)
	return true


func _assert_dragons_charge_staging() -> bool:
	var rig := await _make_rig()
	_unlock_rig(rig)
	var boss := rig.boss as BossBase
	var layer := rig.layer as LightningLayer
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	var stages: Array[String] = []
	var strike_order: Array[String] = []
	layer.dragons_charge_stage_entered.connect(func(stage: String) -> void:
		stages.append(stage)
	)
	layer.strike_activated.connect(func(attack_id: String, _hitbox: Hitbox) -> void:
		if attack_id in ["lightning_dragons_charge_shove", "lightning_dragons_charge"]:
			strike_order.append(attack_id)
	)
	var start_position := boss.global_position
	var charge := boss.attack_library.get_attack("lightning_dragons_charge")
	boss.run_attack(charge)
	boss.run_attack(charge)
	var full_sequence_duration := (
		tunables.lightning_dragons_charge_step_back_duration
		+ tunables.lightning_dragons_charge_emergence_duration
		+ tunables.lightning_dragons_charge_duration
		+ 0.2
	)
	await _advance_layer(layer, full_sequence_duration)
	if stages != ["shove", "emergence", "charge"]:
		_fail("Dragon's Charge stages fired out of order: %s" % [stages])
		return false
	if (
		strike_order.count("lightning_dragons_charge_shove") != 1
		or strike_order.count("lightning_dragons_charge") != 1
		or strike_order.find("lightning_dragons_charge_shove")
		>= strike_order.find("lightning_dragons_charge")
	):
		_fail("Dragon's Charge shove did not precede exactly one real charge strike")
		return false
	if absf(
		boss.global_position.distance_to(start_position)
		- tunables.lightning_dragons_charge_step_back_distance
	) > 0.1:
		_fail("Dragon's Charge boss step-back did not cover its configured distance")
		return false
	# The active corridor outlasts a whole roll, and therefore its shorter i-frame
	# window, so one dodge cannot cover the hazard; sustained lateral running must.
	if tunables.lightning_dragons_charge_duration <= tunables.roll_duration:
		_fail("Dragon's Charge corridor did not outlast one complete dodge roll")
		return false
	if not layer.has_dragons_charge_been_used():
		_fail("Dragon's Charge did not latch its one-time flag")
		return false
	layer.merge_runtime_initiators()
	if "lightning_dragons_charge" in boss.moveset_tree.get_exits_for_state("IDLE"):
		_fail("Dragon's Charge remained in the pool after first use")
		return false
	await _free_rig(rig)
	return true


func _assert_lightning_followup_pools() -> bool:
	var rig := await _make_rig()
	_unlock_rig(rig)
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var layer := rig.layer as LightningLayer
	ai._physics_process(SYNTHETIC_DELTA)
	layer.merge_runtime_initiators()
	var placidusax := boss.attack_library.get_attack("lightning_placidusax_call")
	boss.run_attack(placidusax)
	var actual := _attack_exit_ids(placidusax)
	actual.sort()
	var expected: Array[String] = [
		"x_combo", "jump_lunge", "dragons_memory", "the_pause", "sacred_cleave",
	]
	expected.sort()
	if actual != expected:
		_fail("Placidusax follow-up pool did not match the SPEC mid-band set: %s" % [actual])
		return false
	if "horizontal_sweep" in actual or "sacred_cleave" not in actual:
		_fail("lightning follow-up pool retained Tide or omitted Sacred Cleave")
		return false
	var sweep := boss.attack_library.get_attack("lightning_horizontal_sweep")
	boss.run_attack(sweep)
	var sweep_ids := _attack_exit_ids(sweep)
	sweep_ids.sort()
	var expected_sweep: Array[String] = ["jump_lunge", "x_combo"]
	expected_sweep.sort()
	if sweep_ids != expected_sweep:
		_fail("horizontal lightning sweep follow-ups changed from X/jump-lunge")
		return false
	await _free_rig(rig)
	return true


func _attack_exit_ids(attack: AttackData) -> Array[String]:
	var ids: Array[String] = []
	for option: Dictionary in attack.exit_options:
		ids.append(str(option.get("attack_id", "")))
	return ids


func _marker_id_is_active(layer: LightningLayer, marker_id: int) -> bool:
	for marker: Dictionary in layer.get_active_markers():
		if int(marker.get("marker_id", -1)) == marker_id:
			return true
	return false


func _unlock_rig(rig: Dictionary) -> void:
	var boss := rig.boss as BossBase
	var ai := rig.ai as GodwynP1AI
	var layer := rig.layer as LightningLayer
	var target_hp := roundi(float(boss.boss_stats.max_hp) * BELOW_THRESHOLD_RATIO)
	boss.boss_stats.take_damage(boss.boss_stats.hp - target_hp, DamageTypes.Type.PHYSICAL)
	ai._physics_process(SYNTHETIC_DELTA)
	layer.merge_runtime_initiators()


func _advance_layer(layer: LightningLayer, duration: float) -> void:
	var elapsed := 0.0
	while elapsed < duration:
		var step := minf(SYNTHETIC_DELTA, duration - elapsed)
		layer._process(step)
		await create_timer(step).timeout
		elapsed += step


func _assert_lightning_damage_contract(boss: BossBase) -> bool:
	for attack_id: String in ALL_LIGHTNING_IDS:
		var attack := boss.attack_library.get_attack(attack_id)
		if attack == null:
			_fail("AttackLibrary did not load %s" % attack_id)
			return false
		if attack.damage <= 0:
			_fail("%s damage was not positive" % attack_id)
			return false
		if attack.poise_damage <= 0.0:
			_fail("%s poise damage was not positive" % attack_id)
			return false
	return true


func _assert_small_strike_geometry() -> bool:
	var rig := await _make_rig()
	var boss := rig.boss as BossBase
	var layer := rig.layer as LightningLayer
	var observed: Dictionary = {}
	var invalid: Array[String] = []
	layer.strike_activated.connect(func(attack_id: String, hitbox: Hitbox) -> void:
		if attack_id not in SMALL_STRIKE_IDS:
			return
		observed[attack_id] = int(observed.get(attack_id, 0)) + 1
		var collision_shape := hitbox.get_node_or_null("CollisionShape3D") as CollisionShape3D
		if (
			collision_shape == null
			or collision_shape.shape == null
			or not (collision_shape.shape is Shape3D)
		):
			invalid.append(attack_id)
	)
	var target_hp := roundi(float(boss.boss_stats.max_hp) * BELOW_THRESHOLD_RATIO)
	boss.boss_stats.take_damage(
		boss.boss_stats.hp - target_hp,
		DamageTypes.Type.PHYSICAL
	)
	boss.run_attack(boss.attack_library.get_attack("lightning_placidusax_call"))
	await create_timer(0.9).timeout
	boss.run_attack(boss.attack_library.get_attack("lightning_targeted_strikes_standalone"))
	layer._start_mid_melee_bolt()
	await create_timer(0.3).timeout
	for attack_id: String in SMALL_STRIKE_IDS:
		if int(observed.get(attack_id, 0)) <= 0:
			_fail("%s never emitted a runtime strike" % attack_id)
			return false
	if not invalid.is_empty():
		_fail("runtime strikes lacked valid Shape3D geometry: %s" % [invalid])
		return false
	await _free_rig(rig)
	return true


func _assert_empty_clip_active_cycle() -> bool:
	var rig := await _make_rig(false)
	var boss := rig.boss as BossBase
	boss.auto_select_attacks = false
	var attack := boss.attack_library.get_attack("lightning_placidusax_call")
	if attack == null or not attack.animation_clip.is_empty():
		_fail("FSM regression attack did not have the required empty animation clip")
		return false
	if not boss.attack_library.animation_name(attack).is_empty():
		_fail("AttackLibrary returned a runtime animation name for an empty clip")
		return false
	boss.run_attack(attack)
	var reached_active := false
	var reached_recovery := false
	var resolved_after_recovery := false
	for _frame: int in 80:
		boss._process(SYNTHETIC_DELTA)
		if boss.current_state == BossBase.State.ACTIVE and not reached_active:
			reached_active = true
			boss._process(SYNTHETIC_DELTA)
			if boss.current_state != BossBase.State.ACTIVE:
				_fail("empty-clip lightning attack collapsed ACTIVE after one frame")
				return false
		if reached_active and boss.current_state == BossBase.State.RECOVERY:
			reached_recovery = true
		elif reached_recovery and boss.current_state != BossBase.State.RECOVERY:
			resolved_after_recovery = true
			break
	if not reached_active:
		_fail("empty-clip lightning attack never reached ACTIVE")
		return false
	if not reached_recovery:
		_fail("empty-clip lightning attack never reached RECOVERY")
		return false
	if not resolved_after_recovery:
		_fail("empty-clip lightning attack did not resolve after RECOVERY")
		return false
	await _free_rig(rig)
	return true


func _make_rig(disable_boss_process: bool = true) -> Dictionary:
	var boss := BOSS_BASE_SCRIPT.new() as BossBase
	root.add_child(boss)
	await process_frame
	var player := Node3D.new()
	player.name = "LightningLayerTestPlayer"
	root.add_child(player)
	player.global_position = Vector3(PLAYER_DISTANCE, 0.0, 0.0)
	var ai := AI_SCRIPT.new() as GodwynP1AI
	ai.name = "GodwynP1AI"
	ai.boss = boss
	ai.player_target = player
	root.add_child(ai)
	await process_frame
	var layer := LIGHTNING_LAYER_SCRIPT.new() as LightningLayer
	layer.name = "LightningLayer"
	layer.boss = boss
	layer.player_target = player
	root.add_child(layer)
	await process_frame
	if disable_boss_process:
		boss.set_process(false)
	ai.set_process(false)
	ai.set_physics_process(false)
	layer.set_process(false)
	layer.set_physics_process(false)
	return {"boss": boss, "player": player, "ai": ai, "layer": layer}


func _free_rig(rig: Dictionary) -> void:
	(rig.layer as Node).queue_free()
	(rig.ai as Node).queue_free()
	(rig.player as Node).queue_free()
	(rig.boss as Node).queue_free()
	await process_frame


func _fail(reason: String) -> void:
	print("FAIL test_lightning_layer: %s" % reason)
	quit(1)
