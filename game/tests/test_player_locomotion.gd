extends SceneTree


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const TEST_SCENE := preload("res://scenes/_tests/player_locomotion.tscn")
const HITBOX_SCRIPT := preload("res://scripts/systems/hitbox.gd")
const HIT_RESOLVER_SCRIPT := preload("res://scripts/systems/hit_resolver.gd")
const PHYSICS_FPS := 60.0 # TEST HARNESS VALUE -- project physics tick rate.
const FRAME_CAP := 180 # TEST HARNESS VALUE -- deterministic wait guard.
const SETTLE_FRAMES := 5 # TEST HARNESS VALUE -- physics stabilization only.
const SPEED_TOLERANCE := 0.15 # TEST HARNESS VALUE -- meters/second assertion tolerance.
const RATE_TOLERANCE_RATIO := 0.15 # TEST HARNESS VALUE -- integration tolerance.
const ROLL_DISTANCE_TOLERANCE_RATIO := 0.15 # TEST HARNESS VALUE -- requested greybox tolerance.
const TEST_HIT_DAMAGE := 17 # TEST HARNESS VALUE -- overlap proof damage only.
const TEST_HIT_POISE_DAMAGE := 1.0 # TEST HARNESS VALUE -- overlap proof only.
const TEST_HITBOX_RADIUS := 0.5 # TEST HARNESS VALUE -- overlap geometry only.
const TEST_HITBOX_HEIGHT := 2.0 # TEST HARNESS VALUE -- overlap geometry only.
const IFRAME_BOUNDARY_MARGIN_T := 0.05 # TEST HARNESS VALUE -- normalized edge probe offset.
const DIRECTION_DOT_TOLERANCE := 0.95 # TEST HARNESS VALUE -- directional alignment assertion.
const LOCK_TARGET_OFFSET := 10.0 # TEST HARNESS VALUE -- nonzero target direction only.

