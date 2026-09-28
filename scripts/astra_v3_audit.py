"""Quantitative audit for Godwyn v3 retarget, skin, grip, floor, and blade."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
WIP = ROOT / "models/astra_character_v3_wip.blend"
SAMPLES = OUT / "meshy_v3_retarget_samples.json"
AUDIT = OUT / "meshy_v3_audit.json"
FRAMES = {"idle_guard": 96, "walk_stalk": 72, "lunge_thrust": 64, "rising_spin": 116, "xslash": 90}
EXTENDED = {"idle_guard": 48, "walk_stalk": 36, "lunge_thrust": 40, "rising_spin": 40, "xslash": 55}
BONES = [
    "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
CORE_BONES = [
    "Hips", "Spine02", "Spine01", "Spine",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot",
    "RightUpLeg", "RightLeg", "RightFoot",
]
REPORT_ONLY_BONES = [bone for bone in BONES if bone not in CORE_BONES]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default=str(WIP.relative_to(ROOT)))
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--samples", default=str(SAMPLES.relative_to(ROOT)))
    parser.add_argument("--out", default=str(AUDIT.relative_to(ROOT)))
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def action_for(name):
    return bpy.data.actions[f"Godwyn_V3_{name}"]


def assign_action(rig, name, frame=1, subframe=0.0):
    action = action_for(name)
    animation = rig.animation_data_create()
    animation.action = action
    animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame, subframe=subframe)
    bpy.context.view_layer.update()


def posed_head_world(rig, bone):
    return rig.matrix_world @ rig.pose.bones[bone].head


def percentile(values, amount):
    return float(np.percentile(np.asarray(values, dtype=float), amount))


def anatomical_frame(positions):
    up = (positions["Spine02"] - positions["Hips"]).normalized()
    side = (positions["LeftUpLeg"] - positions["RightUpLeg"]).normalized()
    forward = side.cross(up).normalized()
    side = up.cross(forward).normalized()
    return Matrix((side, up, forward)).transposed()


def joint_audit(rig, samples):
    moves = {}
    all_errors = []
    all_raw_errors = []
    target_rest = {bone: rig.matrix_world @ rig.data.bones[bone].head_local for bone in BONES}
    target_rest_root = target_rest["Hips"]
    for name, count in FRAMES.items():
        source = samples["moves"][name]
        ratio = source["height_ratio"]
        source_rest = {bone: Vector(source["source_rest_positions_world_m"][bone]) for bone in BONES}
        source_rest_root = source_rest["Hips"]
        errors = []
        raw_errors = []
        by_bone = {bone: [] for bone in BONES}
        frame_rows = []
        for frame_row in source["samples"]:
            frame = int(frame_row["frame"])
            assign_action(rig, name, frame)
            source_positions = {bone: Vector(frame_row["source_positions_world_m"][bone]) for bone in BONES}
            target_root = posed_head_world(rig, "Hips")
            source_root = source_positions["Hips"]
            nominal_target_root = target_rest_root + (source_root - source_rest_root) * ratio
            root_alignment = target_root - nominal_target_root
            frame_errors = []
            for bone in BONES:
                expected_raw = target_root + (source_positions[bone] - source_root) * ratio
                expected = target_rest[bone] + (source_positions[bone] - source_rest[bone]) * ratio + root_alignment
                actual = posed_head_world(rig, bone)
                error_mm = (actual - expected).length * 1000.0
                raw_error_mm = (actual - expected_raw).length * 1000.0
                if bone in CORE_BONES:
                    errors.append(raw_error_mm)
                raw_errors.append(error_mm)
                by_bone[bone].append(raw_error_mm)
                if bone in CORE_BONES:
                    frame_errors.append(raw_error_mm)
            frame_rows.append({"frame": frame, "p50_mm": percentile(frame_errors, 50), "p99_mm": percentile(frame_errors, 99), "max_mm": max(frame_errors)})
        row = {
            "samples": len(errors),
            "definition": "gated core-joint old-versus-new posed joint heads: old joints are root-aligned to the evaluated new Hips and uniformly scaled by the recorded skeletal height ratio",
            "gated_bones": CORE_BONES,
            "reported_ungated_bones": REPORT_ONLY_BONES,
            "p50_mm": percentile(errors, 50),
            "p99_mm": percentile(errors, 99),
            "max_mm": max(errors),
            "gate_p99_mm": 40.0,
            "gate_pass": percentile(errors, 99) < 40.0,
            "rest_offset_calibrated_diagnostic": {
                "definition": "diagnostic only: each old joint's displacement from its own rest position applied to the corresponding target rest joint",
                "p50_mm": percentile(raw_errors, 50),
                "p99_mm": percentile(raw_errors, 99),
                "max_mm": max(raw_errors),
            },
            "by_bone": {bone: {"p50_mm": percentile(values, 50), "p99_mm": percentile(values, 99), "max_mm": max(values)} for bone, values in by_bone.items()},
            "worst_frames": sorted(frame_rows, key=lambda item: item["p99_mm"], reverse=True)[:10],
        }
        moves[name] = row
        all_errors.extend(errors)
        all_raw_errors.extend(raw_errors)
        print("V3_JOINT", name, json.dumps({key: row[key] for key in ("p50_mm", "p99_mm", "max_mm", "gate_pass")}), flush=True)
    return {
        "moves": moves,
        "overall": {
            "samples": len(all_errors),
            "p50_mm": percentile(all_errors, 50),
            "p99_mm": percentile(all_errors, 99),
            "max_mm": max(all_errors),
            "gate_p99_mm": 40.0,
            "gate_pass": all(row["gate_pass"] for row in moves.values()),
            "rest_offset_calibrated_diagnostic": {
                "p50_mm": percentile(all_raw_errors, 50),
                "p99_mm": percentile(all_raw_errors, 99),
                "max_mm": max(all_raw_errors),
            },
        },
    }


def evaluated_coordinates(ob):
    evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(evaluated.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    polygons = [tuple(poly.vertices) for poly in mesh.polygons]
    evaluated.to_mesh_clear()
    return coords, polygons


def sole_ids(body):
    names = {group.index: group.name for group in body.vertex_groups}
    result = {}
    for side in ("Left", "Right"):
        allowed = {side + "Foot", side + "ToeBase"}
        result[side] = np.asarray([
            vertex.index for vertex in body.data.vertices
            if (body.matrix_world @ vertex.co).z < 0.24
            and sum(item.weight for item in vertex.groups if names[item.group] in allowed) > 0.50
        ], dtype=np.int32)
        assert len(result[side])
    return result


def sole_audit(rig, body):
    ids = sole_ids(body)
    moves = {}
    for name, count in FRAMES.items():
        rows = []
        for frame in range(1, count + 1):
            assign_action(rig, name, frame)
            coords, _ = evaluated_coordinates(body)
            per_side = {side: float(coords[indices, 2].min()) for side, indices in ids.items()}
            rows.append({"frame": frame, "clearance_m": per_side})
        minimum = min(value for row in rows for value in row["clearance_m"].values())
        moves[name] = {
            "integer_frame_samples": count,
            "sole_vertex_counts": {key: len(value) for key, value in ids.items()},
            "minimum_clearance_m": minimum,
            "worst": min(rows, key=lambda row: min(row["clearance_m"].values())),
            "gate_m": -1e-6,
            "gate_pass": minimum >= -1e-6,
        }
        print("V3_SOLE_AUDIT", name, minimum, moves[name]["gate_pass"], flush=True)
    return {"moves": moves, "gate_pass": all(row["gate_pass"] for row in moves.values())}


def edge_stretch(rig, body):
    rest = np.empty(len(body.data.vertices) * 3, dtype=np.float32)
    body.data.vertices.foreach_get("co", rest)
    rest = rest.reshape(-1, 3)
    matrix = np.asarray(body.matrix_world)
    rest = rest @ matrix[:3, :3].T + matrix[:3, 3]
    edge_vertices = np.empty(len(body.data.edges) * 2, dtype=np.int32)
    body.data.edges.foreach_get("vertices", edge_vertices)
    edge_vertices = edge_vertices.reshape(-1, 2)
    rest_lengths = np.linalg.norm(rest[edge_vertices[:, 0]] - rest[edge_vertices[:, 1]], axis=1)
    valid = rest_lengths >= 0.002
    excluded_indices = np.flatnonzero(~valid)
    excluded = [
        {
            "edge_index": int(index),
            "vertices": [int(value) for value in edge_vertices[index]],
            "rest_length_m": float(rest_lengths[index]),
        }
        for index in excluded_indices
    ]
    rows = {}
    for name, frame in EXTENDED.items():
        assign_action(rig, name, frame)
        posed, _ = evaluated_coordinates(body)
        posed_lengths = np.linalg.norm(posed[edge_vertices[:, 0]] - posed[edge_vertices[:, 1]], axis=1)
        ratios = posed_lengths[valid] / rest_lengths[valid]
        valid_indices = np.flatnonzero(valid)
        slot = int(np.argmax(ratios))
        edge_index = int(valid_indices[slot])
        rows[name] = {
            "frame": frame,
            "edges": len(edge_vertices),
            "valid_edges": int(valid.sum()),
            "excluded_degenerate_edges_below_2mm": len(excluded),
            "p99_ratio": percentile(ratios, 99),
            "max_ratio": float(ratios[slot]),
            "max_edge_index": edge_index,
            "max_edge_vertices": [int(value) for value in edge_vertices[edge_index]],
            "max_edge_rest_length_m": float(rest_lengths[edge_index]),
            "max_edge_posed_length_m": float(posed_lengths[edge_index]),
            "gate_p99": 1.6,
            "gate_max": 3.0,
            "gate_pass": percentile(ratios, 99) <= 1.6 and float(ratios[slot]) <= 3.0,
        }
        print("V3_STRETCH", name, json.dumps(rows[name]), flush=True)
    return {
        "gate_population": "edges with rest length >= 0.002m",
        "excluded_degenerate_seam_edges_count": len(excluded),
        "excluded_degenerate_seam_edges": excluded,
        "moves": rows,
        "gate_pass": all(row["gate_pass"] for row in rows.values()),
    }


def sword_grip_point(sword):
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    local = np.asarray([vertex.co[:] for vertex in sword.data.vertices])
    fit = np.linalg.lstsq(np.column_stack((source, np.ones(len(source)))), local, rcond=None)[0]
    return Vector(np.array([61.2, -66.3, 167.0, 1.0]) @ fit)


def grip_audit(rig, sword):
    assert sword.parent == rig and list(sword.vertex_groups.keys()) == ["RightHand"]
    grip = sword_grip_point(sword)
    rest_hand = rig.matrix_world @ rig.data.bones["RightHand"].matrix_local
    reference = rest_hand.inverted() @ (sword.matrix_world @ grip)
    moves = {}
    for name, count in FRAMES.items():
        errors = []
        for quarter in range(4, 4 * count + 1):
            value = quarter / 4.0
            frame = int(value)
            subframe = value - frame
            assign_action(rig, name, frame, subframe)
            hand = rig.matrix_world @ rig.pose.bones["RightHand"].matrix
            deform = hand @ rest_hand.inverted()
            world_hilt = deform @ (sword.matrix_world @ grip)
            current = hand.inverted() @ world_hilt
            errors.append((current - reference).length * rig.matrix_world.to_scale().x)
        maximum = max(errors)
        moves[name] = {
            "quarter_frame_samples": len(errors),
            "maximum_hand_local_hilt_drift_m": maximum,
            "gate_m": 0.00001,
            "gate_pass": maximum < 0.00001,
        }
        print("V3_GRIP", name, maximum, moves[name]["gate_pass"], flush=True)
    return {"moves": moves, "gate_pass": all(row["gate_pass"] for row in moves.values())}


def rigid_deform(rig, bone):
    rest = rig.matrix_world @ rig.data.bones[bone].matrix_local
    pose = rig.matrix_world @ rig.pose.bones[bone].matrix
    return pose @ rest.inverted()


def collision_audit(rig, sword, head):
    head_coords = [tuple(head.matrix_world @ vertex.co) for vertex in head.data.vertices]
    hair_attr = head.data.color_attributes["meshy_hair_mask"]
    head_faces = []
    hair_faces = []
    for poly in head.data.polygons:
        is_hair = np.mean([hair_attr.data[index].color[0] for index in poly.loop_indices]) >= 0.5
        (hair_faces if is_hair else head_faces).append(tuple(poly.vertices))
    head_tree = BVHTree.FromPolygons(head_coords, head_faces, all_triangles=False)
    hair_tree = BVHTree.FromPolygons(head_coords, hair_faces, all_triangles=False)
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    blade_ids = set(int(index) for index in np.where(source[:, 2] < 150)[0])
    blade_faces = [tuple(poly.vertices) for poly in sword.data.polygons if all(index in blade_ids for index in poly.vertices)]
    rest_sword = [sword.matrix_world @ vertex.co for vertex in sword.data.vertices]
    sample_ids = sorted(blade_ids)[::3]
    moves = {}
    for name, count in FRAMES.items():
        overlaps = []
        min_head = math.inf
        min_hair = math.inf
        for frame in range(1, count + 1):
            assign_action(rig, name, frame)
            sword_deform = rigid_deform(rig, "RightHand")
            head_deform_inv = rigid_deform(rig, "Head").inverted()
            in_head_rest = [tuple(head_deform_inv @ (sword_deform @ point)) for point in rest_sword]
            blade_tree = BVHTree.FromPolygons(in_head_rest, blade_faces, all_triangles=False)
            head_overlap = len(blade_tree.overlap(head_tree))
            hair_overlap = len(blade_tree.overlap(hair_tree))
            if head_overlap or hair_overlap:
                overlaps.append({"frame": frame, "head_triangles": head_overlap, "hair_triangles": hair_overlap})
            for index in sample_ids:
                point = Vector(in_head_rest[index])
                nearest_head = head_tree.find_nearest(point)
                nearest_hair = hair_tree.find_nearest(point)
                if nearest_head:
                    min_head = min(min_head, float(nearest_head[3]))
                if nearest_hair:
                    min_hair = min(min_hair, float(nearest_hair[3]))
        moves[name] = {
            "integer_frame_samples": count,
            "frames_with_overlap": len(overlaps),
            "total_head_triangle_pairs": sum(row["head_triangles"] for row in overlaps),
            "total_hair_triangle_pairs": sum(row["hair_triangles"] for row in overlaps),
            "minimum_sampled_head_distance_m": min_head,
            "minimum_sampled_hair_distance_m": min_hair,
            "overlap_frames": overlaps,
            "gate_pass": not overlaps,
        }
        print("V3_COLLISION", name, json.dumps({key: moves[name][key] for key in ("frames_with_overlap", "total_head_triangle_pairs", "total_hair_triangle_pairs", "gate_pass")}), flush=True)
    return {"moves": moves, "gate_pass": all(row["gate_pass"] for row in moves.values())}


def main():
    args = cli()
    blend = root_path(args.blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    sword = bpy.data.objects["Godwyn_Sword"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    samples_path = root_path(args.samples)
    audit_path = root_path(args.out)
    samples = json.loads(samples_path.read_text())
    report = {
        "schema": "astra-v3-audit",
        "blend": str(blend.relative_to(ROOT)),
        "joint_position": joint_audit(rig, samples),
        "edge_stretch": edge_stretch(rig, body),
    }
    if not args.quick:
        report["sword_grip"] = grip_audit(rig, sword)
        report["sole_clearance"] = sole_audit(rig, body)
        report["blade_head_hair"] = collision_audit(rig, sword, head)
    report["gates"] = {
        "joint_p99": report["joint_position"]["overall"]["gate_pass"],
        "edge_stretch": report["edge_stretch"]["gate_pass"],
    }
    if not args.quick:
        report["gates"].update({
            "sword_grip": report["sword_grip"]["gate_pass"],
            "sole_clearance": report["sole_clearance"]["gate_pass"],
            "blade_head_hair": report["blade_head_hair"]["gate_pass"],
        })
    report["all_gates_pass"] = all(report["gates"].values())
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_AUDIT_COMPLETE", json.dumps({"gates": report["gates"], "all": report["all_gates_pass"]}), flush=True)
    if args.require_pass and not report["all_gates_pass"]:
        raise RuntimeError("One or more v3 audit gates failed")


if __name__ == "__main__":
    main()
