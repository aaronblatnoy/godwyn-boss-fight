extends SceneTree


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const ASSEMBLY_FRAME_CAP := 120 # TEST HARNESS VALUE -- bounded wait for GameManager's runtime assembly.
const SETTLE_FRAMES := 5 # TEST HARNESS VALUE -- lets Area3D overlap state settle.
const IFRAME_PROOF_FRAME_CAP := 480 # TEST HARNESS VALUE -- covers back-to-back rolls across multiple boss attack cycles inside ci.sh's 30s timeout.
const BOT_FRAME_CAP := 900 # TEST HARNESS VALUE -- keeps this smoke comfortably inside ci.sh's 30s timeout.
const TEST_TIME_SCALE := 3.0 # TEST HARNESS VALUE -- accelerates authored delta-time mechanics without changing their values.

var _original_max_fps: int
var _original_time_scale: float
var _manager: GameManager
var _player: PlayerController
var _player_stats: PlayerStats
var _player_combat: PlayerCombat
var _camera_rig: PlayerCamera
var _boss: BossBase
var _tunables: Tunables

var _boss_hp_decreased := false
var _player_damaged_outside_roll := false
var _iframe_overlap_proof_observed := false
var _poise_break_observed := false
var _end_state_reached := false
var _boss_window_open := false
var _recovery_signal_seen := false
var _last_boss_hp := 0
var _last_player_hp := 0
var _attack_started_count := 0
var _window_opened_count := 0
var _window_closed_count := 0


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_original_max_fps = Engine.max_fps
	_original_time_scale = Engine.time_scale
	Engine.max_fps = 120 # TEST HARNESS VALUE -- matches existing combat smoke scheduling.
	Engine.time_scale = 1.0
	_tunables = TUNABLES_SCRIPT.new()

	var packed_scene_resource: Resource = load("res://scenes/main.tscn")
	if not packed_scene_resource is PackedScene:
		_fail("main.tscn did not load as a PackedScene")
		return
	var packed_scene := packed_scene_resource as PackedScene
	var instance := packed_scene.instantiate()
	if instance == null or not instance is GameManager:
		_fail("main.tscn did not instantiate its real GameManager root")
		return
	_manager = instance as GameManager
	root.add_child(_manager)
	if not await _wait_for_assembly():
		_fail("GameManager did not finish vertical-slice assembly")
		return

	_player = _manager.player
	_player_stats = _player.stats
	_player_combat = _player.combat
	_camera_rig = _manager.player_camera
	_boss = _manager.boss
	if not _verify_assembly_contract():
		return

	await _wait_physics_frames(SETTLE_FRAMES)
	await _tap_action(&"lock_on")
	if _camera_rig.lock_on.current_target != _boss:
		_fail("real lock-on did not acquire Godwyn through his layer-9 marker")
		return

	# TEST HARNESS VALUE -- shrinks the fight so it finishes inside the 30s ci.sh timeout.
	# The value is derived from real Tunables so the bot must still apply enough
	# real light-hit poise damage to break the full authored boss poise bar.
	var light_hits_to_break_poise := ceili(
		float(_tunables.boss_poise) / _tunables.light_attack_poise_damage
	)
	_boss.boss_stats.hp = _tunables.light_attack_damage * light_hits_to_break_poise
	_last_boss_hp = _boss.boss_stats.hp
	_last_player_hp = _player_stats.hp
	_connect_runtime_signals()

	Engine.time_scale = TEST_TIME_SCALE
	var attack_target_hp := _boss.boss_stats.hp
	for _frame: int in BOT_FRAME_CAP:
		await physics_frame
		# Hitstop restores to 1.0 after its real unscaled duration. Resume the test
		# acceleration only after that restoration, never while hitstop is active.
		if is_equal_approx(Engine.time_scale, 1.0):
			Engine.time_scale = TEST_TIME_SCALE

		if _all_outcomes_observed():
			break
		if _end_state_reached:
			break

		if not _player_damaged_outside_roll:
			if _boss_window_open:
				_place_player_for_overlap()
			continue

		if not _iframe_overlap_proof_observed:
			var iframe_failure := await _prove_real_iframe_overlap()
			if not iframe_failure.is_empty():
				_fail(iframe_failure)
				return
			continue

		if _player_combat.is_attacking():
			if _boss.boss_stats.hp < attack_target_hp:
				_place_player_safe()
			else:
				_place_player_for_overlap()
			continue

		_place_player_safe()
		if (
			_recovery_signal_seen
			and _boss.current_state == BossBase.State.RECOVERY
			and _player_combat.state == PlayerCombat.State.FREE
			and _player_stats.stamina >= _tunables.stamina_cost_light_attack
		):
			_recovery_signal_seen = false
			attack_target_hp = _boss.boss_stats.hp
			_place_player_for_overlap()
			await _tap_action(&"light_attack")

	if not _all_outcomes_observed():
		_fail(_missing_outcomes_reason())
		return
	if _attack_started_count <= 0 or _window_opened_count <= 0 or _window_closed_count <= 0:
		_fail("boss signal path did not produce complete attack/window lifecycle events")
		return

	_cleanup_inputs()
	_restore_runtime()
	print("PASS test_vertical_slice")
	quit(0)


