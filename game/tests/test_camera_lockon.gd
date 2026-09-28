extends SceneTree


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const TEST_SCENE := preload("res://scenes/_tests/camera_lockon.tscn")
const SETTLE_FRAMES := 5 # TEST HARNESS VALUE -- physics stabilization only.
const COMPOSITION_SETTLE_SECONDS := 1.0 # TEST HARNESS VALUE -- lets both SPEC lerps visibly settle.
const INPUT_FRAMES := 2 # TEST HARNESS VALUE -- guarantees a physics just-pressed sample.
const TIMER_MARGIN := 0.1 # TEST HARNESS VALUE -- scheduler allowance beyond a SPEC tween duration.
const VALUE_TOLERANCE := 0.03 # TEST HARNESS VALUE -- float/tween endpoint tolerance.
const TWEEN_MIDPOINT_RATIO := 0.5 # TEST HARNESS VALUE -- midpoint sample rejects endpoint snaps.
const BOUNDARY_PROBE_MARGIN := 0.5 # TEST HARNESS VALUE -- samples immediately inside/outside SPEC range boundaries.
const SCREEN_CENTER_TOLERANCE_RATIO := 0.2 # TEST HARNESS VALUE -- qualitative "upper-center" bound.
const OUT_OF_RANGE_DISTANCE := 40.0 # TEST HARNESS VALUE -- beyond the SPEC 35m break range.
const CENTER_TARGET_POSITION := Vector3(0.0, 0.0, -20.0) # TEST HARNESS VALUE -- farther world-distance, nearest screen-center.
const NEAR_SIDE_TARGET_POSITION := Vector3(8.0, 0.0, -8.0) # TEST HARNESS VALUE -- nearer in world-space but far screen-right.
const LEFT_TARGET_POSITION := Vector3(-4.0, 0.0, -12.0) # TEST HARNESS VALUE -- fixed screen-left in-range candidate.
const RIGHT_TARGET_POSITION := Vector3(1.0, 0.0, -10.0) # TEST HARNESS VALUE -- fixed screen-right and nearest screen-center.
const STRAFE_DIRECTION_DOT := 0.9 # TEST HARNESS VALUE -- facing verification tolerance.
const PULLBACK_SOURCE := "camera_lockon_test" # TEST HARNESS VALUE -- verifies source-owned release.

# Authoritative SPEC.txt Sections 3/4 and reference Section 7 contract values.
# Runtime code reads only Tunables.
const EXPECTED_TUNABLES := {
	"player_mouse_sensitivity": 0.3,
	"lockon_max_range": 25.0,
	"lockon_break_range": 35.0,
	"lockon_break_grace_seconds": 2.0,
	"lockon_camera_lerp": 8.0,
	"camera_default_distance": 2.5,
	"camera_default_height": 1.4,
	"camera_default_fov": 75.0,
	"camera_pitch_clamp_min_degrees": -60.0,
	"camera_pitch_clamp_max_degrees": 80.0,
	"camera_lockon_fov": 72.0,
	"camera_lockon_distance_min": 3.0,
	"camera_lockon_distance_max": 8.0,
	"camera_lockon_position_lerp": 6.0,
	"camera_pullback_distance": 8.0,
	"camera_pullback_in_time": 0.3,
	"camera_pullback_return_time": 0.5,
}


class HealthLockTarget:
	extends Node3D

	var hp := 1

	func get_hp() -> int:
		return hp

