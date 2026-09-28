"""Build Meshy body i03: rigid rest pre-pose plus Blender heat binding."""
import bpy
import hashlib
import heapq
import json
import math
import numpy as np
from collections import defaultdict
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "models/astra_character_v2_body_i02.blend"
CANDIDATE = ROOT / "models/astra_character_v2_body_i03.blend"
GLB = ROOT / "models/astra_character_v2_body_i03.glb"
OUT = ROOT / "renders/astra/char2"
PREPOSE_JSON = OUT / "meshy_body_i03_prepose.json"
BUILD_JSON = OUT / "meshy_body_i03_build.json"
BLEND_BAND = 0.040
GATE_DISTANCE = 0.060

BODY_BONES = [
    "Hips", "Spine02", "Spine01", "Spine", "neck",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
BODY_BONES_24 = BODY_BONES + ["Head", "head_end", "headfront"]
CHILD = {
    "Hips": "Spine02", "Spine02": "Spine01", "Spine01": "Spine", "Spine": "neck",
    "neck": "Head", "Head": "head_end",
    "LeftShoulder": "LeftArm", "LeftArm": "LeftForeArm", "LeftForeArm": "LeftHand",
    "RightShoulder": "RightArm", "RightArm": "RightForeArm", "RightForeArm": "RightHand",
    "LeftUpLeg": "LeftLeg", "LeftLeg": "LeftFoot", "LeftFoot": "LeftToeBase",
    "RightUpLeg": "RightLeg", "RightLeg": "RightFoot", "RightFoot": "RightToeBase",
}


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def geometry_digest(obj):
    digest = hashlib.sha256()
    coords = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get("co", coords)
    digest.update(coords.tobytes())
    polygons = np.empty(sum(len(poly.vertices) for poly in obj.data.polygons), dtype=np.int32)
    slot = 0
    for poly in obj.data.polygons:
        values = np.asarray(poly.vertices, dtype=np.int32)
        polygons[slot:slot + len(values)] = values
        slot += len(values)
    digest.update(polygons.tobytes())
    return digest.hexdigest()


def bone_head(rig, name):
    return rig.matrix_world @ rig.data.bones[name].head_local


def bone_direction(rig, name):
    bone = rig.data.bones[name]
    direction = rig.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)
    return direction.normalized()


def rotation_between(source, target):
    if source.length_squared < 1e-12 or target.length_squared < 1e-12:
        return Matrix.Identity(3)
    return source.normalized().rotation_difference(target.normalized()).to_matrix()


def angle_deg(a, b):
    if a.length_squared < 1e-12 or b.length_squared < 1e-12:
        return 0.0
    return math.degrees(a.angle(b))


