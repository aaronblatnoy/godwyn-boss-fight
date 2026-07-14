"""
06_render_moveset.py — Phase 7: 7 Moveset Pose Renders

Opens models/godwyn_phase1.blend ONCE, loops through 7 SPEC-matching poses,
renders 1920x1080 GPU (OptiX) to renders/moveset/, resets between poses.

CHARACTER ORIENTATION (verified from blend):
  Godwyn faces -Y direction. Front cameras at negative Y.
  Existing cameras: Cam_Front at (0,-8.8,1.75), Cam_Full at (1.5,-9.4,1.6)
  Lights: Light_Key at (-1.8,-4.5,7.0), Light_Rim at (0.8,6.5,4.5)

BONE COORDINATE SYSTEM (verified):
  root:       local Y = global +Z (up). Location translation moves in local axes.
  pelvis/spine/chest/neck/head: local Y = global +Y (fwd toward +Y NOT toward camera).
    rx > 0 = lean toward +Y (AWAY from camera = lean back visually)
    rx < 0 = lean toward -Y (TOWARD camera = lean forward visually)
    rz > 0 = twist toward +X = twist LEFT as seen from front camera
    rz < 0 = twist toward -X = twist RIGHT as seen from front camera
  shoulder.R:  local Y = global +X (points right). rz > 0 = shoulder rises.
  upper_arm.R: rest Y ≈ (0, +0.5, -0.866) — arm hangs down-forward at ~60°.
    ry > 0 = arm swings OUTWARD (away from body, centrifugally)
    ry < 0 = arm swings INWARD (toward body)
    rx < 0 = arm raises FORWARD (toward -Y camera direction)
    rx > 0 = arm swings BACKWARD
  For upper_arm.R to go UP (overhead), need rx very negative (-110 to -140°).
  thigh.R: local Y ≈ (-0.09,-1.0,0.0) — points down in -Y direction.
    rx > 0 on thigh = leg swings BACKWARD (+Y direction)
    rx < 0 on thigh = leg swings FORWARD (-Y direction, toward camera)
  For jump: elevate with arm.location (armature object Z translation).

INV-1 headless, INV-2 GPU-real per render, INV-6 reset between poses.

Run: blender --background --python scripts/06_render_moveset.py
"""

import sys
import os
import math

import bpy
from mathutils import Euler, Vector

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

_REPO_ROOT    = os.path.dirname(_SCRIPT_DIR)
_BLEND_PATH   = os.path.join(_REPO_ROOT, "models", "godwyn_phase1.blend")
_MOVESET_DIR  = os.path.join(_REPO_ROOT, "renders", "moveset")

os.makedirs(_MOVESET_DIR, exist_ok=True)

RENDER_W       = 1920
RENDER_H       = 1080
RENDER_SAMPLES = 256

ARMATURE_NAME  = "Godwyn_Armature"
R = math.radians

