"""Finish the fist-body Godwyn v3 without altering approved source assets."""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_finalize.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def masked_vertices(head):
    attribute = head.data.color_attributes.get("meshy_skin_mask")
    assert attribute is not None
    result = set()
    for poly in head.data.polygons:
        for loop_index in poly.loop_indices:
            if float(attribute.data[loop_index].color[0]) >= 0.5:
                result.add(head.data.loops[loop_index].vertex_index)
    return result


def trim_donor_skin(head, neck_center_x):
    skin = head.data.color_attributes["meshy_skin_mask"]
    before_faces = len(head.data.polygons)
    before_masked = len(masked_vertices(head))
    removed = []
    for poly in head.data.polygons:
        skin_value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
        center = head.matrix_world @ poly.center
        trim_shoulder = center.z < 2.760 and not (neck_center_x - 0.120 <= center.x <= neck_center_x + 0.120)
        trim_chest = center.z < 2.620
        poly.select = skin_value >= 0.5 and (trim_shoulder or trim_chest)
        if poly.select:
            removed.append(tuple(center))
    assert removed
    bpy.context.view_layer.objects.active = head
    head.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    head.data.update()
    after_masked = len(masked_vertices(head))
    points = np.asarray(removed, dtype=float)
    return {
        "before_faces": before_faces,
        "after_faces": len(head.data.polygons),
        "removed_faces": before_faces - len(head.data.polygons),
        "removed_class": "skin only (meshy_skin_mask >= 0.5)",
        "preserved_neck_x_m": [neck_center_x - 0.120, neck_center_x + 0.120],
        "removed_center_bounds_m": {"min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist()},
        "skin_masked_vertices_before_trim": before_masked,
        "skin_masked_vertices_after_trim": after_masked,
        "skin_mask_attribute_survived": head.data.color_attributes.get("meshy_skin_mask") is not None,
    }


def material(name, color, metallic=0.0, roughness=0.6):
    result = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return result


def bone_parent(obj, rig, bone):
    world = obj.matrix_world.copy()
    obj.parent = rig
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    obj.matrix_world = world


def create_neck_occlusion(rig, center_xy, collar_floor):
    for name in ("Astra_V3_Rigid_Neck_Bridge", "Astra_V3_Collar_Occluder", "Astra_V3_Neck_Gorget_Trim"):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    x, y = center_xy
    cap_z = min(2.640, max(2.600, collar_floor + 0.040))
    dark = material("Astra V3 Collar Interior Occluder", (0.010, 0.012, 0.018), 0.0, 0.82)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.140, depth=0.025, end_fill_type="NGON", location=(x, y, cap_z))
    cap = bpy.context.object
    cap.name = "Astra_V3_Collar_Occluder"
    cap.scale.y = 0.78
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    cap.data.materials.append(dark)
    bone_parent(cap, rig, "neck")
    return {
        "collar_floor_z_m": collar_floor,
        "cap_z_m": cap_z,
        "center_xy_m": list(center_xy),
        "bridge": None,
        "occluder": {"object": cap.name, "radius_m": 0.140, "depth_m": 0.025, "y_scale": 0.78, "parent_bone": "neck", "material": dark.name},
        "gold_trim_added": False,
        "reason": "preserved source gorget supplies the visible gold rim; dark disc closes only the hidden interior",
    }


def hilt_point(sword):
    source = np.asarray([item.vector[:] for item in sword.data.attributes["astra_sword_source"].data])
    local = np.asarray([vertex.co[:] for vertex in sword.data.vertices])
    fit = np.linalg.lstsq(np.column_stack((source, np.ones(len(source)))), local, rcond=None)[0]
    return Vector(np.array([61.2, -66.3, 167.0, 1.0]) @ fit)


def fist_hull(body):
    group = body.vertex_groups["RightHand"].index
    points = []
    for vertex in body.data.vertices:
        weight = sum(item.weight for item in vertex.groups if item.group == group)
        if weight >= 0.35:
            points.append(body.matrix_world @ vertex.co)
    assert len(points) >= 20
    mesh = bpy.data.meshes.new("Astra V3 temporary fist hull")
    mesh.from_pydata([tuple(point) for point in points], [], [])
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    centroid = sum(points, Vector()) / len(points)
    return tree, centroid, bm, mesh, len(points)


def hull_measure(tree, point):
    nearest, normal, _index, distance = tree.find_nearest(point)
    signed = (point - nearest).dot(normal)
    inside = signed <= 1e-7
    return {"inside": inside, "intersection_depth_m": float(distance if inside else 0.0), "outside_clearance_m": float(0.0 if inside else distance), "signed_nearest_m": float(signed)}


