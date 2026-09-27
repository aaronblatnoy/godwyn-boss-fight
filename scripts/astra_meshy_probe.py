"""Inspect the Meshy GLB and the untouched pre-likeness character on black-sky."""
import bpy
import json
import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
BASE = ROOT / "models/astra_character_v2_pre_likeness.blend"
GLB = ROOT / "models/meshy_head_approved.glb"


def bounds(ob):
    p = np.array([ob.matrix_world @ v.co for v in ob.data.vertices], float)
    return {"min": p.min(0).tolist(), "max": p.max(0).tolist(), "size": np.ptp(p, axis=0).tolist()}


def material_inventory(mat):
    images = []
    nodes = []
    if mat and mat.use_nodes:
        for node in mat.node_tree.nodes:
            nodes.append({"name": node.name, "type": node.bl_idname})
            if node.type == "TEX_IMAGE" and node.image:
                im = node.image
                images.append({"node": node.name, "name": im.name, "size": list(im.size),
                               "source": im.source, "filepath": im.filepath})
    return {"name": mat.name if mat else None, "nodes": nodes, "images": images}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    arm = bpy.data.objects["Armature"]
    base = {
        "bones": len(arm.data.bones),
        "actions": len(bpy.data.actions),
        "objects": [{"name": o.name, "type": o.type, "hidden": bool(o.hide_render),
                     "vertices": len(o.data.vertices) if o.type == "MESH" else None,
                     "faces": len(o.data.polygons) if o.type == "MESH" else None}
                    for o in bpy.context.scene.objects],
    }
    for name in ["AstraChar2_Mpfb_Head", "AstraChar2_Eyeball_L", "AstraChar2_Eyeball_R", "char1"]:
        ob = bpy.data.objects.get(name)
        if ob and ob.type == "MESH":
            base.setdefault("bounds", {})[name] = bounds(ob)
    for side in ("L", "R"):
        ob = bpy.data.objects.get("AstraChar2_Eyeball_" + side)
        if ob:
            b = bounds(ob)
            base.setdefault("eye_centers", {})[side] = ((np.array(b["min"]) + np.array(b["max"])) * .5).tolist()
    head = bpy.data.objects.get("AstraChar2_Mpfb_Head")
    if head:
        p = np.array([head.matrix_world @ v.co for v in head.data.vertices], float)
        base["mpfb_landmark_proxies"] = {
            "chin_z": float(np.quantile(p[:, 2], .05)),
            "crown_z": float(p[:, 2].max()),
            "ear_width_x": float(np.quantile(p[:, 0], .995) - np.quantile(p[:, 0], .005)),
            "neck_cut_z": 2.745,
            "neck_base_z": 2.605,
        }
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(GLB))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    imported = {
        "file": str(GLB.relative_to(ROOT)),
        "mesh_count": len(meshes),
        "objects": [],
        "triangles": 0,
        "materials": [],
        "images": [{"name": im.name, "size": list(im.size), "source": im.source,
                    "filepath": im.filepath} for im in bpy.data.images],
    }
    for ob in meshes:
        tri = sum(max(0, len(p.vertices) - 2) for p in ob.data.polygons)
        imported["triangles"] += tri
        imported["objects"].append({"name": ob.name, "vertices": len(ob.data.vertices),
                                    "faces": len(ob.data.polygons), "triangles": tri,
                                    "bounds": bounds(ob), "material_slots": [m.name if m else None for m in ob.data.materials]})
    imported["materials"] = [material_inventory(m) for m in bpy.data.materials]
    report = {"base": base, "meshy": imported}
    (OUT / "meshy_probe.json").write_text(json.dumps(report, indent=2) + "\n")
    print("MESHY_PROBE_DONE", json.dumps({"base_bones": base["bones"], "meshy": imported["objects"]}), flush=True)


if __name__ == "__main__":
    main()