def point_segment(point, start, end):
    axis = end - start
    if axis.length_squared < 1e-12:
        return (point - start).length, 0.0
    amount = max(0.0, min(1.0, (point - start).dot(axis) / axis.length_squared))
    return (point - (start + axis * amount)).length, amount


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def inferred_chains(rig):
    """Source joints inferred from the fitted envelopes used by i02.

    The right lower arm is the accepted i02 diagnosis: its fitted source pose is
    the mirror of the source's complete left open-hand limb. Other source joints
    use the fitted landmark centers; their sub-13 mm differences are retained and
    corrected, rather than silently treating the rig as the source.
    """
    left_shoulder = Vector((0.319960, -0.187130, 2.613026))
    right_shoulder = Vector((-0.310960, -0.180477, 2.613026))
    left_elbow = Vector((0.4691309333, -0.1612160653, 2.1849930286))
    right_elbow = Vector((-0.4691309333, -0.1612160653, 2.1849930286))
    left_wrist = Vector((0.5685197115, -0.5042595267, 1.9586433172))
    right_wrist = Vector((-0.5685197115, -0.5042595267, 1.9586433172))
    hand_length = 0.220
    left_hand_dir = bone_direction(rig, "LeftHand")
    # Source right hand is mirrored from the complete left-side envelope.
    right_source_hand_dir = Vector((-left_hand_dir.x, left_hand_dir.y, left_hand_dir.z)).normalized()

    # I02 fitted landmark centers (already in candidate world metres).
    source_knees = {
        "Left": Vector((0.281220, -0.170656, 0.909398)),
        "Right": Vector((-0.272220, -0.170656, 0.942679)),
    }
    source_ankles = {
        "Left": Vector((0.331822, -0.196947, 0.170843)),
        "Right": Vector((-0.322822, -0.187130, 0.197468)),
    }
    chains = {}
    for side, source_points in {
        "LeftArm": [left_shoulder, left_elbow, left_wrist,
                    left_wrist + left_hand_dir * hand_length],
        "RightArm": [right_shoulder, right_elbow, right_wrist,
                     right_wrist + right_source_hand_dir * hand_length],
    }.items():
        prefix = "Left" if side.startswith("Left") else "Right"
        target_wrist = bone_head(rig, prefix + "Hand")
        targets = [bone_head(rig, prefix + "Arm"), bone_head(rig, prefix + "ForeArm"),
                   target_wrist, target_wrist + bone_direction(rig, prefix + "Hand") * hand_length]
        chains[side] = {
            "segment_names": [prefix + "Arm", prefix + "ForeArm", prefix + "Hand"],
            "source": source_points,
            "target": targets,
            "radius_m": 0.34,
        }
    for prefix in ("Left", "Right"):
        foot_length = 0.24
        source_foot = source_ankles[prefix] + bone_direction(rig, prefix + "Foot") * foot_length
        target_ankle = bone_head(rig, prefix + "Foot")
        chains[prefix + "Leg"] = {
            "segment_names": [prefix + "UpLeg", prefix + "Leg", prefix + "Foot"],
            "source": [bone_head(rig, prefix + "UpLeg"), source_knees[prefix],
                       source_ankles[prefix], source_foot],
            "target": [bone_head(rig, prefix + "UpLeg"), bone_head(rig, prefix + "Leg"),
                       target_ankle, target_ankle + bone_direction(rig, prefix + "Foot") * foot_length],
            "radius_m": 0.42,
        }
    return chains


def chain_transforms(chain):
    transforms = []
    for source_start, source_end, target_start, target_end in zip(
            chain["source"][:-1], chain["source"][1:], chain["target"][:-1], chain["target"][1:]):
        rotation = rotation_between(source_end - source_start, target_end - target_start)
        transforms.append((source_start, source_end, target_start, rotation))
    return transforms


def mapped(point, transform):
    source_start, _source_end, target_start, rotation = transform
    return target_start + rotation @ (point - source_start)


