class_name LockOn
extends Node


signal target_acquired(target: Node3D)
signal target_broken
signal target_changed(target: Node3D)

const TunablesScript := preload("res://scripts/systems/tunables.gd")

var current_target: Node3D
var tunables := TunablesScript.new()
var _player: Node3D
var _camera: Camera3D


func configure(player: Node3D, camera: Camera3D) -> void:
	if current_target != null:
		break_lock()
	_player = player
	_camera = camera


func _physics_process(_delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		return

	if current_target != null and (
		not is_instance_valid(current_target)
		or _player.global_position.distance_to(current_target.global_position) > tunables.lockon_break_range
	):
		break_lock()

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
	var nearest: Node3D
	var nearest_distance := tunables.lockon_max_range
	for candidate: Node3D in _valid_candidates():
		var distance := _player.global_position.distance_to(candidate.global_position)
		if distance <= nearest_distance:
			nearest = candidate
			nearest_distance = distance
	if nearest != null:
		_set_target(nearest, true)
	return nearest


func break_lock() -> void:
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
	for node: Node in get_tree().get_nodes_in_group("lockon_target"):
		if node is Node3D and is_instance_valid(node):
			var candidate := node as Node3D
			if _player.global_position.distance_to(candidate.global_position) <= tunables.lockon_max_range:
				candidates.append(candidate)
	return candidates


func _set_target(target: Node3D, is_acquisition: bool) -> void:
	current_target = target
	_apply_target_to_player(target)
	if is_acquisition:
		target_acquired.emit(target)
	else:
		target_changed.emit(target)


func _apply_target_to_player(target: Node3D) -> void:
	if _player != null and is_instance_valid(_player) and _player.has_method("set_lock_on_target"):
		_player.call("set_lock_on_target", target)
