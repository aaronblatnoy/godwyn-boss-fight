class_name GodwynVisual
extends Node3D


const IDLE_CLIP := &"Combat_Stance"
const EMISSIVE_SHADER := preload("res://shaders/emissive_godwyn.gdshader")


func _ready() -> void:
	_apply_phase1_emissive_overlay(self)
	var player := _find_animation_player(self)
	if player == null:
		push_error("Godwyn visual rig has no AnimationPlayer")
		return
	var idle := _resolve_animation_name(player, IDLE_CLIP)
	if idle.is_empty():
		push_error("Godwyn visual rig is missing Combat_Stance")
		return
	player.play(idle)


func _apply_phase1_emissive_overlay(node: Node) -> void:
	if node is MeshInstance3D:
		var overlay := ShaderMaterial.new()
		overlay.shader = EMISSIVE_SHADER
		(node as MeshInstance3D).material_overlay = overlay
	for child: Node in node.get_children():
		_apply_phase1_emissive_overlay(child)


func _find_animation_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node as AnimationPlayer
	for child: Node in node.get_children():
		var found := _find_animation_player(child)
		if found != null:
			return found
	return null


func _resolve_animation_name(player: AnimationPlayer, clip: StringName) -> StringName:
	for animation_name: StringName in player.get_animation_list():
		if animation_name == clip or String(animation_name).ends_with("/%s" % clip):
			return animation_name
	return &""
