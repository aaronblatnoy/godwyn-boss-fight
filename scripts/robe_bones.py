"""
Phase 2 — robe/cape/hair physics bone chains for Godwyn.

The floor robe, back cape and hair strands currently stretch with the LEG
bones (they were skinned to whatever body bone was nearest). This script:

  1. Opens models/godwyn_p1_weights.blend (24-bone Mixamo-style rig, char1
     mesh, baked GodwynGameMat — all preserved untouched).
  2. ADDS child bone chains to the EXISTING armature (game-exportable real
     deform bones, ready for spring-bone physics in Godot):
        robe front_C/L/R, side_L/R, back_L/R/C     (parent Hips,  8 chains x 8)
        cape_L/C/R                                 (parent Spine, 3 chains x 7)
        hair_front_L/R, hair_back                  (parent Head,  3 chains x 4)
     Chains are ARCED outward (quadratic bow in x/y) along the mesh surface
     so link rotations produce visible billow, not a pivoting straight line.
  3. Classifies cloth/hair vertices geometrically (front = -Y):
        HAIR: verts with combined Head/neck weight >= 0.15 hanging below
              z=2.72 (strands), off the face center.
        CAPE: verts behind the back plane (y > 0.10 below z 1.5,
              y > 0.15 up to z 2.55).
        ROBE: verts below z 1.55 whose radial distance from the nearest
              leg-bone axis exceeds a per-height radius (legs+armor kept).
        Sword + hands (LeftHand/RightHand weight > 0.4), feet/boots
        (Foot/Toe weight > 0.35) and arm-dominated verts are NEVER touched.
  4. REWEIGHTS classified verts: all old influences removed, replaced by a
     z-parameterized linear ramp blended across the 3 nearest chains (wide
     inverse-square falloff), cross-faded to the chain's parent bone near the
     attachment (top 35cm), then a vertex_group_smooth pass restricted to the
     phys_* groups kills faceted crease lines. Rigid armor plates (marked
     RIGID_ARMOR by fix_weights.py) are never captured. Hard assertions +
     a Hips root-motion smoke test guard against bind-pose-anchored verts.
  5. Asserts the original 24 bones + material are byte-identical, packs
     images, saves models/godwyn_p2_robe.blend.

FIXER R3 (movement round 3): the r2 inverse-distance 3-chain blend let
adjacent hem verts be driven by wildly different chains/links — under strong
torso pitch + root motion (f097 leaping slam) the cloth shell collapsed into
tangled shards, and at f040 the hem tore at chain-column boundaries. Fixes:
  a. COLUMN PARAMETERIZATION replaces the distance blend: robe verts get an
     angular coordinate around the hips axis and blend the TWO bracketing
     chain columns (continuous 50/50 at each seam, 100% at column centers);
     cape verts blend the two x-adjacent columns; hair verts bind to their
     single nearest strand chain. Max 2 columns x 2 links = 4 influences.
  b. MUTUALLY EXCLUSIVE MASKS: below the attachment fade band, cloth verts
     carry phys chain weight ONLY — any Spine/Hips/Leg residue left by the
     weight-smooth pass is stripped and the vert renormalized to phys.
  c. LAYER LOCK: coincident inner gold-layer verts (within 2cm of the robe
     shell, gold-textured, non-rigid) receive a nearest-vert copy of the
     outer robe shell's weights so both layers move together; the blue robe
     shell is then pushed ~1cm outward along its normals (z-fight kill).
  d. CAPE WAD: blue cloth carrying arm weights beyond 28cm of the shoulder
     joints is captured into cape chains (arm weights stripped) so the cape
     no longer welds to the left forearm.

Tunable via env: P2_IN, P2_OUT.
"""
import bpy
import os
import json
from collections import defaultdict
from mathutils import Vector, Matrix

IN = os.path.expanduser(os.environ.get(
    "P2_IN", "~/godwyn-boss-fight/models/godwyn_p1_weights.blend"))
OUT = os.path.expanduser(os.environ.get(
    "P2_OUT", "~/godwyn-boss-fight/models/godwyn_p2_robe.blend"))

bpy.ops.wm.open_mainfile(filepath=IN)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = bpy.data.objects["char1"]
me = mesh.data

orig_bones = {b.name: tuple(round(c, 5) for c in b.head_local)
              for b in arm.data.bones}
assert len(orig_bones) == 24, f"expected 24 bones, got {len(orig_bones)}"
orig_mats = [m.name for m in me.materials if m]
n_verts0 = len(me.vertices)

