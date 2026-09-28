"""Native and GLB round-trip numeric validation for Meshy body i01."""
import bpy
import hashlib
import json
import numpy as np
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "models/astra_character_v2_body_i01.blend"
GLB = ROOT / "models/astra_character_v2_body_i01.glb"
OUT = ROOT / "renders/astra/char2"


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def reset(rig):
    rig.animation_data_clear()
    for pose in rig.pose.bones:
        pose.matrix_basis.identity()
    bpy.context.view_layer.update()


def weight_check(objects, rig):
    rows = {}
    unweighted_or_bad = 0
    maximum_error = 0.0
    for obj in objects:
        modifiers = [modifier for modifier in obj.modifiers if modifier.type == "ARMATURE"]
        if obj.type != "MESH" or not modifiers or modifiers[0].object != rig:
            continue
        unweighted = bad = 0
        error = 0.0
        for vertex in obj.data.vertices:
            total = sum(item.weight for item in vertex.groups)
            unweighted += int(not vertex.groups)
            bad += int(abs(total - 1.0) > 2e-3)
            error = max(error, abs(total - 1.0))
        rows[obj.name] = {"vertices": len(obj.data.vertices), "unweighted": unweighted,
                          "bad_weight_sum": bad, "max_weight_sum_error": error}
        unweighted_or_bad += unweighted + bad
        maximum_error = max(maximum_error, error)
    return {"objects": rows, "unweighted_or_bad_sum_vertices": unweighted_or_bad,
            "weight_sum_max_error": maximum_error}


def glb_json(path):
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    json_length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20 + json_length])


def main():
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    rig = bpy.data.objects["Armature"]
    reset(rig)
    baseline = {bone.name: {"head": list(rig.matrix_world @ bone.head_local),
                            "parent": bone.parent.name if bone.parent else None,
                            "rest": np.asarray(bone.matrix_local).tolist()}
                for bone in rig.data.bones}
    body = bpy.data.objects["char1"]
    plate_attribute = body.data.attributes["astra_body_plate"]
    plate_vertices = {index for polygon in body.data.polygons if plate_attribute.data[polygon.index].value
                      for index in polygon.vertices}
    group_names = {group.index: group.name for group in body.vertex_groups}
    plate_bad = 0
    for index in plate_vertices:
        entries = [(group_names[item.group], item.weight) for item in body.data.vertices[index].groups
                   if item.weight > 1e-8]
        plate_bad += int(len(entries) != 1 or entries[0][0].startswith("phys_")
                         or abs(entries[0][1] - 1.0) > 2e-6)
    native = {
        "source": str(CANDIDATE.relative_to(ROOT)), "source_sha256": sha256(CANDIDATE),
        "bones": len(rig.data.bones), "actions": len(bpy.data.actions), "rest_matrix_error": 0.0,
        "head_hair_preserved": "AstraChar2_Meshy_HeadHair" in bpy.data.objects,
        "neck_blend_preserved": "AstraChar2_Meshy_NeckBlend" in bpy.data.objects,
        "sword_binding": {"groups": list(bpy.data.objects["Godwyn_Sword"].vertex_groups.keys()),
                          "parent": bpy.data.objects["Godwyn_Sword"].parent.name},
        "body_weights": weight_check([body], rig), "all_visible_weights": weight_check(
            [obj for obj in bpy.context.scene.objects if not obj.hide_render], rig),
        "plate_vertices": len(plate_vertices), "plate_nonrigid_or_phys_vertices": plate_bad,
    }
    assert native["bones"] == 121 and native["actions"] == 0
    assert native["body_weights"]["unweighted_or_bad_sum_vertices"] == 0 and plate_bad == 0
    assert native["sword_binding"]["groups"] == ["RightHand"]
    (OUT / "meshy_body_validation.json").write_text(json.dumps(native, indent=2) + "\n")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    rig = next(obj for obj in bpy.data.objects if obj.type == "ARMATURE")
    reset(rig)
    errors = {bone.name: float(np.max(np.abs(
        np.asarray(rig.matrix_world @ bone.head_local) - np.asarray(baseline[bone.name]["head"]))))
        for bone in rig.data.bones}
    gltf = glb_json(GLB)
    roundtrip = {
        "source": str(GLB.relative_to(ROOT)), "source_sha256": sha256(GLB),
        "bones": len(rig.data.bones), "actions": len(bpy.data.actions),
        "world_joint_position_max_error_m": max(errors.values()),
        "world_joint_position_tolerance_m": 0.00005,
        "bone_names_and_hierarchy_preserved": all(
            (bone.parent.name if bone.parent else None) == baseline[bone.name]["parent"]
            for bone in rig.data.bones),
        "glb_skin_joint_counts": [len(skin["joints"]) for skin in gltf.get("skins", [])],
        "glb_animations": len(gltf.get("animations", [])),
        "materials": [material.get("name") for material in gltf.get("materials", [])],
        "images": [image.get("name") for image in gltf.get("images", [])],
        "weights": weight_check([obj for obj in bpy.context.scene.objects if obj.type == "MESH"], rig),
    }
    assert roundtrip["bones"] == 121 and roundtrip["actions"] == 0
    assert roundtrip["world_joint_position_max_error_m"] < 0.00005
    assert roundtrip["bone_names_and_hierarchy_preserved"] and not roundtrip["glb_animations"]
    assert roundtrip["glb_skin_joint_counts"] and all(count == 121 for count in roundtrip["glb_skin_joint_counts"])
    assert roundtrip["weights"]["unweighted_or_bad_sum_vertices"] == 0
    (OUT / "meshy_body_roundtrip.json").write_text(json.dumps(roundtrip, indent=2) + "\n")
    print("BODY_VALIDATE_PASS", json.dumps({"native": {"bones": native["bones"],
          "unweighted": native["body_weights"]["unweighted_or_bad_sum_vertices"],
          "plate_bad": plate_bad}, "roundtrip": {"bones": roundtrip["bones"],
          "joint_error_m": roundtrip["world_joint_position_max_error_m"],
          "unweighted": roundtrip["weights"]["unweighted_or_bad_sum_vertices"]}}), flush=True)


if __name__ == "__main__":
    main()
