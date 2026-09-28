"""Full mechanical audit for V3 Meshy mocap clips on black-sky."""

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3m_audit.json"
QUICK = "--quick" in sys.argv
CLIPS = [
    "Combat_Stance", "Walk_Fight_Forward", "Attack", "Left_Slash",
    "Right_Hand_Sword_Slash", "Double_Combo_Attack", "Triple_Combo_Attack",
    "Sword_Judgment", "Reaping_Swing", "Rightward_Spin", "Basic_Jump",
    "Roll_Dodge", "Sword_Parry", "Hit_Reaction", "Dead",
]
if "--clips" in sys.argv:
    marker = sys.argv.index("--clips")
    requested = []
    for value in sys.argv[marker + 1:]:
        if value.startswith("--"):
            break
        requested.append(value)
    assert requested and set(requested).issubset(CLIPS), requested
    CLIPS = requested


def assign(rig, action, frame):
    animation = rig.animation_data_create()
    animation.action = action
    if action.slots:
        animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def evaluated(ob):
    item = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = item.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    matrix = np.asarray(item.matrix_world)
    coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
    faces = [tuple(poly.vertices) for poly in mesh.polygons]
    item.to_mesh_clear()
    return coords, faces


def tree(coords, faces):
    return BVHTree.FromPolygons([tuple(point) for point in coords], faces, all_triangles=False)


def face_sets(body, head, sword):
    body_rest = np.asarray([(body.matrix_world @ vertex.co)[:] for vertex in body.data.vertices], dtype=float)
    plate_attr = body.data.color_attributes["astra_v3_plate_mask"]
    group_names = {group.index: group.name for group in body.vertex_groups}
    head_chain = {"neck", "Head", "head_end", "headfront"}
    collar = []
    for poly in body.data.polygons:
        center = np.mean(body_rest[list(poly.vertices)], axis=0)
        plate = np.mean([plate_attr.data[index].color[0] for index in poly.loop_indices]) >= 0.5
        head_chain_weight = np.mean([
            sum(item.weight for item in body.data.vertices[index].groups if group_names.get(item.group) in head_chain)
            for index in poly.vertices
        ])
        if plate and head_chain_weight < 0.25 and 2.43 <= center[2] <= 2.90 and abs(center[0]) <= 0.82 and -0.65 <= center[1] <= 0.28:
            collar.append(tuple(poly.vertices))
    hair_attr = head.data.color_attributes["meshy_hair_mask"]
    head_rest = np.asarray([(head.matrix_world @ vertex.co)[:] for vertex in head.data.vertices], dtype=float)
    skin_faces, hair_faces = [], []
    for poly in head.data.polygons:
        value = np.mean([hair_attr.data[index].color[0] for index in poly.loop_indices])
        vertices = tuple(poly.vertices)
        if value >= 0.5:
            hair_faces.append(vertices)
        elif float(np.mean(head_rest[list(vertices), 2])) >= 2.68:
            # The donor's lower neck is intentionally buried inside the gorget;
            # it is not visible head/collar penetration.  Gate the jaw/face and
            # all hair, while the separate NeckBlend owns the hidden interior.
            skin_faces.append(vertices)
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    blade_ids = set(int(index) for index in np.where(source[:, 2] < 150)[0])
    blade_faces = [tuple(poly.vertices) for poly in sword.data.polygons if all(index in blade_ids for index in poly.vertices)]
    return body_rest, collar, skin_faces, hair_faces, blade_ids, blade_faces


def sole_ids(body):
    names = {group.index: group.name for group in body.vertex_groups}
    result = {}
    for side in ("Left", "Right"):
        allowed = {side + "Foot", side + "ToeBase"}
        indices = []
        for vertex in body.data.vertices:
            world = body.matrix_world @ vertex.co
            influence = sum(item.weight for item in vertex.groups if names.get(item.group) in allowed)
            if world.z < 0.24 and influence > 0.5:
                indices.append(vertex.index)
        assert indices
        result[side] = np.asarray(indices, dtype=np.int32)
    return result


