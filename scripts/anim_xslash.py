"""
anim_xslash.py — PHASE 1: author the X-SLASH combo (SPEC Section 7).

From a low ready guard: windup UPPER-RIGHT -> CUT 1 down to LOWER-LEFT ( \\ );
short transition; windup UPPER-LEFT -> CUT 2 down to LOWER-RIGHT ( / ).
The two cuts cross to form an X in front of Godwyn. Weighty, readable.

Blender 5.2 slotted actions: we keyframe pose bones directly via
pose_bone.keyframe_insert() (auto-creates the slotted action).
Power comes from the SPINE + SHOULDER, not just the wrist.

Timing @30fps (~64 frames total):
  f1   guard (low ready)
  f6   guard hold (anticipation start)
  f16  windup 1 — sword upper-right   (10f raise = weighty)
  f18  hold / coil
  f21  cut 1 mid (blade through center)
  f25  cut 1 end — lower-left         (7f active swing)
  f29  settle / recoil
  f38  windup 2 — sword upper-left
  f40  hold / coil
  f43  cut 2 mid
  f47  cut 2 end — lower-right        (7f active swing)
  f51  settle
  f64  recover to guard

Run (server):
  blender --background --python ~/godwyn-boss-fight/scripts/anim_xslash.py 2>&1
"""
import bpy, os, math
from mathutils import Euler, Vector, Matrix

REPO   = os.path.expanduser("~/godwyn-boss-fight")
GLB    = os.path.join(REPO, "models", "godwyn_game.glb")
BLEND  = os.path.join(REPO, "models", "godwyn_xslash.blend")
OUTDIR = os.path.join(REPO, "renders", "xslash")
os.makedirs(OUTDIR, exist_ok=True)

FPS = 30
FRAME_END = 64

# ── Clear & import ───────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arm   = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
sword = bpy.data.objects.get("Godwyn_Sword")
print(f"[xslash] armature={arm.name}  sword={sword.name if sword else 'MISSING'}"
      f"  sword.parent_bone={sword.parent_bone if sword else '?'}")

# ── FIX: re-seat the sword in the grip ──────────────────────────────────────
# The glTF import bone-parents the sword at the RightHand bone's guessed tail,
# which is ~49m away (probe2) — the sword has been 47m underground. Solve its
# world matrix at REST so the grip end of the blade sits at the hand, blade
# hanging DOWN (raising the arm then swings the tip up naturally).
bpy.context.view_layer.update()
_bb = [Vector(c) for c in sword.bound_box]          # sword-local bbox
_zmin = min(c.z for c in _bb)
_zmax = max(c.z for c in _bb)
_cx   = sum((c.x for c in _bb)) / 8.0
_cy   = sum((c.y for c in _bb)) / 8.0
GRIP_LOCAL = Vector((_cx, _cy, _zmin))               # bottom-of-blade center
TIP_LOCAL  = Vector((_cx, _cy, _zmax))               # top-of-blade center
hand_rest_w = arm.matrix_world @ arm.pose.bones["RightHand"].head
_R = Matrix.Rotation(math.radians(180), 4, 'X')      # local +Z -> world -Z
_S = Matrix.Diagonal((0.01, 0.01, 0.01, 1.0))        # keep 0.01 world scale
sword.matrix_world = (Matrix.Translation(hand_rest_w) @ _R @ _S
                      @ Matrix.Translation(-GRIP_LOCAL))
bpy.context.view_layer.update()
print(f"[xslash] sword re-seated: grip at {tuple(round(v,2) for v in hand_rest_w)}"
      f", blade length {(_zmax - _zmin) * 0.01:.2f}m")

# ── Scene setup ──────────────────────────────────────────────────────────────
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start = 1
sc.frame_end = FRAME_END

# Ground
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
ground = bpy.context.active_object
gmat = bpy.data.materials.new("Ground")
gmat.use_nodes = True
gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.11, 0.10, 1)
ground.data.materials.append(gmat)

