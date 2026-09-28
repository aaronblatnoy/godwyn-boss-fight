"""Temporary black-sky diagnostic for the Round 2 world-pose solver."""

import importlib.util
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("r2", ROOT / "scripts/astra_v3m_retarget_world.py")
r2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r2)

bpy.ops.wm.open_mainfile(filepath=str(ROOT / "models/astra_character_v3.blend"), load_ui=False)
target = bpy.data.objects["Astra_V3_Rig"]
for object_name in ("Astra_V3_Rig", "char1", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Godwyn_Sword"):
    inspected = bpy.data.objects.get(object_name)
    if inspected:
        print("R2DBG_OBJECT", object_name, "parent", inspected.parent.name if inspected.parent else "-",
              "location", tuple(inspected.location), "scale", tuple(inspected.scale),
              "world_scale", tuple(inspected.matrix_world.to_scale()),
              "modifiers", [(modifier.type, modifier.object.name if modifier.type == "ARMATURE" and modifier.object else "-") for modifier in inspected.modifiers], flush=True)
r2.reset(target)
source, source_action, imported = r2.import_source(ROOT / "models/mocap/Combat_Stance.glb")
order = r2.topological(target)
bpy.context.scene.frame_set(int(source_action.frame_range[0]))
bpy.context.view_layer.update()
target_rest = {name: target.data.bones[name].matrix_local.copy() for name in order}
target_rest_world = {name: target.matrix_world @ target.data.bones[name].matrix_local for name in order}
source_rest_world = {name: source.matrix_world @ source.data.bones[name].matrix_local for name in order}
root_rest_delta = source_rest_world["Hips"].translation - target_rest_world["Hips"].translation
world_inverse = target.matrix_world.inverted()
world_rot_inverse = target.matrix_world.to_quaternion().inverted().to_matrix()
desired_rot = {}
desired_head = {}
for name in order:
    src_world = source.matrix_world @ source.pose.bones[name].matrix
    desired_rot[name] = world_rot_inverse @ src_world.to_3x3().normalized()
    parent = target.data.bones[name].parent
    if parent is None:
        desired_head[name] = world_inverse @ (src_world.translation - root_rest_delta)
    else:
        offset = target_rest[parent.name].to_3x3().inverted() @ (
            target.data.bones[name].head_local - target.data.bones[parent.name].head_local
        )
        desired_head[name] = desired_head[parent.name] + desired_rot[parent.name] @ offset
    matrix = desired_rot[name].to_4x4()
    matrix.translation = desired_head[name]
    target.pose.bones[name].matrix = matrix
    loc, quat, scale = target.pose.bones[name].matrix_basis.decompose()
    print("R2DBG", name, "parent", parent.name if parent else "-", "connected", parent is not None and target.data.bones[name].use_connect,
          "head", tuple(round(v, 5) for v in desired_head[name]),
          "loc", tuple(round(v, 5) for v in loc),
          "scale", tuple(round(v, 5) for v in scale),
          "basis_det", target.pose.bones[name].matrix_basis.to_3x3().determinant(), flush=True)

print("R2DBG_REST_ORIENTATION_DELTAS", flush=True)
for name in order:
    source_q = source_rest_world[name].to_quaternion().normalized()
    target_q = target_rest_world[name].to_quaternion().normalized()
    angle = source_q.rotation_difference(target_q).angle
    angle_deg = min(angle, 2.0 * 3.141592653589793 - angle) * 180.0 / 3.141592653589793
    pose_world = (target.matrix_world @ target.pose.bones[name].matrix).to_quaternion().normalized()
    wanted_world = (source.matrix_world @ source.pose.bones[name].matrix).to_quaternion().normalized()
    pose_angle = pose_world.rotation_difference(wanted_world).angle
    pose_angle_deg = min(pose_angle, 2.0 * 3.141592653589793 - pose_angle) * 180.0 / 3.141592653589793
    print("R2DBG_DELTA", name, "rest_deg", round(angle_deg, 5), "assigned_pose_deg", round(pose_angle_deg, 5), flush=True)
