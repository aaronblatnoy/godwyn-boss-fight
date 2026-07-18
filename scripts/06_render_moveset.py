"""
06_render_moveset.py — Phase 6: 7 Moveset Pose Renders (REFINED)

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

REFINEMENTS (natural-pose pass):
  - VoidCrack + extra lights hidden during moveset (restored after each pose)
  - Pose 1: hand rotated so blade broad face shows (not edge-on)
  - Pose 5: sword arm extended further, shoulder and upper arm adjusted
  - All poses: moderate joint angles, no extreme/contorted positions
  - Light artifacts eliminated

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

# Canonical light positions from blend file (character faces -Y)
_CANONICAL_LIGHTS = {
    "Light_Key":  ((-1.8, -4.5, 7.0), (0.0, 0.0, 2.0), 190.0),
    "Light_Fill": (( 4.0, -2.8, 2.2), (0.0, 0.0, 1.8),  35.0),
    "Light_Rim":  (( 0.8,  6.5, 4.5), (0.0, 0.0, 2.2), 260.0),
}

# Objects to hide during moveset renders to eliminate artifacts
# VoidCrack causes bright vertical/rectangular flare artifacts
_HIDE_FOR_MOVESET = ["Godwyn_VoidCrack"]
# Extra lights that produce noise but aren't needed for moveset shots
_EXTRA_LIGHTS = ["Light_EyeFill", "Light_Hands", "Light_Kick"]


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
    # Restore extra lights visibility
    for name in _EXTRA_LIGHTS:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = True  # keep them hidden — moveset doesn't need them
    # Restore hidden objects
    for name in _HIDE_FOR_MOVESET:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = True  # keep hidden for all moveset renders


def setup_moveset_scene():
    """Hide artifacts and extra lights before any pose renders."""
    for name in _HIDE_FOR_MOVESET:
        obj = bpy.data.objects.get(name)
        if obj:
            print(f"[06] Hiding: {name}")
            obj.hide_render = True
    for name in _EXTRA_LIGHTS:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = True


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
# POSE DEFINITIONS — NATURAL POSES PASS
#
# Philosophy: moderate joint angles, real balance, weighty stances.
# No extreme contortions. Real Elden Ring boss energy.
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
    SPEC: LOW HANG GUARD — neutral loaded stance.
    Sword hanging low at right side, blade tip toward ground.
    Slight contrapposto weight shift right. Noble bearing.
    KEY FIX: hand.R rotated so sword blade shows its broad face to camera,
    not edge-on (which made it look like a thin pole).
    Camera: 3/4 left, slightly low — full figure readable, sword visible.
    """
    reset_pose(arm)

    # Very slight forward lean (toward camera)
    pb(arm, "spine.01", rx=R(-3))
    pb(arm, "chest",    rx=R(-2))

    # RIGHT arm (sword) — hanging low, close to body
    # Pull arm IN toward body (ry < 0) and slightly back (rx > 0)
    pb(arm, "shoulder.R",  rx=R(5),  rz=R(-5))
    pb(arm, "upper_arm.R", rx=R(10), ry=R(-30), rz=R(-5))
    pb(arm, "forearm.R",   rx=R(12))
    # FIXED: hand.R — ry=-25 rotates wrist so blade broad face shows to camera
    # (old: ry=R(15) was edge-on; now ry=R(-25) opens the flat to camera)
    pb(arm, "hand.R",      rx=R(-5), ry=R(-25), rz=R(-10))

    # LEFT arm — relaxed at side, slightly out
    pb(arm, "shoulder.L",  rx=R(3),  rz=R(5))
    pb(arm, "upper_arm.L", rx=R(5),  ry=R(-25))
    pb(arm, "forearm.L",   rx=R(5))

    # Contrapposto: weight right, hip left
    pb(arm, "thigh.R", rx=R(2),  rz=R(-3))
    pb(arm, "thigh.L", rx=R(-2), rz=R( 3))

    # Head up — noble bearing, slight pride
    pb(arm, "neck", rx=R(3))
    pb(arm, "head", rx=R(2))

    bpy.context.view_layer.update()
    restore_lights()
    shift_light("Light_Key", (-2.0, -5.5, 6.5), (0, 0, 2.0), energy=380)

    # Camera: frontal 3/4 left — full figure + sword readable
    _set_camera("Cam_Moveset_01",
                location=(-3.5, -9.5, 0.9),
                look_at=(0.3, 0.0, 2.0),
                lens=60)