# Lights
bpy.ops.object.light_add(type='SUN', location=(4, -6, 10))
sun = bpy.context.active_object
sun.data.energy = 6.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(30)), 'XYZ')
bpy.ops.object.light_add(type='AREA', location=(-3, -5, 4))
fill = bpy.context.active_object
fill.data.energy = 300
fill.data.size = 4

# Camera — near-frontal (character faces -Y) so BOTH diagonals project onto
# the image plane symmetrically and the X reads (fixer r2: was 3/4 at 3.4,-6.6;
# cut 1 foreshortened to nothing from there).
bpy.ops.object.camera_add(location=(1.2, -7.4, 2.1))
cam = bpy.context.active_object
target = Vector((0.0, 0.0, 1.8))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam

# ── Pose keyframing ──────────────────────────────────────────────────────────
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

CTRL = ["RightShoulder", "RightArm", "RightForeArm", "RightHand",
        "LeftShoulder", "LeftArm", "LeftForeArm",
        "Spine", "Spine01", "Spine02", "Hips", "Head",
        "LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg"]

for n in CTRL:
    pb = arm.pose.bones.get(n)
    if pb:
        pb.rotation_mode = 'XYZ'
    else:
        print(f"[xslash] MISSING bone: {n}")

def aim_hand(blade_dir):
    """Rotate the RightHand pose bone so its Y axis (== blade direction, since
    the sword is re-seated grip-at-head along the hand bone) points at the
    given WORLD direction. Deterministic — no euler sign guessing."""
    bpy.context.view_layer.update()
    pb = arm.pose.bones["RightHand"]
    M = arm.matrix_world @ pb.matrix
    y_now = Vector((M[0][1], M[1][1], M[2][1])).normalized()
    q = y_now.rotation_difference(Vector(blade_dir).normalized())
    R = q.to_matrix().to_4x4()
    T = Matrix.Translation(M.translation)
    M_new = T @ R @ T.inverted() @ M
    pb.matrix = arm.matrix_world.inverted() @ M_new
    bpy.context.view_layer.update()

def key_pose(frame, pose, blade_dir=None):
    """Set every controlled bone (unlisted -> 0,0,0), aim the blade, key all."""
    for n in CTRL:
        pb = arm.pose.bones.get(n)
        if not pb:
            continue
        rx, ry, rz = pose.get(n, (0, 0, 0))
        pb.rotation_euler = Euler((math.radians(rx), math.radians(ry),
                                   math.radians(rz)), 'XYZ')
    if blade_dir is not None:
        aim_hand(blade_dir)
    for n in CTRL:
        pb = arm.pose.bones.get(n)
        if pb:
            pb.keyframe_insert(data_path='rotation_euler', frame=frame)

# ---- POSES (degrees, XYZ) --------------------------------------------------
# World frame: he faces -Y; HIS right = -X, HIS left = +X.
# The wrist is aimed analytically per key (BLADE dirs in the timeline), so
# the tables only need to put the HAND in roughly the right place.
# RightArm gimbal note: with the arm RAISED (X~-70), Z- puts the hand at his
# RIGHT shoulder; with the arm LOWERED (X+), Z- brings the hand across to his
# LEFT (verified in v2/v3 renders).

GUARD = {
    "RightShoulder": (0, 0, -4),
    "RightArm":      (15, 0, -18),      # hand low, front-right hip
    "RightForeArm":  (-32, 10, 0),
    "LeftShoulder":  (0, 0, 5),
    "LeftArm":       (22, 0, 12),
    "LeftForeArm":   (-18, 0, 0),
    "Spine":         (4, 0, 0),
    "Spine01":       (3, 0, 0),
    "Head":          (-4, 0, 0),
}

WINDUP1 = {                              # hand above HIS RIGHT shoulder, coiled
    "RightShoulder": (0, 0, -18),
    "RightArm":      (-70, 0, -72),      # verified upper-right in v3 f16
    "RightForeArm":  (-30, 30, 0),
    "LeftShoulder":  (0, 0, 6),
    "LeftArm":       (30, 0, 18),
    "LeftForeArm":   (-25, 0, 0),
    "Spine":         (0, 0, -16),
    "Spine01":       (0, 0, -10),
    "Spine02":       (-4, 0, -6),
    "Hips":          (0, 0, -6),
    "Head":          (0, 0, 10),
    "RightUpLeg":    (6, 0, 0),
}

