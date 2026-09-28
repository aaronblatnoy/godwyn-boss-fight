"""Apply the smallest RightHand leaf rotation that clears xslash frames 54-55."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_xslash_clearance_fix.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def assign(rig, action, frame):
    animation = rig.animation_data_create()
    animation.action = action
    animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def rigid_deform(rig, bone):
    rest = rig.matrix_world @ rig.data.bones[bone].matrix_local
    pose = rig.matrix_world @ rig.pose.bones[bone].matrix
    return pose @ rest.inverted()


def collision_cache(head, sword):
    head_coords = [tuple(head.matrix_world @ vertex.co) for vertex in head.data.vertices]
    hair_attr = head.data.color_attributes["meshy_hair_mask"]
    head_faces, hair_faces = [], []
    for poly in head.data.polygons:
        is_hair = np.mean([hair_attr.data[index].color[0] for index in poly.loop_indices]) >= 0.5
        (hair_faces if is_hair else head_faces).append(tuple(poly.vertices))
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    blade_ids = set(int(index) for index in np.where(source[:, 2] < 150)[0])
    blade_faces = [tuple(poly.vertices) for poly in sword.data.polygons if all(index in blade_ids for index in poly.vertices)]
    return {
        "head": BVHTree.FromPolygons(head_coords, head_faces, all_triangles=False),
        "hair": BVHTree.FromPolygons(head_coords, hair_faces, all_triangles=False),
        "sword_points": [sword.matrix_world @ vertex.co for vertex in sword.data.vertices],
        "blade_faces": blade_faces,
    }


def counts(rig, cache):
    sword_deform = rigid_deform(rig, "RightHand")
    head_deform_inv = rigid_deform(rig, "Head").inverted()
    points = [tuple(head_deform_inv @ (sword_deform @ point)) for point in cache["sword_points"]]
    blade = BVHTree.FromPolygons(points, cache["blade_faces"], all_triangles=False)
    return len(blade.overlap(cache["head"])), len(blade.overlap(cache["hair"]))


def evaluate(rig, action, hand, cache, axis, angle_degrees):
    rows = []
    delta = Quaternion(axis, math.radians(angle_degrees))
    for frame in (54, 55):
        assign(rig, action, frame)
        base = hand.rotation_quaternion.copy()
        hand.rotation_quaternion = base @ delta
        bpy.context.view_layer.update()
        head_count, hair_count = counts(rig, cache)
        rows.append({"frame": frame, "head_triangles": head_count, "hair_triangles": hair_count})
    return rows


def main():
    args = cli()
    blend = root_path(args.blend)
    output = root_path(args.out)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    sword = bpy.data.objects["Godwyn_Sword"]
    action = bpy.data.actions["Godwyn_V3_xslash"]
    hand = rig.pose.bones["RightHand"]
    cache = collision_cache(head, sword)
    candidates = []
    for axis_name, axis in (("X", Vector((1, 0, 0))), ("Y", Vector((0, 1, 0))), ("Z", Vector((0, 0, 1)))):
        for angle in (-60, -50, -45, -40, -36, -30, -24, -18, -12, -8, -5, 5, 8, 12, 18, 24, 30, 36, 40, 45, 50, 60):
            rows = evaluate(rig, action, hand, cache, axis, angle)
            total = sum(row["head_triangles"] + row["hair_triangles"] for row in rows)
            candidates.append({"axis": axis_name, "angle_degrees": angle, "total_triangle_pairs": total, "frames": rows})
    candidates.sort(key=lambda row: (row["total_triangle_pairs"], abs(row["angle_degrees"]), row["axis"], row["angle_degrees"]))
    best = candidates[0]
    assert best["total_triangle_pairs"] == 0, candidates[:10]
    axis = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}[best["axis"]]
    factors = {}
    for frame in range(47, 64):
        if frame <= 54:
            factor = (frame - 47) / 7.0
        elif frame <= 55:
            factor = 1.0
        else:
            factor = (63 - frame) / 8.0
        factors[frame] = max(0.0, min(1.0, factor))
    data_path = 'pose.bones["RightHand"].rotation_quaternion'
    curves = {}
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path == data_path:
                        curves[curve.array_index] = curve
    assert sorted(curves) == [0, 1, 2, 3]
    for frame, factor in factors.items():
        assign(rig, action, frame)
        base = hand.rotation_quaternion.copy()
        hand.rotation_quaternion = base @ Quaternion(axis, math.radians(best["angle_degrees"] * factor))
        for index, value in enumerate(hand.rotation_quaternion):
            point = next(point for point in curves[index].keyframe_points if abs(point.co.x - frame) < 1e-5)
            point.co.y = value
            point.interpolation = "LINEAR"
    verification = evaluate(rig, action, hand, cache, axis, 0.0)
    assert sum(row["head_triangles"] + row["hair_triangles"] for row in verification) == 0, verification
    report = {
        "schema": "astra-v3fists-xslash-clearance-fix",
        "method": "smallest tested local leaf-bone RightHand rotation with zero blade/head/hair triangle pairs at both failing frames",
        "selected": best,
        "per_frame_factors": factors,
        "post_key_verification": verification,
        "candidate_results": candidates,
        "joint_position_effect": "none at RightHand joint head; rotation is on the leaf bone only",
        "grip_effect": "none; sword remains rigidly weighted to RightHand",
    }
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_XSLASH_CLEARANCE_PASS", json.dumps({"selected": best, "verification": verification}), flush=True)


if __name__ == "__main__":
    main()