def pose_2_x_combo_hit1(arm, scene):
    """
    SPEC: X COMBO hit 1 — diagonal \\ (top-RIGHT down to bottom-LEFT).
    Body twisted right, right arm high, sword at top of arc about to sweep down.
    NATURAL: moderate 20-deg torso twist, arm raised but not hyperextended.
    Camera: right-side front, slightly low — catches raised sword arc.
    """
    reset_pose(arm)

    # Moderate axial twist toward sword side + slight forward lean
    pb(arm, "pelvis",   ry=R(18), rx=R(-4))
    pb(arm, "spine.01", ry=R(14), rx=R(-5))
    pb(arm, "chest",    ry=R(10), rx=R(-5))

    # RIGHT arm: RAISED HIGH-RIGHT — top of \\ arc
    pb(arm, "shoulder.R",  rx=R(-12), rz=R(18))
    pb(arm, "upper_arm.R", rx=R(-115), ry=R(28), rz=R(12))
    pb(arm, "forearm.R",   rx=R(28))
    # Hand opens sword to camera (broad face forward)
    pb(arm, "hand.R",      rx=R(5), ry=R(-12), rz=R(25))

    # LEFT arm: counterbalance swept left
    pb(arm, "shoulder.L",  rx=R(6), rz=R(-6))
    pb(arm, "upper_arm.L", rx=R(12), ry=R(-18))
    pb(arm, "forearm.L",   rx=R(8))

    # Legs: natural split stance — right back, left forward
    pb(arm, "thigh.R",  rx=R(8),  rz=R(-5))
    pb(arm, "shin.R",   rx=R(-6))
    pb(arm, "thigh.L",  rx=R(-12), rz=R(5))
    pb(arm, "shin.L",   rx=R(8))

    pb(arm, "neck", ry=R(6))
    pb(arm, "head", ry=R(8))

    bpy.context.view_layer.update()

    # Key from upper-left (camera's left = character's right = where sword is)
    shift_light("Light_Key",  (-4.5, -4.0, 8.5), (0.5, 0, 2.5), energy=600)
    shift_light("Light_Rim",  ( 5.0,  5.0, 3.5), (0, 0, 2.0), energy=320)
    shift_light("Light_Fill", ( 3.0, -4.0, 1.5), (0, 0, 1.8), energy=55)

    # Camera: right-front low angle — reads sword high against void
    _set_camera("Cam_Moveset_02",
                location=(5.0, -8.2, 1.4),
                look_at=(0.0, 0.0, 1.95),
                lens=48)


def pose_3_x_combo_hit2(arm, scene):
    """
    SPEC: X COMBO hit 2 — diagonal / (top-LEFT down to bottom-RIGHT).
    Body twisted left completing the X, sword swinging down-right.
    NATURAL: moderate 20-deg counter-twist, natural follow-through.
    Camera: left-front, low angle.
    """
    reset_pose(arm)

    # Counter-twist as blade sweeps down-right
    pb(arm, "pelvis",   ry=R(-18), rx=R(-4))
    pb(arm, "spine.01", ry=R(-14), rx=R(-5))
    pb(arm, "chest",    ry=R(-10), rx=R(-5))

    # RIGHT arm: sweep coming DOWN — arm now lower-right extended
    pb(arm, "shoulder.R",  rx=R(-6), rz=R(4))
    pb(arm, "upper_arm.R", rx=R(-50), ry=R(32), rz=R(-8))
    pb(arm, "forearm.R",   rx=R(12))
    pb(arm, "hand.R",      rx=R(8), ry=R(-18))

    # LEFT arm: swept HIGH-LEFT as counterbalance
    pb(arm, "shoulder.L",  rx=R(-10), rz=R(16))
    pb(arm, "upper_arm.L", rx=R(-82), ry=R(-18), rz=R(12))
    pb(arm, "forearm.L",   rx=R(22))

    # Legs: reversed from pose 2
    pb(arm, "thigh.R",  rx=R(-12), rz=R(-5))
    pb(arm, "shin.R",   rx=R(8))
    pb(arm, "thigh.L",  rx=R(8),   rz=R(5))
    pb(arm, "shin.L",   rx=R(-6))

    pb(arm, "neck", ry=R(-7))
    pb(arm, "head", ry=R(-9))

    bpy.context.view_layer.update()

    # Key from upper-right
    shift_light("Light_Key",  (4.5, -4.0, 8.5), (-0.5, 0, 2.5), energy=600)
    shift_light("Light_Rim",  (-5.0,  5.0, 3.5), (0, 0, 2.0), energy=320)
    shift_light("Light_Fill", (-3.0, -4.0, 1.5), (0, 0, 1.8), energy=55)

    # Camera: left-front low angle
    _set_camera("Cam_Moveset_03",
                location=(-5.0, -8.2, 1.4),
                look_at=(0.0, 0.0, 1.95),
                lens=48)


