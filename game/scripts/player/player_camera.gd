class_name PlayerCamera
extends Node3D


const TunablesScript := preload("res://scripts/systems/tunables.gd")
# SPEC defines the composition but not its exact aim weights. These implementation-detail
# fractions bias the focal point toward the boss and offset the player toward lower-left.
const LOCK_FOCUS_TARGET_WEIGHT := 0.68
const LOCK_PLAYER_SCREEN_OFFSET_RATIO := 0.12

var tunables := TunablesScript.new()
var _follow_target: Node3D
var _yaw := 0.0
var _pitch := 0.0
var _pullback_source := ""
var _pullback_distance := 0.0
var _pullback_active := false
var _pullback_tween: Tween

@onready var spring_arm: SpringArm3D = $SpringArm3D
@onready var camera: Camera3D = $SpringArm3D/Camera3D
@onready var lock_on: LockOn = $LockOn


func _ready() -> void:
	_yaw = rotation.y
	_pitch = spring_arm.rotation.x
	spring_arm.spring_length = tunables.camera_default_distance
	camera.fov = tunables.camera_default_fov
	lock_on.target_acquired.connect(_on_lock_target_updated)
	lock_on.target_changed.connect(_on_lock_target_updated)
	lock_on.target_broken.connect(_on_lock_target_broken)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and lock_on.current_target == null:
		var motion := event as InputEventMouseMotion
		_yaw -= deg_to_rad(motion.relative.x * tunables.player_mouse_sensitivity)
		_pitch -= deg_to_rad(motion.relative.y * tunables.player_mouse_sensitivity)
		_pitch = clampf(
			_pitch,
			deg_to_rad(tunables.camera_pitch_clamp_min_degrees),
			deg_to_rad(tunables.camera_pitch_clamp_max_degrees)
		)


func _process(delta: float) -> void:
	if _follow_target == null or not is_instance_valid(_follow_target):
		return
	var target := lock_on.current_target
	if target != null and is_instance_valid(target):
		_process_lock_on(delta, target)
	else:
		_process_free_camera()


func set_follow_target(target: Node3D) -> void:
	_follow_target = target
	lock_on.configure(target, camera)
	if target == null:
		return
	global_position = target.global_position + Vector3.UP * tunables.camera_default_height
	if target.has_method("set_movement_camera"):
		target.call("set_movement_camera", camera)


func pull_back(distance: float, in_time: float, source: String) -> void:
	_pullback_source = source
	_pullback_active = true
	if _pullback_tween != null:
		_pullback_tween.kill()
	_pullback_distance = spring_arm.spring_length
	_pullback_tween = create_tween()
	# SPEC fixes distance/time, but not easing; linear preserves the specified travel rate.
	_pullback_tween.set_trans(Tween.TRANS_LINEAR).set_ease(Tween.EASE_IN_OUT)
	_pullback_tween.tween_property(self, "_pullback_distance", distance, in_time)


func release_pull_back(source: String = "") -> void:
	if not _pullback_active or (not source.is_empty() and source != _pullback_source):
		return
	_pullback_active = false
	_pullback_source = ""
	if _pullback_tween != null:
		_pullback_tween.kill()
	var normal_distance := _normal_orbit_distance()
	_pullback_tween = create_tween()
	# SPEC fixes the 0.5 second return, but not easing; linear avoids extra timing assumptions.
	_pullback_tween.set_trans(Tween.TRANS_LINEAR).set_ease(Tween.EASE_IN_OUT)
	_pullback_tween.tween_property(self, "_pullback_distance", normal_distance, tunables.camera_pullback_return_time)
	_pullback_tween.tween_callback(func() -> void: _pullback_distance = 0.0)


func _process_free_camera() -> void:
	global_position = _follow_target.global_position + Vector3.UP * tunables.camera_default_height
	rotation = Vector3(0.0, _yaw, 0.0)
	spring_arm.rotation = Vector3(_pitch, 0.0, 0.0)
	camera.fov = tunables.camera_default_fov
	spring_arm.spring_length = _pullback_distance if _pullback_distance > 0.0 else tunables.camera_default_distance


func _process_lock_on(delta: float, target: Node3D) -> void:
	var position_weight := 1.0 - exp(-tunables.camera_lockon_position_lerp * delta)
	var rotation_weight := 1.0 - exp(-tunables.lockon_camera_lerp * delta)
	var player_anchor := _follow_target.global_position + Vector3.UP * tunables.camera_default_height
	var target_anchor := target.global_position + Vector3.UP * tunables.camera_default_height
	var flat_to_target := target.global_position - _follow_target.global_position
	flat_to_target.y = 0.0
	var screen_right := flat_to_target.normalized().cross(Vector3.UP)
	var composition_offset := screen_right * _normal_orbit_distance() * LOCK_PLAYER_SCREEN_OFFSET_RATIO
	global_position = global_position.lerp(player_anchor + composition_offset, position_weight)

	var focus := player_anchor.lerp(target_anchor, LOCK_FOCUS_TARGET_WEIGHT)
	var look_direction := focus - global_position
	if not look_direction.is_zero_approx():
		var desired_basis := Basis.looking_at(look_direction.normalized(), Vector3.UP)
		var current_quaternion := global_basis.get_rotation_quaternion()
		var desired_quaternion := desired_basis.get_rotation_quaternion()
		global_basis = Basis(current_quaternion.slerp(desired_quaternion, rotation_weight))
	spring_arm.rotation = Vector3.ZERO
	camera.fov = lerpf(camera.fov, tunables.camera_lockon_fov, position_weight)
	var orbit_distance := _pullback_distance if _pullback_distance > 0.0 else _normal_orbit_distance()
	spring_arm.spring_length = lerpf(spring_arm.spring_length, orbit_distance, position_weight)


func _normal_orbit_distance() -> float:
	if lock_on.current_target != null and is_instance_valid(lock_on.current_target) and _follow_target != null:
		return clampf(
			_follow_target.global_position.distance_to(lock_on.current_target.global_position),
			tunables.camera_lockon_distance_min,
			tunables.camera_lockon_distance_max
		)
	return tunables.camera_default_distance


func _on_lock_target_updated(_target: Node3D) -> void:
	pass


func _on_lock_target_broken() -> void:
	_yaw = rotation.y
	_pitch = spring_arm.rotation.x
