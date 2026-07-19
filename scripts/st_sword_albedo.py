"""
st_sword_albedo.py — Phase 3 fixer follow-up (evaluator flaw 3).

The separated blade's UV islands land on ROBE-BLUE texels of godwyn_albedo
(probed: blade z-bands sample meanRGB ~(0.00,0.21,0.52); grip/pommel sample
gold ~(0.6,0.6,0.44)). Off-spec for Godwyn the Golden — the blade must read
steel/gold.

Fix: remap ONLY Godwyn_Sword's blue-sampling faces into a small verified
GOLD texel patch of the same baked albedo (per-vertex deterministic jitter
inside the patch keeps subtle variation). char1's mesh/UVs/materials and the
baked images are NOT touched; the shared GodwynGameMat is NOT rebuilt.

Runs in-place on models/godwyn_st_sword.blend (before st_feet.py).

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/st_sword_albedo.py 2>&1
"""
import bpy
import os
import math

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO, "models", "godwyn_st_sword.blend")
bpy.ops.wm.open_mainfile(filepath=BLEND)

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects["char1"]
sword = bpy.data.objects["Godwyn_Sword"]
me = sword.data
uvl = me.uv_layers.active.data

img = bpy.data.images["godwyn_albedo"]
W, H = img.size
px = list(img.pixels)  # RGBA float
char1_uv_hash0 = hash(tuple(round(d.uv[0], 5) for d in
                            char1.data.uv_layers.active.data[:2000]))

def sample(u, v):
    xi = min(int((u % 1.0) * W), W - 1)
    yi = min(int((v % 1.0) * H), H - 1)
    o = 4 * (yi * W + xi)
    return px[o], px[o + 1], px[o + 2]

def is_blue(r, g, b):
    return b > r + 0.10 and b > 0.25

def is_gold(r, g, b):
    return r > 0.40 and g > 0.30 and r > b + 0.10

# ── find a compact, uniformly-gold texel patch ─────────────────────────────
# candidates: UVs the grip/pommel already samples gold at; verify an 11x11
# texel neighborhood is all gold.
gold_uv = None
for li, d in enumerate(uvl):
    u, v = d.uv
    if not is_gold(*sample(u, v)):
        continue
    xi = int((u % 1.0) * W)
    yi = int((v % 1.0) * H)
    if not (6 <= xi < W - 6 and 6 <= yi < H - 6):
        continue
    ok = True
    for dy in range(-5, 6, 2):
        for dx in range(-5, 6, 2):
            o = 4 * ((yi + dy) * W + (xi + dx))
            if not is_gold(px[o], px[o + 1], px[o + 2]):
                ok = False
                break
        if not ok:
            break
    if ok:
        gold_uv = ((xi + 0.5) / W, (yi + 0.5) / H)
        break
assert gold_uv is not None, "no uniform gold patch found in godwyn_albedo"
print(f"[GOLD PATCH] uv=({gold_uv[0]:.4f},{gold_uv[1]:.4f}) "
      f"rgb={tuple(round(c,2) for c in sample(*gold_uv))}")

# patch jitter radius in UV space (~8 texels)
JIT = 8.0 / W

def jitter(vi):
    a = math.sin(vi * 12.9898) * 43758.5453
    b = math.sin(vi * 78.233) * 12345.6789
    return ((a - math.floor(a)) - 0.5) * 2 * JIT, ((b - math.floor(b)) - 0.5) * 2 * JIT

# ── classify faces by sampled color, remap blue faces ─────────────────────
n_blue_faces = n_loops = 0
for poly in me.polygons:
    rs = gs = bs = 0.0
    for li in poly.loop_indices:
        r, g, b = sample(*uvl[li].uv)
        rs += r; gs += g; bs += b
    n = len(poly.loop_indices)
    if is_blue(rs / n, gs / n, bs / n):
        n_blue_faces += 1
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            jx, jy = jitter(vi)
            uvl[li].uv = (gold_uv[0] + jx, gold_uv[1] + jy)
            n_loops += 1
me.update()
print(f"[REMAP] {n_blue_faces} blue-sampling faces -> gold patch ({n_loops} loops)")

# verify: re-sample sword by z-band, no blue bands left
swco = [sword.matrix_world @ v.co for v in me.vertices]
zs = [w.z for w in swco]
zmin, zmax = min(zs), max(zs)
bands = {}
for poly in me.polygons:
    for li in poly.loop_indices:
        t = (swco[me.loops[li].vertex_index].z - zmin) / (zmax - zmin)
        bands.setdefault(min(int(t * 5), 4), []).append(sample(*uvl[li].uv))
for band in sorted(bands):
    s = bands[band]
    r = sum(x[0] for x in s) / len(s)
    g = sum(x[1] for x in s) / len(s)
    b = sum(x[2] for x in s) / len(s)
    print(f"[BAND {band}] n={len(s)} meanRGB=({r:.2f},{g:.2f},{b:.2f})")
    assert not is_blue(r, g, b), f"band {band} still robe-blue"

# ── verify nothing else was touched ────────────────────────────────────────
assert hash(tuple(round(d.uv[0], 5) for d in
                  char1.data.uv_layers.active.data[:2000])) == char1_uv_hash0, \
    "char1 UVs changed!"
assert len(arm.data.bones) == 121
assert sum(1 for b in arm.data.bones if b.name.startswith("phys_")) == 97
assert not img.is_dirty, "albedo image pixels were modified!"
print("[VERIFY] char1 UVs untouched, rig intact, albedo image untouched")

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"[SAVED] {BLEND}")
print("ST_SWORD_ALBEDO DONE")
