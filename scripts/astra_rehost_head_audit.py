"""Audit published head/groom binding, blade clearance, and gorget collisions."""
import bpy
import json
import math
import numpy as np
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
name, model, out_dir = args[0], Path(args[1]), Path(args[2])
out_dir.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(model))
scene = bpy.context.scene
rig = bpy.data.objects["Armature"]
sword = bpy.data.objects["Godwyn_Sword"]
head = bpy.data.objects["AstraChar2_Mpfb_Head"]
collars = [bpy.data.objects["AstraChar2_R5_Gorget"], bpy.data.objects["AstraChar2_R5_GorgetRim"]]
brows = [bpy.data.objects["AstraChar2_Eyebrows_L"], bpy.data.objects["AstraChar2_Eyebrows_R"]]
controls = sorted((o for o in scene.objects if o.name.startswith("AstraChar2_R5_Control_MPFB_")), key=lambda o: o.name)
curves = sorted((o for o in scene.objects if o.name.startswith("AstraChar2_R5_Curves_MPFB_")), key=lambda o: o.name)
strands = sorted((o for o in scene.objects if o.name.startswith("AstraChar2_R5_Strands_MPFB_")), key=lambda o: o.name)
assert len(controls) == len(curves) == len(strands) == 9


def armature_ok(obj):
    mods = [m for m in obj.modifiers if m.type == "ARMATURE"]
    return obj.parent == rig and len(mods) == 1 and mods[0].object == rig