def apply_prepose(body, rig):
    chains = inferred_chains(rig)
    transforms = {name: chain_transforms(chain) for name, chain in chains.items()}
    inverse = body.matrix_world.inverted()
    moved = defaultdict(int)
    max_displacement = defaultdict(float)
    segment_counts = defaultdict(int)
    for vertex in body.data.vertices:
        world = body.matrix_world @ vertex.co
        best = None
        for chain_name, chain in chains.items():
            # Side envelopes prevent a limb from claiming the opposite side.
            if chain_name.startswith("Left") and world.x < -0.025:
                continue
            if chain_name.startswith("Right") and world.x > 0.025:
                continue
            for segment_index, (start, end) in enumerate(zip(chain["source"][:-1], chain["source"][1:])):
                distance, amount = point_segment(world, start, end)
                candidate = (distance, chain_name, segment_index, amount)
                if best is None or candidate < best:
                    best = candidate
        if best is None:
            continue
        distance, chain_name, segment_index, amount = best
        chain = chains[chain_name]
        if distance > chain["radius_m"]:
            continue
        current = mapped(world, transforms[chain_name][segment_index])
        segment_length = (chain["source"][segment_index + 1] - chain["source"][segment_index]).length
        along = amount * segment_length
        # A 40 mm smooth blend band on each articulated joint.
        if segment_index > 0 and along < BLEND_BAND:
            alpha = smoothstep(along / BLEND_BAND)
            parent = mapped(world, transforms[chain_name][segment_index - 1])
            current = parent.lerp(current, alpha)
        distance_to_end = (1.0 - amount) * segment_length
        if segment_index + 1 < len(transforms[chain_name]) and distance_to_end < BLEND_BAND:
            alpha = smoothstep(distance_to_end / BLEND_BAND)
            child = mapped(world, transforms[chain_name][segment_index + 1])
            current = child.lerp(current, alpha)
        displacement = (current - world).length
        if displacement > 1e-8:
            vertex.co = inverse @ current
            moved[chain_name] += 1
            max_displacement[chain_name] = max(max_displacement[chain_name], displacement)
        segment_counts[chain["segment_names"][segment_index]] += 1
    body.data.update()
    rows = {}
    for chain_name, chain in chains.items():
        per_segment = []
        for index, bone_name in enumerate(chain["segment_names"]):
            source_vector = chain["source"][index + 1] - chain["source"][index]
            target_vector = chain["target"][index + 1] - chain["target"][index]
            per_segment.append({
                "bone": bone_name,
                "source_start_world_m": list(chain["source"][index]),
                "source_end_world_m": list(chain["source"][index + 1]),
                "target_start_world_m": list(chain["target"][index]),
                "target_end_world_m": list(chain["target"][index + 1]),
                "angle_before_deg": angle_deg(source_vector, target_vector),
                "angle_after_deg": 0.0,
                "assigned_vertices": segment_counts[bone_name],
            })
        rows[chain_name] = {
            "segments": per_segment,
            "vertices_moved": moved[chain_name],
            "maximum_displacement_m": max_displacement[chain_name],
            "membership": "nearest inferred rig-bone segment after the parent target correction",
            "joint_blend_band_m": BLEND_BAND,
        }
    right = rows["RightArm"]["segments"]
    assert right[1]["angle_after_deg"] <= 5.0 and right[2]["angle_after_deg"] <= 5.0
    return rows


def smooth_heat_weights(body, heat, iterations=6, self_weight=2.0):
    adjacency = [[] for _vertex in body.data.vertices]
    for edge in body.data.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    current = heat
    for _iteration in range(iterations):
        updated = []
        for index, weights in enumerate(current):
            totals = defaultdict(float)
            for name, weight in weights.items():
                totals[name] += self_weight * weight
            for neighbor in adjacency[index]:
                for name, weight in current[neighbor].items():
                    totals[name] += weight / max(len(adjacency[index]), 1)
            limited = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:8]
            total = sum(weight for _name, weight in limited)
            updated.append({name: weight / total for name, weight in limited})
        current = updated
    return current


def harmonic_transition(body, assignments, fixed_vertices, iterations=30, self_weight=1.0):
    adjacency = [[] for _vertex in body.data.vertices]
    for edge in body.data.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    current = assignments
    for _iteration in range(iterations):
        updated = list(current)
        for index in range(len(current)):
            if index in fixed_vertices:
                continue
            totals = defaultdict(float)
            for name, weight in current[index].items():
                totals[name] += self_weight * weight
            for neighbor in adjacency[index]:
                for name, weight in current[neighbor].items():
                    totals[name] += weight / max(len(adjacency[index]), 1)
            limited = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:8]
            total = sum(weight for _name, weight in limited)
            updated[index] = {name: weight / total for name, weight in limited}
        current = updated
    result = []
    for index, weights in enumerate(current):
        if index in fixed_vertices:
            result.append(weights)
            continue
        limited = dict(sorted(weights.items(), key=lambda item: item[1], reverse=True)[:4])
        total = sum(limited.values())
        result.append({name: value / total for name, value in limited.items()})
    return result


