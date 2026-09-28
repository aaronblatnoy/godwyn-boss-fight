"""Repair low garment islands incorrectly weighted to Head by the Meshy auto-rig."""

import json
from collections import Counter
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_fragment_repair.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    body = bpy.data.objects["char1"]
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
    all_indices = []
    for root, indices in components.items():
        points = np.asarray([(body.matrix_world @ body.data.vertices[index].co)[:] for index in indices], dtype=float)
        head_total = 0.0
        for index in indices:
            head_total += sum(group.weight for group in body.data.vertices[index].groups if group.group == head_index)
        mean_head = head_total / len(indices)
        if float(points[:, 2].max()) >= 1.30 or mean_head <= 0.50:
            continue
        for index in indices:
            vertex = body.data.vertices[index]
            for membership in list(vertex.groups):
                body.vertex_groups[membership.group].remove([index])
            hips.add([index], 1.0, "REPLACE")
        all_indices.extend(indices)
        repaired.append({
            "component_root": root, "vertices": len(indices), "mean_head_weight_before": mean_head,
            "rest_min_m": points.min(axis=0).tolist(), "rest_max_m": points.max(axis=0).tolist(),
            "replacement": "Hips=1.0",
        })
    assert repaired, "No low garment Head-weighted islands found"
    bounds = np.asarray([(body.matrix_world @ body.data.vertices[index].co)[:] for index in all_indices], dtype=float)
    report = {
        "schema": "astra-v3-fragment-repair",
        "selection": "connected body islands with rest max z < 1.30m and mean Head weight > 0.50",
        "reason": "rising_spin contact sheet revealed low garment trim following Head as a detached trail",
        "repaired_components": len(repaired), "repaired_vertices": len(all_indices),
        "combined_rest_bounds_m": {"min": bounds.min(axis=0).tolist(), "max": bounds.max(axis=0).tolist()},
        "repair": "rigid Hips weight, appropriate for disconnected lower-garment trim islands",
        "components": repaired,
    }
    bpy.context.scene["astra_v3_fragment_repair"] = json.dumps({key: value for key, value in report.items() if key != "components"})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_FRAGMENT_REPAIR_PASS", json.dumps({"components": len(repaired), "vertices": len(all_indices), "bounds": report["combined_rest_bounds_m"]}), flush=True)


if __name__ == "__main__":
    main()
