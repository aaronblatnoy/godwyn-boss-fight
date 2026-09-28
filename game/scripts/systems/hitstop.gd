class_name Hitstop
extends Node


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

@export var hit_resolver_path: NodePath

var _active_hitstops: int = 0
var _tunables: Resource = TUNABLES_SCRIPT.new()
var _resolver: HitResolver


func _ready() -> void:
	if not hit_resolver_path.is_empty():
		bind_resolver(get_node_or_null(hit_resolver_path) as HitResolver)


func bind_resolver(resolver: HitResolver) -> void:
	if _resolver != null and _resolver.hit_landed.is_connected(_on_hit_landed):
		_resolver.hit_landed.disconnect(_on_hit_landed)
	_resolver = resolver
	if _resolver != null and not _resolver.hit_landed.is_connected(_on_hit_landed):
		_resolver.hit_landed.connect(_on_hit_landed)


func _on_hit_landed(_owner: Variant, _victim: Variant, _amount: Variant, _poise: Variant) -> void:
	if _resolver != null:
		start(_resolver.last_hitstop_duration)


func start(duration: float) -> void:
	if duration <= 0.0:
		return
	_active_hitstops += 1
	Engine.time_scale = _tunables.hitstop_time_scale
	_restore_after(duration)


func _restore_after(duration: float) -> void:
	# This timer must ignore the time scale that hitstop changes.
	await get_tree().create_timer(duration, false, false, true).timeout
	_active_hitstops -= 1
	if _active_hitstops == 0:
		Engine.time_scale = 1.0
