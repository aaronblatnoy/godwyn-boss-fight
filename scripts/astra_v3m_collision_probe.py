"""Diagnose visible head/hair versus collar/pauldron intersections."""

import json
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_wip.blend"
OUT = ROOT / "renders/astra/char2/astra_v3m_collision_probe.json"
CLIPS = [action.name for action in []]


def assign(rig, action, frame):
    animation = rig.animation_data_create()
    animation.action = action
    if action.slots:
        animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def coords(ob):
    item = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = item.to_mesh()
    values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", values)
    values = values.reshape(-1, 3)
    matrix = np.asarray(item.matrix_world)
    values = values @ matrix[:3, :3].T + matrix[:3, 3]
    item.to_mesh_clear()
    return values


def bounds(values, ids):
    selected = values[sorted(ids)]
    return {"min": selected.min(axis=0).tolist(), "max": selected.max(axis=0).tolist(), "vertices": len(ids)}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    body_rest = np.asarray([(body.matrix_world @ vertex.co)[:] for vertex in body.data.vertices])
    head_rest = np.asarray([(head.matrix_world @ vertex.co)[:] for vertex in head.data.vertices])
    plate_attr = body.data.color_attributes["astra_v3_plate_mask"]
    group_names = {group.index: group.name for group in body.vertex_groups}
    head_chain = {"neck", "Head", "head_end", "headfront"}
    armor = []
    for poly in body.data.polygons:
        center = body_rest[list(poly.vertices)].mean(axis=0)
        plate = np.mean([plate_attr.data[index].color[0] for index in poly.loop_indices]) >= 0.5
        head_chain_weight = np.mean([
            sum(item.weight for item in body.data.vertices[index].groups if group_names.get(item.group) in head_chain)
            for index in poly.vertices
        ])
        if plate and head_chain_weight < 0.25 and 2.43 <= center[2] <= 2.90 and abs(center[0]) <= 0.82 and -0.65 <= center[1] <= 0.28:
            armor.append((poly.index, tuple(poly.vertices)))
    hair_attr = head.data.color_attributes["meshy_hair_mask"]
    hair = []
    skin = []
    for poly in head.data.polygons:
        value = np.mean([hair_attr.data[index].color[0] for index in poly.loop_indices])
        item = (poly.index, tuple(poly.vertices))
        if value >= 0.5:
            hair.append(item)
        elif float(head_rest[list(poly.vertices), 2].mean()) >= 2.68:
            skin.append(item)
    report = {}
    for name in ["Combat_Stance"]:
        action = bpy.data.actions[name]
        start, end = [int(round(value)) for value in action.frame_range]
        # Frame 1 plus the widest extremity pose are enough for the attachment gate.
        samples = []
        max_row = (-1.0, start)
        for frame in range(start, end + 1):
            assign(rig, action, frame)
            root = rig.matrix_world @ rig.pose.bones["Hips"].head
            score = sum((rig.matrix_world @ rig.pose.bones[bone].head - root).length for bone in ("Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot"))
            max_row = max(max_row, (score, frame))
        for frame in sorted(set([start, max_row[1]])):
            assign(rig, action, frame)
            bc = coords(body)
            hc = coords(head)
            armor_tree = BVHTree.FromPolygons([tuple(point) for point in bc], [row[1] for row in armor], all_triangles=False)
            row = {"frame": frame}
            for label, source in (("hair", hair), ("head", skin)):
                source_tree = BVHTree.FromPolygons([tuple(point) for point in hc], [item[1] for item in source], all_triangles=False)
                overlaps = armor_tree.overlap(source_tree)
                source_faces = {source[pair[1]][0] for pair in overlaps}
                armor_faces = {armor[pair[0]][0] for pair in overlaps}
                source_vertices = {index for poly_index in source_faces for index in head.data.polygons[poly_index].vertices}
                armor_vertices = {index for poly_index in armor_faces for index in body.data.polygons[poly_index].vertices}
                row[label] = {
                    "triangle_pairs": len(overlaps),
                    "source_faces": len(source_faces),
                    "armor_faces": len(armor_faces),
                    "source_rest_bounds": bounds(head_rest, source_vertices) if source_vertices else None,
                    "source_posed_bounds": bounds(hc, source_vertices) if source_vertices else None,
                    "armor_posed_bounds": bounds(bc, armor_vertices) if armor_vertices else None,
                }
            samples.append(row)
        report[name] = {"most_extended_frame": max_row[1], "samples": samples}
        print("V3M_COLLISION_PROBE", name, json.dumps(samples), flush=True)
    OUT.write_text(json.dumps({"schema": "astra-v3m-collision-probe", "clips": report}, indent=2) + "\n")


if __name__ == "__main__":
    main()
