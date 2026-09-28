class_name Hurtbox
extends Area3D


@export var stats_target: Node
@export var faction: String = ""
@export var hit_resolver_path: NodePath

var hit_resolver: HitResolver


func _ready() -> void:
	_configure_collision_layers()
	area_entered.connect(_on_area_entered)
	if not hit_resolver_path.is_empty():
		hit_resolver = get_node_or_null(hit_resolver_path) as HitResolver


func _on_area_entered(area: Area3D) -> void:
	if not area is Hitbox:
		return
	try_receive_hit(area as Hitbox)


func try_receive_hit(incoming: Hitbox) -> bool:
	if not monitoring or incoming == null:
		return false
	if not incoming.monitoring or incoming.owner_faction == faction:
		return false
	if hit_resolver == null:
		push_error("Hurtbox cannot resolve a hit without a HitResolver")
		return false
	return hit_resolver.resolve(incoming, self)


func _configure_collision_layers() -> void:
	collision_layer = 0
	collision_mask = 0
	if faction == "player":
		set_collision_layer_value(4, true)
		set_collision_mask_value(8, true)
	elif faction == "boss":
		set_collision_layer_value(7, true)
		set_collision_mask_value(5, true)
