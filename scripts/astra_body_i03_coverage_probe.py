"""Probe every final visible mesh near the head_end midpoint on black-sky."""
import bpy
import json
from pathlib import Path
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2/meshy_body_i03_head_end_probe.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / "models/astra_character_v2_body_i02.blend"))
    rig = bpy.data.objects["Armature"]
    point = rig.matrix_world @ rig.data.bones["head_end"].head_local
    rows = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render or not obj.data.polygons:
            continue
        coords = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
        hit = BVHTree.FromPolygons(coords, polygons, all_triangles=False).find_nearest(point)
        rows.append({"object": obj.name, "distance_m": float(hit[3]),
                     "nearest_world_m": list(hit[0]), "normal": list(hit[1])})
    rows.sort(key=lambda row: row["distance_m"])
    OUT.write_text(json.dumps({"head_end_world_m": list(point), "meshes": rows}, indent=2) + "\n")
    print("BODY_I03_HEAD_END_PROBE", json.dumps(rows[:12]), flush=True)


if __name__ == "__main__":
    main()
