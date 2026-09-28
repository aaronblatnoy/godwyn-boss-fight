"""Build Meshy body I04: split metal from soft topology, then bind separately."""
import bpy
import bmesh
import hashlib
import json
import numpy as np
from collections import defaultdict, deque
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/astra_character_v2_body_i03.blend"
CANDIDATE = ROOT / "models/astra_character_v2_body_i04.blend"
OUT = ROOT / "renders/astra/char2"
SPLIT_JSON = OUT / "meshy_body_i04_split.json"
BUILD_JSON = OUT / "meshy_body_i04_build.json"
MIN_ISLAND_VERTICES = 30
BELT_BLEND_M = 0.100
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
SASH_BONES = {"Spine", "Spine01", "Spine02", "LeftShoulder", "RightShoulder"}


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


def vertex_weights(obj, index, allowed=None):
    names = {group.index: group.name for group in obj.vertex_groups}
    result = {}
    for item in obj.data.vertices[index].groups:
        name = names[item.group]
        if item.weight > 1e-8 and (allowed is None or name in allowed):
            result[name] = float(item.weight)
    return result


def normalize(weights, limit=4, fallback="Hips"):
    filtered = [(name, value) for name, value in weights.items() if value > 1e-10]
    filtered.sort(key=lambda item: item[1], reverse=True)
    filtered = filtered[:limit]
    total = sum(value for _name, value in filtered)
    if total <= 1e-12:
        return {fallback: 1.0}
    return {name: value / total for name, value in filtered}


def rebuild_groups(obj, assignments):
    obj.vertex_groups.clear()
    for name in sorted({name for weights in assignments for name in weights}):
        obj.vertex_groups.new(name=name)
    batches = defaultdict(list)
    for index, weights in enumerate(assignments):
        for name, weight in weights.items():
            batches[(name, round(float(weight), 7))].append(index)
    for (name, weight), indices in batches.items():
        obj.vertex_groups[name].add(indices, weight, "REPLACE")


def purge_nonface_geometry(obj):
    """Remove edit-mode separation remnants that belong to no rendered face."""
    mesh = obj.data
    before = {"vertices": len(mesh.vertices), "edges": len(mesh.edges)}
    bm = bmesh.new()
    bm.from_mesh(mesh)
    doomed = [vertex for vertex in bm.verts if not vertex.link_faces]
    removed = len(doomed)
    if doomed:
        bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return {"before": before, "removed_vertices": removed,
            "after": {"vertices": len(mesh.vertices), "edges": len(mesh.edges)}}


def split_plate_from_soft(body):
    plate = body.data.attributes["astra_body_plate"]
    plate_faces = [poly.index for poly in body.data.polygons if plate.data[poly.index].value]
    assert plate_faces and len(plate_faces) < len(body.data.polygons)
    plate_face_set = set(plate_faces)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for poly in body.data.polygons:
        poly.select = poly.index in plate_face_set
    body.data.update()
    before = set(bpy.context.scene.objects)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    created = [obj for obj in set(bpy.context.scene.objects) - before if obj.type == "MESH"]
    assert len(created) == 1
    candidates = [body, created[0]]
    classified = []
    for obj in candidates:
        attribute = obj.data.attributes["astra_body_plate"]
        classified.append(sum(bool(attribute.data[poly.index].value)
                              for poly in obj.data.polygons))
    plate_slot = max(range(2), key=lambda slot: classified[slot])
    plate_obj = candidates[plate_slot]
    soft_obj = candidates[1 - plate_slot]
    soft_obj.name = "char1"
    soft_obj.data.name = "AstraBody_I04_SoftMesh"
    plate_obj.name = "AstraBody_I04_Plates"
    plate_obj.data.name = "AstraBody_I04_PlateMesh"
    cleanup = {"soft": purge_nonface_geometry(soft_obj),
               "plate": purge_nonface_geometry(plate_obj)}
    classified = []
    for obj in (soft_obj, plate_obj):
        attribute = obj.data.attributes["astra_body_plate"]
        classified.append(sum(bool(attribute.data[poly.index].value)
                              for poly in obj.data.polygons))
    split_counts = {"classified_soft_plate": classified,
                    "faces_soft_plate": [len(soft_obj.data.polygons), len(plate_obj.data.polygons)],
                    "vertices_soft_plate": [len(soft_obj.data.vertices), len(plate_obj.data.vertices)]}
    assert classified[1] == len(plate_obj.data.polygons), split_counts
    assert classified[0] == 0, split_counts
    assert len(soft_obj.data.polygons) + len(plate_obj.data.polygons) > 0
    assert all(not item.value for item in soft_obj.data.attributes["astra_body_plate"].data)
    assert all(item.value for item in plate_obj.data.attributes["astra_body_plate"].data)
    return soft_obj, plate_obj, len(plate_faces), cleanup


