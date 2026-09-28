class_name Hitbox
extends Area3D


@export var damage: int = 0
@export var poise_damage: float = 0.0
@export var damage_type: DamageTypes.Type = DamageTypes.Type.PHYSICAL
@export var knockback: float = 0.0
@export var owner_faction: String = ""
@export var hitstop_duration: float = 0.0

var _already_hit: Dictionary = {}


func _ready() -> void:
	_configure_collision_layer()
	deactivate()


func _physics_process(_delta: float) -> void:
	if not monitoring:
		return
	# Poll while active because toggling monitoring off and on does not make
	# Godot re-emit area_entered for pairs that never stopped overlapping.
	for area: Area3D in get_overlapping_areas():
		if area is Hurtbox:
			(area as Hurtbox).try_receive_hit(self)


func activate() -> void:
	_already_hit.clear()
	monitorable = true
	monitoring = true


func deactivate() -> void:
	monitoring = false
	monitorable = false


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
