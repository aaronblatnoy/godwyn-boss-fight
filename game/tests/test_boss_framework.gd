extends SceneTree


const ATTACK_DATA_SCRIPT := preload("res://scripts/bosses/attack_data.gd")
const ATTACK_LIBRARY_SCRIPT := preload("res://scripts/bosses/attack_library.gd")
const BOSS_BASE_SCRIPT := preload("res://scripts/bosses/boss_base.gd")
const MOVESET := preload("res://resources/moveset/godwyn_p1.tres")
const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const FRAME_CAP := 600 # TEST HARNESS VALUE -- not a gameplay timing.
const TEST_TELEGRAPH := 0.08 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_WINDOW_START := 0.15 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_WINDOW_END := 0.35 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_RECOVERY := 0.08 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_DAMAGE := 1 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_POISE_DAMAGE := 1.0 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_HALF_STAGGER_RATIO := 0.5 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_STAGGER_TOLERANCE := 0.08 # TEST HARNESS VALUE -- not a SPEC number.
const MAX_TRAVERSAL_DEPTH := 12 # TEST HARNESS VALUE -- not a gameplay limit.
const MAX_CHAIN_LENGTH := 6 # SPEC.txt lines 366-368: chains extend to at most six hits.
const SEEDED_CHAIN_SEED := 9 # TEST HARNESS VALUE -- deterministic regression seed.
const VARIANCE_SEED_COUNT := 30 # TEST HARNESS VALUE -- required distinct-seed sample size.
const PHYSICS_FRAME_CAP := 120 # TEST HARNESS VALUE -- not a gameplay timing.
const TEST_SPHERE_RADIUS := 1.25 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_SPHERE_POSITION := Vector3(0.0, 1.0, 0.0) # TEST HARNESS VALUE -- not a SPEC number.

var _original_max_fps: int


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_original_max_fps = Engine.max_fps
	Engine.max_fps = 120
	var library := ATTACK_LIBRARY_SCRIPT.new() as AttackLibrary
	library.load_default_attacks()

	if not _test_tree_completeness(library):
		return
	if not _test_seeded_chain(library):
		return
	if not _test_failed_continuation_terminates():
		return
	if not _test_chain_length_variance(library):
		return
	if not _test_overshoot_rule(library):
		return
	if not await _test_runtime_geometry_and_damage():
		return
	if not await _test_hitbox_window_timing():
		return
	if not await _test_stunned_path():
		return

	Engine.max_fps = _original_max_fps
	print("PASS test_boss_framework")
	quit(0)


func _test_tree_completeness(library: AttackLibrary) -> bool:
	var expected_initiators := {
		"x_combo": true,
		"horizontal_sweep": true,
		"jump_lunge": true,
		"dragons_memory": true,
		"the_pause": true,
	}
	var actual_initiators: Array = MOVESET.get_exits_for_state("IDLE")
	if actual_initiators.size() != expected_initiators.size():
		_fail("initiator pool does not contain all five Phase 4 initiators")
		return false
	for attack_id: String in actual_initiators:
		if not expected_initiators.has(attack_id):
			_fail("unexpected initiator %s" % attack_id)
			return false
	for required_id: String in ["dragons_memory", "the_pause"]:
		if library.get_attack(required_id) == null:
			_fail("required structural placeholder %s is absent from AttackLibrary" % required_id)
			return false
	if not "MEMORY_FRAG" in BossBase.State.keys():
		_fail("BossBase.State is missing MEMORY_FRAG")
		return false

	for state: String in ["BACK_TO_PLAYER", "AIRBORNE", "EXTENDED"]:
		var exits: Array = MOVESET.get_exits_for_state(state)
		if exits.is_empty():
			_fail("%s has an empty/no-op exit list" % state)
			return false
		for attack_id: String in exits:
			if attack_id.is_empty() or library.get_attack(attack_id) == null:
				_fail("%s exit %s does not resolve to AttackData" % [state, attack_id])
				return false

	var queue: Array[Dictionary] = []
	for attack_id: String in actual_initiators:
		queue.append({"attack_id": attack_id, "depth": 0})
	var visited: Dictionary = {}
	while not queue.is_empty():
		var item: Dictionary = queue.pop_front()
		var attack_id: String = item.attack_id
		var depth: int = item.depth
		if visited.has(attack_id) or depth > MAX_TRAVERSAL_DEPTH:
			continue
		visited[attack_id] = true
		var attack := library.get_attack(attack_id)
		if attack == null:
			_fail("reachable attack_id %s has no AttackData resource" % attack_id)
			return false
		for option: Dictionary in attack.exit_options:
			var followup_id: String = str(option.get("attack_id", ""))
			if followup_id.is_empty() or library.get_attack(followup_id) == null:
				_fail("attack %s has missing/no-op follow-up %s" % [attack_id, followup_id])
				return false
			queue.append({"attack_id": followup_id, "depth": depth + 1})
		if attack.enters_state in ["BACK_TO_PLAYER", "AIRBORNE", "EXTENDED"]:
			for state_exit: String in MOVESET.get_exits_for_state(attack.enters_state):
				queue.append({"attack_id": state_exit, "depth": depth + 1})
	return true


