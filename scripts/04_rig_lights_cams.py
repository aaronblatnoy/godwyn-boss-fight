"""
04_rig_lights_cams.py — Phase 4: Armature + lighting rig + cameras + Cycles
config, deform sanity check, then SAVE models/godwyn_phase1.blend.

This is the INTEGRATION phase: everything P5 (character sheet) and P6
(moveset poses) render is fixed here — rig topology, light rig, cameras,
render config, color management.

Loads the existing .blend from Phase 3 (which has the MPFB2 real body +
all dress/hair/sword objects with materials already assigned), then adds:

  1. ARMATURE "Godwyn_Armature": simple humanoid rig — 20 deform bones
       root (no deform), pelvis, spine.01, chest, neck, head,
       shoulder.L/R, upper_arm.L/R, forearm.L/R, hand.L/R,
       thigh.L/R, shin.L/R, foot.L/R.
     +X is Godwyn's RIGHT (sword side — HAND_R x ~+0.98).  Sane names
     throughout (export-friendly for Godot).
  2. PARENTING: Godwyn_Body / Godwyn_Armor / Godwyn_Tabard with AUTOMATIC
     WEIGHTS (bone-heat; envelope-weight fallback if bone-heat fails);
     Godwyn_Hair bone-parented rigidly to `head`;
     Godwyn_Sword bone-parented to `hand.R` (world transform preserved).
  3. LIGHTING RIG (SPEC 337-339): dramatic warm TOP-DOWN key
     (1.0,0.92,0.6 — Godwyn reads as the light source), subtle cool fill
     (shadow side not pure black), warm rim from behind to separate him
     from the void. The void crack stays as background accent.
     Dark-fantasy rig, NOT studio-neutral.
  4. CAMERAS (8, named): Cam_Front, Cam_ThreeQuarter_L, Cam_ThreeQuarter_R,
     Cam_Back, Cam_Side, Cam_Face, Cam_Sword, Cam_Sheet.
     COORDINATE NOTE: Body faces -Y (front = -Y hemisphere), so all
     front-facing cameras sit at negative Y.
  5. CYCLES CONFIG: GPU (OptiX->CUDA), 256 samples + denoise, 1440x2560
     portrait, film transparent OFF, AgX (Filmic fallback).
  6. DEFORM SANITY CHECK: apply a mild test pose (arm bend + spine rotation)
     and drive a face blendshape (Expr_BrowSorrow->0.6), render from
     Cam_ThreeQuarter_L -> renders/wip/04_deform_test.png, then RESET to
     rest pose before saving.
  7. SAVE models/godwyn_phase1.blend (clean rest-pose state).

INV-1 headless, INV-2 GPU asserted, INV-4 names, INV-5 reproducible (loads
committed .blend), INV-6 idempotent (clears armature/lights/cams by name),
INV-7 he is the light.
ANIMATABLE invariant: blendshapes preserved through binding; shape key values
reset to 0 (rest) before final save.

Run:
  blender --background --python scripts/04_rig_lights_cams.py
"""

import sys
import os
import math
import bpy
import mathutils
from mathutils import Vector

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

_REPO_ROOT   = os.path.expanduser("~/godwyn-boss-fight")
_WIP_DIR     = os.path.join(_REPO_ROOT, "renders", "wip")
_MODELS_DIR  = os.path.join(_REPO_ROOT, "models")
_BLEND_IN    = os.path.join(_MODELS_DIR, "godwyn_phase1.blend")
_BLEND_OUT   = os.path.join(_MODELS_DIR, "godwyn_phase1.blend")
_PREVIEW_OUT = os.path.join(_WIP_DIR, "04_lit.png")
_DEFORM_OUT  = os.path.join(_WIP_DIR, "04_deform_test.png")
os.makedirs(_WIP_DIR, exist_ok=True)
os.makedirs(_MODELS_DIR, exist_ok=True)

ARMATURE_NAME = "Godwyn_Armature"
SWORD_BONE    = "hand.R"

# ---------------------------------------------------------------------------
# LANDMARK COORDINATES (from 02_details.py — measured from MPFB2 body)
# Body faces -Y; +X = character's right (sword side).
# ---------------------------------------------------------------------------
# Body midline Z heights (from 01_base_mesh.py proportion constants)
# Godwyn is 3.2m total, these match the Skin+Subsurf-applied mesh.
_H   = 3.20   # total height
_LEG = _H * 0.435      # ~1.392  Z_HIP
_NAVEL   = _LEG + (_H * 0.310 * 0.22)   # ~1.610
_CHEST   = _LEG + (_H * 0.310 * 0.55)   # ~1.937
_SHOULDER = _LEG + (_H * 0.310 * 0.90)  # ~2.285
_NECK_BASE = _LEG + (_H * 0.310)        # ~2.384
_NECK_TOP  = _NECK_BASE + (_H * 0.115 * 0.35)   # ~2.513
_HEAD_TOP  = _H                          # 3.200
_KNEE      = _H * 0.220                  # ~0.704
_ANKLE     = _H * 0.054                  # ~0.173
_SW        = _H * 0.250                  # shoulder half-width ~0.80m

# ---------------------------------------------------------------------------
# HEROIC PROPORTION REMAP (fixer r5 blocker #8): 02_details applies a final
# proportion pass to ALL geometry — legs z*1.09 below the hip plane, whole
# figure renormalized to 3.2m, head -5% x. Every bind-space bone anchor /
# landmark here carries the SAME transform via _prop_pt().
# ---------------------------------------------------------------------------
_LEG_K  = 1.09
_LEG_Z0 = 1.392
_PROP_S = 3.20 / (3.20 + _LEG_Z0 * (_LEG_K - 1.0))


def _prop_pt(p):
    x, y, z = p
    z = z * _LEG_K if z <= _LEG_Z0 else z + _LEG_Z0 * (_LEG_K - 1.0)
    return (x * _PROP_S, y * _PROP_S, z * _PROP_S)


# Arm chain (outward 30° from vertical)
# fixer r5 blocker #8: segment lengths x1.16 to track the mesh arm stretch
# applied by 02_details (heroic proportions).
_ARM_ANGLE = math.radians(30.0)
# phase4 fixer r1 blocker #3: 1.16 -> 1.26, tracking 02_details ARM_K
_ARM_UPPER = _H * 0.340 * 0.46 * 1.26
_ARM_LOWER = _H * 0.340 * 0.38 * 1.26
_ARM_HAND  = _H * 0.340 * 0.16 * 1.26
_SH_X      = _SW * 0.50
_ELBOW_X   = _SH_X + math.sin(_ARM_ANGLE) * _ARM_UPPER
_ELBOW_Z   = _SHOULDER - math.cos(_ARM_ANGLE) * _ARM_UPPER
_WRIST_X   = _ELBOW_X + math.sin(_ARM_ANGLE * 0.7) * _ARM_LOWER
_WRIST_Z   = _ELBOW_Z - math.cos(_ARM_ANGLE * 0.7) * _ARM_LOWER
_HAND_X    = _WRIST_X + _ARM_HAND * math.sin(_ARM_ANGLE * 0.5)
_HAND_Z    = _WRIST_Z - _ARM_HAND * math.cos(_ARM_ANGLE * 0.5)

# ---------------------------------------------------------------------------
# BONE TABLE: (name, head, tail, parent, connect, deform)
# +X = Godwyn's RIGHT. All in world space (body at origin).
# ---------------------------------------------------------------------------

