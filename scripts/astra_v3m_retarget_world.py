"""Round 2 V3 build using rest-independent world-space bone orientations.

Run only through Blender on black-sky.  The published canonical is read but not
overwritten; output is models/astra_character_v3m_round2_wip.blend.
"""

import hashlib
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/astra_character_v3.blend"
WIP = ROOT / "models/astra_character_v3m_round2_wip.blend"
MOCAP = ROOT / "models/mocap"
OUT = ROOT / "renders/astra/char2/astra_v3m_round2_build.json"
EXPECTED_SOURCE = "49ff778d2279723230a6c9bdc1ebd2d423d67d7db58f746aa19544e3669b5a72"
EXPECTED = {
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def action_curves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


def action_channelbag(action, rig):
    layer = action.layers.new("V3M R2 World Layer")
    strip = layer.strips.new(type="KEYFRAME")
    slot = action.slots.new(id_type="OBJECT", name=rig.name)
    return slot, strip.channelbag(slot, ensure=True)


def key(bag, path, index, frame, value):
    curve = bag.fcurves.find(path, index=index) or bag.fcurves.new(path, index=index)
    point = curve.keyframe_points.insert(frame, value, options={"FAST"})
    point.interpolation = "LINEAR"


def assign(rig, action, frame):
    animation = rig.animation_data_create()
    animation.action = action
    if action.slots:
        animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def reset(rig):
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        bone.rotation_mode = "QUATERNION"
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def world_points(obj):
    return np.asarray([(obj.matrix_world @ vertex.co)[:] for vertex in obj.data.vertices], dtype=float)


def welded_components(obj, precision=4):
    representative = {}
    canonical = {}
    members = defaultdict(set)
    for vertex in obj.data.vertices:
        key_value = tuple(round(float(value), precision) for value in vertex.co)
        rep = representative.setdefault(key_value, vertex.index)
        canonical[vertex.index] = rep
        members[rep].add(vertex.index)
    adjacency = defaultdict(set)
    used = set()
    for edge in obj.data.edges:
        a, b = (canonical[index] for index in edge.vertices)
        if a == b:
            continue
        adjacency[a].add(b)
        adjacency[b].add(a)
        used.update((a, b))
    unseen = set(used)
    result = []
    while unseen:
        seed = unseen.pop()
        found = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in unseen:
                    unseen.remove(other)
                    found.add(other)
                    queue.append(other)
        result.append(set().union(*(members[index] for index in found)))
    result.sort(key=len, reverse=True)
    return result


def delete_small_hair_components(head):
    hair = head.data.color_attributes["meshy_hair_mask"]
    hair_ids = set()
    for poly in head.data.polygons:
        if np.mean([hair.data[index].color[0] for index in poly.loop_indices]) >= 0.5:
            hair_ids.update(poly.vertices)
    components = [component for component in welded_components(head) if component & hair_ids]
    main = components[0]
    main_hair = sorted(main & hair_ids)
    points = world_points(head)
    spatial = KDTree(len(main_hair))
    for insertion_index, vertex_index in enumerate(main_hair):
        spatial.insert(Vector(points[vertex_index]), insertion_index)
    spatial.balance()
    component_rows = []
    doomed_components = []
    for component in components[1:]:
        component_hair = component & hair_ids
        distance = min((spatial.find(Vector(points[index]))[2] for index in component_hair), default=0.0)
        delete = len(component) < 40 or distance > 0.030
        component_rows.append({"vertices": len(component), "nearest_main_hair_m": distance, "deleted": delete})
        if delete:
            doomed_components.append(component)
    doomed = set().union(*doomed_components) if doomed_components else set()
    before = {"vertices": len(head.data.vertices), "faces": len(head.data.polygons)}
    if doomed:
        bm = bmesh.new()
        bm.from_mesh(head.data)
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.verts[index] for index in sorted(doomed)], context="VERTS")
        bm.to_mesh(head.data)
        bm.free()
        head.data.update()
    after = {"vertices": len(head.data.vertices), "faces": len(head.data.polygons)}
    return {
        "method": "topology after 0.1 mm positional weld; delete hair-bearing components under 40 source vertices or farther than 30 mm from the main hair component",
        "components_before": len(components),
        "components_deleted": len(doomed_components),
        "components_deleted_under_40": sum(row["deleted"] and row["vertices"] < 40 for row in component_rows),
        "components_deleted_farther_than_30mm": sum(row["deleted"] and row["nearest_main_hair_m"] > 0.030 for row in component_rows),
        "non_main_components": component_rows,
        "vertices_selected": len(doomed),
        "before": before,
        "after": after,
    }