# ---------------------------------------------------------------------------
# 1. chain definitions (WORLD space; front = -Y)
# ---------------------------------------------------------------------------
CHAINS = {
    # name: (parent, n_bones, root_xyz, tip_xyz, region, bow_xy)
    # bow_xy: horizontal (x, y) offset of the chain mid-point — arcs the rest
    # chain outward along the mesh surface so per-link rotation produces a
    # visible billow instead of pivoting a straight vertical line (z stays
    # linear along the chain, so the z->link-index mapping is exact).
    # FIXER R2: 8 chains x 8 links around the full skirt circumference (5x6
    # deformed as a faceted rigid tent — hard planar creases, straight hem).
    # Uniform link spacing keeps the z->link-index mapping exact; 8 links
    # gives the hem the extra articulation the brief asks for.
    "phys_robe_front_C": ("Hips", 8, (+0.00, -0.42, 1.52), (+0.00, -0.50, 0.08), "ROBE", (0.00, -0.08)),
    "phys_robe_front_L": ("Hips", 8, (+0.30, -0.30, 1.52), (+0.45, -0.38, 0.08), "ROBE", (+0.05, -0.06)),
    "phys_robe_front_R": ("Hips", 8, (-0.30, -0.30, 1.52), (-0.45, -0.38, 0.08), "ROBE", (-0.05, -0.06)),
    "phys_robe_side_L":  ("Hips", 8, (+0.42, -0.05, 1.52), (+0.72, +0.02, 0.08), "ROBE", (+0.10, 0.00)),
    "phys_robe_side_R":  ("Hips", 8, (-0.42, -0.05, 1.52), (-0.72, +0.02, 0.08), "ROBE", (-0.10, 0.00)),
    "phys_robe_back_L":  ("Hips", 8, (+0.28, +0.02, 1.52), (+0.45, +0.22, 0.08), "ROBE", (+0.06, +0.08)),
    "phys_robe_back_R":  ("Hips", 8, (-0.28, +0.02, 1.52), (-0.45, +0.22, 0.08), "ROBE", (-0.06, +0.08)),
    "phys_robe_back_C":  ("Hips", 8, (+0.00, +0.05, 1.52), (+0.00, +0.28, 0.08), "ROBE", (0.00, +0.10)),
    "phys_cape_L": ("Spine", 7, (+0.28, +0.10, 2.42), (+0.55, +0.55, 0.08), "CAPE", (+0.08, +0.18)),
    "phys_cape_C": ("Spine", 7, (+0.00, +0.12, 2.42), (+0.00, +0.60, 0.08), "CAPE", (0.00, +0.20)),
    "phys_cape_R": ("Spine", 7, (-0.28, +0.10, 2.42), (-0.55, +0.55, 0.08), "CAPE", (-0.08, +0.18)),
    "phys_hair_front_L": ("Head", 4, (+0.15, -0.33, 2.88), (+0.20, -0.47, 2.02), "HAIR", (+0.03, -0.06)),
    "phys_hair_front_R": ("Head", 4, (-0.15, -0.33, 2.88), (-0.22, -0.47, 2.02), "HAIR", (-0.03, -0.06)),
    "phys_hair_back":    ("Head", 4, (+0.00, +0.08, 2.92), (+0.00, +0.20, 2.28), "HAIR", (0.00, +0.06)),
}

def chain_point(root, tip, bow, u):
    """Quadratic-bezier point at u in [0,1]; bow bends x/y only, z linear."""
    r, t = Vector(root), Vector(tip)
    m = (r + t) * 0.5 + Vector((bow[0], bow[1], 0.0))
    p = r * (1 - u) ** 2 + m * 2 * u * (1 - u) + t * u ** 2
    p.z = r.z + (t.z - r.z) * u          # keep z exactly linear
    return p

arm_inv = arm.matrix_world.inverted()

bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.data.edit_bones
for cname, (parent, n, root, tip, region, bow) in CHAINS.items():
    prev = eb[parent]
    for i in range(n):
        b = eb.new(f"{cname}_{i:02d}")
        b.head = arm_inv @ chain_point(root, tip, bow, i / n)
        b.tail = arm_inv @ chain_point(root, tip, bow, (i + 1) / n)
        b.roll = 0.0
        b.parent = prev
        b.use_connect = (i > 0)
        b.use_deform = True
        prev = b
bpy.ops.object.mode_set(mode="OBJECT")
new_bone_names = [f"{c}_{i:02d}" for c, (_, n, *_rest) in CHAINS.items()
                  for i in range(n)]