var _original_max_fps: int
var _original_time_scale: float
var _scene: Node
var _player: PlayerController
var _stats: PlayerStats
var _combat: PlayerCombat
var _hurtbox: Hurtbox
var _tunables: Resource


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_original_max_fps = Engine.max_fps
	_original_time_scale = Engine.time_scale
	Engine.max_fps = 120
	_tunables = TUNABLES_SCRIPT.new()
	_scene = TEST_SCENE.instantiate()
	root.add_child(_scene)
	_player = _scene.get_node("Player") as PlayerController
	_stats = _player.get_node("Stats") as PlayerStats
	_combat = _player.get_node("Combat") as PlayerCombat
	_hurtbox = _player.get_node("Hurtbox") as Hurtbox
	await _wait_physics_frames(SETTLE_FRAMES)

	if not _player.is_on_floor():
		_fail("player did not settle on the test floor")
		return
	if _stats.fp != _tunables.player_max_fp:
		_fail("display-only FP expected %s, got %s" % [_tunables.player_max_fp, _stats.fp])
		return

	# Walk speed through the real Input singleton.
	Input.action_press("move_fwd")
	await _wait_physics_frames(SETTLE_FRAMES)
	var walk_speed := _horizontal_speed()
	Input.action_release("move_fwd")
	if absf(walk_speed - _tunables.player_walk_speed) > SPEED_TOLERANCE:
		_fail("walk speed expected %.3f, got %.3f" % [_tunables.player_walk_speed, walk_speed])
		return

	# Movement follows the active camera's horizontal basis.
	var movement_camera := Camera3D.new()
	_scene.add_child(movement_camera)
	movement_camera.rotation.y = PI * 0.5
	_player.set_movement_camera(movement_camera)
	Input.action_press("move_fwd")
	await _wait_physics_frames(SETTLE_FRAMES)
	Input.action_release("move_fwd")
	var camera_forward := -movement_camera.global_basis.z
	camera_forward.y = 0.0
	camera_forward = camera_forward.normalized()
	var camera_relative_velocity := Vector3(_player.velocity.x, 0.0, _player.velocity.z).normalized()
	if camera_relative_velocity.dot(camera_forward) < DIRECTION_DOT_TOLERANCE:
		_fail("forward input did not follow the movement camera")
		return
	_player.set_movement_camera(null)
	movement_camera.queue_free()
	await process_frame

	# Sprint speed and drain over one measured second.
	_stats.stamina = _tunables.player_max_stamina
	Input.action_press("move_fwd")
	Input.action_press("sprint")
	await _wait_physics_frames(SETTLE_FRAMES)
	var sprint_speed := _horizontal_speed()
	var sprint_stamina_before: float = _stats.stamina
	var sprint_frames := 60 # TEST HARNESS VALUE -- one physics second.
	await _wait_physics_frames(sprint_frames)
	var sprint_stamina_after: float = _stats.stamina
	Input.action_release("sprint")
	Input.action_release("move_fwd")
	if absf(sprint_speed - _tunables.player_sprint_speed) > SPEED_TOLERANCE:
		_fail("sprint speed expected %.3f, got %.3f" % [_tunables.player_sprint_speed, sprint_speed])
		return
	var expected_sprint_drain: float = _tunables.stamina_cost_sprint_per_second * sprint_frames / PHYSICS_FPS
	if absf((sprint_stamina_before - sprint_stamina_after) - expected_sprint_drain) > expected_sprint_drain * RATE_TOLERANCE_RATIO:
		_fail("sprint drain expected %.3f, got %.3f" % [expected_sprint_drain, sprint_stamina_before - sprint_stamina_after])
		return

	# Lock-on forces strafe speed, faces the target, and supplies a lateral no-input roll.
	var lock_target := Node3D.new()
	_scene.add_child(lock_target)
	lock_target.global_position = _player.global_position + Vector3.RIGHT * LOCK_TARGET_OFFSET
	_player.set_lock_on_target(lock_target)
	_stats.stamina = _tunables.player_max_stamina
	Input.action_press("move_fwd")
	Input.action_press("sprint")
	await _wait_physics_frames(SETTLE_FRAMES * 2)
	var lockon_speed := _horizontal_speed()
	Input.action_release("sprint")
	Input.action_release("move_fwd")
	if absf(lockon_speed - _tunables.player_lockon_strafe_speed) > SPEED_TOLERANCE:
		_fail("lock-on strafe speed expected %.3f, got %.3f" % [_tunables.player_lockon_strafe_speed, lockon_speed])
		return
	var toward_target := lock_target.global_position - _player.global_position
	toward_target.y = 0.0
	toward_target = toward_target.normalized()
	var player_forward := -_player.global_basis.z
	player_forward.y = 0.0
	player_forward = player_forward.normalized()
	if player_forward.dot(toward_target) < DIRECTION_DOT_TOLERANCE:
		_fail("lock-on locomotion did not face the target")
		return
	var lateral_roll_start := _player.global_position
	Input.action_press("roll")
	await physics_frame
	await process_frame
	Input.action_release("roll")
	if not await _wait_for_free():
		_fail("lock-on lateral roll did not finish")
		return
	var lateral_displacement := _player.global_position - lateral_roll_start
	lateral_displacement.y = 0.0
	if absf(lateral_displacement.normalized().dot(toward_target)) > 1.0 - DIRECTION_DOT_TOLERANCE:
		_fail("no-input lock-on roll was not lateral to its target")
		return
	_player.set_lock_on_target(null)
	lock_target.queue_free()
	await process_frame

	# Zero stamina must force walk speed even while sprint remains held.
	_stats.stamina = 0.0
	Input.action_press("move_fwd")
	Input.action_press("sprint")
	await _wait_physics_frames(SETTLE_FRAMES)
	var exhausted_speed := _horizontal_speed()
	Input.action_release("sprint")
	Input.action_release("move_fwd")
	if exhausted_speed > _tunables.player_walk_speed + SPEED_TOLERANCE:
		_fail("zero-stamina sprint exceeded walk speed: %.3f" % exhausted_speed)
		return

	# Recovery stays flat before the delay and then follows the configured rate.
	_stats.stamina = 50.0 # TEST HARNESS VALUE -- below-max recovery precondition.
	if not _stats.spend_stamina(1.0): # TEST HARNESS VALUE -- reset delay through the public API.
		_fail("could not seed stamina recovery delay")
		return
	var recovery_baseline: float = _stats.stamina
	var pre_delay_frames := 45 # TEST HARNESS VALUE -- 0.75 seconds at 60 Hz.
	await _wait_physics_frames(pre_delay_frames)
	if not is_equal_approx(_stats.stamina, recovery_baseline):
		_fail("stamina recovered before configured delay elapsed")
		return
	var regen_frames := 18 # TEST HARNESS VALUE -- crosses delay and samples 0.25 seconds of regen.
	await _wait_physics_frames(regen_frames)
	var expected_regen_seconds: float = (pre_delay_frames + regen_frames) / PHYSICS_FPS - _tunables.stamina_recovery_delay
	var expected_recovery: float = _tunables.stamina_recovery_rate * expected_regen_seconds
	if expected_recovery <= 0.0 or absf((_stats.stamina - recovery_baseline) - expected_recovery) > expected_recovery * RATE_TOLERANCE_RATIO:
		_fail("stamina recovery expected %.3f, got %.3f" % [expected_recovery, _stats.stamina - recovery_baseline])
		return

	# Roll spends its configured cost immediately.
	_stats.stamina = _tunables.player_max_stamina
	var roll_stamina_before: float = _stats.stamina
	Input.action_press("roll")
	await physics_frame
	await process_frame
	Input.action_release("roll")
	if not is_equal_approx(_stats.stamina, roll_stamina_before - _tunables.stamina_cost_roll):
		_fail("roll stamina cost expected %s, got %.3f" % [_tunables.stamina_cost_roll, roll_stamina_before - _stats.stamina])
		return
	if not await _wait_for_free():
		_fail("cost-check roll did not finish")
		return

	# A roll below its up-front cost is rejected without spending.
	_stats.stamina = _tunables.stamina_cost_roll - 1.0 # TEST HARNESS VALUE -- deliberately unaffordable.
	var blocked_stamina_before: float = _stats.stamina
	Input.action_press("roll")
	await physics_frame
	await process_frame
	Input.action_release("roll")
	if _combat.state == PlayerCombat.State.ROLL or not is_equal_approx(_stats.stamina, blocked_stamina_before):
		_fail("roll was not blocked cleanly below stamina cost")
		return

	# A complete input-driven roll covers the configured net distance.
	_stats.stamina = _tunables.player_max_stamina
	await _wait_physics_frames(SETTLE_FRAMES)
	var roll_start := Vector2(_player.global_position.x, _player.global_position.z)
	Input.action_press("move_fwd")
	Input.action_press("roll")
	await physics_frame
	await process_frame
	Input.action_release("roll")
	Input.action_release("move_fwd")
	if not await _wait_for_free():
		_fail("distance-check roll did not finish")
		return
	var roll_end := Vector2(_player.global_position.x, _player.global_position.z)
	var roll_distance := roll_start.distance_to(roll_end)
	if absf(roll_distance - _tunables.roll_distance) > _tunables.roll_distance * ROLL_DISTANCE_TOLERANCE_RATIO:
		_fail("roll distance expected %.3f, got %.3f" % [_tunables.roll_distance, roll_distance])
		return

	# A real boss Hitbox remains co-located as a child of the moving player.
	var resolver := HIT_RESOLVER_SCRIPT.new() as HitResolver
	_scene.add_child(resolver)
	_hurtbox.hit_resolver = resolver
	var test_hitbox := HITBOX_SCRIPT.new() as Hitbox
	test_hitbox.owner_faction = "boss"
	test_hitbox.damage = TEST_HIT_DAMAGE
	test_hitbox.poise_damage = TEST_HIT_POISE_DAMAGE
	var hit_shape := CollisionShape3D.new()
	var hit_capsule := CapsuleShape3D.new()
	hit_capsule.radius = TEST_HITBOX_RADIUS
	hit_capsule.height = TEST_HITBOX_HEIGHT
	hit_shape.shape = hit_capsule
	hit_shape.position = Vector3(0.0, 0.9, 0.0) # TEST HARNESS VALUE -- matches player capsule center.
	test_hitbox.add_child(hit_shape)
	_player.add_child(test_hitbox)
	await _wait_physics_frames(SETTLE_FRAMES)

	# Probe both sides of each normalized i-frame boundary while still rolling.
	var before_open_t: float = _tunables.roll_iframe_start_t - IFRAME_BOUNDARY_MARGIN_T
	if not _combat.is_roll_invulnerable_at(_tunables.roll_iframe_start_t):
		_fail("i-frame opening boundary must be inclusive")
		return
	if _combat.is_roll_invulnerable_at(_tunables.roll_iframe_end_t):
		_fail("i-frame closing boundary must be exclusive")
		return
	if not await _start_test_roll():
		_fail("could not start the pre-open boundary probe roll")
		return
	if not await _wait_for_roll_t(before_open_t):
		_fail("roll did not reach the pre-open boundary probe")
		return
	if not _hurtbox.monitoring:
		_fail("hurtbox disabled before i-frame window at roll_t=%.3f" % _combat.get_roll_t())
		return
	if not await _wait_for_free():
		_fail("pre-open boundary probe roll did not finish")
		return

	var after_open_t: float = _tunables.roll_iframe_start_t + IFRAME_BOUNDARY_MARGIN_T
	if not await _start_test_roll():
		_fail("could not start the post-open boundary probe roll")
		return
	if not await _wait_for_roll_t(after_open_t):
		_fail("roll did not reach the post-open boundary probe")
		return
	if _hurtbox.monitoring:
		_fail("hurtbox remained enabled inside opening edge at roll_t=%.3f" % _combat.get_roll_t())
		return
	if not await _wait_for_free():
		_fail("post-open boundary probe roll did not finish")
		return

	var before_close_t: float = _tunables.roll_iframe_end_t - IFRAME_BOUNDARY_MARGIN_T
	if not await _start_test_roll():
		_fail("could not start the pre-close boundary probe roll")
		return
	if not await _wait_for_roll_t(before_close_t):
		_fail("roll did not reach the pre-close boundary probe")
		return
	if _hurtbox.monitoring:
		_fail("hurtbox enabled before i-frame window closed at roll_t=%.3f" % _combat.get_roll_t())
		return
	if not await _wait_for_free():
		_fail("pre-close boundary probe roll did not finish")
		return

	var after_close_t: float = _tunables.roll_iframe_end_t + IFRAME_BOUNDARY_MARGIN_T
	if not await _start_test_roll():
		_fail("could not start the post-close boundary probe roll")
		return
	if not await _wait_for_roll_t(after_close_t):
		_fail("roll did not reach the post-close boundary probe")
		return
	if not _hurtbox.monitoring:
		_fail("hurtbox remained disabled after i-frame window at roll_t=%.3f" % _combat.get_roll_t())
		return
	if not await _wait_for_free():
		_fail("post-close boundary probe roll did not finish")
		return

	# A real overlap must deal no damage at the middle of the normalized window.
	var iframe_hp_before: int = _stats.hp
	if not await _start_test_roll():
		_fail("could not start the i-frame proof roll")
		return
	var inside_target_t: float = (_tunables.roll_iframe_start_t + _tunables.roll_iframe_end_t) * 0.5
	if not await _wait_for_roll_t(inside_target_t):
		_fail("roll did not reach the i-frame proof time")
		return
	if _hurtbox.monitoring:
		_fail("hurtbox was monitoring inside i-frame window at roll_t=%.3f" % _combat.get_roll_t())
		return
	var inside_attempt_t: float = _combat.get_roll_t()
	test_hitbox.activate()
	await _wait_physics_frames(3) # TEST HARNESS VALUE -- genuine overlap polling window.
	test_hitbox.deactivate()
	if _stats.hp != iframe_hp_before:
		_fail("real overlapping Hitbox damaged player inside i-frame window at roll_t=%.3f" % inside_attempt_t)
		return
	print("iframe-window hit attempted at roll_t=%.3f (window is [%.3f,%.3f))" % [inside_attempt_t, _tunables.roll_iframe_start_t, _tunables.roll_iframe_end_t])
	if not await _wait_for_free():
		_fail("i-frame proof roll did not finish")
		return

	# Prove vulnerability after the window closes but before the roll finishes.
	if not await _start_test_roll():
		_fail("could not start the outside-window proof roll")
		return
	var post_window_t: float = (_tunables.roll_iframe_end_t + 1.0) * 0.5
	if not await _wait_for_roll_t(post_window_t):
		_fail("roll did not reach the still-rolling post-window probe")
		return
	if not _hurtbox.monitoring:
		_fail("hurtbox remained disabled while still rolling past i-frames at roll_t=%.3f" % _combat.get_roll_t())
		return
	var outside_attempt_t: float = _combat.get_roll_t()
	test_hitbox.activate()
	if not await _wait_until(func() -> bool: return _stats.hp == iframe_hp_before - TEST_HIT_DAMAGE):
		_fail("real overlapping Hitbox did not damage player outside i-frame window")
		return
	test_hitbox.deactivate()
	print("outside-window hit attempted at roll_t=%.3f (window is [%.3f,%.3f))" % [outside_attempt_t, _tunables.roll_iframe_start_t, _tunables.roll_iframe_end_t])
	if not await _wait_for_free():
		_fail("outside-window proof roll did not finish")
		return

	# Death is terminal and locks out real movement and roll input.
	_stats.take_damage(_stats.hp)
	await physics_frame
	if not _stats.is_dead or _combat.state != PlayerCombat.State.DEAD:
		_fail("zero HP did not enter DEAD state")
		return
	var dead_start := Vector2(_player.global_position.x, _player.global_position.z)
	Input.action_press("move_fwd")
	Input.action_press("roll")
	await _wait_physics_frames(SETTLE_FRAMES)
	Input.action_release("roll")
	Input.action_release("move_fwd")
	var dead_end := Vector2(_player.global_position.x, _player.global_position.z)
	if dead_start.distance_to(dead_end) > 0.001 or _combat.state != PlayerCombat.State.DEAD:
		_fail("dead player moved or left DEAD state under input")
		return

	_cleanup_inputs()
	_scene.queue_free()
	Engine.time_scale = _original_time_scale
	Engine.max_fps = _original_max_fps
	print("PASS test_player_locomotion")
	quit(0)


