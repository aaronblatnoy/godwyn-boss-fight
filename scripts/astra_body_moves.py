"""Rehost all five finished moves onto body i02 and run delivery audits."""
import bpy
import hashlib
import json
import math
import numpy as np
from collections import defaultdict
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "models/astra_character_v2_body_i02.blend"
OUT = ROOT / "renders/astra/rehost_body_i02"
JOBS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_v2_wip.blend",
                   ROOT / "models/astra_move_idle_guard_body_i02.blend", 48),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_v2_wip.blend",
                   ROOT / "models/astra_move_walk_stalk_body_i02.blend", 36),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_v2_wip.blend",
                     ROOT / "models/astra_move_lunge_thrust_body_i02.blend", 40),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_v2_wip.blend",
                    ROOT / "models/astra_move_rising_spin_body_i02.blend", 40),
    "xslash": (ROOT / "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
               ROOT / "models/astra_xslash_body_i02.blend", 55),
}


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def original_name(name):
    stem, dot, suffix = name.rpartition(".")
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else name


def action_digest(action):
    digest = hashlib.sha256()
    curves = [curve for layer in action.layers for strip in layer.strips
              for bag in strip.channelbags for curve in bag.fcurves]
    for curve in sorted(curves, key=lambda item: (item.data_path, item.array_index)):
        digest.update(f"{curve.data_path}|{curve.array_index}|".encode())
        for key in curve.keyframe_points:
            digest.update(("%.9g,%.9g,%s;" % (key.co.x, key.co.y, key.interpolation)).encode())
    return digest.hexdigest(), len(curves), sum(len(curve.keyframe_points) for curve in curves)


def rehost(name, source, target):
    base_hash = sha256(BASE)
    source_hash = sha256(source)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    character_scene = bpy.context.scene
    character_objects = [obj for obj in character_scene.objects if obj.type not in {"LIGHT", "CAMERA"}
                         and obj.name != "Astra evaluation ground"]
    rig = bpy.data.objects["Armature"]
    with bpy.data.libraries.load(str(source), link=False) as (available, requested):
        assert len(available.scenes) == 1
        requested.scenes = available.scenes[:]
    move_scene = requested.scenes[0]
    bpy.context.window.scene = move_scene
    appended = set(move_scene.objects)
    old_rig = next(obj for obj in appended if obj.type == "ARMATURE")
    source_action = old_rig.animation_data.action
    source_digest, curves, keys = action_digest(source_action)
    for obj in character_objects:
        move_scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    assert len(old_rig.data.bones) == len(rig.data.bones) == 121
    rest_error = max(abs(old_rig.data.bones[bone.name].matrix_local[i][j]
                         - rig.data.bones[bone.name].matrix_local[i][j])
                     for bone in rig.data.bones for i in range(4) for j in range(4))
    assert rest_error == 0.0
    for pose in old_rig.pose.bones:
        other = rig.pose.bones[pose.name]
        other.rotation_mode = pose.rotation_mode
        other.scale = pose.scale
    rig.animation_data_clear()
    rig.animation_data_create()
    transferred = source_action.copy()
    transferred.name = source_action.name + "_BodyI02"
    rig.animation_data.action = transferred
    if transferred.slots:
        rig.animation_data.action_slot = transferred.slots[0]
    assert action_digest(transferred) == (source_digest, curves, keys)
    old_character = {old_rig}
    for obj in appended:
        if obj == old_rig:
            continue
        armature_target = any(modifier.type == "ARMATURE" and modifier.object == old_rig
                              for modifier in obj.modifiers)
        if obj.parent == old_rig or armature_target:
            old_character.add(obj)
    for obj in old_character:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(character_scene)
    move_scene.name = "Astra Body i02 " + name
    move_scene.render.fps = 30
    move_scene["astra_body_i02_rehost"] = name
    move_scene["astra_body_i02_base_sha256"] = base_hash
    move_scene["astra_body_i02_action_source_sha256"] = source_hash
    move_scene["astra_body_i02_action_digest"] = source_digest
    move_scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    assert sha256(BASE) == base_hash and sha256(source) == source_hash
    return move_scene, rig, {
        "name": name, "source": str(source.relative_to(ROOT)), "source_sha256": source_hash,
        "output": str(target.relative_to(ROOT)), "output_sha256": sha256(target),
        "base_sha256": base_hash, "bones": len(rig.data.bones), "rest_matrix_error": rest_error,
        "action_digest": source_digest, "action_fcurves": curves, "action_keys": keys,
        "action_data_identical": True, "frame_range": [move_scene.frame_start, move_scene.frame_end],
    }