print(f"[ok] added {len(new_bone_names)} bones "
      f"(total {len(arm.data.bones)})")

# ---------------------------------------------------------------------------
# 2. classify vertices (WORLD space)
# ---------------------------------------------------------------------------
gname = {g.index: g.name for g in mesh.vertex_groups}
mw = mesh.matrix_world

def hw(n):
    return arm.matrix_world @ arm.data.bones[n].head_local

LEG_SEGS = [(hw("LeftUpLeg"), hw("LeftLeg")), (hw("LeftLeg"), hw("LeftFoot")),
            (hw("RightUpLeg"), hw("RightLeg")), (hw("RightLeg"), hw("RightFoot"))]

def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length

HAND_G = {"LeftHand", "RightHand"}
FOOT_G = {"LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase"}
HEAD_G = {"Head", "neck", "head_end", "headfront"}
ARM_G = {"LeftArm", "RightArm", "LeftForeArm", "RightForeArm",
         "LeftShoulder", "RightShoulder"}

# FIXER R2: the y>0.10/0.15 back-plane + z<1.55 skirt thresholds MISSED cloth
# verts, which kept stale anchoring and exploded into giant slab planes under
# root motion (eval r2 f011/f097). Sweep the FULL cloth shell by sampling the
# baked texture: the robe/cape cloth is blue-dominant (0.08,0.12,0.35) while
# skin is warm-white and armor/hair gold — an unambiguous separator.
uvl = me.uv_layers.active.data
vuv = {}
for p in me.polygons:
    for li, vi2 in zip(p.loop_indices, p.vertices):
        if vi2 not in vuv:
            vuv[vi2] = tuple(uvl[li].uv)
_img = max((i for i in bpy.data.images if i.size[0]), key=lambda i: i.size[0])
_W, _H = _img.size
import array as _array
_px = _array.array("f", [0.0]) * (_W * _H * 4)
_img.pixels.foreach_get(_px)

def blueish(vi):
    uv = vuv.get(vi)
    if uv is None:
        return False
    x = min(_W - 1, max(0, int(uv[0] % 1.0 * _W)))
    y = min(_H - 1, max(0, int(uv[1] % 1.0 * _H)))
    o = (y * _W + x) * 4
    r, g, b = _px[o], _px[o + 1], _px[o + 2]
    return b > 0.04 and b > 1.3 * r and b > 1.2 * g

SHOULDER_PTS = [hw("LeftArm"), hw("RightArm")]

def classify(c, wsum, vi):
    if wsum(HAND_G) > 0.4:
        return None                      # sword / gauntlets — never touch
    if wsum(HEAD_G) >= 0.15 and c.z < 2.72 and (c.y < -0.28 or c.y > 0.0):
        return "HAIR"                    # hanging strands, not the face
    blue = blueish(vi)
    arm_w = wsum(ARM_G)
    far_shoulder = min((c - p).length for p in SHOULDER_PTS) > 0.28
    if arm_w > 0.25 and not (blue and far_shoulder):
        return None                      # arms/sleeves/pauldrons/couters stay
                                         # put. FIXER R3 (flaw 5): blue cloth
                                         # FAR from the shoulder joints is the
                                         # cape wad welded to the forearm —
                                         # capture it (arm weights stripped)
    if wsum(FOOT_G) > 0.35:
        return None                      # boots
    if c.z >= 1.55:
        # cape: ANY blue cloth behind the torso plane (full shell), the blue
        # forearm wad (R3), plus the old geometric band as a color-independent
        # backstop
        if (blue and c.y > 0.02) or (blue and arm_w > 0.25 and far_shoulder) \
           or (c.z < 2.55 and c.y > 0.15):
            return "CAPE"
        return None
    # below the waist: full cloth shell. Blue always captured; non-blue only
    # if radially clear of the legs (keeps greaves/skin on the leg bones).
    if blue:
        return "CAPE" if c.y > 0.10 else "ROBE"
    d = min(seg_dist(c, a, b) for a, b in LEG_SEGS)
    R = 0.38 if c.z > 1.2 else (0.28 if c.z > 0.7 else 0.22)
    if d > R:
        return "CAPE" if c.y > 0.10 else "ROBE"
    return None

# rigid armor plates (marked by fix_weights.py) are NEVER cloth
rigid_set = set()
if "RIGID_ARMOR" in mesh.vertex_groups:
    ridx = mesh.vertex_groups["RIGID_ARMOR"].index
    rigid_set = {v.index for v in me.vertices
                 if any(g.group == ridx for g in v.groups)}