func _horizontal_speed() -> float:
	return Vector2(_player.velocity.x, _player.velocity.z).length()


func _wait_physics_frames(frame_count: int) -> void:
	for _frame: int in frame_count:
		await physics_frame


func _wait_until(predicate: Callable) -> bool:
	for _frame: int in FRAME_CAP:
		if predicate.call():
			return true
		await physics_frame
	return predicate.call()


func _wait_for_free() -> bool:
	return await _wait_until(func() -> bool: return _combat.state == PlayerCombat.State.FREE)


func _start_test_roll() -> bool:
	_stats.stamina = _tunables.player_max_stamina
	Input.action_press("roll")
	await physics_frame
	await process_frame
	Input.action_release("roll")
	return _combat.state == PlayerCombat.State.ROLL


func _wait_for_roll_t(target_t: float) -> bool:
	return await _wait_until(
		func() -> bool:
			return _combat.state == PlayerCombat.State.ROLL and _combat.get_roll_t() >= target_t
	)


func _cleanup_inputs() -> void:
	for action: StringName in [&"move_fwd", &"move_back", &"move_left", &"move_right", &"sprint", &"roll"]:
		Input.action_release(action)


func _fail(reason: String) -> void:
	_cleanup_inputs()
	Engine.time_scale = _original_time_scale
	Engine.max_fps = _original_max_fps
	print("FAIL test_player_locomotion: %s" % reason)
	quit(1)