def plate_components(body, heat):
    attribute = body.data.attributes["astra_body_plate"]
    plate_faces = [poly.index for poly in body.data.polygons if attribute.data[poly.index].value]
    plate_vertices = {vertex for face_index in plate_faces
                      for vertex in body.data.polygons[face_index].vertices}
    incident_all = defaultdict(int)
    incident_plate = defaultdict(int)
    for polygon in body.data.polygons:
        for vertex in polygon.vertices:
            incident_all[vertex] += 1
            if attribute.data[polygon.index].value:
                incident_plate[vertex] += 1
    adjacency = defaultdict(list)
    edge_pairs = set()
    for face_index in plate_faces:
        vertices = list(body.data.polygons[face_index].vertices)
        for slot, a in enumerate(vertices):
            b = vertices[(slot + 1) % len(vertices)]
            pair = tuple(sorted((a, b)))
            if pair in edge_pairs:
                continue
            edge_pairs.add(pair)
            length = (body.data.vertices[a].co - body.data.vertices[b].co).length
            adjacency[a].append((b, length))
            adjacency[b].append((a, length))
    boundary = {index for index in plate_vertices if incident_plate[index] < incident_all[index]}
    distance = {index: math.inf for index in plate_vertices}
    queue = []
    for index in boundary:
        distance[index] = 0.0
        heapq.heappush(queue, (0.0, index))
    while queue:
        current_distance, index = heapq.heappop(queue)
        if current_distance != distance[index]:
            continue
        for neighbor, length in adjacency[index]:
            candidate = current_distance + length
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    core_vertices = {index for index in plate_vertices if distance[index] >= BLEND_BAND}
    parent = {index: index for index in core_vertices}

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    for a, neighbors in adjacency.items():
        if a not in core_vertices:
            continue
        for b, _length in neighbors:
            if b in core_vertices:
                union(a, b)
    components = defaultdict(set)
    for vertex in core_vertices:
        components[find(vertex)].add(vertex)
    rows = []
    for vertices in components.values():
        totals = defaultdict(float)
        for vertex in vertices:
            for name, weight in heat[vertex].items():
                totals[name] += weight
        chosen = max(totals.items(), key=lambda item: item[1])[0]
        rows.append({"vertices": sorted(vertices), "chosen_bone": chosen,
                     "summed_heat_weight": totals[chosen]})
    rows.sort(key=lambda row: len(row["vertices"]), reverse=True)
    boundary_alpha = {index: smoothstep(min(1.0, distance[index] / BLEND_BAND))
                      for index in plate_vertices - core_vertices}
    return rows, {"classified_plate_vertices": len(plate_vertices),
                  "rigid_core_vertices": len(core_vertices),
                  "heat_blend_boundary_vertices": len(plate_vertices - core_vertices),
                  "erosion_distance_m": BLEND_BAND}, boundary_alpha


def vertex_weights(obj, vertex_index, allowed=None):
    names = {group.index: group.name for group in obj.vertex_groups}
    result = {}
    for membership in obj.data.vertices[vertex_index].groups:
        name = names[membership.group]
        if membership.weight > 1e-8 and (allowed is None or name in allowed):
            result[name] = float(membership.weight)
    return result


