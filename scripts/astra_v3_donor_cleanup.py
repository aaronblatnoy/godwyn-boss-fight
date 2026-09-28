"""Remove residual donor shoulder skin outside the fitted neck ellipse."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_donor_cleanup.json")
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
    skin = head.data.color_attributes["meshy_skin_mask"]
    removed = []
    before_faces = len(head.data.polygons)
    for poly in head.data.polygons:
        skin_value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
        center = head.matrix_world @ poly.center
        ellipse = ((center.x - cx) / 0.120) ** 2 + ((center.y - cy) / 0.105) ** 2
        poly.select = skin_value >= 0.5 and center.z < 2.760 and ellipse > 1.0
        if poly.select:
            removed.append(tuple(center))
    assert removed, "No residual donor shoulder faces selected"
    bpy.context.view_layer.objects.active = head
    head.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    head.data.update()
    points = np.asarray(removed, dtype=float)
    report = {
        "schema": "astra-v3fists-donor-cleanup",
        "object": head.name,
        "before_faces": before_faces,
        "after_faces": len(head.data.polygons),
        "removed_faces": before_faces - len(head.data.polygons),
        "removed_class": "skin only (meshy_skin_mask >= 0.5)",
        "rule": "world z < 2.760m and outside fitted neck ellipse x radius 0.120m/y radius 0.105m",
        "neck_center_xy_m": [cx, cy],
        "removed_center_bounds_m": {"min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist()},
        "skin_mask_attribute_survived": head.data.color_attributes.get("meshy_skin_mask") is not None,
    }
    bpy.context.scene["astra_v3fists_donor_cleanup"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_DONOR_CLEANUP_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
