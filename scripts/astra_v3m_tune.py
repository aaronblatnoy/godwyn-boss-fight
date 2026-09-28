"""Tame mocap deformation and add constant floor offsets from the quick audit."""

import json
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_wip.blend"
AUDIT = ROOT / "renders/astra/char2/meshy_v3m_quick_audit.json"
OUT = ROOT / "renders/astra/char2/astra_v3m_tune.json"


def curves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


def curve_map(action):
    return {(curve.data_path, curve.array_index): curve for curve in curves(action)}


def damp_action(action, factor):
    mapping = curve_map(action)
    touched = 0
    for bone in bpy.data.objects["Astra_V3_Rig"].pose.bones:
        if bone.name == "Hips":
            continue
        path = f'pose.bones["{bone.name}"].rotation_quaternion'
        channels = [mapping[(path, index)] for index in range(4)]
        count = len(channels[0].keyframe_points)
        assert all(len(channel.keyframe_points) == count for channel in channels)
        previous = None
        for key_index in range(count):
            q = Quaternion(tuple(channel.keyframe_points[key_index].co[1] for channel in channels)).normalized()
            if previous is not None and q.dot(previous) < 0:
                q.negate()
            q = Quaternion().slerp(q, factor).normalized()
            for index, channel in enumerate(channels):
                channel.keyframe_points[key_index].co[1] = q[index]
            previous = q
            touched += 1
        for channel in channels:
            channel.update()
    return touched


def add_root_lift(action, lift_world_z):
    rig = bpy.data.objects["Astra_V3_Rig"]
    local = rig.data.bones["Hips"].matrix_local.to_3x3().inverted() @ Vector((0.0, 0.0, lift_world_z / rig.matrix_world.to_scale().x))
    mapping = curve_map(action)
    path = 'pose.bones["Hips"].location'
    for index in range(3):
        curve = mapping[(path, index)]
        for point in curve.keyframe_points:
            point.co[1] += local[index]
        curve.update()
    return list(local)


def main():
    audit = json.loads(AUDIT.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    result = {}
    for name, row in audit["clips"].items():
        p99 = row["body_edge_stretch"]["worst_frame_p99"]
        # Linearized conservative estimate with a 5% buffer beneath the gate.
        factor = 1.0 if p99 <= 1.6 else min(1.0, 0.57 / max(0.57, p99 - 1.0))
        minimum = row["feet_floor"]["minimum_m"]
        lift = max(0.0, -0.004 - minimum)
        action = bpy.data.actions[name]
        touched = damp_action(action, factor) if factor < 0.999999 else 0
        local_lift = add_root_lift(action, lift) if lift else [0.0, 0.0, 0.0]
        action["v3m_rotation_amplitude"] = factor
        action["v3m_constant_floor_lift_m"] = lift
        result[name] = {
            "source_worst_p99": p99,
            "non_root_rotation_amplitude": factor,
            "quaternion_keys_touched": touched,
            "source_minimum_sole_m": minimum,
            "constant_world_floor_lift_m": lift,
            "root_local_lift": local_lift,
        }
        print("V3M_TUNE", name, json.dumps(result[name]), flush=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report = {"schema": "astra-v3m-tune", "blend": str(BLEND.relative_to(ROOT)), "clips": result}
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_TUNE_PASS", len(result), flush=True)


if __name__ == "__main__":
    main()
