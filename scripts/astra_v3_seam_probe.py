"""Report head, neck, body, and seam coordinates in local/world/rig spaces."""

import json
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_seam_probe.json"


def bounds(obj, matrix):
    points = np.asarray([(matrix @ vertex.co)[:] for vertex in obj.data.vertices], dtype=float)
    return {"min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist(), "median": np.median(points, axis=0).tolist()}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    result = {}
    for name in ("char1", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Astra_V3_SeamSleeve", "Astra_V3_Rigid_Neck_Bridge", "Astra_V3_Neck_Gorget_Trim"):
        obj = bpy.data.objects.get(name)
        if not obj:
            continue
        result[name] = {
            "matrix_world": [list(row) for row in obj.matrix_world],
            "parent": obj.parent.name if obj.parent else None,
            "local": bounds(obj, obj.matrix_local),
            "world": bounds(obj, obj.matrix_world),
            "rig_space": bounds(obj, rig.matrix_world.inverted() @ obj.matrix_world),
        }
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    skin = head.data.color_attributes.get("meshy_skin_mask")
    result["skin_attribute"] = {"domain": skin.domain, "data_type": skin.data_type, "length": len(skin.data)} if skin else None
    if skin:
        samples = []
        transform = rig.matrix_world.inverted() @ head.matrix_world
        for poly in head.data.polygons:
            value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
            if value >= 0.5:
                center = transform @ poly.center
                samples.append(center[:])
        points = np.asarray(samples, dtype=float)
        result["skin_face_centers_rig_space"] = {
            "min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist(), "median": np.median(points, axis=0).tolist(), "count": len(points)
        }
    parent = list(range(len(head.data.vertices)))
    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for edge in head.data.edges:
        union(*edge.vertices)
    components = {}
    for vertex in head.data.vertices:
        components.setdefault(find(vertex.index), []).append(vertex.index)
    component_rows = []
    for indices in components.values():
        points = np.asarray([(head.matrix_world @ head.data.vertices[index].co)[:] for index in indices], dtype=float)
        component_rows.append({"vertices": len(indices), "min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist()})
    result["connected_components"] = sorted(component_rows, key=lambda item: item["vertices"], reverse=True)[:40]
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("V3_SEAM_PROBE", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
