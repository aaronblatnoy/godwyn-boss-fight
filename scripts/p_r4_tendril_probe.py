"""p_r4_tendril_probe.py — inspect what geometry lives below the left fist.
Loads models/godwyn_sword.blend, prints sub-component stats in the hand zone.
"""
import bpy
import bmesh
import math
import os
from collections import deque
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
bpy.ops.wm.open_mainfile(filepath=os.path.join(REPO, "models", "godwyn_sword.blend"))
arm = bpy.data.objects["Armature"]
body = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
me = body.data
mwm = body.matrix_world
awm = arm.matrix_world
lh = awm @ arm.data.bones["LeftHand"].head_local
sw_pts = [sword.matrix_world @ v.co for v in sword.data.vertices]
grip_top = max(c.z for c in sw_pts)
tip = min(sw_pts, key=lambda c: c.z)
top = max(sw_pts, key=lambda c: c.z)
print(f"[probe] lh={tuple(round(c,3) for c in lh)} grip_top={grip_top:.3f} "
      f"tip={tuple(round(c,3) for c in tip)}")
axis_d = (top - tip).normalized()

def r_ax(w):
    t = (w - tip).dot(axis_d)
    foot = tip + axis_d * t
    return math.hypot(w.x - foot.x, w.y - foot.y)

bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
# generous zone: everything below the palm near the hand
zone = set()
for bv in bm.verts:
    w = mwm @ bv.co
    if not (grip_top - 0.90 < w.z < grip_top - 0.12):
        continue
    if math.hypot(w.x - lh.x, w.y - lh.y) > 0.40:
        continue
    zone.add(bv.index)
print(f"[probe] zone verts={len(zone)}")
seen = set()
comps = []
for i0 in zone:
    if i0 in seen:
        continue
    comp = {i0}
    dq = deque([bm.verts[i0]])
    while dq:
        u = dq.popleft()
        for e in u.link_edges:
            o = e.other_vert(u)
            if o.index in zone and o.index not in comp:
                comp.add(o.index)
                dq.append(o)
    seen |= comp
    comps.append(sorted(comp))
comps.sort(key=len, reverse=True)
print(f"[probe] zone sub-components={len(comps)}")
for ci, comp in enumerate(comps[:25]):
    pts = [mwm @ bm.verts[i].co for i in comp]
    hx = max(p.x for p in pts) - min(p.x for p in pts)
    hy = max(p.y for p in pts) - min(p.y for p in pts)
    hz = max(p.z for p in pts) - min(p.z for p in pts)
    zlo = min(p.z for p in pts)
    zhi = max(p.z for p in pts)
    rs = sorted(r_ax(p) for p in pts)
    print(f"[probe] comp{ci}: n={len(comp)} hx={hx:.3f} hy={hy:.3f} hz={hz:.3f} "
          f"z=[{zlo:.2f},{zhi:.2f}] r=[{rs[0]:.3f},{rs[len(rs)//2]:.3f},{rs[-1]:.3f}]")
bm.free()
print("[probe] DONE")