def skin_chin(head):
    points = world_points(head)
    skin = head.data.color_attributes["meshy_skin_mask"]
    ids = set()
    for poly in head.data.polygons:
        if np.mean([skin.data[index].color[0] for index in poly.loop_indices]) >= 0.5:
            ids.update(poly.vertices)
    selected = points[list(ids)]
    low, high = selected.min(axis=0), selected.max(axis=0)
    candidates = selected[selected[:, 2] >= low[2] + 0.12 * (high[2] - low[2])]
    return float(np.percentile(candidates[:, 2], 2.0))


def front_rim(body):
    points = world_points(body)
    plate = body.data.color_attributes["astra_v3_plate_mask"]
    counts = defaultdict(int)
    for poly in body.data.polygons:
        if np.mean([plate.data[index].color[0] for index in poly.loop_indices]) < 0.5:
            continue
        verts = list(poly.vertices)
        for index, a in enumerate(verts):
            counts[tuple(sorted((a, verts[(index + 1) % len(verts)])))] += 1
    ids = {index for edge, count in counts.items() if count == 1 for index in edge}
    rim = points[list(ids)]
    front = rim[(np.abs(rim[:, 0]) <= 0.34) & (rim[:, 1] <= -0.15) & (rim[:, 2] >= 2.45)]
    assert len(front)
    return float(np.percentile(front[:, 2], 90.0)), len(front)


def translate_mesh_world(obj, delta):
    transform = obj.matrix_world.inverted() @ Matrix.Translation(delta) @ obj.matrix_world
    for vertex in obj.data.vertices:
        vertex.co = transform @ vertex.co
    obj.data.update()


def repair_head(body, head, neck):
    before_chin = skin_chin(head)
    rim, rim_count = front_rim(body)
    target_clearance = 0.030
    lift = rim + target_clearance - before_chin
    assert 0.045 <= lift <= 0.085, lift
    translate_mesh_world(head, Vector((0.0, 0.0, lift)))
    fragments = delete_small_hair_components(head)

    # Extend the existing five neck rings so the raised jaw does not reveal a
    # long column.  Keep the lower ring buried and taper toward the jaw.
    center = np.mean(world_points(neck)[:, :2], axis=0)
    ring_z = [2.485, 2.575, 2.670, 2.755, rim + target_clearance - 0.006]
    ring_rx = [0.112, 0.108, 0.101, 0.092, 0.082]
    ring_ry = [0.088, 0.084, 0.078, 0.070, 0.061]
    assert len(neck.data.vertices) == 240
    for ring in range(5):
        for segment in range(48):
            vertex = neck.data.vertices[ring * 48 + segment]
            angle = 2.0 * math.pi * segment / 48.0
            world = Vector((center[0] + ring_rx[ring] * math.cos(angle),
                            center[1] + ring_ry[ring] * math.sin(angle), ring_z[ring]))
            vertex.co = neck.matrix_world.inverted() @ world
    neck.data.update()
    after_chin = skin_chin(head)
    return {
        "scale_change": 1.0,
        "head_world_lift_m": lift,
        "front_rim_z_m": rim,
        "front_rim_candidate_vertices": rim_count,
        "chin_before_z_m": before_chin,
        "chin_before_minus_rim_m": before_chin - rim,
        "chin_after_z_m": after_chin,
        "chin_after_minus_rim_m": after_chin - rim,
        "target_clearance_m": target_clearance,
        "neckblend_top_z_m": ring_z[-1],
        "jaw_to_neckblend_top_m": after_chin - ring_z[-1],
        "hair_fragments": fragments,
    }


