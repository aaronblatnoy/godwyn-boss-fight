"""Adaptive derived-only distal cloth lift for rehosted evaluated geometry."""
import bpy
import json
import numpy as np
import sys
from pathlib import Path

args = sys.argv[sys.argv.index("--") + 1:]
name, model, out_dir = args[0], Path(args[1]), Path(args[2])
surface = json.loads((out_dir / "surface_verification.json").read_text())
target = surface["old_body"]["cloth_min_m"] + 0.00005
bpy.ops.wm.open_mainfile(filepath=str(model))
scene = bpy.context.scene
rig = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
stage = next(o for o in scene.objects if o.name in {"Astra_Move_Stage", "Astra_Stage"})
floor = max((stage.matrix_world @ v.co).z for v in stage.data.vertices)
AW = rig.matrix_world.copy()
AI = AW.inverted()
groups = {g.index: g.name for g in body.vertex_groups}
families = {}
for bone in rig.pose.bones:
    if bone.name.startswith(("phys_robe", "phys_cape")):
        families.setdefault(bone.name.rsplit("_", 1)[0], {"bones": [], "vertices": []})["bones"].append(bone.name)
for v in body.data.vertices:
    if (body.matrix_world @ v.co).z > .4:
        continue
    weights = {}
    for g in v.groups:
        family = groups[g.group].rsplit("_", 1)[0]
        if family in families:
            weights[family] = weights.get(family, 0.0) + g.weight
    for family, weight in weights.items():
        if weight > .55:
            families[family]["vertices"].append(v.index)
families = {k: v for k, v in families.items() if len(v["vertices"]) > 10}
for data in families.values():
    data["bones"].sort()
    data["needed"] = []

action_end = int(round(rig.animation_data.action.frame_range[1]))
for frame in range(1, action_end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    obj = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = obj.to_mesh()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    matrix = np.array(obj.matrix_world)
    co = co @ matrix[:3, :3].T + matrix[:3, 3]
    for data in families.values():
        clearance = float(co[data["vertices"], 2].min() - floor)
        # The lowest panel vertices blend multiple links, so a distal-chain
        # translation produces less than one-for-one surface lift.
        data["needed"].append(max(0.0, target - clearance) * 1.7)
    obj.to_mesh_clear()

max_needed = max((max(d["needed"]) for d in families.values()), default=0.0)
report = {family: {"vertices": len(data["vertices"]),
                   "max_requested_lift_m": max(data["needed"])}
          for family, data in families.items() if max(data["needed"]) > 0}
families = {family: data for family, data in families.items() if family in report}
if max_needed <= 0:
    print("CLOTH FIX NOT NEEDED", name, flush=True)
    raise SystemExit(0)

visibility = [(o, o.hide_viewport) for o in scene.objects if o.type in {"MESH", "CURVES"}]
for obj, _ in visibility:
    obj.hide_viewport = True
captured = {}
end = action_end
for qf in range(4, 4 * end + 1):
    frame = qf / 4.0
    scene.frame_set(int(frame), subframe=frame % 1)
    bpy.context.view_layer.update()
    for family, data in families.items():
        needed = float(np.interp(frame, np.arange(1, end + 1), data["needed"]))
        previous = 0.0
        last = len(data["bones"]) - 1
        for depth, bone_name in enumerate(data["bones"]):
            if last <= 2:
                continue
            t = max(0.0, (depth - 2) / (last - 2))
            cumulative = needed * t * t * (3.0 - 2.0 * t)
            increment = cumulative - previous
            previous = cumulative
            if depth <= 2:
                continue
            pose = rig.pose.bones[bone_name]
            if increment != 0:
                world = AW @ pose.matrix
                world.translation.z += increment
                pose.matrix = AI @ world
                bpy.context.view_layer.update()
            captured.setdefault(bone_name, []).append(list(pose.location))

curves = [fc for layer in rig.animation_data.action.layers for strip in layer.strips
          for bag in strip.channelbags for fc in bag.fcurves]
for bone_name, values in captured.items():
    path = rig.pose.bones[bone_name].path_from_id("location")
    for fc in curves:
        if fc.data_path != path:
            continue
        assert len(fc.keyframe_points) == len(values)
        for key, value in zip(fc.keyframe_points, values):
            key.co.y = value[fc.array_index]
            key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
        fc.update()
for obj, hidden in visibility:
    obj.hide_viewport = hidden
scene["astra_rehost_cloth_floor_fix"] = json.dumps(report)
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(model))
(out_dir / "cloth_floor_fix.json").write_text(json.dumps({
    "name": name, "target_clearance_m": target,
    "max_requested_lift_m": max_needed, "families": report,
}, indent=2) + "\n")
print("CLOTH FIX COMPLETE", name, json.dumps(report), flush=True)
