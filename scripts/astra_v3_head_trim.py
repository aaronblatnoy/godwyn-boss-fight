"""Trim donor shoulder/chest skin while preserving the approved face, neck, and hair."""

import json
from pathlib import Path

import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_head_trim.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    skin = head.data.color_attributes["meshy_skin_mask"]
    before_faces = len(head.data.polygons)
    removed_centers = []
    for poly in head.data.polygons:
        skin_value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
        center = head.matrix_world @ poly.center
        trim_shoulder = center.z < 2.760 and not (-0.340 <= center.x <= -0.110)
        trim_chest = center.z < 2.620
        poly.select = skin_value >= 0.5 and (trim_shoulder or trim_chest)
        if poly.select:
            removed_centers.append(center[:])
    assert removed_centers, "No donor shoulder/chest faces selected"
    bpy.context.view_layer.objects.active = head
    head.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.delete(type="FACE")
    bpy.ops.object.mode_set(mode="OBJECT")
    head.data.update()
    after_faces = len(head.data.polygons)
    points = np.asarray(removed_centers, dtype=float)
    report = {
        "schema": "astra-v3-head-trim",
        "object": head.name,
        "before_faces": before_faces,
        "after_faces": after_faces,
        "removed_faces": before_faces - after_faces,
        "selection_rule": "skin mask >= 0.5 and ((world z < 2.760m outside neck x[-0.340,-0.110]m) or world z < 2.620m)",
        "removed_center_bounds_m": {"min": points.min(axis=0).tolist(), "max": points.max(axis=0).tolist()},
        "preserved": "face, central neck, and all non-skin hair geometry",
    }
    bpy.context.scene["astra_v3_head_trim"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_HEAD_TRIM_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
