"""Remove residual non-plate/non-cloth Meshy head shell inside the head volume."""

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_body_head_cleanup.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main():
    args = cli()
    blend = root_path(args.blend)
    output = root_path(args.out)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    body = bpy.data.objects["char1"]
    plate = body.data.color_attributes["astra_v3_plate_mask"]
    cloth = body.data.color_attributes["astra_v3_cloth_mask"]
    selected = []
    selected_indices = []
    before_faces = len(body.data.polygons)
    for poly in body.data.polygons:
        center = body.matrix_world @ poly.center
        plate_value = float(np.mean([plate.data[index].color[0] for index in poly.loop_indices]))
        cloth_value = float(np.mean([cloth.data[index].color[0] for index in poly.loop_indices]))
        in_head_volume = center.z >= 2.640 and abs(center.x) <= 0.340 and -0.570 <= center.y <= 0.080
        poly.select = in_head_volume and plate_value < 0.5 and cloth_value < 0.5
        if poly.select:
            selected.append((tuple(center), plate_value, cloth_value))
            selected_indices.append(poly.index)
    assert selected, "No residual body head-shell faces selected"
    assert all(row[1] < 0.5 for row in selected), "Plate face selected"
    assert all(row[2] < 0.5 for row in selected), "Cloth face selected"
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    doomed = [bm.faces[index] for index in selected_indices]
    bmesh.ops.delete(bm, geom=doomed, context="FACES")
    orphaned = [vertex for vertex in bm.verts if not vertex.link_faces]
    if orphaned:
        bmesh.ops.delete(bm, geom=orphaned, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    assert len(body.data.polygons) == before_faces - len(selected_indices)
    assert len(body.data.polygons) > before_faces - 10000, "Cleanup scope unexpectedly broad"
    points = np.asarray([row[0] for row in selected], dtype=float)
    report = {
        "schema": "astra-v3fists-body-head-cleanup",
        "object": body.name,
        "before_faces": before_faces,
        "after_faces": len(body.data.polygons),
        "removed_faces": before_faces - len(body.data.polygons),
        "selection": "rest face center z>=2.640m, |x|<=0.340m, y[-0.570,0.080]m, plate mask<0.5, cloth mask<0.5",
        "removed_class": "residual original Meshy head/neck skin-hair-lining shell",
        "plate_faces_removed": 0,
        "cloth_faces_removed": 0,
        "removed_center_bounds_m": {"min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist()},
    }
    bpy.context.scene["astra_v3fists_body_head_cleanup"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_BODY_HEAD_CLEANUP_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
