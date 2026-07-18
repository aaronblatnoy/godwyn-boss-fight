"""Numeric probe: achieved blade direction + tip path in godwyn_xslash.blend."""
import bpy, os
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=os.path.expanduser(
    "~/godwyn-boss-fight/models/godwyn_xslash.blend"))
sc = bpy.context.scene
sword = bpy.data.objects["Godwyn_Sword"]
bb = [Vector(c) for c in sword.bound_box]
zmin = min(c.z for c in bb); zmax = max(c.z for c in bb)
cx = sum(c.x for c in bb) / 8; cy = sum(c.y for c in bb) / 8
GRIP = Vector((cx, cy, zmin)); TIP = Vector((cx, cy, zmax))
dg = bpy.context.evaluated_depsgraph_get()
KEYS = {1:"guard",16:"windup1",18:"w1hold",21:"cut1_mid",25:"cut1_end",
        29:"c1settle",38:"windup2",40:"w2hold",43:"cut2_mid",47:"cut2_end",
        51:"c2settle",64:"recover"}
tips = {}
for f in range(1, 65):
    sc.frame_set(f); dg.update()
    sw = sword.evaluated_get(dg)
    t = sw.matrix_world @ TIP; g = sw.matrix_world @ GRIP
    tips[f] = t.copy()
    d = (t - g).normalized()
    tag = KEYS.get(f, "")
    print(f"f{f:02d} {tag:9s} tip=({t.x:+.2f},{t.y:+.2f},{t.z:+.2f}) "
          f"dir=({d.x:+.2f},{d.y:+.2f},{d.z:+.2f})")
for name, a, b in (("CUT1", 18, 25), ("CUT2", 40, 47)):
    d = tips[b] - tips[a]
    print(f"{name} tip delta dx={d.x:+.2f} dy={d.y:+.2f} dz={d.z:+.2f}")
