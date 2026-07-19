"""
anim_xslash_cape.py — PHASE 2: cape/robe/hair FOLLOW-THROUGH for the X-slash.

Opens models/godwyn_xslash.blend (Phase 1 animation intact) and bakes a
verlet point-chain simulation into keyframes on every phys_* bone chain:
each chain trails the body motion with inertia + damping, is pulled softly
back toward its rigid (rest-follow) shape, respects link lengths, and
settles after each cut. Secondary motion only — the P1 body/sword keys are
untouched.

Method (no cloth sim, deterministic, fast):
  PASS A: per frame, sample the animated pose matrix of each chain's anchor
          bone (Spine/Hips/Head) -> rigid world joint targets per chain.
  SIM   : world-space verlet particles per chain joint; root pinned to the
          animated anchor; inertia*damping + light gravity + stiffness pull
          toward the rigid target + distance constraints + ground clamp.
  PASS B: per frame, convert simulated joints into local bone quaternions
          analytically (offset/basis math, no depsgraph feedback) and
          keyframe rotation_quaternion on every phys bone.

Run (server):
  blender --background --python ~/godwyn-boss-fight/scripts/anim_xslash_cape.py 2>&1
  RENDER_ANIM=1 ... to also render all 64 frames for the mp4.
"""
import bpy, os, math
from mathutils import Vector, Matrix, Quaternion

REPO   = os.path.expanduser("~/godwyn-boss-fight")
BLEND  = os.path.join(REPO, "models", "godwyn_xslash.blend")
OUTDIR = os.path.join(REPO, "renders", "xslash")
RENDER_ANIM = os.environ.get("RENDER_ANIM") == "1"

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc  = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
F0, F1 = sc.frame_start, sc.frame_end
print(f"[cape] {arm.name} bones={len(arm.pose.bones)} frames {F0}-{F1}")

AW  = arm.matrix_world.copy()
AWI = AW.inverted()

# ── Enumerate phys chains (root = phys bone whose parent is a body bone) ────
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
print(f"[cape] {len(chains)} chains, {sum(len(c) for c in chain for chain in [chains])} bones"
      if False else f"[cape] {len(chains)} chains, {sum(len(c) for c in chains)} phys bones")

# Per-chain-type feel: (stiffness pull to rigid, damping, gravity scale, max deviation deg)
def params(name):
    if "hair" in name:  return (0.30, 0.84, 1.5, 40.0)
    if "robe" in name:  return (0.24, 0.82, 3.5, 30.0)   # heavy skirt, quick settle
    # cape — fixer r2: stiffer pull + tighter deviation cap so it trails LOWER
    # and settles faster instead of flinging into a board-flat sail.
    return (0.22, 0.80, 3.5, 30.0)

def chain_phase(name):
    """fixer r2: slight per-column temporal offset (in frames) for the cape so
    the L/C/R columns break up instead of moving as one rigid plane."""
    if "cape" not in name:
        return 0.0
    if "_C_" in name:
        return 0.4
    if "_R_" in name:
        return 0.8
    return 0.0                                            # cape_L leads

# Static rest offsets: offset_i = parent.matrix_local^-1 @ bone.matrix_local
# NOTE: glTF import gave phys bones bogus ~35m tails (bone.length useless, and
# the bone Y axis does NOT point down the chain). The true chain direction is
# the offset to the CHILD bone head — so we aim VSTEP vectors, never Y.
OFF = {}
for ch in chains:
    for pb in ch:
        OFF[pb.name] = pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
VSTEP = {}                            # bone -> local vector to the next joint
for ch in chains:
    for i, pb in enumerate(ch):
        if i + 1 < len(ch):
            VSTEP[pb.name] = OFF[ch[i + 1].name].translation.copy()
        else:                         # tip: continue the last step in own frame
            o = OFF[pb.name]
            VSTEP[pb.name] = o.to_3x3().inverted() @ o.translation

# ── PASS A: sample anchor pose matrices per frame; build rigid joints ───────
anchor_mats = {}                      # (frame, anchor_name) -> pose-space Matrix
anchors = sorted({ch[0].parent.name for ch in chains})
dg = bpy.context.evaluated_depsgraph_get()
for f in range(F0, F1 + 1):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    for a in anchors:
        anchor_mats[(f, a)] = arm.pose.bones[a].matrix.copy()

def rigid_joints(ch, f):
    """World-space joint positions [head0, head1, ..., tip] with identity
    phys rotations, driven only by the animated anchor."""
    M = anchor_mats[(f, ch[0].parent.name)].copy()
    joints = []
    W = None
    for pb in ch:
        M = M @ OFF[pb.name]
        W = AW @ M
        joints.append(W.translation.copy())
    joints.append(W @ VSTEP[ch[-1].name])          # virtual tip
    return joints

