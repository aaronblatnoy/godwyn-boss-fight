"""
anim_build_godwyn_xslash.py — PHASE 1 (build-critique loop): author Godwyn_XSlash.

Consolidated per-anim build script (named so multiple moves can coexist as
anim_build_<anim>.py). Extends the validated anim_xslash.py + anim_xslash_cape.py
pattern into ONE idempotent pass:

  1. Import models/godwyn_game.glb fresh (INV-3: factory-empty first = idempotent;
     rig + skin + baked materials untouched — INV-5).
  2. Re-seat Godwyn_Sword in the RightHand grip (glTF bone-parent tail bug);
     sword STAYS parented to RightHand (never re-parented).
  3. Keyframe the body: guard -> windup1 -> CUT 1 (\\, upper-right to lower-left)
     -> settle -> windup2 -> CUT 2 (/, upper-left to lower-right) -> recover.
     SPEC sec 7: crossing X in front, spin <= 1 rot/sec (max spine yaw sweep here
     is ~44deg over 9 frames = ~0.4 rot/sec), toes forward, combat grip, ~2s.
     Power from SPINE+SHOULDER rotation. pose_bone.keyframe_insert only
     (Blender 5.2 slotted actions — NO action.fcurves).
     R1 FIX (M2 ang-vel/jerk 360deg + elbow "315deg"): body bones are now
     authored in QUATERNION mode with hemisphere continuity between successive
     keys (q flipped to q.dot(prev)>=0). The old euler authoring let aim_hand's
     matrix->euler decomposition wrap +/-360deg between keys of the same world
     aim (each solve started from the previous mutated pose), so interpolation
     took the LONG way around — the genuine source of the M2 teleport/pop reads.
     Breakdown keys added mid guard->windup1 and cut1_settle->windup2 to smooth
     both swing onsets. Phys bake quats get the same per-bone hemisphere
     continuity.
     R2 FIX (round-2 fixBrief, metric-anchored): probed the exported WIP glb
     exactly as anim_metrics.py reads it (fresh import, default 24fps scene, so
     the 30fps clip is SAMPLED at 1/24s steps = 1.25x the authored per-frame
     travel). ONE genuine violation found: RightHand true (double-cover-FOLDED)
     ang-vel peaked 51.3deg/frame at the cut-2 launch (glb f33-f34, authored
     ~f42-43) — the 3-step launch was too hot once resampled. Fixed by
     RETIMING both cut launches to FIVE even slerp steps (hold->mid over 6
     frames instead of 4): authored peak ~27deg/frame, x1.25 sampling = ~34 <
     45. Self-check now asserts worst folded ang-vel < 36deg/frame @30fps
     (= <45 at the metric's 24fps sampling, since a 1/24s interval spans at
     most 1.25 authored frames). Cuts stay snappy: windup->impact 0.30s.
     EVERY OTHER round-2 M2 flag was verified (probe /tmp/probe_m2.py, w signs
     + folded angles logged) to be quaternion DOUBLE-COVER in the frozen
     metric's UNFOLDED reading, not motion: bones whose total world rotation
     hovers at ~180deg (w~0: shoulders, headfront, toe bases — structural for
     a -Y-facing rig; LeftToeBase w=0.0000 permanently) flip decomposition
     hemisphere while their TRUE folded motion at the flagged frames is
     0.0-33deg (e.g. glb f05 LeftToeBase reads 360.0 unfolded, 0.00 folded;
     RightForeArm "315deg" = 360-45 parent/child hemisphere split). These
     cannot be removed by ANY authoring while anim_metrics.py stays
     byte-identical (INV-9).
     R3 FIX (round-1 full-video VLM critique, 4 items):
     a) X legibility (blocker): camera moved dead-frontal, spine yaw sweeps
        widened (coil ~-70deg total -> uncoil ~+76deg) so the two diagonals
        span wider and unambiguously cross; NEW numeric self-check finds the
        actual 2D (camera-plane XZ) intersection of the two dense tip paths
        and asserts it exists, sits at mid-torso height, near the midline,
        and IN FRONT of the body (y < -0.15).
     b) spine/shoulder power (blocker): spine+hips yaw magnitudes ~doubled at
        every anchor, and launch in-betweens now give TORSO bones a timing
        LEAD (t*1.35 vs the arm's t) so the shoulders visibly lead the arm
        into each cut — whole-body uncoil, not an arm swing.
     c) over-right-shoulder wind-up (major): windup1 is now a HELD BEAT
        (f15-f18, ~0.13s) with the blade dir pulled further up-and-behind
        (-0.35, 0.42, 0.84) so the loaded position over the right shoulder
        reads; windup2 held f40-f43 symmetrically.
     d) forward step (minor): Hips bone now gets WORLD -Y (forward) location
        keys — 0 through windup1, creeping in cut1 (0.05-0.10m), committing
        through cut2 (0.32m at impact), kept in recover (0.28m, a NEW
        'recover' anchor so he does not slide back). Left leg swings/plants
        with bigger UpLeg/Leg deltas through cut2. Toes stay forward.
     Phys cape/robe/hair params UNTOUCHED this round (critic praised the cape;
     damped-spring verlet + both INV-6 guards stay as-is).
     R4 FIX (round-2 full-video VLM critique, 3 items):
     a) X geometry absent / reads as a vertical yo-yo (blocker): the strokes
        WERE diagonal in world numbers but too vertical ON SCREEN — the blade
        end directions were ~75deg from horizontal and the windup1 tip hid
        BEHIND the head. All D_ blade vectors re-planed for LATERAL amplitude:
        windup1 tip now clearly at his upper-RIGHT (x -0.60, only slightly
        behind), cut1 mid/end drive down-LEFT at ~40deg off vertical
        (x 0.70/0.58 vs old 0.62/0.36); cut2 mirrored down-RIGHT. NEW numeric
        self-check: each stroke's tip delta must satisfy |dx|/|dz| >= 0.55
        (>= ~29deg off vertical) so neither cut can read as a vertical drop.
     b) transition coil direction (blocker): the old cut1_settle->windup2 yaw
        was nearly static (+50 -> +70 summed) while the head counter-rotated
        RIGHT (-20) — the visible cue read as a rightward pivot. Now the
        torso coils VISIBLY LEFT into windup2 (summed yaw +50 -> +100), the
        LEFT shoulder pulls back (-14), and the head counter-rotation is
        halved (-10) so no body part sweeps rightward during the transition.
     c) torso rotation too small (major): spine/hips yaw scaled up ~35% at
        every anchor (coil -94deg summed -> uncoil +94 -> -85), shoulders lead
        harder. LEAD dropped 0.35 -> 0.25 so the bigger sweep still clears the
        M2 self-check gate (torso lead-step 0.25 x ~190deg launch sweep stays
        < 36deg/frame authored).
     R5 FIX (round-3 full-video VLM critique, 6 items):
     a) windup coil missing (blocker): NEW explicit 'windup1_rise' anchor at
        f10 — the blade now visibly sweeps UP along his right side (dir
        (-0.88, 0.05, 0.30), tip far right at ~ear height) before arriving
        loaded over the right shoulder at f14. NEW numeric self-checks: the
        tip must RISE >0.3m between f6 and f10 and again into f14, and the
        held windup tip (f15) must sit high (z>=2.6) and clearly on HIS
        RIGHT (x<=-0.5).
     b) torso pre-rotation (major): NEW 'windup*_prime' anchors replace the
        static second hold key (f18/f44) — TORSO+SHOULDER bones only are
        blended 25% toward the cut-mid pose while the arm+blade stay coiled,
        so the spine/shoulders are visibly ~15-20deg into the turn for 3-4
        frames BEFORE the blade accelerates (and each launch's torso travel
        SHRINKS, helping the M2 gate). Self-check asserts the summed torso
        yaw moves >=10deg toward each cut across the held beat.
     c) X crossing centered (major): assert tightened |x| < 0.9 -> < 0.55.
     d) cut1 \\ legibility (major): rise anchor puts the stroke start
        unambiguously RIGHT of center; stroke-diagonality + tip-delta checks
        retained.
     e) cape snap/bunch at the pivot (major): cape/robe damped-spring
        re-damped for drag inertia — stiffness 0.22/0.24 -> 0.16/0.19,
        damping 0.80/0.82 -> 0.86/0.85, gravity 3.5 -> 3.0/3.2, angular cap
        30 -> 36/34deg (the hard cap kicking in mid-pivot was the 'snap';
        a softer pull + higher cap lets the fabric trail through the pivot
        instead of being yanked to the rigid follow pose). STILL the same
        damped-spring verlet + BOTH INV-6 guards — NOT a cloth sim.
     f) forward step stronger (minor, low-conf): step offsets scaled up
        (commit 0.32 -> 0.42m at cut2 impact, kept 0.38 in recover) so the
        weight shift reads on camera.
  4. phys_ cape/robe/hair chains: deterministic verlet damped-spring bake that
     LAGS the body (inertia + damping + stiffness pull to the rigid follow
     shape + link-length constraints + ground clamp) with TWO explosion guards
     authored in FROM THE START (INV-6, pre-emptive):
       a) per-frame PARTICLE POSITION DELTA CLAMP (<= DELTA_CLAMP m/frame,
          under the M1 0.06*height threshold with margin), and
       b) per-bone angular deviation clamp vs the rigid follow pose.
     NEVER a full cloth sim.
  5. Name the action "Godwyn_XSlash", set scene frame range 1..64 @30fps,
     save models/godwyn_xslash_wip.blend, export models/godwyn_xslash_wip.glb
     (armature + skinned mesh + sword + baked materials + animation).
  6. Self-check renders (EEVEE): guard/windup1/cut1/windup2/cut2/recover,
     front + back cams, to /tmp/godwyn_xslash_build/.

Run (server):
  blender --background --python ~/godwyn-boss-fight/scripts/anim_build_godwyn_xslash.py 2>&1
"""
import bpy, os, math
from mathutils import Euler, Vector, Matrix, Quaternion

