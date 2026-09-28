"""Find disconnected body islands that separate from the character during rising_spin."""

import json
from collections import Counter
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_fragment_probe.json"


def assign(rig, action_name, frame):
    action = bpy.data.actions[action_name]
    animation = rig.animation_data_create()
    animation.action = action
    animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    body = bpy.data.objects["char1"]
    assign(rig, "Godwyn_V3_rising_spin", 40)
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
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    posed = np.asarray([(evaluated.matrix_world @ vertex.co)[:] for vertex in mesh.vertices], dtype=float)
    rest = np.asarray([(body.matrix_world @ vertex.co)[:] for vertex in body.data.vertices], dtype=float)
    hips = np.asarray((rig.matrix_world @ rig.pose.bones["Hips"].head)[:], dtype=float)
    rows = []
    for root, indices in components.items():
        p = posed[indices]
        r = rest[indices]
        displacement = p - r
        weights = Counter()
        for index in indices:
            for group in body.data.vertices[index].groups:
                weights[body.vertex_groups[group.group].name] += group.weight
        total = sum(weights.values()) or 1.0
        rows.append({
            "component_root": root,
            "vertices": len(indices),
            "indices": indices if len(indices) <= 5000 else [],
            "rest_min": r.min(axis=0).tolist(), "rest_max": r.max(axis=0).tolist(),
            "posed_min": p.min(axis=0).tolist(), "posed_max": p.max(axis=0).tolist(),
            "posed_centroid": p.mean(axis=0).tolist(),
            "centroid_distance_from_hips_m": float(np.linalg.norm(p.mean(axis=0) - hips)),
            "mean_displacement_m": displacement.mean(axis=0).tolist(),
            "top_groups": [{"name": name, "mean_weight": value / len(indices), "share": value / total} for name, value in weights.most_common(8)],
        })
    suspects = [row for row in rows if row["posed_min"][0] < hips[0] - 1.10 or row["centroid_distance_from_hips_m"] > 2.75]
    report = {
        "schema": "astra-v3-fragment-probe",
        "action": "Godwyn_V3_rising_spin", "frame": 40,
        "hips_world_m": hips.tolist(), "components": len(rows),
        "suspects": sorted(suspects, key=lambda row: row["posed_min"][0]),
        "extreme_components": sorted(rows, key=lambda row: row["centroid_distance_from_hips_m"], reverse=True)[:30],
    }
    evaluated.to_mesh_clear()
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_FRAGMENT_PROBE", json.dumps({"components": len(rows), "suspects": len(suspects), "suspect_roots": [row["component_root"] for row in report["suspects"]]}), flush=True)


if __name__ == "__main__":
    main()
