"""
fix_face.py — Phase 2 (round 2): reshape the face toward body-concepts/god_C.png.
Narrower face, slimmer cheeks, sharper chiseled jaw + cheekbones,
more masculine, refined straight nose.

Round-2 change: ALL broad narrowing is gated to the FRONT FACE only
(fgate on y/|x|). Round 1 narrowed every vert above the neck, which
squashed the hair shells into a melted-wax blob. Hair geometry is now
completely untouched; only jaw/cheek/chin/nose/brow/lip zones move.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/fix_face.py 2>&1

Invariants:
  - Loads models/godwyn_sword.blend (Phase 1 output). Armature 'Armature'
    (24 bones) + char1 skinning + Godwyn_Sword bone-parent stay intact.
  - Baked textures / UVs / material untouched — VERTEX MOVES ONLY.
  - Shape-key-safe edit pattern (mesh currently has none, but guarded).
  - Face region only: z above the neck blend zone; body untouched.
"""
import bpy
import os
import math
from mathutils import Vector

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND_IN = os.path.join(REPO, "models", "godwyn_sword.blend")
BLEND_OUT = os.path.join(REPO, "models", "godwyn_face.blend")
PREVIEW_DIR = "/tmp/face_previews"
ROUND = int(os.environ.get("FACE_ROUND", "1"))

# ─────────────────────────────────────────────────────────────────
# TUNABLES (iterated per critique round)
# All coordinates are WORLD space. Head joint ~z 2.85, crown z 3.20,
# face front y ~-0.47, head width incl. hair ~0.40.
# ─────────────────────────────────────────────────────────────────
P = dict(
    # vertical blend: 0 effect at/below z_lo, full at/above z_hi
    z_lo=2.60, z_hi=2.76,
    # FRONT-FACE GATE (round 2): the round-1 global narrow squashed the HAIR
    # shells into a melted blob. All broad narrowing is now gated to the
    # front face only — full effect for y < face_y_full, zero by y >
    # face_y_zero, and fading out beyond |x| > face_x_full toward face_x_zero.
    # Hair (top/sides/back shells) is left completely untouched.
    face_y_full=-0.36, face_y_zero=-0.24,
    face_x_full=0.13, face_x_zero=0.20,
    # 1) face narrow: x *= (1 - narrow_amt) at full weight (front face only)
    narrow_amt=0.10,
    # extra narrowing of the LOWER face (jowls/jaw region), ramping from
    # z_jaw_top (0) down to chin (full)
    lower_narrow_amt=0.18, z_jaw_top=3.00,
    # 2) cheek slim: inward push (m) of front-side cheek verts,
    # gaussian in z about cheek_z, active for |x| in cheek band, front y
    cheek_amt=0.022, cheek_z=2.96, cheek_sig=0.070,
    cheek_x_min=0.045, cheek_x_max=0.17, cheek_y_front=-0.30,
    # 3) cheekbone emphasis: small outward push just under eye line
    cbone_amt=0.018, cbone_z=3.03, cbone_sig=0.035,
    cbone_x_min=0.06, cbone_x_max=0.16, cbone_y_front=-0.30,
    # 4) chin: slight forward+down extension for a chiseled point
    chin_amt_y=-0.022, chin_amt_z=-0.006,
    chin_z=2.79, chin_sig=0.050, chin_x_max=0.055, chin_y_front=-0.30,
    # 5) nose: narrow + straighten bridge
    nose_narrow=0.20,          # fraction of x removed on nose verts
    nose_x_max=0.045, nose_y_front=-0.42, nose_z_min=2.90, nose_z_max=3.05,
    # 6) brow ridge: subtle forward push for a heavier masculine brow
    # (round 4: sig tightened 0.028 -> 0.024 for a crisper band)
    brow_amt_y=-0.009, brow_z=3.07, brow_sig=0.024,
    brow_x_max=0.10, brow_y_front=-0.36,
    # 7) mouth/muzzle pull-back: reduce forward bulge around the lips
    mouth_amt_y=0.010, mouth_z=2.885, mouth_sig=0.030,
    mouth_x_max=0.06, mouth_y_front=-0.40,
    # 8) eye de-sunken: gentle forward lift of the eye band (concept has
    # bright, healthy eyes — not hollow sockets)
    # (round 4: sig tightened 0.026 -> 0.022, x_max 0.135 -> 0.13)
    eye_amt_y=-0.011, eye_z=3.045, eye_sig=0.022,
    eye_x_min=0.04, eye_x_max=0.13, eye_y_front=-0.33,
    # 9) jawline chisel (round 3): outward push at the jaw corner for a
    # defined mandible angle, plus a slight under-jaw tuck above the chin
    jawc_amt=0.012, jawc_z=2.885, jawc_sig=0.040,
    jawc_x_min=0.05, jawc_x_max=0.115, jawc_y_front=-0.26,
    jawtuck_amt=0.010, jawtuck_z=2.83, jawtuck_sig=0.030,
)

