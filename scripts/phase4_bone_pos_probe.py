"""
phase4_bone_pos_probe.py — Find RightHand bone world position from godwyn_game.glb
Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_bone_pos_probe.py 2>&1
"""
import bpy, os
from mathutils import Vector

REPO   = os.path.expanduser("~/godwyn-boss-fight")
OUTGLB = f"{REPO}/models/godwyn_game.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUTGLB)
bpy.context.view_layer.update()

arm = next((o for o in bpy.context.scene.objects if o.type == 'ARMATURE'), None)
char1 = bpy.data.objects.get('char1')
sword = bpy.data.objects.get('Godwyn_Sword')

print("=== bone positions (world space) ===")
key_bones = ['RightHand', 'RightForeArm', 'RightArm', 'Hips', 'Spine', 'Head', 'LeftHand', 'LeftFoot', 'RightFoot']
for bn in key_bones:
    if bn in arm.data.bones:
        b = arm.data.bones[bn]
        whead = arm.matrix_world @ b.head_local
        wtail = arm.matrix_world @ b.tail_local
        print(f"  {bn}: head={tuple(round(v,3) for v in whead)}  tail={tuple(round(v,3) for v in wtail)}")

if sword:
    bpy.context.view_layer.update()
    swpts = [sword.matrix_world @ Vector(c) for c in sword.bound_box]
    smin = Vector((min(p.x for p in swpts), min(p.y for p in swpts), min(p.z for p in swpts)))
    smax = Vector((max(p.x for p in swpts), max(p.y for p in swpts), max(p.z for p in swpts)))
    sctr = (smin + smax) / 2
    print(f"\nGodwyn_Sword world bbox:")
    print(f"  min={tuple(round(v,3) for v in smin)}")
    print(f"  max={tuple(round(v,3) for v in smax)}")
    print(f"  center={tuple(round(v,3) for v in sctr)}")

c1pts  = [char1.matrix_world @ Vector(c) for c in char1.bound_box]
bbmin  = Vector((min(p.x for p in c1pts), min(p.y for p in c1pts), min(p.z for p in c1pts)))
bbmax  = Vector((max(p.x for p in c1pts), max(p.y for p in c1pts), max(p.z for p in c1pts)))
H = bbmax.z - bbmin.z
ctr = (bbmin + bbmax) / 2
print(f"\nchar1 bbox: H={H:.3f} center={tuple(round(v,3) for v in ctr)}")
print("=== done ===")