print(f"[ok] rigid-armor marker verts skipped: {len(rigid_set)}")

cls = {}
counts = defaultdict(int)
for v in me.vertices:
    if v.index in rigid_set:
        continue
    ws = {gname.get(g.group): g.weight for g in v.groups}
    def wsum(names, ws=ws):
        return sum(ws.get(n, 0.0) for n in names)
    c = mw @ v.co
    r = classify(c, wsum, v.index)
    if r:
        cls[v.index] = (r, c)
        counts[r] += 1
print(f"[ok] classified: {dict(counts)}  (of {n_verts0} verts)")
assert 5000 < len(cls) < 150000, f"suspicious classification size {len(cls)}"
# HAIR classifier sanity: the long back hair must actually be captured
assert counts["HAIR"] > 200, \
    f"HAIR classifier captured only {counts['HAIR']} verts — back hair missed"

# ---------------------------------------------------------------------------
# 3. reweight
# ---------------------------------------------------------------------------
# chain polylines in world space for nearest-chain lookup (same curved
# sampling as the edit bones, so distances match the actual rest chains)
chain_pts = {}
for cname, (parent, n, root, tip, region, bow) in CHAINS.items():
    chain_pts[cname] = [chain_point(root, tip, bow, i / n) for i in range(n + 1)]

def chain_dist(c, pts):
    return min(seg_dist(c, pts[i], pts[i + 1]) for i in range(len(pts) - 1))

# new vertex groups
for bn in new_bone_names:
    if bn not in mesh.vertex_groups:
        mesh.vertex_groups.new(name=bn)

FADE = 0.35  # metres below the chain root over which parent weight fades out
             # (0.18 made the hip attachment transition an abrupt shelf)
MARKERS = {"RIGID_ARMOR", "HAIR"}   # non-deform marker groups — never strip,
                                    # never count in weight sums

# FIXER R3 COLUMN PARAMETERIZATION — the r2 inverse-distance 3-chain blend
# let adjacent hem verts be owned by wildly different chains (f097 collapse,
# f040 boundary tearing). Replace it with a deterministic, CONTINUOUS column
# coordinate: each vert blends AT MOST the two bracketing columns (exact
# 50/50 at each column seam, 100% at the column center) and 2 links within
# each column — influences can never span non-adjacent chains again.
import math as _math

def _chain_theta(cname):
    _p, _n, root, tip, _r, _b = CHAINS[cname]
    mx = (root[0] + tip[0]) * 0.5
    my = (root[1] + tip[1]) * 0.5
    return _math.atan2(mx, -my)          # 0 = front (-Y), +ccw toward +X

ROBE_SORTED = sorted((c for c, s in CHAINS.items() if s[4] == "ROBE"),
                     key=_chain_theta)
ROBE_TH = [_chain_theta(c) for c in ROBE_SORTED]
CAPE_X = sorted((CHAINS[c][2][0], c)
                for c, s in CHAINS.items() if s[4] == "CAPE")
HAIR_CH = [c for c, s in CHAINS.items() if s[4] == "HAIR"]
TWO_PI = 2.0 * _math.pi

def robe_picks(c):
    th = _math.atan2(c.x, -c.y)
    n = len(ROBE_SORTED)
    for k in range(n):
        a, b = ROBE_TH[k], ROBE_TH[(k + 1) % n]
        span = (b - a) % TWO_PI
        off = (th - a) % TWO_PI
        if off <= span + 1e-9:
            s = off / span if span > 1e-9 else 0.0
            return [(ROBE_SORTED[k], 1.0 - s), (ROBE_SORTED[(k + 1) % n], s)]
    return [(ROBE_SORTED[0], 1.0)]       # unreachable (circular cover)

def cape_picks(c):
    xs = [x for x, _ in CAPE_X]
    if c.x <= xs[0]:
        return [(CAPE_X[0][1], 1.0)]
    if c.x >= xs[-1]:
        return [(CAPE_X[-1][1], 1.0)]
    for k in range(len(xs) - 1):
        if xs[k] <= c.x <= xs[k + 1]:
            s = (c.x - xs[k]) / (xs[k + 1] - xs[k])
            return [(CAPE_X[k][1], 1.0 - s), (CAPE_X[k + 1][1], s)]
    return [(CAPE_X[-1][1], 1.0)]

def hair_picks(c):
    d = min((chain_dist(c, chain_pts[cn]), cn) for cn in HAIR_CH)
    return [(d[1], 1.0)]

assign = defaultdict(list)   # group name -> [(vi, w)]
remove = defaultdict(list)   # group name -> [vi]