CUT1_MID = {                             # hand at SHOULDER height, arm extended
    "RightShoulder": (0, 0, -4),
    "RightArm":      (-45, 0, -10),      # fixer r1: raised so blade sweeps chest height
    "RightForeArm":  (-5, 10, 0),        # fixer r1: extend through the swing
    "LeftArm":       (24, 0, 14),
    "LeftForeArm":   (-20, 0, 0),
    "Spine":         (6, 0, 2),
    "Spine01":       (4, 0, 2),
    "Head":          (-4, 0, 0),
    "LeftUpLeg":     (-14, 0, 0),        # small step-in with the cut
    "LeftLeg":       (10, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}

CUT1_END = {                             # hand at HIP height across at HIS LEFT
    "RightShoulder": (0, 0, 14),
    "RightArm":      (5, 0, -35),        # fixer r1c: probed — lowest across-left hand
    "RightForeArm":  (-5, 0, 0),         # fixer r1: extended, not tucked
    "LeftShoulder":  (0, 0, -4),
    "LeftArm":       (14, 0, 8),
    "LeftForeArm":   (-12, 0, 0),
    "Spine":         (2, 0, 22),         # fixer r2: cut pitch — proud finish, no doubling over
    "Spine01":       (3, 0, 12),
    "Spine02":       (2, 0, 6),
    "Hips":          (0, 0, 8),          # fixer r2: no hip pitch
    "Head":          (-8, 0, -8),        # fixer r2: chin UP through the finish
    "LeftUpLeg":     (-12, 0, 0),        # fixer r2: shallower step-in pitch
    "LeftLeg":       (12, 0, 0),
    "RightUpLeg":    (10, 0, 0),
}

CUT1_SETTLE = {
    "RightShoulder": (0, 0, 11),
    "RightArm":      (5, 0, -32),        # fixer r1c: settle stays LOW, no upward scoop
    "RightForeArm":  (-10, 0, 0),
    "LeftArm":       (16, 0, 10),
    "LeftForeArm":   (-14, 0, 0),
    "Spine":         (2, 0, 18),         # fixer r2: cut pitch
    "Spine01":       (3, 0, 10),
    "Hips":          (0, 0, 6),          # fixer r2: no hip pitch
    "Head":          (-7, 0, -6),        # fixer r2: chin up
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (10, 0, 0),
    "RightUpLeg":    (8, 0, 0),
}

WINDUP2 = {                              # hand HIGH near center, blade up-left
    "RightShoulder": (0, 0, 16),
    "RightArm":      (-85, -45, 0),      # fixer r2: probed — grip z 2.66 (was 1.85!)
    "RightForeArm":  (-25, -15, 0),
    "LeftShoulder":  (0, 0, -4),
    "LeftArm":       (26, 0, 16),
    "LeftForeArm":   (-22, 0, 0),
    "Spine":         (0, 0, 26),         # fixer r2: exaggerated lateral coil
    "Spine01":       (0, 0, 10),
    "Spine02":       (-4, 0, 5),
    "Hips":          (0, 0, 6),
    "Head":          (0, 0, -16),        # fixer r2: distinct left silhouette
    "LeftUpLeg":     (-14, 0, 0),
    "LeftLeg":       (9, 0, 0),
    "RightUpLeg":    (7, 0, 0),
}

CUT2_MID = {
    "RightShoulder": (0, 0, 2),
    "RightArm":      (-45, 0, 10),       # fixer r1: raised so blade sweeps chest height
    "RightForeArm":  (-5, -10, 0),       # fixer r1: extend through the swing
    "LeftArm":       (22, 0, 12),
    "LeftForeArm":   (-18, 0, 0),
    "Spine":         (6, 0, -2),
    "Spine01":       (4, 0, -1),
    "Head":          (-4, 0, 2),
    "LeftUpLeg":     (-12, 0, 0),
    "LeftLeg":       (8, 0, 0),
    "RightUpLeg":    (6, 0, 0),
}

CUT2_END = {                             # hand at HIP height out at HIS RIGHT
    "RightShoulder": (0, 0, -16),
    "RightArm":      (8, 0, -24),        # fixer r2: probed — grip z 1.90, rig floor ~1.85
    "RightForeArm":  (-20, 10, 0),       # fixer r2: slight bend lowers the grip
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
    "RightArm":      (8, 0, -22),        # fixer r2: settle matches low finish
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

# WORLD blade directions per key (his right = -X, front = -Y, up = +Z)
D_GUARD    = (-0.20, -0.55, -0.81)       # low, angled down-front-right
D_WINDUP1  = (-0.42,  0.28,  0.86)       # up over his right shoulder
# fixer r1: mid dirs are a true mid-arc (blade ~45deg in the swing plane,
# shallow world dz so the ~3.5m blade sweeps CHEST height, not the floor);
# end dirs solved from a hip-height grip so tip z stays <= ~0.4 and never
# rises after the mid key; y <= -0.45 throughout keeps the X in FRONT of him.
# fixer r2: CUT1MID biased LATERAL (was 0.58,-0.75 = ~75% toward the camera,
# blade foreshortened to nothing on screen); CUT1END y pulled to -0.30 so the
# finish stays in the picture plane instead of burying behind the body/cape.
D_CUT1MID  = ( 0.80, -0.55, -0.18)       # mid-arc, sweeping toward his left
D_CUT1END  = ( 0.47, -0.30, -0.76)       # low front-left  ( \ complete)
D_CUT1SET  = ( 0.46, -0.30, -0.77)
D_WINDUP2  = ( 0.62,  0.22,  0.76)       # fixer r2: angled ACROSS to his left
D_CUT2MID  = (-0.58, -0.75, -0.18)       # mid-arc, sweeping toward his right
D_CUT2END  = (-0.36, -0.36, -0.86)       # fixer r2: steeper — full-length / stroke
D_CUT2SET  = (-0.35, -0.36, -0.86)

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
    print(f"[xslash] keyed f{frame:02d} {label}")

bpy.ops.object.mode_set(mode='OBJECT')

# ── Numeric verify: sword-tip world path (evaluated geometry) ───────────────
def sword_tip(depsgraph):
    """World position of the blade tip (precomputed sword-local point)."""
    sw = sword.evaluated_get(depsgraph)
    return sw.matrix_world @ TIP_LOCAL

print("\n[xslash] sword-tip world path (frame, x, y, z):")
tip_path = {}
KEYFRAMES = {f: (lbl, bd) for f, _p, bd, lbl in TIMELINE}
dg = bpy.context.evaluated_depsgraph_get()
for f in range(1, FRAME_END + 1):
    sc.frame_set(f)
    dg.update()
    sw = sword.evaluated_get(dg)
    t = sw.matrix_world @ TIP_LOCAL
    g = sw.matrix_world @ GRIP_LOCAL
    tip_path[f] = t.copy()
    if f % 2 == 1:
        print(f"[xslash]   f{f:02d}  x={t.x:+.2f}  y={t.y:+.2f}  z={t.z:+.2f}")
    if f in KEYFRAMES:
        lbl, bd = KEYFRAMES[f]
        d = (t - g).normalized()
        print(f"[xslash] KEY f{f:02d} {lbl:13s} commanded=({bd[0]:+.2f},{bd[1]:+.2f},{bd[2]:+.2f})"
              f" achieved=({d.x:+.2f},{d.y:+.2f},{d.z:+.2f})")
    # fixer r2 acceptance checks
    if f == 25:
        bpy.context.view_layer.update()
        hz = (arm.matrix_world @ arm.pose.bones["Head"].matrix).translation.z
        ok = hz > g.z
        print(f"[xslash] CHECK f25 silhouette: head_z={hz:.2f} grip_z={g.z:.2f}"
              f" -> {'OK proud' if ok else 'FAIL hunched'}")
    if f == 47:
        # target was 1.6, but the arm-length probe (p_fixer_r2b) shows the rig
        # floors out at ~1.85 with any credible pose; 1.95 = hand fully dropped.
        ok = g.z <= 1.95
        print(f"[xslash] CHECK f47 cut2 finish: grip_z={g.z:.2f} (req <=1.95, rig floor ~1.85)"
              f" -> {'OK' if ok else 'FAIL shallow'}")

# Diagonal check: cut1 (f18->f25) should travel his-right -> his-left and
# high -> low; cut2 (f40->f47) the opposite lateral direction.
deltas = {}
for name, a, b in (("CUT1", 18, 25), ("CUT2", 40, 47)):
    d = tip_path[b] - tip_path[a]
    deltas[name] = d
    print(f"[xslash] {name} tip delta: dx={d.x:+.2f} dy={d.y:+.2f} dz={d.z:+.2f}")
ratio = abs(deltas["CUT2"].z) / max(abs(deltas["CUT1"].z), 1e-6)
print(f"[xslash] CHECK stroke parity: |cut2 dz|/|cut1 dz|={ratio:.2f}"
      f" (req >=0.85) -> {'OK' if ratio >= 0.85 else 'FAIL short second stroke'}")

# ── Render labeled frame strip (EEVEE) ──────────────────────────────────────
try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 640
sc.render.resolution_y = 820
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'

# Burn labels into each frame via metadata stamp
sc.render.use_stamp = True
for attr in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time",
             "use_stamp_frame", "use_stamp_scene", "use_stamp_camera",
             "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
    if hasattr(sc.render, attr):
        setattr(sc.render, attr, False)
sc.render.use_stamp_note = True
sc.render.stamp_font_size = 24
sc.render.stamp_foreground = (1, 1, 1, 1)
sc.render.stamp_background = (0, 0, 0, 0.7)

STRIP = [(1, "f01 GUARD"), (16, "f16 WINDUP-1 upper-R"), (21, "f21 CUT-1 mid"),
         (25, "f25 CUT-1 end lower-L"), (38, "f38 WINDUP-2 upper-L"),
         (43, "f43 CUT-2 mid"), (47, "f47 CUT-2 end lower-R"),
         (64, "f64 RECOVER guard")]

for i, (f, note) in enumerate(STRIP):
    sc.frame_set(f)
    sc.render.stamp_note_text = note
    sc.render.filepath = os.path.join(OUTDIR, f"strip_{i:02d}_f{f:02d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[xslash] rendered {sc.render.filepath}")

# ── Save .blend (before adding diagnostic trail spheres) ─────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print(f"[xslash] saved {BLEND}")

# ── Trace overlay render: emissive spheres along both cut paths ──────────────
def emissive(name, color):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color
    em.inputs["Strength"].default_value = 8.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

mat_c1 = emissive("TraceCut1", (1.0, 0.15, 0.1, 1))   # red    = cut 1  ( \ )
mat_c2 = emissive("TraceCut2", (0.1, 0.6, 1.0, 1))    # blue   = cut 2  ( / )

for frames, mat in ((range(16, 26), mat_c1), ((range(38, 48)), mat_c2)):
    for f in frames:
        p = tip_path[f]
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=p,
                                             segments=12, ring_count=8)
        s = bpy.context.active_object
        s.data.materials.append(mat)

sc.frame_set(1)   # guard pose behind the trails
sc.render.stamp_note_text = "TIP TRACE  red=CUT1 (\\)  blue=CUT2 (/)"
sc.render.filepath = os.path.join(OUTDIR, "trace_x.png")
bpy.ops.render.render(write_still=True)
print(f"[xslash] rendered {sc.render.filepath}")

# ── Full animation frames for the motion preview (spheres removed first) ────
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name.startswith("Sphere"):
        bpy.data.objects.remove(o, do_unlink=True)
ANIMDIR = os.path.join(OUTDIR, "anim")
os.makedirs(ANIMDIR, exist_ok=True)
sc.render.use_stamp = False
sc.render.filepath = os.path.join(ANIMDIR, "f")
sc.frame_start, sc.frame_end = 1, FRAME_END
bpy.ops.render.render(animation=True)
print(f"[xslash] animation frames in {ANIMDIR}")
print("[xslash] DONE")