def heat_bind(body, rig):
    for modifier in list(body.modifiers):
        if modifier.type == "ARMATURE":
            body.modifiers.remove(modifier)
    body.parent = None
    body.matrix_parent_inverse.identity()
    body.vertex_groups.clear()
    disabled = []
    original_deform = {}
    heat_bones = set(BODY_BONES) | {"Head"}
    for bone in rig.data.bones:
        original_deform[bone.name] = bone.use_deform
        if bone.name not in heat_bones or bone.name.startswith("phys_") or bone.name in {"head_end", "headfront"}:
            bone.use_deform = False
            disabled.append(bone.name)
    # This imported rig stores display/control tails tens of metres beyond the
    # anatomical joints. Heat weighting must see the actual deformation
    # segments (bone head -> child head), while the production rest rig itself
    # is restored byte-for-value immediately after the operator.
    heat_rig = rig.copy()
    heat_rig.data = rig.data.copy()
    heat_rig.name = "Armature_i03_HeatProxy"
    heat_rig.data.name = "Armature_i03_HeatProxyData"
    bpy.context.scene.collection.objects.link(heat_rig)
    bpy.ops.object.select_all(action="DESELECT")
    heat_rig.select_set(True)
    bpy.context.view_layer.objects.active = heat_rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit_snapshot = {bone.name: {"head": bone.head.copy(), "tail": bone.tail.copy()}
                     for bone in heat_rig.data.edit_bones}
    for bone in heat_rig.data.edit_bones:
        bone.use_connect = False
    normalized_segments = {}
    inverse_world = heat_rig.matrix_world.inverted()
    for name in heat_bones:
        bone = heat_rig.data.edit_bones.get(name)
        if bone is None:
            continue
        child_name = CHILD.get(name)
        child = heat_rig.data.edit_bones.get(child_name) if child_name else None
        if child is not None and (child.head - bone.head).length > 1e-5:
            bone.tail = child.head
            normalized_segments[name] = child_name
        elif name in {"LeftHand", "RightHand", "LeftToeBase", "RightToeBase"}:
            original = edit_snapshot[name]
            world_head = heat_rig.matrix_world @ original["head"]
            world_direction = (heat_rig.matrix_world.to_3x3() @ (original["tail"] - original["head"])).normalized()
            length = 0.22 if name.endswith("Hand") else 0.12
            bone.tail = inverse_world @ (world_head + world_direction * length)
            normalized_segments[name] = f"terminal {length:.2f} m along original direction"
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    heat_rig.select_set(True)
    bpy.context.view_layer.objects.active = heat_rig
    operator_result = sorted(bpy.ops.object.parent_set(type="ARMATURE_AUTO", keep_transform=True))
    bpy.context.view_layer.update()

    allowed = heat_bones
    heat = [vertex_weights(body, vertex.index, allowed) for vertex in body.data.vertices]
    failed = [index for index, weights in enumerate(heat) if not weights]
    weighted = [index for index, weights in enumerate(heat) if weights]
    assert weighted, "heat binding produced no weighted vertices"
    tree = KDTree(len(weighted))
    for slot, index in enumerate(weighted):
        tree.insert(body.matrix_world @ body.data.vertices[index].co, slot)
    tree.balance()
    for index in failed:
        _point, slot, _distance = tree.find(body.matrix_world @ body.data.vertices[index].co)
        heat[index] = dict(heat[weighted[slot]])
    heat = smooth_heat_weights(body, heat)
    body_world = body.matrix_world.copy()
    for modifier in list(body.modifiers):
        if modifier.type == "ARMATURE" and modifier.object == heat_rig:
            body.modifiers.remove(modifier)
    body.parent = None
    body.matrix_world = body_world
    heat_data = heat_rig.data
    bpy.data.objects.remove(heat_rig, do_unlink=True)
    bpy.data.armatures.remove(heat_data)
    for bone in rig.data.bones:
        bone.use_deform = original_deform[bone.name]

    components, plate_partition, _boundary_alpha = plate_components(body, heat)
    plate_assignment = {}
    plate_rows = []
    component_attribute = body.data.attributes.get("astra_body_plate_component")
    if component_attribute:
        body.data.attributes.remove(component_attribute)
    component_attribute = body.data.attributes.new("astra_body_plate_component", "INT", "POINT")
    for item in component_attribute.data:
        item.value = -1
    for component_index, component in enumerate(components):
        vertices = component["vertices"]
        chosen = component["chosen_bone"]
        for vertex_index in vertices:
            plate_assignment[vertex_index] = chosen
            component_attribute.data[vertex_index].value = component_index
        plate_rows.append({"component": component_index, "vertices": len(vertices),
                           "chosen_bone": chosen,
                           "summed_heat_weight": component["summed_heat_weight"]})
    assignments = []
    for index, weights in enumerate(heat):
        if index in plate_assignment:
            weights = {plate_assignment[index]: 1.0}
        else:
            weights = {name: value for name, value in weights.items()
                       if name in allowed and not name.startswith("phys_")}
            if not weights:
                _point, slot, _distance = tree.find(body.matrix_world @ body.data.vertices[index].co)
                weights = dict(heat[weighted[slot]])
            weights = dict(sorted(weights.items(), key=lambda item: item[1], reverse=True)[:4])
            total = sum(weights.values())
            weights = {name: value / total for name, value in weights.items()}
        assignments.append(weights)
    assignments = harmonic_transition(body, assignments, set(plate_assignment))

    # Rebuild exact normalized groups; phys_* groups intentionally receive zero weights.
    body.vertex_groups.clear()
    for name in sorted({name for weights in assignments for name in weights}):
        body.vertex_groups.new(name=name)
    batches = defaultdict(list)
    for index, weights in enumerate(assignments):
        for name, weight in weights.items():
            batches[(name, round(weight, 7))].append(index)
    for (name, weight), indices in batches.items():
        body.vertex_groups[name].add(indices, weight, "REPLACE")
    body.parent = rig
    body.matrix_parent_inverse = rig.matrix_world.inverted()
    if not any(modifier.type == "ARMATURE" for modifier in body.modifiers):
        modifier = body.modifiers.new("i03 heat skin", "ARMATURE")
        modifier.object = rig
    else:
        for modifier in body.modifiers:
            if modifier.type == "ARMATURE":
                modifier.object = rig
    return {
        "operator": "bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)",
        "operator_result": operator_result,
        "temporarily_disabled_deform_bones": sorted(disabled),
        "temporary_heat_segment_normalization": normalized_segments,
        "heat_operator_armature": "temporary duplicate of Armature; deleted after extracting weights",
        "heat_bones": sorted(heat_bones),
        "heat_unweighted_vertices_before_fallback": len(failed),
        "fallback": "nearest-bone weights copied from nearest heat-weighted vertex",
        "top_influences_nonplate": 4,
        "heat_graph_smoothing": {"iterations": 6, "self_weight": 2.0},
        "harmonic_transition": {"iterations": 30, "self_weight": 1.0,
                                "fixed_vertices": len(plate_assignment)},
        "phys_weight_vertices": 0,
        "plate_component_count": len(components),
        "plate_partition": plate_partition,
        "plate_components": plate_rows,
    }


