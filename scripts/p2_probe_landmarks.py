"""p2_probe_landmarks.py — print Godwyn_Body landmark data for Phase 2 authoring."""
import bpy, os, sys, mathutils

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_phase1.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)
body = bpy.data.objects["Godwyn_Body"]
mw = body.matrix_world
vs = [mw @ v.co for v in body.data.vertices]
H = max(v.z for v in vs)
print(f"verts={len(vs)} height={H:.3f}")

print("\n-- vertex groups --")
for g in body.vertex_groups:
    print(" vg:", g.name)

def band(z0, z1, pred=lambda c: True):
    pts = [c for c in vs if z0 <= c.z <= z1 and pred(c)]
    if not pts:
        return None
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    cx = sum(xs)/len(xs); cy = sum(ys)/len(ys)
    return (len(pts), min(xs), max(xs), min(ys), max(ys), cx, cy)

print("\n-- z slices (all) --")
for i in range(33):
    z0 = i*0.1; z1 = z0+0.1
    b = band(z0, z1)
    if b:
        n, x0, x1, y0, y1, cx, cy = b
        print(f" z {z0:4.1f}-{z1:4.1f}: n={n:5d} x[{x0:+.3f},{x1:+.3f}] "
              f"y[{y0:+.3f},{y1:+.3f}] c=({cx:+.3f},{cy:+.3f})")

# torso-only slices (|x|<0.35) around chest/waist
print("\n-- torso slices |x|<0.35 --")
for i in range(14, 29):
    z0 = i*0.1; z1 = z0+0.1
    b = band(z0, z1, lambda c: abs(c.x) < 0.35)
    if b:
        n, x0, x1, y0, y1, cx, cy = b
        print(f" z {z0:4.1f}-{z1:4.1f}: n={n:5d} x[{x0:+.3f},{x1:+.3f}] "
              f"y[{y0:+.3f},{y1:+.3f}] c=({cx:+.3f},{cy:+.3f})")

# arm extremes
right = [c for c in vs if c.x > 0.4]
print("\n-- right arm (x>0.4) --")
xmax = max(c.x for c in right)
tip = [c for c in right if c.x > xmax - 0.05]
tc = sum(tip, mathutils.Vector())/len(tip)
print(f" arm tip centroid: ({tc.x:.3f},{tc.y:.3f},{tc.z:.3f}) xmax={xmax:.3f}")
for i in range(4, 15):
    x0 = 0.3 + i*0.1; x1 = x0 + 0.1
    pts = [c for c in right if x0 <= c.x <= x1]
    if pts:
        zs = [p.z for p in pts]; ys = [p.y for p in pts]
        cz = sum(zs)/len(zs); cy = sum(ys)/len(ys)
        print(f" x {x0:.1f}-{x1:.1f}: n={len(pts):4d} z[{min(zs):.3f},{max(zs):.3f}] "
              f"cz={cz:.3f} cy={cy:.3f} y[{min(ys):+.3f},{max(ys):+.3f}]")

# head band
print("\n-- head (top 0.45m) --")
for i in range(5):
    z0 = H - 0.45 + i*0.1
    b = band(z0, z0+0.1)
    if b:
        n, x0, x1, y0, y1, cx, cy = b
        print(f" z {z0:.2f}: n={n:4d} x[{x0:+.3f},{x1:+.3f}] y[{y0:+.3f},{y1:+.3f}] c=({cx:+.3f},{cy:+.3f})")
print("PROBE OK")
