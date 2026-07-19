"""
Phase 1 — Skin-weight cleanup for godwyn_game.glb.

Improves BODY skin weights so joints deform cleanly:
  1. clean   — remove near-zero influences (limit 0.02)
  2. smooth  — Laplacian-smooth all deform-group weights to kill pinching /
               jagged weight boundaries at shoulders/elbows/hips/knees/neck
  3. limit   — max 4 bone influences per vertex (game-ready)
  4. normalize_all — weight sums back to 1.0

  5. rigid-plate rebind — gold armor-plate islands (detected by sampling the
     baked texture: gold-dominant color, small compact islands) are rebound
     1.0 to their single dominant bone AFTER the smooth pass, so plates
     translate rigidly with the limb instead of bending/melting through the
     cloth. They are marked in a "RIGID_ARMOR" vertex group so later scripts
     (robe_bones.py) never capture them into cloth chains.

Preserves: the 24-bone armature (untouched), materials/UVs/textures
(untouched), object parenting. No bones added/removed/renamed here.

Output: models/godwyn_p1_weights.blend (images packed).

Tunables via env:
  P1_SMOOTH_FACTOR (default 0.5)
  P1_SMOOTH_REPEAT (default 3)
  P1_CLEAN_LIMIT   (default 0.02)
"""
import bpy
import os

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
OUT = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_p1_weights.blend")

# Defaults locked after visual iteration (rounds 1-6): repeat=6 visibly calms
# the sharp weight-boundary shards at the elbow/shoulder without volume loss.
SMOOTH_FACTOR = float(os.environ.get("P1_SMOOTH_FACTOR", "0.5"))
SMOOTH_REPEAT = int(os.environ.get("P1_SMOOTH_REPEAT", "6"))
CLEAN_LIMIT = float(os.environ.get("P1_CLEAN_LIMIT", "0.05"))

print(f"=== fix_weights: factor={SMOOTH_FACTOR} repeat={SMOOTH_REPEAT} clean={CLEAN_LIMIT} ===")

# ── fresh import (idempotent) ────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
assert os.path.exists(GLB), f"missing {GLB}"
bpy.ops.import_scene.gltf(filepath=GLB)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH")
n_bones_before = len(arm.data.bones)
mats_before = [m.name for m in mesh.data.materials if m]
assert n_bones_before == 24, f"expected 24 bones, got {n_bones_before}"
assert len(mesh.vertex_groups) > 0, "mesh has no vertex groups"
print(f"armature '{arm.name}' bones={n_bones_before}  mesh '{mesh.name}' verts={len(mesh.data.vertices)}")


def weight_stats(tag):
    hist = {}
    bad_sum = 0
    for v in mesh.data.vertices:
        n = len([g for g in v.groups if g.weight > 1e-4])
        hist[n] = hist.get(n, 0) + 1
        if abs(sum(g.weight for g in v.groups) - 1.0) > 0.01:
            bad_sum += 1
    print(f"[{tag}] influences hist={dict(sorted(hist.items()))}  bad_sums={bad_sum}")


weight_stats("before")

# ── run cleanup ops on the mesh ──────────────────────────────────────────────
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh

# 1. remove tiny influences
bpy.ops.object.vertex_group_clean(group_select_mode="ALL", limit=CLEAN_LIMIT, keep_single=True)
print("[ok] clean")

# 2. smooth weights (weight-paint mode required for the smooth op)
#    FIXER R2: the GLOBAL smooth bled hair-strand + pauldron weights onto
#    Spine/arm bones, melting the gold hair mass over the shoulders/upper arms
#    (eval r2 f068 'melted wax'). Mask hair-strand verts and everything above
#    the pauldron line OUT of the smooth via vertex-selection paint masking
#    (mirrors the RIGID_ARMOR pattern; HAIR marker group is written at the
#    end, after normalize, so it never joins deform normalization).
_gname0 = {g.index: g.name for g in mesh.vertex_groups}
_HEAD_G = {"Head", "neck", "head_end", "headfront"}
_mw0 = mesh.matrix_world
PAULDRON_Z = 2.45          # world z of the pauldron line (shoulders ~2.3)
hair_set = set()
for v in mesh.data.vertices:
    hwt = sum(g.weight for g in v.groups if _gname0.get(g.group) in _HEAD_G)
    if hwt >= 0.15 or (_mw0 @ v.co).z > PAULDRON_Z:
        hair_set.add(v.index)
print(f"[hair-mask] {len(hair_set)} hair/above-pauldron verts excluded from smooth")
assert 200 < len(hair_set) < len(mesh.data.vertices) * 0.5, \
    f"suspicious hair-mask size {len(hair_set)}"
for v in mesh.data.vertices:
    v.select = v.index not in hair_set
mesh.data.use_paint_mask_vertex = True
bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
bpy.ops.object.vertex_group_smooth(
    group_select_mode="ALL", factor=SMOOTH_FACTOR, repeat=SMOOTH_REPEAT, expand=0.0
)
bpy.ops.object.mode_set(mode="OBJECT")
mesh.data.use_paint_mask_vertex = False
for v in mesh.data.vertices:
    v.select = False
print(f"[ok] smooth (masked, {len(mesh.data.vertices) - len(hair_set)} verts)")

# 3. limit influences to 4
bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
print("[ok] limit_total(4)")

# 4. renormalize
bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
print("[ok] normalize_all")

weight_stats("after")

