class_name Hitbox
extends Area3D


@export var damage: int = 0
@export var poise_damage: float = 0.0
@export var damage_type: DamageTypes.Type = DamageTypes.Type.PHYSICAL
@export var knockback: float = 0.0
@export var owner_faction: String = ""
@export var hitstop_duration: float = 0.0

var _already_hit: Dictionary = {}
var _active_requested := false


func _ready() -> void:
	_configure_collision_layer()
	deactivate()


func _physics_process(_delta: float) -> void:
	if not _active_requested or not monitoring:
		return
	# Poll while active because toggling monitoring off and on does not make
	# Godot re-emit area_entered for pairs that never stopped overlapping.
	for area: Area3D in get_overlapping_areas():
		if area is Hurtbox:
			(area as Hurtbox).try_receive_hit(self)


func activate() -> void:
	_already_hit.clear()
	_active_requested = true
	set_deferred(&"monitorable", true)
	set_deferred(&"monitoring", true)


func activate_window(window: Dictionary) -> void:
	configure_window(window)
	activate()


func configure_window(window: Dictionary) -> void:
	var collision_shape := get_node_or_null("CollisionShape3D") as CollisionShape3D
	if collision_shape == null:
		collision_shape = CollisionShape3D.new()
		collision_shape.name = "CollisionShape3D"
		add_child(collision_shape)
	collision_shape.position = window.get("position", Vector3.ZERO) as Vector3
	if window.has("extents"):
		var box := BoxShape3D.new()
		box.size = (window.get("extents", Vector3.ZERO) as Vector3) * 2.0
		collision_shape.shape = box
	elif window.has("radius"):
		var sphere := SphereShape3D.new()
		sphere.radius = maxf(float(window.get("radius", 0.0)), 0.0)
		collision_shape.shape = sphere
	else:
		push_error("Hitbox active window has no extents or radius geometry")


func deactivate() -> void:
	# Animation call tracks and hit resolution can close a window while Godot is
	# flushing Area3D enter/exit signals. Deferred writes are the engine-safe
	# path; _active_requested stops overlap polling in this same frame.
	_active_requested = false
	set_deferred(&"monitoring", false)
	set_deferred(&"monitorable", false)


func is_active() -> bool:
	return _active_requested


func has_hit(hurtbox: Hurtbox) -> bool:
	return _already_hit.has(hurtbox.get_instance_id())


func mark_hit(hurtbox: Hurtbox) -> void:
	_already_hit[hurtbox.get_instance_id()] = true


func _configure_collision_layer() -> void:
	collision_layer = 0
	collision_mask = 0
	if owner_faction == "player":
		set_collision_layer_value(5, true)
		set_collision_mask_value(7, true)
	elif owner_faction == "boss":
		set_collision_layer_value(8, true)
		set_collision_mask_value(4, true)
