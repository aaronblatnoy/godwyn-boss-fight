extends SceneTree


const RIG_SCENE := preload("res://scenes/bosses/godwyn_phase1.tscn")
const EXPECTED_BONES: Array[String] = [
	"Hips", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
	"RightUpLeg", "RightLeg", "RightFoot", "RightToeBase", "Spine02",
	"Spine01", "Spine", "LeftShoulder", "LeftArm", "LeftForeArm",
	"LeftHand", "neck", "Head", "head_end", "headfront",
	"RightShoulder", "RightArm", "RightForeArm", "RightHand",
]


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var boss := RIG_SCENE.instantiate() as BossBase
	if boss == null:
		_fail("godwyn_phase1.tscn did not instantiate as BossBase")
		return
	root.add_child(boss)
	await process_frame
	var skeleton := _find_skeleton(boss)
	if skeleton == null:
		_fail("imported rig has no Skeleton3D")
		return
	if skeleton.get_bone_count() != EXPECTED_BONES.size():
		_fail("imported rig has %d bones, expected 24" % skeleton.get_bone_count())
		return
	var actual: Array[String] = []
	for index: int in skeleton.get_bone_count():
		actual.append(skeleton.get_bone_name(index))
	if actual != EXPECTED_BONES:
		_fail("imported rig bone names/order differ: %s" % [actual])
		return
	var visual := boss.get_node("VisualRig") as GodwynVisual
	var player := visual._find_animation_player(visual)
	if player == null:
		_fail("imported rig has no visual AnimationPlayer")
		return
	var clips := Array(player.get_animation_list())
	if not _has_clip(clips, "Combat_Stance"):
		_fail("imported rig clips omit Combat_Stance: %s" % [clips])
		return
	if not player.is_playing():
		_fail("imported rig did not start Combat_Stance idle")
		return
	var phase_light := boss.get_node_or_null("Phase1Light") as OmniLight3D
	if phase_light == null or not is_equal_approx(phase_light.omni_range, 12.0):
		_fail("Phase 1 rig is missing its authored 12m OmniLight")
		return
	var mesh := _find_mesh(visual)
	if mesh == null or mesh.material_overlay == null:
		_fail("Phase 1 rig meshes did not receive the emissive overlay")
		return
	print("PASS test_godwyn_rig_import bones=24 clips=%s" % [clips])
	quit(0)


func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node as Skeleton3D
	for child: Node in node.get_children():
		var found := _find_skeleton(child)
		if found != null:
			return found
	return null


func _find_mesh(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D:
		return node as MeshInstance3D
	for child: Node in node.get_children():
		var found := _find_mesh(child)
		if found != null:
			return found
	return null


func _has_clip(clips: Array, suffix: String) -> bool:
	for clip: Variant in clips:
		if str(clip) == suffix or str(clip).ends_with("/%s" % suffix):
			return true
	return false


func _fail(reason: String) -> void:
	print("FAIL test_godwyn_rig_import: %s" % reason)
	quit(1)