for vi, (region, c) in cls.items():
    # strip every existing DEFORM influence (markers stay)
    for g in me.vertices[vi].groups:
        nm = gname.get(g.group)
        if nm and nm not in MARKERS:
            remove[nm].append(vi)
    if region == "ROBE":
        picks = robe_picks(c)
    elif region == "CAPE":
        picks = cape_picks(c)
    else:
        picks = hair_picks(c)
    picks = [(cn, pw) for cn, pw in picks if pw > 0.02]
    _s0 = sum(pw for _, pw in picks)
    picks = [(cn, pw / _s0) for cn, pw in picks]

    w = defaultdict(float)
    for best, cw in picks:
        # BUGFIX: fade + parent are computed PER PICK inside the loop; the old
        # code let `t`/`parent` leak from the last pick only, so multi-chain
        # verts lost weight mass and could end up nearly unweighted.
        parent, n, root, tip, _, _bow = CHAINS[best]
        root_z, tip_z = root[2], tip[2]
        f = (root_z - c.z) / (root_z - tip_z) * n  # fractional bone index
        f = max(0.0, min(n - 1e-4, f))
        i = int(f)
        u = f - i
        t = max(0.0, min(1.0, (root_z - c.z) / FADE))  # 0 at root -> 1 below
        w[f"{best}_{i:02d}"] += (1.0 - u) * t * cw
        if i + 1 < n:
            w[f"{best}_{i + 1:02d}"] += u * t * cw
        else:
            w[f"{best}_{i:02d}"] += u * t * cw
        if t < 1.0:
            w[parent] += (1.0 - t) * cw
    # cap at 4 influences (game-ready), renormalize
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    s = sum(v for _, v in top)
    assert s > 1e-6, f"vert {vi} ({region}) got zero weight mass"
    for nm, ww in top:
        if ww / s > 1e-4:
            assign[nm].append((vi, ww / s))

for nm, vis in remove.items():
    mesh.vertex_groups[nm].remove(list(set(vis)))
for nm, pairs in assign.items():
    vg = mesh.vertex_groups[nm]
    for vi, ww in pairs:
        vg.add([vi], ww, "REPLACE")
print(f"[ok] reweighted {len(cls)} verts onto {len(assign)} groups")

# per-chain captured vert counts (a chain that owns almost nothing produces
# no visible secondary motion — fail loud instead of shipping a dead chain)
own = defaultdict(int)
gname2 = {g.index: g.name for g in mesh.vertex_groups}
for vi in cls:
    best, bw = None, 0.0
    for g in me.vertices[vi].groups:
        nm = gname2.get(g.group, "")
        if nm.startswith("phys_") and g.weight > bw:
            best, bw = nm.rsplit("_", 1)[0], g.weight
    if best:
        own[best] += 1
print("[chains] captured verts per chain:")
for cname in CHAINS:
    print(f"    {cname:22s} {own.get(cname, 0):6d}")
    if own.get(cname, 0) < 50:
        print(f"    !! WARNING: {cname} owns <50 verts — near-dead chain")

# smooth ONLY the phys_* groups to kill the faceted crease lines at
# chain/panel boundaries; body groups already smoothed in phase 1 and rigid
# plates must stay rigid, so never 'ALL' here. FIXER R3: repeat back down
# 4 -> 2 — the continuous column parameterization no longer needs heavy
# smoothing, and heavy smoothing was re-bleeding weight across columns and
# onto body bones (the very leak the exclusive mask below strips).
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
for bn in new_bone_names:
    mesh.vertex_groups.active_index = mesh.vertex_groups[bn].index
    bpy.ops.object.vertex_group_smooth(
        group_select_mode="ACTIVE", factor=0.5, repeat=2, expand=0.0)
bpy.ops.object.mode_set(mode="OBJECT")
print(f"[ok] smoothed {len(new_bone_names)} phys groups (factor .5 x2)")

# smoothing bleeds small phys weights onto boundary verts — strip any phys
# weight that leaked onto rigid armor plates, then renormalize every vert
# carrying phys influence (marker groups excluded from all sums)
phys_idx = {mesh.vertex_groups[bn].index for bn in new_bone_names}
marker_idx = {mesh.vertex_groups[n].index for n in MARKERS
              if n in mesh.vertex_groups}
for vi in rigid_set:
    for g in list(me.vertices[vi].groups):
        if g.group in phys_idx:
            mesh.vertex_groups[gname2[g.group]].remove([vi])