# ── 5. rigid armor-plate rebind ─────────────────────────────────────────────
# Single baked material, so plates are found by island + baked-texture color.
me = mesh.data
print("[rigid] building islands…")
uf = list(range(len(me.vertices)))
def _find(a):
    while uf[a] != a:
        uf[a] = uf[uf[a]]
        a = uf[a]
    return a
for e in me.edges:
    ra, rb = _find(e.vertices[0]), _find(e.vertices[1])
    if ra != rb:
        uf[ra] = rb
from collections import defaultdict
islands = defaultdict(list)
for v in me.vertices:
    islands[_find(v.index)].append(v.index)

# per-vertex UV (first loop wins)
uvl = me.uv_layers.active.data
vuv = {}
for p in me.polygons:
    for li, vi in zip(p.loop_indices, p.vertices):
        if vi not in vuv:
            vuv[vi] = tuple(uvl[li].uv)

img = max((i for i in bpy.data.images if i.size[0]), key=lambda i: i.size[0])
W, H = img.size
import array
px = array.array("f", [0.0]) * (W * H * 4)
img.pixels.foreach_get(px)
def tex(uv):
    x = min(W - 1, max(0, int(uv[0] % 1.0 * W)))
    y = min(H - 1, max(0, int(uv[1] % 1.0 * H)))
    o = (y * W + x) * 4
    return px[o], px[o + 1], px[o + 2]

gname = {g.index: g.name for g in mesh.vertex_groups}
mw = mesh.matrix_world
RIGID_MAX_VERTS = 5000
RIGID_MAX_DIM = 0.60
rigid_verts = []
n_plates = 0
for root, vis in islands.items():
    if len(vis) < 8 or len(vis) > RIGID_MAX_VERTS:
        continue
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for vi in vis:
        c = mw @ me.vertices[vi].co
        for k in range(3):
            lo[k] = min(lo[k], c[k]); hi[k] = max(hi[k], c[k])
    if max(hi[k] - lo[k] for k in range(3)) > RIGID_MAX_DIM:
        continue
    # mean baked color over a sample of verts
    samp = vis[:: max(1, len(vis) // 100)]
    r = g = b = 0.0
    ns = 0
    for vi in samp:
        if vi in vuv:
            cr, cg, cb = tex(vuv[vi])
            r += cr; g += cg; b += cb; ns += 1
    if ns == 0:
        continue
    r, g, b = r / ns, g / ns, b / ns
    # gold armor: warm, red/green dominant over blue (robe is blue-dominant,
    # skin is near-white so r/b ~1.15 — both rejected)
    if not (r > 0.25 and r > 2.0 * b and g > 1.3 * b):
        continue
    # dominant bone across the island
    bw = defaultdict(float)
    for vi in vis:
        for gr in me.vertices[vi].groups:
            nm = gname.get(gr.group)
            if nm:
                bw[nm] += gr.weight
    if not bw:
        continue
    dom = max(bw, key=bw.get)
    dvg = mesh.vertex_groups[dom]
    for vi in vis:
        v = me.vertices[vi]
        for gr in list(v.groups):
            nm = gname.get(gr.group)
            if nm and nm != dom:
                mesh.vertex_groups[nm].remove([vi])
        dvg.add([vi], 1.0, "REPLACE")
    rigid_verts.extend(vis)
    n_plates += 1
print(f"[rigid] rebound {n_plates} gold-plate islands "
      f"({len(rigid_verts)} verts) 1.0 to their dominant bone")

# marker group so robe_bones.py never captures plates into cloth chains
if "RIGID_ARMOR" in mesh.vertex_groups:
    mesh.vertex_groups.remove(mesh.vertex_groups["RIGID_ARMOR"])
marker = mesh.vertex_groups.new(name="RIGID_ARMOR")
if rigid_verts:
    marker.add(rigid_verts, 1.0, "REPLACE")

# HAIR marker group (smooth-mask set from above) so robe_bones.py can verify
# hair capture and later scripts can mask hair without re-deriving it.
# Added AFTER normalize_all so the marker never participates in deform sums.
if "HAIR" in mesh.vertex_groups:
    mesh.vertex_groups.remove(mesh.vertex_groups["HAIR"])
hair_marker = mesh.vertex_groups.new(name="HAIR")
if hair_set:
    hair_marker.add(sorted(hair_set), 1.0, "REPLACE")
print(f"[ok] HAIR marker group: {len(hair_set)} verts")
# marker must not affect deform normalization: verify rigid verts sum to 1
# over BONE groups only
bone_names = {b.name for b in arm.data.bones}
gname = {g.index: g.name for g in mesh.vertex_groups}
for vi in rigid_verts[:: max(1, len(rigid_verts) // 500)]:
    s = sum(g.weight for g in me.vertices[vi].groups
            if gname.get(g.group) in bone_names)
    assert abs(s - 1.0) < 1e-3, f"rigid vert {vi} bone-weight sum {s}"

# ── integrity checks: rig + materials untouched ──────────────────────────────
assert len(arm.data.bones) == 24, "BONE COUNT CHANGED"
assert [m.name for m in mesh.data.materials if m] == mats_before, "MATERIALS CHANGED"
imgs = [(i.name, tuple(i.size)) for i in bpy.data.images if i.size[0]]
print(f"[ok] rig intact (24 bones), materials intact {mats_before}, images {imgs}")

# ── save .blend with packed images ───────────────────────────────────────────
try:
    bpy.ops.file.pack_all()
except Exception as e:
    print("pack_all note:", e)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"[ok] saved {OUT}")
print("=== fix_weights DONE ===")
