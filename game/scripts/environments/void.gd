extends Node3D


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const ARENA_BOUNDARY_RADIUS: float = 20.0 # SPEC.txt Section 5, Arena Playable radius: 20 meters / Boundary.
const SEGMENT_COUNT: int = 24 # Collision-ring tessellation; within the approved 16-24 segment implementation range.
const WORLD_LAYER: int = 1

var _boundary_built := false


func _ready() -> void:
	_build_boundary()


func _build_boundary() -> void:
	if _boundary_built:
		return
	_boundary_built = true

	var tunables: Resource = TUNABLES_SCRIPT.new()
	var boundary_radius: float = tunables.arena_boundary_radius
	if not is_equal_approx(boundary_radius, ARENA_BOUNDARY_RADIUS):
		push_error("Arena boundary radius must remain aligned with SPEC.txt Section 5")
		return

	# Every wall dimension is derived from the SPEC radius. The boxes overlap
	# tangentially so physics bodies cannot escape through segment seams.
	var radial_thickness: float = boundary_radius / float(SEGMENT_COUNT)
	var wall_height: float = boundary_radius
	var segment_length: float = (
		2.0
		* (boundary_radius + radial_thickness)
		* tan(PI / float(SEGMENT_COUNT))
	)

	for segment_index: int in SEGMENT_COUNT:
		var angle: float = TAU * float(segment_index) / float(SEGMENT_COUNT)
		var outward := Vector3(cos(angle), 0.0, sin(angle))
		var segment := StaticBody3D.new()
		segment.name = "Segment%02d" % segment_index
		segment.collision_layer = WORLD_LAYER
		segment.collision_mask = 0
		segment.position = outward * (boundary_radius + radial_thickness * 0.5)
		segment.position.y = wall_height * 0.5
		segment.rotation.y = -angle

		var collision_shape := CollisionShape3D.new()
		collision_shape.name = "CollisionShape3D"
		var box_shape := BoxShape3D.new()
		box_shape.size = Vector3(radial_thickness, wall_height, segment_length)
		collision_shape.shape = box_shape
		segment.add_child(collision_shape)
		add_child(segment)
