"""Gather distal robe/cape chains until quarter-frame floor clearance passes."""
import bpy
import hashlib
import json
import numpy as np
import sys
from collections import defaultdict
from pathlib import Path


args = sys.argv[sys.argv.index("--") + 1:]
source, destination, before_path, report_path = map(Path, args[:4])
assert source.resolve() != destination.resolve(), "source must remain read-only"
target_clearance = 0.00225  # 0.25 mm guard band above the required +2.0 mm.
required_clearance = 0.002
max_passes = 5


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


source_sha256 = sha256(source)
before = json.loads(before_path.read_text())
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
rig = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
stage = next(obj for obj in scene.objects if obj.name in {"Astra_Move_Stage", "Astra_Stage"})
floor_z = max(float((stage.matrix_world @ vertex.co).z) for vertex in stage.data.vertices)
action = rig.animation_data.action
end = int(round(action.frame_range[1]))
assert [scene.frame_start, scene.frame_end] == [1, 90]
assert end == 90 and before["samples"] == 357

families = defaultdict(list)
for bone in rig.pose.bones:
    if bone.name.startswith(("phys_robe", "phys_cape")):
        families[bone.name.rsplit("_", 1)[0]].append(bone.name)
families = {name: sorted(bones) for name, bones in families.items()
            if name in before["vertex_counts"]["families"]}
selected_families = sorted({
    family
    for row in before["rows"]
    for family, clearance in row["family_minimum_clearance_m"].items()
    if clearance < target_clearance
})
assert selected_families
modified_bones = sorted(bone for family in selected_families for bone in families[family][3:])
assert all(bone.startswith(("phys_robe", "phys_cape")) for bone in modified_bones)

group_names = {group.index: group.name for group in body.vertex_groups}
family_vertices = defaultdict(list)
for vertex in body.data.vertices:
    if float((body.matrix_world @ vertex.co).z) > 0.4:
        continue
    weights = defaultdict(float)
    for membership in vertex.groups:
        family = group_names[membership.group].rsplit("_", 1)[0]
        if family in families:
            weights[family] += float(membership.weight)
    if not weights:
        continue
    family, weight = max(weights.items(), key=lambda item: item[1])
    if weight > 0.55:
        family_vertices[family].append(vertex.index)
family_vertices = {name: np.asarray(indices, dtype=np.int32)
                   for name, indices in family_vertices.items() if name in families}
assert set(family_vertices) == set(families)

curves = [curve for layer in action.layers for strip in layer.strips
          for bag in strip.channelbags for curve in bag.fcurves]


def curve_digest(excluded_bones=()):
    excluded_paths = {rig.pose.bones[name].path_from_id("location") for name in excluded_bones}
    digest = hashlib.sha256()
    for curve in sorted(curves, key=lambda item: (item.data_path, item.array_index)):
        if curve.data_path in excluded_paths:
            continue
        digest.update(f"{curve.data_path}|{curve.array_index}|".encode())
        for key in curve.keyframe_points:
            digest.update(("%.9f,%.9f,%.9f,%.9f,%.9f,%.9f|" % (
                key.co.x, key.co.y, key.handle_left.x, key.handle_left.y,
                key.handle_right.x, key.handle_right.y)).encode())
    return digest.hexdigest()


noncloth_digest_before = curve_digest(modified_bones)
all_curve_digest_before = curve_digest()
rest_digest_before = hashlib.sha256("".join(
    f"{bone.name}:{tuple(value for row in bone.matrix_local for value in row)}:{bone.parent.name if bone.parent else ''};"
    for bone in rig.data.bones).encode()).hexdigest()
mesh_digest_before = before.get("mesh_digest")


def evaluated_world_coordinates():
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    coordinates = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coordinates)
    coordinates = coordinates.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coordinates = coordinates @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return coordinates


def measure():
    rows = []
    for quarter_index in range(4, 4 * end + 1):
        frame = quarter_index / 4.0
        scene.frame_set(int(frame), subframe=frame % 1.0)
        bpy.context.view_layer.update()
        coordinates = evaluated_world_coordinates()
        rows.append({family: float((coordinates[indices, 2] - floor_z).min())
                     for family, indices in family_vertices.items()})
    return rows


def smooth_required(values):
    deficits = np.maximum(0.0, target_clearance - np.asarray(values))
    # A short maximum envelope keeps the correction continuous around threshold
    # crossings while retaining a conservative floor gate.
    padded = np.pad(deficits, (2, 2), mode="edge")
    envelope = np.asarray([padded[index:index + 5].max()
                           for index in range(len(deficits))])
    return envelope * 1.8


def location_curve(bone_name, component):
    path = rig.pose.bones[bone_name].path_from_id("location")
    matches = [curve for curve in curves
               if curve.data_path == path and curve.array_index == component]
    assert len(matches) == 1, (bone_name, component, len(matches))
    curve = matches[0]
    assert len(curve.keyframe_points) == 357, (bone_name, component, len(curve.keyframe_points))
    expected = [index / 4.0 for index in range(4, 361)]
    assert all(abs(key.co.x - frame) < 1e-6
               for key, frame in zip(curve.keyframe_points, expected))
    return curve


