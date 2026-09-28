"""Trim donor neck/hair ends that sit inside the V3 gorget."""

import json
from pathlib import Path

import bmesh
import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_wip.blend"
OUT = ROOT / "renders/astra/char2/astra_v3m_trim_head.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    head = bpy.data.objects["AstraChar2_Meshy_HeadHair"]
    hair = head.data.color_attributes["meshy_hair_mask"]
    skin = head.data.color_attributes["meshy_skin_mask"]
    doomed = []
    classes = {"hair_below_2.73m": 0, "non_hair_below_2.71m": 0}
    for poly in head.data.polygons:
        center = head.matrix_world @ poly.center
        hair_value = float(np.mean([hair.data[index].color[0] for index in poly.loop_indices]))
        skin_value = float(np.mean([skin.data[index].color[0] for index in poly.loop_indices]))
        label = None
        if hair_value >= 0.5 and center.z < 2.73:
            label = "hair_below_2.73m"
        elif hair_value < 0.5 and center.z < 2.71:
            label = "non_hair_below_2.71m"
        if label:
            doomed.append(poly.index)
            classes[label] += 1
    assert doomed
    before = {"vertices": len(head.data.vertices), "faces": len(head.data.polygons)}
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[index] for index in doomed], context="FACES")
    orphan = [vertex for vertex in bm.verts if not vertex.link_faces]
    if orphan:
        bmesh.ops.delete(bm, geom=orphan, context="VERTS")
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    after = {"vertices": len(head.data.vertices), "faces": len(head.data.polygons)}
    report = {
        "schema": "astra-v3m-hidden-gorget-trim",
        "selection": "hair-mask faces below rest world z=2.73 m and all non-hair donor faces below z=2.71 m",
        "reason": "remove only donor neck and hair ends buried inside the closed gorget; NeckBlend owns the hidden collar interior",
        "before": before, "after": after,
        "removed_faces": len(doomed), "removed_orphan_vertices": len(orphan),
        "classes": classes,
    }
    bpy.context.scene["astra_v3m_trim_head"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_TRIM_HEAD_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
