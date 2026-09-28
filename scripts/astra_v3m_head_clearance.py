"""Add a tiny clip-local Head lift to clear the high gorget on one good slash."""

import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_wip.blend"
OUT = ROOT / "renders/astra/char2/astra_v3m_head_clearance.json"
CLIP = "Right_Hand_Sword_Slash"
WORLD_LIFT_M = 0.012


def curves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    action = bpy.data.actions[CLIP]
    mapping = {(curve.data_path, curve.array_index): curve for curve in curves(action)}
    path = 'pose.bones["Head"].location'
    # Pose-channel translation is expressed in the bone's rest coordinate frame.
    local = rig.data.bones["Head"].matrix_local.to_3x3().inverted() @ Vector((0.0, 0.0, WORLD_LIFT_M))
    touched = 0
    for index in range(3):
        curve = mapping[(path, index)]
        for point in curve.keyframe_points:
            point.co[1] += local[index]
            touched += 1
        curve.update()
    action["v3m_head_clearance_world_m"] = WORLD_LIFT_M
    action["v3m_head_clearance_reason"] = "remove two-triangle jaw/gorget contact at extended frame"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report = {
        "schema": "astra-v3m-head-clearance",
        "clip": CLIP,
        "world_lift_m": WORLD_LIFT_M,
        "local_head_translation_added": list(local),
        "key_values_touched": touched,
        "reason": "The clip was visually useful, but the first full audit found two jaw/gorget triangle pairs at its most extended frame.",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_HEAD_CLEARANCE_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
