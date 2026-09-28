"""Rehost five moves and enforce the I04 pre-render stretch and seam-gap gate."""
import bpy
import hashlib
import json
import numpy as np
from collections import defaultdict
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "models/astra_character_v2_body_i04.blend"
I02_STILLS = ROOT / "renders/astra/rehost_body_i02/meshy_body_move_stills.json"
OUT = ROOT / "renders/astra/rehost_body_i04"
REPORT = OUT / "meshy_body_i04_stretch.json"
JOBS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_v2_wip.blend",
                   ROOT / "models/astra_move_idle_guard_body_i04.blend"),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_v2_wip.blend",
                   ROOT / "models/astra_move_walk_stalk_body_i04.blend"),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_v2_wip.blend",
                     ROOT / "models/astra_move_lunge_thrust_body_i04.blend"),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_v2_wip.blend",
                    ROOT / "models/astra_move_rising_spin_body_i04.blend"),
    "xslash": (ROOT / "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
               ROOT / "models/astra_xslash_body_i04.blend"),
}


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def action_digest(action):
    digest = hashlib.sha256()
    curves = [curve for layer in action.layers for strip in layer.strips
              for bag in strip.channelbags for curve in bag.fcurves]
    for curve in sorted(curves, key=lambda item: (item.data_path, item.array_index)):
        digest.update(f"{curve.data_path}|{curve.array_index}|".encode())
        for key in curve.keyframe_points:
            digest.update(("%.9g,%.9g,%s;" %
                           (key.co.x, key.co.y, key.interpolation)).encode())
    return digest.hexdigest(), len(curves), sum(len(curve.keyframe_points) for curve in curves)


def rehost(name, source, target):
    base_hash = sha256(BASE)
    source_hash = sha256(source)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    character_scene = bpy.context.scene
    character_objects = [obj for obj in character_scene.objects
                         if obj.type not in {"LIGHT", "CAMERA"}
                         and obj.name != "Astra evaluation ground"]
    rig = bpy.data.objects["Armature"]
    with bpy.data.libraries.load(str(source), link=False) as (available, requested):
        assert len(available.scenes) == 1
        requested.scenes = available.scenes[:]
    move_scene = requested.scenes[0]
    bpy.context.window.scene = move_scene
    appended = set(move_scene.objects)
    old_rig = next(obj for obj in appended if obj.type == "ARMATURE")
    source_action = old_rig.animation_data.action
    source_digest, curves, keys = action_digest(source_action)
    for obj in character_objects:
        move_scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    assert len(old_rig.data.bones) == len(rig.data.bones) == 121
    rest_error = max(abs(old_rig.data.bones[bone.name].matrix_local[i][j]
                         - rig.data.bones[bone.name].matrix_local[i][j])
                     for bone in rig.data.bones for i in range(4) for j in range(4))
    assert rest_error == 0.0
    for pose in old_rig.pose.bones:
        other = rig.pose.bones[pose.name]
        other.rotation_mode = pose.rotation_mode
        other.scale = pose.scale
    rig.animation_data_clear()
    rig.animation_data_create()
    transferred = source_action.copy()
    transferred.name = source_action.name + "_BodyI04"
    rig.animation_data.action = transferred
    if transferred.slots:
        rig.animation_data.action_slot = transferred.slots[0]
    assert action_digest(transferred) == (source_digest, curves, keys)
    old_character = {old_rig}
    for obj in appended:
        if obj == old_rig:
            continue
        armature_target = any(modifier.type == "ARMATURE" and modifier.object == old_rig
                              for modifier in obj.modifiers)
        if obj.parent == old_rig or armature_target:
            old_character.add(obj)
    for obj in old_character:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(character_scene)
    move_scene.name = "Astra Body i04 " + name
    move_scene.render.fps = 30
    move_scene["astra_body_i04_rehost"] = name
    move_scene["astra_body_i04_base_sha256"] = base_hash
    move_scene["astra_body_i04_action_source_sha256"] = source_hash
    move_scene["astra_body_i04_action_digest"] = source_digest
    move_scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    assert sha256(BASE) == base_hash and sha256(source) == source_hash
    return move_scene, rig, {
        "source": str(source.relative_to(ROOT)), "source_sha256": source_hash,
        "output": str(target.relative_to(ROOT)), "output_sha256": sha256(target),
        "base_sha256": base_hash, "bones": len(rig.data.bones),
        "rest_matrix_error": rest_error, "action_digest": source_digest,
        "action_fcurves": curves, "action_keys": keys, "action_data_identical": True,
    }


