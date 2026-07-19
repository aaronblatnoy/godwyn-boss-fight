"""
Phase 2 probe #3 — nail spatial thresholds for robe/cape/hair classification.

Front is -Y, back is +Y, character z 0..3.2, hips z~1.7, legs x~±0.25 y~-0.18.

Prints, per z-slice:
  - y histogram (where does the body back end / cape begin)
  - radial-distance-from-nearest-leg-axis histogram for z<1.7
  - hair candidates: verts with dominant Head/neck weight below z=2.8
"""
import bpy
import os
from collections import defaultdict
from mathutils import Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_p1_weights.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
mesh = bpy.data.objects["char1"]
me = mesh.data
mw = mesh.matrix_world
gname = {g.index: g.name for g in mesh.vertex_groups}

def dom(v):
    best, bw = None, 0.0
    for g in v.groups:
        if g.weight > bw:
            bw = g.weight
            best = gname.get(g.group)
    return best

co = [mw @ v.co for v in me.vertices]

# 1. y histograms per z slice (0.1 bins)
for z0, z1 in [(0.2, 0.6), (0.9, 1.2), (1.4, 1.6), (1.9, 2.2), (2.3, 2.55)]:
    ys = [c.y for c in co if z0 <= c.z <= z1]
    hist = defaultdict(int)
    for y in ys:
        hist[round(y // 0.1) * 0.1] += 1
    print(f"z[{z0},{z1}] n={len(ys)} y-hist:",
          {f"{k:+.1f}": v for k, v in sorted(hist.items())})

# 2. radial distance from nearest leg axis, z slices below hips
import math
def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length

bones = mesh.parent.data.bones
def hw(n):
    return mesh.parent.matrix_world @ bones[n].head_local
Lu, Ll, Lf = hw("LeftUpLeg"), hw("LeftLeg"), hw("LeftFoot")
Ru, Rl, Rf = hw("RightUpLeg"), hw("RightLeg"), hw("RightFoot")

for z0, z1 in [(0.25, 0.6), (0.7, 1.1), (1.2, 1.55)]:
    ds = []
    for c in co:
        if z0 <= c.z <= z1:
            d = min(seg_dist(c, Lu, Ll), seg_dist(c, Ll, Lf),
                    seg_dist(c, Ru, Rl), seg_dist(c, Rl, Rf))
            ds.append(d)
    hist = defaultdict(int)
    for d in ds:
        hist[round(d // 0.05) * 0.05] += 1
    print(f"z[{z0},{z1}] n={len(ds)} legdist-hist:",
          {f"{k:.2f}": v for k, v in sorted(hist.items())})

# 3. hair: dominant Head/neck verts by z band and y sign
hz = defaultdict(int)
for v in me.vertices:
    d = dom(v)
    if d in ("Head", "neck", "head_end", "headfront"):
        c = co[v.index]
        band = round(c.z // 0.2) * 0.2
        side = "front" if c.y < -0.25 else ("back" if c.y > 0.02 else "mid")
        hz[(band, side)] += 1
print("head/neck-dominant verts by (z-band, y-side):")
for k, n in sorted(hz.items()):
    print("  ", k, n)

# 4. x-extent at z 2.3-2.8 for hair strands vs shoulders
xs = [(c.x, c.y) for c in co if 2.3 <= c.z <= 2.75]
print("chest/shoulder slice z[2.3,2.75]: x range",
      min(x for x, _ in xs), max(x for x, _ in xs))
print("=== DONE ===")
