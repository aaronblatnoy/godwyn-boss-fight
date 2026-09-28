"""Inventory Meshy mocap GLBs and diagnose the published V3 head fit.

Run in Blender on black-sky only.
"""

import hashlib
import json
import math
import struct
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
MOCAP = ROOT / "models/mocap"
BLEND = ROOT / "models/astra_character_v3.blend"
OUT = ROOT / "renders/astra/char2/astra_v3m_probe.json"
EXPECTED = [
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def glb_json(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2 and length == len(data)
    offset = 12
    while offset < len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset:offset + size]
        offset += size
        if kind == 0x4E4F534A:
            return json.loads(payload.decode("utf-8").rstrip(" \t\r\n\x00"))
    raise RuntimeError(f"No JSON chunk in {path}")


def action_curves(action):
    if action.is_action_layered:
        return [curve for layer in action.layers for strip in layer.strips
                for bag in strip.channelbags for curve in bag.fcurves]
    return list(action.fcurves)


def rest_rows(rig):
    return {
        bone: {
            "head": list(rig.matrix_world @ rig.data.bones[bone].head_local),
            "matrix": [list(row) for row in (rig.matrix_world @ rig.data.bones[bone].matrix_local)],
        }
        for bone in EXPECTED
    }


def bounds_world(ob, vertex_ids=None):
    ids = range(len(ob.data.vertices)) if vertex_ids is None else vertex_ids
    points = np.asarray([(ob.matrix_world @ ob.data.vertices[index].co)[:] for index in ids], dtype=float)
    return points.min(axis=0), points.max(axis=0), points


def head_diagnostic():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    body = bpy.data.objects["char1"]
    meta = json.loads(scene.get("astra_v3", "{}"))
    skin = head.data.color_attributes.get("meshy_skin_mask")
    hair = head.data.color_attributes.get("meshy_hair_mask")
    skin_ids = set()
    hair_ids = set()
    if skin:
        for poly in head.data.polygons:
            value = np.mean([skin.data[index].color[0] for index in poly.loop_indices])
            target = skin_ids if value >= 0.5 else hair_ids
            target.update(poly.vertices)
    head_low, head_high, head_points = bounds_world(head)
    skin_low, skin_high, skin_points = bounds_world(head, sorted(skin_ids))
    collar = meta.get("segmentation", {}).get("collar_measurement", {})
    collar_rim = float(collar.get("lowest_selected_vertex_z_m", 2.464160442))
    collar_floor = float(collar.get("interior_floor_z_m", 2.6))
    # The donor skin's low central vertices are the neck column.  The jaw underside
    # is the 2nd percentile after excluding the lowest 12% of the skin height.
    skin_span = skin_high[2] - skin_low[2]
    jaw_candidates = skin_points[skin_points[:, 2] >= skin_low[2] + 0.12 * skin_span]
    jaw_z = float(np.percentile(jaw_candidates[:, 2], 2.0))
    shoulders = []
    for name in ("LeftShoulder", "RightShoulder"):
        shoulders.append(rig.matrix_world @ rig.data.bones[name].head_local)
    shoulder_width = float((shoulders[0] - shoulders[1]).length)
    body_low, body_high, _ = bounds_world(body)
    body_height = float(max(body_high[2], head_high[2]) - min(body_low[2], head_low[2]))
    head_height = float(head_high[2] - jaw_z)
    return {
        "blend_sha256": sha256(BLEND),
        "rig_rest": rest_rows(rig),
        "objects": {
            "head_parent": head.parent.name if head.parent else None,
            "head_parent_type": head.parent_type,
            "head_parent_bone": head.parent_bone,
            "neckblend_present": bpy.data.objects.get("AstraChar2_Meshy_NeckBlend") is not None,
        },
        "measurements": {
            "head_bounds_world_m": {"min": head_low.tolist(), "max": head_high.tolist()},
            "skin_bounds_world_m": {"min": skin_low.tolist(), "max": skin_high.tolist()},
            "jaw_underside_estimate_z_m": jaw_z,
            "collar_rim_lowest_z_m": collar_rim,
            "collar_interior_floor_z_m": collar_floor,
            "jaw_to_collar_rim_gap_m": jaw_z - collar_rim,
            "exposed_neck_column_m": max(0.0, jaw_z - collar_floor),
            "body_height_m": body_height,
            "head_height_above_jaw_m": head_height,
            "head_to_body_height_ratio": head_height / body_height,
            "concept_target_ratio": 1.0 / 7.5,
            "shoulder_joint_width_m": shoulder_width,
            "head_width_m": float(head_high[0] - head_low[0]),
            "head_width_to_shoulders": float((head_high[0] - head_low[0]) / shoulder_width),
        },
    }


def inspect_clip(path, target_rest):
    document = glb_json(path)
    glb_anims = []
    for animation in document.get("animations", []):
        times = []
        for sampler in animation.get("samplers", []):
            accessor = document["accessors"][sampler["input"]]
            times.extend(accessor.get("min", []))
            times.extend(accessor.get("max", []))
        start = min(times) if times else 0.0
        end = max(times) if times else 0.0
        glb_anims.append({
            "name": animation.get("name", ""),
            "channels": len(animation.get("channels", [])),
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": end - start,
            "frames_at_30fps_inclusive": int(round((end - start) * 30.0)) + 1,
        })
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(path))
    rigs = [ob for ob in bpy.context.scene.objects if ob.type == "ARMATURE"]
    assert len(rigs) == 1, (path, [ob.name for ob in rigs])
    rig = rigs[0]
    bones = [bone.name for bone in rig.data.bones]
    actions = list(bpy.data.actions)
    assert len(actions) == 1, (path, [action.name for action in actions])
    action = actions[0]
    animation = rig.animation_data_create()
    animation.action = action
    if action.slots:
        animation.action_slot = action.slots[0]
    scene = bpy.context.scene
    start, end = action.frame_range
    scene.frame_set(int(round(start)))
    bpy.context.view_layer.update()
    hips_start = (rig.matrix_world @ rig.pose.bones["Hips"].head).copy()
    scene.frame_set(int(round(end)))
    bpy.context.view_layer.update()
    hips_end = (rig.matrix_world @ rig.pose.bones["Hips"].head).copy()
    rest_position_diffs = []
    rest_matrix_diffs = []
    for bone in EXPECTED:
        source_matrix = rig.matrix_world @ rig.data.bones[bone].matrix_local
        target_matrix = target_rest[bone]["matrix"]
        target_matrix = np.asarray(target_matrix, dtype=float)
        source_np = np.asarray(source_matrix, dtype=float)
        rest_position_diffs.append(float(np.linalg.norm(source_np[:3, 3] - target_matrix[:3, 3])))
        rest_matrix_diffs.append(float(np.max(np.abs(source_np - target_matrix))))
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "glb_animations": glb_anims,
        "import_action": action.name,
        "import_frame_range": [float(start), float(end)],
        "import_frames_inclusive": int(round(end - start)) + 1,
        "fcurves": len(action_curves(action)),
        "bone_count": len(bones),
        "bone_names": bones,
        "bone_names_exact": bones == EXPECTED,
        "bone_name_set_exact": sorted(bones) == sorted(EXPECTED),
        "rest_max_head_position_difference_m": max(rest_position_diffs),
        "rest_max_matrix_element_difference": max(rest_matrix_diffs),
        "rest_pose_exact": max(rest_matrix_diffs) < 1e-7,
        "hips_root_displacement_m": list(hips_end - hips_start),
        "hips_root_displacement_length_m": float((hips_end - hips_start).length),
        "in_place": (hips_end - hips_start).length < 0.01,
    }


