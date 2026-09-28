"""Publish Godwyn v3 Blend/GLB and round-trip validate skeleton plus five clips."""

import hashlib
import json
import struct
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
WIP = ROOT / "models/astra_character_v3_wip.blend"
FINAL_BLEND = ROOT / "models/astra_character_v3.blend"
FINAL_GLB = ROOT / "models/astra_character_v3.glb"
OUT = ROOT / "renders/astra/char2"
ROUNDTRIP = OUT / "meshy_v3_roundtrip.json"
PUBLISH = OUT / "meshy_v3_publish.json"
MOVES = {"idle_guard": 96, "walk_stalk": 72, "lunge_thrust": 64, "rising_spin": 116, "xslash": 90}
ACTION_NAMES = [f"Godwyn_V3_{name}" for name in MOVES]
EXPECTED_BONES = [
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
PROTECTED = {
    "models/astra_character_v2.blend": "a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255",
    "models/astra_character_v2.glb": "17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protected_hashes():
    result = {}
    for relative, expected in PROTECTED.items():
        path = ROOT / relative
        actual = sha256(path)
        assert actual == expected, f"Protected v2 changed: {relative} {actual} != {expected}"
        result[relative] = actual
    return result


def read_glb_json(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2 and length == len(data)
    offset = 12
    chunks = []
    while offset < len(data):
        size, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset:offset + size]
        offset += size
        chunks.append((kind, payload))
    json_chunk = next(payload for kind, payload in chunks if kind == 0x4E4F534A)
    return json.loads(json_chunk.decode("utf-8").rstrip(" \t\r\n\x00"))


def glb_clip_summary(document):
    accessors = document.get("accessors", [])
    result = []
    for animation in document.get("animations", []):
        starts, ends = [], []
        for sampler in animation.get("samplers", []):
            accessor = accessors[sampler["input"]]
            if "min" in accessor:
                starts.append(float(accessor["min"][0]))
            if "max" in accessor:
                ends.append(float(accessor["max"][0]))
        start = min(starts) if starts else None
        end = max(ends) if ends else None
        result.append({
            "name": animation.get("name", ""), "channels": len(animation.get("channels", [])),
            "start_seconds": start, "end_seconds": end,
            "duration_seconds": (end - start) if start is not None and end is not None else None,
        })
    return result


def action_summary(actions):
    result = []
    for action in actions:
        start, end = action.frame_range
        result.append({"name": action.name, "frame_start": float(start), "frame_end": float(end), "frames_inclusive": int(round(end - start)) + 1})
    return sorted(result, key=lambda item: item["name"])


def body_weight_summary(body):
    unweighted = 0
    bad_sum = 0
    influences = []
    for vertex in body.data.vertices:
        values = [item.weight for item in vertex.groups if item.weight > 1e-8]
        influences.append(len(values))
        if not values:
            unweighted += 1
        elif abs(sum(values) - 1.0) > 1e-3:
            bad_sum += 1
    return {
        "vertices": len(body.data.vertices), "vertex_groups": len(body.vertex_groups),
        "unweighted_vertices": unweighted, "bad_weight_sum_vertices": bad_sum,
        "influences_min": min(influences), "influences_max": max(influences),
    }


def main():
    protected_before = protected_hashes()
    bpy.ops.wm.open_mainfile(filepath=str(WIP), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    desired = [bpy.data.actions[name] for name in ACTION_NAMES]
    for action in list(bpy.data.actions):
        if action not in desired:
            bpy.data.actions.remove(action)
    assert sorted(action.name for action in bpy.data.actions) == sorted(ACTION_NAMES)
    for move, count in MOVES.items():
        action = bpy.data.actions[f"Godwyn_V3_{move}"]
        assert int(round(action.frame_range[1] - action.frame_range[0])) + 1 == count
    source_action_rows = action_summary(desired)
    animation = rig.animation_data_create()
    animation.action = bpy.data.actions["Godwyn_V3_idle_guard"]
    animation.action_slot = animation.action.slots[0]
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(FINAL_BLEND))
    export_names = [
        "Astra_V3_Rig", "char1", "AstraChar2_Meshy_HeadHair", "Godwyn_Sword",
        "Astra_V3_Rigid_Neck_Bridge", "Astra_V3_Neck_Gorget_Trim",
    ]
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = []
    for name in export_names:
        obj = bpy.data.objects.get(name)
        assert obj is not None, f"Missing publish object: {name}"
        obj.select_set(True)
        export_objects.append(obj)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(
        filepath=str(FINAL_GLB), export_format="GLB", use_selection=True,
        export_animations=True, export_animation_mode="ACTIONS", export_merge_animation="NONE",
        export_force_sampling=True, export_frame_range=False, export_def_bones=True,
        export_extras=True,
    )
    assert FINAL_BLEND.exists() and FINAL_BLEND.stat().st_size > 0
    assert FINAL_GLB.exists() and FINAL_GLB.stat().st_size > 0
    document = read_glb_json(FINAL_GLB)
    clip_summary = glb_clip_summary(document)
    clip_names = sorted(item["name"] for item in clip_summary)
    assert clip_names == sorted(ACTION_NAMES), f"GLB clips wrong: {clip_names}"
    assert len(document.get("skins", [])) == 1
    assert len(document["skins"][0].get("joints", [])) == 24
    for item in clip_summary:
        move = item["name"].removeprefix("Godwyn_V3_")
        expected_duration = (MOVES[move] - 1) / 30.0
        assert abs(item["duration_seconds"] - expected_duration) < 1e-4, (item, expected_duration)
    exported = {
        "glb_animations": clip_summary,
        "glb_animation_count": len(clip_summary),
        "glb_skin_count": len(document.get("skins", [])),
        "glb_skin_joint_count": len(document["skins"][0].get("joints", [])),
        "glb_mesh_count": len(document.get("meshes", [])),
        "glb_node_count": len(document.get("nodes", [])),
    }
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(FINAL_GLB))
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    assert len(armatures) == 1
    imported_rig = armatures[0]
    imported_bones = [bone.name for bone in imported_rig.data.bones]
    imported_actions = list(bpy.data.actions)
    imported_action_names = sorted(action.name for action in imported_actions)
    assert sorted(imported_bones) == sorted(EXPECTED_BONES), imported_bones
    assert imported_action_names == sorted(ACTION_NAMES), imported_action_names
    for action in imported_actions:
        move = action.name.removeprefix("Godwyn_V3_")
        imported_count = int(round(action.frame_range[1] - action.frame_range[0])) + 1
        assert imported_count == MOVES[move], (action.name, imported_count, MOVES[move])
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    imported_body = max(mesh_objects, key=lambda obj: len(obj.data.vertices))
    weights = body_weight_summary(imported_body)
    assert weights["unweighted_vertices"] == 0
    assert weights["bad_weight_sum_vertices"] == 0
    roundtrip = {
        "schema": "astra-v3-glb-roundtrip",
        "source_glb": str(FINAL_GLB.relative_to(ROOT)),
        "armatures": len(armatures), "rig_object": imported_rig.name,
        "bone_count": len(imported_bones), "bone_names": imported_bones,
        "expected_bone_names_exact": sorted(imported_bones) == sorted(EXPECTED_BONES),
        "animation_count": len(imported_actions), "animations": action_summary(imported_actions),
        "expected_animation_names_exact": imported_action_names == sorted(ACTION_NAMES),
        "largest_mesh_object": imported_body.name, "largest_mesh_weights": weights,
        "pass": True,
    }
    ROUNDTRIP.write_text(json.dumps(roundtrip, indent=2) + "\n")
    protected_after = protected_hashes()
    publish = {
        "schema": "astra-v3-publish",
        "source_wip": str(WIP.relative_to(ROOT)),
        "blend": {"path": str(FINAL_BLEND.relative_to(ROOT)), "bytes": FINAL_BLEND.stat().st_size, "sha256": sha256(FINAL_BLEND)},
        "glb": {"path": str(FINAL_GLB.relative_to(ROOT)), "bytes": FINAL_GLB.stat().st_size, "sha256": sha256(FINAL_GLB)},
        "actions": source_action_rows, "fps": 30,
        "selected_export_objects": export_names,
        "glb_document": exported,
        "roundtrip_pass": roundtrip["pass"],
        "protected_v2_hashes_before": protected_before,
        "protected_v2_hashes_after": protected_after,
        "protected_v2_unchanged": protected_before == protected_after,
        "publish_pass": True,
    }
    PUBLISH.write_text(json.dumps(publish, indent=2) + "\n")
    print("V3_PUBLISH_PASS", json.dumps({"blend": publish["blend"], "glb": publish["glb"], "clips": clip_names, "bones": len(imported_bones), "protected_v2_unchanged": publish["protected_v2_unchanged"]}), flush=True)


if __name__ == "__main__":
    main()