def weights(obj, collect_samples=False):
    names = {g.index: g.name for g in obj.vertex_groups}
    unweighted = bad_sum = 0
    max_error = 0.0
    used = set()
    samples = []
    stride = max(1, len(obj.data.vertices) // 2500)
    for vertex in obj.data.vertices:
        total = sum(g.weight for g in vertex.groups)
        if not vertex.groups:
            unweighted += 1
        if abs(total - 1.0) > 2e-3:
            bad_sum += 1
        max_error = max(max_error, abs(total - 1.0))
        used.update(names[g.group] for g in vertex.groups if g.weight > 1e-6)
        if collect_samples and vertex.index % stride == 0:
            samples.append((obj, vertex.index, vertex.co.copy(),
                            [(names[g.group], g.weight) for g in vertex.groups
                             if names[g.group] in rig.pose.bones and g.weight > 1e-6]))
    return {"vertices": len(obj.data.vertices), "unweighted": unweighted,
            "bad_weight_sum": bad_sum, "max_weight_sum_error": max_error,
            "used_bones": sorted(used)}, samples


binding = {"brows": {}, "hair_controls": {}, "portable_strands": {}, "native_curves": {}}
hair_samples = []
for obj in brows:
    stats, _ = weights(obj)
    stats["armature_binding_ok"] = armature_ok(obj)
    binding["brows"][obj.name] = stats
for obj in controls:
    stats, samples = weights(obj, True)
    stats["armature_binding_ok"] = armature_ok(obj)
    binding["hair_controls"][obj.name] = stats
    hair_samples.extend(samples)
for obj in strands:
    binding["portable_strands"][obj.name] = {
        "vertices": len(obj.data.vertices), "armature_binding_ok": armature_ok(obj),
        "hidden_in_native_render": bool(obj.hide_render),
    }
for obj in curves:
    binding["native_curves"][obj.name] = {
        "visible_in_native_render": not obj.hide_render,
        "geometry_nodes_modifiers": sum(m.type == "NODES" for m in obj.modifiers),
        "parent_is_armature": obj.parent == rig,
    }
assert all(x["armature_binding_ok"] and not x["unweighted"] and not x["bad_weight_sum"]
           for section in [binding["brows"], binding["hair_controls"]]
           for x in section.values())
assert all(x["armature_binding_ok"] for x in binding["portable_strands"].values())
assert all(x["visible_in_native_render"] and x["geometry_nodes_modifiers"] == 1
           for x in binding["native_curves"].values())


def evaluated_world(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    matrix = np.array(evaluated.matrix_world)
    co = co @ matrix[:3, :3].T + matrix[:3, 3]
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return co, polygons


def make_bvh(co, polygons):
    return BVHTree.FromPolygons([tuple(x) for x in co], polygons, all_triangles=False)


def segment_distance(points, a, b):
    axis = b - a
    rel = points - a
    u = np.clip(rel @ axis / max(float(axis @ axis), 1e-12), 0.0, 1.0)
    return np.linalg.norm(rel - u[:, None] * axis, axis=1)


# Sword dimensions and rigid landmarks match the original grip audit.
src = np.array([p.vector[:] for p in sword.data.attributes["astra_sword_source"].data])
local = np.array([v.co[:] for v in sword.data.vertices])
fit = np.linalg.lstsq(np.column_stack((src, np.ones(len(src)))), local, rcond=None)[0]
tip_index = int(src[:, 2].argmin())
tip_local = sword.data.vertices[tip_index].co.copy()
grip_local = Vector(np.array([61.2, -66.3, 167, 1]) @ fit)
blade_ids = np.where(src[:, 2] < 150)[0]
radius_ids = np.where((src[:, 2] > 30) & (src[:, 2] < 145))[0]
rest_grip_world = np.array(sword.matrix_world @ grip_local)
rest_tip_world = np.array(sword.matrix_world @ tip_local)
rest_blade_world = np.array([sword.matrix_world @ Vector(local[i]) for i in radius_ids])
axis_world = rest_tip_world - rest_grip_world
rel = rest_blade_world - rest_grip_world
u = np.clip(rel @ axis_world / (axis_world @ axis_world), 0.0, 1.0)
blade_radius = float(np.quantile(np.linalg.norm(rel - u[:, None] * axis_world, axis=1), .99))
bind = (rig.data.bones["RightHand"].matrix_local.inverted() @
        rig.matrix_world.inverted() @ sword.matrix_world)


def blade_points():
    deform = rig.matrix_world @ rig.pose.bones["RightHand"].matrix @ bind
    return np.array(deform @ grip_local), np.array(deform @ tip_local)


def analytic_hair_points():
    points = []
    for obj, _index, co, influences in hair_samples:
        p = np.zeros(3)
        total = 0.0
        for bone_name, weight in influences:
            transform = (rig.matrix_world @ rig.pose.bones[bone_name].matrix @
                         rig.data.bones[bone_name].matrix_local.inverted() @
                         rig.matrix_world.inverted() @ obj.matrix_world)
            p += weight * np.array(transform @ co)
            total += weight
        if total > 0:
            points.append(p / total)
    return np.array(points)


frames = range(1, scene.frame_end + 1)
rows = []
exact_blade = name in {"rising_spin", "xslash"}
for frame in frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    head_co, head_poly = evaluated_world(head, dg)
    head_bvh = make_bvh(head_co, head_poly)
    collar_parts = [evaluated_world(o, dg) for o in collars]
    collar_co = []
    collar_poly = []
    offset = 0
    for co, poly in collar_parts:
        collar_co.extend(co)
        collar_poly.extend(tuple(i + offset for i in face) for face in poly)
        offset += len(co)
    collar_co = np.asarray(collar_co)
    collar_bvh = make_bvh(collar_co, collar_poly)
    overlap_pairs = head_bvh.overlap(collar_bvh)
    collar_top = float(collar_co[:, 2].max())
    # The published graft deliberately inserts the hidden base of the neck
    # inside the gorget. Classify that seam separately from exposed jaw/neck.
    exposed_pairs = []
    for head_face, collar_face in overlap_pairs:
        face_z = head_co[list(head_poly[head_face]), 2]
        if float(face_z.min()) > collar_top - .002:
            exposed_pairs.append((head_face, collar_face))
    exposed_head = head_co[head_co[:, 2] > collar_top + .003]
    clearance = min((collar_bvh.find_nearest(Vector(p))[3]
                     for p in exposed_head[::8]), default=math.inf)
    if exposed_pairs:
        clearance = 0.0
    grip, tip = blade_points()
    head_centerline = float(segment_distance(head_co, grip, tip).min())
    hair_points = analytic_hair_points()
    hair_centerline = float(segment_distance(hair_points, grip, tip).min())
    exact_overlap = None
    exact_head_distance = None
    exact_hair_distance = None
    if exact_blade:
        sword_co, sword_poly_all = evaluated_world(sword, dg)
        blade_set = set(int(i) for i in blade_ids)
        blade_poly = [face for face in sword_poly_all if all(i in blade_set for i in face)]
        blade_bvh = make_bvh(sword_co, blade_poly)
        exact_overlap = len(head_bvh.overlap(blade_bvh))
        exact_head_distance = min(
            min((head_bvh.find_nearest(Vector(sword_co[i]))[3] for i in blade_ids[::3]), default=math.inf),
            min((blade_bvh.find_nearest(Vector(p))[3] for p in head_co[::12]), default=math.inf),
        )
        if exact_overlap:
            exact_head_distance = 0.0
        exact_hair_distance = min((blade_bvh.find_nearest(Vector(p))[3]
                                   for p in hair_points), default=math.inf) - .002
    rows.append({
        "frame": frame,
        "gorget_head_internal_seam_triangle_overlaps": len(overlap_pairs),
        "gorget_exposed_head_triangle_overlaps": len(exposed_pairs),
        "gorget_exposed_head_min_sampled_distance_m": float(clearance),
        "blade_head_centerline_vertex_min_m": head_centerline,
        "blade_head_surface_clearance_proxy_m": head_centerline - blade_radius,
        "blade_hair_sample_centerline_min_m": hair_centerline,
        "blade_hair_clearance_proxy_m": hair_centerline - blade_radius - .002,
        "blade_head_exact_triangle_overlaps": exact_overlap,
        "blade_head_exact_sampled_surface_distance_m": exact_head_distance,
        "blade_hair_exact_sampled_surface_clearance_m": exact_hair_distance,
    })
    if frame % 10 == 0:
        print("HEAD AUDIT", name, frame, flush=True)

summary = {
    "name": name,
    "frames_checked": scene.frame_end,
    "binding": binding,
    "hair_control_points_sampled_per_frame": len(hair_samples),
    "blade_radius_99pct_m": blade_radius,
    "gorget_head": {
        "internal_neck_insertion_frames": [r["frame"] for r in rows if r["gorget_head_internal_seam_triangle_overlaps"]],
        "exposed_intersection_frames": [r["frame"] for r in rows if r["gorget_exposed_head_triangle_overlaps"]],
        "minimum_exposed_sampled_distance_m": min(r["gorget_exposed_head_min_sampled_distance_m"] for r in rows),
        "worst_frame": min(rows, key=lambda r: r["gorget_exposed_head_min_sampled_distance_m"])["frame"],
        "classification": "hidden published neck insertion below the gorget lip is reported separately; exposed jaw/neck is the acceptance surface",
    },
    "blade_head": {
        "minimum_clearance_proxy_m": min(r["blade_head_surface_clearance_proxy_m"] for r in rows),
        "worst_frame": min(rows, key=lambda r: r["blade_head_surface_clearance_proxy_m"])["frame"],
        "exact_intersection_frames": [r["frame"] for r in rows if r["blade_head_exact_triangle_overlaps"]],
        "exact_minimum_sampled_surface_distance_m": min((r["blade_head_exact_sampled_surface_distance_m"] for r in rows if r["blade_head_exact_sampled_surface_distance_m"] is not None), default=None),
    },
    "blade_hair": {
        "minimum_sampled_clearance_proxy_m": min(r["blade_hair_clearance_proxy_m"] for r in rows),
        "worst_frame": min(rows, key=lambda r: r["blade_hair_clearance_proxy_m"])["frame"],
        "fiber_radius_assumption_m": .002,
        "exact_minimum_sampled_surface_clearance_m": min((r["blade_hair_exact_sampled_surface_clearance_m"] for r in rows if r["blade_hair_exact_sampled_surface_clearance_m"] is not None), default=None),
        "exact_worst_frame": min((r for r in rows if r["blade_hair_exact_sampled_surface_clearance_m"] is not None), key=lambda r: r["blade_hair_exact_sampled_surface_clearance_m"], default={"frame": None})["frame"],
    },
    "rows": rows,
}
(out_dir / "head_hair_collar_verification.json").write_text(json.dumps(summary, indent=2) + "\n")
assert not summary["gorget_head"]["exposed_intersection_frames"]
assert not summary["blade_head"]["exact_intersection_frames"]
if exact_blade:
    assert summary["blade_head"]["exact_minimum_sampled_surface_distance_m"] > 0
    assert summary["blade_hair"]["exact_minimum_sampled_surface_clearance_m"] > 0
else:
    assert summary["blade_head"]["minimum_clearance_proxy_m"] > 0
    assert summary["blade_hair"]["minimum_sampled_clearance_proxy_m"] > 0
print("HEAD AUDIT COMPLETE", name, json.dumps({k: v for k, v in summary.items() if k not in {"binding", "rows"}}), flush=True)
