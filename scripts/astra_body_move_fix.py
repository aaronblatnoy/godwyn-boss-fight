"""Quarter-frame sole alignment and distal cloth gathering for body i02 moves."""
import bpy
import json
import numpy as np
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/rehost_body_i02"
MODELS = {
    "idle_guard": ROOT / "models/astra_move_idle_guard_body_i02.blend",
    "walk_stalk": ROOT / "models/astra_move_walk_stalk_body_i02.blend",
    "lunge_thrust": ROOT / "models/astra_move_lunge_thrust_body_i02.blend",
    "rising_spin": ROOT / "models/astra_move_rising_spin_body_i02.blend",
    "xslash": ROOT / "models/astra_xslash_body_i02.blend",
}
SOLE_TARGET = 0.0005
CLOTH_TARGET = 0.0025
CLOTH_GATE = 0.002


def original_name(name):
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else name


def curves(action):
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


def location_curve(all_curves, pose, component, sample_frames):
    path = pose.path_from_id("location")
    matches = [curve for curve in all_curves if curve.data_path == path and curve.array_index == component]
    assert len(matches) == 1, (pose.name, component, len(matches))
    curve = matches[0]
    authored = [key.co.x for key in curve.keyframe_points]
    assert all(any(abs(frame - key_frame) < 1e-6 for key_frame in authored) for frame in sample_frames)
    return curve


def evaluated_coords(body):
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    evaluated.to_mesh_clear()
    return coords


def selections(scene, body, rig):
    stage = next(obj for obj in scene.objects if original_name(obj.name) in {"Astra_Move_Stage", "Astra_Stage"})
    floor = max((stage.matrix_world @ vertex.co).z for vertex in stage.data.vertices)
    names = {group.index: group.name for group in body.vertex_groups}
    soles = {}
    for side in ("Left", "Right"):
        allowed = {side + "Foot", side + "ToeBase"}
        soles[side] = np.asarray([vertex.index for vertex in body.data.vertices
                                  if (body.matrix_world @ vertex.co).z < 0.24
                                  and sum(item.weight for item in vertex.groups
                                          if names[item.group] in allowed) > 0.55], dtype=np.int32)
    families = defaultdict(lambda: {"bones": [], "vertices": []})
    for pose in rig.pose.bones:
        if pose.name.startswith(("phys_robe", "phys_cape")):
            families[pose.name.rsplit("_", 1)[0]]["bones"].append(pose.name)
    for vertex in body.data.vertices:
        if (body.matrix_world @ vertex.co).z > 0.48:
            continue
        totals = defaultdict(float)
        for item in vertex.groups:
            family = names[item.group].rsplit("_", 1)[0]
            if family in families:
                totals[family] += item.weight
        if totals:
            family, weight = max(totals.items(), key=lambda pair: pair[1])
            if weight > 0.35:
                families[family]["vertices"].append(vertex.index)
    families = {name: {"bones": sorted(data["bones"]),
                       "vertices": np.asarray(data["vertices"], dtype=np.int32)}
                for name, data in families.items() if len(data["vertices"]) > 10}
    assert all(len(indices) for indices in soles.values()) and families
    return floor, soles, families


def measure(scene, body, floor, soles, families, sample_frames):
    sole_rows = []
    cloth_rows = []
    for index, frame in enumerate(sample_frames):
        scene.frame_set(int(frame), subframe=frame % 1.0)
        bpy.context.view_layer.update()
        coords = evaluated_coords(body)
        sole_rows.append({side: float(coords[ids, 2].min() - floor) for side, ids in soles.items()})
        cloth_rows.append({family: float(coords[data["vertices"], 2].min() - floor)
                           for family, data in families.items()})
        if (index + 1) % 60 == 0:
            print("BODY_MOVE_FIX_MEASURE", frame, flush=True)
    return sole_rows, cloth_rows


def smooth_deficit(values, target, factor=1.0):
    deficit = np.maximum(0.0, target - np.asarray(values))
    padded = np.pad(deficit, (2, 2), mode="edge")
    envelope = np.asarray([padded[index:index + 5].max() for index in range(len(deficit))])
    return envelope * factor


def rewrite_locations(all_curves, rig, captured, sample_frames):
    for bone_name, values in captured.items():
        pose = rig.pose.bones[bone_name]
        for component in range(3):
            curve = location_curve(all_curves, pose, component, sample_frames)
            for key in curve.keyframe_points:
                if key.co.x > sample_frames[-1] + 1e-6:
                    value = values[0]  # loop closure endpoint
                else:
                    sample_index = int(round((key.co.x - sample_frames[0]) * 4))
                    sample_index = max(0, min(len(values) - 1, sample_index))
                    value = values[sample_index]
                key.co.y = value[component]
                key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"
            curve.update()