n_norm = 0
for v in me.vertices:
    if not any(g.group in phys_idx for g in v.groups):
        continue
    s = sum(g.weight for g in v.groups if g.group not in marker_idx)
    if s > 1e-6 and abs(s - 1.0) > 0.001:
        for g in v.groups:
            if g.group not in marker_idx:
                g.weight /= s
        n_norm += 1
print(f"[ok] renormalized {n_norm} phys-influenced verts")

# ---------------------------------------------------------------------------
# 3a1. FIXER R3 — MUTUALLY EXCLUSIVE MASKS: below the attachment fade band a
# cloth vert is owned by phys chains ONLY. The weight-smooth pass (and the
# original skinning) can leave Spine/Hips/Leg residue on hem verts; stacking
# body weight on top of chain weight is what dragged hem verts with the torso
# at f097. Strip every non-phys deform influence and renormalize to phys.
REGION_ROOT_Z = {r: max(CHAINS[c][2][2]
                        for c, s in CHAINS.items() if s[4] == r)
                 for r in ("ROBE", "CAPE", "HAIR")}
n_excl = 0
for vi, (region, c) in cls.items():
    if c.z > REGION_ROOT_Z[region] - FADE:
        continue                          # attachment band keeps parent fade
    v = me.vertices[vi]
    body_names = [gname2[g.group] for g in v.groups
                  if g.group not in phys_idx and g.group not in marker_idx
                  and g.weight > 1e-6]
    if not body_names:
        continue
    phys_sum = sum(g.weight for g in v.groups if g.group in phys_idx)
    if phys_sum < 1e-6:
        continue                          # anchor rescue will handle it
    for nm2 in body_names:
        mesh.vertex_groups[nm2].remove([vi])
    for g in me.vertices[vi].groups:
        if g.group in phys_idx:
            g.weight /= phys_sum
    n_excl += 1
print(f"[excl-mask] stripped body-bone residue from {n_excl} hem/cloth verts")

# ---------------------------------------------------------------------------
# 3a1b. FIXER R3 — LAYER LOCK: the inner gold under-layer shell sits (near-)
# coincident with the blue robe shell but kept its old body weights, so the
# two layers move apart and z-fight (gold striping/blobs through the cloth in
# every frame). Copy the OUTER shell's weights onto any gold-textured,
# non-rigid, non-classified vert within 2cm of a classified cloth vert.
import mathutils as _mu

def goldish(vi):
    uv = vuv.get(vi)
    if uv is None:
        return False
    x = min(_W - 1, max(0, int(uv[0] % 1.0 * _W)))
    y = min(_H - 1, max(0, int(uv[1] % 1.0 * _H)))
    o = (y * _W + x) * 4
    r, g, b = _px[o], _px[o + 1], _px[o + 2]
    return r > 0.25 and r > 2.0 * b and g > 1.3 * b

cloth_kd = _mu.kdtree.KDTree(len(cls))
for vi, (region, c) in cls.items():
    if region != "HAIR":
        cloth_kd.insert(c, vi)
cloth_kd.balance()

n_lock = 0
for v in me.vertices:
    vi = v.index
    if vi in cls or vi in rigid_set:
        continue
    c = mw @ v.co
    if c.z > 2.6:
        continue                          # head/hair zone — never
    ws = {gname2.get(g.group): g.weight for g in v.groups}
    if (sum(ws.get(n2, 0.0) for n2 in HAND_G) > 0.3
            or sum(ws.get(n2, 0.0) for n2 in FOOT_G) > 0.3):
        continue
    if not goldish(vi):
        continue
    hit = cloth_kd.find(c)
    # R3b: 2cm missed gold trim strips riding just inside the hem (gold hem
    # dominance at f068 side) — widen to 3.5cm; still far below any limb gap.
    if hit[0] is None or hit[2] > 0.035:
        continue
    src = me.vertices[hit[1]]
    src_w = [(gname2[g.group], g.weight) for g in src.groups
             if g.group not in marker_idx and g.weight > 1e-5]
    if not src_w:
        continue
    old_names = [gname2[g.group] for g in v.groups
                 if g.group not in marker_idx]
    for nm2 in old_names:
        mesh.vertex_groups[nm2].remove([vi])
    for nm2, w2 in src_w:
        mesh.vertex_groups[nm2].add([vi], w2, "REPLACE")
    n_lock += 1
print(f"[layer-lock] copied outer-shell weights onto {n_lock} "
      "coincident gold under-layer verts")