func _prove_real_iframe_overlap() -> String:
	var proof_frames := 0
	var roll_attempts := 0
	var active_overlap_seen := false
	var disabled_iframe_overlap_seen := false

	while proof_frames < IFRAME_PROOF_FRAME_CAP:
		_place_player_for_overlap()
		if _player_combat.state == PlayerCombat.State.FREE:
			await _tap_action(&"roll")
			proof_frames += 1
			_place_player_for_overlap()
			if _player_combat.state != PlayerCombat.State.ROLL:
				if proof_frames >= IFRAME_PROOF_FRAME_CAP:
					break
				await physics_frame
				proof_frames += 1
				continue
		elif _player_combat.state != PlayerCombat.State.ROLL:
			await physics_frame
			proof_frames += 1
			continue

		# Free-running back-to-back rolls sweep their i-frame windows across the
		# boss's longer, differently timed attack cycle. Pinning every physics frame
		# prevents roll displacement from invalidating the geometry proof.
		roll_attempts += 1

		var attempt_active_overlap_seen := false
		var attempt_disabled_iframe_overlap_seen := false
		var iframe_bracket_active := false
		var iframe_bracket_hp := 0
		while (
			_player_combat.state == PlayerCombat.State.ROLL
			and proof_frames < IFRAME_PROOF_FRAME_CAP
		):
			_place_player_for_overlap()
			await physics_frame
			proof_frames += 1
			_place_player_for_overlap()

			if not _boss_hitbox_overlaps_player_hurtbox():
				iframe_bracket_active = false
				continue
			attempt_active_overlap_seen = true
			active_overlap_seen = true
			var roll_t := _player_combat.get_roll_t()
			var inside_confirmed_iframe_overlap := (
				not _player.hurtbox.monitoring
				and _player_combat.is_roll_invulnerable_at(roll_t)
			)
			if not inside_confirmed_iframe_overlap:
				iframe_bracket_active = false
				continue

			attempt_disabled_iframe_overlap_seen = true
			disabled_iframe_overlap_seen = true
			if not iframe_bracket_active:
				iframe_bracket_active = true
				iframe_bracket_hp = _player_stats.hp
			elif _player_stats.hp != iframe_bracket_hp:
				return (
					"player HP changed to %d from %d while genuinely inside the confirmed-disabled "
					+ "i-frame window and overlapping an active boss hitbox -- real invariant violation"
				) % [_player_stats.hp, iframe_bracket_hp]

		var roll_completed := _player_combat.state != PlayerCombat.State.ROLL
		if attempt_active_overlap_seen and attempt_disabled_iframe_overlap_seen and roll_completed:
			_iframe_overlap_proof_observed = true
			_place_player_for_overlap()
			return ""

	var details: Array[String] = []
	if roll_attempts == 0:
		details.append("no roll ever started despite repeated attempts")
	if not active_overlap_seen:
		details.append("no active boss hitbox reported the player Hurtbox overlap during a roll")
	if not disabled_iframe_overlap_seen:
		details.append("no active overlap coincided with the authored disabled-hurtbox i-frame window")
	if details.is_empty():
		details.append("no completed roll combined active overlap and a confirmed disabled-hurtbox i-frame bracket")
	var detail_reason := ""
	for index: int in details.size():
		if index > 0:
			detail_reason += "; "
		detail_reason += details[index]
	return "i-frame overlap proof exceeded its %d-frame cap: %s" % [
		IFRAME_PROOF_FRAME_CAP,
		detail_reason,
	]


