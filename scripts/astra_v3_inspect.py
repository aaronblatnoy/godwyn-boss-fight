"""Inspect the Meshy auto-rig GLB against its unrigged source.

Blender-only.  This script does not mutate either input and emits JSON evidence.
"""

import argparse
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = []
    if "--" in __import__("sys").argv:
        raw = __import__("sys").argv[__import__("sys").argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--rigged", default="models/meshy_body_godA_hairback_rigged.glb")
    parser.add_argument("--source", default="models/meshy_body_godA_hairback.glb")
    parser.add_argument("--out", default="renders/astra/char2/meshy_rig_inspect.json")
    return parser.parse_args(raw)


def absolute(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [ob for ob in bpy.data.objects if ob not in before]


def packed_digest(image):
    packed = getattr(image, "packed_file", None)
    if packed is None:
        packed_files = getattr(image, "packed_files", None)
        packed = packed_files[0] if packed_files else None
    if packed is None:
        return None
    try:
        return hashlib.sha256(bytes(packed.data)).hexdigest()
    except Exception:
        return None


def image_row(image):
    return {
        "name": image.name,
        "size": list(image.size),
        "channels": image.channels,
        "alpha_mode": image.alpha_mode,
        "colorspace": image.colorspace_settings.name,
        "source": image.source,
        "packed": bool(getattr(image, "packed_file", None) or getattr(image, "packed_files", None)),
        "packed_sha256": packed_digest(image),
        "filepath": image.filepath,
    }


def material_row(mat):
    images = []
    links = []
    if mat and mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                images.append(node.image.name)
        for link in mat.node_tree.links:
            links.append({
                "from_node": link.from_node.name,
                "from_socket": link.from_socket.name,
                "to_node": link.to_node.name,
                "to_socket": link.to_socket.name,
            })
    return {
        "name": mat.name if mat else None,
        "images": sorted(set(images)),
        "links": links,
    }


def armature_row(arm):
    bones = []
    for bone in arm.data.bones:
        bones.append({
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "connected": bone.use_connect,
            "head": list(bone.head_local),
            "tail": list(bone.tail_local),
            "length_m": bone.length,
            "roll_rad": bone.matrix_local.to_3x3().to_euler("XYZ").y,
            "children": sorted(child.name for child in bone.children),
        })
    return {
        "object": arm.name,
        "bone_count": len(bones),
        "root_bones": sorted(b["name"] for b in bones if b["parent"] is None),
        "finger_bones": sorted(b["name"] for b in bones if "finger" in b["name"].lower() or "thumb" in b["name"].lower()),
        "bones": bones,
    }


def mesh_row(ob):
    mesh = ob.data
    group_names = {group.index: group.name for group in ob.vertex_groups}
    unweighted = []
    bad_sums = []
    influences = []
    for vertex in mesh.vertices:
        weights = [(group_names.get(g.group, str(g.group)), g.weight) for g in vertex.groups if g.weight > 1e-8]
        total = sum(weight for _, weight in weights)
        influences.append(len(weights))
        if not weights:
            unweighted.append(vertex.index)
        if weights and abs(total - 1.0) > 1e-4:
            bad_sums.append({"vertex": vertex.index, "sum": total})
    corners = [ob.matrix_world @ Vector(corner) for corner in ob.bound_box]
    modifiers = []
    for mod in ob.modifiers:
        modifiers.append({
            "name": mod.name,
            "type": mod.type,
            "object": getattr(getattr(mod, "object", None), "name", None),
        })
    return {
        "object": ob.name,
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "triangles": sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons),
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "color_attributes": [attr.name for attr in mesh.color_attributes],
        "material_slots": [slot.material.name if slot.material else None for slot in ob.material_slots],
        "vertex_groups": [group.name for group in ob.vertex_groups],
        "unweighted_vertex_count": len(unweighted),
        "unweighted_vertex_examples": unweighted[:20],
        "bad_weight_sum_count": len(bad_sums),
        "bad_weight_sum_examples": bad_sums[:20],
        "influences_min": min(influences, default=0),
        "influences_max": max(influences, default=0),
        "bounds_world_min": [min(point[i] for point in corners) for i in range(3)],
        "bounds_world_max": [max(point[i] for point in corners) for i in range(3)],
        "modifiers": modifiers,
    }


def inspect(path):
    clear_scene()
    imported = import_glb(path)
    meshes = [ob for ob in imported if ob.type == "MESH"]
    arms = [ob for ob in imported if ob.type == "ARMATURE"]
    actions = []
    for action in bpy.data.actions:
        frame_range = list(action.frame_range)
        actions.append({"name": action.name, "frame_range": frame_range})
    return {
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "objects": [{"name": ob.name, "type": ob.type, "parent": ob.parent.name if ob.parent else None} for ob in imported],
        "meshes": [mesh_row(ob) for ob in meshes],
        "armatures": [armature_row(ob) for ob in arms],
        "actions": actions,
        "images": [image_row(image) for image in bpy.data.images],
        "materials": [material_row(mat) for mat in bpy.data.materials],
    }


def totals(record):
    meshes = record["meshes"]
    return {
        key: sum(row[key] for row in meshes)
        for key in ("vertices", "edges", "polygons", "triangles")
    }


def main():
    args = cli()
    rigged_path = absolute(args.rigged)
    source_path = absolute(args.source)
    out_path = absolute(args.out)
    rigged = inspect(rigged_path)
    source = inspect(source_path)
    rigged_totals = totals(rigged)
    source_totals = totals(source)
    expected = {
        "bone_names": [
            "Hips", "Spine02", "Spine01", "Spine", "neck", "Head", "head_end", "headfront",
            "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand", "RightShoulder", "RightArm",
            "RightForeArm", "RightHand", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
            "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
        ],
        "height_m": 3.16,
    }
    arms = rigged["armatures"]
    actual_names = sorted(b["name"] for b in arms[0]["bones"]) if arms else []
    body_rows = [row for row in rigged["meshes"] if row["vertex_groups"]]
    report = {
        "schema": "astra-meshy-rig-inspect-v3",
        "rigged": rigged,
        "source": source,
        "comparison": {
            "rigged_totals": rigged_totals,
            "source_totals": source_totals,
            "polygon_ratio": rigged_totals["polygons"] / max(1, source_totals["polygons"]),
            "triangle_ratio": rigged_totals["triangles"] / max(1, source_totals["triangles"]),
            "same_geometry_counts": rigged_totals == source_totals,
            "rigged_image_sizes": sorted(row["size"] for row in rigged["images"]),
            "source_image_sizes": sorted(row["size"] for row in source["images"]),
        },
        "expected": expected,
        "gates": {
            "one_armature": len(arms) == 1,
            "exact_24_bone_set": len(actual_names) == 24 and actual_names == sorted(expected["bone_names"]),
            "root_is_hips": bool(arms) and arms[0]["root_bones"] == ["Hips"],
            "no_finger_bones": bool(arms) and not arms[0]["finger_bones"],
            "bound_body_found": len(body_rows) == 1,
            "no_unweighted_vertices": bool(body_rows) and body_rows[0]["unweighted_vertex_count"] == 0,
            "normalized_weights": bool(body_rows) and body_rows[0]["bad_weight_sum_count"] == 0,
            "full_resolution_not_decimated": rigged_totals["triangles"] >= 300000,
            "has_2048_texture": any(row["size"] == [2048, 2048] for row in rigged["images"]),
        },
    }
    report["passed"] = all(report["gates"].values())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"out": str(out_path), "passed": report["passed"], "gates": report["gates"]}, indent=2))
    if not report["passed"]:
        raise RuntimeError("Meshy rig inspection gates failed")


if __name__ == "__main__":
    main()