def mesh_components(mesh):
    adjacency = [[] for _vertex in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    unseen = set(range(len(mesh.vertices)))
    components = []
    while unseen:
        root = unseen.pop()
        component = {root}
        queue = deque([root])
        while queue:
            current = queue.popleft()
            found = set(adjacency[current]) & unseen
            unseen.difference_update(found)
            component.update(found)
            queue.extend(found)
        components.append(sorted(component))
    components.sort(key=len, reverse=True)
    return components


def cluster_plate_islands(plate):
    components = mesh_components(plate.data)
    large = [component for component in components if len(component) >= MIN_ISLAND_VERTICES]
    small = [component for component in components if len(component) < MIN_ISLAND_VERTICES]
    assert large, "no plate island reaches the 30-vertex merge floor"
    tree = KDTree(sum(len(component) for component in large))
    slot_to_island = []
    slot = 0
    for island_id, component in enumerate(large):
        for vertex_index in component:
            tree.insert(plate.matrix_world @ plate.data.vertices[vertex_index].co, slot)
            slot_to_island.append(island_id)
            slot += 1
    tree.balance()
    clusters = [list(component) for component in large]
    merged_components = [[] for _component in large]
    for component in small:
        best = None
        for vertex_index in component:
            point = plate.matrix_world @ plate.data.vertices[vertex_index].co
            _location, tree_slot, distance = tree.find(point)
            candidate = (distance, slot_to_island[tree_slot])
            if best is None or candidate < best:
                best = candidate
        island_id = best[1]
        clusters[island_id].extend(component)
        merged_components[island_id].append({
            "vertices": len(component), "nearest_distance_m": float(best[0])})

    source_weights = [vertex_weights(plate, index, set(BODY_BONES))
                      for index in range(len(plate.data.vertices))]
    assignments = [{} for _vertex in plate.data.vertices]
    attribute = plate.data.attributes.get("astra_body_i04_island")
    if attribute:
        plate.data.attributes.remove(attribute)
    attribute = plate.data.attributes.new("astra_body_i04_island", "INT", "POINT")
    rows = []
    for island_id, vertices in enumerate(clusters):
        totals = defaultdict(float)
        for vertex_index in vertices:
            for name, weight in source_weights[vertex_index].items():
                totals[name] += weight
        chosen = max(totals.items(), key=lambda item: item[1])[0]
        for vertex_index in vertices:
            assignments[vertex_index] = {chosen: 1.0}
            attribute.data[vertex_index].value = island_id
        world = [plate.matrix_world @ plate.data.vertices[index].co for index in vertices]
        rows.append({
            "island_id": island_id,
            "vertices": len(vertices),
            "original_large_component_vertices": len(large[island_id]),
            "small_components_merged": len(merged_components[island_id]),
            "small_vertices_merged": sum(row["vertices"] for row in merged_components[island_id]),
            "maximum_small_merge_distance_m": max(
                (row["nearest_distance_m"] for row in merged_components[island_id]), default=0.0),
            "bone": chosen,
            "summed_i03_heat_weight": float(totals[chosen]),
            "summed_i03_heat_weights_top8": sorted(
                totals.items(), key=lambda item: item[1], reverse=True)[:8],
            "bounds_world_m": {
                "min": [min(point[axis] for point in world) for axis in range(3)],
                "max": [max(point[axis] for point in world) for axis in range(3)],
            },
        })
    assert all(assignments)
    rebuild_groups(plate, assignments)
    return rows, {
        "topological_component_count_before_small_merge": len(components),
        "components_at_least_30_vertices": len(large),
        "components_under_30_vertices": len(small),
        "small_components_merged_by": "nearest vertex on a >=30-vertex island",
        "island_count_after_small_merge": len(rows),
        "islands": rows,
    }


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
                scale = 1.0 / max(len(adjacency[index]), 1)
                for name, weight in current[neighbor].items():
                    totals[name] += scale * weight
            updated.append(normalize(totals, limit=8))
        current = updated
    return current


def make_heat_proxy(rig):
    proxy = rig.copy()
    proxy.data = rig.data.copy()
    proxy.name = "Armature_i04_HeatProxy"
    proxy.data.name = "Armature_i04_HeatProxyData"
    bpy.context.scene.collection.objects.link(proxy)
    heat_bones = set(BODY_BONES) | {"Head"}
    disabled = []
    for bone in proxy.data.bones:
        enabled = (bone.name in heat_bones and not bone.name.startswith("phys_")
                   and bone.name not in {"head_end", "headfront"})
        bone.use_deform = enabled
        if not enabled:
            disabled.append(bone.name)
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True)
    bpy.context.view_layer.objects.active = proxy
    bpy.ops.object.mode_set(mode="EDIT")
    snapshot = {bone.name: (bone.head.copy(), bone.tail.copy()) for bone in proxy.data.edit_bones}
    inverse_world = proxy.matrix_world.inverted()
    normalized_segments = {}
    for bone in proxy.data.edit_bones:
        bone.use_connect = False
    for name in heat_bones:
        bone = proxy.data.edit_bones.get(name)
        if bone is None:
            continue
        child_name = CHILD.get(name)
        child = proxy.data.edit_bones.get(child_name) if child_name else None
        if child is not None and (child.head - bone.head).length > 1e-5:
            bone.tail = child.head
            normalized_segments[name] = child_name
        elif name in {"LeftHand", "RightHand", "LeftToeBase", "RightToeBase"}:
            old_head, old_tail = snapshot[name]
            world_head = proxy.matrix_world @ old_head
            direction = (proxy.matrix_world.to_3x3() @ (old_tail - old_head)).normalized()
            length = 0.22 if name.endswith("Hand") else 0.12
            bone.tail = inverse_world @ (world_head + direction * length)
            normalized_segments[name] = f"terminal {length:.2f} m"
    bpy.ops.object.mode_set(mode="OBJECT")
    return proxy, heat_bones, disabled, normalized_segments