def _bone_table():
    bones = [
        # name        head                      tail                       parent      conn   deform
        ("root",      (0, 0, 0.0),              (0, 0, _KNEE * 0.5),      None,       False, False),
        ("pelvis",    (0, 0, _LEG * 0.97),      (0, 0, _NAVEL),           "root",     False, True),
        ("spine.01",  (0, 0, _NAVEL),           (0, 0, _CHEST),           "pelvis",   True,  True),
        ("chest",     (0, 0, _CHEST),           (0, 0, _NECK_BASE),       "spine.01", True,  True),
        ("neck",      (0, 0, _NECK_BASE),       (0, 0, _NECK_TOP),        "chest",    True,  True),
        ("head",      (0, 0, _NECK_TOP),        (0, 0, _HEAD_TOP),        "neck",     True,  True),
    ]
    for side, s in (("R", 1), ("L", -1)):
        bones += [
            (f"shoulder.{side}",  (s * 0.10, 0, _SHOULDER),  (s * _SH_X,    0, _SHOULDER),
             "chest",             False, True),   # pauldrons rigid-weight here (p5r2)
            (f"upper_arm.{side}", (s * _SH_X, 0, _SHOULDER), (s * _ELBOW_X, 0, _ELBOW_Z),
             f"shoulder.{side}",  True,  True),
            (f"forearm.{side}",   (s * _ELBOW_X, 0, _ELBOW_Z), (s * _WRIST_X, 0, _WRIST_Z),
             f"upper_arm.{side}", True,  True),
            (f"hand.{side}",      (s * _WRIST_X, 0, _WRIST_Z), (s * _HAND_X,  0, _HAND_Z),
             f"forearm.{side}",   True,  True),
            (f"thigh.{side}",     (s * _SW * 0.22, 0, _LEG),   (s * _SW * 0.14, 0, _KNEE),
             "pelvis",            False, True),
            (f"shin.{side}",      (s * _SW * 0.14, 0, _KNEE),  (s * _SW * 0.18, 0, _ANKLE),
             f"thigh.{side}",     True,  True),
            (f"foot.{side}",      (s * _SW * 0.18, 0, _ANKLE), (s * _SW * 0.18, 0.10, 0.005),
             f"shin.{side}",      True,  True),
        ]
    # fixer r5 blocker #8: every head/tail through the proportion remap so
    # the rig lands on the remapped mesh
    return [(n, _prop_pt(h), _prop_pt(t), par, conn, dfm)
            for (n, h, t, par, conn, dfm) in bones]


# ---------------------------------------------------------------------------
# HAND / FINGER CHAINS (p5r2 blocker #1: the rig had ZERO finger bones — the
# hand collapsed to a wafer under a wrist bend and no grip was posable).
# Each hand gets a 3-bone composite finger chain + a 2-bone thumb, placed
# along the CURLED finger centreline that 02_details sculpted (same curl
# math: rotate about the knuckle axis by max_deg * u^0.85). Bind-space
# landmarks match 02_details.py; the right palm normal is persisted on the
# sword ("palm_normal"), the knuckle line on the body (godwyn_knuckle_r/l).
# ---------------------------------------------------------------------------
# fixer r5 blocker #8: 02_details now stretches each arm +16% along its
# axis about the shoulder (ARM_K=1.16) and translates the hand RIGIDLY,
# THEN applies the heroic proportion remap — these bind-space landmarks
# carry the SAME two transforms in the same order.
_ARM_S     = Vector((0.40, 0.08, 2.285))
_ARM_AXIS  = (Vector((0.88, -0.19, 1.99)) - _ARM_S).normalized()
_ARM_DW    = (Vector((0.88, -0.19, 1.99)) - _ARM_S).length
_HAND_SHV  = _ARM_AXIS * ((_ARM_DW - 0.02) * 0.26)  # tracks ARM_K=1.26
_WRIST_LM  = Vector(_prop_pt(Vector((0.88, -0.19, 1.99)) + _HAND_SHV))
_HAND_LM   = Vector(_prop_pt(Vector((0.98, -0.28, 1.84)) + _HAND_SHV))
_HAND_SMAX = 0.36 * _PROP_S          # wrist->fingertip reach (bind, pre-curl)
_CURL_DEG  = {"R": 86.0, "L": 32.0}  # matches 02_details curl_fingers calls

FINGER_BONES = tuple(f"fingers.{i:02d}.{s}" for s in ("R", "L")
                     for i in (1, 2, 3))
THUMB_BONES  = tuple(f"thumb.{i:02d}.{s}" for s in ("R", "L") for i in (1, 2))


def _hand_frame(side):
    """Bind-space (W, f_dir, palm_n, curl_axis, knuckle p0) for one hand."""
    sgn = 1.0 if side == "R" else -1.0
    body  = bpy.data.objects["Godwyn_Body"]
    sword = bpy.data.objects.get("Godwyn_Sword")
    W = Vector((sgn * _WRIST_LM.x, _WRIST_LM.y, _WRIST_LM.z))
    H = Vector((sgn * _HAND_LM.x, _HAND_LM.y, _HAND_LM.z))
    f_dir = (H - W).normalized()
    if sword is not None and "palm_normal" in sword.keys():
        pn = Vector(sword["palm_normal"][:]).normalized()
        palm_n = pn if side == "R" else Vector((-pn.x, pn.y, pn.z))
    else:
        palm_n = Vector((0.0, -1.0, 0.0))
    axis = f_dir.cross(palm_n)
    axis = axis.normalized() if axis.length > 1e-6 else Vector((0, 0, 1))
    test = mathutils.Quaternion(axis, math.radians(8.0)) @ f_dir
    if (test - f_dir).dot(palm_n) < 0.0:
        axis = -axis
    kn = body.get(f"godwyn_knuckle_{side.lower()}")
    if kn is not None:
        p0 = Vector(kn[:]) + palm_n * 0.030   # 02 stored p0 - palm_n*0.030
    else:
        p0 = W + f_dir * (_HAND_SMAX * 0.42)
    return W, f_dir, palm_n, axis, p0


def _hand_chains(side):
    """Joint positions: ([knuckle, j1, j2, tip], [thumb0, t1, t2])."""
    W, f_dir, palm_n, axis, p0 = _hand_frame(side)
    L = _HAND_SMAX * 0.58
    max_deg = _CURL_DEG[side]
    joints = [p0.copy()]
    for u in (1.0 / 3.0, 2.0 / 3.0, 1.0):
        ang = math.radians(max_deg) * (u ** 0.85)
        q = mathutils.Quaternion(axis, ang)
        joints.append(p0 + q @ (f_dir * (u * L)))
    # thumb side: the hand mass is asymmetric along the knuckle axis
    body = bpy.data.objects["Godwyn_Body"]
    sgn = 1.0 if side == "R" else -1.0
    ds = [(v.co - p0).dot(axis) for v in body.data.vertices
          if sgn * v.co.x > 0.80 and (v.co - W).length < 0.45]
    t_sgn = 1.0 if (ds and (max(ds) + min(ds)) > 0.0) else -1.0
    axis_t = axis * t_sgn
    tb0 = p0 + axis_t * 0.050 - f_dir * 0.020
    d1 = (f_dir * 0.55 + palm_n * 0.70 + axis_t * 0.30).normalized()
    tb1 = tb0 + d1 * 0.075
    tb2 = tb1 + (f_dir * 0.30 + palm_n * 0.90).normalized() * 0.060
    return joints, [tb0, tb1, tb2]


# ---------------------------------------------------------------------------
# CAMERA SPECS
# COORDINATE NOTE: Body faces -Y.  Front of character (face/chest) is in the
# -Y hemisphere.  All "front-facing" cameras must be placed at negative Y.
# "L" = character's LEFT = world -X.  "R" = character's RIGHT = world +X.
# Targets: mid-chest/head centre at (0, 0, ~1.75).
# ---------------------------------------------------------------------------
_MID_TARGET = (0.0, 0.0, 1.75)   # mid-body look-at point (waist-to-chest)
_FACE_TGT   = (0.0, 0.0, 2.92)   # face/head look-at
_SWORD_LOC  = (1.0, -0.30, 1.84) # Godwyn_Sword world location (right hand)
_SWORD_TGT  = (0.65, -0.15, 1.40) # blade mid-point

CAMERA_SPECS = {
    # name                   location                   look_at         lens
    # Cam_Full: whole 3.2m figure head-to-toe with modest headroom. r4: nudged
    # to x=+1.5 (his right) so the sword-gripping hand is NOT edge-on and the
    # grip reads (major #3); the void crack (x~2.6, y=12, 03_materials) then
    # sits ~12deg right of centre — in frame, clear of his silhouette.
    "Cam_Full":            ((  1.5,  -9.4,  1.60),  (0.0, 0.0, 1.62), 58),
    "Cam_Front":           ((  0.0,  -8.8,  1.75),  _MID_TARGET,      65),
    "Cam_ThreeQuarter_L":  (( -5.8,  -6.6,  2.10),  _MID_TARGET,      65),
    "Cam_ThreeQuarter_R":  ((  5.8,  -6.6,  2.10),  _MID_TARGET,      65),
    "Cam_Back":            ((  0.0,   8.6,  1.75),  _MID_TARGET,      65),
    "Cam_Side":            ((  8.8,   0.0,  1.75),  _MID_TARGET,      65),
    "Cam_Face":            ((  0.0,  -2.1,  2.95),  _FACE_TGT,        85),
    "Cam_Sword":           ((  3.2,  -2.8,  0.90),  _SWORD_TGT,       85),
    "Cam_Sheet":           ((  0.0, -13.5,  1.90),  _MID_TARGET,      50),
}