func _boss_hitbox_overlaps_player_hurtbox() -> bool:
	if not _boss.boss_hitbox.monitoring:
		return false
	for area: Area3D in _boss.boss_hitbox.get_overlapping_areas():
		if area == _player.hurtbox:
			return true
	return false


func _wait_for_assembly() -> bool:
	for _frame: int in ASSEMBLY_FRAME_CAP:
		if (
			_manager.arena != null
			and _manager.player != null
			and _manager.player_camera != null
			and _manager.boss != null
			and _manager.boss_ai != null
			and _manager.hud != null
			and _manager.boss_healthbar != null
			and _manager.death_screen != null
		):
			return true
		await process_frame
	return false


func _verify_assembly_contract() -> bool:
	var player_spawn := _manager.arena.get_node_or_null("PlayerSpawn") as Marker3D
	var boss_spawn := _manager.arena.get_node_or_null("BossSpawn") as Marker3D
	if player_spawn == null or boss_spawn == null:
		_fail("assembled Void is missing its authored spawn markers")
		return false
	if not _player.global_position.is_equal_approx(player_spawn.global_position):
		_fail("player did not spawn at Void/PlayerSpawn")
		return false
	if not _boss.global_position.is_equal_approx(boss_spawn.global_position):
		_fail("boss did not spawn at Void/BossSpawn")
		return false
	if _manager.boss_ai.player_target != _player or _manager.boss_ai.boss != _boss:
		_fail("GodwynP1AI is not bound to the assembled boss and player")
		return false
	var marker := _boss.get_node_or_null("LockOnMarker") as Area3D
	if marker == null or marker.get_parent() != _boss:
		_fail("boss lacks a direct-child LockOnMarker Area3D")
		return false
	if (
		not marker.get_collision_layer_value(9)
		or marker.collision_mask != 0
		or marker.monitoring
		or not marker.monitorable
	):
		_fail("boss LockOnMarker does not match the frozen layer-9 contract")
		return false
	if marker.get_node_or_null("CollisionShape3D") == null:
		_fail("boss LockOnMarker has no detectable CollisionShape3D")
		return false
	if _boss.get_node_or_null("GreyboxCapsule") == null:
		_fail("boss is missing its logic-layer capsule visual")
		return false
	if _manager.hud == null or _manager.boss_healthbar == null or _manager.death_screen == null:
		_fail("assembled combat UI is incomplete")
		return false
	return true


func _connect_runtime_signals() -> void:
	_boss.state_changed.connect(_on_boss_state_changed)
	_boss.attack_started.connect(_on_boss_attack_started)
	_boss.attack_window_opened.connect(_on_boss_window_opened)
	_boss.attack_window_closed.connect(_on_boss_window_closed)
	_boss.hp_changed.connect(_on_boss_hp_changed)
	_boss.poise_broken.connect(_on_boss_poise_broken)
	_player_stats.hp_changed.connect(_on_player_hp_changed)
	_player_stats.died.connect(_on_player_died)
	_manager.victory_reached.connect(_on_victory_reached)


