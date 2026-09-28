"""Publish the mechanically and visually accepted V3 Meshy mocap actions.

Run only in Blender on black-sky.  Positional arguments after ``--`` are the
accepted action names.  The source canonical is backed up only after a fully
validated temporary GLB round-trip succeeds.
"""

import hashlib
import json
import os
import shutil
import struct
import sys
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
WIP = ROOT / "models/astra_character_v3m_wip.blend"
BLEND = ROOT / "models/astra_character_v3.blend"
GLB = ROOT / "models/astra_character_v3.glb"
PREV_BLEND = ROOT / "models/astra_character_v3_prev.blend"
PREV_GLB = ROOT / "models/astra_character_v3_prev.glb"
TEMP_BLEND = ROOT / "models/astra_character_v3_publish_tmp.blend"
TEMP_GLB = ROOT / "models/astra_character_v3_publish_tmp.glb"
OUT = ROOT / "renders/astra/char2/astra_v3m_publish.json"
ROUNDTRIP_OUT = ROOT / "renders/astra/char2/astra_v3m_roundtrip.json"
EXPECTED_SOURCE_BLEND = "e254ac97530c265ee1ac36b659f4d5ae752e8d27ec6842254e8b79277ca2abc9"
EXPECTED_SOURCE_GLB = "e2577625e35af133ef3fe0e240016e59108a10e9453430c4a58d4ca95e6b9fe9"
EXPECTED_BONES = {
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
}


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def glb_json(path):
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    json_length, json_type = struct.unpack_from("<II", data, 12)
    assert json_type == 0x4E4F534A
    return json.loads(data[20:20 + json_length])


def action_counts():
    result = {}
    for action in bpy.data.actions:
        start, end = [int(round(value)) for value in action.frame_range]
        result[action.name] = end - start + 1
    return result


def rest_snapshot(rig):
    return {
        bone.name: {
            "parent": bone.parent.name if bone.parent else None,
            "head_world_m": list(rig.matrix_world @ bone.head_local),
        }
        for bone in rig.data.bones
    }


def weight_audit(objects, rig):
    rows = {}
    failures = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        modifiers = [item for item in obj.modifiers if item.type == "ARMATURE" and item.object == rig]
        if not modifiers:
            continue
        unweighted = 0
        bad_sum = 0
        maximum_error = 0.0
        for vertex in obj.data.vertices:
            total = sum(group.weight for group in vertex.groups)
            error = abs(total - 1.0)
            unweighted += int(not vertex.groups)
            bad_sum += int(error > 2e-3)
            maximum_error = max(maximum_error, error)
        failures += unweighted + bad_sum
        rows[obj.name] = {
            "vertices": len(obj.data.vertices),
            "unweighted": unweighted,
            "bad_weight_sum": bad_sum,
            "maximum_weight_sum_error": maximum_error,
        }
    return {"objects": rows, "unweighted_or_bad_sum_vertices": failures}


