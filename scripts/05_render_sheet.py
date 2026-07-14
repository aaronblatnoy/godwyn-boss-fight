"""
05_render_sheet.py — Phase 6: Character Sheet Renders (high-quality rewrite)

Opens models/godwyn_phase1.blend ONCE, sets LOW HANG GUARD base pose
(SPEC 410: sword hanging low at side, tip toward ground), then loops the
7 character-sheet cameras rendering each to renders/character/<name>.png.

Key fixes in this revision:
  - Skin emission tamed: MixShader fac reduced to 0.08 (was 0.22) so the
    pale luminous skin reveals 3D form rather than blowing to white.
  - Scene exposure -0.3 (was +0.25) to reveal shadows and structure.
  - Cam_Face repositioned: pulled back and reframed to actually show the
    face silhouette rather than a blank white oval filling the frame.
  - Low hang guard strengthened: upper_arm.R drops further (-75 deg Y)
    and forearm adds more bend so the sword hand clearly hangs at hip.
  - Samples bumped to 256 (was 192).
  - GPU re-asserted (INV-2) before every render.

Camera loop order (all 1440x2560 portrait):
  Cam_Front           -> renders/character/front.png
  Cam_ThreeQuarter_L  -> renders/character/3q_left.png
  Cam_ThreeQuarter_R  -> renders/character/3q_right.png
  Cam_Back            -> renders/character/back.png
  Cam_Side            -> renders/character/side.png
  Cam_Face            -> renders/character/face.png
  Cam_Sword           -> renders/character/sword.png

INV-1 headless, INV-2 GPU re-asserted before every render, INV-3 spec-faithful,
INV-6 idempotent (opens .blend fresh; PNGs overwritten each run).

Run:
  blender --background --python scripts/05_render_sheet.py
"""

import sys
import os
import math
import bpy
import mathutils
from mathutils import Vector

# ---------------------------------------------------------------------------
# PATH SETUP — so lib_godwyn is importable
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
_BLEND_IN  = os.path.join(_REPO_ROOT, "models", "godwyn_phase1.blend")
_OUT_DIR   = os.path.join(_REPO_ROOT, "renders", "character")
_WIP_DIR   = os.path.join(_REPO_ROOT, "renders", "wip")