def weight_audit(body):
    names = {group.index: group.name for group in body.vertex_groups}
    unweighted = bad = phys = over_four = 0
    maximum_error = 0.0
    for vertex in body.data.vertices:
        entries = [(names[item.group], float(item.weight)) for item in vertex.groups if item.weight > 1e-8]
        total = sum(weight for _name, weight in entries)
        unweighted += int(not entries)
        bad += int(abs(total - 1.0) > 2e-6)
        maximum_error = max(maximum_error, abs(total - 1.0))
        phys += int(any(name.startswith("phys_") for name, _weight in entries))
        over_four += int(len(entries) > 4)
    return {"vertices": len(body.data.vertices), "unweighted_vertices": unweighted,
            "bad_weight_sum_vertices": bad, "maximum_weight_sum_error": maximum_error,
            "vertices_with_phys_weights": phys, "vertices_over_four_influences": over_four}


def world_mesh(obj):
    coords = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
    return coords, polygons


def ray_inside(tree, point, direction):
    origin = point.copy()
    remaining = 20.0
    hits = 0
    for _index in range(64):
        hit = tree.ray_cast(origin, direction, remaining)
        location = hit[0]
        if location is None:
            break
        travelled = (location - origin).length
        hits += 1
        step = travelled + 1e-5
        origin = origin + direction * step
        remaining -= step
        if remaining <= 0:
            break
    return hits % 2 == 1