def pose_4_overhead_slam(arm, scene):
    """
    SPEC: OVERHEAD SLAM — two-handed overhead, committed but not contorted.
    Arms raised above head, sword pointing up. Believable power stance.
    NATURAL: moderate backward arch (not extreme), arms naturally overhead.
    Camera: frontal, low upshot. Shows full silhouette against void.
    """
    reset_pose(arm)

    # Slight backward arch — chest forward, committed power
    pb(arm, "pelvis",   rx=R(8))
    pb(arm, "spine.01", rx=R(6))
    pb(arm, "chest",    rx=R(4))

    # Head tilts back — looking up past the blade
    pb(arm, "neck", rx=R(-8))
    pb(arm, "head", rx=R(-12))

    # RIGHT arm: OVERHEAD. rx=-150 brings arm fully up from rest position.
    # ry=-20 pulls it toward centerline for two-hand grip proximity.
    pb(arm, "shoulder.R",  rx=R(-22), rz=R(18))
    pb(arm, "upper_arm.R", rx=R(-148), ry=R(-22), rz=R(0))
    pb(arm, "forearm.R",   rx=R(6))   # slight natural bend
    pb(arm, "hand.R",      rx=R(-5), rz=R(50))

    # LEFT arm: off-hand grip — both arms overhead close together
    pb(arm, "shoulder.L",  rx=R(-20), rz=R(16))
    pb(arm, "upper_arm.L", rx=R(-140), ry=R(22), rz=R(0))
    pb(arm, "forearm.L",   rx=R(8))
    pb(arm, "hand.L",      rx=R(-5))

    # Legs: wide grounded stance, slight knee bend for power
    pb(arm, "thigh.R", rx=R(5),  rz=R(-8))
    pb(arm, "shin.R",  rx=R(-8))
    pb(arm, "thigh.L", rx=R(5),  rz=R(8))
    pb(arm, "shin.L",  rx=R(-8))

    bpy.context.view_layer.update()

    # Key from high front — dramatically under-lights the raised arms
    shift_light("Light_Key",  (0.0,  -3.5, 10.0), (0, 0, 3.2), energy=1000)
    shift_light("Light_Fill", (4.0,  -5.0,  2.0), (0, 0, 2.0), energy=60)
    shift_light("Light_Rim",  (0.5,   7.0,  5.0), (0, 0, 2.5), energy=300)

    # Camera: frontal low upshot — feet/legs/torso/arms+sword fill frame
    _set_camera("Cam_Moveset_04",
                location=(0.6, -9.8, 0.55),
                look_at=(0.0, 0.0, 2.55),
                lens=40)