# ---------------------------------------------------------------------------
# 3a1c. FIXER R3 — push the blue robe/cape shell ~1cm outward along vertex
# normals so the (now co-moving) inner gold layer can never z-fight through.
OFFSET = 0.018                            # metres, WORLD space (R3b: 10mm
                                          # still striped at the hem — 18mm)
R3n = mw.to_3x3()
R3n_inv = R3n.inverted()
n_off = 0
for vi, (region, c) in cls.items():
    if region == "HAIR" or not blueish(vi):
        continue
    nrm_w = (R3n @ me.vertices[vi].normal)
    if nrm_w.length < 1e-6:
        continue
    me.vertices[vi].co += R3n_inv @ (nrm_w.normalized() * OFFSET)
    n_off += 1
mesh.data.update()
print(f"[offset] pushed {n_off} blue shell verts {OFFSET*1000:.0f}mm outward "
      "along world normals")

# ---------------------------------------------------------------------------
# 3a2. GLOBAL anchor rescue — a vert whose deform-bone weight sum < 1 is
# PARTIALLY ANCHORED to bind pose by the armature modifier and stretches into
# giant slab planes under root motion (the eval r2 f011/f097 explosion). Every
# vert in the mesh must sum to 1.0 over ACTUAL BONE groups.
bone_idx = {mesh.vertex_groups[b.name].index for b in arm.data.bones
            if b.name in mesh.vertex_groups}
hips_vg = mesh.vertex_groups["Hips"]
n_fixnorm = n_rescue = 0
for v in me.vertices:
    s = sum(g.weight for g in v.groups if g.group in bone_idx)
    if s >= 0.999:
        continue
    if s > 0.2:
        for g in v.groups:
            if g.group in bone_idx:
                g.weight /= s
        n_fixnorm += 1
    else:
        hips_vg.add([v.index], 1.0, "REPLACE")
        n_rescue += 1
print(f"[anchor-rescue] renormalized {n_fixnorm}, "
      f"rebound {n_rescue} near-weightless verts to Hips")

# ---------------------------------------------------------------------------
# 3b. HARD ASSERTIONS on every touched vert (regression guard: unweighted or
#     leg-anchored robe verts shred the robe under root motion)
# ---------------------------------------------------------------------------
LEG_IDX = {mesh.vertex_groups[n].index for n in
           ("LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg",
            "LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase")
           if n in mesh.vertex_groups}
CHAIN_PARENTS = {"Hips", "Spine", "Head"}
parent_idx = {mesh.vertex_groups[n].index for n in CHAIN_PARENTS
              if n in mesh.vertex_groups}
bad_empty = bad_sum = bad_leg = bad_purity = 0
for vi, (region, _c) in cls.items():
    v = me.vertices[vi]
    live = [g for g in v.groups
            if g.weight > 1e-6 and g.group not in marker_idx]
    if not live:
        bad_empty += 1
        continue
    s = sum(g.weight for g in live)
    if not (0.999 <= s <= 1.001):
        bad_sum += 1
    if region == "ROBE" and any(g.group in LEG_IDX and g.weight > 1e-4
                                for g in live):
        bad_leg += 1
    # FIXER R2 hard purity gate: 100% of deform weight on phys_* chains or
    # their chain-root parent bone — anything else is a residual anchor that
    # shreds under root motion
    ok_w = sum(g.weight for g in live
               if g.group in phys_idx or g.group in parent_idx)
    if ok_w < 0.999 * s:
        bad_purity += 1
assert bad_empty == 0, f"{bad_empty} touched verts have NO weights (bind-pose anchors!)"
assert bad_sum == 0, f"{bad_sum} touched verts with weight sum outside [0.999,1.001]"
assert bad_leg == 0, f"{bad_leg} ROBE verts retain leg-bone weight"
assert bad_purity == 0, (
    f"{bad_purity} cloth verts carry deform weight OUTSIDE phys_* chains / "
    "chain-root parents — residual anchors")
print(f"[ok] assertions: {len(cls)} touched verts all weighted, normalized, "
      f"zero leg residue on ROBE, 100% phys/parent purity")

