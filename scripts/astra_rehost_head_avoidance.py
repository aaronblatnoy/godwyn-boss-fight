"""Probe or apply the rising-spin char2 head-avoidance animation beat."""
import bpy
import json
import math
import numpy as np
import sys
from pathlib import Path
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/astra_move_rising_spin_v2_wip.blend"
OUT = ROOT / "renders/astra/rehost/rising_spin"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
scene = bpy.context.scene
rig = bpy.data.objects["Armature"]
head = bpy.data.objects["AstraChar2_Mpfb_Head"]
sword = bpy.data.objects["Godwyn_Sword"]
AW = rig.matrix_world.copy()
AI = AW.inverted()
src = np.array([p.vector[:] for p in sword.data.attributes["astra_sword_source"].data])
blade_ids = set(int(i) for i in np.where(src[:, 2] < 150)[0])


def world_mesh(obj):
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = [ev.matrix_world @ v.co for v in me.vertices]
    poly = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return co, poly


def collision():
    hc, hp = world_mesh(head)
    sc, sp = world_mesh(sword)
    sp = [p for p in sp if all(i in blade_ids for i in p)]
    hb = BVHTree.FromPolygons(hc, hp)
    sb = BVHTree.FromPolygons(sc, sp)
    overlaps = len(hb.overlap(sb))
    distance = min((hb.find_nearest(sc[i])[3] for i in list(blade_ids)[::3]), default=999.0)
    return overlaps, distance


def rotate_world(bone_name, axis, degrees):
    pose = rig.pose.bones[bone_name]
    world = AW @ pose.matrix
    world = world @ Quaternion(Vector(axis), math.radians(degrees)).to_matrix().to_4x4()
    pose.matrix = AI @ world
    bpy.context.view_layer.update()


if "probe" in args:
    results = []
    for y in [-45, -35, -25, -15, 0, 15, 25, 35, 45]:
        for z in [-45, -30, -15, 0, 15, 30, 45]:
            scene.frame_set(46)
            bpy.context.view_layer.update()
            neck_basis = rig.pose.bones["neck"].matrix_basis.copy()
            head_basis = rig.pose.bones["Head"].matrix_basis.copy()
            rotate_world("neck", (0, 1, 0), y)
            rotate_world("neck", (0, 0, 1), z)
            overlaps, distance = collision()
            results.append({"y_deg": y, "z_deg": z, "overlaps": overlaps,
                            "sampled_distance_m": distance})
            rig.pose.bones["neck"].matrix_basis = neck_basis
            rig.pose.bones["Head"].matrix_basis = head_basis
            bpy.context.view_layer.update()
    results.sort(key=lambda x: (x["overlaps"], -x["sampled_distance_m"], abs(x["y_deg"]) + abs(x["z_deg"])))
    (OUT / "head_avoidance_probe.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results[:20], indent=2), flush=True)
    raise SystemExit(0)

# Applied envelope is intentionally narrow and smooth. Values are authored at
# every existing quarter-frame key; only neck rotation channels are changed.
def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def envelope(frame):
    if frame <= 30 or frame >= 54:
        return 0.0
    if frame < 38:
        return smooth((frame - 30) / 8)
    if frame <= 50:
        return 1.0
    return smooth((54 - frame) / 4)


y_deg = float(args[0]) if args else 0.0
z_deg = float(args[1]) if len(args) > 1 else -45.0
# Idempotently restore the approved source neck channels before applying this
# rehost-only correction; retain all unrelated cloth and action edits.
with bpy.data.libraries.load(str(ROOT / "models/astra_move_rising_spin_wip.blend"), link=False) as (src, dst):
    source_name = next(n for n in src.actions if n.startswith("Astra_Move_rising_spin"))
    dst.actions = [source_name]
source_action = dst.actions[0]
target_action = rig.animation_data.action
source_curves = [fc for layer in source_action.layers for strip in layer.strips
                 for bag in strip.channelbags for fc in bag.fcurves]
target_curves = [fc for layer in target_action.layers for strip in layer.strips
                 for bag in strip.channelbags for fc in bag.fcurves]
neck_path = rig.pose.bones["neck"].path_from_id("rotation_quaternion")
source_map = {(fc.data_path, fc.array_index): fc for fc in source_curves}
for fc in target_curves:
    if fc.data_path != neck_path:
        continue
    source_fc = source_map[(fc.data_path, fc.array_index)]
    assert len(fc.keyframe_points) == len(source_fc.keyframe_points)
    for key, original in zip(fc.keyframe_points, source_fc.keyframe_points):
        key.co.y = original.co.y
        key.handle_left_type = original.handle_left_type
        key.handle_right_type = original.handle_right_type
    fc.update()
bpy.data.actions.remove(source_action)
scene.frame_set(1)
bpy.context.view_layer.update()
values = []
for qf in range(4, 4 * 116 + 1):
    frame = qf / 4.0
    scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    amount = envelope(frame)
    rotate_world("neck", (0, 1, 0), y_deg * amount)
    rotate_world("neck", (0, 0, 1), z_deg * amount)
    values.append(list(rig.pose.bones["neck"].rotation_quaternion))

curves = [fc for layer in rig.animation_data.action.layers for strip in layer.strips
          for bag in strip.channelbags for fc in bag.fcurves]
path = rig.pose.bones["neck"].path_from_id("rotation_quaternion")
changed = 0
for fc in curves:
    if fc.data_path != path:
        continue
    assert len(fc.keyframe_points) == len(values)
    for key, value in zip(fc.keyframe_points, values):
        key.co.y = value[fc.array_index]
        key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
    fc.update()
    changed += 1
assert changed == 4
scene["astra_rehost_head_avoidance"] = json.dumps({
    "frames": [30, 54], "plateau_frames": [38, 50], "peak_frame": 46, "world_y_deg": y_deg,
    "world_z_deg": z_deg, "changed_channels": changed,
})
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(MODEL))
(OUT / "head_avoidance_fix.json").write_text(json.dumps({
    "frames": [30, 54], "plateau_frames": [38, 50], "peak_frame": 46, "world_y_deg": y_deg,
    "world_z_deg": z_deg, "changed_channels": changed,
}, indent=2) + "\n")
print("HEAD AVOIDANCE SAVED", y_deg, z_deg, flush=True)
