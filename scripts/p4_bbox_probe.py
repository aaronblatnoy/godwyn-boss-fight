"""
p4_bbox_probe.py — probe bbox of the newly exported godwyn_game.glb

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/p4_bbox_probe.py 2>&1
"""
import bpy, os
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
GLB  = f"{REPO}/models/godwyn_game.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scn = bpy.context.scene
bpy.context.view_layer.update()

arm    = next((o for o in scn.objects if o.type == "ARMATURE"), None)
meshes = [o for o in scn.objects if o.type == "MESH"]

print(f"\n[bbox] OBJECTS:")
for o in scn.objects:
    print(f"[bbox]   {o.name}  type={o.type}  loc={tuple(round(v,3) for v in o.location)}")

if arm:
    print(f"\n[bbox] ARMATURE location: {tuple(round(v,3) for v in arm.location)}")
    print(f"[bbox] ARMATURE scale: {tuple(round(v,3) for v in arm.scale)}")

for o in meshes:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xmin = min(p.x for p in pts); xmax = max(p.x for p in pts)
    ymin = min(p.y for p in pts); ymax = max(p.y for p in pts)
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    print(f"\n[bbox] MESH {o.name}:")
    print(f"[bbox]   loc={tuple(round(v,3) for v in o.location)}  scale={tuple(round(v,3) for v in o.scale)}")
    print(f"[bbox]   X: {xmin:.3f} to {xmax:.3f}  ({xmax-xmin:.3f})")
    print(f"[bbox]   Y: {ymin:.3f} to {ymax:.3f}  ({ymax-ymin:.3f})")
    print(f"[bbox]   Z: {zmin:.3f} to {zmax:.3f}  ({zmax-zmin:.3f})")

print("\n[bbox] DONE")
