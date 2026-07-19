"""
p4_robe_blend_probe2.py — deeper probe of godwyn_p2_robe.blend to
understand coordinate system, armature scale, and LeftHand bone pose.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/p4_robe_blend_probe2.py 2>&1
"""
import bpy, os
from mathutils import Vector

REPO  = os.path.expanduser("~/godwyn-boss-fight")
BLEND = f"{REPO}/models/godwyn_p2_robe.blend"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene
bpy.context.view_layer.update()

arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
char1 = bpy.data.objects.get("char1")

print(f"\n[probe] armature location={arm.location[:]}")
print(f"[probe] armature scale={arm.scale[:]}")
print(f"[probe] armature rotation={arm.rotation_euler[:]}")

print(f"\n[probe] char1 location={char1.location[:]}")
print(f"[probe] char1 scale={char1.scale[:]}")

# What does char1 bbox look like in world space?
pts = [char1.matrix_world @ Vector(c) for c in char1.bound_box]
zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
xmin = min(p.x for p in pts); xmax = max(p.x for p in pts)
print(f"\n[probe] char1 world bbox:")
print(f"[probe]   X: {xmin:.3f} to {xmax:.3f}")
print(f"[probe]   Z: {zmin:.3f} to {zmax:.3f}  H={zmax-zmin:.3f}")

# Check scene unit settings
print(f"\n[probe] scene units: system={scn.unit_settings.system}  scale_length={scn.unit_settings.scale_length}")

# Check LeftHand bone world position
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
lh = arm.pose.bones.get("LeftHand")
if lh:
    # pose matrix in world space
    wm = arm.matrix_world @ lh.matrix
    print(f"\n[probe] LeftHand world pos = {tuple(wm.translation)}")
    print(f"[probe] LeftHand bone matrix (pose):\n{lh.matrix}")
bpy.ops.object.mode_set(mode='OBJECT')

# Check face blend for comparison
bpy.ops.wm.open_mainfile(filepath=f"{REPO}/models/godwyn_face.blend")
scn2 = bpy.context.scene
bpy.context.view_layer.update()
arm2 = next((o for o in scn2.objects if o.type == "ARMATURE"), None)
char2 = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")

print(f"\n[probe] FACE BLEND:")
print(f"[probe]   armature scale={arm2.scale[:]}")
print(f"[probe]   char1 scale={char2.scale[:]}")
if sword:
    print(f"[probe]   sword location={sword.location[:]}")
    print(f"[probe]   sword parent={sword.parent.name if sword.parent else None}  parent_bone={sword.parent_bone}")
    print(f"[probe]   sword parent_inverse:\n{sword.matrix_parent_inverse}")
    pts = [sword.matrix_world @ Vector(c) for c in sword.bound_box]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    print(f"[probe]   sword world Z: {zmin:.3f} to {zmax:.3f}")

bpy.context.view_layer.objects.active = arm2
bpy.ops.object.mode_set(mode='POSE')
lh2 = arm2.pose.bones.get("LeftHand")
if lh2:
    wm2 = arm2.matrix_world @ lh2.matrix
    print(f"[probe]   face LeftHand world pos = {tuple(wm2.translation)}")
bpy.ops.object.mode_set(mode='OBJECT')

print("\n[probe] DONE")