func _test_seeded_chain(library: AttackLibrary) -> bool:
	var rng := RandomNumberGenerator.new()
	rng.seed = SEEDED_CHAIN_SEED
	var actual := _walk_chain("x_combo", library, rng)
	# Filled from the deterministic Godot RNG result; protects edge weighting,
	# continuation rolls, and their call order as one graph contract.
	var expected: Array[String] = [
		"x_combo",
		"branch_c_full_half_overhead",
		"flow_into_x",
		"x_combo",
		"branch_b_half_spin_overhead",
		"flow_into_x",
	]
	if actual != expected:
		_fail("seeded chain mismatch: expected %s, got %s" % [expected, actual])
		return false
	return true


func _test_chain_length_variance(library: AttackLibrary) -> bool:
	var lengths: Dictionary = {}
	var minimum := MAX_CHAIN_LENGTH
	var maximum := 0
	for seed_value: int in VARIANCE_SEED_COUNT:
		var rng := RandomNumberGenerator.new()
		rng.seed = seed_value
		var chain := _walk_chain("x_combo", library, rng)
		var chain_length := chain.size()
		if chain_length < 2 or chain_length > MAX_CHAIN_LENGTH:
			_fail("seed %d produced out-of-range chain length %d: %s" % [seed_value, chain_length, chain])
			return false
		lengths[chain_length] = true
		minimum = mini(minimum, chain_length)
		maximum = maxi(maximum, chain_length)
	if lengths.size() < 2 or minimum != 2 or maximum != MAX_CHAIN_LENGTH:
		_fail("30 seeds did not span variable chain lengths from 2 through 6: %s" % [lengths.keys()])
		return false
	return true


func _test_failed_continuation_terminates() -> bool:
	var attack := ATTACK_DATA_SCRIPT.new() as AttackData
	attack.id = "test_never_continue"
	attack.enters_state = "EXTENDED"
	attack.exit_options = [{
		"attack_id": "x_combo",
		"weight": 1.0,
		"continue_probability": 0.0,
	}]
	var rng := RandomNumberGenerator.new()
	rng.seed = SEEDED_CHAIN_SEED
	if not MOVESET.pick_attack_followup(attack, rng).is_empty():
		_fail("zero continue_probability did not terminate a non-IDLE attack chain")
		return false
	return true


func _walk_chain(start_attack_id: String, library: AttackLibrary, rng: RandomNumberGenerator) -> Array[String]:
	var chain: Array[String] = [start_attack_id]
	while chain.size() < MAX_CHAIN_LENGTH:
		var attack := library.get_attack(chain.back())
		if attack == null:
			break
		var next_id := ""
		if not attack.exit_options.is_empty():
			next_id = MOVESET.pick_attack_followup(attack, rng)
		elif not attack.enters_state.is_empty() and attack.enters_state != "IDLE":
			next_id = MOVESET.pick_next_attack(attack.enters_state, rng)
		if next_id.is_empty():
			break
		chain.append(next_id)
	return chain


