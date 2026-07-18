"""Probe models/godwyn_head_target.glb: bbox, orientation, mesh stats.

Also probes the CURRENT body head region in godwyn_phase1.blend for
alignment landmarks (eye centres stored as custom props, lip centre).

Run: blender --background --python scripts/p4_probe_head_target.py
"""
import os
import sys

import bpy
from mathutils import Vector

_REPO = os.path.expanduser("~/godwyn-boss-fight")

# --- part 1: fresh scene, import the GLB --------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
glb = os.path.join(_REPO, "models", "godwyn_head_target.glb")
assert os.path.isfile(glb), glb
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
print(f"[probe] imported objects: {[o.name for o in bpy.data.objects]}")
for m in meshes:
    bpy.context.view_layer.update()
    mw = m.matrix_world
    cos = [mw @ v.co for v in m.data.vertices]
    xs = [c.x for c in cos]; ys = [c.y for c in cos]; zs = [c.z for c in cos]
    print(f"[probe] {m.name}: verts={len(cos)} faces={len(m.data.polygons)}")
    print(f"[probe]   x [{min(xs):.4f}, {max(xs):.4f}]")
    print(f"[probe]   y [{min(ys):.4f}, {max(ys):.4f}]")
    print(f"[probe]   z [{min(zs):.4f}, {max(zs):.4f}]")
    # front-direction guess: nose is the most protruding point near mid-x
    mid_x = (min(xs) + max(xs)) / 2
    near_mid = [c for c in cos if abs(c.x - mid_x) < (max(xs)-min(xs))*0.05]
    if near_mid:
        ymin_pt = min(near_mid, key=lambda c: c.y)
        ymax_pt = max(near_mid, key=lambda c: c.y)
        zmax_pt = max(near_mid, key=lambda c: c.z)
        print(f"[probe]   mid-x extremes: y-min {tuple(round(t,4) for t in ymin_pt)} "
              f"y-max {tuple(round(t,4) for t in ymax_pt)} "
              f"z-max {tuple(round(t,4) for t in zmax_pt)}")
    # materials / textures
    print(f"[probe]   materials: {[ms.material.name if ms.material else None for ms in m.material_slots]}")
print(f"[probe] images: {[(i.name, tuple(i.size)) for i in bpy.data.images]}")

# --- part 2: open the blend, dump head landmarks -------------------------
blend = os.path.join(_REPO, "models", "godwyn_phase1.blend")
if os.path.isfile(blend):
    bpy.ops.wm.open_mainfile(filepath=blend)
    body = bpy.data.objects.get("Godwyn_Body")
    if body:
        print(f"[probe] body custom props: "
              f"{ {k: list(v) if hasattr(v, '__len__') else v for k, v in body.items()} }")
        me = body.data
        head_cos = [v.co for v in me.vertices if v.co.z > 2.75]
        if head_cos:
            xs = [c.x for c in head_cos]; ys = [c.y for c in head_cos]
            zs = [c.z for c in head_cos]
            print(f"[probe] body head region (z>2.75): {len(head_cos)} verts")
            print(f"[probe]   x [{min(xs):.4f}, {max(xs):.4f}]")
            print(f"[probe]   y [{min(ys):.4f}, {max(ys):.4f}]")
            print(f"[probe]   z [{min(zs):.4f}, {max(zs):.4f}]")
    eyes = bpy.data.objects.get("Godwyn_Eyes")
    if eyes:
        mw = eyes.matrix_world
        cos = [mw @ v.co for v in eyes.data.vertices]
        left = [c for c in cos if c.x > 0]; right = [c for c in cos if c.x < 0]
        if left and right:
            cl = sum(left, Vector()) / len(left)
            cr = sum(right, Vector()) / len(right)
            print(f"[probe] eye centres L={tuple(round(t,4) for t in cl)} "
                  f"R={tuple(round(t,4) for t in cr)}")
print("[probe] done")