REPO      = os.path.expanduser("~/godwyn-boss-fight")
GLB_IN    = os.path.join(REPO, "models", "godwyn_game.glb")
BLEND_OUT = os.path.join(REPO, "models", "godwyn_xslash_wip.blend")
GLB_OUT   = os.path.join(REPO, "models", "godwyn_xslash_wip.glb")
OUTDIR    = "/tmp/godwyn_xslash_build"
os.makedirs(OUTDIR, exist_ok=True)

ACTION_NAME = "Godwyn_XSlash"
FPS         = 30
FRAME_END   = 64          # ~2.1s
CHAR_HEIGHT = 3.2         # SPEC: Godwyn is 3.2m
# INV-6 pre-emptive guard: M1 fails at per-frame vert delta > 0.06*height
# (= 0.192m). Clamp every sim particle's per-frame travel well under that.
DELTA_CLAMP = 0.15        # m per frame, hard cap on phys particle travel

# ── Clear & import (idempotent: factory-empty first) ─────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_IN)

arm   = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sword = bpy.data.objects.get("Godwyn_Sword")
assert sword is not None, "FATAL: Godwyn_Sword missing"
assert sword.parent_bone == "RightHand", f"FATAL: sword parent_bone={sword.parent_bone}"
print(f"[build] armature={arm.name} bones={len(arm.pose.bones)} "
      f"sword.parent_bone={sword.parent_bone}")

# ── Re-seat the sword in the grip (proven fix from anim_xslash.py) ──────────
# glTF import bone-parents the sword at the RightHand bone's guessed tail
# (~49m off). Solve its world matrix at REST so the grip end sits at the hand,
# blade hanging DOWN. Sword remains bone-parented to RightHand (INV: no re-parent).
bpy.context.view_layer.update()
_bb   = [Vector(c) for c in sword.bound_box]
_zmin = min(c.z for c in _bb)
_zmax = max(c.z for c in _bb)
_cx   = sum(c.x for c in _bb) / 8.0
_cy   = sum(c.y for c in _bb) / 8.0
GRIP_LOCAL = Vector((_cx, _cy, _zmin))
TIP_LOCAL  = Vector((_cx, _cy, _zmax))
hand_rest_w = arm.matrix_world @ arm.pose.bones["RightHand"].head
_R = Matrix.Rotation(math.radians(180), 4, 'X')
_S = Matrix.Diagonal((0.01, 0.01, 0.01, 1.0))
sword.matrix_world = (Matrix.Translation(hand_rest_w) @ _R @ _S
                      @ Matrix.Translation(-GRIP_LOCAL))
bpy.context.view_layer.update()
print(f"[build] sword re-seated at {tuple(round(v, 2) for v in hand_rest_w)}, "
      f"blade {(_zmax - _zmin) * 0.01:.2f}m")

# ── Scene setup ──────────────────────────────────────────────────────────────
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, FRAME_END

def _delete_if(name):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)

for n in ("XS_Ground", "XS_Sun", "XS_Fill", "XS_Cam", "XS_BackCam"):
    _delete_if(n)          # INV-3 delete-by-name before recreate

bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "XS_Ground"
gmat = bpy.data.materials.new("XS_Ground")
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.11, 0.10, 1)
ground.data.materials.append(gmat)

bpy.ops.object.light_add(type='SUN', location=(4, -6, 10))
sun = bpy.context.active_object
sun.name = "XS_Sun"
sun.data.energy = 6.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(30)), 'XYZ')
bpy.ops.object.light_add(type='AREA', location=(-3, -5, 4))
fill = bpy.context.active_object
fill.name = "XS_Fill"
fill.data.energy = 300
fill.data.size = 4

# R3: DEAD-FRONTAL cam (he faces -Y) so the X crossing is unambiguous on
# screen (round-1 critic: crossing not legible from the oblique angle);
# plus a back cam for cape.
bpy.ops.object.camera_add(location=(0.35, -8.2, 1.9))
cam = bpy.context.active_object
cam.name = "XS_Cam"
tgt = Vector((0.0, -0.3, 1.7))
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
bpy.ops.object.camera_add(location=(-3.0, 6.4, 2.3))
back_cam = bpy.context.active_object
back_cam.name = "XS_BackCam"
tgt = Vector((0.0, 0.0, 1.5))
back_cam.rotation_euler = (tgt - back_cam.location).to_track_quat('-Z', 'Y').to_euler()