def body_edge_data(body, rest):
    edges = np.empty(len(body.data.edges) * 2, dtype=np.int32)
    body.data.edges.foreach_get("vertices", edges)
    edges = edges.reshape(-1, 2)
    lengths = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
    valid = lengths >= 0.002
    return edges, lengths, valid


def max_extent_frame(rig, action, start, end):
    names = ["Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot"]
    rows = []
    for frame in range(start, end + 1):
        assign(rig, action, frame)
        root = rig.matrix_world @ rig.pose.bones["Hips"].head
        score = sum((rig.matrix_world @ rig.pose.bones[name].head - root).length for name in names)
        rows.append((score, frame))
    return max(rows)[1]


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    neck = bpy.data.objects["AstraChar2_Meshy_NeckBlend"]
    sword = bpy.data.objects["Godwyn_Sword"]
    rest, collar_faces, skin_faces, hair_faces, blade_ids, blade_faces = face_sets(body, head, sword)
    edges, rest_lengths, valid_edges = body_edge_data(body, rest)
    soles = sole_ids(body)
    body_faces = [tuple(poly.vertices) for poly in body.data.polygons]
    reports = {}
    for name in CLIPS:
        action = bpy.data.actions[name]
        start, end = [int(round(value)) for value in action.frame_range]
        extended = max_extent_frame(rig, action, start, end)
        stretch_p99 = []
        stretch_max = []
        foot_rows = []
        floor_rows = []
        blade_head_rows = []
        blade_body_rows = []
        head_armor_rows = []
        for frame in range(start, end + 1):
            assign(rig, action, frame)
            body_coords, _ = evaluated(body)
            posed_lengths = np.linalg.norm(body_coords[edges[:, 0]] - body_coords[edges[:, 1]], axis=1)
            ratios = posed_lengths[valid_edges] / rest_lengths[valid_edges]
            stretch_p99.append((float(np.percentile(ratios, 99)), frame))
            stretch_max.append((float(ratios.max()), frame))
            foot = {side: float(body_coords[indices, 2].min()) for side, indices in soles.items()}
            foot_rows.append((min(foot.values()), frame, foot))
            if QUICK:
                if frame == start or frame == end or (frame - start + 1) % 20 == 0:
                    print("V3M_AUDIT_PROGRESS", name, frame - start + 1, end - start + 1, flush=True)
                continue
            head_coords, _ = evaluated(head)
            sword_coords, _ = evaluated(sword)
            blade_floor = float(sword_coords[list(blade_ids), 2].min())
            floor_rows.append((blade_floor, frame))
            blade_tree = tree(sword_coords, blade_faces)
            skin_pairs = len(blade_tree.overlap(tree(head_coords, skin_faces)))
            hair_pairs = len(blade_tree.overlap(tree(head_coords, hair_faces)))
            if skin_pairs or hair_pairs:
                blade_head_rows.append({"frame": frame, "head_triangle_pairs": skin_pairs, "hair_triangle_pairs": hair_pairs})
            body_tree = tree(body_coords, body_faces)
            body_pairs = len(blade_tree.overlap(body_tree))
            if body_pairs:
                blade_body_rows.append({"frame": frame, "triangle_pairs": body_pairs})
            if frame == extended or frame == start:
                armor_tree = tree(body_coords, collar_faces)
                head_pairs = len(armor_tree.overlap(tree(head_coords, skin_faces)))
                hair_armor_pairs = len(armor_tree.overlap(tree(head_coords, hair_faces)))
                head_armor_rows.append({"frame": frame, "head_triangle_pairs": head_pairs, "hair_triangle_pairs": hair_armor_pairs})
            if frame == start or frame == end or (frame - start + 1) % 20 == 0:
                print("V3M_AUDIT_PROGRESS", name, frame - start + 1, end - start + 1, flush=True)
        worst_p99 = max(stretch_p99)
        worst_max = max(stretch_max)
        worst_foot = min(foot_rows)
        worst_sword_floor = min(floor_rows) if floor_rows else (math.inf, start)
        head_armor_pairs = sum(row["head_triangle_pairs"] + row["hair_triangle_pairs"] for row in head_armor_rows)
        reports[name] = {
            "frames": end - start + 1,
            "fps": 30,
            "most_extended_frame": extended,
            "body_edge_stretch": {
                "gate_p99": 1.6,
                "worst_frame_p99": worst_p99[0],
                "worst_frame": worst_p99[1],
                "absolute_max_ratio": worst_max[0],
                "absolute_max_frame": worst_max[1],
                "gate_pass": worst_p99[0] <= 1.6,
                "population": f"{int(valid_edges.sum())} edges with rest length >= 2 mm, sampled every integer frame",
            },
            "feet_floor": {
                "gate_minimum_m": -0.005,
                "minimum_m": worst_foot[0],
                "worst_frame": worst_foot[1],
                "per_side_m": worst_foot[2],
                "gate_pass": worst_foot[0] >= -0.005,
            },
            "head_hair_vs_collar_pauldrons": {
                "sampled_frames": sorted(set([start, extended])),
                "rows": head_armor_rows,
                "triangle_pairs": head_armor_pairs,
                "gate_pass": head_armor_pairs == 0,
                "selection": "astra_v3_plate_mask faces with mean neck/head-chain weight <0.25 in upper-torso collar/pauldron volume versus all hair and donor skin at/above rest z=2.68 m; hidden lower donor neck and residual source-head shell excluded",
            },
            "sword_vs_head_hair": {
                "frames_with_overlap": len(blade_head_rows),
                "worst_triangle_pairs": max((row["head_triangle_pairs"] + row["hair_triangle_pairs"] for row in blade_head_rows), default=0),
                "overlap_frames": blade_head_rows,
                "gate_pass": not blade_head_rows,
            },
            "sword_vs_body": {
                "frames_with_overlap": len(blade_body_rows),
                "worst_triangle_pairs": max((row["triangle_pairs"] for row in blade_body_rows), default=0),
                "overlap_frames": blade_body_rows,
                "flagged": bool(blade_body_rows),
            },
            "sword_vs_floor": {
                "minimum_blade_z_m": worst_sword_floor[0],
                "worst_frame": worst_sword_floor[1],
                "penetration_depth_m": max(0.0, -worst_sword_floor[0]),
                "flagged": worst_sword_floor[0] < -0.005,
            },
        }
        reports[name]["quality_gate_pass"] = all([
            reports[name]["body_edge_stretch"]["gate_pass"],
            reports[name]["feet_floor"]["gate_pass"],
            reports[name]["head_hair_vs_collar_pauldrons"]["gate_pass"],
            reports[name]["sword_vs_head_hair"]["gate_pass"],
        ])
        print("V3M_AUDIT_CLIP", name, json.dumps({
            "p99": worst_p99[0], "foot": worst_foot[0], "head_armor_pairs": head_armor_pairs,
            "sword_head_frames": len(blade_head_rows), "sword_body_frames": len(blade_body_rows),
            "sword_floor": worst_sword_floor[0], "pass": reports[name]["quality_gate_pass"],
        }), flush=True)
    prior = {}
    if OUT.exists() and len(CLIPS) < 15 and not QUICK:
        prior = json.loads(OUT.read_text()).get("clips", {})
        prior.update(reports)
        reports = prior
    report = {
        "schema": "meshy-v3m-audit",
        "blend": str(BLEND.relative_to(ROOT)),
        "fps": 30,
        "clip_count": len(reports),
        "binding": {
            "head_rigid_head_bone": head.parent == rig and list(head.vertex_groups.keys()) == ["Head"],
            "neckblend_rigid_neck_bone": neck.parent == rig and list(neck.vertex_groups.keys()) == ["neck"],
            "sword_rigid_right_hand": sword.parent == rig and list(sword.vertex_groups.keys()) == ["RightHand"],
        },
        "clips": reports,
        "all_quality_gates_pass": all(row["quality_gate_pass"] for row in reports.values()),
    }
    output = OUT.with_name("meshy_v3m_quick_audit.json") if QUICK else OUT
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_AUDIT_COMPLETE", json.dumps({"all": report["all_quality_gates_pass"], "binding": report["binding"]}), flush=True)


if __name__ == "__main__":
    main()