var _scene: Node3D
var _player: PlayerController
var _camera_rig: PlayerCamera
var _lock_on: LockOn
var _left_target: Node3D
var _right_target: Node3D
var _tunables: Resource


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_tunables = TUNABLES_SCRIPT.new()
	_scene = TEST_SCENE.instantiate() as Node3D
	root.add_child(_scene)
	_player = _scene.get_node("Player") as PlayerController
	_camera_rig = _scene.get_node("PlayerCamera") as PlayerCamera
	_lock_on = _camera_rig.get_node("LockOn") as LockOn
	_left_target = _scene.get_node("TargetLeft") as Node3D
	_right_target = _scene.get_node("TargetRight") as Node3D
	_camera_rig.set_follow_target(_player)
	await _wait_physics_frames(SETTLE_FRAMES)
	if not _verify_tunable_contract():
		return
	if not _verify_default_camera():
		return

	# Both initial targets are beyond the SPEC acquisition range.
	await _press_action(&"lock_on")
	if _lock_on.current_target != null:
		_fail("lock acquired while every target was beyond %.1fm" % _tunables.lockon_max_range)
		return

	# Fresh acquisition honors both sides of the SPEC 25 m boundary.
	_right_target.global_position = _position_ahead(
		_tunables.lockon_max_range + BOUNDARY_PROBE_MARGIN
	)
	await _wait_physics_frames(SETTLE_FRAMES)
	await _press_action(&"lock_on")
	if _lock_on.current_target != null:
		_fail("fresh lock acquired just outside the SPEC 25m boundary")
		return
	_right_target.global_position = _position_ahead(
		_tunables.lockon_max_range - BOUNDARY_PROBE_MARGIN
	)
	await _wait_physics_frames(SETTLE_FRAMES)
	await _press_action(&"lock_on")
	if _lock_on.current_target != _right_target:
		_fail("fresh lock did not acquire just inside the SPEC 25m boundary")
		return
	await _press_action(&"lock_on")
	if _lock_on.current_target != null:
		_fail("could not clear the 25m boundary probe lock")
		return
	_right_target.global_position = Vector3(4.0, 0.0, -OUT_OF_RANGE_DISTANCE)

	# Acquisition prefers screen center, not the nearer world-space target.
	_left_target.global_position = CENTER_TARGET_POSITION
	_right_target.global_position = NEAR_SIDE_TARGET_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	await _press_action(&"lock_on")
	if _lock_on.current_target != _left_target:
		_fail("lock_on did not acquire the in-range target nearest screen center")
		return
	await create_timer(COMPOSITION_SETTLE_SECONDS).timeout
	if not _verify_locked_camera_composition(_left_target):
		return
	# Public locomotion behavior proves set_lock_on_target reached the player:
	# sprint is suppressed to strafe speed and facing rotates toward the target.
	Input.action_press("move_fwd")
	Input.action_press("sprint")
	await _wait_physics_frames(SETTLE_FRAMES * 2)
	Input.action_release("sprint")
	Input.action_release("move_fwd")
	var horizontal_speed := Vector2(_player.velocity.x, _player.velocity.z).length()
	if absf(horizontal_speed - _tunables.player_lockon_strafe_speed) > 0.15: # TEST HARNESS VALUE -- locomotion integration tolerance.
		_fail("player did not enter lock-on strafe behavior")
		return
	var toward_target := _left_target.global_position - _player.global_position
	toward_target.y = 0.0
	var player_forward := -_player.global_basis.z
	player_forward.y = 0.0
	if player_forward.normalized().dot(toward_target.normalized()) < STRAFE_DIRECTION_DOT:
		_fail("player did not face the acquired target")
		return

	# An active lock survives just inside 35 m. A brief excursion just outside
	# cannot flicker the lock, but a continuous excursion breaks after the exact
	# reference keep-alive duration.
	_left_target.global_position = _position_ahead(
		_tunables.lockon_break_range - BOUNDARY_PROBE_MARGIN
	)
	await _wait_physics_frames(SETTLE_FRAMES)
	if _lock_on.current_target != _left_target:
		_fail("active lock did not survive just inside the SPEC 35m boundary")
		return
	_left_target.global_position = _position_ahead(
		_tunables.lockon_break_range + BOUNDARY_PROBE_MARGIN
	)
	await _wait_physics_frames(SETTLE_FRAMES)
	if _lock_on.current_target != _left_target:
		_fail("brief movement just outside 35m flickered the active lock")
		return
	_left_target.global_position = _position_ahead(
		_tunables.lockon_break_range - BOUNDARY_PROBE_MARGIN
	)
	await _wait_physics_frames(SETTLE_FRAMES)
	if _lock_on.current_target != _left_target:
		_fail("returning inside 35m did not reset the break grace")
		return
	_left_target.global_position = _position_ahead(
		_tunables.lockon_break_range + BOUNDARY_PROBE_MARGIN
	)
	await create_timer(_tunables.lockon_break_grace_seconds + TIMER_MARGIN).timeout
	await physics_frame
	if _lock_on.current_target != null:
		_fail("lock did not break continuously outside the SPEC 35m boundary")
		return

	# Restore two valid targets. Nearest acquisition is right, then left/right cycle by screen x.
	_left_target.global_position = LEFT_TARGET_POSITION
	_right_target.global_position = RIGHT_TARGET_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	await _press_action(&"lock_on")
	if _lock_on.current_target != _right_target:
		_fail("could not reacquire right target for cycle test")
		return
	await _press_action(&"target_left")
	if _lock_on.current_target != _left_target:
		_fail("target_left did not select the screen-left target")
		return
	await _press_action(&"target_right")
	if _lock_on.current_target != _right_target:
		_fail("target_right did not select the screen-right target")
		return

	# Re-press toggles the active lock off.
	await _press_action(&"lock_on")
	if _lock_on.current_target != null:
		_fail("re-pressing lock_on did not break the active lock")
		return

	# Targets exposing zero HP cannot be acquired and an active target breaks on death.
	_left_target.global_position = Vector3(0.0, 0.0, -OUT_OF_RANGE_DISTANCE)
	_right_target.global_position = Vector3(0.0, 0.0, -OUT_OF_RANGE_DISTANCE)
	var health_target := HealthLockTarget.new()
	health_target.name = "HealthTarget"
	health_target.hp = 0
	_scene.add_child(health_target)
	health_target.global_position = Vector3(0.0, 0.0, -10.0)
	_add_lockon_marker(health_target)
	await _wait_physics_frames(SETTLE_FRAMES)
	await _press_action(&"lock_on")
	if _lock_on.current_target != null:
		_fail("lock_on acquired a dead target")
		return
	health_target.hp = 1
	await _press_action(&"lock_on")
	if _lock_on.current_target != health_target:
		_fail("lock_on did not acquire a live health-bearing target")
		return
	health_target.hp = 0
	await _wait_physics_frames(SETTLE_FRAMES)
	if _lock_on.current_target != null:
		_fail("lock did not break when the target died")
		return
	health_target.queue_free()

	# The public boss hook progresses over each SPEC duration rather than snapping,
	# reaches both endpoints, and only its exact non-empty owner can release it.
	var pullback_start := _camera_rig.spring_arm.spring_length
	_camera_rig.pull_back(
		_tunables.camera_pullback_distance,
		_tunables.camera_pullback_in_time,
		PULLBACK_SOURCE
	)
	await create_timer(_tunables.camera_pullback_in_time * TWEEN_MIDPOINT_RATIO).timeout
	var pullback_midpoint := _camera_rig.spring_arm.spring_length
	if (
		pullback_midpoint <= pullback_start + VALUE_TOLERANCE
		or pullback_midpoint >= _tunables.camera_pullback_distance - VALUE_TOLERANCE
	):
		_fail("pull_back snapped instead of progressing through the SPEC 0.3s tween")
		return
	await create_timer(
		_tunables.camera_pullback_in_time * (1.0 - TWEEN_MIDPOINT_RATIO) + TIMER_MARGIN
	).timeout
	if not _near(_camera_rig.spring_arm.spring_length, _tunables.camera_pullback_distance):
		_fail("pull_back did not reach the SPEC %.1fm distance" % _tunables.camera_pullback_distance)
		return
	_camera_rig.release_pull_back("")
	await create_timer(TIMER_MARGIN).timeout
	if not _near(_camera_rig.spring_arm.spring_length, _tunables.camera_pullback_distance):
		_fail("an explicit empty source bypassed pullback ownership")
		return
	_camera_rig.release_pull_back("different_source")
	await create_timer(TIMER_MARGIN).timeout
	if not _near(_camera_rig.spring_arm.spring_length, _tunables.camera_pullback_distance):
		_fail("a non-owner released the active camera pullback")
		return
	_camera_rig.release_pull_back(PULLBACK_SOURCE)
	await create_timer(_tunables.camera_pullback_return_time * TWEEN_MIDPOINT_RATIO).timeout
	var return_midpoint := _camera_rig.spring_arm.spring_length
	if (
		return_midpoint >= _tunables.camera_pullback_distance - VALUE_TOLERANCE
		or return_midpoint <= _tunables.camera_default_distance + VALUE_TOLERANCE
	):
		_fail("pullback release snapped instead of progressing through the SPEC 0.5s tween")
		return
	await create_timer(
		_tunables.camera_pullback_return_time * (1.0 - TWEEN_MIDPOINT_RATIO) + TIMER_MARGIN
	).timeout
	if not _near(_camera_rig.spring_arm.spring_length, _tunables.camera_default_distance):
		_fail("camera did not return from pullback over the SPEC return time")
		return

	if not await _verify_mouse_look():
		return

	_cleanup_inputs()
	_scene.queue_free()
	print("PASS test_camera_lockon")
	quit(0)


