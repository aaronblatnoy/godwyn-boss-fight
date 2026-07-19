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

# Near-frontal cam (he faces -Y) so BOTH diagonals read; plus a back cam for cape.
bpy.ops.object.camera_add(location=(1.2, -7.4, 2.1))
cam = bpy.context.active_object
cam.name = "XS_Cam"
tgt = Vector((0.0, 0.0, 1.8))
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
    pb.rotation_mode = 'XYZ'

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

def key_pose(frame, pose, blade_dir=None):
    for n in CTRL:
        rx, ry, rz = pose.get(n, (0, 0, 0))
        arm.pose.bones[n].rotation_euler = Euler(
            (math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ')
    if blade_dir is not None:
        aim_hand(blade_dir)
    for n in CTRL:
        arm.pose.bones[n].keyframe_insert(data_path='rotation_euler', frame=frame)

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
    "RightShoulder": (0, 0, -18),
    "RightArm":      (-70, 0, -72),
    "RightForeArm":  (-30, 30, 0),
    "LeftShoulder":  (0, 0, 6),
    "LeftArm":       (30, 0, 18),
    "LeftForeArm":   (-25, 0, 0),
    "Spine":         (0, 0, -16),        # spine coil = the power source
    "Spine01":       (0, 0, -10),
    "Spine02":       (-4, 0, -6),
    "Hips":          (0, 0, -6),
    "Head":          (0, 0, 10),
    "RightUpLeg":    (6, 0, 0),
}
CUT1_MID = {
    "RightShoulder": (0, 0, -4),
    "RightArm":      (-45, 0, -10),
    "RightForeArm":  (-5, 10, 0),
    "LeftArm":       (24, 0, 14),
    "LeftForeArm":   (-20, 0, 0),
    "Spine":         (6, 0, 2),
    "Spine01":       (4, 0, 2),
    "Head":          (-4, 0, 0),
    "LeftUpLeg":     (-14, 0, 0),        # small forward step with the cut
    "LeftLeg":       (10, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
CUT1_END = {                             # hip height across at HIS LEFT (\ done)
    "RightShoulder": (0, 0, 14),
    "RightArm":      (5, 0, -35),
    "RightForeArm":  (-5, 0, 0),
    "LeftShoulder":  (0, 0, -4),
    "LeftArm":       (14, 0, 8),
    "LeftForeArm":   (-12, 0, 0),
    "Spine":         (2, 0, 22),         # rotation carried THROUGH the cut
    "Spine01":       (3, 0, 12),
    "Spine02":       (2, 0, 6),
    "Hips":          (0, 0, 8),
    "Head":          (-8, 0, -8),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (12, 0, 0),
    "RightUpLeg":    (10, 0, 0),
}
CUT1_SETTLE = {
    "RightShoulder": (0, 0, 11),
    "RightArm":      (5, 0, -32),
    "RightForeArm":  (-10, 0, 0),
    "LeftArm":       (16, 0, 10),
    "LeftForeArm":   (-14, 0, 0),
    "Spine":         (2, 0, 18),
    "Spine01":       (3, 0, 10),
    "Hips":          (0, 0, 6),
    "Head":          (-7, 0, -6),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (10, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
WINDUP2 = {                              # hand HIGH, blade up-left, lateral coil
    "RightShoulder": (0, 0, 16),
    "RightArm":      (-85, -45, 0),
    "RightForeArm":  (-25, -15, 0),
    "LeftShoulder":  (0, 0, -4),
    "LeftArm":       (26, 0, 16),
    "LeftForeArm":   (-22, 0, 0),
    "Spine":         (0, 0, 26),
    "Spine01":       (0, 0, 10),
    "Spine02":       (-4, 0, 5),
    "Hips":          (0, 0, 6),
    "Head":          (0, 0, -16),
    "LeftUpLeg":     (-14, 0, 0),
    "LeftLeg":       (9, 0, 0),
    "RightUpLeg":    (7, 0, 0),
}
CUT2_MID = {
    "RightShoulder": (0, 0, 2),
    "RightArm":      (-45, 0, 10),
    "RightForeArm":  (-5, -10, 0),
    "LeftArm":       (22, 0, 12),
    "LeftForeArm":   (-18, 0, 0),
    "Spine":         (6, 0, -2),
    "Spine01":       (4, 0, -1),
    "Head":          (-4, 0, 2),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (8, 0, 0),
    "RightUpLeg":    (6, 0, 0),
}
CUT2_END = {                             # hip height out at HIS RIGHT (/ done)
    "RightShoulder": (0, 0, -16),
    "RightArm":      (8, 0, -24),
    "RightForeArm":  (-20, 10, 0),
    "LeftShoulder":  (0, 0, 6),
    "LeftArm":       (20, 0, 14),
    "LeftForeArm":   (-16, 0, 0),
    "Spine":         (10, 0, -18),
    "Spine01":       (6, 0, -10),
    "Spine02":       (4, 0, -5),
    "Hips":          (4, 0, -6),
    "Head":          (2, 0, 8),
    "LeftUpLeg":     (-14, 0, 0),
    "LeftLeg":       (9, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}
CUT2_SETTLE = {
    "RightShoulder": (0, 0, -13),
    "RightArm":      (8, 0, -22),
    "RightForeArm":  (-20, 8, 0),
    "LeftArm":       (21, 0, 13),
    "LeftForeArm":   (-17, 0, 0),
    "Spine":         (8, 0, -12),
    "Spine01":       (5, 0, -7),
    "Hips":          (3, 0, -4),
    "Head":          (0, 0, 6),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (8, 0, 0),
    "RightUpLeg":    (6, 0, 0),
}

# WORLD blade directions per key (validated: X crosses in FRONT, strokes full)
D_GUARD   = (-0.20, -0.55, -0.81)
D_WINDUP1 = (-0.42,  0.28,  0.86)
D_CUT1MID = ( 0.80, -0.55, -0.18)
D_CUT1END = ( 0.47, -0.30, -0.76)
D_CUT1SET = ( 0.46, -0.30, -0.77)
D_WINDUP2 = ( 0.62,  0.22,  0.76)
D_CUT2MID = (-0.58, -0.75, -0.18)
D_CUT2END = (-0.36, -0.36, -0.86)
D_CUT2SET = (-0.35, -0.36, -0.86)

TIMELINE = [
    (1,  GUARD,       D_GUARD,   "guard"),
    (6,  GUARD,       D_GUARD,   "guard_hold"),
    (16, WINDUP1,     D_WINDUP1, "windup1"),
    (18, WINDUP1,     D_WINDUP1, "windup1_hold"),
    (21, CUT1_MID,    D_CUT1MID, "cut1_mid"),
    (25, CUT1_END,    D_CUT1END, "cut1_end"),
    (29, CUT1_SETTLE, D_CUT1SET, "cut1_settle"),
    (38, WINDUP2,     D_WINDUP2, "windup2"),
    (40, WINDUP2,     D_WINDUP2, "windup2_hold"),
    (43, CUT2_MID,    D_CUT2MID, "cut2_mid"),
    (47, CUT2_END,    D_CUT2END, "cut2_end"),
    (51, CUT2_SETTLE, D_CUT2SET, "cut2_settle"),
    (64, GUARD,       D_GUARD,   "recover"),
]
for frame, pose, blade, label in TIMELINE:
    key_pose(frame, pose, blade)
    print(f"[build] keyed f{frame:02d} {label}")
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
    """(stiffness pull to rigid, damping, gravity scale, max deviation deg)"""
    if "hair" in name:  return (0.30, 0.84, 1.5, 40.0)
    if "robe" in name:  return (0.24, 0.82, 3.5, 30.0)
    return (0.22, 0.80, 3.5, 30.0)      # cape: stiff pull, tight cap, trails low

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
            pb.rotation_quaternion = basis.to_quaternion().normalized()
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
dg = bpy.context.evaluated_depsgraph_get()
tip_path, grip_path, yaw_track = {}, {}, {}
for f in range(1, FRAME_END + 1):
    sc.frame_set(f)
    dg.update()
    sw = sword.evaluated_get(dg)
    tip_path[f]  = (sw.matrix_world @ TIP_LOCAL).copy()
    grip_path[f] = (sw.matrix_world @ GRIP_LOCAL).copy()
    # torso yaw (deg) at this frame — actual interpolated pose values
    yaw_track[f] = sum(math.degrees(arm.pose.bones[n].rotation_euler.z)
                       for n in ("Spine", "Spine01", "Spine02", "Hips"))
    # sword-grip distance to hand (M4 preview)
    hand_w = (arm.matrix_world @ arm.pose.bones["RightHand"].matrix).translation
    gd = (grip_path[f] - hand_w).length
    assert gd < 0.30, f"FATAL f{f}: sword grip {gd:.2f}m from hand (detach)"
d1 = tip_path[25] - tip_path[18]
d2 = tip_path[47] - tip_path[40]
print(f"[build] CUT1 tip delta dx={d1.x:+.2f} dz={d1.z:+.2f} (want +x, -z: \\)")
print(f"[build] CUT2 tip delta dx={d2.x:+.2f} dz={d2.z:+.2f} (want -x, -z: /)")
assert d1.x > 0.5 and d1.z < -0.5, "FATAL: cut1 not a \\ stroke"
assert d2.x < -0.5 and d2.z < -0.5, "FATAL: cut2 not a / stroke"
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

STRIP = [(1, "GUARD"), (16, "WINDUP-1 upper-R"), (21, "CUT-1 mid"),
         (25, "CUT-1 end lower-L"), (38, "WINDUP-2 upper-L"),
         (43, "CUT-2 mid"), (47, "CUT-2 end lower-R"), (64, "RECOVER")]
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
