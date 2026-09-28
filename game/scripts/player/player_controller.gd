class_name PlayerController
extends CharacterBody3D


const TunablesScript := preload("res://scripts/systems/tunables.gd")

var tunables := TunablesScript.new()
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity", 9.8)
var _roll_direction: Vector3 = Vector3.FORWARD
var _iframe_indicator_material: StandardMaterial3D
var _movement_camera: Camera3D
var _lock_on_target: Node3D
var _weapon_window_open: bool = false

@onready var stats: PlayerStats = $Stats
@onready var combat: PlayerCombat = $Combat
@onready var flask: Flask = $Flask
@onready var hurtbox: Hurtbox = $Hurtbox
@onready var weapon_hitbox: Hitbox = $HandSocket/WeaponHitbox
@onready var hit_resolver: HitResolver = $HitResolver
@onready var hitstop: Hitstop = $Hitstop
@onready var iframe_indicator: MeshInstance3D = $IFrameIndicator


func _ready() -> void:
	_iframe_indicator_material = iframe_indicator.material_override.duplicate() as StandardMaterial3D
	iframe_indicator.material_override = _iframe_indicator_material
	hurtbox.stats_target = stats
	hurtbox.hit_resolver = hit_resolver
	hitstop.bind_resolver(hit_resolver)
	stats.died.connect(_on_died)
	weapon_hitbox.deactivate()
	_set_hurtbox_monitoring(true)


func _physics_process(delta: float) -> void:
	if stats.is_dead or combat.state == PlayerCombat.State.DEAD:
		_process_dead(delta)
		return

	var input_vector := Input.get_vector("move_left", "move_right", "move_fwd", "move_back")
	var move_direction := _get_camera_relative_direction(input_vector)

	if Input.is_action_just_pressed("light_attack"):
		combat.try_start_light_attack(stats)
	if Input.is_action_just_pressed("heavy_attack"):
		combat.try_start_heavy_attack(stats)
	if Input.is_action_just_pressed("use_flask"):
		combat.try_start_flask(flask)

	if Input.is_action_just_pressed("roll"):
		var roll_started := false
		if combat.state == PlayerCombat.State.FLASK:
			roll_started = combat.try_cancel_flask_into_roll(stats, flask, tunables.stamina_cost_roll)
		elif combat.state != PlayerCombat.State.ROLL:
			roll_started = combat.try_start_roll(stats, tunables.stamina_cost_roll)
		if roll_started:
			_roll_direction = _get_roll_direction(move_direction)

	if combat.state == PlayerCombat.State.ROLL:
		_process_roll(delta)
		return
	if combat.is_attacking():
		_process_attack(delta)
		return
	if combat.state == PlayerCombat.State.FLASK:
		_process_flask(delta)
		return

	_process_locomotion(delta, move_direction)


func _process_locomotion(delta: float, move_direction: Vector3) -> void:
	var wants_sprint := Input.is_action_pressed("sprint") and not move_direction.is_zero_approx()
	var sprint_cost: float = tunables.stamina_cost_sprint_per_second * delta
	var can_sprint := wants_sprint and _lock_on_target == null and stats.stamina >= sprint_cost
	combat.set_sprinting(can_sprint)

	var speed: float = tunables.player_lockon_strafe_speed if _lock_on_target != null else (
		tunables.player_sprint_speed if can_sprint else tunables.player_walk_speed
	)
	velocity.x = move_direction.x * speed
	velocity.z = move_direction.z * speed
	_apply_gravity(delta)

	var facing_direction := move_direction
	if _lock_on_target != null:
		facing_direction = _horizontal_direction_to(_lock_on_target.global_position)
	if not facing_direction.is_zero_approx():
		var target_yaw := atan2(-facing_direction.x, -facing_direction.z)
		var rotation_step := deg_to_rad(tunables.player_rotation_speed_degrees) * delta
		rotation.y = rotate_toward(rotation.y, target_yaw, rotation_step)

	if can_sprint:
		stats.spend_stamina(sprint_cost)
	else:
		stats.process_stamina_regen(delta, false)

	move_and_slide()