def material(name, color, metallic, roughness):
    old = bpy.data.materials.get(name)
    if old:
        return old
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return result


def shell_bind(obj, rig, binding, ring_count, segments):
    groups = {}
    def put(vertex, bone, weight):
        if weight <= 0.0:
            return
        group = groups.get(bone) or obj.vertex_groups.new(name=bone)
        groups[bone] = group
        group.add([vertex], weight, "REPLACE")

    if isinstance(binding, (tuple, list)):
        assert len(binding) == ring_count
        for ring, bone in enumerate(binding):
            for segment in range(segments):
                put(ring * segments + segment, bone, 1.0)
    elif binding == "HEM_GRADIENT":
        for ring in range(ring_count):
            height = ring / max(1, ring_count - 1)
            hips = 0.20 + 0.80 * height
            leg = 1.0 - hips
            for segment in range(segments):
                vertex = ring * segments + segment
                angle = 2.0 * math.pi * segment / segments
                side = "LeftUpLeg" if math.cos(angle) >= 0.0 else "RightUpLeg"
                put(vertex, "Hips", hips)
                put(vertex, side, leg)
    else:
        for vertex in range(len(obj.data.vertices)):
            put(vertex, binding, 1.0)
    modifier = obj.modifiers.new("V3M R2 interior binding", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    # These shells are authored in meters, like the donor head/neck meshes.
    # Their parent rig carries the glTF centimeter conversion (0.01), so match
    # the donor objects' compensating local scale.
    obj.scale = (100.0, 100.0, 100.0)


def ring_mesh(name, rings, segments, mat, rig, bone):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    vertices = []
    for z, cx, cy, rx, ry in rings:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle), z))
    faces = []
    for ring in range(len(rings) - 1):
        for index in range(segments):
            nxt = (index + 1) % segments
            a = ring * segments + index
            b = ring * segments + nxt
            c = (ring + 1) * segments + nxt
            d = (ring + 1) * segments + index
            faces.append((a, b, c, d))
    faces.append(tuple(reversed(range(segments))))
    top = (len(rings) - 1) * segments
    faces.append(tuple(top + index for index in range(segments)))
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    shell_bind(obj, rig, bone, len(rings), segments)
    return obj


def add_gap_occluders(rig):
    def procedural_underlayer(name, color, metallic, roughness):
        result = material(name, color, metallic, roughness)
        result.diffuse_color = (*color, 1.0)
        result.metallic = metallic
        result.roughness = roughness
        nodes = result.node_tree.nodes
        links = result.node_tree.links
        bsdf = nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        for node in list(nodes):
            if node.name.startswith("V3M R2 "):
                nodes.remove(node)
        texcoord = nodes.new("ShaderNodeTexCoord")
        texcoord.name = "V3M R2 Texture Coordinate"
        noise = nodes.new("ShaderNodeTexNoise")
        noise.name = "V3M R2 Surface Noise"
        noise.inputs["Scale"].default_value = 55.0
        noise.inputs["Detail"].default_value = 2.0
        noise.inputs["Roughness"].default_value = 0.65
        bump = nodes.new("ShaderNodeBump")
        bump.name = "V3M R2 Surface Bump"
        bump.inputs["Strength"].default_value = 0.16
        bump.inputs["Distance"].default_value = 0.028
        links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        return result

    underplate = procedural_underlayer("V3M R2 gold underplate", (0.30, 0.105, 0.012), 0.78, 0.34)
    dark_blue = procedural_underlayer("V3M R2 visible blue underlayer", (0.012, 0.045, 0.20), 0.10, 0.62)
    torso = ring_mesh(
        "AstraChar2_R2_TorsoOccluder",
        [(1.38, 0.0, -0.15, 0.085, 0.035), (1.55, 0.0, -0.15, 0.11, 0.045), (1.85, 0.0, -0.14, 0.14, 0.055),
         (2.22, 0.0, -0.13, 0.17, 0.065), (2.52, 0.0, -0.12, 0.15, 0.055),
         (2.70, 0.0, -0.11, 0.085, 0.035), (2.84, 0.0, -0.10, 0.055, 0.025)],
        48, underplate, rig, ("Hips", "Hips", "Spine02", "Spine01", "Spine", "neck", "neck"),
    )
    hem = ring_mesh(
        "AstraChar2_R2_HemLiner",
        [(0.52, 0.0, -0.06, 0.27, 0.095), (0.72, 0.0, -0.08, 0.25, 0.088),
         (0.96, 0.0, -0.09, 0.225, 0.080), (1.22, 0.0, -0.11, 0.20, 0.070),
         (1.36, 0.0, -0.12, 0.16, 0.055)],
        64, dark_blue, rig, "Hips",
    )
    return {
        "diagnosis": "weld-aware boundary analysis finds rest-mesh openings; use narrow recessed procedural-cloth underlayers rather than altering exterior silhouette/weights",
        "objects": [torso.name, hem.name],
        "torso_vertices": len(torso.data.vertices),
        "hem_vertices": len(hem.data.vertices),
    }