def heat_bind_soft(body, rig):
    for modifier in list(body.modifiers):
        if modifier.type == "ARMATURE":
            body.modifiers.remove(modifier)
    body.parent = None
    body.matrix_parent_inverse.identity()
    body.vertex_groups.clear()
    proxy, heat_bones, disabled, normalized_segments = make_heat_proxy(rig)
    components = mesh_components(body.data)
    component_of_vertex = np.full(len(body.data.vertices), -1, dtype=np.int32)
    for component_id, component in enumerate(components):
        component_of_vertex[component] = component_id
    faces_by_component = defaultdict(list)
    for polygon in body.data.polygons:
        component_id = int(component_of_vertex[polygon.vertices[0]])
        assert all(component_of_vertex[index] == component_id for index in polygon.vertices)
        faces_by_component[component_id].append(tuple(polygon.vertices))
    heat = [{} for _vertex in body.data.vertices]
    component_rows = []
    for component_id, component in enumerate(components):
        if len(component) < 30:
            component_rows.append({"component": component_id, "vertices": len(component),
                                   "faces": len(faces_by_component[component_id]),
                                   "operator": "skipped; nearest heat-weighted fallback",
                                   "weighted_vertices": 0})
            continue
        global_to_local = {value: slot for slot, value in enumerate(component)}
        coords = [body.data.vertices[index].co[:] for index in component]
        faces = [tuple(global_to_local[index] for index in face)
                 for face in faces_by_component[component_id]]
        temp_mesh = bpy.data.meshes.new(f"I04HeatComponent{component_id:04d}")
        temp_mesh.from_pydata(coords, [], faces)
        temp_mesh.update()
        temp = bpy.data.objects.new(f"I04HeatComponent{component_id:04d}", temp_mesh)
        bpy.context.scene.collection.objects.link(temp)
        temp.matrix_world = body.matrix_world.copy()
        bpy.ops.object.select_all(action="DESELECT")
        temp.select_set(True)
        proxy.select_set(True)
        bpy.context.view_layer.objects.active = proxy
        operator_result = sorted(bpy.ops.object.parent_set(type="ARMATURE_AUTO", keep_transform=True))
        bpy.context.view_layer.update()
        extracted = [vertex_weights(temp, index, heat_bones)
                     for index in range(len(temp.data.vertices))]
        weighted_count = sum(bool(row) for row in extracted)
        for local_index, global_index in enumerate(component):
            if extracted[local_index]:
                heat[global_index] = extracted[local_index]
        component_rows.append({"component": component_id, "vertices": len(component),
                               "faces": len(faces), "operator_result": operator_result,
                               "weighted_vertices": weighted_count})
        print("BODY_I04_HEAT_COMPONENT", component_id, len(component), weighted_count, flush=True)
        bpy.data.objects.remove(temp, do_unlink=True)
        bpy.data.meshes.remove(temp_mesh)

    failed = [index for index, weights in enumerate(heat) if not weights]
    weighted = [index for index, weights in enumerate(heat) if weights]
    assert weighted, "component-wise heat binding produced no weighted soft vertices"
    tree = KDTree(len(weighted))
    for slot, index in enumerate(weighted):
        tree.insert(body.matrix_world @ body.data.vertices[index].co, slot)
    tree.balance()
    for index in failed:
        _point, slot, _distance = tree.find(body.matrix_world @ body.data.vertices[index].co)
        heat[index] = dict(heat[weighted[slot]])
    heat = smooth_heat_weights(body, heat)
    proxy_data = proxy.data
    bpy.data.objects.remove(proxy, do_unlink=True)
    bpy.data.armatures.remove(proxy_data)
    return heat, {
        "operator": "bpy.ops.object.parent_set(type='ARMATURE_AUTO', keep_transform=True)",
        "operator_result": "component-wise results below",
        "heat_target": "I04 soft body alone after metal face separation",
        "heat_bones": sorted(heat_bones),
        "temporarily_disabled_deform_bones": sorted(disabled),
        "temporary_heat_segment_normalization": normalized_segments,
        "unweighted_before_nearest_weighted_fallback": len(failed),
        "soft_topological_components": len(components),
        "component_operator_rows": component_rows,
        "graph_smoothing": {"iterations": 6, "self_weight": 2.0},
    }