def seat_sword(body, sword, rig):
    tree, centroid, bm, mesh, points = fist_hull(body)
    before_point = sword.matrix_world @ hilt_point(sword)
    before = hull_measure(tree, before_point)
    offset = Vector((0.0, 0.0, 0.0))
    if not before["inside"]:
        direction = centroid - before_point
        if direction.length:
            offset = direction.normalized() * min(0.030, before["outside_clearance_m"] + 0.004)
            for vertex in sword.data.vertices:
                world = sword.matrix_world @ vertex.co + offset
                vertex.co = sword.matrix_world.inverted() @ world
            sword.data.update()
    after_point = sword.matrix_world @ hilt_point(sword)
    after = hull_measure(tree, after_point)
    bm.free()
    bpy.data.meshes.remove(mesh)
    assert offset.length <= 0.0300001
    assert after["inside"], (before, after, list(offset))
    hand_rest = rig.matrix_world @ rig.data.bones["RightHand"].matrix_local
    return {
        "method": "hilt point tested against convex hull of vertices with RightHand weight >= 0.35",
        "fist_vertices_in_hull": points,
        "before": before,
        "after": after,
        "adjustment_world_m": list(offset),
        "adjustment_length_m": offset.length,
        "adjustment_limit_m": 0.030,
        "hilt_world_after_m": list(after_point),
        "hilt_right_hand_local_after_m": list(hand_rest.inverted() @ after_point),
    }


def repair_low_fragments(body):
    parent = list(range(len(body.data.vertices)))
    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for edge in body.data.edges:
        union(*edge.vertices)
    components = {}
    for vertex in body.data.vertices:
        components.setdefault(find(vertex.index), []).append(vertex.index)
    head_index = body.vertex_groups["Head"].index
    hips = body.vertex_groups["Hips"]
    repaired = []
    for root, indices in components.items():
        points = np.asarray([(body.matrix_world @ body.data.vertices[index].co)[:] for index in indices])
        mean_head = np.mean([
            sum(item.weight for item in body.data.vertices[index].groups if item.group == head_index)
            for index in indices
        ])
        if float(points[:, 2].max()) >= 1.30 or mean_head <= 0.50:
            continue
        for index in indices:
            for membership in list(body.data.vertices[index].groups):
                body.vertex_groups[membership.group].remove([index])
            hips.add([index], 1.0, "REPLACE")
        repaired.append({"component_root": root, "vertices": len(indices), "mean_head_weight_before": float(mean_head)})
    return {"components": len(repaired), "vertices": sum(item["vertices"] for item in repaired), "details": repaired}


def main():
    args = cli()
    blend = root_path(args.blend)
    output = root_path(args.out)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    sword = bpy.data.objects["Godwyn_Sword"]
    metadata = json.loads(bpy.context.scene["astra_v3"])
    donor_trim = trim_donor_skin(head, metadata["head_fit"]["target_seam_center_xy_m"][0])
    neck_blend = bpy.data.objects.get("AstraChar2_Meshy_NeckBlend")
    removed_neck_blend = neck_blend.name if neck_blend else None
    if neck_blend:
        bpy.data.objects.remove(neck_blend, do_unlink=True)
    segmentation = metadata["segmentation"]
    assert segmentation["removed_faces_by_class"]["plate"] == 0
    upper_xy = segmentation["removed_head_measurements"]["upper_center_xy_m"]
    seam_xy = metadata["head_fit"]["target_seam_center_xy_m"]
    collar_center = [(upper_xy[0] + seam_xy[0]) * 0.5, (upper_xy[1] + seam_xy[1]) * 0.5]
    collar = create_neck_occlusion(
        rig,
        collar_center,
        segmentation["collar_measurement"]["interior_floor_z_m"],
    )
    sword_seating = seat_sword(body, sword, rig)
    fragments = repair_low_fragments(body)
    report = {
        "schema": "astra-v3fists-finalize",
        "blend": str(blend.relative_to(ROOT)),
        "body_head_neck_removal": {
            "faces_by_class": segmentation["removed_faces_by_class"],
            "collar_measurement": segmentation["collar_measurement"],
            "plate_faces_removed": 0,
        },
        "donor_head_trim": donor_trim,
        "removed_neck_blend": removed_neck_blend,
        "collar_occlusion": collar,
        "sword_fist_seating": sword_seating,
        "low_garment_fragment_repair": fragments,
    }
    bpy.context.scene["astra_v3fists_finalize"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_FINALIZE_PASS", json.dumps({"plate_faces_removed": 0, "donor_faces_removed": donor_trim["removed_faces"], "hilt": sword_seating, "fragments": fragments}), flush=True)


if __name__ == "__main__":
    main()
