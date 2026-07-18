"""
phase4_st_feet_probe.py — Probe godwyn_st_feet.blend to see what's in it.
Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_st_feet_probe.py 2>&1
"""
import bpy, os

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = f"{REPO}/models/godwyn_st_feet.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene

arm   = next((o for o in scn.objects if o.type == 'ARMATURE'), None)
char1 = bpy.data.objects.get('char1')
sword = bpy.data.objects.get('Godwyn_Sword')
gaunt = bpy.data.objects.get('Godwyn_Gauntlet')

print("=== st_feet.blend probe ===")
print(f"Armature: {arm.name if arm else None}  bones={len(arm.data.bones) if arm else 0}")
print(f"char1: {char1.name if char1 else None}  vgroups={len(char1.vertex_groups) if char1 else 0}")
print(f"Godwyn_Sword: {sword}")
print(f"Godwyn_Gauntlet: {gaunt}")

meshes = [o for o in scn.objects if o.type == 'MESH']
print(f"All meshes: {[o.name for o in meshes]}")

mats = [m.name for m in bpy.data.materials]
print(f"Materials: {mats}")

imgs = [i.name for i in bpy.data.images]
print(f"Images: {imgs}")

if arm:
    bones = [b.name for b in arm.data.bones]
    chain_bones = [b for b in bones if any(b.startswith(p) for p in ('phys_', 'robe_', 'cape_', 'hair_', 'cloth_'))]
    mixamo_bones = [b for b in bones if not any(b.startswith(p) for p in ('phys_', 'robe_', 'cape_', 'hair_', 'cloth_'))]
    print(f"Total bones: {len(bones)} (chains: {len(chain_bones)}, mixamo: {len(mixamo_bones)})")
    print(f"Mixamo bones: {mixamo_bones}")

# Check foot bone directions (feet fix verification)
if arm:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    import math
    from mathutils import Vector
    for side in ('Left', 'Right'):
        tbn = side + 'ToeBase'
        if tbn in arm.pose.bones:
            pb = arm.pose.bones[tbn]
            d = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head)
            d.z = 0.0
            if d.length > 0:
                d = d.normalized()
                ang = math.degrees(math.atan2(d.x, -d.y))
                print(f"{tbn}: world XY dir=({d.x:.3f},{d.y:.3f})  splay={ang:.1f}deg")
    bpy.ops.object.mode_set(mode='OBJECT')

print("=== probe done ===")
