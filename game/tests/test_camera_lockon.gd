extends SceneTree


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const TEST_SCENE := preload("res://scenes/_tests/camera_lockon.tscn")
const SETTLE_FRAMES := 5 # TEST HARNESS VALUE -- physics stabilization only.
const INPUT_FRAMES := 2 # TEST HARNESS VALUE -- guarantees a physics just-pressed sample.
const OUT_OF_RANGE_DISTANCE := 40.0 # TEST HARNESS VALUE -- beyond the SPEC 35m break range.
const LEFT_TARGET_POSITION := Vector3(-4.0, 0.0, -12.0) # TEST HARNESS VALUE -- fixed screen-left in-range candidate.
const RIGHT_TARGET_POSITION := Vector3(4.0, 0.0, -10.0) # TEST HARNESS VALUE -- fixed screen-right and nearest candidate.
const STRAFE_DIRECTION_DOT := 0.9 # TEST HARNESS VALUE -- facing verification tolerance.

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

	# Both initial targets are beyond the SPEC acquisition range.
	await _press_action(&"lock_on")
	if _lock_on.current_target != null:
		_fail("lock acquired while every target was beyond %.1fm" % _tunables.lockon_max_range)
		return

	# The nearer in-range target is acquired through the real input action.
	_left_target.global_position = LEFT_TARGET_POSITION
	_right_target.global_position = RIGHT_TARGET_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	await _press_action(&"lock_on")
	if _lock_on.current_target != _right_target:
		_fail("lock_on did not acquire the nearest in-range target")
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
	var toward_target := _right_target.global_position - _player.global_position
	toward_target.y = 0.0
	var player_forward := -_player.global_basis.z
	player_forward.y = 0.0
	if player_forward.normalized().dot(toward_target.normalized()) < STRAFE_DIRECTION_DOT:
		_fail("player did not face the acquired target")
		return

	# Real target movement beyond the SPEC break range breaks on a physics tick.
	_right_target.global_position = Vector3(4.0, 0.0, -OUT_OF_RANGE_DISTANCE)
	await _wait_physics_frames(SETTLE_FRAMES)
	if _lock_on.current_target != null:
		_fail("lock did not break beyond %.1fm" % _tunables.lockon_break_range)
		return

	# Restore two valid targets. Nearest acquisition is right, then left/right cycle by screen x.
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


func _cleanup_inputs() -> void:
	for action: StringName in [&"move_fwd", &"sprint", &"lock_on", &"target_left", &"target_right"]:
		Input.action_release(action)


func _fail(reason: String) -> void:
	_cleanup_inputs()
	print("FAIL test_camera_lockon: %s" % reason)
	quit(1)