# per-round overrides
if ROUND >= 2:
    pass  # edited in place per round instead

# ─────────────────────────────────────────────────────────────────
# 0. Load Phase-1 blend
# ─────────────────────────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
arm = bpy.data.objects.get("Armature")
body = bpy.data.objects.get("char1")
sword = bpy.data.objects.get("Godwyn_Sword")
assert arm and body, "missing Armature/char1"
me = body.data
bones_before = sorted(b.name for b in arm.data.bones)
vgroups_before = sorted(g.name for g in body.vertex_groups)
uv_before = len(me.uv_layers)
mats_before = [m.name for m in me.materials]
print(f"[fix_face] loaded: body verts={len(me.vertices)} bones={len(bones_before)} "
      f"vgroups={len(vgroups_before)} uvs={uv_before} mats={mats_before} "
      f"shapekeys={me.shape_keys.key_blocks.keys() if me.shape_keys else None} "
      f"sword={'ok' if sword else 'MISSING'}")

mwm = body.matrix_world
mwm_inv = mwm.inverted()

# ── landmark report (world) ──────────────────────────────────────
cands = [(v.index, mwm @ v.co) for v in me.vertices if (mwm @ v.co).z > 2.75]
nose = min((c for c in cands if abs(c[1].x) < 0.05 and 2.85 < c[1].z < 3.05),
           key=lambda c: c[1].y)
chin = min((c for c in cands if abs(c[1].x) < 0.05 and c[1].y < -0.33 and c[1].z < 2.92),
           key=lambda c: c[1].z)
print(f"[fix_face] nose tip world={tuple(round(v,4) for v in nose[1])}")
print(f"[fix_face] chin world={tuple(round(v,4) for v in chin[1])}")

def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)

def gauss(z, mu, sig):
    return math.exp(-0.5 * ((z - mu) / sig) ** 2)