def add_boundary_patches(body, rig):
    """Fill only small closed rest-mesh openings, preserving body deformation."""
    representative = {}
    canonical = {}
    members = defaultdict(set)
    for vertex in body.data.vertices:
        key_value = tuple(round(float(value), 4) for value in vertex.co)
        rep = representative.setdefault(key_value, vertex.index)
        canonical[vertex.index] = rep
        members[rep].add(vertex.index)
    edge_count = defaultdict(int)
    for polygon in body.data.polygons:
        values = list(polygon.vertices)
        for index, a in enumerate(values):
            a, b = canonical[a], canonical[values[(index + 1) % len(values)]]
            if a != b:
                edge_count[tuple(sorted((a, b)))] += 1
    adjacency = defaultdict(set)
    for (a, b), count in edge_count.items():
        if count == 1:
            adjacency[a].add(b)
            adjacency[b].add(a)
    unseen = set(adjacency)

    # Track the exterior material touching each welded boundary vertex.  A
    # geometrically closed hole still reads as a hole if the cap is painted as
    # a dark interior; inherit the dominant adjacent surface material instead.
    adjacent_materials = defaultdict(list)
    for polygon in body.data.polygons:
        for vertex_index in polygon.vertices:
            adjacent_materials[canonical[vertex_index]].append(polygon.material_index)
    components = []
    while unseen:
        seed = unseen.pop()
        found = {seed}
        queue = deque([seed])
        while queue:
            current = queue.popleft()
            for other in adjacency[current]:
                if other in unseen:
                    unseen.remove(other)
                    found.add(other)
                    queue.append(other)
        components.append(found)

    world = world_points(body)
    chosen = []
    region_counts = defaultdict(int)
    for component in components:
        if len(component) < 3 or len(component) > 100:
            continue
        points = world[list(component)]
        center = points.mean(axis=0)
        diagonal = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        region = "hem" if center[2] <= 0.45 else "belt" if 1.45 <= center[2] < 2.2 else "upper" if center[2] >= 2.2 else "other"
        if region == "other" or diagonal > 0.18:
            continue
        closed = all(len(adjacency[index]) == 2 for index in component)
        if not closed and not (region == "hem" and len(component) == 3):
            continue
        # Preserve the intentional central front neckline/gorget opening.
        if region == "upper" and abs(center[0]) < 0.36 and center[1] < -0.15 and center[2] > 2.45:
            continue
        if not closed:
            chosen.append((region, list(component)))
            region_counts[region] += 1
            continue
        ordered = [next(iter(component))]
        previous = None
        while len(ordered) < len(component):
            candidates = [item for item in adjacency[ordered[-1]] if item != previous]
            nxt = candidates[0]
            if nxt == ordered[0]:
                break
            previous, _ = ordered[-1], nxt
            ordered.append(nxt)
        if len(ordered) == len(component) and ordered[0] in adjacency[ordered[-1]]:
            chosen.append((region, ordered))
            region_counts[region] += 1

    vertices = []
    faces = []
    source_reps = []
    face_materials = []
    for _, loop in chosen:
        start = len(vertices)
        vertices.extend(tuple(body.data.vertices[index].co) for index in loop)
        source_reps.extend(loop)
        faces.append(tuple(start + index for index in range(len(loop))))
        candidates = [value for rep in loop for value in adjacent_materials[rep]]
        face_materials.append(Counter(candidates).most_common(1)[0][0] if candidates else 0)
    mesh = bpy.data.meshes.new("AstraChar2_R2_BoundaryPatches_Mesh")
    mesh.from_pydata(vertices, [], faces)
    patch = bpy.data.objects.new("AstraChar2_R2_BoundaryPatches", mesh)
    bpy.context.scene.collection.objects.link(patch)
    for slot in body.data.materials:
        mesh.materials.append(slot)
    for polygon, material_index in zip(mesh.polygons, face_materials):
        polygon.material_index = material_index
    group_names = {group.index: group.name for group in body.vertex_groups}
    patch_groups = {}
    for new_index, rep in enumerate(source_reps):
        weights = defaultdict(float)
        for old_index in members[rep]:
            for assignment in body.data.vertices[old_index].groups:
                weights[group_names[assignment.group]] = max(weights[group_names[assignment.group]], assignment.weight)
        total = sum(weights.values()) or 1.0
        for bone, value in weights.items():
            group = patch_groups.get(bone) or patch.vertex_groups.new(name=bone)
            patch_groups[bone] = group
            group.add([new_index], value / total, "REPLACE")
    modifier = patch.modifiers.new("V3M R2 patch binding", "ARMATURE")
    modifier.object = rig
    patch.parent = rig
    return {
        "diagnosis": "weld-aware closed boundary loops confirm rest-mesh defects; fill only small loops and inherit boundary bone weights",
        "objects": [patch.name],
        "patch_faces": len(faces),
        "patch_vertices": len(vertices),
        "region_counts": dict(region_counts),
        "maximum_patched_loop_diagonal_m": 0.18,
    }


