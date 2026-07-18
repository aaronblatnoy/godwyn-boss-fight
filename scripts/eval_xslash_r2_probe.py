"""eval_xslash_r2_probe.py — numeric tip-path check of the baked X-slash blend."""
import bpy, os
from mathutils import Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_xslash.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
sword = bpy.data.objects["Godwyn_Sword"]
bb = [Vector(c) for c in sword.bound_box]
zmin = min(c.z for c in bb); zmax = max(c.z for c in bb)
cx = sum(c.x for c in bb) / 8.0; cy = sum(c.y for c in bb) / 8.0
TIP = Vector((cx, cy, zmax)); GRIP = Vector((cx, cy, zmin))
dg = bpy.context.evaluated_depsgraph_get()
path = {}
for f in range(1, 65):
    sc.frame_set(f); dg.update()
    sw = sword.evaluated_get(dg)
    t = sw.matrix_world @ TIP; g = sw.matrix_world @ GRIP
    path[f] = (t.copy(), g.copy())
    if f in (1, 16, 18, 21, 23, 25, 29, 38, 40, 43, 45, 47, 51, 64):
        print(f"[probe] f{f:02d} tip=({t.x:+.2f},{t.y:+.2f},{t.z:+.2f}) "
              f"grip=({g.x:+.2f},{g.y:+.2f},{g.z:+.2f})")
for name, a, b in (("CUT1 f18->f25", 18, 25), ("CUT2 f40->f47", 40, 47)):
    d = path[b][0] - path[a][0]
    print(f"[probe] {name} tip delta dx={d.x:+.2f} dy={d.y:+.2f} dz={d.z:+.2f}")
# grip-to-hand distance check (sword stays in hand?)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
worst = (0.0, 0)
for f in range(1, 65):
    sc.frame_set(f); dg.update()
    sw = sword.evaluated_get(dg)
    g = sw.matrix_world @ GRIP
    h = (arm.matrix_world @ arm.pose.bones["RightHand"].matrix).translation
    d = (g - h).length
    if d > worst[0]:
        worst = (d, f)
print(f"[probe] max grip-to-hand distance {worst[0]:.3f}m at f{worst[1]}")
print("[probe] DONE")
