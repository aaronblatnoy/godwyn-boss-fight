extends SceneTree


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const WORLD_LAYER: int = 1
const PLAYER_LAYER: int = 2
const MIN_BOUNDARY_SEGMENTS: int = 16 # TEST HARNESS VALUE -- approved minimum ring tessellation.
const TEST_SPEED: float = 20.0 # TEST HARNESS VALUE -- outward containment probe speed.
const TEST_FRAMES: int = 180 # TEST HARNESS VALUE -- three physics seconds at the project tick rate.
const BOUNDARY_TOLERANCE: float = 2.0 # TEST HARNESS VALUE -- collider thickness/body-shape allowance.
const MIN_TRAVEL_DISTANCE: float = 10.0 # TEST HARNESS VALUE -- rejects accidental near-origin clamping.


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed_scene_resource: Resource = load("res://scenes/environments/void.tscn")
	if not packed_scene_resource is PackedScene:
		_fail("void scene did not load as PackedScene")
		return

	var packed_scene: PackedScene = packed_scene_resource as PackedScene
	var instance: Node = packed_scene.instantiate()
	if instance == null or not instance is Node3D:
		_fail("void scene root is not a valid Node3D")
		return

	root.add_child(instance)
	await physics_frame

	var floor := instance.get_node_or_null("Floor") as StaticBody3D
	if floor == null:
		_fail("void scene is missing the Floor StaticBody3D")
		return

	var floor_collision := floor.get_node_or_null("CollisionShape3D") as CollisionShape3D
	if floor_collision == null or floor_collision.shape == null:
		_fail("Floor is missing a configured CollisionShape3D")
		return

	if (floor.collision_layer & WORLD_LAYER) == 0:
		_fail("Floor collision_layer does not include world layer bit 1")
		return

	var boundary := instance.get_node_or_null("Boundary") as Node3D
	if boundary == null:
		_fail("void scene is missing the Boundary Node3D")
		return

	var boundary_meshes := boundary.find_children("*", "MeshInstance3D", true, false)
	if not boundary_meshes.is_empty():
		_fail("Boundary must be invisible but contains %d MeshInstance3D descendant(s)" % boundary_meshes.size())
		return

	var boundary_bodies := boundary.find_children("*", "StaticBody3D", true, false)
	if boundary_bodies.size() < MIN_BOUNDARY_SEGMENTS:
		_fail("Boundary has %d collision bodies; expected at least %d" % [boundary_bodies.size(), MIN_BOUNDARY_SEGMENTS])
		return

	for body_node: Node in boundary_bodies:
		var body := body_node as StaticBody3D
		if body == null:
			_fail("Boundary contains a non-StaticBody3D entry in its collision-body list")
			return
		if (body.collision_layer & WORLD_LAYER) == 0:
			_fail("Boundary body %s does not include world layer bit 1" % body.name)
			return
		if body.collision_mask != 0:
			_fail("Boundary body %s collision_mask must remain 0" % body.name)
			return
		var shape_node := body.get_node_or_null("CollisionShape3D") as CollisionShape3D
		if shape_node == null or shape_node.shape == null:
			_fail("Boundary body %s is missing a configured CollisionShape3D" % body.name)
			return

	var player_spawn := instance.get_node_or_null("PlayerSpawn")
	if player_spawn == null or not player_spawn is Marker3D:
		_fail("PlayerSpawn is missing or is not a Marker3D")
		return

	var boss_spawn := instance.get_node_or_null("BossSpawn")
	if boss_spawn == null or not boss_spawn is Marker3D:
		_fail("BossSpawn is missing or is not a Marker3D")
		return

	var tunables: Resource = TUNABLES_SCRIPT.new()
	var directions: Array[Vector3] = [Vector3.RIGHT, Vector3.LEFT, Vector3.BACK]
	var direction_labels: Array[String] = ["+X", "-X", "+Z"]
	for direction_index: int in directions.size():
		var final_distance := await _push_dummy_outward(instance, directions[direction_index])
		if final_distance > tunables.arena_boundary_radius + BOUNDARY_TOLERANCE:
			_fail(
				"Boundary failed %s containment: final radius %.3fm exceeds %.3fm"
				% [
					direction_labels[direction_index],
					final_distance,
					tunables.arena_boundary_radius + BOUNDARY_TOLERANCE,
				]
			)
			return
		if final_distance <= MIN_TRAVEL_DISTANCE:
			_fail(
				"Boundary %s probe traveled only %.3fm; expected more than %.3fm"
				% [direction_labels[direction_index], final_distance, MIN_TRAVEL_DISTANCE]
			)
			return
		print("boundary %s containment radius: %.3fm" % [direction_labels[direction_index], final_distance])

	instance.queue_free()
	print("PASS test_void_arena")
	quit(0)


func _push_dummy_outward(arena: Node, direction: Vector3) -> float:
	var dummy := CharacterBody3D.new()
	dummy.name = "BoundaryProbe"
	dummy.collision_layer = PLAYER_LAYER
	dummy.collision_mask = WORLD_LAYER
	dummy.position = Vector3(0.0, 1.0, 0.0)

	var collision_shape := CollisionShape3D.new()
	collision_shape.name = "CollisionShape3D"
	collision_shape.shape = BoxShape3D.new()
	dummy.add_child(collision_shape)
	arena.add_child(dummy)
	await physics_frame

	for _frame: int in TEST_FRAMES:
		dummy.velocity = direction * TEST_SPEED
		dummy.move_and_slide()
		await physics_frame

	var horizontal_distance := Vector2(dummy.global_position.x, dummy.global_position.z).length()
	dummy.queue_free()
	await process_frame
	return horizontal_distance


func _fail(reason: String) -> void:
	print("FAIL test_void_arena: %s" % reason)
	quit(1)