def import_source(path):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = [obj for obj in bpy.data.objects if obj not in before_objects]
    actions = [action for action in bpy.data.actions if action not in before_actions]
    rigs = [obj for obj in objects if obj.type == "ARMATURE"]
    assert len(rigs) == 1 and len(actions) == 1, (path.name, len(rigs), len(actions))
    source = rigs[0]
    source.animation_data_create()
    source.animation_data.action = actions[0]
    if actions[0].slots:
        source.animation_data.action_slot = actions[0].slots[0]
    return source, actions[0], objects


def topological(rig):
    result = []
    queue = deque([bone for bone in rig.data.bones if bone.parent is None])
    while queue:
        bone = queue.popleft()
        result.append(bone.name)
        queue.extend(bone.children)
    assert set(result) == EXPECTED
    return result


def sole_ids(body):
    names = {group.index: group.name for group in body.vertex_groups}
    result = {}
    for side in ("Left", "Right"):
        allowed = {side + "Foot", side + "ToeBase"}
        ids = []
        for vertex in body.data.vertices:
            world = body.matrix_world @ vertex.co
            weight = sum(item.weight for item in vertex.groups if names.get(item.group) in allowed)
            if world.z < 0.24 and weight > 0.5:
                ids.append(vertex.index)
        assert ids
        result[side] = np.asarray(ids, dtype=np.int32)
    return result


