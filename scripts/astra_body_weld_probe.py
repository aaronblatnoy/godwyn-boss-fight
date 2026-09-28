"""Probe safe near-coincident weld tolerances for Meshy body i02 on black-sky."""
import bpy
import bmesh
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "models/meshy_body_godA_hairback.glb"
OUT = ROOT / "renders/astra/char2/meshy_body_i02_weld_probe.json"


def component_sizes(mesh):
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = bytearray(len(mesh.vertices))
    sizes = []
    for seed in range(len(mesh.vertices)):
        if seen[seed]:
            continue
        seen[seed] = 1
        stack = [seed]
        size = 0
        while stack:
            current = stack.pop()
            size += 1
            for other in adjacency[current]:
                if not seen[other]:
                    seen[other] = 1
                    stack.append(other)
        sizes.append(size)
    sizes.sort(reverse=True)
    return sizes


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    tolerances = [float(value) for value in args] or [0.00025]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
    report = {}
    for tolerance in tolerances:
        mesh = source.data.copy()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        before = len(bm.verts)
        result = bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=tolerance)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        sizes = component_sizes(mesh)
        report[f"{tolerance:.8f}"] = {
            "vertices_before": before,
            "vertices_after": len(mesh.vertices),
            "vertices_merged": before - len(mesh.vertices),
            "components": len(sizes),
            "components_ge_200_vertices": sum(size >= 200 for size in sizes),
            "vertices_in_components_ge_200": sum(size for size in sizes if size >= 200),
            "largest_component_sizes": sizes[:40],
        }
        bpy.data.meshes.remove(mesh)
        print("BODY_WELD_PROBE", tolerance, json.dumps(report[f"{tolerance:.8f}"]), flush=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
