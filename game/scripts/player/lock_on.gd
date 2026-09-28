class_name LockOn
extends Node3D


signal target_acquired(target: Node3D)
signal target_broken
signal target_changed(target: Node3D)

const TunablesScript := preload("res://scripts/systems/tunables.gd")
const LOCKON_TARGET_LAYER := 9

var current_target: Node3D
var tunables := TunablesScript.new()
var _player: Node3D
var _camera: Camera3D
var _break_range_exceeded_seconds := 0.0

@onready var _acquisition_area: Area3D = $AcquisitionArea
@onready var _acquisition_shape: CollisionShape3D = $AcquisitionArea/CollisionShape3D


func _ready() -> void:
	_acquisition_area.collision_layer = 0
	_acquisition_area.collision_mask = 0
	_acquisition_area.set_collision_mask_value(LOCKON_TARGET_LAYER, true)
	_acquisition_area.monitoring = true
	_acquisition_area.monitorable = false
	var sphere := _acquisition_shape.shape as SphereShape3D
	if sphere != null:
		sphere.radius = tunables.lockon_max_range


func configure(player: Node3D, camera: Camera3D) -> void:
	if current_target != null:
		break_lock()
	_player = player
	_camera = camera
	_break_range_exceeded_seconds = 0.0
	if _player != null and is_instance_valid(_player):
		_acquisition_area.global_position = _player.global_position


func _physics_process(delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		return
	_acquisition_area.global_position = _player.global_position

	if current_target != null:
		if not is_instance_valid(current_target) or not _is_target_alive(current_target):
			break_lock()
		elif _player.global_position.distance_to(current_target.global_position) > tunables.lockon_break_range:
			# Acquisition at 25 m and break at 35 m already prevent immediate
			# re-acquisition. The reference's exact 2 s keep-alive additionally
			# prevents a mobile target's brief 35 m excursion from dropping lock.
			_break_range_exceeded_seconds += delta
			if _break_range_exceeded_seconds >= tunables.lockon_break_grace_seconds:
				break_lock()
		else:
			_break_range_exceeded_seconds = 0.0

	if Input.is_action_just_pressed("lock_on"):
		if current_target == null:
			acquire_nearest()
		else:
			break_lock()
		return

	if current_target == null:
		return
	if Input.is_action_just_pressed("target_left"):
		cycle_target(-1)
	elif Input.is_action_just_pressed("target_right"):
		cycle_target(1)


func acquire_nearest() -> Node3D:
	if _player == null or not is_instance_valid(_player):
		return null
	var nearest: Node3D = null
	var nearest_screen_distance := INF
	var viewport_center := Vector2.ZERO
	var can_score_screen := _camera != null and is_instance_valid(_camera)
	if can_score_screen:
		viewport_center = _camera.get_viewport().get_visible_rect().size / 2.0
	for candidate: Node3D in _valid_candidates():
		var screen_distance := _player.global_position.distance_to(candidate.global_position)
		if can_score_screen:
			screen_distance = viewport_center.distance_to(
				_camera.unproject_position(candidate.global_position)
			)
		if screen_distance < nearest_screen_distance:
			nearest = candidate
			nearest_screen_distance = screen_distance
	if nearest != null:
		_set_target(nearest, true)
	return nearest


func break_lock() -> void:
	_break_range_exceeded_seconds = 0.0
	if current_target == null:
		return
	current_target = null
	_apply_target_to_player(null)
	target_broken.emit()


func cycle_target(direction: int) -> Node3D:
	if current_target == null or _camera == null or not is_instance_valid(_camera):
		return current_target
	var candidates := _valid_candidates()
	if candidates.size() <= 1 or not candidates.has(current_target):
		return current_target
	candidates.sort_custom(
		func(a: Node3D, b: Node3D) -> bool:
			return _camera.unproject_position(a.global_position).x < _camera.unproject_position(b.global_position).x
	)
	var current_index := candidates.find(current_target)
	var next_index := wrapi(current_index + signi(direction), 0, candidates.size())
	var next_target: Node3D = candidates[next_index]
	if next_target != current_target:
		_set_target(next_target, false)
	return current_target


func _valid_candidates() -> Array[Node3D]:
	var candidates: Array[Node3D] = []
	if _player == null or not is_instance_valid(_player):
		return candidates
	for marker: Area3D in _acquisition_area.get_overlapping_areas():
		var candidate := _candidate_from_marker(marker)
		if candidate == null or candidates.has(candidate):
			continue
		# Physics layer 9 and the acquisition sphere are the primary candidate
		# gate. The center-distance check keeps marker radius from extending the
		# authored 25 m target-center contract.
		if (
			_is_target_alive(candidate)
			and _player.global_position.distance_to(candidate.global_position) <= tunables.lockon_max_range
		):
			candidates.append(candidate)
	return candidates


func _candidate_from_marker(marker: Area3D) -> Node3D:
	# Lock-on markers live on physics layer 9. They may declare a Node3D owner
	# through "lockon_owner" metadata; otherwise their direct Node3D parent is
	# the target. This is the convention future boss scenes must follow.
	if marker.has_meta(&"lockon_owner"):
		var declared_owner: Variant = marker.get_meta(&"lockon_owner")
		if declared_owner is Node3D and is_instance_valid(declared_owner):
			return declared_owner as Node3D
	var marker_parent := marker.get_parent()
	if marker_parent is Node3D and is_instance_valid(marker_parent):
		return marker_parent as Node3D
	return null


func _is_target_alive(candidate: Node3D) -> bool:
	if candidate.has_method("get_hp"):
		return int(candidate.call("get_hp")) > 0
	return true


func _set_target(target: Node3D, is_acquisition: bool) -> void:
	current_target = target
	_break_range_exceeded_seconds = 0.0
	_apply_target_to_player(target)
	if is_acquisition:
		target_acquired.emit(target)
	else:
		target_changed.emit(target)


func _apply_target_to_player(target: Node3D) -> void:
	if _player != null and is_instance_valid(_player) and _player.has_method("set_lock_on_target"):
		_player.call("set_lock_on_target", target)
