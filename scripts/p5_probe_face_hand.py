"""
p5_probe_face_hand.py — Phase 5 fixer probe: measure eye / hand / chest
landmarks from the freshly-built Godwyn_Body (post 01_base_human.py).

Read-only: opens models/godwyn_phase1.blend, prints numbers, saves nothing.

Run:
  blender --background --python scripts/p5_probe_face_hand.py
"""
import os
import bpy
from mathutils import Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_phase1.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
body = bpy.data.objects["Godwyn_Body"]
me = body.data

print("[probe] verts:", len(me.vertices))
print("[probe] vertex groups:", [vg.name for vg in body.vertex_groups])

# --- eye helper groups ------------------------------------------------------
for gname in ("helper-l-eye", "helper-r-eye"):
    vg = body.vertex_groups.get(gname)
    if vg is None:
        print(f"[probe] {gname}: MISSING")
        continue
    gi = vg.index
    pts = []
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi and g.weight > 0:
                pts.append(v.co.copy())
                break
    if not pts:
        print(f"[probe] {gname}: 0 verts")
        continue
    c = sum(pts, Vector()) / len(pts)
    r = max((p - c).length for p in pts)
    miny = min(p.y for p in pts)
    print(f"[probe] {gname}: n={len(pts)} centroid=({c.x:.4f},{c.y:.4f},{c.z:.4f}) "
          f"maxr={r:.4f} front_y={miny:.4f}")
    # lid verts: NON-eye verts near the eye centre
    near = [v.co.copy() for v in me.vertices
            if (v.co - c).length < r * 2.0
            and not any(g.group == gi and g.weight > 0 for g in v.groups)]
    if near:
        nminy = min(p.y for p in near)
        nzmin = min(p.z for p in near)
        nzmax = max(p.z for p in near)
        print(f"[probe]   lid-region: n={len(near)} front_y={nminy:.4f} "
              f"z=[{nzmin:.4f},{nzmax:.4f}]")

# --- right hand: fingers + palm normal --------------------------------------
WRIST_R = Vector((0.88, -0.19, 1.99))
HAND_R = Vector((0.98, -0.28, 1.84))
f_dir = (HAND_R - WRIST_R).normalized()
hand_verts = [(v.co.copy(), v.normal.copy()) for v in me.vertices
              if (v.co - WRIST_R).dot(f_dir) > 0.02
              and (v.co - WRIST_R).length < 0.50 and v.co.x > 0.80]
print(f"[probe] right-hand verts: {len(hand_verts)}")
if hand_verts:
    cs = [c for c, n in hand_verts]
    cx = sum(cs, Vector()) / len(cs)
    smax = max((c - WRIST_R).dot(f_dir) for c in cs)
    print(f"[probe] hand centroid=({cx.x:.4f},{cx.y:.4f},{cx.z:.4f}) "
          f"finger extent along f_dir={smax:.4f}")
    # palm region = first 40% along finger dir
    palm_n = Vector()
    for c, n in hand_verts:
        s = (c - WRIST_R).dot(f_dir)
        if s < smax * 0.45:
            palm_n += n
    palm_n.normalize()
    print(f"[probe] avg hand-region normal (palm ambiguity check): "
          f"({palm_n.x:.3f},{palm_n.y:.3f},{palm_n.z:.3f})")
    # split by normal hemisphere vs f_dir x world-z candidates
    for label, axis in (("+Y(back)", Vector((0, 1, 0))),
                        ("-Y(front)", Vector((0, -1, 0))),
                        ("+X(out)", Vector((1, 0, 0))),
                        ("-X(in)", Vector((-1, 0, 0)))):
        cnt = sum(1 for c, n in hand_verts if n.dot(axis) > 0.5)
        print(f"[probe]   verts with normal toward {label}: {cnt}")

# --- chest front surface samples (for filigree conform) ----------------------
def surf_y(x, z):
    best = None
    for v in me.vertices:
        if abs(v.co.x - x) < 0.035 and abs(v.co.z - z) < 0.035 and v.co.y < 0.18:
            if best is None or v.co.y < best:
                best = v.co.y
    return best

print("[probe] chest front y samples:")
for z in (2.05, 2.15, 2.25, 2.35, 2.45, 2.52, 2.58):
    for x in (0.0, 0.1, 0.2):
        y = surf_y(x, z)
        print(f"[probe]   x={x:.2f} z={z:.2f} -> y={y if y is None else round(y,4)}")

# --- neck ring radial samples (gorget fit) -----------------------------------
import math
print("[probe] neck radial samples at z=2.60..2.66:")
for a_deg in range(0, 360, 45):
    a = math.radians(a_deg)
    d = Vector((math.cos(a), math.sin(a), 0.0))
    best = 0.0
    for v in me.vertices:
        if 2.58 < v.co.z < 2.68:
            rel = Vector((v.co.x, v.co.y - 0.16, 0.0))
            if rel.length > 0.01 and rel.normalized().dot(d) > 0.97:
                best = max(best, rel.length)
    print(f"[probe]   a={a_deg} r={best:.4f}")

print("[probe] done")