# ---------------------------------------------------------------------------
# LIGHTING SPECS
# Dark-fantasy rig per SPEC 337-339: Godwyn IS the light source.
# Key: warm top-down from front (1.0,0.92,0.6); Fill: subtle cool from side;
# Rim: warm gold from behind; all aimed at character.
# Body faces -Y so "front" = -Y side.
# ---------------------------------------------------------------------------
# Round 3 (major #2): the r2 key at 420 was strong enough to read as studio
# lighting — the skin looked externally-lit plaster. The skin emission now
# carries 0.55 effective radiance (03_materials r3), so the external key
# drops to a DIM warm shaper and Godwyn's own glow leads the exposure.
# Light_Hands (major #7): soft low warm fill so the hands/hilt aren't lost
# in shadow at the low-hang guard.
LIGHT_SPECS = {
    # name        location             look_at          color              energy  size
    # p5b fixer r3 major #7: dark-fantasy shaping — key LOWERED (190->150) so
    # frontal light stops washing the forms flat; a NEW strong cool kicker
    # from behind-left carves the silhouette; low fill lifted slightly so
    # muscle/fold shadow detail stays readable.
    # fixer r2 blocker #3: key 150->125 — pulls the face out of the AgX
    # highlight-desaturation shoulder so skin chroma survives.
    "Light_Key":  ((-1.8,  -4.5, 7.0), (0.0, 0.0, 2.2), (1.0, 0.92, 0.60), 125.0, 3.5),
    "Light_Fill": (( 4.0,  -2.8, 1.4), (0.0, 0.0, 1.8), (0.55, 0.65, 0.90), 50.0, 4.5),
    "Light_Rim":  (( 0.8,   6.5, 4.5), (0.0, 0.0, 2.2), (1.0, 0.88, 0.50), 260.0, 2.5),
    "Light_Kick": ((-3.8,   4.6, 3.2), (0.0, 0.0, 2.1), (0.55, 0.68, 1.00), 300.0, 2.8),
    # phase4 fixer r1 blocker #3: 85 -> 130 — the gauntlets vanished into
    # shadow at Cam_Full; the hands/hilt must read.
    "Light_Hands": ((1.6,  -3.0, 1.1), (0.5, -0.3, 1.6), (1.0, 0.92, 0.60), 130.0, 3.0),
    # r4 major #2: tiny dedicated eye fill — a small DISK close to the face
    # axis gives the corneas a round catchlight (the old square area lights
    # stamped rectangular speculars into the eyes).
    "Light_EyeFill": ((0.0, -2.4, 3.05), (0.0, 0.0, 2.92), (1.0, 0.94, 0.70), 8.0, 0.30),
}


# ---------------------------------------------------------------------------
# SMALL HELPERS
# ---------------------------------------------------------------------------

def _activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _track_rotation(from_loc, to_loc):
    """Euler that points a camera/light's -Z axis at to_loc."""
    direction = Vector(to_loc) - Vector(from_loc)
    return direction.to_track_quat("-Z", "Y").to_euler()