def evaluated_world(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    evaluated.to_mesh_clear()
    return coords, polygons


def surface_audit(name, scene, body, rig):
    stage = next(obj for obj in scene.objects if original_name(obj.name) in {"Astra_Move_Stage", "Astra_Stage"})
    floor = max((stage.matrix_world @ vertex.co).z for vertex in stage.data.vertices)
    group_names = {group.index: group.name for group in body.vertex_groups}
    soles = {}
    for side in ("Left", "Right"):
        allowed = {side + "Foot", side + "ToeBase"}
        soles[side] = [vertex.index for vertex in body.data.vertices
                       if (body.matrix_world @ vertex.co).z < 0.24
                       and sum(item.weight for item in vertex.groups
                               if group_names[item.group] in allowed) > 0.55]
    family_names = {bone.name.rsplit("_", 1)[0] for bone in rig.pose.bones
                    if bone.name.startswith(("phys_robe", "phys_cape"))}
    family_vertices = defaultdict(list)
    for vertex in body.data.vertices:
        if (body.matrix_world @ vertex.co).z > 0.48:
            continue
        totals = defaultdict(float)
        for item in vertex.groups:
            family = group_names[item.group].rsplit("_", 1)[0]
            if family in family_names:
                totals[family] += item.weight
        if totals:
            family, weight = max(totals.items(), key=lambda pair: pair[1])
            if weight > 0.35:
                family_vertices[family].append(vertex.index)
    family_vertices = {name: np.asarray(indices, dtype=np.int32)
                       for name, indices in family_vertices.items() if len(indices) > 10}
    assert all(soles.values()) and family_vertices
    quarter = name == "xslash"
    samples = [index / 4 for index in range(4, 4 * scene.frame_end + 1)] if quarter else list(range(1, scene.frame_end + 1))
    rows = []
    for sample in samples:
        scene.frame_set(int(sample), subframe=sample % 1.0)
        bpy.context.view_layer.update()
        coords, _polygons = evaluated_world(body)
        sole = {side: float(coords[indices, 2].min() - floor) for side, indices in soles.items()}
        cloth = {family: float(coords[indices, 2].min() - floor)
                 for family, indices in family_vertices.items()}
        rows.append({"frame": sample, "sole": sole, "cloth": cloth})
        if len(rows) % 40 == 0:
            print("BODY_MOVE_SURFACE", name, sample, flush=True)
    sole_min = min(value for row in rows for value in row["sole"].values())
    cloth_min = min(value for row in rows for value in row["cloth"].values())
    return {"floor_z_m": floor, "sample_step_frames": 0.25 if quarter else 1.0,
            "samples": len(rows), "sole_vertex_counts": {k: len(v) for k, v in soles.items()},
            "cloth_family_vertex_counts": {k: len(v) for k, v in family_vertices.items()},
            "sole_minimum_clearance_m": sole_min,
            "sole_worst_frame": min(rows, key=lambda row: min(row["sole"].values()))["frame"],
            "cloth_minimum_clearance_m": cloth_min,
            "cloth_worst_frame": min(rows, key=lambda row: min(row["cloth"].values()))["frame"],
            "sole_gate_pass": sole_min >= 0.0, "cloth_gate_m": 0.002,
            "cloth_gate_pass": cloth_min >= 0.002, "rows": rows}


def grip_audit(scene, rig, sword):
    assert sword.parent == rig and sword.parent_type == "OBJECT"
    assert list(sword.vertex_groups.keys()) == ["RightHand"]
    assert all(len(vertex.groups) == 1 and abs(vertex.groups[0].weight - 1.0) < 1e-7
               for vertex in sword.data.vertices)
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    local = np.asarray([vertex.co[:] for vertex in sword.data.vertices])
    fit = np.linalg.lstsq(np.column_stack((source, np.ones(len(source)))), local, rcond=None)[0]
    grip = Vector(np.array([61.2, -66.3, 167, 1]) @ fit)
    armature_world = rig.matrix_world
    bind = (rig.data.bones["RightHand"].matrix_local.inverted() @ armature_world.inverted()
            @ sword.matrix_world)
    reference = bind @ grip
    errors = []
    for quarter in range(4, 4 * scene.frame_end + 1):
        frame = quarter / 4
        scene.frame_set(int(frame), subframe=frame % 1.0)
        bpy.context.view_layer.update()
        hand = armature_world @ rig.pose.bones["RightHand"].matrix
        world_grip = hand @ bind @ grip
        errors.append((hand.inverted() @ world_grip - reference).length * 0.01)
    maximum = max(errors)
    return {"binding": "RightHand-only rigid sword", "quarter_samples": len(errors),
            "max_hand_local_hilt_drift_m": maximum, "gate_m": 0.00001,
            "gate_pass": maximum < 0.00001}


def bvh(coords, polygons):
    return BVHTree.FromPolygons([tuple(point) for point in coords], polygons, all_triangles=False)


def collision_audit(name, scene, sword, head_hair, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    sword_coords, sword_polygons = evaluated_world(sword)
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    blade_ids = set(int(index) for index in np.where(source[:, 2] < 150)[0])
    blade_polygons = [face for face in sword_polygons if all(index in blade_ids for index in face)]
    blade_tree = bvh(sword_coords, blade_polygons)
    head_coords, all_polygons = evaluated_world(head_hair)
    hair_attribute = head_hair.data.color_attributes["meshy_hair_mask"]
    hair_flags = [np.mean([hair_attribute.data[index].color[0] for index in polygon.loop_indices]) >= 0.5
                  for polygon in head_hair.data.polygons]
    head_polygons = [face for face, hair in zip(all_polygons, hair_flags) if not hair]
    hair_polygons = [face for face, hair in zip(all_polygons, hair_flags) if hair]
    head_tree = bvh(head_coords, head_polygons)
    hair_tree = bvh(head_coords, hair_polygons)
    head_overlap = len(blade_tree.overlap(head_tree))
    hair_overlap = len(blade_tree.overlap(hair_tree))
    blade_sample = sword_coords[sorted(blade_ids)[::3]]
    head_distance = min((head_tree.find_nearest(Vector(point))[3] for point in blade_sample), default=math.inf)
    hair_distance = min((hair_tree.find_nearest(Vector(point))[3] for point in blade_sample), default=math.inf)
    if head_overlap:
        head_distance = 0.0
    if hair_overlap:
        hair_distance = 0.0
    return {"move": name, "frame": frame, "blade_head_triangle_overlaps": head_overlap,
            "blade_hair_triangle_overlaps": hair_overlap,
            "blade_head_sampled_distance_m": float(head_distance),
            "blade_hair_sampled_distance_m": float(hair_distance),
            "gate_pass": head_overlap == 0 and hair_overlap == 0}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base_hash = sha256(BASE)
    results = {}
    for name, (source, target, extended_frame) in JOBS.items():
        scene, rig, transfer = rehost(name, source, target)
        body = bpy.data.objects["char1"]
        sword = bpy.data.objects["Godwyn_Sword"]
        surface = surface_audit(name, scene, body, rig)
        grip = grip_audit(scene, rig, sword)
        collision = None
        if name in {"rising_spin", "xslash"}:
            collision = collision_audit(name, scene, sword, bpy.data.objects["AstraChar2_Meshy_HeadHair"], extended_frame)
        results[name] = {"transfer": transfer, "surface": surface, "grip": grip,
                         "collision": collision, "most_extended_frame": extended_frame}
        (OUT / f"{name}_audit.json").write_text(json.dumps(results[name], indent=2) + "\n")
        print("BODY_MOVE_AUDIT", name, json.dumps({"sole": surface["sole_minimum_clearance_m"],
              "cloth": surface["cloth_minimum_clearance_m"], "grip": grip["max_hand_local_hilt_drift_m"],
              "collision": collision}), flush=True)
    summary = {
        "candidate": str(BASE.relative_to(ROOT)), "candidate_sha256": base_hash,
        "moves": results,
        "all_transfer_gates_pass": all(row["transfer"]["bones"] == 121
                                        and row["transfer"]["rest_matrix_error"] == 0.0
                                        and row["transfer"]["action_data_identical"] for row in results.values()),
        "all_grip_gates_pass": all(row["grip"]["gate_pass"] for row in results.values()),
        "all_sole_gates_pass": all(row["surface"]["sole_gate_pass"] for row in results.values()),
        "all_cloth_gates_pass": all(row["surface"]["cloth_gate_pass"] for row in results.values()),
        "all_collision_gates_pass": all(row["collision"] is None or row["collision"]["gate_pass"]
                                         for row in results.values()),
    }
    summary["all_numeric_gates_pass"] = all(summary[key] for key in (
        "all_transfer_gates_pass", "all_grip_gates_pass", "all_sole_gates_pass",
        "all_cloth_gates_pass", "all_collision_gates_pass"))
    (OUT / "meshy_body_moves_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert sha256(BASE) == base_hash
    print("BODY_MOVES_COMPLETE", json.dumps({key: value for key, value in summary.items()
          if key.startswith("all_")}), flush=True)


if __name__ == "__main__":
    main()
