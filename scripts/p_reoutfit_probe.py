"""p_reoutfit_probe.py — measure Godwyn_Body landmarks for the gold-plate
re-outfit (torso widths, leg centrelines, knee/ankle z, foot bbox, hand bbox,
arm axis). Reads models/godwyn_phase1.blend, prints a table. No writes."""
import bpy, os
from mathutils import Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_phase1.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
body = bpy.data.objects["Godwyn_Body"]
vs = [v.co.copy() for v in body.data.vertices]
print(f"[probe] body verts: {len(vs)}")
zs = [c.z for c in vs]
print(f"[probe] z range: {min(zs):.3f} .. {max(zs):.3f}")

def band(z0, z1, pred=lambda c: True):
    sel = [c for c in vs if z0 <= c.z < z1 and pred(c)]
    if not sel:
        return None
    xs = [c.x for c in sel]; ys = [c.y for c in sel]
    cx = sum(xs) / len(xs); cy = sum(ys) / len(ys)
    return (len(sel), min(xs), max(xs), min(ys), max(ys), cx, cy)

print("\n[probe] TORSO/FULL bands (all verts):")
for z0 in [2.60, 2.55, 2.50, 2.45, 2.40, 2.35, 2.30, 2.25, 2.20, 2.15,
           2.10, 2.05, 2.00, 1.95, 1.90, 1.85, 1.80, 1.75, 1.70, 1.65,
           1.60, 1.55, 1.50, 1.45, 1.40]:
    b = band(z0, z0 + 0.05, lambda c: abs(c.x) < 0.42)
    if b:
        n, x0, x1, y0, y1, cx, cy = b
        print(f"  z={z0:.2f}: n={n:4d} x[{x0:+.3f},{x1:+.3f}] "
              f"y[{y0:+.3f},{y1:+.3f}] c=({cx:+.3f},{cy:+.3f})")

print("\n[probe] RIGHT LEG bands (x>0.02, z<1.6):")
for z0 in [1.55, 1.45, 1.35, 1.25, 1.15, 1.05, 0.95, 0.85, 0.75, 0.65,
           0.55, 0.45, 0.35, 0.25, 0.15, 0.05]:
    b = band(z0, z0 + 0.10, lambda c: c.x > 0.02)
    if b:
        n, x0, x1, y0, y1, cx, cy = b
        rmax = max(((c.x - cx) ** 2 + (c.y - cy) ** 2) ** 0.5
                   for c in vs if z0 <= c.z < z0 + 0.10 and c.x > 0.02)
        print(f"  z={z0:.2f}: n={n:4d} x[{x0:+.3f},{x1:+.3f}] "
              f"y[{y0:+.3f},{y1:+.3f}] c=({cx:+.3f},{cy:+.3f}) rmax={rmax:.3f}")

print("\n[probe] FOOT R (z<0.22, x>0.02):")
sel = [c for c in vs if c.z < 0.22 and c.x > 0.02]
if sel:
    print(f"  n={len(sel)} x[{min(c.x for c in sel):+.3f},{max(c.x for c in sel):+.3f}]"
          f" y[{min(c.y for c in sel):+.3f},{max(c.y for c in sel):+.3f}]"
          f" z[{min(c.z for c in sel):+.3f},{max(c.z for c in sel):+.3f}]")

print("\n[probe] RIGHT ARM bands (x>0.40, z>1.7):")
for x0 in [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85,
           0.90, 0.95, 1.00, 1.05]:
    sel = [c for c in vs if x0 <= c.x < x0 + 0.05 and c.z > 1.6]
    if sel:
        cy = sum(c.y for c in sel) / len(sel)
        cz = sum(c.z for c in sel) / len(sel)
        rmax = max(((c.y - cy) ** 2 + (c.z - cz) ** 2) ** 0.5 for c in sel)
        print(f"  x={x0:.2f}: n={len(sel):4d} "
              f"y[{min(c.y for c in sel):+.3f},{max(c.y for c in sel):+.3f}] "
              f"z[{min(c.z for c in sel):+.3f},{max(c.z for c in sel):+.3f}] "
              f"c=({cy:+.3f},{cz:+.3f}) rmax={rmax:.3f}")

print("\n[probe] RIGHT HAND (x>0.80, z<2.1):")
sel = [c for c in vs if c.x > 0.80 and c.z < 2.10]
if sel:
    print(f"  n={len(sel)} x[{min(c.x for c in sel):+.3f},{max(c.x for c in sel):+.3f}]"
          f" y[{min(c.y for c in sel):+.3f},{max(c.y for c in sel):+.3f}]"
          f" z[{min(c.z for c in sel):+.3f},{max(c.z for c in sel):+.3f}]")
print("\n[probe] LEFT HAND (x<-0.80, z<2.1):")
sel = [c for c in vs if c.x < -0.80 and c.z < 2.10]
if sel:
    print(f"  n={len(sel)} x[{min(c.x for c in sel):+.3f},{max(c.x for c in sel):+.3f}]"
          f" y[{min(c.y for c in sel):+.3f},{max(c.y for c in sel):+.3f}]"
          f" z[{min(c.z for c in sel):+.3f},{max(c.z for c in sel):+.3f}]")

print("\n[probe] NECK bands:")
for z0 in [2.60, 2.64, 2.68, 2.72, 2.76]:
    b = band(z0, z0 + 0.04, lambda c: abs(c.x) < 0.20 and abs(c.y - 0.15) < 0.25)
    if b:
        n, x0, x1, y0, y1, cx, cy = b
        print(f"  z={z0:.2f}: n={n:4d} x[{x0:+.3f},{x1:+.3f}] "
              f"y[{y0:+.3f},{y1:+.3f}] c=({cx:+.3f},{cy:+.3f})")
print("[probe] done")
