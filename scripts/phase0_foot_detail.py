"""
Phase 0 - Foot bone orientation detail probe
"""
import bpy
import os
import math

glb_path = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=glb_path)

arm_obj = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm = arm_obj.data

print("=" * 60)
print("FOOT/TOE BONE ORIENTATION DETAIL")
print("=" * 60)

foot_keywords = ['foot', 'toe', 'ankle', 'heel']
for b in arm.bones:
    if any(kw in b.name.lower() for kw in foot_keywords):
        head = b.head_local
        tail = b.tail_local
        dir_vec = (tail[0]-head[0], tail[1]-head[1], tail[2]-head[2])
        length = math.sqrt(sum(x*x for x in dir_vec))
        dir_norm = tuple(x/length for x in dir_vec) if length > 0 else (0,0,0)

        # Matrix columns tell us the bone's local axes
        mat = b.matrix_local
        x_axis = (mat[0][0], mat[1][0], mat[2][0])
        y_axis = (mat[0][1], mat[1][1], mat[2][1])  # bone's own Y (along length)
        z_axis = (mat[0][2], mat[1][2], mat[2][2])

        print(f"\nBone: {b.name}")
        print(f"  head_local: {tuple(round(x,4) for x in head)}")
        print(f"  tail_local: {tuple(round(x,4) for x in tail)}")
        print(f"  length: {length:.4f}")
        print(f"  dir (head->tail normalized): {tuple(round(x,3) for x in dir_norm)}")
        print(f"  bone Y-axis (long axis): {tuple(round(x,3) for x in y_axis)}")
        # Compute angle of toe from forward direction (assuming Y is forward in world)
        # If toe X component is large, it's splayed outward
        dx, dy, dz = dir_norm
        splay_angle = math.degrees(math.atan2(abs(dx), abs(dy))) if abs(dy) > 0.001 else 90.0
        print(f"  Splay angle from forward (Y-axis): {splay_angle:.1f} deg (0=pointing fwd, 90=pointing sideways)")

print("\n[ALL 121 BONES LISTING]")
for b in arm.bones:
    parent_name = b.parent.name if b.parent else "ROOT"
    head = b.head_local
    print(f"  {b.name:<40} parent={parent_name:<40} head=({head[0]:.3f},{head[1]:.3f},{head[2]:.3f})")

print("\nDONE")