def base_color_image(body):
    for material in body.data.materials:
        if not material or not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if (node.bl_idname == "ShaderNodeTexImage" and node.image
                    and (node.label.upper() == "BASE COLOR" or "base" in node.name.lower())):
                return node.image
    raise AssertionError("base-color image not found")


def blue_velvet_vertices(body):
    image = base_color_image(body)
    width, height = image.size
    pixels = np.asarray(image.pixels[:], dtype=np.float32).reshape(-1, 4)
    uv_layer = body.data.uv_layers.active.data
    votes = np.zeros(len(body.data.vertices), dtype=np.int32)
    samples = np.zeros(len(body.data.vertices), dtype=np.int32)
    rgb_sum = np.zeros((len(body.data.vertices), 3), dtype=np.float64)
    metallic = body.data.attributes.get("astra_body_metallic")
    for polygon in body.data.polygons:
        metal = float(metallic.data[polygon.index].value) if metallic else 0.0
        for loop_index in polygon.loop_indices:
            vertex_index = body.data.loops[loop_index].vertex_index
            uv = uv_layer[loop_index].uv
            x = int(round((uv.x % 1.0) * (width - 1)))
            y = int(round((uv.y % 1.0) * (height - 1)))
            rgb = pixels[y * width + x, :3]
            rgb_sum[vertex_index] += rgb
            samples[vertex_index] += 1
            blue = rgb[2] > 1.20 * rgb[0] and rgb[2] > 1.20 * rgb[1] and metal < 0.35
            votes[vertex_index] += int(blue)
    flags = votes * 2 >= np.maximum(samples, 1)
    mean_rgb = rgb_sum / np.maximum(samples[:, None], 1)
    return flags, mean_rgb, {
        "image": image.name, "size": [width, height],
        "threshold": "B > 1.20 R, B > 1.20 G, face metallic < 0.35",
        "decision": "at least half of a vertex's UV-loop texel samples satisfy the threshold",
        "vertices": int(flags.sum()),
    }