# ─────────────────────────────────────────────────────────────────
# 1. Compute per-vertex deltas (world space)
# ─────────────────────────────────────────────────────────────────
deltas = {}
n_touched = 0
for v in me.vertices:
    w = mwm @ v.co
    if w.z <= P["z_lo"]:
        continue
    wz = smooth((w.z - P["z_lo"]) / (P["z_hi"] - P["z_lo"]))  # neck blend
    dx = 0.0
    dy = 0.0
    dz = 0.0
    ax = abs(w.x)
    sx = 1.0 if w.x >= 0 else -1.0

    # front-face gate: hair shells (side/top/back, y behind face_y_zero or
    # wide of face_x_zero) get ZERO broad narrowing — no more melted hair
    fgate = smooth((P["face_y_zero"] - w.y) / (P["face_y_zero"] - P["face_y_full"])) \
        * smooth((P["face_x_zero"] - ax) / (P["face_x_zero"] - P["face_x_full"]))

    # 1) face narrow (front face only)
    k = P["narrow_amt"]
    # 1b) lower-face extra narrow (ramp below z_jaw_top toward chin)
    if w.z < P["z_jaw_top"]:
        t = smooth((P["z_jaw_top"] - w.z) / (P["z_jaw_top"] - chin[1].z + 1e-6))
        k += P["lower_narrow_amt"] * t
    dx += -w.x * k * wz * fgate

    # 2) cheek slim (front-side skin only)
    if (P["cheek_x_min"] < ax < P["cheek_x_max"]) and w.y < P["cheek_y_front"]:
        g = gauss(w.z, P["cheek_z"], P["cheek_sig"])
        band = smooth((ax - P["cheek_x_min"]) / 0.03) * smooth((P["cheek_x_max"] - ax) / 0.03)
        dx += -sx * P["cheek_amt"] * g * band * wz * fgate

    # 3) cheekbone emphasis
    if (P["cbone_x_min"] < ax < P["cbone_x_max"]) and w.y < P["cbone_y_front"]:
        g = gauss(w.z, P["cbone_z"], P["cbone_sig"])
        band = smooth((ax - P["cbone_x_min"]) / 0.02) * smooth((P["cbone_x_max"] - ax) / 0.02)
        dx += sx * P["cbone_amt"] * g * band * wz * fgate

    # 4) chin point
    if ax < P["chin_x_max"] and w.y < P["chin_y_front"]:
        g = gauss(w.z, P["chin_z"], P["chin_sig"])
        band = smooth((P["chin_x_max"] - ax) / 0.03)
        dy += P["chin_amt_y"] * g * band * wz
        dz += P["chin_amt_z"] * g * band * wz

    # 5) nose narrow (straighten by pulling toward midline)
    if ax < P["nose_x_max"] and w.y < P["nose_y_front"] and \
       P["nose_z_min"] < w.z < P["nose_z_max"]:
        band = smooth((P["nose_x_max"] - ax) / 0.02)
        dx += -w.x * P["nose_narrow"] * band * wz

    # 6) brow ridge forward
    if ax < P["brow_x_max"] and w.y < P["brow_y_front"]:
        g = gauss(w.z, P["brow_z"], P["brow_sig"])
        band = smooth((P["brow_x_max"] - ax) / 0.03)
        dy += P["brow_amt_y"] * g * band * wz

    # 7) mouth/muzzle pull-back (skip nose-tip zone above mouth)
    if ax < P["mouth_x_max"] and w.y < P["mouth_y_front"]:
        g = gauss(w.z, P["mouth_z"], P["mouth_sig"])
        band = smooth((P["mouth_x_max"] - ax) / 0.03)
        dy += P["mouth_amt_y"] * g * band * wz

    # 8) eye de-sunken lift
    if (P["eye_x_min"] < ax < P["eye_x_max"]) and w.y < P["eye_y_front"]:
        g = gauss(w.z, P["eye_z"], P["eye_sig"])
        band = smooth((ax - P["eye_x_min"]) / 0.02) * smooth((P["eye_x_max"] - ax) / 0.02)
        dy += P["eye_amt_y"] * g * band * wz

    # 9) jawline chisel: mandible-corner pop + under-jaw tuck
    if (P["jawc_x_min"] < ax < P["jawc_x_max"]) and w.y < P["jawc_y_front"]:
        g = gauss(w.z, P["jawc_z"], P["jawc_sig"])
        band = smooth((ax - P["jawc_x_min"]) / 0.02) * smooth((P["jawc_x_max"] - ax) / 0.02)
        dx += sx * P["jawc_amt"] * g * band * wz * fgate
    if ax < P["jawc_x_min"] + 0.02 and w.y < P["chin_y_front"]:
        g = gauss(w.z, P["jawtuck_z"], P["jawtuck_sig"])
        dy += P["jawtuck_amt"] * g * wz * 0.5  # slight pull-back under jaw

    if dx or dy or dz:
        neww = w + Vector((dx, dy, dz))
        deltas[v.index] = (mwm_inv @ neww) - v.co
        n_touched += 1

print(f"[fix_face] round={ROUND} touching {n_touched} verts")

# shape-key-safe apply
if me.shape_keys:
    for kb in me.shape_keys.key_blocks:
        for i, d in deltas.items():
            kb.data[i].co += d
for i, d in deltas.items():
    me.vertices[i].co += d
me.update()

# ─────────────────────────────────────────────────────────────────
# 1b. Round 4 (flaw 5): EYE/BROW SYMMETRY. The reshape bands are already
# |x|-mirrored, but the underlying mesh is rough/asymmetric in the eye and
# brow zones. Mirror-average each eye/brow vert with its nearest partner
# across x=0, gaussian-gated to the eye/brow bands only. Vertex moves
# only; deliberately gentle so the (good) overall face shape is untouched.
# ─────────────────────────────────────────────────────────────────
from mathutils import kdtree as _kdt
band = [v.index for v in me.vertices
        if (lambda w: 2.98 < w.z < 3.14 and w.y < -0.30 and abs(w.x) < 0.17)
        (mwm @ v.co)]