func _on_boss_state_changed(_old_state: BossBase.State, new_state: BossBase.State) -> void:
	if new_state == BossBase.State.RECOVERY:
		_recovery_signal_seen = true
	if new_state == BossBase.State.STUNNED:
		_poise_break_observed = true


func _on_boss_attack_started(_attack_id: String) -> void:
	_attack_started_count += 1


func _on_boss_window_opened(_attack_id: String) -> void:
	_boss_window_open = true
	_window_opened_count += 1


func _on_boss_window_closed(_attack_id: String) -> void:
	_boss_window_open = false
	_window_closed_count += 1


func _on_boss_hp_changed(new_hp: int, _maximum_hp: int) -> void:
	if new_hp < _last_boss_hp:
		_boss_hp_decreased = true
	_last_boss_hp = new_hp


func _on_boss_poise_broken() -> void:
	_poise_break_observed = true


func _on_player_hp_changed(new_hp: int, _maximum_hp: int) -> void:
	if new_hp < _last_player_hp and _player_combat.state != PlayerCombat.State.ROLL:
		_player_damaged_outside_roll = true
	_last_player_hp = new_hp


func _on_player_died() -> void:
	_end_state_reached = true


func _on_victory_reached() -> void:
	_end_state_reached = true


func _place_player_for_overlap() -> void:
	_player.global_position = _boss.global_position
	_player.velocity = Vector3.ZERO


func _place_player_safe() -> void:
	# TEST HARNESS VALUE -- uses the authored arena radius as a repeatable combat
	# separation; no production movement, hitbox, or attack value is changed.
	var lateral := _boss.global_basis.x.normalized()
	if lateral.is_zero_approx():
		lateral = Vector3.RIGHT
	_player.global_position = _boss.global_position + lateral * _tunables.arena_boundary_radius
	_player.velocity = Vector3.ZERO


func _tap_action(action: StringName) -> void:
	Input.action_press(action)
	await physics_frame
	await process_frame
	Input.action_release(action)
	await process_frame


func _wait_physics_frames(frame_count: int) -> void:
	for _frame: int in frame_count:
		await physics_frame


func _all_outcomes_observed() -> bool:
	return (
		_boss_hp_decreased
		and _player_damaged_outside_roll
		and _iframe_overlap_proof_observed
		and _poise_break_observed
		and _end_state_reached
	)


func _missing_outcomes_reason() -> String:
	var missing: Array[String] = []
	if not _boss_hp_decreased:
		missing.append("(1) boss HP did not strictly decrease")
	if not _player_damaged_outside_roll:
		missing.append("(2) player never took damage outside PlayerCombat.State.ROLL")
	if not _iframe_overlap_proof_observed:
		missing.append("(3) no pinned roll combined active Area3D overlap, disabled hurtbox i-frames, and unchanged HP")
	if not _poise_break_observed:
		missing.append("(4) no boss poise-break/STUNNED state occurred")
	if not _end_state_reached:
		missing.append("(5) neither player death nor GameManager.victory_reached occurred")
	var reason := "safety cap reached without: "
	for index: int in missing.size():
		if index > 0:
			reason += "; "
		reason += missing[index]
	return reason


func _cleanup_inputs() -> void:
	for action: StringName in [
		&"move_fwd",
		&"move_back",
		&"move_left",
		&"move_right",
		&"sprint",
		&"roll",
		&"light_attack",
		&"heavy_attack",
		&"use_flask",
		&"lock_on",
		&"target_left",
		&"target_right",
	]:
		Input.action_release(action)


func _restore_runtime() -> void:
	Engine.time_scale = _original_time_scale
	Engine.max_fps = _original_max_fps


func _fail(reason: String) -> void:
	_cleanup_inputs()
	_restore_runtime()
	print("FAIL test_vertical_slice: %s" % reason)
	quit(1)