func _press_action(action: StringName) -> void:
	Input.action_press(action)
	await _wait_physics_frames(INPUT_FRAMES)
	Input.action_release(action)
	await physics_frame


func _wait_physics_frames(frame_count: int) -> void:
	for _frame: int in frame_count:
		await physics_frame


func _position_ahead(distance: float) -> Vector3:
	return _player.global_position + Vector3(0.0, 0.0, -distance)


func _add_lockon_marker(target: Node3D) -> void:
	var marker := Area3D.new()
	marker.name = "LockOnMarker"
	marker.collision_layer = 0
	marker.set_collision_layer_value(9, true) # Frozen Phase 0 lockon_target physics layer.
	marker.collision_mask = 0
	marker.monitoring = false
	marker.monitorable = true
	marker.set_meta(&"lockon_owner", target)
	var marker_shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.5 # TEST HARNESS VALUE -- small detection marker, not gameplay collision.
	marker_shape.shape = sphere
	target.add_child(marker)
	marker.add_child(marker_shape)


func _verify_tunable_contract() -> bool:
	for property_name: String in EXPECTED_TUNABLES:
		var actual := float(_tunables.get(property_name))
		var expected := float(EXPECTED_TUNABLES[property_name])
		if not is_equal_approx(actual, expected):
			_fail("%s is %.3f, expected SPEC value %.3f" % [property_name, actual, expected])
			return false
	return true


