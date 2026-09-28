"""Remove residual source-head shell without touching torso-driven armor."""

import json
from pathlib import Path

import bmesh
import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_wip.blend"
OUT = ROOT / "renders/astra/char2/astra_v3m_cleanup.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    body = bpy.data.objects["char1"]
    plate = body.data.color_attributes["astra_v3_plate_mask"]
    names = {group.index: group.name for group in body.vertex_groups}
    head_bones = {"Head", "head_end", "headfront"}
    doomed = []
    samples = []
    for poly in body.data.polygons:
        coords = [body.matrix_world @ body.data.vertices[index].co for index in poly.vertices]
        center = sum(coords, coords[0].copy() * 0.0) / len(coords)
        head_weight = float(np.mean([
            sum(item.weight for item in body.data.vertices[index].groups if names.get(item.group) in head_bones)
            for index in poly.vertices
        ]))
        plate_value = float(np.mean([plate.data[index].color[0] for index in poly.loop_indices]))
        if center.z > 2.46 and head_weight >= 0.50:
            doomed.append(poly.index)
            if len(samples) < 100:
                samples.append({"poly": poly.index, "center_world_m": list(center), "head_weight": head_weight, "plate_mask": plate_value})
    assert doomed, "No residual Head-weighted source shell found"
    before = {"vertices": len(body.data.vertices), "faces": len(body.data.polygons)}
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[index] for index in doomed], context="FACES")
    orphan = [vertex for vertex in bm.verts if not vertex.link_faces]
    if orphan:
        bmesh.ops.delete(bm, geom=orphan, context="VERTS")
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    after = {"vertices": len(body.data.vertices), "faces": len(body.data.polygons)}
    report = {
        "schema": "astra-v3m-residual-head-shell-cleanup",
        "selection": "body faces above z=2.46 m with mean weight >=0.50 to Head/head_end/headfront",
        "reason": "source-head remnants move rigidly with the Head bone and were falsely plate-classified by metallic texture; they are not torso/shoulder-driven gorget or pauldron geometry",
        "before": before,
        "after": after,
        "removed_faces": len(doomed),
        "removed_orphan_vertices": len(orphan),
        "samples": samples,
    }
    bpy.context.scene["astra_v3m_cleanup"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_CLEANUP_PASS", json.dumps({key: report[key] for key in ("before", "after", "removed_faces", "removed_orphan_vertices")}), flush=True)


if __name__ == "__main__":
    main()