# ── Body keyframing (pose tables validated through fixer rounds r1-r2c) ─────
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

CTRL = ["RightShoulder", "RightArm", "RightForeArm", "RightHand",
        "LeftShoulder", "LeftArm", "LeftForeArm",
        "Spine", "Spine01", "Spine02", "Hips", "Head",
        "LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg"]
for n in CTRL:
    pb = arm.pose.bones.get(n)
    assert pb is not None, f"FATAL: missing body bone {n}"
    # R1 FIX: quaternion authoring — euler decomposition of aim_hand's matrix
    # solve wrapped +/-360deg between keys, making interpolation spin the long
    # way (M2 ang-vel/jerk 360deg/frame). Quaternions + hemisphere continuity
    # interpolate the SHORT path by construction.
    pb.rotation_mode = 'QUATERNION'

def aim_hand(blade_dir):
    """Rotate RightHand so its Y axis (blade dir after re-seat) points at the
    given WORLD direction. Deterministic — no euler sign guessing."""
    bpy.context.view_layer.update()
    pb = arm.pose.bones["RightHand"]
    M = arm.matrix_world @ pb.matrix
    y_now = Vector((M[0][1], M[1][1], M[2][1])).normalized()
    q = y_now.rotation_difference(Vector(blade_dir).normalized())
    R = q.to_matrix().to_4x4()
    T = Matrix.Translation(M.translation)
    pb.matrix = arm.matrix_world.inverted() @ (T @ R @ T.inverted() @ M)
    bpy.context.view_layer.update()

def _pose_quat(pose, n):
    rx, ry, rz = pose.get(n, (0, 0, 0))
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)),
                 'XYZ').to_quaternion()

PREV_Q = {}                              # R1 FIX: hemisphere continuity per bone

# R3 (fix d): convert a WORLD forward offset (meters, -Y) into Hips bone-local
# location units once — (AW @ rest).to_3x3() carries armature+rest scale/orient.
_HIPS_L3 = (arm.matrix_world @ arm.pose.bones["Hips"].bone.matrix_local).to_3x3()
HIPS_FWD_LOCAL = _HIPS_L3.inverted() @ Vector((0.0, -1.0, 0.0))

def key_pose(frame, pose, hand_quat, step=0.0):
    """Key all CTRL bones from a pose table, with the RightHand local quat
    given EXPLICITLY (pre-solved per anchor, slerped for in-betweens — R1 FIX:
    per-key aim_hand re-solves carried inconsistent blade-axis twist, which
    dense keys baked in as jitter). step = world-forward Hips offset (m)."""
    for n in CTRL:
        arm.pose.bones[n].rotation_quaternion = _pose_quat(pose, n)
    arm.pose.bones["RightHand"].rotation_quaternion = hand_quat.normalized()
    for n in CTRL:
        pb = arm.pose.bones[n]
        q = pb.rotation_quaternion.copy().normalized()
        pq = PREV_Q.get(n)
        if pq is not None and q.dot(pq) < 0.0:
            q = -q                       # same rotation, short-path hemisphere
        pb.rotation_quaternion = q
        PREV_Q[n] = q.copy()
        pb.keyframe_insert(data_path='rotation_quaternion', frame=frame)
    hips = arm.pose.bones["Hips"]
    hips.location = HIPS_FWD_LOCAL * step
    hips.keyframe_insert(data_path='location', frame=frame)

# R3: torso bones can LEAD the arm through a blend — shoulders/spine arrive
# ahead of the hand so each cut reads as a whole-body uncoil (blocker fix b).
TORSO_LEAD = {"Spine", "Spine01", "Spine02", "Hips", "Head"}

def blend_pose(pa, pb_, t, lead=0.0):
    """Slerp-blend two pose tables (per-bone short-path) -> new pose table.
    lead > 0 advances TORSO_LEAD bones (t*(1+lead), capped 1) vs the arm."""
    out = {}
    for n in CTRL:
        tt = min(1.0, t * (1.0 + lead)) if (lead and n in TORSO_LEAD) else t
        qa, qb = _pose_quat(pa, n), _pose_quat(pb_, n)
        if qa.dot(qb) < 0.0:
            qb = -qb
        e = qa.slerp(qb, tt).to_euler('XYZ')
        out[n] = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
    return out

def blend_dir(a, b, t):
    v = Vector(a).normalized().lerp(Vector(b).normalized(), t)
    return tuple(v.normalized())

# R5 (fix b): torso/shoulder PRE-ROTATION set — these bones get blended toward
# the cut during the held windup beat while the arm+blade stay coiled.
PRELEAD = TORSO_LEAD | {"RightShoulder", "LeftShoulder"}

def torso_blend(pa, pb_, t):
    """Blend ONLY PRELEAD (spine/hips/head/shoulders) t of the way pa->pb_;
    the sword arm and legs stay at pa. R5 fix b: the power source (spine +
    shoulder) is visibly into its turn BEFORE the blade moves at speed."""
    out = dict(pa)
    for n in CTRL:
        if n not in PRELEAD:
            continue
        qa, qb = _pose_quat(pa, n), _pose_quat(pb_, n)
        if qa.dot(qb) < 0.0:
            qb = -qb
        e = qa.slerp(qb, t).to_euler('XYZ')
        out[n] = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
    return out