def pose_5_backhand_rotation(arm, scene):
    """
    SPEC: BACKHAND ROTATION — CCW turning cut, back mostly to camera.
    Armature rotated ~125 deg so we see a 3/4 back-left angle.
    The backhand swing = sword arm sweeps across (R arm arcing to the left).
    At this angle, the extended sword arm is visible against the void.
    Camera: low right-side to see the sword arc extending across body.
    """
    reset_pose(arm)

    # 125-deg rotation: character faces mostly left-back
    # CCW spin: his chest faces ~35deg past the camera's left.
    # His R arm (with sword) swings across in front from this view.
    arm.rotation_euler = Euler((0, 0, R(125)))

    # Body mid-CCW spin: twist + slight lean into the swing
    pb(arm, "pelvis",   ry=R(-10), rx=R(-4))
    pb(arm, "spine.01", ry=R(-8),  rx=R(-3))
    pb(arm, "chest",    ry=R(-5))

    # Head looking over left shoulder toward camera (natural spin look)
    pb(arm, "neck", ry=R(-15), rx=R(3))
    pb(arm, "head", ry=R(-20), rx=R(4))

    # RIGHT arm (sword): backhand extended — arm sweeping across the body
    # ry > 0 = outward, rx < 0 = forward-ish; this should extend sword to the left
    pb(arm, "shoulder.R",  rx=R(-5), rz=R(12))
    pb(arm, "upper_arm.R", rx=R(-60), ry=R(50), rz=R(10))
    pb(arm, "forearm.R",   rx=R(8))   # nearly straight
    pb(arm, "hand.R",      rx=R(-10), ry=R(20), rz=R(-30))

    # LEFT arm: counterbalance pulling back
    pb(arm, "shoulder.L",  rx=R(5), rz=R(-8))
    pb(arm, "upper_arm.L", rx=R(15), ry=R(-22), rz=R(-5))
    pb(arm, "forearm.L",   rx=R(8))

    # Legs: grounded spin — right planted, left trailing
    pb(arm, "thigh.R", rx=R(4),  rz=R(-5))
    pb(arm, "shin.R",  rx=R(-4))
    pb(arm, "thigh.L", rx=R(-6), rz=R(4))
    pb(arm, "shin.L",  rx=R(8))

    bpy.context.view_layer.update()

    # Key light from camera-side (low-left in world) to illuminate the swing
    shift_light("Light_Key",  (-3.5, -6.5, 6.5), (0, 0, 2.0), energy=520)
    shift_light("Light_Fill", ( 4.0, -4.0, 2.5), (0, 0, 1.8), energy=70)
    # Rim from behind the character to outline the silhouette
    shift_light("Light_Rim",  ( 2.5,  6.0, 4.5), (0, 0, 2.2), energy=300)

    # Camera: low-right-front — looking at the 3/4 back-left figure.
    # Position at camera-left (+X) to see the sword arc sweeping past the body.
    _set_camera("Cam_Moveset_05",
                location=(5.5, -6.5, 1.5),
                look_at=(0.0, 0.0, 2.0),
                lens=55)


def pose_6_jump_lunge(arm, scene):
    """
    SPEC: JUMP LUNGE — grounded leaping thrust, not wild mid-air split.
    Character 1m airborne, forward lean, sword extending downward-forward.
    NATURAL: moderate leg tuck (not extreme 90-deg splits), believable arc.
    Camera: frontal low-angle upshot — reads airborne silhouette clearly.
    """
    reset_pose(arm)

    # Elevate character: 1m off ground
    arm.location = Vector((0, 0, 1.0))
    bpy.context.view_layer.update()

    # Forward lean into the lunge — committed but not contorted
    pb(arm, "pelvis",   rx=R(-12))
    pb(arm, "spine.01", rx=R(-10))
    pb(arm, "chest",    rx=R(-6))

    # Head looking slightly down at target
    pb(arm, "neck", rx=R(5))
    pb(arm, "head", rx=R(7))

    # RIGHT arm: sword extended DOWNWARD-FORWARD — committed lunge
    pb(arm, "shoulder.R",  rx=R(-5),  rz=R(8))
    pb(arm, "upper_arm.R", rx=R(-38), ry=R(14))
    pb(arm, "forearm.R",   rx=R(68))   # elbow bends into the thrust
    pb(arm, "hand.R",      rx=R(12), ry=R(-10))

    # LEFT arm: spread for airborne balance
    pb(arm, "shoulder.L",  rx=R(-15), rz=R(18))
    pb(arm, "upper_arm.L", rx=R(-48), ry=R(-35), rz=R(25))
    pb(arm, "forearm.L",   rx=R(20))

    # Legs MODERATELY TUCKED — not extreme splits, natural in-flight
    pb(arm, "thigh.R",  rx=R(-38), rz=R(-5))
    pb(arm, "shin.R",   rx=R(60))
    pb(arm, "foot.R",   rx=R(-18))
    pb(arm, "thigh.L",  rx=R(-30), rz=R(5))
    pb(arm, "shin.L",   rx=R(50))
    pb(arm, "foot.L",   rx=R(-14))

    bpy.context.view_layer.update()

    # Key from front-above; character 1m higher so adjust target
    shift_light("Light_Key",  (-1.5, -3.5, 10.5), (0, 0, 3.5), energy=750)
    shift_light("Light_Fill", ( 3.5, -5.0,  2.0), (0, 0, 3.0), energy=50)
    shift_light("Light_Rim",  ( 1.0,  6.5,  4.0), (0, 0, 3.5), energy=300)

    # Camera: 3/4 low-front angle, closer in — fills the frame better.
    # Character is 1m elevated; center mass ~Z=3.2. Camera at Z=1.0
    # gives a moderate upshot without crushing them into the top of frame.
    # The sword extending down-forward reads clearly from this angle.
    _set_camera("Cam_Moveset_06",
                location=(2.0, -8.0, 1.0),
                look_at=(0.0, 0.0, 2.8),
                lens=50,
                roll=3)