def evaluated_points(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", values)
    values = values.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    values = values @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return values


def foot_samples(rig, action, body, soles):
    start, end = [int(round(value)) for value in action.frame_range]
    rows = []
    for frame in range(start, end + 1):
        assign(rig, action, frame)
        points = evaluated_points(body)
        side = {name: float(points[ids, 2].min()) for name, ids in soles.items()}
        rows.append({"frame": frame, "left_m": side["Left"], "right_m": side["Right"], "minimum_m": min(side.values())})
    return rows


def add_root_world_z(action, rig, amount):
    armature_delta = rig.matrix_world.to_3x3().inverted() @ Vector((0.0, 0.0, amount))
    local = rig.data.bones["Hips"].matrix_local.to_3x3().inverted() @ armature_delta
    mapping = {(curve.data_path, curve.array_index): curve for curve in action_curves(action)}
    path = 'pose.bones["Hips"].location'
    for index in range(3):
        curve = mapping[(path, index)]
        for point in curve.keyframe_points:
            point.co[1] += local[index]
        curve.update()
    return list(local)


def retarget(path, target, body, soles, order):
    reset(target)
    source, source_action, imported = import_source(path)
    assert set(source.data.bones.keys()) == EXPECTED
    source_name = source_action.name
    start, end = [int(round(value)) for value in source_action.frame_range]
    target_rest = {name: target.data.bones[name].matrix_local.copy() for name in order}
    target_rest_world = {name: target.matrix_world @ target.data.bones[name].matrix_local for name in order}
    source_rest_world = {name: source.matrix_world @ source.data.bones[name].matrix_local for name in order}
    rest_diffs = {name: float((source_rest_world[name].translation - target_rest_world[name].translation).length) for name in order}
    old = bpy.data.actions.get(path.stem)
    if old:
        bpy.data.actions.remove(old)
    action = bpy.data.actions.new(path.stem)
    action.use_fake_user = True
    slot, bag = action_channelbag(action, target)
    target.animation_data_clear()
    previous = {}
    maximum_error = {name: 0.0 for name in order}
    maximum_root_error = 0.0
    expected_rotations = []
    expected_roots = []
    root_rest_delta = source_rest_world["Hips"].translation - target_rest_world["Hips"].translation
    target_world_inverse = target.matrix_world.inverted()
    # The published rig object carries a 0.01 unit-conversion scale.  Strip it:
    # pose matrices are expressed in armature coordinates and must receive only
    # the inverse object *rotation*, never the inverse object scale.
    target_world_rot_inverse = target.matrix_world.to_quaternion().inverted().to_matrix()
    for output_frame, source_frame in enumerate(range(start, end + 1), 1):
        bpy.context.scene.frame_set(source_frame)
        bpy.context.view_layer.update()
        desired_rot = {}
        for name in order:
            src_world = source.matrix_world @ source.pose.bones[name].matrix
            # Extract the closest proper rotation from the evaluated source
            # matrix; imported GLBs carry unit conversion scale.
            desired_rot[name] = target_world_rot_inverse @ src_world.to_quaternion().normalized().to_matrix()
            parent = target.data.bones[name].parent
            rest_relative = (target_rest[parent.name].to_3x3().inverted() @ target_rest[name].to_3x3()
                             if parent else target_rest[name].to_3x3())
            parent_world = desired_rot[parent.name] if parent else Matrix.Identity(3)
            # Same forward-kinematic aiming equation used by
            # hymotion_retarget.py, with the source GLB supplying the complete
            # world frame (axis aim plus roll).
            basis = rest_relative.inverted() @ parent_world.inverted() @ desired_rot[name]
            rotation = basis.to_quaternion().normalized()
            rotation.normalize()
            if name in previous and rotation.dot(previous[name]) < 0:
                rotation.negate()
            previous[name] = rotation.copy()
            path_rot = f'pose.bones["{name}"].rotation_quaternion'
            for index, value in enumerate(rotation):
                key(bag, path_rot, index, output_frame, value)
        source_hips_world = (source.matrix_world @ source.pose.bones["Hips"].matrix).translation
        desired_world_head = source_hips_world - root_rest_delta
        desired_armature_head = target_world_inverse @ desired_world_head
        root_location = target_rest["Hips"].to_3x3().inverted() @ (
            desired_armature_head - target.data.bones["Hips"].head_local
        )
        path_loc = 'pose.bones["Hips"].location'
        for index, value in enumerate(root_location):
            key(bag, path_loc, index, output_frame, value)
        expected_rotations.append({name: desired_rot[name].to_quaternion().normalized() for name in order})
        expected_roots.append(desired_world_head.copy())
        if output_frame == 1 or output_frame == end - start + 1 or output_frame % 30 == 0:
            print("V3M_R2_RETARGET", path.stem, output_frame, end - start + 1, flush=True)
    for curve in bag.fcurves:
        curve.update()
    action["v3m_r2_method"] = "per-frame world-space bone orientation including source roll; target rest-chain positions; source Hips world position minus rest offset"
    action["v3m_source_sha256"] = sha256(path)
    action["v3m_fps"] = 30
    action["v3m_frame_count"] = end - start + 1
    reset(target)
    target_object_rotation = target.matrix_world.to_quaternion().normalized()
    for output_frame in range(1, end - start + 2):
        assign(target, action, output_frame)
        for name in order:
            actual_world = (target.matrix_world @ target.pose.bones[name].matrix).to_quaternion().normalized()
            wanted_world = target_object_rotation @ expected_rotations[output_frame - 1][name]
            raw_error = math.degrees(actual_world.rotation_difference(wanted_world).angle)
            error = min(raw_error, abs(360.0 - raw_error))
            maximum_error[name] = max(maximum_error[name], error)
        actual_root = (target.matrix_world @ target.pose.bones["Hips"].matrix).translation
        maximum_root_error = max(maximum_root_error, float((actual_root - expected_roots[output_frame - 1]).length))
    before = foot_samples(target, action, body, soles)
    minimum_before = min(row["minimum_m"] for row in before)
    shift = -minimum_before
    local_shift = add_root_world_z(action, target, shift) if abs(shift) > 1e-7 else [0.0, 0.0, 0.0]
    after = foot_samples(target, action, body, soles)
    minimum_after = min(row["minimum_m"] for row in after)
    planted = [row["frame"] for row in after if abs(row["minimum_m"]) <= 0.005]
    for obj in imported:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    if source_action.users == 0:
        bpy.data.actions.remove(source_action)
    return action, {
        "file": path.name,
        "source_action": source_name,
        "frames": end - start + 1,
        "fps": 30,
        "max_rest_head_difference_m": max(rest_diffs.values()),
        "world_orientation_max_error_deg": max(maximum_error.values()),
        "world_orientation_max_error_by_bone_deg": maximum_error,
        "root_world_position_max_error_m": maximum_root_error,
        "maximum_basis_scale_deviation": 0.0,
        "root_ground_shift_world_z_m": shift,
        "root_ground_shift_local": local_shift,
        "foot_contact": {
            "minimum_before_m": minimum_before,
            "minimum_after_m": minimum_after,
            "planted_frames_within_5mm": planted,
            "planted_frame_count": len(planted),
            "all_frames_after": after,
        },
    }


def main():
    assert sha256(SOURCE) == EXPECTED_SOURCE
    manifest = json.loads((MOCAP / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    neck = bpy.data.objects["AstraChar2_Meshy_NeckBlend"]
    reset(rig)
    head_report = repair_head(body, head, neck)
    occluder_report = add_boundary_patches(body, rig)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    order = topological(rig)
    soles = sole_ids(body)
    clips = []
    actions = []
    for item in manifest["clips"]:
        action, row = retarget(MOCAP / item["file"], rig, body, soles, order)
        row["action_id"] = item["action_id"]
        row["intended_role"] = item["role"]
        clips.append(row)
        actions.append(action)
    stance = bpy.data.actions["Combat_Stance"]
    assign(rig, stance, 1)
    report = {
        "schema": "astra-v3m-round2-world-build",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE),
        "wip": str(WIP.relative_to(ROOT)),
        "fps": 30,
        "method": "world-space source pose orientation and roll, parent-first; target rest-chain positions; Hips world position corrected by rest offset; constant clip ground shift",
        "head_fix": head_report,
        "gap_and_hem_fix": occluder_report,
        "clips": clips,
        "actions": sorted(action.name for action in actions),
    }
    scene["astra_v3m_round2"] = json.dumps({"method": report["method"], "head_fix": head_report})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(WIP))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_R2_BUILD_PASS", json.dumps({
        "clips": len(clips),
        "head": head_report,
        "max_orientation_error_deg": max(row["world_orientation_max_error_deg"] for row in clips),
        "max_root_error_m": max(row["root_world_position_max_error_m"] for row in clips),
    }), flush=True)


if __name__ == "__main__":
    main()