# POSES (degrees, XYZ). World: faces -Y; HIS right = -X, HIS left = +X.
# Toes forward: no UpLeg yaw anywhere (SPEC sec 7 — no splay).
GUARD = {
    "RightShoulder": (0, 0, -4),
    "RightArm":      (15, 0, -18),
    "RightForeArm":  (-32, 10, 0),
    "LeftShoulder":  (0, 0, 5),
    "LeftArm":       (22, 0, 12),
    "LeftForeArm":   (-18, 0, 0),
    "Spine":         (4, 0, 0),
    "Spine01":       (3, 0, 0),
    "Head":          (-4, 0, 0),
}
WINDUP1 = {                              # coiled over HIS RIGHT shoulder
    "RightShoulder": (0, 0, -20),
    "RightArm":      (-74, 0, -72),
    "RightForeArm":  (-30, 30, 0),
    "LeftShoulder":  (0, 0, 6),
    "LeftArm":       (30, 0, 18),
    "LeftForeArm":   (-25, 0, 0),
    # R4: spine coil scaled up again — round-2 critic still read the torso as
    # "relatively stable"; the coil must be unmistakable at spine/hip level
    "Spine":         (0, 4, -38),
    "Spine01":       (0, 0, -24),
    "Spine02":       (-4, 0, -16),
    "Hips":          (0, 0, -16),
    "Head":          (0, 0, 22),         # counter-rotate: eyes stay on target
    "RightUpLeg":    (6, 0, 0),
}
CUT1_MID = {
    "RightShoulder": (0, 0, -4),
    "RightArm":      (-45, 0, -10),
    "RightForeArm":  (-5, 10, 0),
    "LeftArm":       (24, 0, 14),
    "LeftForeArm":   (-20, 0, 0),
    # R4: torso already well into the uncoil at mid-cut (leads the arm, and
    # keeps the mid->end world ang-vel under the M2 gate); magnitudes up ~40%
    "Spine":         (6, 0, 22),
    "Spine01":       (4, 0, 13),
    "Spine02":       (0, 0, 8),
    "Hips":          (0, 0, 9),
    "Head":          (-4, 0, -2),
    "LeftUpLeg":     (-14, 0, 0),        # small forward step with the cut
    "LeftLeg":       (10, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
CUT1_END = {                             # hip height across at HIS LEFT (\ done)
    "RightShoulder": (0, 0, 18),
    "RightArm":      (5, 0, -38),
    "RightForeArm":  (-5, 0, 0),
    "LeftShoulder":  (0, 0, -4),
    "LeftArm":       (14, 0, 8),
    "LeftForeArm":   (-12, 0, 0),
    "Spine":         (2, 0, 40),         # R4: rotation carried THROUGH the cut
    "Spine01":       (3, 0, 24),
    "Spine02":       (2, 0, 14),
    "Hips":          (0, 0, 16),
    "Head":          (-8, 0, -8),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (12, 0, 0),
    "RightUpLeg":    (10, 0, 0),
}
CUT1_SETTLE = {
    "RightShoulder": (0, 0, 14),
    "RightArm":      (5, 0, -34),
    "RightForeArm":  (-10, 0, 0),
    "LeftArm":       (16, 0, 10),
    "LeftForeArm":   (-14, 0, 0),
    "Spine":         (2, 0, 33),
    "Spine01":       (3, 0, 20),
    "Spine02":       (1, 0, 11),
    "Hips":          (0, 0, 12),
    "Head":          (-7, 0, -6),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (10, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
WINDUP2 = {                              # hand HIGH, blade up-left, lateral coil
    "RightShoulder": (0, 0, 18),
    "RightArm":      (-80, -40, 0),      # R4: hair less extreme — trims the
                                         # hot cut2 launch arm travel ~7deg
    "RightForeArm":  (-25, -15, 0),
    # R4 (blocker b): the transition must READ as a LEFTWARD coil — left
    # shoulder pulls BACK, torso yaw keeps sweeping left (+50 -> +100 summed,
    # was nearly static), head counter-rotation halved so nothing pivots right
    "LeftShoulder":  (0, 0, -14),
    "LeftArm":       (26, 0, 16),
    "LeftForeArm":   (-22, 0, 0),
    "Spine":         (0, -4, 46),
    "Spine01":       (0, 0, 24),
    "Spine02":       (-4, 0, 14),
    "Hips":          (0, 0, 16),
    "Head":          (0, 0, -10),
    "LeftUpLeg":     (-20, 0, 0),
    "LeftLeg":       (18, 0, 0),
    "RightUpLeg":    (7, 0, 0),
}
CUT2_MID = {
    "RightShoulder": (0, 0, 2),
    "RightArm":      (-45, 0, 10),
    "RightForeArm":  (-5, -10, 0),
    "LeftArm":       (22, 0, 12),
    "LeftForeArm":   (-18, 0, 0),
    # R4: torso already into the opposite uncoil at mid-cut (same reasoning)
    "Spine":         (6, 0, -20),
    "Spine01":       (4, 0, -12),
    "Spine02":       (0, 0, -7),
    "Hips":          (0, 0, -8),
    "Head":          (-4, 0, 4),
    "LeftUpLeg":     (-24, 0, 0),        # R3: left leg swinging forward w/ cut
    "LeftLeg":       (22, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
CUT2_END = {                             # hip height out at HIS RIGHT (/ done)
    "RightShoulder": (0, 0, -20),
    "RightArm":      (8, 0, -24),
    "RightForeArm":  (-20, 10, 0),
    "LeftShoulder":  (0, 0, 8),
    "LeftArm":       (20, 0, 14),
    "LeftForeArm":   (-16, 0, 0),
    "Spine":         (10, 0, -36),
    "Spine01":       (6, 0, -22),
    "Spine02":       (4, 0, -13),
    "Hips":          (4, 0, -14),
    "Head":          (2, 0, 10),
    "LeftUpLeg":     (-22, 0, 0),        # R3: lead foot PLANTED forward
    "LeftLeg":       (8, 0, 0),
    "RightUpLeg":    (14, 0, 0),         # trailing leg extends behind
    "RightLeg":      (6, 0, 0),
}
CUT2_SETTLE = {
    "RightShoulder": (0, 0, -16),
    "RightArm":      (8, 0, -22),
    "RightForeArm":  (-20, 8, 0),
    "LeftArm":       (21, 0, 13),
    "LeftForeArm":   (-17, 0, 0),
    "Spine":         (8, 0, -27),
    "Spine01":       (5, 0, -16),
    "Spine02":       (2, 0, -9),
    "Hips":          (3, 0, -10),
    "Head":          (0, 0, 8),
    "LeftUpLeg":     (-20, 0, 0),
    "LeftLeg":       (8, 0, 0),
    "RightUpLeg":    (12, 0, 0),
    "RightLeg":      (5, 0, 0),
}

# WORLD blade directions per key (validated: X crosses in FRONT, strokes full)
# R4 (blocker a): round-2 full-video critic read the strokes as a VERTICAL
# yo-yo — the old end dirs were ~75deg from horizontal and the windup1 tip hid
# BEHIND the head (y +0.42). Re-planed for LATERAL on-screen amplitude: the
# windup1 tip sits clearly at his upper-RIGHT (x -0.60, barely behind), and
# both cuts drive ~40deg off vertical (end |x| 0.58 vs old 0.36) so each
# diagonal is unmistakable from the frontal cam. Cut2 mirrors cut1.
D_GUARD   = (-0.20, -0.55, -0.81)
# R5 (fix a): explicit RISE direction — the blade sweeps up along HIS RIGHT
# side (tip far right, near-level) on the way to the over-shoulder coil, so
# the upward coil is unmistakable instead of a low-static start.
D_RISE1   = (-0.88,  0.05,  0.30)
D_WINDUP1 = (-0.60,  0.18,  0.78)
# R4: crossing-point geometry (measured over 3 probe runs): raising cut1's
# line moves the X crossing toward HIS LEFT (+x); raising cut2's line moves
# it toward the midline and UP. So cut1 mid descends moderately (z -0.42)
# while cut2 mid sweeps nearly LEVEL (z -0.18) through the centerline.
D_CUT1MID = ( 0.72, -0.48, -0.42)
D_CUT1END = ( 0.58, -0.30, -0.76)
D_CUT1SET = ( 0.56, -0.30, -0.77)
D_WINDUP2 = ( 0.60,  0.18,  0.78)
D_CUT2MID = (-0.80, -0.42, -0.18)
D_CUT2END = (-0.58, -0.30, -0.76)
D_CUT2SET = (-0.56, -0.30, -0.77)

# ── R1 FIX: pre-solve the RightHand aim ONCE per anchor pose ────────────────
# aim_hand is deterministic per (pose, dir) but its minimal-rotation solve
# carries arbitrary twist about the blade axis; solving per-key made twist
# jump between adjacent dense keys (measured 67.8deg/frame). Instead: solve
# each ANCHOR once, then SLERP the hand local quat for in-between keys —
# per-frame velocity is total-angle/nframes by construction.
# R5: derived anchor poses.
# windup1_rise — mid guard->windup1 body, blade sweeping up the right side.
RISE1_POSE  = blend_pose(GUARD, WINDUP1, 0.55)
# windup*_prime — held-coil body but TORSO+SHOULDERS 25% into the cut (fix b).
PRIME1_POSE = torso_blend(WINDUP1, CUT1_MID, 0.25)
PRIME2_POSE = torso_blend(WINDUP2, CUT2_MID, 0.25)
# hold anchors pre-rotate the blade toward the cut (anticipation).
# R4: 0.22 / 0.32 — the re-planed dirs sweep a wider arc, so the held blade
# starts further into it to keep each launch under the M2 gate.
HOLD1_DIR = blend_dir(D_WINDUP1, D_CUT1MID, 0.22)
HOLD2_DIR = blend_dir(D_WINDUP2, D_CUT2MID, 0.32)
ANCHORS = [
    ("guard",         GUARD,       D_GUARD),
    ("windup1_rise",  RISE1_POSE,  D_RISE1),      # R5 fix a: visible up-coil
    ("windup1",       WINDUP1,     D_WINDUP1),
    ("windup1_hold",  WINDUP1,     HOLD1_DIR),
    ("windup1_prime", PRIME1_POSE, HOLD1_DIR),    # R5 fix b: torso pre-rot
    ("cut1_mid",      CUT1_MID,    D_CUT1MID),
    ("cut1_end",      CUT1_END,    D_CUT1END),
    ("cut1_settle",   CUT1_SETTLE, D_CUT1SET),
    ("windup2",       WINDUP2,     D_WINDUP2),
    ("windup2_hold",  WINDUP2,     HOLD2_DIR),
    ("windup2_prime", PRIME2_POSE, HOLD2_DIR),    # R5 fix b: torso pre-rot
    ("cut2_mid",      CUT2_MID,    D_CUT2MID),
    ("cut2_end",      CUT2_END,    D_CUT2END),
    ("cut2_settle",   CUT2_SETTLE, D_CUT2SET),
    # R3: distinct recover anchor = guard pose but KEEPING the forward step
    # (weight stays committed; he must not slide back to the origin).
    ("recover",       GUARD,       D_GUARD),
]
# R3 (fix d) + R5 (fix f, scaled up ~30%): small forward step — WORLD forward
# (-Y) Hips offset in meters per anchor. Creeps in with cut 1, COMMITS as
# cut 2 lands (0.42m), kept in recover. A step, not a lunge; toes forward.
STEP_OF = {
    "guard": 0.0, "windup1_rise": 0.0, "windup1": 0.0,
    "windup1_hold": 0.0, "windup1_prime": 0.02,
    "cut1_mid": 0.10, "cut1_end": 0.16, "cut1_settle": 0.16,
    "windup2": 0.18, "windup2_hold": 0.18, "windup2_prime": 0.18,
    "cut2_mid": 0.30, "cut2_end": 0.42, "cut2_settle": 0.42,
    "recover": 0.38,
}
POSE_OF, HANDQ = {}, {}
_hq_prev = None
for _label, _pose, _dir in ANCHORS:
    POSE_OF[_label] = _pose
    for n in CTRL:
        arm.pose.bones[n].rotation_quaternion = _pose_quat(_pose, n)
    bpy.context.view_layer.update()
    aim_hand(_dir)
    _q = arm.pose.bones["RightHand"].rotation_quaternion.copy().normalized()
    if _hq_prev is not None and _q.dot(_hq_prev) < 0.0:
        _q = -_q                         # hemisphere continuity between anchors
    HANDQ[_label] = _q
    _hq_prev = _q.copy()
print(f"[build] pre-solved hand aim for {len(HANDQ)} anchors")

def hand_slerp(a, b, t):
    qa, qb = HANDQ[a].copy(), HANDQ[b].copy()
    if qa.dot(qb) < 0.0:
        qb = -qb
    return qa.slerp(qb, t)

# TIMELINE entries: (frame, labelA, labelB_or_None, t, printlabel).
# t=0 -> pure anchor labelA. t>0 -> slerp/blend labelA->labelB.
# R1: breakdown keys (guard->windup1, cut1_settle->windup2) smooth both onsets.
# R2 FIX (metric-anchored): each cut launch is now FIVE even slerp steps
# (hold -> mid over 6 frames, was 4). The metric samples the exported glb at
# 24fps (1.25x the authored 30fps per-frame travel); the old 3-step launch
# peaked 51.3deg/frame folded at that sampling (> the 45 gate). Five steps
# put the authored peak at ~27deg/frame -> ~34 at 24fps sampling. Each cut
# is still windup->impact in 0.30s (snappy per SPEC sec 7).
# R3: windup1/windup2 are now HELD BEATS (double-keyed, ~0.13s) so the loaded
# over-shoulder positions read (major fix c); launch in-betweens carry a
# torso LEAD so the shoulders arrive ahead of the arm (blocker fix b).
# R4: LEAD 0.35 -> 0.15 — the yaw sweep grew ~35% (fix c), so the per-frame
# torso lead-step must shrink to keep the summed-chain world ang-vel under
# the 36deg/frame authored gate (measured ladder: LEAD 0.25 -> 39.1, 0.22 ->
# 36.3-36.5, all peaking RightHand@f49). The shoulder lead now reads mostly
# from the ~35% bigger anchor yaws, not the in-between offset.
# Entries: (frame, labelA, labelB_or_None, t, printlabel, lead).
LEAD = 0.15
# R4: each launch RETIMED to SEVEN even slerp steps (held -> mid over 7
# frames, was 6) — the wider R4 arcs peaked 38-39deg/frame on the 6-step
# launch (RightHand@f47) regardless of hold pre-rotation, because the ARM
# POSE travel dominates the hand's world rotation. One extra frame per
# launch cuts the per-frame step ~14%. Downstream keys shift +1/+2; each
# cut is still held->impact in 0.37s (snappy per SPEC sec 7).
# R5: f10 is now the EXPLICIT rise anchor (fix a — visible up-coil along his
# right side); the second held key (f18/f44) is the PRIME anchor (fix b —
# torso/shoulders 25% into the turn, blade still coiled), and each launch
# slerps from the PRIME pose so torso launch travel shrinks.
TIMELINE = [
    (1,  "guard",         None,           0.00, "guard",          0.0),
    (6,  "guard",         None,           0.00, "guard_hold",     0.0),
    (10, "windup1_rise",  None,           0.00, "windup1_rise",   0.0),
    (14, "windup1",       None,           0.00, "windup1",        0.0),
    (15, "windup1_hold",  None,           0.00, "windup1_hold",   0.0),
    (18, "windup1_prime", None,           0.00, "windup1_prime",  0.0),
    (19, "windup1_prime", "cut1_mid",     1/7., "cut1_launch_a",  LEAD),
    (20, "windup1_prime", "cut1_mid",     2/7., "cut1_launch_b",  LEAD),
    (21, "windup1_prime", "cut1_mid",     3/7., "cut1_launch",    LEAD),
    (22, "windup1_prime", "cut1_mid",     4/7., "cut1_launch_c",  LEAD),
    (23, "windup1_prime", "cut1_mid",     5/7., "cut1_launch_d",  LEAD),
    (24, "windup1_prime", "cut1_mid",     6/7., "cut1_launch_e",  LEAD),
    (25, "cut1_mid",      None,           0.00, "cut1_mid",       0.0),
    (29, "cut1_end",      None,           0.00, "cut1_end",       0.0),
    (32, "cut1_settle",   None,           0.00, "cut1_settle",    0.0),
    (36, "cut1_settle",   "windup2",      0.50, "windup2_break",  0.0),
    (40, "windup2",       None,           0.00, "windup2",        0.0),
    (41, "windup2_hold",  None,           0.00, "windup2_hold",   0.0),
    (44, "windup2_prime", None,           0.00, "windup2_prime",  0.0),
    (45, "windup2_prime", "cut2_mid",     1/7., "cut2_launch_a",  LEAD),
    (46, "windup2_prime", "cut2_mid",     2/7., "cut2_launch_b",  LEAD),
    (47, "windup2_prime", "cut2_mid",     3/7., "cut2_launch",    LEAD),
    (48, "windup2_prime", "cut2_mid",     4/7., "cut2_launch_c",  LEAD),
    (49, "windup2_prime", "cut2_mid",     5/7., "cut2_launch_d",  LEAD),
    (50, "windup2_prime", "cut2_mid",     6/7., "cut2_launch_e",  LEAD),
    (51, "cut2_mid",      None,           0.00, "cut2_mid",       0.0),
    (55, "cut2_end",      None,           0.00, "cut2_end",       0.0),
    (59, "cut2_settle",   None,           0.00, "cut2_settle",    0.0),
    (64, "recover",       None,           0.00, "recover",        0.0),
]
for frame, la, lb, t, label, lead in TIMELINE:
    if lb is None or t == 0.0:
        pose, hq, step = POSE_OF[la], HANDQ[la], STEP_OF[la]
    else:
        pose = blend_pose(POSE_OF[la], POSE_OF[lb], t, lead=lead)
        hq = hand_slerp(la, lb, t)
        step = STEP_OF[la] * (1.0 - t) + STEP_OF[lb] * t
    key_pose(frame, pose, hq, step=step)
    print(f"[build] keyed f{frame:02d} {label} step={step:.2f}")
bpy.ops.object.mode_set(mode='OBJECT')

# ── phys_ chains: damped-spring verlet bake with pre-emptive INV-6 guards ───
AW, AWI = arm.matrix_world.copy(), arm.matrix_world.inverted()
chains = []
for pb in arm.pose.bones:
    if pb.name.startswith("phys_") and not pb.parent.name.startswith("phys_"):
        chain = [pb]
        while chain[-1].children:
            nxt = [c for c in chain[-1].children if c.name.startswith("phys_")]
            if not nxt:
                break
            chain.append(nxt[0])
        chains.append(chain)
n_phys = sum(len(c) for c in chains)
print(f"[build] phys chains={len(chains)} bones={n_phys}")
assert n_phys == 97, f"FATAL: expected 97 phys bones, chained {n_phys}"

def params(name):
    """(stiffness pull to rigid, damping, gravity scale, max deviation deg)
    R5 (fix e): round-3 critic saw the cape BUNCH + SNAP at the cut1->cut2
    pivot. Root cause: a stiff pull to the rigid follow pose + the 30deg
    angular cap saturating mid-pivot, then releasing — a yank, not a trail.
    Re-damped for drag inertia: LOWER stiffness (fabric lags the pivot and
    keeps trailing the cut-1 direction), HIGHER damping (velocity bleeds off
    instead of springing back), slightly wider angular cap (the hard clamp
    engages later/softer). Same damped-spring verlet, same two INV-6 guards
    (delta clamp + angular cap) — still NEVER a cloth sim."""
    if "hair" in name:  return (0.30, 0.84, 1.5, 40.0)
    if "robe" in name:  return (0.19, 0.85, 3.2, 34.0)
    return (0.16, 0.86, 3.0, 36.0)      # cape: soft pull, high drag, trails

def chain_phase(name):
    """Slight per-column temporal offset so cape columns break up."""
    if "cape" not in name: return 0.0
    if "_C_" in name:      return 0.4
    if "_R_" in name:      return 0.8
    return 0.0

OFF, VSTEP = {}, {}
for ch in chains:
    for pb in ch:
        OFF[pb.name] = pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
for ch in chains:
    for i, pb in enumerate(ch):
        if i + 1 < len(ch):
            VSTEP[pb.name] = OFF[ch[i + 1].name].translation.copy()
        else:
            o = OFF[pb.name]
            VSTEP[pb.name] = o.to_3x3().inverted() @ o.translation

anchors = sorted({ch[0].parent.name for ch in chains})
anchor_mats = {}
for f in range(1, FRAME_END + 1):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    for a in anchors:
        anchor_mats[(f, a)] = arm.pose.bones[a].matrix.copy()

def rigid_joints(ch, f):
    M = anchor_mats[(f, ch[0].parent.name)].copy()
    joints, W = [], None
    for pb in ch:
        M = M @ OFF[pb.name]
        W = AW @ M
        joints.append(W.translation.copy())
    joints.append(W @ VSTEP[ch[-1].name])
    return joints

DT2 = (1.0 / FPS) ** 2
sim = {}
max_particle_delta = 0.0                 # observed AFTER clamping (report)
for ci, ch in enumerate(chains):
    stiff, damp, gscale, _ = params(ch[0].name)
    rest = rigid_joints(ch, 1)
    lens = [(rest[i + 1] - rest[i]).length for i in range(len(rest) - 1)]
    P  = [v.copy() for v in rest]
    Pp = [v.copy() for v in rest]
    ph = chain_phase(ch[0].name)
    for f in range(1, FRAME_END + 1):
        if ph > 0.0 and f > 1:
            ta, tb = rigid_joints(ch, f - 1), rigid_joints(ch, f)
            tgt = [a * ph + b * (1.0 - ph) for a, b in zip(ta, tb)]
        else:
            tgt = rigid_joints(ch, f)
        prev = [v.copy() for v in P]     # last frame's final positions
        P[0] = tgt[0].copy()             # root pinned to animated anchor
        for i in range(1, len(P)):
            vel = (P[i] - Pp[i]) * damp
            new = (P[i] + vel + Vector((0, 0, -9.8 * gscale)) * DT2
                   + (tgt[i] - P[i]) * stiff)
            Pp[i] = P[i].copy()
            P[i] = new
        for _ in range(3):               # link-length constraints, root outward
            for i in range(1, len(P)):
                d = P[i] - P[i - 1]
                if d.length > 1e-9:
                    P[i] = P[i - 1] + d * (lens[i - 1] / d.length)
        for i in range(1, len(P)):       # ground clamp
            if P[i].z < 0.05:
                P[i].z = 0.05
        # INV-6 PRE-EMPTIVE GUARD: hard clamp per-frame particle travel so a
        # single frame can never breach M1 (0.06*3.2m = 0.192; clamp 0.15).
        for i in range(1, len(P)):
            d = P[i] - prev[i]
            if d.length > DELTA_CLAMP:
                P[i] = prev[i] + d * (DELTA_CLAMP / d.length)
                Pp[i] = prev[i].copy()   # kill the excess velocity too
            max_particle_delta = max(max_particle_delta, min(d.length, DELTA_CLAMP))
        sim[(f, ci)] = [v.copy() for v in P]
print(f"[build] sim done; max per-frame particle delta (post-clamp) = "
      f"{max_particle_delta:.3f}m (clamp {DELTA_CLAMP}m, M1 limit "
      f"{0.06 * CHAR_HEIGHT:.3f}m)")

# Bake sim -> local quaternions on every phys bone (angular deviation clamp)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
PREV_PQ = {}                # R1 FIX: hemisphere continuity for phys quats too
for ci, ch in enumerate(chains):
    _, _, _, maxdev = params(ch[0].name)
    for f in range(1, FRAME_END + 1):
        Mparent = anchor_mats[(f, ch[0].parent.name)].copy()
        P = sim[(f, ci)]
        for i, pb in enumerate(ch):
            Mu = Mparent @ OFF[pb.name]
            Wu = AW @ Mu
            y = (Wu.to_3x3() @ VSTEP[pb.name]).normalized()
            d = P[i + 1] - P[i]
            if d.length < 1e-9:
                q = Quaternion()
            else:
                q = y.rotation_difference(d.normalized())
                if math.degrees(q.angle) > maxdev:
                    q = Quaternion(q.axis, math.radians(maxdev))
            head = Wu.translation
            Wc = (Matrix.Translation(head) @ q.to_matrix().to_4x4()
                  @ Matrix.Translation(-head)) @ Wu
            Mc = AWI @ Wc
            basis = OFF[pb.name].inverted() @ Mparent.inverted() @ Mc
            # R1 FIX: to_quaternion() can land on either hemisphere frame to
            # frame (reads as ~360deg/frame in M2 world-quat diffs); flip so
            # q.dot(prev) >= 0 — identical rotation, continuous representation.
            bq = basis.to_quaternion().normalized()
            ppq = PREV_PQ.get(pb.name)
            if ppq is not None and bq.dot(ppq) < 0.0:
                bq = -bq
            PREV_PQ[pb.name] = bq.copy()
            pb.rotation_quaternion = bq
            pb.keyframe_insert(data_path='rotation_quaternion', frame=f)
            Mparent = Mc
    print(f"[build] baked {ch[0].name[:-3]} ({len(ch)} bones)")
bpy.ops.object.mode_set(mode='OBJECT')

# ── Name the action ─────────────────────────────────────────────────────────
act = arm.animation_data.action
assert act is not None, "FATAL: no action created"
old = bpy.data.actions.get(ACTION_NAME)
if old and old is not act:
    bpy.data.actions.remove(old)         # INV-3 idempotent rename
act.name = ACTION_NAME
print(f"[build] action = {act.name}")

# ── Numeric self-checks (sword path + X-cross + spin rate) ──────────────────
def _fold(a):
    """Fold a quaternion double-cover angle (0..360) to true rotation (0..180)."""
    return min(a, 360.0 - a)

dg = bpy.context.evaluated_depsgraph_get()
tip_path, grip_path, yaw_track = {}, {}, {}
prev_wq = {}
worst_av, worst_av_info = 0.0, ""
worst_bend, worst_bend_info = 0.0, ""
HINGES = ("RightForeArm", "LeftForeArm", "RightLeg", "LeftLeg")
for f in range(1, FRAME_END + 1):
    sc.frame_set(f)
    dg.update()
    sw = sword.evaluated_get(dg)
    tip_path[f]  = (sw.matrix_world @ TIP_LOCAL).copy()
    grip_path[f] = (sw.matrix_world @ GRIP_LOCAL).copy()
    # torso yaw (deg) at this frame — actual interpolated pose values
    # (R1: bones are quaternion mode now; decompose for the yaw sum)
    yaw_track[f] = sum(
        math.degrees(arm.pose.bones[n].rotation_quaternion.to_euler('XYZ').z)
        for n in ("Spine", "Spine01", "Spine02", "Hips"))
    # sword-grip distance to hand (M4 preview)
    hand_w = (arm.matrix_world @ arm.pose.bones["RightHand"].matrix).translation
    gd = (grip_path[f] - hand_w).length
    assert gd < 0.30, f"FATAL f{f}: sword grip {gd:.2f}m from hand (detach)"
    # R1 FIX self-checks — TRUE (double-cover-folded) M2 quantities:
    # a) world angular velocity of every keyed body bone < 45 deg/frame
    for n in CTRL:
        wq = (arm.matrix_world @ arm.pose.bones[n].matrix).to_quaternion()
        if n in prev_wq:
            av = _fold(math.degrees(prev_wq[n].rotation_difference(wq).angle))
            if av > worst_av:
                worst_av, worst_av_info = av, f"{n}@f{f}"
        prev_wq[n] = wq
    # b) elbow/knee true bend (parent-vs-child world rotation) < 175 deg
    for n in HINGES:
        pbh = arm.pose.bones[n]
        qp = (arm.matrix_world @ pbh.parent.matrix).to_quaternion()
        qc = (arm.matrix_world @ pbh.matrix).to_quaternion()
        bend = _fold(math.degrees(qp.rotation_difference(qc).angle))
        if bend > worst_bend:
            worst_bend, worst_bend_info = bend, f"{n}@f{f}"
# R2: the metric re-imports the glb into a default 24fps scene and samples at
# 1/24s steps; one metric step spans at most 1.25 authored frames, so the
# authored (30fps) worst must clear 45/1.25 = 36 deg/frame for the metric's
# folded truth to clear 45.
print(f"[build] M2 self-check: worst TRUE body ang-vel {worst_av:.1f}deg/frame "
      f"@30fps ({worst_av_info}, limit 36 = 45 at the metric's 24fps sampling)")
print(f"[build] M2 self-check: worst TRUE elbow/knee bend {worst_bend:.1f}deg "
      f"({worst_bend_info}, limit 175)")
assert worst_av < 36.0, f"FATAL: body ang-vel {worst_av:.1f} ({worst_av_info})"
assert worst_bend < 175.0, f"FATAL: hinge bend {worst_bend:.1f} ({worst_bend_info})"
# R5 fix a: the windup COIL must read — tip rises visibly along his right
# side (f6 guard -> f10 rise -> f14 loaded) and the held windup tip sits
# HIGH and clearly on HIS RIGHT (-x) of center.
rise1 = tip_path[10].z - tip_path[6].z
rise2 = tip_path[14].z - tip_path[10].z
tw = tip_path[15]
print(f"[build] WINDUP coil: tip rise f6->f10 {rise1:+.2f}m, f10->f14 "
      f"{rise2:+.2f}m; held tip x={tw.x:+.2f} z={tw.z:.2f} "
      f"(want rise>0.3 each, x<=-0.5, z>=2.6)")
assert rise1 > 0.3 and rise2 > 0.3, "FATAL: windup coil does not rise"
assert tw.x <= -0.5, f"FATAL: windup tip not over HIS RIGHT (x={tw.x:+.2f})"
assert tw.z >= 2.6, f"FATAL: windup tip too low (z={tw.z:.2f})"
# R5 fix b: torso pre-rotation across each held beat — summed spine/hips yaw
# must move >=10deg TOWARD the cut before the launch frames begin.
pre1 = yaw_track[18] - yaw_track[15]     # cut1 uncoils toward +yaw
pre2 = yaw_track[44] - yaw_track[41]     # cut2 uncoils toward -yaw
print(f"[build] torso pre-rotation: beat1 {pre1:+.1f}deg (want >=+10), "
      f"beat2 {pre2:+.1f}deg (want <=-10)")
assert pre1 >= 10.0, f"FATAL: no torso pre-rotation into cut1 ({pre1:+.1f})"
assert pre2 <= -10.0, f"FATAL: no torso pre-rotation into cut2 ({pre2:+.1f})"
d1 = tip_path[29] - tip_path[19]         # R4 retime: cut1 held f18 -> end f29
d2 = tip_path[55] - tip_path[45]         # R4 retime: cut2 held f44 -> end f55
print(f"[build] CUT1 tip delta dx={d1.x:+.2f} dz={d1.z:+.2f} (want +x, -z: \\)")
print(f"[build] CUT2 tip delta dx={d2.x:+.2f} dz={d2.z:+.2f} (want -x, -z: /)")
assert d1.x > 0.5 and d1.z < -0.5, "FATAL: cut1 not a \\ stroke"
assert d2.x < -0.5 and d2.z < -0.5, "FATAL: cut2 not a / stroke"
# R4 blocker fix a: each stroke must be DIAGONAL on screen, not a vertical
# drop — lateral travel at least 0.55x the vertical travel (~29deg+ off
# vertical in the frontal camera plane).
r1 = abs(d1.x) / max(abs(d1.z), 1e-6)
r2 = abs(d2.x) / max(abs(d2.z), 1e-6)
print(f"[build] stroke diagonality |dx|/|dz|: cut1={r1:.2f} cut2={r2:.2f} "
      f"(min 0.55)")
assert r1 >= 0.55, f"FATAL: cut1 too vertical (|dx|/|dz|={r1:.2f})"
assert r2 >= 0.55, f"FATAL: cut2 too vertical (|dx|/|dz|={r2:.2f})"
# R3 blocker fix a: the two dense tip paths must actually INTERSECT in the
# frontal camera plane (world XZ — the cam looks straight down +Y), at
# mid-torso height, near the midline, and IN FRONT of the body (y < -0.15).
def _seg_x(p1, p2, p3, p4):
    """2D (x,z) segment intersection; returns (t, u) in [0,1]^2 or None."""
    d1x, d1z = p2.x - p1.x, p2.z - p1.z
    d2x, d2z = p4.x - p3.x, p4.z - p3.z
    den = d1x * d2z - d1z * d2x
    if abs(den) < 1e-9:
        return None
    t = ((p3.x - p1.x) * d2z - (p3.z - p1.z) * d2x) / den
    u = ((p3.x - p1.x) * d1z - (p3.z - p1.z) * d1x) / den
    return (t, u) if (0.0 <= t <= 1.0 and 0.0 <= u <= 1.0) else None

seg1 = [tip_path[f] for f in range(19, 30)]   # cut1 stroke, dense (R4 retime)
seg2 = [tip_path[f] for f in range(45, 56)]   # cut2 stroke, dense (R4 retime)
xing = None
for i in range(len(seg1) - 1):
    for j in range(len(seg2) - 1):
        hit = _seg_x(seg1[i], seg1[i + 1], seg2[j], seg2[j + 1])
        if hit:
            t, u = hit
            pA = seg1[i].lerp(seg1[i + 1], t)
            pB = seg2[j].lerp(seg2[j + 1], u)
            xing = (pA, pB)
            break
    if xing:
        break
assert xing, "FATAL: cut paths do NOT cross in the camera plane (no X)"
pA, pB = xing
print(f"[build] X-CROSS at x={pA.x:+.2f} z={pA.z:.2f} "
      f"(depths y1={pA.y:+.2f} y2={pB.y:+.2f})")
assert 0.9 < pA.z < 2.4, f"FATAL: X crosses at z={pA.z:.2f}, not mid-torso"
# R5 fix c: tightened 0.9 -> 0.55 — the crossing must sit ON the midline.
assert abs(pA.x) < 0.55, f"FATAL: X crossing off-midline x={pA.x:+.2f}"
assert pA.y < -0.15 and pB.y < -0.15, "FATAL: X crossing not in FRONT of body"
# spin rate (SPEC sec 7: no more than ~1 full ROTATION per second): the torso
# must never accumulate >=360deg of yaw travel inside any 1-second window.
# (A ~50deg torso rotation releasing a cut is a cut, not a spin — measured on
# the actual interpolated per-frame yaw, not key-table diffs.)
max_window_sweep = 0.0
for f0 in range(1, FRAME_END - FPS + 2):
    sweep = sum(abs(yaw_track[f + 1] - yaw_track[f])
                for f in range(f0, f0 + FPS - 1))
    max_window_sweep = max(max_window_sweep, sweep)
print(f"[build] max torso yaw travel in any 1s window = {max_window_sweep:.0f}deg "
      f"(SPEC limit 360)")
assert max_window_sweep < 360.0, "FATAL: torso spins faster than 1 rot/sec"

# ── Save .blend ─────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print(f"[build] saved {BLEND_OUT}")

# ── Export WIP glb (armature + skinned meshes + sword + materials + action) ─
skinned = [o for o in sc.objects if o.type == 'MESH' and len(o.vertex_groups) > 0]
assert skinned, "FATAL: no skinned mesh"
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
sword.select_set(True)
for o in skinned:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=GLB_OUT,
    use_selection=True,
    export_format="GLB",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_skins=True,
    export_yup=True,
    export_lights=False,
    export_cameras=False,
    export_animations=True,
    export_armature_object_remove=False,
    export_rest_position_armature=False,
    export_apply=False,
)
print(f"[build] exported {GLB_OUT} ({os.path.getsize(GLB_OUT):,} bytes)")

# ── Self-check strip renders (EEVEE) ────────────────────────────────────────
try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x, sc.render.resolution_y = 640, 820
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.render.use_stamp = True
for attr in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time",
             "use_stamp_frame", "use_stamp_scene", "use_stamp_camera",
             "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
    if hasattr(sc.render, attr):
        setattr(sc.render, attr, False)
sc.render.use_stamp_note = True
sc.render.stamp_font_size = 22
sc.render.stamp_foreground = (1, 1, 1, 1)
sc.render.stamp_background = (0, 0, 0, 0.7)

STRIP = [(1, "GUARD"), (10, "WINDUP-1 rise (coil up R side)"),
         (16, "WINDUP-1 over-R-shoulder"), (25, "CUT-1 mid"),
         (29, "CUT-1 end lower-L"), (42, "WINDUP-2 upper-L"),
         (51, "CUT-2 mid"), (55, "CUT-2 end lower-R + step"), (64, "RECOVER")]
for camtag, c in (("front", cam), ("back", back_cam)):
    sc.camera = c
    for f, note in STRIP:
        sc.frame_set(f)
        sc.render.stamp_note_text = f"{ACTION_NAME} f{f:02d} {note} [{camtag}]"
        sc.render.filepath = os.path.join(OUTDIR, f"check_{camtag}_f{f:02d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[build] rendered {sc.render.filepath}")
sc.camera = cam
print("[build] DONE")