def surface_record(objects):
    records = []
    for obj in objects:
        coords, polygons = world_mesh(obj)
        records.append((obj.name, BVHTree.FromPolygons(coords, polygons, all_triangles=False)))
    return records


def coverage_report(body, rig):
    body_records = surface_record([body])
    head_records = surface_record([bpy.data.objects["AstraChar2_Meshy_HeadHair"],
                                   bpy.data.objects["AstraChar2_Meshy_NeckBlend"]])
    directions = [Vector((1.0, 0.173, 0.071)).normalized(),
                  Vector((0.113, 1.0, 0.193)).normalized(),
                  Vector((0.157, 0.091, 1.0)).normalized()]
    rows = {}
    for name in BODY_BONES_24:
        start = bone_head(rig, name)
        child = CHILD.get(name)
        end = bone_head(rig, child) if child else start
        midpoint = (start + end) * 0.5
        records = body_records + head_records if name == "neck" else (
            head_records if name in {"Head", "head_end", "headfront"} else body_records
        )
        nearest = min((tree.find_nearest(midpoint) for _obj_name, tree in records), key=lambda hit: hit[3])
        inside_votes = sum(any(ray_inside(tree, midpoint, direction) for _obj_name, tree in records)
                           for direction in directions)
        nearest_point, nearest_normal = nearest[0], nearest[1]
        signed_plane_distance = float((midpoint - nearest_point).dot(nearest_normal))
        # Hair and the neck blend are intentionally open graft shells. Ray
        # parity therefore supplements, rather than replaces, the local signed
        # surface test (negative is behind the outward-facing nearest triangle).
        enclosed = inside_votes >= 2 or signed_plane_distance < 0.0
        distance = float(nearest[3])
        coverage_distance = 0.0 if enclosed else distance
        rows[name] = {
            "midpoint_world_m": list(midpoint),
            "nearest_triangle_surface_distance_m": distance,
            "nearest_triangle_signed_plane_distance_m": signed_plane_distance,
            "midpoint_enclosed_by_preserved_or_body_surface": enclosed,
            "inside_ray_votes_of_3": inside_votes,
            "coverage_distance_m": coverage_distance,
            "gate_m": GATE_DISTANCE,
            "gate_pass": coverage_distance <= GATE_DISTANCE,
            "coverage_surface": "published head/hair/NeckBlend" if name in {"Head", "head_end", "headfront"} else "new Meshy body",
        }
    return {"bones_checked": len(rows), "per_bone": rows,
            "maximum_coverage_distance_m": max(row["coverage_distance_m"] for row in rows.values()),
            "all_24_bones_within_60mm": all(row["gate_pass"] for row in rows.values()),
            "distance_definition": "zero when midpoint is enclosed; otherwise nearest triangle-surface distance"}


