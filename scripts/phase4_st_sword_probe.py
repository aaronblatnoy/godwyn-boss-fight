"""
phase4_st_sword_probe.py — Probe godwyn_st_sword.blend.
Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_st_sword_probe.py 2>&1
"""
import bpy, os

REPO  = os.path.expanduser("~/godwyn-boss-fight")
BLEND = f"{REPO}/models/godwyn_st_sword.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene

arm   = next((o for o in scn.objects if o.type == 'ARMATURE'), None)
meshes = [o for o in scn.objects if o.type == 'MESH']
print("=== st_sword.blend probe ===")
print(f"Armature: {arm.name if arm else None}  bones={len(arm.data.bones) if arm else 0}")
print(f"All meshes: {[o.name for o in meshes]}")
for m in meshes:
    print(f"  {m.name}: verts={len(m.data.vertices)} vgroups={len(m.vertex_groups)} parent={m.parent.name if m.parent else None} parent_type={m.parent_type} parent_bone={m.parent_bone}")
mats = [m.name for m in bpy.data.materials]
print(f"Materials: {mats}")
imgs = [i.name for i in bpy.data.images]
print(f"Images: {imgs}")
print("=== probe done ===")