def pose_7_double_spin(arm, scene):
    """
    SPEC: DOUBLE SPIN — mid CW turning cut, sword extended centrifugally.
    Character upright (spinning = vertical axis), sword sweeping outward right.
    NATURAL: 25-deg torso twist, arm extended — upright and grounded, not falling.
    Camera: frontal right-offset — reads upright figure + wide sword arc.
    """
    reset_pose(arm)

    # Body mid-CW spin: modest axial twist (ry = axial on this rig)
    pb(arm, "pelvis",   ry=R(-22), rx=R(-2))
    pb(arm, "spine.01", ry=R(-17), rx=R(-2))
    pb(arm, "chest",    ry=R(-12), rx=R(-2))

    # Head: gaze leads the spin
    pb(arm, "neck", ry=R(-12))
    pb(arm, "head", ry=R(-15))

    # RIGHT arm: SWORD FULLY EXTENDED CENTRIFUGALLY outward
    # ry > 0 on R arm = outward/centrifugal; rx slightly negative = upward angle
    pb(arm, "shoulder.R",  rx=R(-8), rz=R(20))
    pb(arm, "upper_arm.R", rx=R(-88), ry=R(42), rz=R(0))
    pb(arm, "forearm.R",   rx=R(5))    # nearly straight — centrifugal extension
    pb(arm, "hand.R",      ry=R(18), rz=R(-30))

    # LEFT arm: drawn across body (centripetal) for balance
    pb(arm, "shoulder.L",  rx=R(6),  rz=R(-10))
    pb(arm, "upper_arm.L", rx=R(22), ry=R(-20), rz=R(10))
    pb(arm, "forearm.L",   rx=R(10))

    # Legs: planted right, left slightly lifted in spin
    pb(arm, "thigh.R",  rx=R(3),  rz=R(-6))
    pb(arm, "shin.R",   rx=R(-4))
    pb(arm, "thigh.L",  rx=R(-10), rz=R(5))
    pb(arm, "shin.L",   rx=R(15))

    bpy.context.view_layer.update()

    # Key from upper front-left — illuminates chest + pauldron
    shift_light("Light_Key",  (-2.5, -5.0, 7.5), (0, 0, 2.0), energy=620)
    shift_light("Light_Fill", (-1.5, -4.5, 1.5), (0, 0, 1.8), energy=60)
    # Strong rim from +X to rim-light the extended sword arm
    shift_light("Light_Rim",  ( 9.0,  0.5, 4.0), (0, 0, 2.0), energy=550)

    # Camera: front-center, slight right offset at chest height
    _set_camera("Cam_Moveset_07",
                location=(1.5, -8.6, 1.7),
                look_at=(0.3, 0.0, 1.9),
                lens=52)


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
    print("[06] Phase 6 — Moveset Pose Renders (7 poses, NATURAL PASS)")
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

    # Hide artifacts and extra lights for all moveset renders
    setup_moveset_scene()
    print("[06] Scene prepared: VoidCrack hidden, extra lights off")

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
            # Re-hide VoidCrack for next pose
            for name in _HIDE_FOR_MOVESET:
                obj = bpy.data.objects.get(name)
                if obj:
                    obj.hide_render = True
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
    print("[06] Phase 6 complete — natural poses rendered.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