func _test_overshoot_rule(library: AttackLibrary) -> bool:
	var jump_lunge := library.get_attack("jump_lunge")
	if jump_lunge == null or not jump_lunge.overshoot_possible:
		_fail("jump_lunge is not configured as overshoot-capable")
		return false
	if MOVESET.resolve_post_attack_state(jump_lunge, true) != "BACK_TO_PLAYER":
		_fail("overshoot did not override jump_lunge's own post-attack state")
		return false
	if MOVESET.resolve_post_attack_state(jump_lunge, false) != jump_lunge.enters_state:
		_fail("non-overshoot path did not retain jump_lunge's own state")
		return false
	var rng := RandomNumberGenerator.new()
	rng.seed = SEEDED_CHAIN_SEED
	var back_to_player_id := MOVESET.pick_next_attack("BACK_TO_PLAYER", rng)
	if back_to_player_id.is_empty() or library.get_attack(back_to_player_id) == null:
		_fail("BACK_TO_PLAYER resolved to an empty or missing AttackData exit")
		return false
	return true


func _test_runtime_geometry_and_damage() -> bool:
	var boss := BOSS_BASE_SCRIPT.new() as BossBase
	boss.auto_select_attacks = false
	root.add_child(boss)
	await process_frame
	for area: Area3D in [boss.boss_hitbox, boss.boss_hurtbox]:
		var collision_shape := area.get_node_or_null("CollisionShape3D") as CollisionShape3D
		if collision_shape == null or collision_shape.shape == null:
			_fail("%s lacks a real CollisionShape3D shape" % area.name)
			return false
	boss.boss_hitbox.configure_window({
		"position": TEST_SPHERE_POSITION,
		"radius": TEST_SPHERE_RADIUS,
	})
	var hitbox_shape := boss.boss_hitbox.get_node("CollisionShape3D") as CollisionShape3D
	var sphere := hitbox_shape.shape as SphereShape3D
	if sphere == null or not is_equal_approx(sphere.radius, TEST_SPHERE_RADIUS):
		_fail("radius window did not configure a SphereShape3D")
		return false
	if hitbox_shape.position != TEST_SPHERE_POSITION:
		_fail("radius window did not apply its local position")
		return false
	var attacker := Node3D.new()
	attacker.name = "FrameworkTestAttacker"
	var attacker_hitbox := Hitbox.new()
	attacker_hitbox.name = "Hitbox"
	attacker_hitbox.owner_faction = "player"
	attacker_hitbox.damage = TEST_DAMAGE
	attacker_hitbox.poise_damage = TEST_POISE_DAMAGE
	attacker.add_child(attacker_hitbox)
	root.add_child(attacker)
	attacker_hitbox.configure_window({"position": Vector3.ZERO, "extents": Vector3.ONE})
	await physics_frame
	var hp_before := boss.get_hp()
	attacker_hitbox.activate()
	if not await _wait_until_physics(func() -> bool: return boss.get_hp() == hp_before - TEST_DAMAGE):
		_fail("real Area3D overlap did not decrement BossStats hp through HitResolver")
		return false
	attacker_hitbox.deactivate()
	attacker.queue_free()
	boss.queue_free()
	await process_frame
	return true