def apply_world_lifts(lifts):
    armature_world = rig.matrix_world.copy()
    armature_inverse = armature_world.inverted()
    captured = {bone: [] for bone in modified_bones}
    visibility = [(obj, obj.hide_viewport) for obj in scene.objects
                  if obj.type in {"MESH", "CURVES"}]
    for obj, _hidden in visibility:
        obj.hide_viewport = True
    for sample_index, quarter_index in enumerate(range(4, 4 * end + 1)):
        frame = quarter_index / 4.0
        scene.frame_set(int(frame), subframe=frame % 1.0)
        bpy.context.view_layer.update()
        for family in selected_families:
            requested = float(lifts[family][sample_index])
            bones = families[family]
            last = len(bones) - 1
            previous = 0.0
            for depth, bone_name in enumerate(bones):
                if depth <= 2:
                    continue
                t = (depth - 2) / (last - 2)
                cumulative = requested * t * t * (3.0 - 2.0 * t)
                increment = cumulative - previous
                previous = cumulative
                pose = rig.pose.bones[bone_name]
                if increment:
                    world = armature_world @ pose.matrix
                    world.translation.z += increment
                    pose.matrix = armature_inverse @ world
                    bpy.context.view_layer.update()
            for bone_name in bones[3:]:
                captured[bone_name].append(tuple(rig.pose.bones[bone_name].location))
        for bone_name in modified_bones:
            if bone_name not in captured or len(captured[bone_name]) <= sample_index:
                captured[bone_name].append(tuple(rig.pose.bones[bone_name].location))
    for bone_name, values in captured.items():
        assert len(values) == 357, (bone_name, len(values))
        for component in range(3):
            curve = location_curve(bone_name, component)
            for key, value in zip(curve.keyframe_points, values):
                key.co.y = value[component]
                key.handle_left_type = "AUTO_CLAMPED"
                key.handle_right_type = "AUTO_CLAMPED"
            curve.update()
    for obj, hidden in visibility:
        obj.hide_viewport = hidden


passes = []
rows = measure()
for pass_index in range(1, max_passes + 1):
    minima = {family: min(row[family] for row in rows) for family in families}
    global_minimum = min(minima.values())
    passes.append({"pass": pass_index - 1, "family_minimum_clearance_m": minima,
                   "global_minimum_clearance_m": global_minimum})
    print("XSLASH CLOTH FIX MEASURE", pass_index - 1,
          json.dumps(minima, sort_keys=True), flush=True)
    if global_minimum >= required_clearance:
        break
    lifts = {family: smooth_required([row[family] for row in rows])
             for family in selected_families}
    apply_world_lifts(lifts)
    rows = measure()
else:
    raise AssertionError(f"cloth floor gate did not converge: {global_minimum}")

final_minima = {family: min(row[family] for row in rows) for family in families}
final_global_minimum = min(final_minima.values())
assert final_global_minimum >= required_clearance
assert curve_digest(modified_bones) == noncloth_digest_before
rest_digest_after = hashlib.sha256("".join(
    f"{bone.name}:{tuple(value for row in bone.matrix_local for value in row)}:{bone.parent.name if bone.parent else ''};"
    for bone in rig.data.bones).encode()).hexdigest()
assert rest_digest_after == rest_digest_before

scene["astra_rehost_xslash_cloth_floor_fix"] = json.dumps({
    "required_clearance_m": required_clearance,
    "target_clearance_m": target_clearance,
    "modified_bones": modified_bones,
    "source_sha256": source_sha256,
})
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
destination.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(destination))
output_sha256 = sha256(destination)
report = {
    "source": str(source),
    "source_sha256": source_sha256,
    "output": str(destination),
    "output_sha256": output_sha256,
    "action": action.name,
    "frame_range": [1, end],
    "sample_step_frames": 0.25,
    "required_clearance_m": required_clearance,
    "target_clearance_m": target_clearance,
    "selected_families": selected_families,
    "modified_bones": modified_bones,
    "untouched_channels": "every curve except location on the listed distal robe/cape bones",
    "noncloth_action_digest_before": noncloth_digest_before,
    "noncloth_action_digest_after": curve_digest(modified_bones),
    "all_action_digest_before": all_curve_digest_before,
    "all_action_digest_after": curve_digest(),
    "rest_digest_before": rest_digest_before,
    "rest_digest_after": rest_digest_after,
    "before_minimum_clearance_m": before["minimum_clearance_m"],
    "before_worst_frame": before["worst_frame"],
    "after_minimum_clearance_m": final_global_minimum,
    "family_minimum_clearance_m": final_minima,
    "passes": passes,
    "method": "quarter-frame evaluated-surface deficits; short conservative envelope; progressively distributed world-Z gathering over distal chain links 03 through tip; no scale or rest edit",
}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2) + "\n")
print("XSLASH CLOTH FIX COMPLETE", json.dumps({
    "output": str(destination), "output_sha256": output_sha256,
    "after_minimum_clearance_m": final_global_minimum,
    "modified_bones": modified_bones,
}), flush=True)
