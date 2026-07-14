"""
04_rig_lights_cams.py — Phase 4: Armature + lighting rig + cameras + Cycles
config, then SAVE models/godwyn_phase1.blend.

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
  2. PARENTING: Godwyn_Body / Godwyn_Armor / Godwyn_Robe with AUTOMATIC
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
  5. CYCLES CONFIG: GPU (OptiX->CUDA), 192 samples + denoise, 1440x2560
     portrait, film transparent OFF, AgX (Filmic fallback).
  6. SAVE models/godwyn_phase1.blend, then render a lit GPU preview from
     Cam_ThreeQuarter_L -> renders/wip/04_lit.png.

INV-1 headless, INV-2 GPU asserted, INV-4 names, INV-5 reproducible (loads
committed .blend), INV-6 idempotent (clears armature/lights/cams by name),
INV-7 he is the light.

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

# Arm chain (outward 30° from vertical)
_ARM_ANGLE = math.radians(30.0)
_ARM_UPPER = _H * 0.340 * 0.46
_ARM_LOWER = _H * 0.340 * 0.38
_ARM_HAND  = _H * 0.340 * 0.16
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
             "chest",             False, True),
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
    return bones


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
    "Light_Key":  ((-1.8,  -4.5, 7.0), (0.0, 0.0, 2.2), (1.0, 0.92, 0.60), 190.0, 3.5),
    "Light_Fill": (( 4.0,  -2.8, 2.2), (0.0, 0.0, 1.8), (0.55, 0.65, 0.90), 35.0, 4.5),
    "Light_Rim":  (( 0.8,   6.5, 4.5), (0.0, 0.0, 2.2), (1.0, 0.88, 0.50), 260.0, 2.5),
    "Light_Hands": ((1.6,  -3.0, 1.1), (0.5, -0.3, 1.6), (1.0, 0.92, 0.60), 85.0, 3.0),
    # r4 major #2: tiny dedicated eye fill — a small DISK close to the face
    # axis gives the corneas a round catchlight (the old square area lights
    # stamped rectangular speculars into the eyes).
    "Light_EyeFill": ((0.0, -2.4, 3.05), (0.0, 0.0, 2.92), (1.0, 0.94, 0.70), 14.0, 0.30),
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
    _pose_rotate(arm_obj, "pelvis",   (0, 0, 1), 5.0)    # twist
    _pose_rotate(arm_obj, "pelvis",   (0, 1, 0), 2.6)    # frontal tilt (hip shift)
    _pose_rotate(arm_obj, "spine.01", (0, 0, 1), -2.5)
    _pose_rotate(arm_obj, "chest",    (0, 0, 1), -3.5)
    _pose_rotate(arm_obj, "chest",    (0, 1, 0), -2.2)
    # head: fractional tilt + slight downward serene gaze
    _pose_rotate(arm_obj, "neck",     (0, 1, 0), 1.5)
    _pose_rotate(arm_obj, "head",     (0, 1, 0), 3.0)
    _pose_rotate(arm_obj, "head",     (1, 0, 0), 4.0)

    # r4 minor #7: effortless master-swordsman idle — sword arm relaxed
    # slightly FORWARD/OUTWARD (blade will hang down-back), off-hand raised
    # and opened a few degrees away from the thigh.
    _pose_aim(arm_obj, "upper_arm.L", (-0.24, 0.00, -0.970))
    _pose_aim(arm_obj, "forearm.L",   (-0.16, -0.40, -0.90))
    # right (sword) arm: forward/outward, clear of the hip
    _pose_aim(arm_obj, "upper_arm.R", (0.28, -0.08, -0.955))
    _pose_aim(arm_obj, "forearm.R",   (0.22, -0.50, -0.84))

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
    ga = (ga * 0.74 + Vector((0.22, 0.16, -0.40))).normalized()
    rot = ga.to_track_quat("Z", "Y")
    sword.matrix_world = mathutils.Matrix.LocRotScale(gp, rot, None)
    print(f"[04_rig] Sword re-gripped at posed hand: "
          f"({gp.x:.3f},{gp.y:.3f},{gp.z:.3f}), blade dir "
          f"({ga.x:.2f},{ga.y:.2f},{ga.z:.2f}).")


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
)


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

    for name in ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Robe"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            errors.append(f"{name} missing")
            continue
        if not any(m.type == "ARMATURE" and m.object is arm
                   for m in obj.modifiers):
            errors.append(f"{name} has no Armature modifier bound to the rig")
        if len(obj.vertex_groups) == 0:
            errors.append(f"{name} has no vertex groups (weights missing)")

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
          "3 lights, deform weights all present.")


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
    expected_objs = ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Robe",
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
    robe  = bpy.data.objects["Godwyn_Robe"]
    hair  = bpy.data.objects["Godwyn_Hair"]
    sword = bpy.data.objects["Godwyn_Sword"]
    eyes  = bpy.data.objects["Godwyn_Eyes"]

    parent_deforming(arm_obj, [body, armor, robe])

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

    # Cameras
    build_cameras()

    # Set active camera for preview render
    scene = bpy.context.scene
    scene.camera = bpy.data.objects["Cam_ThreeQuarter_L"]

    # Cycles GPU config
    G.configure_cycles(scene,
                       samples=192,
                       resolution_x=1440,
                       resolution_y=2560,
                       use_denoiser=True,
                       film_transparent=False)
    # film exposure lift (major #5): the full-body beauty shot must read
    # clearly — saved into the .blend so P5 renders inherit it
    # (0.5 washed the face to a white mask; 0.25 keeps form)
    scene.view_settings.exposure = 0.25
    print(f"[04_rig] Cycles: {scene.cycles.samples} samples, "
          f"{scene.render.resolution_x}x{scene.render.resolution_y}, "
          f"view_transform={scene.view_settings.view_transform}.")

    # Validate gate
    assert_phase4()

    # Save .blend BEFORE preview render so the saved file is the clean state
    bpy.ops.wm.save_as_mainfile(filepath=_BLEND_OUT, compress=True)
    sz = os.path.getsize(_BLEND_OUT) if os.path.isfile(_BLEND_OUT) else 0
    if sz < 10240:
        print(f"[04_rig] FATAL: .blend missing/too small ({sz} bytes): {_BLEND_OUT}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[04_rig] Saved {_BLEND_OUT} ({sz // 1024} KB).")

    # Lit GPU preview from Cam_ThreeQuarter_L
    print(f"[04_rig] Rendering lit preview -> {_PREVIEW_OUT}")
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
    print("[04_rig] Phase 4 complete — models/godwyn_phase1.blend saved.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
