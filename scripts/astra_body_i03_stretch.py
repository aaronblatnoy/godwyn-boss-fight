"""Rehost five moves onto body i03 and enforce the pre-render stretch gate."""
import bpy
import hashlib
import json
import numpy as np
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "models/astra_character_v2_body_i03.blend"
I02_STILLS = ROOT / "renders/astra/rehost_body_i02/meshy_body_move_stills.json"
OUT = ROOT / "renders/astra/rehost_body_i03"
REPORT = OUT / "meshy_body_i03_stretch.json"
JOBS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_v2_wip.blend",
                   ROOT / "models/astra_move_idle_guard_body_i03.blend"),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_v2_wip.blend",
                   ROOT / "models/astra_move_walk_stalk_body_i03.blend"),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_v2_wip.blend",
                     ROOT / "models/astra_move_lunge_thrust_body_i03.blend"),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_v2_wip.blend",
                    ROOT / "models/astra_move_rising_spin_body_i03.blend"),
    "xslash": (ROOT / "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
               ROOT / "models/astra_xslash_body_i03.blend"),
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
            digest.update(("%.9g,%.9g,%s;" % (key.co.x, key.co.y, key.interpolation)).encode())
    return digest.hexdigest(), len(curves), sum(len(curve.keyframe_points) for curve in curves)


def rehost(name, source, target):
    base_hash = sha256(BASE)
    source_hash = sha256(source)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    character_scene = bpy.context.scene
    character_objects = [obj for obj in character_scene.objects if obj.type not in {"LIGHT", "CAMERA"}
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
    transferred.name = source_action.name + "_BodyI03"
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
    move_scene.name = "Astra Body i03 " + name
    move_scene.render.fps = 30
    move_scene["astra_body_i03_rehost"] = name
    move_scene["astra_body_i03_base_sha256"] = base_hash
    move_scene["astra_body_i03_action_source_sha256"] = source_hash
    move_scene["astra_body_i03_action_digest"] = source_digest
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
    evaluated.to_mesh_clear()
    return coords


def weight_row(body, index):
    names = {group.index: group.name for group in body.vertex_groups}
    return sorted(((names[item.group], float(item.weight)) for item in body.data.vertices[index].groups
                   if item.weight > 1e-8), key=lambda item: item[1], reverse=True)


def plate_edges(body):
    face_attribute = body.data.attributes["astra_body_plate"]
    component_attribute = body.data.attributes["astra_body_plate_component"]
    component = [item.value for item in component_attribute.data]
    result = set()
    for polygon in body.data.polygons:
        if not face_attribute.data[polygon.index].value:
            continue
        vertices = list(polygon.vertices)
        for index, a in enumerate(vertices):
            b = vertices[(index + 1) % len(vertices)]
            if component[a] >= 0 and component[a] == component[b]:
                result.add(tuple(sorted((a, b))))
    return result


def stretch(scene, body, frame):
    rest = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get("co", rest)
    rest = rest.reshape(-1, 3)
    matrix = np.asarray(body.matrix_world)
    rest = rest @ matrix[:3, :3].T + matrix[:3, 3]
    edge_vertices = np.empty(len(body.data.edges) * 2, dtype=np.int32)
    body.data.edges.foreach_get("vertices", edge_vertices)
    edge_vertices = edge_vertices.reshape(-1, 2)
    rest_lengths = np.linalg.norm(rest[edge_vertices[:, 0]] - rest[edge_vertices[:, 1]], axis=1)
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    posed = evaluated_world(body)
    posed_lengths = np.linalg.norm(posed[edge_vertices[:, 0]] - posed[edge_vertices[:, 1]], axis=1)
    valid = rest_lengths > 1e-6
    valid_slots = np.flatnonzero(valid)
    ratios = posed_lengths[valid] / rest_lengths[valid]
    order = np.argsort(ratios)[-5:][::-1]
    plate = plate_edges(body)
    plate_mask = np.asarray([tuple(sorted(pair)) in plate for pair in edge_vertices], dtype=bool) & valid
    worst = []
    for ratio_slot in order:
        edge_index = int(valid_slots[ratio_slot])
        a, b = (int(value) for value in edge_vertices[edge_index])
        worst.append({
            "edge_index": edge_index, "vertices": [a, b],
            "ratio": float(ratios[ratio_slot]),
            "rest_length_m": float(rest_lengths[edge_index]),
            "posed_length_m": float(posed_lengths[edge_index]),
            "rest_midpoint_world_m": ((rest[a] + rest[b]) * 0.5).tolist(),
            "posed_midpoint_world_m": ((posed[a] + posed[b]) * 0.5).tolist(),
            "plate_edge": bool(plate_mask[edge_index]),
            "endpoint_weights": {str(a): weight_row(body, a), str(b): weight_row(body, b)},
            "region": "/".join(sorted({weight_row(body, a)[0][0], weight_row(body, b)[0][0]})),
        })
    maximum = float(ratios.max())
    p99 = float(np.percentile(ratios, 99))
    plate_max = float((posed_lengths[plate_mask] / rest_lengths[plate_mask]).max()) if plate_mask.any() else 0.0
    return {
        "frame": frame, "edges": len(edge_vertices),
        "valid_edges_rest_length_gt_1um": int(valid.sum()),
        "plate_edges": int(plate_mask.sum()),
        "maximum_ratio": maximum, "p99_ratio": p99,
        "maximum_plate_edge_ratio": plate_max,
        "gates": {"p99_le_1_6": p99 <= 1.6, "maximum_le_3_0": maximum <= 3.0,
                  "plate_maximum_le_1_01": plate_max <= 1.01},
        "worst_5_edges": worst,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {name: int(row["frame"]) for name, row in json.loads(I02_STILLS.read_text()).items()}
    assert set(frames) == set(JOBS)
    results = {}
    for name, (source, target) in JOBS.items():
        scene, _rig, transfer = rehost(name, source, target)
        row = stretch(scene, bpy.data.objects["char1"], frames[name])
        row["transfer"] = transfer
        row["gate_pass"] = all(row["gates"].values())
        results[name] = row
        print("BODY_I03_STRETCH", name, json.dumps({
            "frame": frames[name], "p99": row["p99_ratio"], "max": row["maximum_ratio"],
            "plate_max": row["maximum_plate_edge_ratio"], "pass": row["gate_pass"],
            "worst": row["worst_5_edges"],
        }), flush=True)
    report = {
        "candidate": str(BASE.relative_to(ROOT)), "candidate_sha256": sha256(BASE),
        "frame_source": str(I02_STILLS.relative_to(ROOT)), "moves": results,
        "thresholds": {"p99_max": 1.6, "maximum_max": 3.0, "plate_maximum_max": 1.01},
        "all_moves_pass": all(row["gate_pass"] for row in results.values()),
        "render_authorized": all(row["gate_pass"] for row in results.values()),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print("BODY_I03_STRETCH_COMPLETE", json.dumps({
        "all_moves_pass": report["all_moves_pass"], "render_authorized": report["render_authorized"]
    }), flush=True)
    assert report["all_moves_pass"], "stretch gate failed; inspect worst_5_edges before rendering"


if __name__ == "__main__":
    main()