def measure_belt_line(plate, rig):
    hips = rig.matrix_world @ rig.data.bones["Hips"].head_local
    spine02 = rig.matrix_world @ rig.data.bones["Spine02"].head_local
    leg_z = np.mean([(rig.matrix_world @ rig.data.bones[name].head_local).z
                     for name in ("LeftUpLeg", "RightUpLeg")])
    candidates = []
    for vertex in plate.data.vertices:
        point = plate.matrix_world @ vertex.co
        if abs(point.x - hips.x) <= 0.45 and leg_z <= point.z <= spine02.z:
            candidates.append(point.z)
    assert candidates
    belt_z = float(np.median(np.asarray(candidates)))
    return belt_z, {
        "method": "median z of classified plate-island vertices in the central pelvis envelope",
        "central_envelope": {"abs_x_from_hips_max_m": 0.45,
                             "z_min_m": float(leg_z), "z_max_m": float(spine02.z)},
        "pelvis_plate_vertices": len(candidates),
        "z_min_m": float(min(candidates)), "z_median_m": belt_z,
        "z_max_m": float(max(candidates)),
    }


def apply_soft_overrides(body, heat, blue, belt_z):
    assignments = []
    counts = defaultdict(int)
    leg_influence_vertices = 0
    for index, source in enumerate(heat):
        point = body.matrix_world @ body.data.vertices[index].co
        base = normalize({name: value for name, value in source.items()
                          if name in BODY_BONES and not name.startswith("phys_")}, limit=4)
        if blue[index] and point.z < belt_z:
            if point.z <= belt_z - BELT_BLEND_M:
                weights = {"Hips": 1.0}
                counts["blue_skirt_cape_hips_only"] += 1
            else:
                alpha = (point.z - (belt_z - BELT_BLEND_M)) / BELT_BLEND_M
                mixed = defaultdict(float, {"Hips": 1.0 - alpha})
                belt_target = normalize({name: value for name, value in base.items()
                                         if name == "Hips" or name in SASH_BONES}, limit=4)
                for name, value in belt_target.items():
                    mixed[name] += alpha * value
                weights = normalize(mixed, limit=4)
                counts["blue_skirt_cape_belt_blend"] += 1
            # The brief permits, but does not require, retained leg influence on
            # front slit panels. I04 uses zero to prioritize the no-tearing gate.
        elif blue[index] and belt_z <= point.z <= 2.62 and abs(point.x) <= 0.60:
            restricted = {name: value for name, value in base.items() if name in SASH_BONES}
            if restricted:
                weights = normalize(restricted, limit=4)
            else:
                nearest = min(SASH_BONES, key=lambda name: (
                    point - (bpy.data.objects["Armature"].matrix_world
                             @ bpy.data.objects["Armature"].data.bones[name].head_local)).length)
                weights = {nearest: 1.0}
            counts["blue_torso_sash_restricted"] += 1
        else:
            weights = base
            counts["heat_top4_other_soft"] += 1
        if any(name.startswith(("LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg"))
               and value > 1e-8 for name, value in weights.items()) and blue[index] and point.z < belt_z:
            leg_influence_vertices += 1
        assignments.append(weights)
    rebuild_groups(body, assignments)
    return assignments, {
        "belt_line_z_m": belt_z,
        "belt_blend_band_m": BELT_BLEND_M,
        "counts": dict(counts),
        "front_slit_policy": "permitted leg influence set to 0%; Hips-only selected to prevent tearing",
        "blue_below_belt_vertices_with_leg_influence": leg_influence_vertices,
        "sash_allowed_bones": sorted(SASH_BONES),
        "undersleeves_and_gauntlet_adjacent_cloth": "heat weights, top four normalized",
        "phys_weights": "zeroed",
    }


def attach_to_rig(obj, rig, modifier_name):
    obj.parent = rig
    obj.matrix_parent_inverse = rig.matrix_world.inverted()
    armatures = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
    if armatures:
        for modifier in armatures:
            modifier.object = rig
    else:
        modifier = obj.modifiers.new(modifier_name, "ARMATURE")
        modifier.object = rig


def weight_audit(objects):
    aggregate = {"vertices": 0, "unweighted_vertices": 0, "bad_weight_sum_vertices": 0,
                 "maximum_weight_sum_error": 0.0, "vertices_with_phys_weights": 0,
                 "vertices_over_four_influences": 0}
    per_object = {}
    for obj in objects:
        names = {group.index: group.name for group in obj.vertex_groups}
        row = {key: 0 for key in aggregate}
        row["vertices"] = len(obj.data.vertices)
        maximum_error = 0.0
        for vertex in obj.data.vertices:
            entries = [(names[item.group], float(item.weight)) for item in vertex.groups
                       if item.weight > 1e-8]
            total = sum(weight for _name, weight in entries)
            row["unweighted_vertices"] += int(not entries)
            row["bad_weight_sum_vertices"] += int(abs(total - 1.0) > 2e-6)
            maximum_error = max(maximum_error, abs(total - 1.0))
            row["vertices_with_phys_weights"] += int(
                any(name.startswith("phys_") for name, _weight in entries))
            row["vertices_over_four_influences"] += int(len(entries) > 4)
        row["maximum_weight_sum_error"] = maximum_error
        per_object[obj.name] = row
        for key in aggregate:
            if key == "maximum_weight_sum_error":
                aggregate[key] = max(aggregate[key], row[key])
            else:
                aggregate[key] += row[key]
    aggregate["per_object"] = per_object
    return aggregate


