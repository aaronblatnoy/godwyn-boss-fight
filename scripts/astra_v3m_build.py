"""Build the V3 mocap/head-fix WIP from the published fist-body V3.

Run in Blender on black-sky only.  The canonical files are not overwritten.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/astra_character_v3.blend"
WIP = ROOT / "models/astra_character_v3m_wip.blend"
MOCAP = ROOT / "models/mocap"
OUT = ROOT / "renders/astra/char2/astra_v3m_build.json"
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


def action_channelbag(action):
    layer = action.layers.new("V3M Layer")
    strip = layer.strips.new(type="KEYFRAME")
    slot = action.slots.new(id_type="OBJECT", name="Astra_V3_Rig")
    return slot, strip.channelbag(slot, ensure=True)


def curve_key(bag, path, index, frame, value):
    curve = bag.fcurves.find(path, index=index) or bag.fcurves.new(path, index=index)
    point = curve.keyframe_points.insert(frame, value, options={"FAST"})
    point.interpolation = "LINEAR"


def assign_action(rig, action, frame):
    animation = rig.animation_data_create()
    animation.action = action
    if action.slots:
        animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def skin_material(head):
    skin = head.data.color_attributes["meshy_skin_mask"]
    indices = []
    for poly in head.data.polygons:
        if np.mean([skin.data[index].color[0] for index in poly.loop_indices]) >= 0.5:
            indices.append(poly.material_index)
    assert indices
    return head.data.materials[Counter(indices).most_common(1)[0][0]]


def head_skin_points(head):
    skin = head.data.color_attributes["meshy_skin_mask"]
    ids = set()
    for poly in head.data.polygons:
        if np.mean([skin.data[index].color[0] for index in poly.loop_indices]) >= 0.5:
            ids.update(poly.vertices)
    return np.asarray([(head.matrix_world @ head.data.vertices[index].co)[:] for index in sorted(ids)], dtype=float)


def transform_mesh_world(ob, matrix):
    inverse = ob.matrix_world.inverted()
    for vertex in ob.data.vertices:
        vertex.co = inverse @ (matrix @ (ob.matrix_world @ vertex.co))
    ob.data.update()


def rigid_bind(obj, rig, bone):
    for modifier in list(obj.modifiers):
        if modifier.type == "ARMATURE":
            obj.modifiers.remove(modifier)
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    group = obj.vertex_groups.new(name=bone)
    group.add(range(len(obj.data.vertices)), 1.0, "REPLACE")
    modifier = obj.modifiers.new("V3M rigid attachment", "ARMATURE")
    modifier.object = rig
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "OBJECT"
    obj.parent_bone = ""
    obj.matrix_world = world


def create_neckblend(rig, head, center):
    old = bpy.data.objects.get("AstraChar2_Meshy_NeckBlend")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    x, y = center
    rings = [
        (2.485, 0.112, 0.088),
        (2.535, 0.110, 0.085),
        (2.595, 0.104, 0.080),
        (2.650, 0.096, 0.074),
        (2.690, 0.089, 0.068),
    ]
    segments = 48
    vertices = []
    for z, rx, ry in rings:
        for index in range(segments):
            angle = 2.0 * np.pi * index / segments
            vertices.append((x + rx * np.cos(angle), y + ry * np.sin(angle), z))
    faces = []
    for ring in range(len(rings) - 1):
        for index in range(segments):
            nxt = (index + 1) % segments
            a = ring * segments + index
            b = ring * segments + nxt
            c = (ring + 1) * segments + nxt
            d = (ring + 1) * segments + index
            faces.append((a, b, c, d))
    faces.append(tuple(reversed(range(segments))))
    top = (len(rings) - 1) * segments
    faces.append(tuple(top + index for index in range(segments)))
    mesh = bpy.data.meshes.new("AstraChar2_Meshy_NeckBlend_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(skin_material(head))
    neck = bpy.data.objects.new("AstraChar2_Meshy_NeckBlend", mesh)
    bpy.context.scene.collection.objects.link(neck)
    for poly in mesh.polygons:
        poly.use_smooth = True
    rigid_bind(neck, rig, "neck")
    neck["v3m_role"] = "collar-interior neck bridge driven rigidly by neck bone"
    return neck, {"center_xy_m": [x, y], "rings": [{"z_m": z, "radius_x_m": rx, "radius_y_m": ry} for z, rx, ry in rings], "parent_bone": "neck"}


def fix_head(rig, head):
    before = head_skin_points(head)
    low, high = before.min(axis=0), before.max(axis=0)
    span = high[2] - low[2]
    candidates = before[before[:, 2] >= low[2] + 0.12 * span]
    jaw_before = float(np.percentile(candidates[:, 2], 2.0))
    # Preserve the face's lateral alignment.  Scale modestly around the head-bone
    # anchor and lower the whole donor so the jaw nestles into the high gorget.
    pivot = rig.matrix_world @ rig.data.bones["Head"].head_local
    scale = 0.94
    lower = 0.020
    matrix = Matrix.Translation(Vector((0.0, 0.0, -lower))) @ Matrix.Translation(pivot) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-pivot)
    transform_mesh_world(head, matrix)
    rigid_bind(head, rig, "Head")
    after = head_skin_points(head)
    low_after, high_after = after.min(axis=0), after.max(axis=0)
    span_after = high_after[2] - low_after[2]
    candidates_after = after[after[:, 2] >= low_after[2] + 0.12 * span_after]
    jaw_after = float(np.percentile(candidates_after[:, 2], 2.0))
    neck_subset = after[after[:, 2] <= jaw_after + 0.015]
    center = np.median(neck_subset[:, :2], axis=0) if len(neck_subset) else np.median(after[:, :2], axis=0)
    neck, neck_report = create_neckblend(rig, head, center)
    return neck, {
        "method": "uniform 0.94 scale about Head rest anchor followed by 20 mm lowering",
        "scale": scale,
        "lowering_m": lower,
        "pivot_world_m": list(pivot),
        "jaw_underside_before_m": jaw_before,
        "jaw_underside_after_m": jaw_after,
        "skin_bounds_before_m": {"min": low.tolist(), "max": high.tolist()},
        "skin_bounds_after_m": {"min": low_after.tolist(), "max": high_after.tolist()},
        "head_binding": {"parent": head.parent.name, "groups": list(head.vertex_groups.keys()), "modifier": head.modifiers[-1].object.name},
        "neckblend": neck_report,
    }


def import_source(path):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(path))
    added_objects = [ob for ob in bpy.data.objects if ob not in before_objects]
    added_actions = [action for action in bpy.data.actions if action not in before_actions]
    rigs = [ob for ob in added_objects if ob.type == "ARMATURE"]
    assert len(rigs) == 1, (path.name, [ob.name for ob in added_objects])
    assert len(added_actions) == 1, (path.name, [action.name for action in added_actions])
    source = rigs[0]
    source.animation_data_create()
    source.animation_data.action = added_actions[0]
    if added_actions[0].slots:
        source.animation_data.action_slot = added_actions[0].slots[0]
    return source, added_actions[0], added_objects


def retarget_clip(path, target):
    source, source_action, imported_objects = import_source(path)
    source_action_name = source_action.name
    source_names = [bone.name for bone in source.data.bones]
    assert sorted(source_names) == sorted(EXPECTED), (path.name, source_names)
    rest_rows = []
    for name in EXPECTED:
        src = source.matrix_world @ source.data.bones[name].matrix_local
        dst = target.matrix_world @ target.data.bones[name].matrix_local
        rest_rows.append({
            "bone": name,
            "head_difference_m": float((src.translation - dst.translation).length),
            "matrix_max_abs_difference": float(np.max(np.abs(np.asarray(src) - np.asarray(dst)))),
        })
    start, end = [int(round(value)) for value in source_action.frame_range]
    name = path.stem
    old = bpy.data.actions.get(name)
    if old:
        bpy.data.actions.remove(old)
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    action["v3m_source_file"] = str(path.relative_to(ROOT))
    action["v3m_source_sha256"] = sha256(path)
    action["v3m_fps"] = 30
    action["v3m_frame_count"] = end - start + 1
    action["v3m_retarget"] = "per-bone rest-relative rotation delta plus root translation"
    slot, bag = action_channelbag(action)
    scene = bpy.context.scene
    for output_frame, source_frame in enumerate(range(start, end + 1), 1):
        scene.frame_set(source_frame)
        bpy.context.view_layer.update()
        for bone in EXPECTED:
            source_bone = source.pose.bones[bone]
            target_bone = target.pose.bones[bone]
            target_bone.rotation_mode = "QUATERNION"
            # Pose channels are deltas relative to each rig's own rest matrix, so
            # applying them by name performs the required per-bone rest offset.
            target_bone.rotation_quaternion = source_bone.rotation_quaternion.normalized()
            # Meshy writes translation channels on every joint.  Keeping those
            # non-root translations on a slightly different rest skeleton pulls
            # seams apart.  Standard skeletal retargeting retains joint rotation
            # deltas and root translation, while each target child keeps its own
            # rest offset from its parent.
            target_bone.location = source_bone.location if bone == "Hips" else Vector((0.0, 0.0, 0.0))
            target_bone.scale = Vector((1.0, 1.0, 1.0))
            q = target_bone.rotation_quaternion.normalized()
            for index, value in enumerate(q):
                curve_key(bag, f'pose.bones["{bone}"].rotation_quaternion', index, output_frame, value)
            for index, value in enumerate(target_bone.location):
                curve_key(bag, f'pose.bones["{bone}"].location', index, output_frame, value)
        if output_frame == 1 or output_frame == end - start + 1 or output_frame % 30 == 0:
            print("V3M_RETARGET", name, output_frame, "/", end - start + 1, flush=True)
    for curve in bag.fcurves:
        curve.update()
    assign_action(target, action, 1)
    root_start = (target.matrix_world @ target.pose.bones["Hips"].head).copy()
    assign_action(target, action, end - start + 1)
    root_end = (target.matrix_world @ target.pose.bones["Hips"].head).copy()
    for ob in imported_objects:
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    if source_action.users == 0:
        bpy.data.actions.remove(source_action)
    return action, {
        "file": path.name,
        "source_sha256": sha256(path),
        "source_action": source_action_name,
        "target_action": name,
        "frames": end - start + 1,
        "fps": 30,
        "bone_names_set_exact": sorted(source_names) == sorted(EXPECTED),
        "source_bone_order": source_names,
        "rest_offset": {
            "method": "per-bone rotation delta relative to source rest applied to target rest; root translation preserved; non-root translation suppressed to prevent skeletal separation",
            "max_head_difference_m": max(row["head_difference_m"] for row in rest_rows),
            "max_matrix_element_difference": max(row["matrix_max_abs_difference"] for row in rest_rows),
            "by_bone": rest_rows,
        },
        "root_displacement_m": list(root_end - root_start),
        "root_displacement_length_m": float((root_end - root_start).length),
        "in_place": (root_end - root_start).length < 0.01,
    }


def main():
    assert sha256(SOURCE) == "e254ac97530c265ee1ac36b659f4d5ae752e8d27ec6842254e8b79277ca2abc9"
    manifest = json.loads((MOCAP / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    neck, head_report = fix_head(rig, head)
    old_actions = list(bpy.data.actions)
    clips = []
    new_actions = []
    for item in manifest["clips"]:
        action, row = retarget_clip(MOCAP / item["file"], rig)
        row["action_id"] = item["action_id"]
        row["intended_role"] = item["role"]
        clips.append(row)
        new_actions.append(action)
    for action in old_actions:
        if action.name in bpy.data.actions and action not in new_actions:
            bpy.data.actions.remove(action)
    assert sorted(action.name for action in bpy.data.actions) == sorted(item["target_action"] for item in clips)
    stance = bpy.data.actions["Combat_Stance"]
    assign_action(rig, stance, 1)
    report = {
        "schema": "astra-v3m-build",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": sha256(SOURCE),
        "wip": str(WIP.relative_to(ROOT)),
        "fps": 30,
        "head_fix": head_report,
        "clips": clips,
        "clip_count": len(clips),
        "all_hashes_distinct": len({row["source_sha256"] for row in clips}) == len(clips),
        "all_bones_match": all(row["bone_names_set_exact"] for row in clips),
        "action_names": sorted(action.name for action in new_actions),
    }
    scene["astra_v3m"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(WIP))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_BUILD_PASS", json.dumps({"wip": str(WIP), "clips": len(clips), "head": head_report, "distinct": report["all_hashes_distinct"]}), flush=True)


if __name__ == "__main__":
    main()