# Actual light positions from blend file (character faces -Y)
_CANONICAL_LIGHTS = {
    "Light_Key":  ((-1.8, -4.5, 7.0), (0.0, 0.0, 2.0), 190.0),
    "Light_Fill": (( 4.0, -2.8, 2.2), (0.0, 0.0, 1.8),  35.0),
    "Light_Rim":  (( 0.8,  6.5, 4.5), (0.0, 0.0, 2.2), 260.0),
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _track_rotation(from_loc, to_loc):
    direction = Vector(to_loc) - Vector(from_loc)
    return direction.to_track_quat("-Z", "Y").to_euler()


def _set_camera(name, location, look_at, lens=65, roll=0.0):
    scene = bpy.context.scene
    cam_obj = bpy.data.objects.get(name)
    if cam_obj is None:
        cam_data = bpy.data.cameras.new(name)
        cam_obj = bpy.data.objects.new(name, cam_data)
        col = bpy.data.collections.get("Godwyn") or scene.collection
        col.objects.link(cam_obj)
    cam_obj.location = Vector(location)
    cam_obj.rotation_euler = _track_rotation(location, look_at)
    if roll != 0.0:
        cam_obj.rotation_euler[2] += R(roll)
    cam_obj.data.lens = lens
    cam_obj.data.clip_end = 200.0
    scene.camera = cam_obj
    return cam_obj


def _get_arm():
    arm = bpy.data.objects.get(ARMATURE_NAME)
    if arm is None:
        print(f"[06] FATAL: '{ARMATURE_NAME}' not found", file=sys.stderr)
        sys.exit(1)
    return arm


def reset_pose(arm):
    """Full reset: bone poses + armature object transform."""
    for pb_bone in arm.pose.bones:
        pb_bone.rotation_mode = "XYZ"
        pb_bone.rotation_euler = Euler((0, 0, 0))
        pb_bone.location       = Vector((0, 0, 0))
        pb_bone.scale          = Vector((1, 1, 1))
    # Reset armature object itself
    arm.location      = Vector((0, 0, 0))
    arm.rotation_euler = Euler((0, 0, 0))
    bpy.context.view_layer.update()


def pb(arm, name, rx=0.0, ry=0.0, rz=0.0):
    """Set pose bone euler (XYZ, radians)."""
    bone = arm.pose.bones.get(name)
    if bone is None:
        print(f"[06] WARNING: bone '{name}' missing", file=sys.stderr)
        return
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = Euler((rx, ry, rz))


def shift_light(name, location, look_at, energy=None):
    lo = bpy.data.objects.get(name)
    if lo is None:
        return
    lo.location = Vector(location)
    lo.rotation_euler = _track_rotation(location, look_at)
    if energy is not None:
        lo.data.energy = energy


def restore_lights():
    for name, (loc, tgt, eng) in _CANONICAL_LIGHTS.items():
        shift_light(name, loc, tgt, eng)


def assert_gpu(scene):
    cprefs = bpy.context.preferences.addons["cycles"].preferences
    gpu = [d for d in cprefs.devices if d.use and d.type in ("OPTIX", "CUDA")]
    if not gpu:
        print("[06] FATAL: no GPU enabled before render", file=sys.stderr)
        sys.exit(1)
    scene.cycles.device = "GPU"
    print(f"[06] GPU: {[d.name for d in gpu]}")


def configure_scene(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = RENDER_SAMPLES
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.008
    scene.render.resolution_x = RENDER_W
    scene.render.resolution_y = RENDER_H
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except Exception:
        try:
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
        except Exception:
            pass
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "None"


def render_pose(filepath, scene):
    assert_gpu(scene)
    scene.render.filepath = filepath
    print(f"[06] Rendering -> {os.path.basename(filepath)}")
    bpy.ops.render.render(write_still=True)
    size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    if size < 1024:
        print(f"[06] FATAL: output too small ({size}B): {filepath}", file=sys.stderr)
        sys.exit(1)
    print(f"[06] OK: {os.path.basename(filepath)} ({size//1024} KB)")


# ===========================================================================
# POSE DEFINITIONS
#
# REMEMBER:
#   Character faces -Y. Camera at -Y = frontal view.
#   spine rx < 0  = leans toward -Y = leans TOWARD camera (forward)
#   spine rz > 0  = twists toward +X = body turns LEFT from viewer
#   spine rz < 0  = twists toward -X = body turns RIGHT from viewer
#   upper_arm.R ry > 0 = extends OUTWARD (away from body centrifugally)
#   upper_arm.R ry < 0 = pulls INWARD (toward body)
#   upper_arm.R rx < 0 = swings arm toward -Y = FORWARD (toward camera)
#   upper_arm.R rx > 0 = swings arm toward +Y = BACKWARD
#   thigh.R rx < 0 = leg FORWARD toward camera
#   thigh.R rx > 0 = leg BACKWARD
#   For airborne: translate arm.location upward on Z
# ===========================================================================


def pose_1_low_hang_guard(arm, scene):
    """
    SPEC 395-398: neutral LOW HANG GUARD.
    Sword hanging low at his right side, tip angled toward ground.
    Slight forward lean (toward -Y camera). Right arm close to body, down.
    Weight on right leg (contrapposto). Noble, loaded, inevitable.
    Camera: frontal 3/4 left, slightly below chest level — full figure readable.
    """
    reset_pose(arm)

    # Very slight forward lean (toward camera = rx < 0 on spine)
    pb(arm, "spine.01", rx=R(-3))
    pb(arm, "chest",    rx=R(-2))

    # RIGHT arm (sword) — close to body, hanging LOW
    # Pull arm IN toward body (ry < 0) and slightly back (rx > 0)
    pb(arm, "shoulder.R",  rx=R(5),  rz=R(-5))
    pb(arm, "upper_arm.R", rx=R(10), ry=R(-35), rz=R(-5))
    pb(arm, "forearm.R",   rx=R(10))
    # Hand rotated so blade tip angles downward
    pb(arm, "hand.R",      rx=R(-10), ry=R(15))

    # LEFT arm — relaxed, slightly out from body
    pb(arm, "shoulder.L",  rx=R(3),  rz=R(5))
    pb(arm, "upper_arm.L", rx=R(5),  ry=R(-25))
    pb(arm, "forearm.L",   rx=R(5))

    # Contrapposto legs
    pb(arm, "thigh.R", rz=R(-3))
    pb(arm, "thigh.L", rz=R( 3))

    # Head up, slightly back — noble bearing
    pb(arm, "neck", rx=R(3))
    pb(arm, "head", rx=R(2))

    bpy.context.view_layer.update()
    restore_lights()
    # Boost key energy for a clear read
    shift_light("Light_Key", (-2.0, -5.5, 6.5), (0, 0, 2.0), energy=380)

    # Camera: frontal 3/4 left, slightly below chest — see full figure + sword
    _set_camera("Cam_Moveset_01",
                location=(-3.0, -9.5, 0.8),
                look_at=(0.3, 0.0, 2.0),
                lens=65)


def pose_2_x_combo_hit1(arm, scene):
    """
    SPEC 447: X COMBO hit 1 — diagonal \\ (top-RIGHT down to bottom-LEFT).
    Body twisted RIGHT (rz < 0 from viewer = CW). Right arm high-right,
    sword at TOP of arc about to sweep down-left.
    Camera: right-side front, slightly low — catches the raised sword arc.
    """
    reset_pose(arm)

    # Body rotates RIGHT from viewer perspective = rz < 0 on spine bones
    pb(arm, "pelvis",   rz=R(-22), rx=R(-3))
    pb(arm, "spine.01", rz=R(-20), rx=R(-5))
    pb(arm, "chest",    rz=R(-15), rx=R(-6))

    # RIGHT arm: RAISED HIGH-RIGHT — sword at top of \\ arc
    # Shoulder rises (rz > 0) and forward (rx < 0 = toward -Y = forward)
    pb(arm, "shoulder.R",  rx=R(-15), rz=R(20))
    # Upper arm sweeps up and outward: rx < 0 forward + ry > 0 outward
    pb(arm, "upper_arm.R", rx=R(-105), ry=R(25), rz=R(15))
    pb(arm, "forearm.R",   rx=R(20))
    pb(arm, "hand.R",      rx=R(5), ry=R(-15))

    # LEFT arm: counterbalance swept left-low
    pb(arm, "shoulder.L",  rx=R(8), rz=R(-8))
    pb(arm, "upper_arm.L", rx=R(15), ry=R(-20))
    pb(arm, "forearm.L",   rx=R(8))

    # Legs: wide stance — right back, left forward (body weight left-forward)
    pb(arm, "thigh.R",  rx=R(8),  rz=R(-5))  # right leg BACK
    pb(arm, "shin.R",   rx=R(-8))
    pb(arm, "thigh.L",  rx=R(-15), rz=R(5))  # left leg FORWARD
    pb(arm, "shin.L",   rx=R(10))

    pb(arm, "neck", rz=R(-8))
    pb(arm, "head", rz=R(-10))

    bpy.context.view_layer.update()

    # Key from upper-left (camera's left = character's right = where sword is)
    shift_light("Light_Key",  (-4.5, -4.0, 8.5), (0.5, 0, 2.5), energy=600)
    shift_light("Light_Rim",  ( 5.0,  5.0, 3.5), (0, 0, 2.0), energy=320)
    shift_light("Light_Fill", ( 3.0, -4.0, 1.5), (0, 0, 1.8), energy=55)

    # Camera: right-front low angle — from right side (positive X) + front (-Y)
    _set_camera("Cam_Moveset_02",
                location=(5.5, -6.5, 0.5),
                look_at=(-0.5, 0.0, 2.4),
                lens=55)


def pose_3_x_combo_hit2(arm, scene):
    """
    SPEC 447: X COMBO hit 2 — diagonal / (top-LEFT down to bottom-RIGHT).
    Body twisted LEFT (rz > 0 from viewer = CCW), completing the X.
    Sword extended out to his right, sweeping downward to bottom-right.
    Camera: left-side front, low angle.
    """
    reset_pose(arm)

    # Body twisted LEFT from viewer = rz > 0
    pb(arm, "pelvis",   rz=R(25), rx=R(-3))
    pb(arm, "spine.01", rz=R(22), rx=R(-5))
    pb(arm, "chest",    rz=R(16), rx=R(-6))

    # RIGHT arm: sweep has come DOWN from top-left — arm now lower-right
    # rx small negative (arm mostly sideways-out), ry > 0 (outward extended)
    pb(arm, "shoulder.R",  rx=R(-8), rz=R(5))
    pb(arm, "upper_arm.R", rx=R(-55), ry=R(35), rz=R(-10))
    pb(arm, "forearm.R",   rx=R(15))
    pb(arm, "hand.R",      rx=R(10), ry=R(-20))

    # LEFT arm: swept HIGH-LEFT as counterbalance
    pb(arm, "shoulder.L",  rx=R(-12), rz=R(18))
    pb(arm, "upper_arm.L", rx=R(-90), ry=R(-20), rz=R(15))
    pb(arm, "forearm.L",   rx=R(25))

    # Legs: reversed from pose 2
    pb(arm, "thigh.R",  rx=R(-15), rz=R(-5))  # right leg FORWARD
    pb(arm, "shin.R",   rx=R(10))
    pb(arm, "thigh.L",  rx=R(8),   rz=R(5))   # left leg BACK
    pb(arm, "shin.L",   rx=R(-8))

    pb(arm, "neck", rz=R(10))
    pb(arm, "head", rz=R(12))

    bpy.context.view_layer.update()

    # Key from upper-right
    shift_light("Light_Key",  (4.5, -4.0, 8.5), (-0.5, 0, 2.5), energy=600)
    shift_light("Light_Rim",  (-5.0,  5.0, 3.5), (0, 0, 2.0), energy=320)
    shift_light("Light_Fill", (-3.0, -4.0, 1.5), (0, 0, 1.8), energy=55)

    # Camera: left-front low angle
    _set_camera("Cam_Moveset_03",
                location=(-5.5, -6.5, 0.5),
                look_at=(0.5, 0.0, 2.4),
                lens=55)


def pose_4_overhead_slam(arm, scene):
    """
    SPEC 430: overhead slam — sword raised TWO-HANDED above head.
    Right hand on hilt, left grips lower blade (two-handed overhead).
    Body arched back slightly, arms fully overhead, about to slam DOWN.
    Camera: front, medium-low, capture full figure with arms overhead.
    """
    reset_pose(arm)

    # Very slight backward arch (arms overhead = natural arch)
    pb(arm, "pelvis",   rx=R(5))
    pb(arm, "spine.01", rx=R(4))
    pb(arm, "chest",    rx=R(3))

    # Head back slightly — looking up at the sword
    pb(arm, "neck", rx=R(8))
    pb(arm, "head", rx=R(10))

    # RIGHT arm: PRIMARY GRIP — FULLY overhead (rx very negative)
    pb(arm, "shoulder.R",  rx=R(-25), rz=R(30))
    pb(arm, "upper_arm.R", rx=R(-155), ry=R(15), rz=R(15))
    pb(arm, "forearm.R",   rx=R(15))
    pb(arm, "hand.R",      rx=R(-10), ry=R(5))

    # LEFT arm: OFF-HAND GRIP — mirrors right, both overhead
    pb(arm, "shoulder.L",  rx=R(-22), rz=R(30))
    pb(arm, "upper_arm.L", rx=R(-145), ry=R(-18), rz=R(-15))
    pb(arm, "forearm.L",   rx=R(20))
    pb(arm, "hand.L",      rx=R(-8), ry=R(-5))

    # Legs: stable wide stance
    pb(arm, "thigh.R", rx=R(5),  rz=R(-6))
    pb(arm, "shin.R",  rx=R(-5))
    pb(arm, "thigh.L", rx=R(5),  rz=R( 6))
    pb(arm, "shin.L",  rx=R(-5))

    bpy.context.view_layer.update()

    # Overhead drama: key from front-above
    shift_light("Light_Key",  (0.0, -3.5, 10.5), (0, 0, 3.5), energy=800)
    shift_light("Light_Fill", (4.0, -4.5, 2.0),  (0, 0, 2.0), energy=50)
    shift_light("Light_Rim",  (0.5,  6.5, 5.0),  (0, 0, 2.5), energy=280)

    # Camera: slightly lower front, wide lens — see arms overhead + whole figure
    _set_camera("Cam_Moveset_04",
                location=(0.5, -9.5, -0.5),
                look_at=(0.0, 0.0, 3.0),
                lens=55)


def pose_5_backhand_rotation(arm, scene):
    """
    SPEC 500-501: mid CCW spin, BACK TO CAMERA.
    Armature object rotated 180° — character now faces +Y (away from us).
    Sword swings around on the backhand; body mid-CCW spin.
    Camera at +Y to see his back clearly.
    """
    reset_pose(arm)

    # Rotate the whole armature 180° to face away
    arm.rotation_euler = Euler((0, 0, R(180)))

    # In his local frame (now facing +Y), body mid-CCW spin:
    # rz > 0 in his NEW facing would be... let's keep small twist
    pb(arm, "pelvis",   rz=R(-10), rx=R(-3))
    pb(arm, "spine.01", rz=R(-8),  rx=R(-2))
    pb(arm, "chest",    rz=R(-5))

    # Head turned to look back over his shoulder (toward +X direction now)
    pb(arm, "neck", rz=R(15), rx=R(5))
    pb(arm, "head", rz=R(20), rx=R(5))

    # RIGHT arm (sword): on the backhand sweep — arm extended to his side
    # In his new +Y facing, "extending outward right" = extending toward global -X
    pb(arm, "shoulder.R",  rx=R(-5), rz=R(8))
    pb(arm, "upper_arm.R", rx=R(-30), ry=R(30), rz=R(10))
    pb(arm, "forearm.R",   rx=R(15))
    pb(arm, "hand.R",      rx=R(-5), ry=R(10))

    # LEFT arm: sweeping forward as counterbalance
    pb(arm, "shoulder.L",  rx=R(-8), rz=R(-5))
    pb(arm, "upper_arm.L", rx=R(-50), ry=R(-20), rz=R(-10))
    pb(arm, "forearm.L",   rx=R(15))

    # Legs: spinning stance — weight on right, left lifting
    pb(arm, "thigh.R", rx=R(5),  rz=R(-5))
    pb(arm, "thigh.L", rx=R(-10), rz=R(4))
    pb(arm, "shin.L",  rx=R(12))

    bpy.context.view_layer.update()

    # After 180° rotation: character faces +Y. Camera at -Y sees his BACK.
    # Key light from -Y (behind him now = illuminates his back well)
    shift_light("Light_Key",  (-1.5, -7.5, 6.5), (0, 0, 2.0), energy=450)
    shift_light("Light_Fill", ( 3.5, -5.0, 2.5), (0, 0, 1.8), energy=80)
    # Rim from +Y (his new front) to silhouette the back edges
    shift_light("Light_Rim",  ( 0.5,  6.0, 4.5), (0, 0, 2.2), energy=200)

    # Camera at -Y (his back side after rotation) — sees his back + sword arc
    _set_camera("Cam_Moveset_05",
                location=(3.0, -9.0, 2.2),
                look_at=(0.0, 0.0, 2.0),
                lens=62)


def pose_6_jump_lunge(arm, scene):
    """
    SPEC 416/480: jump lunge — AIRBORNE, sword thrust downward.
    Elevate entire character by moving the armature object up on Z.
    Forward lean, legs tucked, right arm driving sword down-forward.
    Camera: frontal, very low, looking steeply UP — see airborne silhouette.
    """
    reset_pose(arm)

    # ELEVATE entire character by moving the armature object up on Z.
    # Note: arm.location is in world space since armature has no parent.
    arm.location = Vector((0, 0, 1.0))  # 1m airborne
    bpy.context.view_layer.update()

    # Forward lean into the lunge (rx < 0 toward camera)
    pb(arm, "pelvis",   rx=R(-15))
    pb(arm, "spine.01", rx=R(-12))
    pb(arm, "chest",    rx=R(-8))

    # Head looking slightly down at the target
    pb(arm, "neck", rx=R(5))
    pb(arm, "head", rx=R(8))

    # RIGHT arm: sword extended DOWNWARD — arm forward and down
    pb(arm, "shoulder.R",  rx=R(-5),  rz=R(8))
    pb(arm, "upper_arm.R", rx=R(-40), ry=R(15))
    pb(arm, "forearm.R",   rx=R(75))   # Elbow bends down hard
    pb(arm, "hand.R",      rx=R(15), ry=R(-8))

    # LEFT arm: extended sideways-back for airborne balance
    pb(arm, "shoulder.L",  rx=R(-18), rz=R(20))
    pb(arm, "upper_arm.L", rx=R(-85), ry=R(-20), rz=R(12))
    pb(arm, "forearm.L",   rx=R(22))

    # Legs TUCKED UP: thighs toward camera, shins bent back
    pb(arm, "thigh.R",  rx=R(-45), rz=R(-5))
    pb(arm, "shin.R",   rx=R(75))
    pb(arm, "foot.R",   rx=R(-22))
    pb(arm, "thigh.L",  rx=R(-38), rz=R(5))
    pb(arm, "shin.L",   rx=R(65))
    pb(arm, "foot.L",   rx=R(-18))

    bpy.context.view_layer.update()

    # Key from front-above; character is 1m higher so adjust target height
    shift_light("Light_Key",  (-1.5, -3.5, 10.5), (0, 0, 3.5), energy=750)
    shift_light("Light_Fill", ( 3.5, -5.0,  2.0), (0, 0, 3.0), energy=50)
    shift_light("Light_Rim",  ( 1.0,  6.5,  4.0), (0, 0, 3.5), energy=300)

    # Camera: positioned close enough to fill the frame properly
    # Character center is ~Z=3.2 (elevated 1m + natural ~2.2m center)
    # Camera at medium distance, looking at character center
    cam = _set_camera("Cam_Moveset_06",
                      location=(2.0, -7.5, 1.5),
                      look_at=(0.0, 0.0, 3.2),
                      lens=52,
                      roll=6)


def pose_7_double_spin(arm, scene):
    """
    SPEC 458-460: mid CW double-spin — sword extended centrifugally outward.
    Body twisted RIGHT (CW from viewer = rz < 0 on spine).
    Right arm fully extended outward, sword sweeping a wide arc.
    Camera: elevated 3/4 right-front — sees extended sword + robe sweep.
    """
    reset_pose(arm)

    # Body mid-CW spin (twist RIGHT from viewer = rz < 0)
    pb(arm, "pelvis",   rz=R(-50), rx=R(-3))
    pb(arm, "spine.01", rz=R(-40), rx=R(-4))
    pb(arm, "chest",    rz=R(-30), rx=R(-4))

    # Head: gaze leads the spin (looking right = rz < 0 from viewer)
    pb(arm, "neck", rz=R(-20))
    pb(arm, "head", rz=R(-25))

    # RIGHT arm: CENTRIFUGALLY EXTENDED outward in spin direction
    # In CW spin (turning right), right arm is the trailing extended arm
    pb(arm, "shoulder.R",  rx=R(-10), rz=R(18))
    pb(arm, "upper_arm.R", rx=R(-80), ry=R(45), rz=R(20))
    pb(arm, "forearm.R",   rx=R(10))   # Extended — near straight
    pb(arm, "hand.R",      ry=R(18))

    # LEFT arm: drawn inward from the centrifugal energy
    pb(arm, "shoulder.L",  rx=R(5),  rz=R(-8))
    pb(arm, "upper_arm.L", rx=R(15), ry=R(-20), rz=R(15))
    pb(arm, "forearm.L",   rx=R(8))

    # Legs: right planted (pivot), left lifts in spin
    pb(arm, "thigh.R",  rx=R(5),  rz=R(-6))
    pb(arm, "shin.R",   rx=R(-4))
    pb(arm, "thigh.L",  rx=R(-20), rz=R(5))
    pb(arm, "shin.L",   rx=R(25))

    bpy.context.view_layer.update()

    # Rim light from his extended right (= global +X side from him, shifted by spin)
    shift_light("Light_Key",  (-1.5, -4.0, 7.5), (0, 0, 2.0), energy=520)
    shift_light("Light_Fill", (-3.5, -3.5, 1.5), (0, 0, 1.8), energy=60)
    shift_light("Light_Rim",  ( 7.0,  2.0, 3.5), (0, 0, 2.0), energy=400)

    # Camera: elevated 3/4 right-front
    _set_camera("Cam_Moveset_07",
                location=(7.0, -6.5, 3.0),
                look_at=(0.0, 0.0, 2.0),
                lens=60)


# ===========================================================================
# POSE TABLE
# ===========================================================================

POSES = [
    ("1_low_hang_guard",    pose_1_low_hang_guard),
    ("2_x_combo_hit1",      pose_2_x_combo_hit1),
    ("3_x_combo_hit2",      pose_3_x_combo_hit2),
    ("4_overhead_slam",     pose_4_overhead_slam),
    ("5_backhand_rotation", pose_5_backhand_rotation),
    ("6_jump_lunge",        pose_6_jump_lunge),
    ("7_double_spin",       pose_7_double_spin),
]

EXPECTED_FILES = [f"{name}.png" for name, _ in POSES]


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("=" * 60)
    print("[06] Phase 7 — Moveset Pose Renders (7 poses)")
    print("=" * 60)

    active_gpu = G.enable_gpu()
    print(f"[06] GPU active: {active_gpu}")

    if not os.path.isfile(_BLEND_PATH):
        print(f"[06] FATAL: .blend not found: {_BLEND_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"[06] Opening {_BLEND_PATH} ...")
    bpy.ops.wm.open_mainfile(filepath=_BLEND_PATH)
    active_gpu = G.enable_gpu()
    print(f"[06] GPU re-enabled: {active_gpu}")

    scene = bpy.context.scene
    configure_scene(scene)

    arm = _get_arm()
    print(f"[06] Armature: '{arm.name}', {len(arm.pose.bones)} bones")

    sword = bpy.data.objects.get("Godwyn_Sword")
    if sword is None:
        print("[06] FATAL: Godwyn_Sword missing", file=sys.stderr)
        sys.exit(1)

    failed = []

    for i, (pose_name, pose_fn) in enumerate(POSES, start=1):
        out_path = os.path.join(_MOVESET_DIR, f"{pose_name}.png")
        print(f"\n[06] --- Pose {i}/7: {pose_name} ---")
        try:
            pose_fn(arm, scene)
            bpy.context.view_layer.update()
            render_pose(out_path, scene)
        except Exception as exc:
            import traceback
            msg = f"Pose {i} ({pose_name}): {exc}"
            print(f"[06] DEFERRED: {msg}", file=sys.stderr)
            traceback.print_exc()
            failed.append(msg)
        finally:
            reset_pose(arm)
            restore_lights()
            bpy.context.view_layer.update()

    # Validation gate
    print("\n[06] --- Validation ---")
    produced, missing = [], []
    for fname in EXPECTED_FILES:
        fpath = os.path.join(_MOVESET_DIR, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) >= 1024:
            produced.append(f"{fname} ({os.path.getsize(fpath)//1024} KB)")
        else:
            missing.append(fname)

    for f in produced:
        print(f"  OK   {f}")
    for f in missing:
        print(f"  MISS {f}", file=sys.stderr)
    for f in failed:
        print(f"  FAIL {f}", file=sys.stderr)

    if missing:
        print(f"[06] FATAL: {len(missing)} missing — gate NOT met", file=sys.stderr)
        sys.exit(1)

    print(f"[06] GATE MET: {len(produced)}/{len(EXPECTED_FILES)} renders in {_MOVESET_DIR}")
    print(f"[06] GPU: {active_gpu}")
    print("[06] Phase 7 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
