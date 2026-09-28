"""Remove disconnected low donor shoulder components outside the fitted neck."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import bmesh
import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_donor_component_cleanup.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main():
    args = cli()
    blend = root_path(args.blend)
    output = root_path(args.out)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    metadata = json.loads(bpy.context.scene["astra_v3"])
    cx, cy = metadata["head_fit"]["target_seam_center_xy_m"]
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
    hair = head.data.color_attributes["meshy_hair_mask"]
    selected_components = []
    selected_faces = []
    for root, polys in faces.items():
        ids = {index for poly in polys for index in poly.vertices}
        points = np.asarray([(head.matrix_world @ head.data.vertices[index].co)[:] for index in ids])
        centroid = points.mean(axis=0)
        mean_hair = float(np.mean([
            np.mean([hair.data[index].color[0] for index in poly.loop_indices]) for poly in polys
        ]))
        ellipse = ((centroid[0] - cx) / 0.130) ** 2 + ((centroid[1] - cy) / 0.120) ** 2
        if float(points[:, 2].max()) < 2.830 and mean_hair < 0.5 and ellipse > 1.0:
            selected_faces.extend(poly.index for poly in polys)
            selected_components.append({
                "root": root, "vertices": len(ids), "faces": len(polys),
                "bounds_min_m": points.min(axis=0).tolist(), "bounds_max_m": points.max(axis=0).tolist(),
                "centroid_m": centroid.tolist(), "neck_ellipse_value": float(ellipse), "mean_hair": mean_hair,
            })
    assert selected_components
    before_faces = len(head.data.polygons)
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[index] for index in selected_faces], context="FACES")
    orphaned = [vertex for vertex in bm.verts if not vertex.link_faces]
    if orphaned:
        bmesh.ops.delete(bm, geom=orphaned, context="VERTS")
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    assert len(head.data.polygons) == before_faces - len(selected_faces)
    assert head.data.color_attributes.get("meshy_skin_mask") is not None
    assert head.data.color_attributes.get("meshy_hair_mask") is not None
    report = {
        "schema": "astra-v3fists-donor-component-cleanup",
        "selection": "disconnected component max z<2.830m, mean hair mask<0.5, centroid outside fitted neck ellipse x0.130m/y0.120m",
        "neck_center_xy_m": [cx, cy],
        "before_faces": before_faces, "after_faces": len(head.data.polygons),
        "removed_faces": len(selected_faces), "removed_components": len(selected_components),
        "components": selected_components,
        "preserved": "main connected face/neck and every hair-classified component",
    }
    bpy.context.scene["astra_v3fists_donor_component_cleanup"] = json.dumps({key: value for key, value in report.items() if key != "components"})
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_DONOR_COMPONENT_CLEANUP_PASS", json.dumps({"components": len(selected_components), "faces": len(selected_faces)}), flush=True)


if __name__ == "__main__":
    main()