def main():
    manifest = json.loads((MOCAP / "manifest.json").read_text())
    head = head_diagnostic()
    target_rest = head.pop("rig_rest")
    clips = []
    for item in manifest["clips"]:
        row = inspect_clip(MOCAP / item["file"], target_rest)
        row["action_id"] = item["action_id"]
        row["intended_role"] = item["role"]
        clips.append(row)
        print("V3M_CLIP", row["file"], row["sha256"], row["import_frames_inclusive"], row["bone_names_exact"], row["in_place"], flush=True)
    hashes = [row["sha256"] for row in clips]
    report = {
        "schema": "astra-v3m-probe",
        "source_blend": str(BLEND.relative_to(ROOT)),
        "fps": 30,
        "head_attachment_before": head,
        "clips": clips,
        "all_clip_files_sha256_distinct": len(set(hashes)) == len(hashes),
        "all_bone_names_exact": all(row["bone_names_exact"] for row in clips),
        "all_single_animation": all(len(row["glb_animations"]) == 1 for row in clips),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_PROBE_PASS", json.dumps({
        "clips": len(clips),
        "distinct": report["all_clip_files_sha256_distinct"],
        "bones": report["all_bone_names_exact"],
        "head": report["head_attachment_before"]["measurements"],
    }), flush=True)


if __name__ == "__main__":
    main()