def evaluated_world(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    polygons = [tuple(poly.vertices) for poly in mesh.polygons]
    evaluated.to_mesh_clear()
    return coords, polygons


def rest_world(obj):
    coords = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(obj.matrix_world)
    return coords @ matrix[:3, :3].T + matrix[:3, 3]


def edges_array(obj):
    edges = np.empty(len(obj.data.edges) * 2, dtype=np.int32)
    obj.data.edges.foreach_get("vertices", edges)
    return edges.reshape(-1, 2)


def weight_row(obj, index):
    names = {group.index: group.name for group in obj.vertex_groups}
    return sorted(((names[item.group], float(item.weight))
                   for item in obj.data.vertices[index].groups if item.weight > 1e-8),
                  key=lambda item: item[1], reverse=True)


def stretch_object(obj, posed, include_worst=False):
    rest = rest_world(obj)
    edges = edges_array(obj)
    rest_lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    posed_lengths = np.linalg.norm(posed[edges[:, 0]] - posed[edges[:, 1]], axis=1)
    valid = rest_lengths > 1e-6
    slots = np.flatnonzero(valid)
    ratios = posed_lengths[valid] / rest_lengths[valid]
    row = {"edges": len(edges), "valid_edges_rest_length_gt_1um": int(valid.sum()),
           "maximum_ratio": float(ratios.max()),
           "p99_ratio": float(np.percentile(ratios, 99))}
    if include_worst:
        worst = []
        for ratio_slot in np.argsort(ratios)[-10:][::-1]:
            edge_index = int(slots[ratio_slot])
            a, b = (int(value) for value in edges[edge_index])
            worst.append({
                "edge_index": edge_index, "vertices": [a, b],
                "ratio": float(ratios[ratio_slot]),
                "rest_length_m": float(rest_lengths[edge_index]),
                "posed_length_m": float(posed_lengths[edge_index]),
                "rest_midpoint_world_m": ((rest[a] + rest[b]) * 0.5).tolist(),
                "posed_midpoint_world_m": ((posed[a] + posed[b]) * 0.5).tolist(),
                "endpoint_weights": {str(a): weight_row(obj, a), str(b): weight_row(obj, b)},
            })
        row["worst_10_edges"] = worst
    return row


def plate_boundary_by_island(plate):
    edge_faces = defaultdict(int)
    for polygon in plate.data.polygons:
        vertices = list(polygon.vertices)
        for slot, a in enumerate(vertices):
            edge_faces[tuple(sorted((a, vertices[(slot + 1) % len(vertices)])))] += 1
    attribute = plate.data.attributes["astra_body_i04_island"]
    result = defaultdict(set)
    for (a, b), count in edge_faces.items():
        if count != 1:
            continue
        island_a = int(attribute.data[a].value)
        island_b = int(attribute.data[b].value)
        assert island_a == island_b
        result[island_a].update((a, b))
    return {island: sorted(vertices) for island, vertices in result.items()}


def gap_audit(soft_coords, soft_polygons, plate, plate_coords):
    tree = BVHTree.FromPolygons([tuple(point) for point in soft_coords], soft_polygons,
                                all_triangles=False)
    per_island = {}
    for island_id, vertices in plate_boundary_by_island(plate).items():
        distances = []
        for index in vertices:
            hit = tree.find_nearest(Vector(plate_coords[index]))
            distances.append(float(hit[3]))
        maximum = max(distances, default=0.0)
        per_island[str(island_id)] = {
            "boundary_vertices": len(vertices), "maximum_gap_m": maximum,
            "p99_gap_m": float(np.percentile(distances, 99)) if distances else 0.0,
            "over_15mm": maximum > 0.015,
        }
    maximum = max((row["maximum_gap_m"] for row in per_island.values()), default=0.0)
    return {"definition": "nearest soft-body surface from posed plate boundary vertices",
            "maximum_gap_m": maximum, "gate_m": 0.015,
            "gate_pass": maximum <= 0.015,
            "islands_over_15mm": [int(key) for key, row in per_island.items()
                                   if row["over_15mm"]],
            "per_island": per_island}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {name: int(row["frame"]) for name, row in json.loads(I02_STILLS.read_text()).items()}
    assert set(frames) == set(JOBS)
    results = {}
    for name, (source, target) in JOBS.items():
        scene, _rig, transfer = rehost(name, source, target)
        scene.frame_set(frames[name])
        bpy.context.view_layer.update()
        soft = bpy.data.objects["char1"]
        plate = bpy.data.objects["AstraBody_I04_Plates"]
        soft_coords, soft_polygons = evaluated_world(soft)
        plate_coords, _plate_polygons = evaluated_world(plate)
        soft_stretch = stretch_object(soft, soft_coords, include_worst=True)
        plate_stretch = stretch_object(plate, plate_coords)
        gaps = gap_audit(soft_coords, soft_polygons, plate, plate_coords)
        gates = {"soft_p99_le_1_6": soft_stretch["p99_ratio"] <= 1.6,
                 "soft_maximum_le_3_0": soft_stretch["maximum_ratio"] <= 3.0,
                 "plate_maximum_le_1_01": plate_stretch["maximum_ratio"] <= 1.01}
        row = {"frame": frames[name], "transfer": transfer,
               "soft_body": soft_stretch, "plate_islands": plate_stretch,
               "plate_to_soft_gaps": gaps, "gates": gates,
               "stretch_gate_pass": all(gates.values())}
        results[name] = row
        print("BODY_I04_STRETCH", name, json.dumps({
            "frame": frames[name], "soft_p99": soft_stretch["p99_ratio"],
            "soft_max": soft_stretch["maximum_ratio"],
            "plate_max": plate_stretch["maximum_ratio"],
            "gap_max_m": gaps["maximum_gap_m"],
            "gap_islands_over_15mm": gaps["islands_over_15mm"],
            "stretch_pass": row["stretch_gate_pass"],
        }), flush=True)
    all_pass = all(row["stretch_gate_pass"] for row in results.values())
    report = {"candidate": str(BASE.relative_to(ROOT)), "candidate_sha256": sha256(BASE),
              "frame_source": str(I02_STILLS.relative_to(ROOT)), "moves": results,
              "thresholds": {"soft_p99_max": 1.6, "soft_maximum_max": 3.0,
                             "plate_maximum_max": 1.01, "seam_gap_publication_max_m": 0.015},
              "all_moves_stretch_pass": all_pass,
              "all_moves_gap_pass": all(row["plate_to_soft_gaps"]["gate_pass"]
                                         for row in results.values()),
              "render_authorized": all_pass}
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print("BODY_I04_STRETCH_COMPLETE", json.dumps({
        "all_moves_stretch_pass": report["all_moves_stretch_pass"],
        "all_moves_gap_pass": report["all_moves_gap_pass"],
        "render_authorized": report["render_authorized"],
    }), flush=True)
    assert all_pass, "stretch gate failed; rendering is forbidden"


if __name__ == "__main__":
    main()