func _test_hitbox_window_timing() -> bool:
	var boss := BOSS_BASE_SCRIPT.new() as BossBase
	boss.auto_select_attacks = false
	root.add_child(boss)
	await process_frame
	var attack := _make_timing_attack("test_window_attack")
	boss.run_attack(attack)
	if boss.current_state != BossBase.State.TELEGRAPH or boss.boss_hitbox.monitoring:
		_fail("hitbox was not closed during TELEGRAPH")
		return false
	if not await _wait_until(func() -> bool: return boss.current_state == BossBase.State.ACTIVE):
		_fail("test attack never entered ACTIVE")
		return false
	if boss.boss_hitbox.monitoring:
		_fail("hitbox opened before the active-window call-track key")
		return false
	if not await _wait_until(func() -> bool: return boss.boss_hitbox.monitoring):
		_fail("AnimationPlayer method track did not activate the Hitbox")
		return false
	var collision_shape := boss.boss_hitbox.get_node_or_null("CollisionShape3D") as CollisionShape3D
	var box: BoxShape3D
	if collision_shape != null:
		box = collision_shape.shape as BoxShape3D
	if box == null or box.size != Vector3.ONE * 2.0 or collision_shape.position != Vector3.ZERO:
		_fail("active-window method track did not configure box geometry from extents/position")
		return false
	if not await _wait_until(func() -> bool: return not boss.boss_hitbox.monitoring):
		_fail("AnimationPlayer method track did not deactivate the Hitbox")
		return false
	if not await _wait_until(func() -> bool: return boss.current_state == BossBase.State.RECOVERY):
		_fail("test attack never entered RECOVERY")
		return false
	if boss.boss_hitbox.monitoring:
		_fail("hitbox remained open during RECOVERY")
		return false
	boss.queue_free()
	await process_frame
	return true


func _test_stunned_path() -> bool:
	var boss := BOSS_BASE_SCRIPT.new() as BossBase
	boss.auto_select_attacks = false
	root.add_child(boss)
	await process_frame
	boss.run_attack(_make_timing_attack("test_stun_attack"))
	if not await _wait_until(func() -> bool: return boss.current_state == BossBase.State.ACTIVE):
		_fail("stun test attack never entered ACTIVE")
		return false
	var tunables: Resource = TUNABLES_SCRIPT.new()
	var stun_started_msec := Time.get_ticks_msec()
	boss.take_poise_damage(boss.current_poise)
	if boss.current_state != BossBase.State.STUNNED:
		_fail("poise break did not interrupt ACTIVE into STUNNED")
		return false
	await create_timer(tunables.boss_stagger_duration * TEST_HALF_STAGGER_RATIO).timeout
	if boss.current_state != BossBase.State.STUNNED:
		_fail("STUNNED ended before boss_stagger_duration")
		return false
	if not await _wait_until(func() -> bool: return boss.current_state == BossBase.State.IDLE):
		_fail("STUNNED did not return to IDLE")
		return false
	var stun_elapsed := float(Time.get_ticks_msec() - stun_started_msec) / 1000.0
	if stun_elapsed < tunables.boss_stagger_duration - TEST_STAGGER_TOLERANCE:
		_fail("STUNNED duration was shorter than boss_stagger_duration")
		return false
	boss.queue_free()
	await process_frame
	return true


func _make_timing_attack(attack_id: String) -> AttackData:
	var attack := ATTACK_DATA_SCRIPT.new() as AttackData
	attack.id = attack_id
	attack.telegraph_time = TEST_TELEGRAPH
	attack.active_windows = [{
		"start_t": TEST_WINDOW_START,
		"end_t": TEST_WINDOW_END,
		"radius": 1.0,
		"position": Vector3.ZERO,
		"extents": Vector3.ONE,
	}]
	attack.recovery_time = TEST_RECOVERY
	attack.damage = TEST_DAMAGE
	attack.poise_damage = TEST_POISE_DAMAGE
	attack.animation_clip = attack_id
	attack.enters_state = "IDLE"
	return attack


func _wait_until(predicate: Callable) -> bool:
	for _frame: int in FRAME_CAP:
		if predicate.call():
			return true
		await process_frame
	return predicate.call()


func _wait_until_physics(predicate: Callable) -> bool:
	for _frame: int in PHYSICS_FRAME_CAP:
		if predicate.call():
			return true
		await physics_frame
	return predicate.call()


func _fail(reason: String) -> void:
	Engine.max_fps = _original_max_fps
	print("FAIL test_boss_framework: %s" % reason)
	quit(1)