def apply_root_lift(scene, rig, lifts, sample_frames, all_curves):
    armature_world = rig.matrix_world.copy()
    armature_inverse = armature_world.inverted()
    pose = rig.pose.bones["Hips"]
    values = []
    for frame, lift in zip(sample_frames, lifts):
        scene.frame_set(int(frame), subframe=frame % 1.0)
        bpy.context.view_layer.update()
        world = armature_world @ pose.matrix
        world.translation.z += float(lift)
        pose.matrix = armature_inverse @ world
        bpy.context.view_layer.update()
        values.append(tuple(pose.location))
    rewrite_locations(all_curves, rig, {"Hips": values}, sample_frames)


def apply_cloth_lifts(scene, rig, families, requested, sample_frames, all_curves):
    armature_world = rig.matrix_world.copy()
    armature_inverse = armature_world.inverted()
    modified = sorted({bone for family in requested for bone in families[family]["bones"][3:]})
    captured = {bone: [] for bone in modified}
    for sample_index, frame in enumerate(sample_frames):
        scene.frame_set(int(frame), subframe=frame % 1.0)
        bpy.context.view_layer.update()
        for family, lifts in requested.items():
            bones = families[family]["bones"]
            lift = float(lifts[sample_index])
            last = len(bones) - 1
            previous = 0.0
            for depth, bone_name in enumerate(bones):
                if depth <= 2:
                    continue
                amount = (depth - 2) / max(last - 2, 1)
                cumulative = lift * amount * amount * (3.0 - 2.0 * amount)
                increment = cumulative - previous
                previous = cumulative
                pose = rig.pose.bones[bone_name]
                if increment:
                    world = armature_world @ pose.matrix
                    world.translation.z += increment
                    pose.matrix = armature_inverse @ world
                    bpy.context.view_layer.update()
        for bone_name in modified:
            captured[bone_name].append(tuple(rig.pose.bones[bone_name].location))
    rewrite_locations(all_curves, rig, captured, sample_frames)
    return modified


def fix(name, model):
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    rig = bpy.data.objects["Armature"]
    body = bpy.data.objects["char1"]
    action = rig.animation_data.action
    end = scene.frame_end
    sample_frames = [index / 4 for index in range(4, 4 * end + 1)]
    all_curves = curves(action)
    floor, soles, families = selections(scene, body, rig)
    before_sole, before_cloth = measure(scene, body, floor, soles, families, sample_frames)
    sole_values = [min(row.values()) for row in before_sole]
    root_lifts = smooth_deficit(sole_values, SOLE_TARGET, 1.05)
    apply_root_lift(scene, rig, root_lifts, sample_frames, all_curves)
    after_root_sole, after_root_cloth = measure(scene, body, floor, soles, families, sample_frames)
    assert min(min(row.values()) for row in after_root_sole) >= 0.0
    passes = []
    modified_bones = set()
    current_cloth = after_root_cloth
    for pass_index in range(4):
        minima = {family: min(row[family] for row in current_cloth) for family in families}
        global_minimum = min(minima.values())
        passes.append({"pass": pass_index, "global_minimum_m": global_minimum,
                       "family_minimum_m": minima})
        if global_minimum >= CLOTH_GATE:
            break
        selected = {family: smooth_deficit([row[family] for row in current_cloth], CLOTH_TARGET, 1.8)
                    for family, value in minima.items() if value < CLOTH_TARGET}
        modified_bones.update(apply_cloth_lifts(scene, rig, families, selected, sample_frames, all_curves))
        _sole, current_cloth = measure(scene, body, floor, soles, families, sample_frames)
    final_sole, final_cloth = measure(scene, body, floor, soles, families, sample_frames)
    sole_min = min(min(row.values()) for row in final_sole)
    cloth_min = min(min(row.values()) for row in final_cloth)
    assert sole_min >= 0.0 and cloth_min >= CLOTH_GATE, (name, sole_min, cloth_min)
    scene["astra_body_i02_contact_fix"] = json.dumps({"root_lift_max_m": float(root_lifts.max()),
                                                       "modified_phys_bones": sorted(modified_bones)})
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(model))
    report = {
        "name": name, "sample_step_frames": 0.25, "samples": len(sample_frames),
        "before": {"sole_minimum_m": min(sole_values),
                   "cloth_minimum_m": min(min(row.values()) for row in before_cloth)},
        "root": {"maximum_lift_m": float(root_lifts.max()),
                 "post_root_sole_minimum_m": min(min(row.values()) for row in after_root_sole)},
        "cloth": {"target_m": CLOTH_TARGET, "gate_m": CLOTH_GATE, "passes": passes,
                  "modified_bones": sorted(modified_bones), "final_minimum_m": cloth_min},
        "final": {"sole_minimum_m": sole_min, "cloth_minimum_m": cloth_min,
                  "sole_gate_pass": sole_min >= 0.0, "cloth_gate_pass": cloth_min >= CLOTH_GATE},
    }
    (OUT / f"{name}_contact_fix.json").write_text(json.dumps(report, indent=2) + "\n")
    print("BODY_MOVE_FIX_PASS", name, json.dumps(report["final"]), flush=True)
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reports = {name: fix(name, model) for name, model in MODELS.items()}
    (OUT / "meshy_body_contact_fixes.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
