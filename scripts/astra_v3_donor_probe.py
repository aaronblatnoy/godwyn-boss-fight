"""Report donor head/hair connected components near the shoulder line."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_donor_probe.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main():
    args = cli()
    bpy.ops.wm.open_mainfile(filepath=str(root_path(args.blend)), load_ui=False)
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
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
    faces = defaultdict(list)
    for poly in head.data.polygons:
        faces[find(poly.vertices[0])].append(poly)
    skin = head.data.color_attributes["meshy_skin_mask"]
    hair = head.data.color_attributes["meshy_hair_mask"]
    rows = []
    for root, polys in faces.items():
        ids = {index for poly in polys for index in poly.vertices}
        points = np.asarray([(head.matrix_world @ head.data.vertices[index].co)[:] for index in ids])
        skin_values = [float(np.mean([skin.data[index].color[0] for index in poly.loop_indices])) for poly in polys]
        hair_values = [float(np.mean([hair.data[index].color[0] for index in poly.loop_indices])) for poly in polys]
        rows.append({
            "root": root, "vertices": len(ids), "faces": len(polys),
            "bounds_min_m": points.min(axis=0).tolist(), "bounds_max_m": points.max(axis=0).tolist(),
            "mean_skin": float(np.mean(skin_values)), "mean_hair": float(np.mean(hair_values)),
            "skin_faces_ge_0_5": sum(value >= 0.5 for value in skin_values),
            "hair_faces_ge_0_5": sum(value >= 0.5 for value in hair_values),
        })
    rows.sort(key=lambda row: (row["bounds_min_m"][2], -row["vertices"]))
    report = {"schema": "astra-v3fists-donor-probe", "components": len(rows), "rows": rows}
    output = root_path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_DONOR_PROBE_PASS", json.dumps({"components": len(rows), "low": [row for row in rows if row["bounds_min_m"][2] < 2.80][:20]}), flush=True)


if __name__ == "__main__":
    main()