def export_glb(scene, rig, path):
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    for obj in scene.objects:
        asset_mesh = obj.type == "MESH" and (
            obj.name == "char1" or obj.name == "Godwyn_Sword" or obj.name.startswith("AstraChar2_")
        )
        if obj == rig or (asset_mesh and not obj.hide_render and len(obj.data.polygons)):
            obj.hide_set(False)
            obj.select_set(True)
            selected.append(obj.name)
    assert rig.name in selected
    assert {"char1", "Godwyn_Sword", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend"}.issubset(selected)
    bpy.context.view_layer.objects.active = rig
    options = {
        "filepath": str(path),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_skins": True,
        "export_def_bones": False,
        "export_leaf_bone": False,
        "export_texcoords": True,
        "export_normals": True,
        "export_tangents": True,
        "export_materials": "EXPORT",
        "export_cameras": False,
        "export_lights": False,
        "export_animations": True,
        "export_animation_mode": "ACTIONS",
        "export_frame_range": True,
        "export_force_sampling": True,
        "export_bake_animation": True,
        "export_optimize_animation_size": False,
        "export_optimize_animation_keep_anim_armature": True,
        "export_anim_scene_split_object": False,
        "export_nla_strips_merged_animation_name": "Animation",
    }
    valid = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    used = {key: value for key, value in options.items() if key in valid}
    bpy.ops.export_scene.gltf(**used)
    assert path.exists() and path.stat().st_size > 0
    return selected, sorted(used)


def main():
    accepted = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    assert accepted, "Pass at least one accepted action name after --"
    assert len(accepted) == len(set(accepted)), accepted
    assert sha256(BLEND) == EXPECTED_SOURCE_BLEND, "Canonical blend changed before publish"
    assert sha256(GLB) == EXPECTED_SOURCE_GLB, "Canonical GLB changed before publish"

    bpy.ops.wm.open_mainfile(filepath=str(WIP), load_ui=False)
    scene = bpy.context.scene
    rig = bpy.data.objects["Astra_V3_Rig"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    neck = bpy.data.objects["AstraChar2_Meshy_NeckBlend"]
    sword = bpy.data.objects["Godwyn_Sword"]
    available = {action.name for action in bpy.data.actions}
    assert set(accepted).issubset(available), (accepted, sorted(available))
    for action in list(bpy.data.actions):
        if action.name not in accepted:
            bpy.data.actions.remove(action)
    native_counts = action_counts()
    assert set(native_counts) == set(accepted)
    assert set(rig.data.bones.keys()) == EXPECTED_BONES
    assert head.parent == rig and list(head.vertex_groups.keys()) == ["Head"]
    assert neck.parent == rig and list(neck.vertex_groups.keys()) == ["neck"]
    assert sword.parent == rig and list(sword.vertex_groups.keys()) == ["RightHand"]
    native_weights = weight_audit([obj for obj in scene.objects if obj.type == "MESH"], rig)
    assert native_weights["unweighted_or_bad_sum_vertices"] == 0
    baseline = rest_snapshot(rig)
    scene.render.fps = 30
    scene["astra_v3m_accepted_actions"] = json.dumps(sorted(accepted))
    stance = bpy.data.actions.get("Combat_Stance") or bpy.data.actions[accepted[0]]
    rig.animation_data_create()
    rig.animation_data.action = stance
    if stance.slots:
        rig.animation_data.action_slot = stance.slots[0]
    scene.frame_set(int(round(stance.frame_range[0])))
    bpy.context.view_layer.update()

    for path in (TEMP_BLEND, TEMP_GLB):
        if path.exists():
            path.unlink()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TEMP_BLEND))
    selected, export_options = export_glb(scene, rig, TEMP_GLB)
    document = glb_json(TEMP_GLB)
    gltf_animation_names = sorted(item.get("name", "") for item in document.get("animations", []))
    assert set(gltf_animation_names) == set(accepted), gltf_animation_names
    skin_joint_counts = [len(item["joints"]) for item in document.get("skins", [])]
    assert skin_joint_counts and all(count == len(EXPECTED_BONES) for count in skin_joint_counts), skin_joint_counts

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(TEMP_GLB))
    imported_rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    assert len(imported_rigs) == 1, [obj.name for obj in imported_rigs]
    imported = imported_rigs[0]
    imported_counts = action_counts()
    assert set(imported_counts) == set(accepted), imported_counts
    assert imported_counts == native_counts, (native_counts, imported_counts)
    assert set(imported.data.bones.keys()) == EXPECTED_BONES
    hierarchy_ok = all(
        (bone.parent.name if bone.parent else None) == baseline[bone.name]["parent"]
        for bone in imported.data.bones
    )
    errors = {
        bone.name: float(np.max(np.abs(
            np.asarray(imported.matrix_world @ bone.head_local)
            - np.asarray(baseline[bone.name]["head_world_m"])
        )))
        for bone in imported.data.bones
    }
    roundtrip_weights = weight_audit(
        [obj for obj in bpy.context.scene.objects if obj.type == "MESH"], imported
    )
    roundtrip = {
        "schema": "astra-v3m-roundtrip",
        "temporary_glb": str(TEMP_GLB.relative_to(ROOT)),
        "action_names": sorted(imported_counts),
        "action_frame_counts": imported_counts,
        "expected_action_frame_counts": native_counts,
        "fps": 30,
        "bones": len(imported.data.bones),
        "bone_names_exact": set(imported.data.bones.keys()) == EXPECTED_BONES,
        "bone_hierarchy_preserved": hierarchy_ok,
        "world_joint_position_max_error_m": max(errors.values()),
        "skin_joint_counts": skin_joint_counts,
        "weights": roundtrip_weights,
        "gltf_animation_names": gltf_animation_names,
    }
    assert hierarchy_ok
    assert roundtrip["world_joint_position_max_error_m"] < 0.00005
    assert roundtrip_weights["unweighted_or_bad_sum_vertices"] == 0

    # Promotion occurs only after the temporary files have passed every check.
    shutil.copy2(BLEND, PREV_BLEND)
    shutil.copy2(GLB, PREV_GLB)
    assert sha256(PREV_BLEND) == EXPECTED_SOURCE_BLEND
    assert sha256(PREV_GLB) == EXPECTED_SOURCE_GLB
    os.replace(TEMP_BLEND, BLEND)
    os.replace(TEMP_GLB, GLB)
    roundtrip["published_glb"] = str(GLB.relative_to(ROOT))
    roundtrip["published_glb_sha256"] = sha256(GLB)
    ROUNDTRIP_OUT.write_text(json.dumps(roundtrip, indent=2) + "\n")
    report = {
        "schema": "astra-v3m-publish",
        "source_wip": str(WIP.relative_to(ROOT)),
        "source_wip_sha256": sha256(WIP),
        "accepted_actions": sorted(accepted),
        "action_frame_counts": native_counts,
        "fps": 30,
        "binding": {
            "head": "rigid Head",
            "neckblend": "rigid neck",
            "sword": "rigid RightHand",
        },
        "selected_objects": selected,
        "export_options_used": export_options,
        "native_weights": native_weights,
        "backup": {
            "blend": str(PREV_BLEND.relative_to(ROOT)),
            "blend_sha256": sha256(PREV_BLEND),
            "glb": str(PREV_GLB.relative_to(ROOT)),
            "glb_sha256": sha256(PREV_GLB),
        },
        "published": {
            "blend": str(BLEND.relative_to(ROOT)),
            "blend_sha256": sha256(BLEND),
            "blend_bytes": BLEND.stat().st_size,
            "glb": str(GLB.relative_to(ROOT)),
            "glb_sha256": sha256(GLB),
            "glb_bytes": GLB.stat().st_size,
        },
        "roundtrip": roundtrip,
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_PUBLISH_PASS", json.dumps({
        "accepted": sorted(accepted),
        "counts": native_counts,
        "published": report["published"],
        "backup": report["backup"],
        "joint_error_m": roundtrip["world_joint_position_max_error_m"],
    }), flush=True)


if __name__ == "__main__":
    main()