kt = _kdt.KDTree(len(band))
for i in band:
    kt.insert(mwm @ me.vertices[i].co, i)
kt.balance()
sym_target = {}
for i in band:
    w = mwm @ me.vertices[i].co
    co, j, dist = kt.find(Vector((-w.x, w.y, w.z)))
    if j is None or dist > 0.012:
        continue
    g = max(gauss(w.z, P["eye_z"], P["eye_sig"] * 1.4),
            gauss(w.z, P["brow_z"], P["brow_sig"] * 1.4))
    f = 0.5 * g
    if f < 0.02:
        continue
    tgt = (w + Vector((-co.x, co.y, co.z))) * 0.5   # pair midpoint, mirrored
    sym_target[i] = w + (tgt - w) * f
for i, t in sym_target.items():
    d = (mwm_inv @ t) - me.vertices[i].co
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            kb.data[i].co += d
    me.vertices[i].co += d
me.update()
print(f"[fix_face] round4 symmetry: mirror-averaged {len(sym_target)} "
      f"eye/brow verts (band={len(band)})")

# ─────────────────────────────────────────────────────────────────
# 2. Invariant checks
# ─────────────────────────────────────────────────────────────────
assert sorted(b.name for b in arm.data.bones) == bones_before, "bones changed!"
assert sorted(g.name for g in body.vertex_groups) == vgroups_before, "vgroups changed!"
assert len(me.uv_layers) == uv_before, "UVs changed!"
assert [m.name for m in me.materials] == mats_before, "materials changed!"
assert any(m.type == 'ARMATURE' for m in body.modifiers), "armature modifier lost!"
print("[fix_face] RIG INTACT: bones/vgroups/UVs/materials/armature-mod all preserved")

# ─────────────────────────────────────────────────────────────────
# 3. EEVEE previews
# ─────────────────────────────────────────────────────────────────
os.makedirs(PREVIEW_DIR, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
world = scene.world or bpy.data.worlds.new("PrevWorld")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.24, 0.26, 0.32, 1.0)
    bg.inputs[1].default_value = 1.3
for nm in ("PrevSun", "PrevFill", "PrevCam"):
    ob = bpy.data.objects.get(nm)
    if ob:
        bpy.data.objects.remove(ob, do_unlink=True)
sun = bpy.data.objects.new("PrevSun", bpy.data.lights.new("PrevSun", 'SUN'))
sun.data.energy = 4.2
sun.rotation_euler = (math.radians(55), 0, math.radians(-30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("PrevFill", bpy.data.lights.new("PrevFill", 'AREA'))
fill.data.energy = 120
fill.data.size = 2.0
face_c = Vector((0.0, -0.40, 2.99))
fill.location = face_c + Vector((0.3, -0.9, 0.2))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("PrevCam", bpy.data.cameras.new("PrevCam"))
scene.collection.objects.link(cam)
scene.camera = cam

def aim(frm, to):
    cam.location = frm
    cam.rotation_euler = (to - frm).to_track_quat('-Z', 'Y').to_euler()

shots = [
    ("face_front", face_c + Vector((0, -1.05, 0.02)), face_c, 80),
    ("face_34",    face_c + Vector((-0.65, -0.80, 0.05)), face_c, 80),
    ("face_side",  face_c + Vector((-1.00, 0.0, 0.02)), face_c, 80),
    ("face_close", face_c + Vector((0, -0.72, 0.02)), face_c, 80),
    ("full_front", Vector((0, -4.4, 1.6)), Vector((0, 0, 1.5)), 40),
]
for name, frm, to, lens in shots:
    cam.data.lens = lens
    aim(frm, to)
    scene.render.filepath = os.path.join(PREVIEW_DIR, f"r{ROUND}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[fix_face] rendered {scene.render.filepath}")

# ─────────────────────────────────────────────────────────────────
# 4. Save
# ─────────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print(f"[fix_face] saved {BLEND_OUT}")
print("[fix_face] DONE")
