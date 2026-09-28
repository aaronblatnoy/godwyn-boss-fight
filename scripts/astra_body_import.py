"""Inspect and quick-render the supplied Meshy Godwyn body GLB on black-sky."""
import bpy
import json
import math
import sys
from collections import deque
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/meshy_body_godA_hairback.glb"
OUT = ROOT / "renders/astra/char2"
REPORT = OUT / "meshy_body_i02_import.json"


def world_bounds(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def components(mesh):
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = bytearray(len(mesh.vertices))
    rows = []
    for seed in range(len(mesh.vertices)):
        if seen[seed]:
            continue
        stack = [seed]
        seen[seed] = 1
        ids = []
        while stack:
            current = stack.pop()
            ids.append(current)
            for other in adjacency[current]:
                if not seen[other]:
                    seen[other] = 1
                    stack.append(other)
        coords = [mesh.vertices[index].co for index in ids]
        lo = [min(p[k] for p in coords) for k in range(3)]
        hi = [max(p[k] for p in coords) for k in range(3)]
        rows.append({"vertices": len(ids), "bounds_local": [lo, hi],
                     "extent_local": [hi[k] - lo[k] for k in range(3)]})
    rows.sort(key=lambda row: row["vertices"], reverse=True)
    return rows


def image_record(image):
    return {
        "name": image.name,
        "size": list(image.size),
        "channels": image.channels,
        "colorspace": image.colorspace_settings.name,
        "packed": image.packed_file is not None,
        "filepath": image.filepath,
    }


def render_views(obj, lo, hi):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 768, 1152
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("Meshy body import world")
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs[0].default_value = (0.035, 0.035, 0.045, 1)
    background.inputs[1].default_value = 0.55
    center = (lo + hi) * 0.5
    height = hi.z - lo.z
    for name, offset, energy, color, size in [
        ("Import Key", Vector((-2.2, -3.2, 2.3)), 1800, (1.0, 0.83, 0.62), 2.8),
        ("Import Fill", Vector((2.6, -2.1, 0.7)), 1050, (0.62, 0.72, 1.0), 3.5),
        ("Import Rim", Vector((1.2, 2.8, 2.0)), 1500, (1.0, 0.78, 0.45), 2.3),
    ]:
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.color = color
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = center + offset * height
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("Meshy body import camera")
    camera_data.lens = 70
    camera = bpy.data.objects.new("Meshy body import camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [
        ("front", Vector((0, -1, 0))),
        ("side", Vector((1, 0, 0))),
        ("tq", Vector((0.72, -0.72, 0))),
    ]
    for label, direction in views:
        camera.location = center + direction.normalized() * height * 2.20
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUT / f"meshy_body2_import_{label}.png")
        bpy.ops.render.render(write_still=True)
        print("IMPORT_RENDER", label, flush=True)


def main():
    assert SOURCE.exists()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    assert len(meshes) == 1, [obj.name for obj in meshes]
    obj = meshes[0]
    mesh = obj.data
    mesh.calc_loop_triangles()
    lo, hi = world_bounds(obj)
    component_rows = components(mesh)
    material_rows = []
    for material in mesh.materials:
        nodes = []
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type in {"TEX_IMAGE", "BSDF_PRINCIPLED", "NORMAL_MAP", "SEPARATE_COLOR"}:
                    nodes.append({"name": node.name, "type": node.type,
                                  "image": node.image.name if node.type == "TEX_IMAGE" and node.image else None})
        material_rows.append({"name": material.name if material else None, "nodes": nodes})
    # A sword candidate would be a long, thin disconnected component. This is
    # intentionally geometry-driven because the hand-painted texture alone is ambiguous.
    sword_candidates = []
    for index, row in enumerate(component_rows):
        ext = sorted(row["extent_local"], reverse=True)
        if row["vertices"] > 100 and ext[0] > 0.35 and ext[0] > 5.0 * max(ext[1], 1e-6):
            sword_candidates.append(index)
    report = {
        "source": str(SOURCE.relative_to(ROOT)),
        "blender_version": bpy.app.version_string,
        "objects": [obj.name],
        "mesh": {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "triangles": len(mesh.loop_triangles),
            "uv_layers": [layer.name for layer in mesh.uv_layers],
            "material_slots": len(mesh.materials),
        },
        "object_transform": {
            "location": list(obj.location), "rotation_euler": list(obj.rotation_euler), "scale": list(obj.scale),
        },
        "bounds_world_m": {"min": list(lo), "max": list(hi), "extent": list(hi - lo)},
        "materials": material_rows,
        "textures": [image_record(image) for image in bpy.data.images],
        "connected_components": len(component_rows),
        "largest_components": component_rows[:40],
        "sword_like_component_indices": sword_candidates,
        "sword_geometry_present": bool(sword_candidates),
        "concept_read": {
            "verdict": "strong match",
            "observations": [
                "Recognizable gold plate, deep blue velvet robe and sash, laurel trim, gauntlets, greaves and boots.",
                "The continuous decorated textile and layered armor silhouette are materially closer to god_A than the procedural body.",
                "The tied-back source hair does not cross the shoulders or arms; both upper limbs read as complete in the raw views.",
                "Source head and tied-back hair are lower-detail and will be removed in favor of the published Meshy i02 head and hair.",
            ],
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2) + "\n"
    REPORT.write_text(payload)
    # The brief retains the original generic filename as a required handoff.
    (OUT / "meshy_body_import.json").write_text(payload)
    render_views(obj, lo, hi)
    print("IMPORT_REPORT", json.dumps({"triangles": report["mesh"]["triangles"],
                                       "bounds": report["bounds_world_m"],
                                       "components": report["connected_components"],
                                       "sword": report["sword_geometry_present"]}), flush=True)


if __name__ == "__main__":
    main()