func _process_roll(delta: float) -> void:
	_set_weapon_hitbox_active(false)
	var roll_t := combat.get_roll_t()
	_set_hurtbox_monitoring(not combat.is_roll_invulnerable_at(roll_t))

	var roll_speed: float = tunables.roll_distance / tunables.roll_duration
	var roll_time_remaining := maxf(tunables.roll_duration - combat.roll_elapsed, 0.0)
	var movement_fraction := minf(delta, roll_time_remaining) / delta if delta > 0.0 else 0.0
	velocity.x = _roll_direction.x * roll_speed * movement_fraction
	velocity.z = _roll_direction.z * roll_speed * movement_fraction
	_apply_gravity(delta)
	move_and_slide()

	combat.roll_elapsed += delta
	stats.process_stamina_regen(delta, true)
	if combat.roll_elapsed >= tunables.roll_duration:
		combat.finish_roll()
		_set_hurtbox_monitoring(true)
		velocity.x = 0.0
		velocity.z = 0.0


func _process_attack(delta: float) -> void:
	_set_weapon_hitbox_active(combat.is_attack_hitbox_open())
	velocity.x = 0.0
	velocity.z = 0.0
	_apply_gravity(delta)
	move_and_slide()
	combat.advance_attack(delta, stats)
	stats.process_stamina_regen(delta, true)
	if not combat.is_attacking():
		_set_weapon_hitbox_active(false)


func _process_flask(delta: float) -> void:
	_set_weapon_hitbox_active(false)
	velocity.x = 0.0
	velocity.z = 0.0
	_apply_gravity(delta)
	move_and_slide()
	combat.advance_flask(delta, flask, stats)
	stats.process_stamina_regen(delta, false)


func set_movement_camera(camera: Camera3D) -> void:
	_movement_camera = camera


func set_lock_on_target(target: Node3D) -> void:
	_lock_on_target = target


func _get_camera_relative_direction(input_vector: Vector2) -> Vector3:
	var camera := _movement_camera
	if camera == null:
		camera = get_viewport().get_camera_3d()
	if camera == null:
		return Vector3(input_vector.x, 0.0, input_vector.y).normalized()

	var camera_forward := -camera.global_basis.z
	camera_forward.y = 0.0
	if camera_forward.is_zero_approx():
		camera_forward = Vector3.FORWARD
	else:
		camera_forward = camera_forward.normalized()
	var camera_right := camera.global_basis.x
	camera_right.y = 0.0
	if camera_right.is_zero_approx():
		camera_right = Vector3.RIGHT
	else:
		camera_right = camera_right.normalized()
	return (camera_right * input_vector.x - camera_forward * input_vector.y).normalized()


func _get_roll_direction(move_direction: Vector3) -> Vector3:
	if not move_direction.is_zero_approx():
		return move_direction
	if _lock_on_target != null:
		var toward_target := _horizontal_direction_to(_lock_on_target.global_position)
		if not toward_target.is_zero_approx():
			return Vector3.UP.cross(toward_target).normalized()
	var facing_direction := -global_basis.z
	facing_direction.y = 0.0
	return facing_direction.normalized()


func _horizontal_direction_to(target_position: Vector3) -> Vector3:
	var direction := target_position - global_position
	direction.y = 0.0
	return direction.normalized()


func _apply_gravity(delta: float) -> void:
	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= _gravity * delta


func _process_dead(delta: float) -> void:
	_set_weapon_hitbox_active(false)
	_set_hurtbox_monitoring(true)
	velocity.x = 0.0
	velocity.z = 0.0
	_apply_gravity(delta)
	move_and_slide()


func _on_died() -> void:
	flask.cancel_drink()
	combat.enter_dead()
	_set_weapon_hitbox_active(false)
	_set_hurtbox_monitoring(true)
	velocity = Vector3.ZERO


func _set_hurtbox_monitoring(enabled: bool) -> void:
	hurtbox.set_enabled(enabled)
	# Minimal logic-only QA overlay: white is vulnerable, magenta is in i-frames.
	_iframe_indicator_material.albedo_color = Color.WHITE if enabled else Color.MAGENTA


func _set_weapon_hitbox_active(enabled: bool) -> void:
	if enabled == _weapon_window_open:
		return
	_weapon_window_open = enabled
	if enabled:
		weapon_hitbox.damage = combat.get_attack_damage()
		weapon_hitbox.poise_damage = combat.get_attack_poise_damage()
		weapon_hitbox.hitstop_duration = combat.get_attack_hitstop_duration()
		weapon_hitbox.activate()
	else:
		weapon_hitbox.deactivate()