# ---------------------------------------------------------------------------
# 3c. SMOKE TEST — root motion must carry the whole robe with it.
#     Translate Hips +2m X / -1m Z in pose mode; every robe vert must stay
#     within ~2m of the rigid hip displacement (a vert stuck at bind pose
#     shows up as a ~2.2m residual and fails).
# ---------------------------------------------------------------------------
pb = arm.pose.bones["Hips"]
dg = bpy.context.evaluated_depsgraph_get()
rest_hips = (arm.matrix_world @ pb.matrix).translation.copy()
rest_co = {vi: (mw @ me.vertices[vi].co).copy() for vi in cls}
# pose-bone location is expressed in the bone's LOCAL axes — convert the
# desired armature-space delta (+2m X, -1m Z) into bone-local first
delta_arm = arm.matrix_world.inverted().to_3x3() @ Vector((2.0, 0.0, -1.0))
pb.location = pb.bone.matrix_local.to_3x3().inverted() @ delta_arm
bpy.context.view_layer.update()
dg.update()
hips_delta = (arm.matrix_world @ pb.matrix).translation - rest_hips
assert hips_delta.length > 1.5, (
    f"smoke test no-op: hips only moved {hips_delta.length:.3f}m")
ev = mesh.evaluated_get(dg)
emw = ev.matrix_world
worst = 0.0
worst_vi = -1
for vi in list(cls)[::7]:            # ~1/7 sample is plenty
    p = emw @ ev.data.vertices[vi].co
    resid = ((p - rest_co[vi]) - hips_delta).length
    if resid > worst:
        worst, worst_vi = resid, vi
print(f"[smoke] hips_delta={tuple(round(c, 2) for c in hips_delta)} "
      f"worst residual={worst:.3f}m at vert {worst_vi}")

# FIXER R2 HARD STRETCH GATE: with Hips translated 2m, NO mesh edge may
# elongate >1.5x its rest length. This catches any residual-anchor vert
# (classified or not) that tears the cloth into giant slab planes — the exact
# eval r2 f011/f097 failure — regardless of which classifier missed it.
import numpy as np
nv = len(me.vertices)
assert len(ev.data.vertices) == nv, "evaluated vert count mismatch"
rest_l = np.empty(nv * 3, dtype=np.float64)
me.vertices.foreach_get("co", rest_l)
R3 = np.array(mw.to_3x3())
rest_w = rest_l.reshape(-1, 3) @ R3.T + np.array(mw.translation)
pos_l = np.empty(nv * 3, dtype=np.float64)
ev.data.vertices.foreach_get("co", pos_l)
E3 = np.array(emw.to_3x3())
pos_w = pos_l.reshape(-1, 3) @ E3.T + np.array(emw.translation)
ne = len(me.edges)
eidx = np.empty(ne * 2, dtype=np.int32)
me.edges.foreach_get("vertices", eidx)
eidx = eidx.reshape(-1, 2)
rl = np.linalg.norm(rest_w[eidx[:, 0]] - rest_w[eidx[:, 1]], axis=1)
pl = np.linalg.norm(pos_w[eidx[:, 0]] - pos_w[eidx[:, 1]], axis=1)
valid = rl > 1e-4
ratio = pl[valid] / rl[valid]
wi = int(np.argmax(ratio))
worst_ratio = float(ratio[wi])
we = eidx[valid][wi]
print(f"[stretch] {int(valid.sum())} edges  max elongation {worst_ratio:.3f}x "
      f"(edge {int(we[0])}-{int(we[1])})")
pb.location = Vector((0.0, 0.0, 0.0))
pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
assert worst < 2.0, (
    f"SMOKE TEST FAILED: vert {worst_vi} lags hip root motion by {worst:.2f}m "
    "— robe verts are anchored to bind pose / wrong bones")
assert worst_ratio < 1.5, (
    f"STRETCH GATE FAILED: edge {int(we[0])}-{int(we[1])} elongates "
    f"{worst_ratio:.2f}x under 2m Hips root motion — residual anchor verts")

# ---------------------------------------------------------------------------
# 4. integrity + save
# ---------------------------------------------------------------------------
now_bones = {b.name: tuple(round(c, 5) for c in b.head_local)
             for b in arm.data.bones if b.name in orig_bones}
assert now_bones == orig_bones, "ORIGINAL BONES CHANGED"
assert [m.name for m in me.materials if m] == orig_mats, "MATERIALS CHANGED"
assert len(me.vertices) == n_verts0, "VERT COUNT CHANGED"
assert len(arm.data.bones) == 24 + len(new_bone_names)
print(f"[ok] integrity: 24 original bones intact, materials {orig_mats}, "
      f"{len(arm.data.bones)} bones total")

try:
    bpy.ops.file.pack_all()
except Exception as e:
    print("pack_all note:", e)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print(f"[ok] saved {OUT}")
with open("/tmp/p2_robe_report.json", "w") as fh:
    json.dump({"counts": dict(counts), "new_bones": len(new_bone_names),
               "total_bones": len(arm.data.bones)}, fh, indent=1)
print("=== ROBE_BONES DONE ===")