def world_mesh(obj):
    return ([obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
            [tuple(poly.vertices) for poly in obj.data.polygons])


def ray_inside(tree, point, direction):
    origin = point.copy()
    remaining = 20.0
    hits = 0
    for _index in range(64):
        location = tree.ray_cast(origin, direction, remaining)[0]
        if location is None:
            break
        travelled = (location - origin).length
        hits += 1
        step = travelled + 1e-5
        origin += direction * step
        remaining -= step
        if remaining <= 0:
            break
    return hits % 2 == 1


def coverage_report(soft, plate, rig):
    def records(objects):
        result = []
        for obj in objects:
            coords, polygons = world_mesh(obj)
            result.append((obj.name, BVHTree.FromPolygons(coords, polygons, all_triangles=False)))
        return result
    body_records = records([soft, plate])
    head_records = records([bpy.data.objects["AstraChar2_Meshy_HeadHair"],
                            bpy.data.objects["AstraChar2_Meshy_NeckBlend"]])
    directions = [Vector((1.0, 0.173, 0.071)).normalized(),
                  Vector((0.113, 1.0, 0.193)).normalized(),
                  Vector((0.157, 0.091, 1.0)).normalized()]
    rows = {}
    for name in BODY_BONES_24:
        start = rig.matrix_world @ rig.data.bones[name].head_local
        child = CHILD.get(name)
        end = rig.matrix_world @ rig.data.bones[child].head_local if child else start
        midpoint = (start + end) * 0.5
        selected = body_records + head_records if name == "neck" else (
            head_records if name in {"Head", "head_end", "headfront"} else body_records)
        hits = [(obj_name, tree, tree.find_nearest(midpoint)) for obj_name, tree in selected]
        obj_name, _tree, nearest = min(hits, key=lambda item: item[2][3])
        inside_votes = sum(any(ray_inside(tree, midpoint, direction)
                               for _obj_name, tree in selected) for direction in directions)
        signed = float((midpoint - nearest[0]).dot(nearest[1]))
        enclosed = inside_votes >= 2 or signed < 0.0
        distance = float(nearest[3])
        coverage = 0.0 if enclosed else distance
        rows[name] = {"midpoint_world_m": list(midpoint),
                      "nearest_object": obj_name,
                      "nearest_triangle_surface_distance_m": distance,
                      "nearest_triangle_signed_plane_distance_m": signed,
                      "midpoint_enclosed": enclosed, "inside_ray_votes_of_3": inside_votes,
                      "coverage_distance_m": coverage, "gate_m": GATE_DISTANCE,
                      "gate_pass": coverage <= GATE_DISTANCE}
    return {"bones_checked": len(rows), "per_bone": rows,
            "maximum_coverage_distance_m": max(row["coverage_distance_m"] for row in rows.values()),
            "all_24_bones_within_60mm": all(row["gate_pass"] for row in rows.values())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(SOURCE)
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    rig = bpy.data.objects["Armature"]
    body = bpy.data.objects["char1"]
    assert len(rig.data.bones) == 121 and len(body.data.vertices) == 149413
    preserved_names = ["AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Godwyn_Sword"]
    preserved_before = {name: geometry_digest(bpy.data.objects[name]) for name in preserved_names}
    rest_before = {bone.name: np.asarray(bone.matrix_local).copy() for bone in rig.data.bones}
    rig.animation_data_clear()
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    for pose in rig.pose.bones:
        pose.matrix_basis.identity()
    bpy.context.view_layer.update()

    source_totals = {"vertices": len(body.data.vertices), "faces": len(body.data.polygons)}
    soft, plate, classified_plate_faces, loose_cleanup = split_plate_from_soft(body)
    island_rows, split = cluster_plate_islands(plate)
    belt_z, belt_measurement = measure_belt_line(plate, rig)
    heat, heat_report = heat_bind_soft(soft, rig)
    blue, _mean_rgb, blue_report = blue_velvet_vertices(soft)
    _assignments, override_report = apply_soft_overrides(soft, heat, blue, belt_z)
    attach_to_rig(soft, rig, "I04 soft heat skin")
    attach_to_rig(plate, rig, "I04 rigid plate islands")

    audit = weight_audit([soft, plate])
    coverage = coverage_report(soft, plate, rig)
    rest_error = max(float(np.max(np.abs(np.asarray(bone.matrix_local) - rest_before[bone.name])))
                     for bone in rig.data.bones)
    preserved_after = {name: geometry_digest(bpy.data.objects[name]) for name in preserved_names}
    split_payload = {
        "source": str(SOURCE.relative_to(ROOT)), "source_sha256": source_hash,
        "method": "selected classified plate faces separated from char1; boundary vertices duplicated by Blender mesh separation",
        "uv_material_normals_preserved": True,
        "source_vertices": source_totals["vertices"], "source_faces": source_totals["faces"],
        "classified_plate_faces": classified_plate_faces,
        "soft_object": soft.name, "soft_vertices": len(soft.data.vertices),
        "soft_faces": len(soft.data.polygons),
        "plate_object": plate.name, "plate_vertices": len(plate.data.vertices),
        "plate_faces": len(plate.data.polygons),
        "nonface_geometry_cleanup": loose_cleanup,
        **split,
        "vertices_per_island": {str(row["island_id"]): row["vertices"] for row in island_rows},
        "bone_per_island": {str(row["island_id"]): row["bone"] for row in island_rows},
        "belt_measurement": belt_measurement,
    }
    SPLIT_JSON.write_text(json.dumps(split_payload, indent=2) + "\n")
    report = {
        "source": str(SOURCE.relative_to(ROOT)), "source_sha256": source_hash,
        "candidate": str(CANDIDATE.relative_to(ROOT)),
        "split_json": str(SPLIT_JSON.relative_to(ROOT)),
        "split": split_payload, "heat_binding": heat_report,
        "blue_velvet": blue_report, "soft_overrides": override_report,
        "weights": audit, "coverage_24_bones": coverage,
        "bones": len(rig.data.bones), "actions": len(bpy.data.actions),
        "rest_matrix_error": rest_error,
        "preserved_geometry_sha256_before": preserved_before,
        "preserved_geometry_sha256_after": preserved_after,
        "preserved_geometry_unchanged": preserved_before == preserved_after,
        "known_gaps": ["zero phys_* weights / no cloth secondary motion",
                       "skirt-leg clipping is allowed in I04",
                       "source sword hand remains open"],
    }
    assert audit["unweighted_vertices"] == 0 and audit["bad_weight_sum_vertices"] == 0
    assert audit["vertices_with_phys_weights"] == 0 and audit["vertices_over_four_influences"] == 0
    assert report["bones"] == 121 and report["actions"] == 0 and rest_error == 0.0
    assert report["preserved_geometry_unchanged"]
    assert list(bpy.data.objects["Godwyn_Sword"].vertex_groups.keys()) == ["RightHand"]
    scene["astra_body_i04"] = json.dumps({"plate_islands": len(island_rows),
                                            "belt_z_m": belt_z, "phys_weights": 0})
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(CANDIDATE))
    report["candidate_sha256"] = sha256(CANDIDATE)
    report["candidate_bytes"] = CANDIDATE.stat().st_size
    report["source_unchanged"] = sha256(SOURCE) == source_hash
    assert report["source_unchanged"]
    BUILD_JSON.write_text(json.dumps(report, indent=2) + "\n")
    print("BODY_I04_BUILD_PASS", json.dumps({
        "soft_vertices": len(soft.data.vertices), "plate_vertices": len(plate.data.vertices),
        "plate_islands": len(island_rows), "belt_z_m": belt_z,
        "unweighted": audit["unweighted_vertices"], "bad_sums": audit["bad_weight_sum_vertices"],
        "bones": report["bones"], "actions": report["actions"],
        "rest_matrix_error": rest_error, "coverage": coverage["all_24_bones_within_60mm"],
        "candidate_sha256": report["candidate_sha256"],
    }), flush=True)


if __name__ == "__main__":
    main()