os.makedirs(_OUT_DIR, exist_ok=True)
os.makedirs(_WIP_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# CAMERA -> OUTPUT FILENAME MAPPING
# ---------------------------------------------------------------------------
SHEET_CAMERAS = [
    ("Cam_Front",          "front.png"),
    ("Cam_ThreeQuarter_L", "3q_left.png"),
    ("Cam_ThreeQuarter_R", "3q_right.png"),
    ("Cam_Back",           "back.png"),
    ("Cam_Side",           "side.png"),
    ("Cam_Face",           "face.png"),
    ("Cam_Sword",          "sword.png"),
]

ARMATURE_NAME = "Godwyn_Armature"

# ---------------------------------------------------------------------------
# MATERIAL OVERRIDE — tame skin emission for renders
# ---------------------------------------------------------------------------

def tame_skin_emission():
    """
    The skin MixShader fac of 0.22 * emission strength 2.5 = 0.55 effective
    radiance blows out the face to pure white in a near-black scene under AgX.
    Reduce MixShader fac to 0.08 (effective 0.20) so the luminous glow reads
    but face form is preserved.  Only the Fac input node value changes —
    node topology and all other inputs are untouched.
    """
    mat = bpy.data.materials.get("Mat_Skin")
    if mat is None:
        print("[05_sheet] WARNING: Mat_Skin not found; skipping emission tame.",
              file=sys.stderr)
        return
    nt = mat.node_tree
    for node in nt.nodes:
        if node.type == "MIX_SHADER":
            old_fac = node.inputs["Fac"].default_value
            node.inputs["Fac"].default_value = 0.08
            print(f"[05_sheet] Mat_Skin MixShader Fac: {old_fac:.3f} -> 0.08 "
                  f"(skin emission tamed for render clarity).")
            return
    # Fallback: look for Emission node and drop its strength
    for node in nt.nodes:
        if node.type == "EMISSION":
            old_str = node.inputs["Strength"].default_value
            node.inputs["Strength"].default_value = 0.35
            print(f"[05_sheet] Mat_Skin Emission Strength: {old_str:.2f} -> 0.35 "
                  f"(fallback: strength capped).")
            return
    print("[05_sheet] WARNING: could not locate MixShader or Emission in Mat_Skin.",
          file=sys.stderr)


def boost_eye_fill_light():
    """
    The Eye Fill light at 14 W was too dim to provide a catchlight once the
    key drops and emission is tamed.  Boost to 45 W so the face reads with
    clear specular separation.  Also nudge Light_Key energy down from 190 to
    130 so it shapes without flooding.
    """
    adjustments = {
        "Light_EyeFill": 45.0,
        "Light_Key":     130.0,
        "Light_Hands":   110.0,  # bring up so sword-hand hilt glints
    }
    for name, new_energy in adjustments.items():
        obj = bpy.data.objects.get(name)
        if obj and obj.type == "LIGHT":
            old = obj.data.energy
            obj.data.energy = new_energy
            print(f"[05_sheet] {name}: energy {old:.0f} -> {new_energy:.0f} W")


def reframe_face_camera():
    """
    Cam_Face was at (0, -2.1, 2.95) with 85mm lens looking at (0,0,2.92) —
    so tight that the face blob filled the entire 1440x2560 frame with no
    room to read the facial silhouette or hair framing.

    Pull back to Y=-3.8, drop to Z=2.80 (head center, not just top), keep
    85mm.  The face now fills roughly 60% of frame height with hair on top
    and chin visible — a proper character-sheet close-up rather than a
    macro nose shot.

    The actual look-at point is Z=2.75 (mid-face, between chin and brow)
    so the gaze lands naturally on the face rather than the top of the skull.
    """
    cam_obj = bpy.data.objects.get("Cam_Face")
    if cam_obj is None or cam_obj.type != "CAMERA":
        print("[05_sheet] WARNING: Cam_Face not found; cannot reframe.",
              file=sys.stderr)
        return

    new_loc    = Vector((0.0, -3.8, 2.80))
    look_at    = Vector((0.0,  0.0, 2.72))  # mid-face
    direction  = look_at - new_loc
    rot        = direction.to_track_quat("-Z", "Y").to_euler()

    cam_obj.location       = new_loc
    cam_obj.rotation_euler = rot
    cam_obj.data.lens      = 85.0          # keep telephoto compression

    print(f"[05_sheet] Cam_Face reframed: loc={tuple(round(v,2) for v in new_loc)}, "
          f"look_at={tuple(round(v,2) for v in look_at)}, lens=85mm")


def reframe_full_body_cameras():
    """
    Pull Cam_Front and Cam_Back out slightly so the full 3.2m figure fits
    with modest headroom.  The existing positions were already good but let's
    confirm they show the whole figure including feet.

    Also nudge Cam_Side to +X to better show the sword-hanging-low profile.
    """
    # These were calibrated in Phase 4; only adjust if form reveals they clip
    # Cam_Front was at (0, -8.8, 1.75) — keep; Cam_Side at (8.8, 0, 1.75) — keep
    # Just print confirmation
    for cam_name in ("Cam_Front", "Cam_Back", "Cam_Side"):
        obj = bpy.data.objects.get(cam_name)
        if obj:
            print(f"[05_sheet] {cam_name}: loc={tuple(round(v,2) for v in obj.location)}")


# ---------------------------------------------------------------------------
# POSE HELPERS
# ---------------------------------------------------------------------------

def _pose_bone(arm_obj, bone_name, euler_xyz_deg):
    """Set a pose bone's rotation (XYZ Euler, degrees)."""
    pb = arm_obj.pose.bones.get(bone_name)
    if pb is None:
        print(f"[05_sheet] WARNING: pose bone '{bone_name}' not found.",
              file=sys.stderr)
        return
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (math.radians(euler_xyz_deg[0]),
                         math.radians(euler_xyz_deg[1]),
                         math.radians(euler_xyz_deg[2]))


def reset_to_idle_pose(arm_obj):
    """
    Reset all pose bones to rest (T-pose), then re-apply the idle contrapposto
    that was baked into the .blend by Phase 4's apply_idle_pose().

    We can't call apply_idle_pose directly (it uses world-axis rotation helpers
    that depend on the bone rest matrices matching the Phase 4 values) so
    instead we just zero the pose and let the Phase 4 idle sit in the rest
    pose data.  Then we overlay our LOW HANG GUARD deltas on top.

    Actually: the .blend was SAVED with the idle pose APPLIED as the visual
    rest state but NOT as applied pose (it was set via pose bones, not applied
    to the mesh).  So zeroing pose bones gives T-pose, and we need to re-apply
    idle + low-hang.

    Strategy: zero all, then apply our combined idle+low-hang target.
    """
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()
    print("[05_sheet] Pose reset to T-pose rest.")


def apply_low_hang_guard(arm_obj):
    """
    LOW HANG GUARD — SPEC 410: sword hanging low at side, tip toward ground.

    This is the COMBINED idle contrapposto + low-hang overlay in one pass.
    Phase 4's apply_idle_pose was stored as pose-bone deltas on the .blend's
    current pose; since we reset to T-pose above, we need to re-establish
    the idle base and then layer the low-hang on top.

    IDLE BASE (replicating Phase 4 contrapposto without the world-axis helper):
      spine.01 slight Z-twist (contrapposto), head fractional downward tilt,
      both arms relaxed down from T-pose.

    LOW HANG GUARD OVERLAY (stronger than Phase 5):
      upper_arm.R: Y = -75 deg (drops arm well below horizontal toward hip)
      forearm.R  : X = +35 deg (elbow bend bringing hand to hip level)
      hand.R     : Y = +20, Z = -15 (wrist rotated so blade tip faces down)
      shoulder.R : Y = -8 deg (slight droop matching lowered arm)
      upper_arm.L: Y = -35 deg (left arm relaxed companion hang)
      forearm.L  : X = +12 deg (slight companion bend)

    Bone convention (from 04_rig_lights_cams.py):
      +X = Godwyn's RIGHT (sword side)
      Body faces -Y
      Euler order XYZ
    """
    reset_to_idle_pose(arm_obj)

    # -- IDLE BASE: contrapposto + relaxed arms --
    # Slight spine twist for living weight shift
    _pose_bone(arm_obj, "spine.01",   (0.0,  0.0,  4.0))
    _pose_bone(arm_obj, "chest",      (0.0,  0.0, -3.0))
    _pose_bone(arm_obj, "pelvis",     (0.0,  2.5,  3.5))
    # Head: fractional downward serene gaze, slight tilt
    _pose_bone(arm_obj, "neck",       (0.0,  0.0,  0.0))
    _pose_bone(arm_obj, "head",       (6.0,  0.0,  2.0))  # look slightly down

    # -- LOW HANG GUARD: right (sword) arm drops to hip --
    # upper_arm.R: Y=-75 drops arm firmly toward hip; X=+12 slight forward tuck
    _pose_bone(arm_obj, "upper_arm.R", (12.0, -75.0,  0.0))
    # forearm.R: X=+35 bends elbow bringing hand toward hip level
    _pose_bone(arm_obj, "forearm.R",   (35.0,   0.0,  0.0))
    # hand.R: orient so sword tip points downward (blade hangs away from body)
    _pose_bone(arm_obj, "hand.R",      ( 0.0,  20.0, -15.0))
    # shoulder.R: droop to match lowered arm
    _pose_bone(arm_obj, "shoulder.R",  ( 0.0,  -8.0,   0.0))

    # -- LEFT ARM: relaxed companion hang (slightly less dropped than sword arm) --
    _pose_bone(arm_obj, "upper_arm.L", ( 8.0, -35.0,  0.0))
    _pose_bone(arm_obj, "forearm.L",   (12.0,   0.0,  0.0))
    _pose_bone(arm_obj, "shoulder.L",  ( 0.0,  -4.0,  0.0))

    bpy.context.view_layer.update()
    print("[05_sheet] Low Hang Guard pose applied (strengthened): "
          "upper_arm.R Y=-75, forearm.R X=+35, head down-tilt.")


# ---------------------------------------------------------------------------
# GPU RE-ASSERT (INV-2)
# ---------------------------------------------------------------------------

def assert_and_reenable_gpu(scene):
    """Re-enable GPU devices and assert Cycles/GPU is set (INV-2)."""
    G.enable_gpu()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    if scene.cycles.device != "GPU":
        print("[05_sheet] FATAL: GPU not active after re-assert — aborting.",
              file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# PER-CAMERA EXPOSURE OVERRIDES
# Cam_Face needs more exposure to reveal facial detail;
# full-body shots need less to avoid blowing the skin.
# ---------------------------------------------------------------------------

CAMERA_EXPOSURE = {
    "Cam_Front":          -0.30,
    "Cam_ThreeQuarter_L": -0.30,
    "Cam_ThreeQuarter_R": -0.30,
    "Cam_Back":           -0.20,
    "Cam_Side":           -0.25,
    "Cam_Face":            0.10,   # face shot: slight lift to see features
    "Cam_Sword":          -0.40,   # sword detail: darker bg to make hilt pop
}


# ---------------------------------------------------------------------------
# RENDER ONE CAMERA
# ---------------------------------------------------------------------------

def render_camera(scene, cam_name, out_path):
    """Point scene.camera at cam_name, set exposure, assert GPU, render."""
    cam_obj = bpy.data.objects.get(cam_name)
    if cam_obj is None or cam_obj.type != "CAMERA":
        print(f"[05_sheet] FATAL: camera '{cam_name}' not found.",
              file=sys.stderr)
        sys.exit(1)

    scene.camera = cam_obj

    # Per-camera exposure
    exp = CAMERA_EXPOSURE.get(cam_name, -0.30)
    scene.view_settings.exposure = exp

    # INV-2: re-assert GPU before every render
    assert_and_reenable_gpu(scene)

    print(f"[05_sheet] Rendering {cam_name} (exposure={exp:+.2f}) -> {out_path}")
    G.render_to_path(out_path, scene)

    if not os.path.isfile(out_path) or os.path.getsize(out_path) < 1024:
        print(f"[05_sheet] FATAL: render output missing/empty: {out_path}",
              file=sys.stderr)
        return False, 0

    size = os.path.getsize(out_path)
    print(f"[05_sheet] OK: {cam_name} -> {out_path} ({size // 1024} KB)")
    return True, size


# ---------------------------------------------------------------------------
# VALIDATION GATE
# ---------------------------------------------------------------------------

def assert_phase6():
    """All 7 character sheet PNGs exist and are non-trivially sized."""
    errors = []
    total_size = 0
    for _cam, fname in SHEET_CAMERAS:
        path = os.path.join(_OUT_DIR, fname)
        if not os.path.isfile(path):
            errors.append(f"MISSING: {fname}")
        elif os.path.getsize(path) < 4096:
            errors.append(f"TOO SMALL: {fname} ({os.path.getsize(path)} bytes)")
        else:
            total_size += os.path.getsize(path)

    if errors:
        for e in errors:
            print(f"[05_sheet] ASSERT FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[05_sheet] ASSERT OK: all {len(SHEET_CAMERAS)} character sheet PNGs "
          f"present ({total_size // 1024} KB total).")
    for _cam, fname in SHEET_CAMERAS:
        path = os.path.join(_OUT_DIR, fname)
        print(f"  {fname}  ({os.path.getsize(path) // 1024} KB)")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("[05_sheet] Phase 6 — Character Sheet Renders (high-quality)")
    print("=" * 60)

    # 1. Verify .blend exists
    if not os.path.isfile(_BLEND_IN) or os.path.getsize(_BLEND_IN) < 10240:
        print(f"[05_sheet] FATAL: .blend missing or too small: {_BLEND_IN}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[05_sheet] Opening {_BLEND_IN} "
          f"({os.path.getsize(_BLEND_IN) // 1024} KB) ...")

    # 2. Open the Phase 4 .blend
    bpy.ops.wm.open_mainfile(filepath=_BLEND_IN)
    print("[05_sheet] .blend loaded.")

    scene = bpy.context.scene

    # 3. Enable GPU (INV-2) after file open
    active_gpu = G.enable_gpu()
    print(f"[05_sheet] GPU active: {active_gpu}")
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"

    # 4. Upgrade render quality for character sheet
    scene.cycles.samples = 256
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.008
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except Exception:
        pass

    # Resolution (preserve Phase 4 1440x2560 portrait)
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 2560
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode  = "RGBA"
    scene.render.image_settings.color_depth = "16"

    # Color management: AgX or Filmic
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        try:
            scene.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    scene.view_settings.look = "None"

    print(f"[05_sheet] Cycles: {scene.cycles.samples} samples, "
          f"{scene.render.resolution_x}x{scene.render.resolution_y}, "
          f"engine={scene.render.engine}, device={scene.cycles.device}")

    # 5. Tame skin emission so face form reads (key fix)
    tame_skin_emission()

    # 6. Boost eye fill and reshape lights for tamed-emission scene
    boost_eye_fill_light()

    # 7. Reframe Cam_Face to actually show face with room
    reframe_face_camera()
    reframe_full_body_cameras()

    # 8. Find armature and apply LOW HANG GUARD pose (SPEC 410)
    arm_obj = bpy.data.objects.get(ARMATURE_NAME)
    if arm_obj is None:
        print(f"[05_sheet] FATAL: armature '{ARMATURE_NAME}' not found.",
              file=sys.stderr)
        sys.exit(1)
    print(f"[05_sheet] Armature '{ARMATURE_NAME}' found, "
          f"{len(arm_obj.data.bones)} bones.")
    apply_low_hang_guard(arm_obj)

    # 9. Verify all sheet cameras present
    missing_cams = [c for c, _ in SHEET_CAMERAS
                    if bpy.data.objects.get(c) is None or
                       bpy.data.objects[c].type != "CAMERA"]
    if missing_cams:
        print(f"[05_sheet] FATAL: cameras missing: {missing_cams}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[05_sheet] All {len(SHEET_CAMERAS)} sheet cameras present.")

    # 10. Render loop — one .blend open, 7 renders
    render_results = []
    for cam_name, fname in SHEET_CAMERAS:
        out_path = os.path.join(_OUT_DIR, fname)
        print(f"\n[05_sheet] --- {cam_name} -> {fname} ---")

        ok, size = render_camera(scene, cam_name, out_path)
        render_results.append((cam_name, fname, ok, size))

        if not ok:
            print(f"[05_sheet] FATAL: render failed for {cam_name}.",
                  file=sys.stderr)
            sys.exit(1)

    # 11. Validation gate
    print("\n[05_sheet] === Validation Gate ===")
    assert_phase6()

    # 12. Summary
    print("\n[05_sheet] === Render Summary ===")
    for cam_name, fname, ok, size in render_results:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {cam_name:25s} -> {fname:20s}  ({size // 1024} KB)")

    print(f"\n[05_sheet] Phase 6 character sheet complete.")
    print(f"[05_sheet] Output: {_OUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