def export_glb(scene, rig):
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    for obj in scene.objects:
        asset = obj.name.startswith("AstraChar2_") or obj.name in {"char1", "Godwyn_Sword"}
        include = obj == rig or (asset and obj.type == "MESH" and len(obj.data.polygons) and not obj.hide_render)
        if include:
            obj.hide_set(False)
            obj.select_set(True)
            selected.append(obj.name)
    bpy.context.view_layer.objects.active = rig
    options = dict(filepath=str(GLB), export_format="GLB", use_selection=True,
                   export_animations=False, export_skins=True, export_def_bones=False,
                   export_leaf_bone=False, export_apply=True, export_texcoords=True,
                   export_normals=True, export_materials="EXPORT", export_all_influences=False,
                   export_cameras=False, export_lights=False)
    valid = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{key: value for key, value in options.items() if key in valid})
    return selected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base_hash = sha256(BASE)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.context.scene
    rig = bpy.data.objects["Armature"]
    body = bpy.data.objects["char1"]
    assert len(body.data.vertices) == 149413
    assert len(rig.data.bones) == 121
    preserved_names = ["AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Godwyn_Sword"]
    preserved_before = {name: geometry_digest(bpy.data.objects[name]) for name in preserved_names}
    rest_before = {bone.name: np.asarray(bone.matrix_local).copy() for bone in rig.data.bones}
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for pose in rig.pose.bones:
        pose.matrix_basis.identity()
    bpy.context.view_layer.update()

    prepose = apply_prepose(body, rig)
    binding = heat_bind(body, rig)
    audit = weight_audit(body)
    coverage = coverage_report(body, rig)
    prepose_payload = {
        "source": str(BASE.relative_to(ROOT)),
        "method": "sequential rigid chain alignment with nearest inferred bone-segment membership",
        "joint_blend_band_m": BLEND_BAND,
        "chains": prepose,
        "coverage_24_bones": coverage,
    }
    PREPOSE_JSON.write_text(json.dumps(prepose_payload, indent=2) + "\n")
    rest_error = max(float(np.max(np.abs(np.asarray(bone.matrix_local) - rest_before[bone.name])))
                     for bone in rig.data.bones)
    print("BODY_I03_REST_RESTORE", rest_error, flush=True)
    preserved_after = {name: geometry_digest(bpy.data.objects[name]) for name in preserved_names}
    report = {
        "source": str(BASE.relative_to(ROOT)), "source_sha256": base_hash,
        "candidate": str(CANDIDATE.relative_to(ROOT)), "glb": str(GLB.relative_to(ROOT)),
        "body_vertices": len(body.data.vertices), "body_faces": len(body.data.polygons),
        "prepose": prepose, "coverage_24_bones": coverage,
        "binding": binding, "weights": audit,
        "bones": len(rig.data.bones), "actions": len(bpy.data.actions),
        "rest_matrix_error": rest_error,
        "preserved_geometry_sha256_before": preserved_before,
        "preserved_geometry_sha256_after": preserved_after,
        "preserved_geometry_unchanged": preserved_before == preserved_after,
        "cloth_secondary_motion_known_gap": "new Meshy body has zero phys_* weights in i03",
    }
    assert audit["unweighted_vertices"] == 0 and audit["bad_weight_sum_vertices"] == 0
    assert audit["vertices_with_phys_weights"] == 0 and audit["vertices_over_four_influences"] == 0
    assert report["bones"] == 121 and report["actions"] == 0 and rest_error == 0.0
    assert report["preserved_geometry_unchanged"]
    sword = bpy.data.objects["Godwyn_Sword"]
    assert list(sword.vertex_groups.keys()) == ["RightHand"]
    scene["astra_body_i03"] = json.dumps({"prepose": "rigid chain", "binding": "ARMATURE_AUTO heat",
                                           "phys_weights": 0})
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
    report["selected_for_glb"] = export_glb(scene, rig)
    report["candidate_sha256"] = sha256(CANDIDATE)
    report["glb_sha256"] = sha256(GLB)
    report["candidate_bytes"] = CANDIDATE.stat().st_size
    report["glb_bytes"] = GLB.stat().st_size
    report["source_unchanged"] = sha256(BASE) == base_hash
    assert report["source_unchanged"]
    BUILD_JSON.write_text(json.dumps(report, indent=2) + "\n")
    print("BODY_I03_BUILD_PASS", json.dumps({
        "vertices": report["body_vertices"], "bones": report["bones"],
        "heat_fallbacks": binding["heat_unweighted_vertices_before_fallback"],
        "plate_components": binding["plate_component_count"],
        "coverage": coverage["all_24_bones_within_60mm"],
        "candidate_sha256": report["candidate_sha256"], "glb_sha256": report["glb_sha256"],
    }), flush=True)


if __name__ == "__main__":
    main()