func _verify_default_camera() -> bool:
	if not _near(_camera_rig.spring_arm.spring_length, _tunables.camera_default_distance):
		_fail("default SpringArm distance does not match SPEC")
		return false
	if not _near(_camera_rig.camera.fov, _tunables.camera_default_fov):
		_fail("default camera FOV does not match SPEC")
		return false
	var actual_height := _camera_rig.global_position.y - _player.global_position.y
	if not _near(actual_height, _tunables.camera_default_height):
		_fail("camera follow height does not match SPEC")
		return false
	return true


func _verify_locked_camera_composition(target: Node3D) -> bool:
	if not _near(_camera_rig.camera.fov, _tunables.camera_lockon_fov):
		_fail("locked camera FOV did not settle to the SPEC value")
		return false
	var viewport_size := _camera_rig.camera.get_viewport().get_visible_rect().size
	var screen_center := viewport_size / 2.0
	var boss_anchor: Vector3 = target.global_position + Vector3.UP * float(_tunables.camera_default_height)
	var boss_screen: Vector2 = _camera_rig.camera.unproject_position(boss_anchor)
	var player_screen: Vector2 = _camera_rig.camera.unproject_position(_player.global_position)
	if absf(boss_screen.x - screen_center.x) > viewport_size.x * SCREEN_CENTER_TOLERANCE_RATIO:
		_fail("locked boss was not composed near screen center")
		return false
	if boss_screen.y >= player_screen.y:
		_fail("locked boss was not composed above the player")
		return false
	if boss_screen.y >= viewport_size.y / 2.0:
		_fail("locked boss was not composed in the viewport upper half")
		return false
	if player_screen.x >= screen_center.x or player_screen.y <= screen_center.y:
		_fail("locked player was not composed in the lower-left")
		return false
	return true


func _verify_mouse_look() -> bool:
	var start_yaw := _camera_rig.rotation.y
	var start_pitch := _camera_rig.spring_arm.rotation.x
	var sensitivity_event := InputEventMouseMotion.new()
	sensitivity_event.relative = Vector2(10.0, 10.0) # TEST HARNESS VALUE -- produces a measurable 3-degree change at SPEC sensitivity.
	_camera_rig._unhandled_input(sensitivity_event)
	await process_frame
	await process_frame
	var expected_delta := deg_to_rad(10.0 * _tunables.player_mouse_sensitivity)
	if not _near(_camera_rig.rotation.y, start_yaw - expected_delta):
		_fail("mouse yaw did not use the SPEC sensitivity")
		return false
	if not _near(_camera_rig.spring_arm.rotation.x, start_pitch - expected_delta):
		_fail("mouse pitch did not use the SPEC sensitivity")
		return false
	var down_event := InputEventMouseMotion.new()
	down_event.relative = Vector2(0.0, 1000.0) # TEST HARNESS VALUE -- exceeds the lower clamp.
	_camera_rig._unhandled_input(down_event)
	await process_frame
	await process_frame
	if not _near(rad_to_deg(_camera_rig.spring_arm.rotation.x), _tunables.camera_pitch_clamp_min_degrees):
		_fail("mouse pitch did not clamp at the SPEC minimum")
		return false
	var up_event := InputEventMouseMotion.new()
	up_event.relative = Vector2(0.0, -1000.0) # TEST HARNESS VALUE -- exceeds the upper clamp.
	_camera_rig._unhandled_input(up_event)
	await process_frame
	await process_frame
	if not _near(rad_to_deg(_camera_rig.spring_arm.rotation.x), _tunables.camera_pitch_clamp_max_degrees):
		_fail("mouse pitch did not clamp at the SPEC maximum")
		return false
	return true


func _near(actual: float, expected: float) -> bool:
	return absf(actual - expected) <= VALUE_TOLERANCE


func _cleanup_inputs() -> void:
	for action: StringName in [&"move_fwd", &"sprint", &"lock_on", &"target_left", &"target_right"]:
		Input.action_release(action)


func _fail(reason: String) -> void:
	_cleanup_inputs()
	print("FAIL test_camera_lockon: %s" % reason)
	quit(1)
