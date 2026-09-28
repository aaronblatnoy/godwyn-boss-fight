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
const MELEE_IDS: Array[String] = [
	"x_combo",
	"horizontal_sweep",
	"jump_lunge",
	"dragons_memory",
	"the_pause",
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
	layer.merge_runtime_initiators()
	if layer.is_unlocked():
		_fail("fresh full-HP rig unlocked lightning")
		return
	if not _assert_ids_absent(boss, IDLE_LIGHTNING_IDS, "full-HP pool"):
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
	if not _assert_ids_present(boss, MELEE_IDS, "unlocked melee pool"):
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
	# entry while leaving all five melee entries selectable.
	ai._physics_process(SYNTHETIC_DELTA)
	layer.merge_runtime_initiators()
	layer.merge_runtime_initiators()
	if not _assert_no_duplicates(boss):
		return
	boss.boss_stats.take_damage(1, DamageTypes.Type.PHYSICAL)
	if int(threshold_count.value) != 1:
		_fail("latched threshold-cross tell fired more than once")
		return

	var charge_strikes := {"value": 0}
	layer.strike_activated.connect(func(attack_id: String, _hitbox: Hitbox) -> void:
		if attack_id == "lightning_dragons_charge":
			charge_strikes.value = int(charge_strikes.value) + 1
	)
	var charge := boss.attack_library.get_attack("lightning_dragons_charge")
	boss.run_attack(charge)
	boss.run_attack(charge)
	if not layer.has_dragons_charge_been_used():
		_fail("Dragon's Charge did not latch its one-time flag")
		return
	if int(charge_strikes.value) != 1:
		_fail("Dragon's Charge activated %d times instead of once" % charge_strikes.value)
		return
	layer.merge_runtime_initiators()
	if "lightning_dragons_charge" in boss.moveset_tree.get_exits_for_state("IDLE"):
		_fail("Dragon's Charge remained in the pool after first use")
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
	for option: Dictionary in independent_overhead.exit_options:
		if str(option.get("attack_id", "")) == "lightning_slam_aoe":
			_fail("independent locked rig inherited the overhead lightning exit")
			return
	await _free_rig(independent_rig)

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