# ── Verlet simulation (world space) ─────────────────────────────────────────
DT2 = (1.0 / sc.render.fps) ** 2
sim = {}                              # (frame, chain_idx) -> list[Vector]
for ci, ch in enumerate(chains):
    stiff, damp, gscale, _ = params(ch[0].name)
    rest = rigid_joints(ch, F0)
    lens = [(rest[i + 1] - rest[i]).length for i in range(len(rest) - 1)]
    P  = [v.copy() for v in rest]
    Pp = [v.copy() for v in rest]
    ph = chain_phase(ch[0].name)
    for f in range(F0, F1 + 1):
        if ph > 0.0 and f > F0:       # sample the target ph frames in the past
            ta = rigid_joints(ch, f - 1)
            tb = rigid_joints(ch, f)
            tgt = [a * ph + b * (1.0 - ph) for a, b in zip(ta, tb)]
        else:
            tgt = rigid_joints(ch, f)
        P[0] = tgt[0].copy()          # pin root joint to the animated anchor
        for i in range(1, len(P)):
            vel = (P[i] - Pp[i]) * damp
            new = (P[i] + vel
                   + Vector((0, 0, -9.8 * gscale)) * DT2
                   + (tgt[i] - P[i]) * stiff)
            Pp[i] = P[i].copy()
            P[i] = new
        for _ in range(3):            # distance constraints, root outward
            for i in range(1, len(P)):
                d = P[i] - P[i - 1]
                L = d.length
                if L > 1e-9:
                    P[i] = P[i - 1] + d * (lens[i - 1] / L)
        for i in range(1, len(P)):    # ground clamp
            if P[i].z < 0.05:
                P[i].z = 0.05
        sim[(f, ci)] = [v.copy() for v in P]

# Lag metric on the center cape chain at key frames
ccape = next(i for i, ch in enumerate(chains) if ch[0].name == "phys_cape_C_00")
print("[cape] cape_C tip lag (deg between rigid dir and sim dir, root->tip):")
maxlag = 0.0
for f in range(F0, F1 + 1):
    r = rigid_joints(chains[ccape], f)
    s = sim[(f, ccape)]
    a = math.degrees((r[-1] - r[0]).angle(s[-1] - s[0]))
    maxlag = max(maxlag, a)
    if f in (1, 16, 21, 25, 29, 38, 43, 47, 51, 64):
        print(f"[cape]   f{f:02d} lag={a:5.1f}deg  simTip=({s[-1].x:+.2f},{s[-1].y:+.2f},{s[-1].z:+.2f})")
print(f"[cape] max cape_C lag over clip: {maxlag:.1f}deg")

# ── PASS B: bake sim -> local quaternions, keyframe every phys bone ─────────
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for ci, ch in enumerate(chains):
    _, _, _, maxdev = params(ch[0].name)
    for f in range(F0, F1 + 1):
        Mparent = anchor_mats[(f, ch[0].parent.name)].copy()   # corrected chain parent
        P = sim[(f, ci)]
        for i, pb in enumerate(ch):
            Mu = Mparent @ OFF[pb.name]                        # uncorrected pose mat
            Wu = AW @ Mu
            y = (Wu.to_3x3() @ VSTEP[pb.name]).normalized()    # chain dir, NOT bone Y
            d = (P[i + 1] - P[i])
            if d.length < 1e-9:
                q = Quaternion()
            else:
                q = y.rotation_difference(d.normalized())
                if math.degrees(q.angle) > maxdev:             # clamp deviation
                    q = Quaternion(q.axis, math.radians(maxdev))
            head = Wu.translation
            Wc = (Matrix.Translation(head) @ q.to_matrix().to_4x4()
                  @ Matrix.Translation(-head)) @ Wu
            Mc = AWI @ Wc
            basis = OFF[pb.name].inverted() @ Mparent.inverted() @ Mc
            pb.rotation_quaternion = basis.to_quaternion().normalized()
            pb.keyframe_insert(data_path='rotation_quaternion', frame=f)
            Mparent = Mc                                       # child sees corrected parent
    print(f"[cape] baked chain {ch[0].name[:-3]} ({len(ch)} bones x {F1-F0+1} frames)")
bpy.ops.object.mode_set(mode='OBJECT')

# ── Save .blend ──────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"[cape] saved {BLEND}")

# ── Render verification strip (EEVEE) ───────────────────────────────────────
try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x, sc.render.resolution_y = 640, 820
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

# Add a BACK camera too — the cape lives behind him; verify from both sides
back_cam = bpy.data.objects.get("BackCam")
if back_cam is None:
    cd = bpy.data.cameras.new("BackCam")
    back_cam = bpy.data.objects.new("BackCam", cd)
    sc.collection.objects.link(back_cam)
back_cam.location = Vector((-3.0, 6.4, 2.3))
tgt = Vector((0.0, 0.0, 1.5))
back_cam.rotation_euler = (tgt - back_cam.location).to_track_quat('-Z', 'Y').to_euler()
front_cam = sc.camera

STRIP = [(16, "WINDUP-1"), (21, "CUT-1 mid"), (25, "CUT-1 end"), (29, "settle"),
         (43, "CUT-2 mid"), (47, "CUT-2 end"), (51, "settle"), (64, "RECOVER")]
for cam, camtag in ((front_cam, "front"), (back_cam, "back")):
    sc.camera = cam
    for f, note in STRIP:
        sc.frame_set(f)
        sc.render.stamp_note_text = f"P2 CAPE f{f:02d} {note} [{camtag}]"
        sc.render.filepath = os.path.join(OUTDIR, f"cape_{camtag}_f{f:02d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[cape] rendered {sc.render.filepath}")
sc.camera = front_cam

# ── Optional: full animation frames for the preview mp4 ─────────────────────
if RENDER_ANIM:
    ANIMDIR = os.path.join(OUTDIR, "anim_cape")
    os.makedirs(ANIMDIR, exist_ok=True)
    sc.render.use_stamp = False
    sc.render.filepath = os.path.join(ANIMDIR, "f")
    sc.frame_start, sc.frame_end = F0, F1
    bpy.ops.render.render(animation=True)
    print(f"[cape] animation frames in {ANIMDIR}")
print("[cape] DONE")