def _clear_by_names(names):
    """Idempotent clear (INV-6): remove objects (and orphan data) by name."""
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
    for coll in (bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for block in list(coll):
            if block.name in names and block.users == 0:
                coll.remove(block)


# ---------------------------------------------------------------------------
# 1) ARMATURE — simple humanoid rig
# ---------------------------------------------------------------------------

def build_armature():
    _clear_by_names([ARMATURE_NAME])

    col = G.get_or_create_collection("Godwyn")

    arm_data = bpy.data.armatures.new(ARMATURE_NAME)
    arm_obj  = bpy.data.objects.new(ARMATURE_NAME, arm_data)
    col.objects.link(arm_obj)

    _activate(arm_obj)
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = arm_data.edit_bones
    for name, head, tail, parent, connect, deform in _bone_table():
        eb = ebones.new(name)
        eb.head = head
        eb.tail = tail
        eb.use_deform = deform
        eb.envelope_distance = 0.25   # generous coverage for envelope fallback
        if parent:
            eb.parent = ebones[parent]
            eb.use_connect = connect

    # -- finger + thumb chains (p5r2 blocker #1) ------------------------------
    for side in ("R", "L"):
        fj, tj = _hand_chains(side)
        prev = f"hand.{side}"
        for i in range(3):
            eb = ebones.new(f"fingers.{i + 1:02d}.{side}")
            eb.head, eb.tail = fj[i], fj[i + 1]
            eb.use_deform = True
            eb.envelope_distance = 0.05   # tight: fingers, not the forearm
            eb.parent = ebones[prev]
            eb.use_connect = (i > 0)
            prev = eb.name
        prev = f"hand.{side}"
        for i in range(2):
            eb = ebones.new(f"thumb.{i + 1:02d}.{side}")
            eb.head, eb.tail = tj[i], tj[i + 1]
            eb.use_deform = True
            eb.envelope_distance = 0.05
            eb.parent = ebones[prev]
            eb.use_connect = (i > 0)
            prev = eb.name
    bpy.ops.object.mode_set(mode="OBJECT")

    n = len(arm_data.bones)
    print(f"[04_rig] Armature '{ARMATURE_NAME}' built with {n} bones:")
    print("[04_rig]   " + ", ".join(sorted(b.name for b in arm_data.bones)))
    return arm_obj


# ---------------------------------------------------------------------------
# 2) PARENTING — auto weights (envelope fallback), bone-parent hair + sword
# ---------------------------------------------------------------------------

def parent_deforming(arm_obj, objs):
    """
    Parent each mesh to the armature with AUTOMATIC WEIGHTS, one object at
    a time (so a bone-heat failure on one island doesn't poison the rest).
    Fallback: envelope weights (always solvable).
    """
    bone_names = {b.name for b in arm_obj.data.bones}
    for obj in objs:
        for mode in ("ARMATURE_AUTO", "ARMATURE_ENVELOPE"):
            # Reset any previous partial parenting — but ONLY bone-named
            # groups. The body's MPFB2 marker groups (helper-l-eye/-r-eye,
            # scalp, fingernails, ...) are load-bearing for 02/03 rebuilds.
            obj.parent = None
            for vg in list(obj.vertex_groups):
                if vg.name in bone_names:
                    obj.vertex_groups.remove(vg)
            for mod in list(obj.modifiers):
                if mod.type == "ARMATURE":
                    obj.modifiers.remove(mod)

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            arm_obj.select_set(True)
            bpy.context.view_layer.objects.active = arm_obj
            try:
                bpy.ops.object.parent_set(type=mode)
            except RuntimeError as e:
                print(f"[04_rig] {obj.name}: {mode} raised: {e}", file=sys.stderr)
                continue

            weighted = [vg for vg in obj.vertex_groups
                        if vg.name in bone_names]
            if weighted:
                print(f"[04_rig] {obj.name}: parented via {mode} "
                      f"({len(weighted)} vertex groups).")
                break
            print(f"[04_rig] {obj.name}: {mode} produced no vertex groups; "
                  f"trying fallback.", file=sys.stderr)
        else:
            print(f"[04_rig] FATAL: could not weight-parent {obj.name}.",
                  file=sys.stderr)
            sys.exit(1)


def bone_parent(arm_obj, obj, bone_name):
    """Rigidly parent obj to a bone, preserving its world transform."""
    mw = obj.matrix_world.copy()
    obj.parent = arm_obj
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    bpy.context.view_layer.update()
    obj.matrix_world = mw
    print(f"[04_rig] {obj.name}: bone-parented to '{bone_name}' "
          f"(world transform preserved).")


# ---------------------------------------------------------------------------
# 2a) WEIGHT OVERRIDES (p5r2 blockers #1 + item 7)
# ---------------------------------------------------------------------------

def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def fix_hand_weights(arm_obj, body):
    """
    p5r2 blocker #1: auto weights smeared the hand across forearm/hand and
    it collapsed to a wafer under a wrist bend. Re-weight every hand vertex
    (bind space, beyond the wrist) to the nearest two of: the hand bone
    (palm), the 3-bone composite finger chain, the 2-bone thumb — inverse-
    distance blended. Verts within 45mm of the wrist keep their auto blend
    so the forearm transition stays smooth.
    """
    bone_names = {b.name for b in arm_obj.data.bones}
    for side in ("R", "L"):
        sgn = 1.0 if side == "R" else -1.0
        W, f_dir, palm_n, axis, p0 = _hand_frame(side)
        fj, tj = _hand_chains(side)
        segs = [(f"hand.{side}", W, p0)]
        segs += [(f"fingers.{i + 1:02d}.{side}", fj[i], fj[i + 1])
                 for i in range(3)]
        segs += [(f"thumb.{i + 1:02d}.{side}", tj[i], tj[i + 1])
                 for i in range(2)]
        idxs = [v.index for v in body.data.vertices
                if sgn * v.co.x > 0.80 and (v.co - W).length < 0.45
                and (v.co - W).dot(f_dir) > 0.045]
        if not idxs:
            print(f"[04_rig] WARNING: no {side}-hand verts to re-weight",
                  file=sys.stderr)
            continue
        vgs = {}
        for bn, _, _ in segs:
            vgs[bn] = (body.vertex_groups.get(bn)
                       or body.vertex_groups.new(name=bn))
        for g in body.vertex_groups:
            if g.name in bone_names:
                try:
                    g.remove(idxs)
                except RuntimeError:
                    pass
        for i in idxs:
            p = body.data.vertices[i].co
            ds = sorted((_seg_dist(p, a, b), bn) for bn, a, b in segs)
            (d0, b0), (d1, b1) = ds[0], ds[1]
            w0 = 1.0 / (d0 + 0.004)
            w1 = 1.0 / (d1 + 0.004)
            tot = w0 + w1
            vgs[b0].add([i], w0 / tot, "REPLACE")
            vgs[b1].add([i], w1 / tot, "REPLACE")
        print(f"[04_rig] {side} hand re-weighted: {len(idxs)} verts across "
              f"hand/fingers/thumb chains.")


def rigid_weight_armor(arm_obj, armor):
    """
    RE-OUTFIT: skin the full gold-plate kit by TRANSFERRING the body's
    weights onto Godwyn_Armor (POLYINTERP_NEAREST) — plates deform exactly
    with the skin beneath them. (History: rigid islands opened joint
    slivers; bone-heat auto weights left whole islands weightless.)
    """
    # RE-OUTFIT r19: bone-heat AUTO weights failed on the disjoint plate
    # shells (whole islands weightless -> a bare left leg in the idle pose),
    # and fully-RIGID islands opened skin slivers at every joint. The fix is
    # the production-standard one: TRANSFER the body's skin weights onto the
    # armor (POLYINTERP_NEAREST). Every plate then deforms exactly like the
    # skin underneath it — no poke-through at any joint, fingers stay live
    # inside the gauntlets.
    body = bpy.data.objects["Godwyn_Body"]
    armor.vertex_groups.clear()
    bpy.ops.object.select_all(action="DESELECT")
    armor.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body   # transfer active->selected
    bpy.ops.object.data_transfer(
        use_create=True, data_type="VGROUP_WEIGHTS",
        vert_mapping="POLYINTERP_NEAREST",
        layers_select_src="ALL", layers_select_dst="NAME")
    n_g = len(armor.vertex_groups)
    # sanity: every vert must carry some weight
    unweighted = sum(1 for v in armor.data.vertices if not v.groups)
    print(f"[04_rig] Godwyn_Armor weights TRANSFERRED from body: "
          f"{n_g} groups, {unweighted} unweighted verts")
    if unweighted:
        # fall back: bind stragglers rigidly to the nearest bone via chest
        vg = (armor.vertex_groups.get("chest")
              or armor.vertex_groups.new(name="chest"))
        vg.add([v.index for v in armor.data.vertices if not v.groups],
               1.0, "REPLACE")
        print(f"[04_rig]   {unweighted} stragglers pinned to chest")

    # RE-OUTFIT fixer r1 blocker #3: SHARPEN the transferred weights so the
    # plates deform near-RIGIDLY instead of creasing like flesh under a
    # spine twist. Raising each vert's weights to the 1.5th power (then
    # renormalising) makes the dominant bone own the plate while keeping a
    # narrow smooth blend at lame overlaps/joints (no popping). NOTE: ^3.0
    # shifted plates 1-2cm off the (smooth-weighted) body in the idle pose
    # and the calves/armpits poked through as white patches — ^1.5 keeps the
    # shift inside the plate clearance while still firming the plates up.
    gi = {g.index: g for g in armor.vertex_groups}
    n_sharp = 0
    for v in armor.data.vertices:
        if not v.groups:
            continue
        if v.co.z < 1.30 * _LEG_K * _PROP_S:   # r5: follows the leg remap
            continue   # legs stay pure-transfer: sharpening opened calf
                       # slivers vs the smooth-weighted body (r4/r5)
        ws = [(ge.group, ge.weight ** 1.5) for ge in v.groups]
        tot = sum(w for _, w in ws)
        if tot <= 1e-9:
            continue
        for g_idx, w in ws:
            gi[g_idx].add([v.index], w / tot, "REPLACE")
        n_sharp += 1
    print(f"[04_rig]   plate weights sharpened (rigid read): {n_sharp} verts")

    # fixer r1 blocker #1: the body's foot polys are DELETED (masked under
    # the sabatons), so POLYINTERP_NEAREST gave the sabaton verts shin/ankle
    # weights. Re-bind them explicitly: rigid foot.L/R below the ankle with
    # a short shin blend band, so the boots ride the foot bones.
    for side, sgn in (("R", 1.0), ("L", -1.0)):
        fg = (armor.vertex_groups.get(f"foot.{side}")
              or armor.vertex_groups.new(name=f"foot.{side}"))
        sg = (armor.vertex_groups.get(f"shin.{side}")
              or armor.vertex_groups.new(name=f"shin.{side}"))
        gi = {g.index: g for g in armor.vertex_groups}
        n_foot = 0
        _sab_z = 0.26 * _LEG_K * _PROP_S       # r5: follows the leg remap
        for v in armor.data.vertices:
            if sgn * v.co.x <= 0.0 or v.co.z >= _sab_z:
                continue
            t = max(0.0, min(1.0, (_sab_z - v.co.z) / 0.06))
            for ge in list(v.groups):
                gi[ge.group].remove([v.index])
            fg.add([v.index], t, "REPLACE")
            if t < 1.0:
                sg.add([v.index], 1.0 - t, "REPLACE")
            n_foot += 1
        print(f"[04_rig]   sabaton {side}: {n_foot} verts bound to "
              f"foot.{side} (shin blend above ankle)")


# ---------------------------------------------------------------------------
# 2b-TABARD) SOFT CLOTH SKINNING for Godwyn_Tabard
# ---------------------------------------------------------------------------
# The tabard is a hanging front-tabard/surcoat with optional side/back panels
# (waist->floor). Auto-weights fail on 251k-vert cloth shells (bone-heat is
# too expensive and the disjoint panels get zero weights). Data-transfer from
# the body + a Z-height-based soft blend gives a clean cloth drape:
#   - Belt/top (~hip Z): blended pelvis 0.7 + spine.01 0.3
#   - Mid (waist to knee): blended pelvis 0.5 + thigh 0.3 + spine.01 0.2
#   - Lower (knee to floor): thigh.L/R or pelvis depending on X offset
# This keeps the front panel flowing smoothly when pelvis/spine twist,
# and the side panels trailing naturally off the thighs.

def skin_tabard_soft(arm_obj, tabard):
    """
    Z-height-based soft cloth skinning for the front tabard/surcoat panel.
    Three zones from belt to floor. All weights are smooth-blended — no
    rigid islands — so the cloth trails naturally under any spine/hip pose.
    Idempotent: clears and rebuilds all bone vertex groups each call.
    """
    body = bpy.data.objects.get("Godwyn_Body")
    if body is None:
        print("[04_rig] WARNING: Godwyn_Body missing — cannot skin tabard",
              file=sys.stderr)
        return

    # Step 1: clear existing bone vertex groups on the tabard
    arm_bone_names = {b.name for b in arm_obj.data.bones}
    for vg in list(tabard.vertex_groups):
        if vg.name in arm_bone_names:
            tabard.vertex_groups.remove(vg)

    # Step 2: ensure EXACTLY ONE armature modifier bound to arm_obj.
    # phase4 fixer r1 minor #6: an inert extra ARMATURE modifier
    # (object=None) rode along from an earlier parenting pass — delete any
    # ARMATURE modifier not bound to THIS armature, and keep one real bind.
    seen_bind = False
    for m in list(tabard.modifiers):
        if m.type != "ARMATURE":
            continue
        if m.object is arm_obj and not seen_bind:
            seen_bind = True
        else:
            print(f"[04_rig] Tabard: removing stray ARMATURE modifier "
                  f"'{m.name}' (object={m.object})")
            tabard.modifiers.remove(m)
    if not seen_bind:
        mod = tabard.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        print("[04_rig] Tabard: added armature modifier")

    # Step 3: for the upper portion try data-transfer from the body first
    # (gives correct per-vertex weights at the belt/waist where the tabard
    # overlaps the body geometry). Then override the lower panels with the
    # Z-zone cloth blend.
    bpy.ops.object.select_all(action="DESELECT")
    tabard.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    try:
        bpy.ops.object.data_transfer(
            use_create=True, data_type="VGROUP_WEIGHTS",
            vert_mapping="POLYINTERP_NEAREST",
            layers_select_src="ALL", layers_select_dst="NAME")
        transferred = sum(1 for v in tabard.data.vertices if v.groups)
        print(f"[04_rig] Tabard: data-transfer from body gave weights to "
              f"{transferred}/{len(tabard.data.vertices)} verts")
    except Exception as e:
        print(f"[04_rig] Tabard: data-transfer failed ({e}), "
              f"using pure Z-zone skinning", file=sys.stderr)
        transferred = 0

    # Step 4: Z-zone cloth override.
    # Proportionally-remapped landmark heights (same as bone table _prop_pt):
    z_belt  = _prop_pt((0, 0, _LEG * 0.97))[2]   # ~top of pelvis bone / belt
    z_hip   = _prop_pt((0, 0, _LEG))[2]           # hip / top of thigh
    z_knee  = _prop_pt((0, 0, _KNEE))[2]          # knee
    z_ankle = _prop_pt((0, 0, _ANKLE))[2]         # ankle / near floor

    # Get or create the key groups we'll write
    def _vg(name):
        return (tabard.vertex_groups.get(name)
                or tabard.vertex_groups.new(name=name))

    g_pelvis   = _vg("pelvis")
    g_spine01  = _vg("spine.01")
    g_chest    = _vg("chest")
    g_thigh_r  = _vg("thigh.R")
    g_thigh_l  = _vg("thigh.L")
    g_shin_r   = _vg("shin.R")
    g_shin_l   = _vg("shin.L")

    # Group index map for efficient weight assignment
    gi = {g.index: g for g in tabard.vertex_groups}

    # Clear all bone weights on every vert before re-writing
    # (we override fully — the data-transfer weights above served only to
    # prime the modifier; the cloth logic below replaces them cleanly)
    all_idx = list(range(len(tabard.data.vertices)))
    for g in tabard.vertex_groups:
        if g.name in arm_bone_names:
            try:
                g.remove(all_idx)
            except RuntimeError:
                pass

    # Assign zone-blended cloth weights
    n_belt = n_mid = n_lower = n_floor = 0
    for v in tabard.data.vertices:
        z = v.co.z
        x = v.co.x   # +X = Godwyn's right; ±X tells us if this is a side panel

        # Normalized side offset for thigh blending
        side_fac = min(abs(x) / 0.22, 1.0)  # 0=centre, 1=fully to one side

        if z >= z_belt:
            # BELT / TOP OF TABARD: anchored to chest + pelvis + spine01
            # (tabs at the top attach at the belt, just below breastplate)
            t = min((z - z_belt) / max(z_hip - z_belt, 0.01), 1.0)
            w_chest  = 0.25 * t
            w_spine  = 0.35 - 0.15 * t
            w_pelvis = 1.0 - w_chest - w_spine
            g_chest.add([v.index], w_chest, "REPLACE")
            g_spine01.add([v.index], w_spine, "REPLACE")
            g_pelvis.add([v.index], w_pelvis, "REPLACE")
            n_belt += 1

        elif z >= z_knee:
            # MID PANEL: pelvis + spine.01 blend, side panels add thigh
            t = (z - z_knee) / max(z_belt - z_knee, 0.01)   # 1=top, 0=knee
            w_spine  = 0.20 * t
            w_thigh  = 0.40 * (1.0 - t) * side_fac
            w_pelvis = 1.0 - w_spine - w_thigh
            if x >= 0:
                g_thigh_r.add([v.index], w_thigh, "REPLACE")
            else:
                g_thigh_l.add([v.index], w_thigh, "REPLACE")
            g_spine01.add([v.index], w_spine, "REPLACE")
            g_pelvis.add([v.index], w_pelvis, "REPLACE")
            n_mid += 1

        elif z >= z_ankle:
            # LOWER PANEL (knee to ankle): thigh dominant, shin blend begins
            t = (z - z_ankle) / max(z_knee - z_ankle, 0.01)  # 1=knee, 0=ankle
            w_shin   = (1.0 - t) * 0.40 * side_fac
            w_thigh  = t * 0.60 * side_fac
            w_pelvis = 1.0 - w_shin - w_thigh
            if x >= 0:
                g_thigh_r.add([v.index], w_thigh, "REPLACE")
                g_shin_r.add([v.index], w_shin, "REPLACE")
            else:
                g_thigh_l.add([v.index], w_thigh, "REPLACE")
                g_shin_l.add([v.index], w_shin, "REPLACE")
            g_pelvis.add([v.index], w_pelvis, "REPLACE")
            n_lower += 1

        else:
            # FLOOR TRAILING EDGE: pin to pelvis (stationary ground contact)
            g_pelvis.add([v.index], 1.0, "REPLACE")
            n_floor += 1

    total = n_belt + n_mid + n_lower + n_floor
    print(f"[04_rig] Tabard Z-zone cloth weights applied: "
          f"belt={n_belt}, mid={n_mid}, lower={n_lower}, floor={n_floor} "
          f"({total}/{len(tabard.data.vertices)} verts)")

    # Final sanity: every vert must have at least one weight
    still_empty = sum(1 for v in tabard.data.vertices if not v.groups)
    if still_empty:
        g_pelvis.add([v.index for v in tabard.data.vertices if not v.groups],
                     1.0, "REPLACE")
        print(f"[04_rig] Tabard: {still_empty} stragglers pinned to pelvis")
    else:
        print("[04_rig] Tabard: all verts weighted — clean cloth bind")

    # phase4 fixer r1 minor #6: STRIP every non-deform vertex group. The
    # body data-transfer (layers_select_src='ALL') copied ~180 MakeHuman
    # helper/joint groups onto the tabard — export confusion + accidental-
    # rebind hazard. Keep ONLY the deform zone groups written above.
    keep = {"pelvis", "spine.01", "chest",
            "thigh.R", "thigh.L", "shin.R", "shin.L"}
    stripped = 0
    for vg in list(tabard.vertex_groups):
        if vg.name not in keep:
            tabard.vertex_groups.remove(vg)
            stripped += 1
    print(f"[04_rig] Tabard: stripped {stripped} non-deform vertex groups "
          f"(kept {sorted(g.name for g in tabard.vertex_groups)})")


# ---------------------------------------------------------------------------
# 2b) IDLE POSE — serene contrapposto, arms relaxed, blade low (blocker #3)
# ---------------------------------------------------------------------------

def _pose_rotate(arm_obj, name, axis, angle_deg):
    """Rotate a pose bone about a WORLD axis through its own head."""
    bpy.context.view_layer.update()
    pb = arm_obj.pose.bones[name]
    R = mathutils.Matrix.Rotation(math.radians(angle_deg), 4,
                                  Vector(axis).normalized())
    t = pb.matrix.translation.copy()
    piv = (mathutils.Matrix.Translation(t) @ R
           @ mathutils.Matrix.Translation(-t))
    pb.matrix = piv @ pb.matrix


def _pose_aim(arm_obj, name, target_dir):
    """Rotate a pose bone so it points along target_dir (world space)."""
    bpy.context.view_layer.update()
    pb = arm_obj.pose.bones[name]
    cur = (pb.tail - pb.head)
    if cur.length < 1e-9:
        return
    q = cur.normalized().rotation_difference(Vector(target_dir).normalized())
    R = q.to_matrix().to_4x4()
    t = pb.matrix.translation.copy()
    piv = (mathutils.Matrix.Translation(t) @ R
           @ mathutils.Matrix.Translation(-t))
    pb.matrix = piv @ pb.matrix


def apply_idle_pose(arm_obj):
    """
    Serene idle: both arms relaxed down at the sides (sword arm fractionally
    forward), slight contrapposto through hips/shoulders, head fractionally
    tilted. Kills the raw symmetric A-pose bind read.
    """
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")

    # contrapposto (r4 minor #7: STRONGER — the r3 2deg values still read
    # as a symmetric mannequin display): real hip shift + torso twist with
    # counter-rotated shoulders. Still bounded so the thighs stay inside
    # the auto-weighted skirt.
    # phase4 fixer r4 minor #6 ("near-symmetric low A-pose"): a clearer
    # asymmetric shoulder/torso turn (~10deg cumulative) — relaxed at-ready,
    # not a mannequin display stand.
    _pose_rotate(arm_obj, "pelvis",   (0, 0, 1), 6.0)    # twist
    _pose_rotate(arm_obj, "pelvis",   (0, 1, 0), 2.6)    # frontal tilt (hip shift)
    _pose_rotate(arm_obj, "spine.01", (0, 0, 1), -4.5)
    _pose_rotate(arm_obj, "chest",    (0, 0, 1), -6.5)
    _pose_rotate(arm_obj, "chest",    (0, 1, 0), -2.2)
    # head: fractional tilt + slight downward serene gaze
    _pose_rotate(arm_obj, "neck",     (0, 1, 0), 1.5)
    _pose_rotate(arm_obj, "head",     (0, 1, 0), 3.0)
    _pose_rotate(arm_obj, "head",     (1, 0, 0), 4.0)

    # r4 minor #7: effortless master-swordsman idle — sword arm relaxed
    # slightly FORWARD/OUTWARD (blade will hang down-back), off-hand raised
    # and opened a few degrees away from the thigh.
    # fixer r4 blocker #8 ("T-ish slump" at Cam_Full): a clearer A-pose
    # weight shift — arms swing wider from the torso so the silhouette
    # opens (armored elbows clear the faulds), sword arm a touch more so.
    # p4 r4 minor #6: arms de-symmetrized — off-hand hangs closer to the
    # thigh, sword arm keeps its forward set.
    _pose_aim(arm_obj, "upper_arm.L", (-0.27, 0.03, -0.962))
    _pose_aim(arm_obj, "forearm.L",   (-0.20, -0.32, -0.925))
    # right (sword) arm: forward/outward, clear of the hip
    _pose_aim(arm_obj, "upper_arm.R", (0.37, -0.09, -0.925))
    _pose_aim(arm_obj, "forearm.R",   (0.30, -0.50, -0.81))

    # p4 r4 minor #6 ("empty left hand drooping in a claw"): LEFT fingers
    # softly curled at rest + a relaxed wrist set — a hand at ease, not a
    # rigid claw. Small local-axis curls on every finger/thumb bone.
    if "hand.L" in arm_obj.pose.bones:
        _pose_rotate(arm_obj, "hand.L", (1, 0, 0), 8.0)
    for bn in FINGER_BONES + THUMB_BONES:
        if bn.endswith(".L") and bn in arm_obj.pose.bones:
            _pose_rotate(arm_obj, bn, (1, 0, 0), 16.0)

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    print("[04_rig] Idle pose applied: contrapposto, arms relaxed, "
          "head tilted (no more bind-pose read).")


def place_sword_posed(arm_obj, sword):
    """
    Re-derive the sword grip from the POSED hand.R: transform the bind-space
    grip point/axis (persisted by 02 as custom props) through the bone's
    rest->pose matrix, then aim the blade down-and-out (low-hang master grip).
    """
    if "grip_point" not in sword.keys():
        print("[04_rig] WARNING: sword grip props missing — leaving placement",
              file=sys.stderr)
        return
    B  = arm_obj.data.bones[SWORD_BONE]
    pb = arm_obj.pose.bones[SWORD_BONE]
    bpy.context.view_layer.update()
    M = (arm_obj.matrix_world @ pb.matrix @ B.matrix_local.inverted())
    gp = M @ Vector(sword["grip_point"][:])
    ga = (M.to_3x3() @ Vector(sword["grip_axis"][:])).normalized()
    if ga.z > 0.0:
        ga = -ga
    # Round 4 (minor #7): blade angled DOWN-BACK (+y is behind — body faces
    # -Y) and outward: the effortless low-hang of a master swordsman whose
    # sword arm now sits slightly forward/outward.
    # phase4 fixer r4 minor #6 ("blade straight lateral"): less outward x,
    # more down-and-back — the blade hangs naturally from the relaxed wrist.
    ga = (ga * 0.74 + Vector((0.10, 0.26, -0.52))).normalized()
    rot = ga.to_track_quat("Z", "Y")
    sword.matrix_world = mathutils.Matrix.LocRotScale(gp, rot, None)
    print(f"[04_rig] Sword re-gripped at posed hand: "
          f"({gp.x:.3f},{gp.y:.3f},{gp.z:.3f}), blade dir "
          f"({ga.x:.2f},{ga.y:.2f},{ga.z:.2f}).")


# ---------------------------------------------------------------------------
# 2c) DEFORM SANITY CHECK — test pose + blendshape, then RESET to rest
# ---------------------------------------------------------------------------

def apply_test_deform(arm_obj):
    """
    Phase 3 NATURAL deform test: mild grounded stances like a real Elden Ring
    boss pose — slight arm bend, slight spine turn, a half-step weight shift.
    NOT extreme / contorted — the goal is to confirm the tabard trails
    naturally under hip/spine motion without tearing, and that the plate armor
    follows cleanly, while remaining a believable weighty pose.

      - spine.01: 8° torso twist toward Cam_ThreeQuarter_L (natural weight shift)
      - upper_arm.R: 18° forward swing (slight sword-arm advancement)
      - forearm.R: 15° elbow bend forward (natural arm hang, not stiff)
      - hand.R: 12° wrist cock (natural grip attitude)
      - pelvis: 4° hip tilt (weight-shifted step — drives tabard drape test)
      - thigh.L: 8° slight stride lift (partial step — confirms tabard trails)
    """
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")

    # Spine: mild torso twist toward camera (natural breathing rotation)
    _pose_rotate(arm_obj, "spine.01",    (0, 0, 1),   8.0)
    _pose_rotate(arm_obj, "chest",       (0, 0, 1),   4.0)

    # Sword arm: slight natural advancement — the low-hang pose with
    # fractional elbow crook, like a practiced swordsman settling weight
    _pose_rotate(arm_obj, "upper_arm.R", (0, 1, 0),  18.0)  # swing fwd
    _pose_rotate(arm_obj, "forearm.R",   (1, 0, 0), -15.0)  # mild elbow bend
    _pose_rotate(arm_obj, "hand.R",      (1, 0, 0),  12.0)  # wrist cock

    # Off-hand: slight open relaxation, hand away from body
    _pose_rotate(arm_obj, "upper_arm.L", (0, 1, 0),  10.0)

    # Hip tilt: one-side weight shift drives the tabard drape test
    _pose_rotate(arm_obj, "pelvis",      (0, 1, 0),   4.0)  # frontal hip tilt

    # Left thigh: partial stride lift (half-step — tests tabard trailing)
    _pose_rotate(arm_obj, "thigh.L",     (1, 0, 0),  -8.0)

    # R-hand fingers: mild grip tighten (not combat-curl — just settled grip)
    for bn in FINGER_BONES + THUMB_BONES:
        if bn.endswith(".R") and bn in arm_obj.pose.bones:
            _pose_rotate(arm_obj, bn, (1, 0, 0), 8.0)

    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    print("[04_rig] Deform test pose applied (NATURAL): spine twist 8°, "
          "sword arm fwd 18° + elbow 15°, hip tilt 4°, thigh stride 8°. "
          "Tests tabard drape + plate follow cleanly.")


def drive_test_blendshape(body):
    """
    Set Expr_BrowSorrow to 0.6 on Godwyn_Body to confirm the face blendshape
    survives armature binding (shape keys are preserved through weight-parenting
    — the armature modifier does not destroy them, but this render proves it).
    Returns True if the key was found and driven.
    """
    if body is None:
        print("[04_rig] WARNING: Godwyn_Body missing, cannot drive blendshape.",
              file=sys.stderr)
        return False
    sk = body.data.shape_keys
    if sk is None:
        print("[04_rig] WARNING: Godwyn_Body has no shape keys.",
              file=sys.stderr)
        return False
    key = sk.key_blocks.get("Expr_BrowSorrow")
    if key is None:
        # fall back to any non-Basis key
        non_basis = [k for k in sk.key_blocks if k.name != "Basis"]
        if not non_basis:
            print("[04_rig] WARNING: No expression shape keys found.",
                  file=sys.stderr)
            return False
        key = non_basis[0]
    key.value = 0.6
    print(f"[04_rig] Blendshape '{key.name}' driven to 0.6 for deform test.")
    return True


def reset_test_deform(arm_obj, body):
    """
    Reset all pose bones to rest pose and blendshape values to 0.
    Must be called before the final .blend save.
    """
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.rot_clear()
    bpy.ops.pose.loc_clear()
    bpy.ops.pose.scale_clear()
    bpy.ops.object.mode_set(mode="OBJECT")

    # Reset blendshapes to 0
    if body is not None and body.data.shape_keys:
        for kb in body.data.shape_keys.key_blocks:
            if kb.name != "Basis":
                kb.value = 0.0

    # Re-apply the idle serene pose that was the intended rest display
    apply_idle_pose(arm_obj)
    bpy.context.view_layer.update()
    print("[04_rig] Deform test reset: pose cleared, blendshapes to 0, "
          "idle pose re-applied.")


# ---------------------------------------------------------------------------
# 3) LIGHTING RIG (SPEC 337-339)
# ---------------------------------------------------------------------------

def build_lights():
    _clear_by_names(list(LIGHT_SPECS.keys()))
    col = G.get_or_create_collection("Godwyn")
    for name, (loc, target, color, energy, size) in LIGHT_SPECS.items():
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.color  = color
        ld.size   = size
        ld.shape  = "DISK"   # r4 major #2: ROUND catchlights in the corneas
        lo = bpy.data.objects.new(name, ld)
        col.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = _track_rotation(loc, target)
    print(f"[04_rig] Lighting rig built: {', '.join(LIGHT_SPECS)} "
          f"(warm top-down key, cool fill, warm rim).")


def build_ground():
    """fixer r5 blocker #8 ("stance floats above the ground shadow"):
    a near-black, faintly glossy floor disc PLANTS the figure — contact
    shadow under the sabatons + a faint golden reflection pool (Godwyn is
    the light source). Named Preview_Ground (NOT in the Godwyn collection):
    02's idempotent clear removes it, 07 strips it before GLB export."""
    old = bpy.data.objects.get("Preview_Ground")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    mat = bpy.data.materials.get("Mat_GroundPreview")
    if mat is None:
        mat = bpy.data.materials.new("Mat_GroundPreview")
        mat.use_nodes = True
        pb = mat.node_tree.nodes.get("Principled BSDF")
        if pb is not None:
            pb.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1.0)
            pb.inputs["Roughness"].default_value = 0.30
            pb.inputs["Metallic"].default_value = 0.0
    bpy.ops.mesh.primitive_circle_add(vertices=64, radius=7.0,
                                      fill_type="NGON",
                                      location=(0.0, 0.0, 0.0))
    ob = bpy.context.active_object
    ob.name = "Preview_Ground"
    ob.data.name = "Preview_Ground_Mesh"
    ob.data.materials.append(mat)
    print("[04_rig] Preview_Ground floor disc built (contact shadow + "
          "faint reflection pool).")


