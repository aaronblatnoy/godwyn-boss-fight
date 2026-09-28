"""Probe v2 blend inputs needed by the v3 builder without modifying them."""

import argparse
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
BODY_BONES = [
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm",
    "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
FILES = {
    "skin": "models/astra_character_v2_skin_i01.blend",
    "idle_guard": "models/astra_move_idle_guard_v2_wip.blend",
    "walk_stalk": "models/astra_move_walk_stalk_v2_wip.blend",
    "lunge_thrust": "models/astra_move_lunge_thrust_v2_wip.blend",
    "rising_spin": "models/astra_move_rising_spin_v2_wip.blend",
    "xslash": "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
}


def matrix_row(matrix):
    return [list(row) for row in matrix]


def object_row(ob):
    row = {
        "name": ob.name,
        "type": ob.type,
        "parent": ob.parent.name if ob.parent else None,
        "parent_type": ob.parent_type,
        "parent_bone": ob.parent_bone,
        "matrix_world": matrix_row(ob.matrix_world),
        "location": list(ob.location),
        "rotation_quaternion": list(ob.rotation_quaternion),
        "scale": list(ob.scale),
        "modifiers": [
            {"name": mod.name, "type": mod.type, "object": getattr(getattr(mod, "object", None), "name", None)}
            for mod in ob.modifiers
        ],
    }
    if ob.type == "MESH":
        corners = [ob.matrix_world @ __import__("mathutils").Vector(corner) for corner in ob.bound_box]
        row.update({
            "vertices": len(ob.data.vertices),
            "polygons": len(ob.data.polygons),
            "bounds_world_min": [min(point[i] for point in corners) for i in range(3)],
            "bounds_world_max": [max(point[i] for point in corners) for i in range(3)],
            "materials": [slot.material.name if slot.material else None for slot in ob.material_slots],
            "vertex_groups": [group.name for group in ob.vertex_groups],
            "attributes": [attr.name for attr in ob.data.attributes],
        })
    return row


def action_row(action):
    row = {"name": action.name, "frame_range": list(action.frame_range), "use_fake_user": action.use_fake_user}
    row["slots"] = [{"identifier": slot.identifier, "target_id_type": slot.target_id_type} for slot in action.slots]
    return row


def inspect_blend(label, path):
    bpy.ops.wm.open_mainfile(filepath=str(path), load_ui=False)
    scene = bpy.context.scene
    armatures = [ob for ob in bpy.data.objects if ob.type == "ARMATURE"]
    preferred = bpy.data.objects.get("Armature")
    arm = preferred if preferred is not None else armatures[0]
    bones = {}
    for name in BODY_BONES:
        bone = arm.data.bones.get(name)
        if bone is None:
            continue
        bones[name] = {
            "parent": bone.parent.name if bone.parent else None,
            "head_armature": list(bone.head_local),
            "tail_armature": list(bone.tail_local),
            "head_world": list(arm.matrix_world @ bone.head_local),
            "tail_world": list(arm.matrix_world @ bone.tail_local),
            "length_armature": bone.length,
            "matrix_local": matrix_row(bone.matrix_local),
        }
    relevant_names = {
        "Armature", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Godwyn_Sword",
        "char1", "AstraChar2_R5_Gorget", "AstraChar2_R5_GorgetRim",
    }
    return {
        "label": label,
        "path": str(path.relative_to(ROOT)),
        "scene_frames": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps / scene.render.fps_base,
        "objects_total": len(bpy.data.objects),
        "armatures": [ob.name for ob in armatures],
        "armature": object_row(arm),
        "armature_bones": len(arm.data.bones),
        "body_bones": bones,
        "active_action": arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,
        "active_action_slot": arm.animation_data.action_slot.identifier if arm.animation_data and arm.animation_data.action_slot else None,
        "actions": [action_row(action) for action in bpy.data.actions],
        "relevant_objects": [object_row(ob) for ob in bpy.data.objects if ob.name in relevant_names],
        "scene_properties": {key: scene[key] for key in scene.keys() if key != "_RNA_UI"},
    }


def main():
    raw = __import__("sys").argv
    raw = raw[raw.index("--") + 1 :] if "--" in raw else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3_source_probe.json")
    parser.add_argument("--label", choices=sorted(FILES))
    args = parser.parse_args(raw)
    selected = {args.label: FILES[args.label]} if args.label else FILES
    result = {label: inspect_blend(label, ROOT / rel) for label, rel in selected.items()}
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print("V3_SOURCE_PROBE_PASS", json.dumps({label: {
        "bones": row["armature_bones"], "active_action": row["active_action"],
        "scene_frames": row["scene_frames"], "objects": row["objects_total"],
    } for label, row in result.items()}), flush=True)


if __name__ == "__main__":
    main()