# ---------------------------------------------------------------------------
# 4) CAMERAS — 8 named, framed for a 3.2m subject facing -Y
# ---------------------------------------------------------------------------

def build_cameras():
    _clear_by_names(list(CAMERA_SPECS.keys()))
    col = G.get_or_create_collection("Godwyn")
    for name, (loc, target, lens) in CAMERA_SPECS.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 200.0
        co = bpy.data.objects.new(name, cd)
        col.objects.link(co)
        co.location = loc
        co.rotation_euler = _track_rotation(loc, target)
    print(f"[04_rig] Cameras built: {', '.join(CAMERA_SPECS)}.")
    print(f"[04_rig] NOTE: Body faces -Y. Front cameras at negative Y.")


# ---------------------------------------------------------------------------
# VALIDATION GATE
# ---------------------------------------------------------------------------

REQUIRED_BONES = (
    "root", "pelvis", "spine.01", "chest", "neck", "head",
    "shoulder.R", "upper_arm.R", "forearm.R", "hand.R",
    "shoulder.L", "upper_arm.L", "forearm.L", "hand.L",
    "thigh.R", "shin.R", "foot.R", "thigh.L", "shin.L", "foot.L",
) + FINGER_BONES + THUMB_BONES


def assert_phase4():
    errors = []

    arm = bpy.data.objects.get(ARMATURE_NAME)
    if arm is None or arm.type != "ARMATURE":
        errors.append(f"armature '{ARMATURE_NAME}' missing")
    else:
        have = {b.name for b in arm.data.bones}
        for b in REQUIRED_BONES:
            if b not in have:
                errors.append(f"bone '{b}' missing")

    for name in CAMERA_SPECS:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "CAMERA":
            errors.append(f"camera '{name}' missing")

    for name in LIGHT_SPECS:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "LIGHT":
            errors.append(f"light '{name}' missing")

    sword = bpy.data.objects.get("Godwyn_Sword")
    if sword is None:
        errors.append("Godwyn_Sword missing")
    elif not (sword.parent is arm and sword.parent_type == "BONE"
              and sword.parent_bone == SWORD_BONE):
        errors.append(f"Godwyn_Sword not bone-parented to '{SWORD_BONE}' "
                      f"(parent={sword.parent}, type={getattr(sword,'parent_type','?')}, "
                      f"bone='{getattr(sword,'parent_bone','?')}')")

    for name in ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Tabard"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            errors.append(f"{name} missing")
            continue
        if not any(m.type == "ARMATURE" and m.object is arm
                   for m in obj.modifiers):
            errors.append(f"{name} has no Armature modifier bound to the rig")
        if len(obj.vertex_groups) == 0:
            errors.append(f"{name} has no vertex groups (weights missing)")
        else:
            # Spot-check: at least half of verts should have non-zero weights
            n_weighted = sum(1 for v in obj.data.vertices if v.groups)
            n_total = len(obj.data.vertices)
            pct = n_weighted / max(n_total, 1)
            if pct < 0.50:
                errors.append(
                    f"{name} has only {n_weighted}/{n_total} weighted verts "
                    f"({pct:.0%}) — skinning likely failed"
                )

    for hname in ("Godwyn_Hair", "Godwyn_Eyes"):
        hobj = bpy.data.objects.get(hname)
        if hobj is None:
            errors.append(f"{hname} missing")
        elif not (hobj.parent is arm and hobj.parent_type == "BONE"
                  and hobj.parent_bone == "head"):
            errors.append(f"{hname} not bone-parented to 'head'")

    if errors:
        for e in errors:
            print(f"[04_rig] FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    print("[04_rig] ASSERT OK: armature (incl. sword->hand.R), 8 cameras, "
          f"{len(LIGHT_SPECS)} lights, deform weights all present.")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("[04_rig] Phase 4 — Armature, Lights, Cameras, Cycles config")
    print("=" * 60)

    # INV-2: GPU asserted before any work
    active_gpu = G.enable_gpu()
    print(f"[04_rig] GPU active: {active_gpu}")

    # Load committed .blend (INV-5: scripts are source of truth but we load the
    # .blend that was produced and committed by Phase 3, which already has all
    # Godwyn_* objects with MPFB2 body + materials assigned).
    if not os.path.isfile(_BLEND_IN):
        print(f"[04_rig] FATAL: .blend not found: {_BLEND_IN}", file=sys.stderr)
        sys.exit(1)
    bpy.ops.wm.open_mainfile(filepath=_BLEND_IN)
    print(f"[04_rig] Loaded: {_BLEND_IN}")

    # Re-assert GPU after file open (file open resets scene settings)
    active_gpu = G.enable_gpu()
    print(f"[04_rig] GPU re-enabled after file open: {active_gpu}")

    # Confirm Godwyn objects present
    expected_objs = ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Tabard",
                     "Godwyn_Hair", "Godwyn_Sword", "Godwyn_Eyes")
    missing = [n for n in expected_objs if bpy.data.objects.get(n) is None]
    if missing:
        print(f"[04_rig] FATAL: objects missing from .blend: {missing}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[04_rig] Objects confirmed: {list(expected_objs)}")
    print(f"[04_rig] Body verts: "
          f"{len(bpy.data.objects['Godwyn_Body'].data.vertices)}")

    # Ensure the Godwyn collection exists
    col = G.get_or_create_collection("Godwyn")

    # REST-STATE RESTORE (INV-6): on a rerun over an already-rigged .blend,
    # deleting the old armature strands its bone-parented children (hair/
    # eyes/sword) at stale local matrices — the hair literally fell to the
    # floor. 02 builds hair/eyes with baked geometry at IDENTITY transforms,
    # and the sword's rest transform is re-derivable from its bind grip
    # props, so reset all three before re-rigging.
    for nm in ("Godwyn_Hair", "Godwyn_Eyes", "Godwyn_Sword"):
        ob = bpy.data.objects.get(nm)
        if ob is None:
            continue
        ob.parent = None
        if nm == "Godwyn_Sword" and "grip_point" in ob.keys():
            gp = Vector(ob["grip_point"][:])
            ga = Vector(ob["grip_axis"][:]).normalized()
            ob.matrix_world = mathutils.Matrix.LocRotScale(
                gp, ga.to_track_quat("Z", "Y"), None)
        else:
            ob.matrix_world = mathutils.Matrix.Identity(4)
    bpy.context.view_layer.update()

    # Idempotent: clear any previous rig/lights/cams before rebuilding
    _clear_by_names(
        [ARMATURE_NAME] +
        list(LIGHT_SPECS.keys()) +
        list(CAMERA_SPECS.keys())
    )

    # Build rig
    arm_obj = build_armature()
    G.move_to_collection(arm_obj, col)

    # Parent deforming meshes with auto weights
    body  = bpy.data.objects["Godwyn_Body"]
    armor = bpy.data.objects["Godwyn_Armor"]
    robe  = bpy.data.objects["Godwyn_Tabard"]
    hair  = bpy.data.objects["Godwyn_Hair"]
    sword = bpy.data.objects["Godwyn_Sword"]
    eyes  = bpy.data.objects["Godwyn_Eyes"]

    # Body: auto weights (bone-heat / envelope fallback)
    parent_deforming(arm_obj, [body, armor])

    # p5r2 weight overrides: gripping-hand chains + rigid armor islands
    fix_hand_weights(arm_obj, body)
    rigid_weight_armor(arm_obj, armor)

    # Tabard: dedicated soft cloth skinning (Z-zone blend: belt->floor).
    # The tabard has 251k verts — auto-weights via bone-heat would take
    # minutes and fail on disjoint cloth panels. The Z-zone cloth approach
    # gives clean pelvis/spine/thigh drape instantly and deterministically.
    skin_tabard_soft(arm_obj, robe)

    # Hair + eyes: rigid bone-parent to head (eyes track the head pose)
    bone_parent(arm_obj, hair, "head")
    bone_parent(arm_obj, eyes, "head")

    # Sword: rigid bone-parent to hand.R (world transform preserved)
    bone_parent(arm_obj, sword, SWORD_BONE)

    # Serene idle pose (blocker #3) — after parenting so everything follows
    apply_idle_pose(arm_obj)

    # Re-derive the sword grip from the POSED hand (major #7)
    place_sword_posed(arm_obj, sword)

    # Lighting rig
    build_lights()

    # Ground contact (fixer r5 blocker #8)
    build_ground()

    # Cameras
    build_cameras()

    # Set active camera for preview render
    scene = bpy.context.scene
    scene.camera = bpy.data.objects["Cam_ThreeQuarter_L"]

    # Cycles GPU config (256 samples per spec, ~256 + denoise)
    G.configure_cycles(scene,
                       samples=256,
                       resolution_x=1440,
                       resolution_y=2560,
                       use_denoiser=True,
                       film_transparent=False)
    # film exposure lift (major #5): the full-body beauty shot must read
    # clearly — saved into the .blend so P5 renders inherit it
    # (0.5 washed the face to a white mask; 0.25 keeps form)
    # fixer r2 blocker #3: exposure 0.25 -> 0.10 + AgX Punchy look — the
    # face diffuse sat in AgX's highlight-desaturation zone and rendered
    # porcelain-white regardless of albedo; Punchy restores chroma and
    # deepens the gold's worn tones (pixel-verified: cheek R:G 1.08 -> 1.19).
    scene.view_settings.exposure = 0.10
    try:
        scene.view_settings.look = "AgX - Punchy"
    except TypeError:
        try:
            scene.view_settings.look = "Punchy"
        except TypeError:
            pass
    print(f"[04_rig] Cycles: {scene.cycles.samples} samples, "
          f"{scene.render.resolution_x}x{scene.render.resolution_y}, "
          f"view_transform={scene.view_settings.view_transform}.")

    # Validate gate (before deform test so we fail fast on structure issues)
    assert_phase4()

    # -----------------------------------------------------------------------
    # DEFORM SANITY CHECK
    # Apply a test deformation: bend arm + twist spine + drive blendshape.
    # Render from Cam_ThreeQuarter_L to confirm clean skin/armor deformation
    # and that face shape keys survive armature binding.
    # Then RESET to rest (idle pose, blendshapes=0) before saving.
    # -----------------------------------------------------------------------
    print("[04_rig] === DEFORM SANITY CHECK ===")
    arm_obj_check = bpy.data.objects[ARMATURE_NAME]
    body_check    = bpy.data.objects.get("Godwyn_Body")

    # Apply test pose
    apply_test_deform(arm_obj_check)

    # Drive face blendshape
    bkey_driven = drive_test_blendshape(body_check)
    if not bkey_driven:
        print("[04_rig] WARNING: blendshape drive failed — checking for "
              "shape key presence ...", file=sys.stderr)

    # Render deform test from Cam_ThreeQuarter_L
    print(f"[04_rig] Rendering deform test -> {_DEFORM_OUT}")
    scene.camera = bpy.data.objects["Cam_ThreeQuarter_L"]
    G.render_to_path(_DEFORM_OUT, scene)
    sz_deform = os.path.getsize(_DEFORM_OUT) if os.path.isfile(_DEFORM_OUT) else 0
    if sz_deform < 1024:
        print(f"[04_rig] FATAL: deform test PNG missing/empty: {_DEFORM_OUT}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[04_rig] Deform test render OK: {_DEFORM_OUT} ({sz_deform // 1024} KB)")

    # Verify blendshape is still present (survived the render)
    body_post = bpy.data.objects.get("Godwyn_Body")
    if body_post and body_post.data.shape_keys:
        keys_alive = [k.name for k in body_post.data.shape_keys.key_blocks]
        print(f"[04_rig] Blendshapes confirmed alive after deform render: "
              f"{keys_alive}")
    else:
        print("[04_rig] FATAL: shape keys lost after deform render!",
              file=sys.stderr)
        sys.exit(1)

    # Reset to rest pose + zero blendshapes before final save
    reset_test_deform(arm_obj_check, body_post)
    print("[04_rig] === DEFORM SANITY CHECK COMPLETE ===")

    # Re-place sword from posed idle hand (reset_test_deform re-applies idle)
    sword_post = bpy.data.objects.get("Godwyn_Sword")
    if sword_post and "grip_point" in sword_post.keys():
        place_sword_posed(arm_obj_check, sword_post)

    # Save .blend in clean rest-idle-pose state with blendshapes at 0
    bpy.ops.wm.save_as_mainfile(filepath=_BLEND_OUT, compress=True)
    sz = os.path.getsize(_BLEND_OUT) if os.path.isfile(_BLEND_OUT) else 0
    if sz < 10240:
        print(f"[04_rig] FATAL: .blend missing/too small ({sz} bytes): {_BLEND_OUT}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[04_rig] Saved {_BLEND_OUT} ({sz // 1024} KB).")

    # Lit GPU preview from Cam_ThreeQuarter_L (clean idle pose, post-deform-test)
    print(f"[04_rig] Rendering lit idle preview -> {_PREVIEW_OUT}")
    G.render_to_path(_PREVIEW_OUT, scene)
    sz_png = os.path.getsize(_PREVIEW_OUT) if os.path.isfile(_PREVIEW_OUT) else 0
    if sz_png < 1024:
        print(f"[04_rig] FATAL: preview PNG missing/empty: {_PREVIEW_OUT}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[04_rig] Preview OK: {_PREVIEW_OUT} ({sz_png // 1024} KB)")

    # Summary
    print("[04_rig] Cameras:", ", ".join(sorted(CAMERA_SPECS)))
    print("[04_rig] Bones:", ", ".join(
        sorted(b.name for b in bpy.data.objects[ARMATURE_NAME].data.bones)))
    arm_final = bpy.data.objects.get(ARMATURE_NAME)
    n_cams = len([o for o in bpy.data.objects if o.type == "CAMERA"])
    print(f"[04_rig] Armature bones: {len(arm_final.data.bones)}, "
          f"Cameras: {n_cams}.")
    print("[04_rig] Phase 4 complete — models/godwyn_phase1.blend saved.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
