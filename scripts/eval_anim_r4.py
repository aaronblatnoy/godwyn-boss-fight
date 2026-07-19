"""
Movement-eval round 4 — animation frames from godwyn_p2_robe.blend.

1. Opens models/godwyn_p2_robe.blend (24 body bones + 44 phys_* chain bones).
2. Imports the animation from models/godwyn_sword_judgment.glb (same Mixamo
   bone names) and retargets its action onto the p2 armature.
   Fallback: keyframes a simple walk + sword swing directly.
3. Layers procedural spring-style sway onto the phys_robe/cape/hair chains
   (per-link sine offsets — approximates what Godot spring bones will do).
4. Renders 4 frames across the motion, 3q + side view each, EEVEE,
   to /tmp/eval_anim_r4_f<frame>_<view>.png
"""
import bpy
import os
import math
from math import radians, sin, pi
from mathutils import Vector, Matrix, Quaternion

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_p2_robe.blend")
ANIM_GLB = os.path.expanduser(
    "~/godwyn-boss-fight/models/godwyn_sword_judgment.glb")

bpy.ops.wm.open_mainfile(filepath=BLEND)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
scene = bpy.context.scene
print(f"[open] armature '{arm.name}' bones={len(arm.data.bones)}")

body_bones = {b.name for b in arm.data.bones if not b.name.startswith("phys_")}
phys_bones = [b.name for b in arm.data.bones if b.name.startswith("phys_")]
print(f"[rig] body={len(body_bones)} phys={len(phys_bones)}")

# ── 1. bring in the animation ───────────────────────────────────────────────
pre_objs = set(bpy.data.objects)
pre_acts = set(bpy.data.actions)
action = None
try:
    bpy.ops.import_scene.gltf(filepath=ANIM_GLB)
    new_objs = [o for o in bpy.data.objects if o not in pre_objs]
    new_acts = [a for a in bpy.data.actions if a not in pre_acts]
    print(f"[import] objs={len(new_objs)} actions={[a.name for a in new_acts]}")
    # pick the action with the longest frame range
    cands = [a for a in new_acts if a.frame_range[1] > a.frame_range[0] + 1]
    if cands:
        action = max(cands, key=lambda a: a.frame_range[1] - a.frame_range[0])
        action.use_fake_user = True
    # verify the action's fcurve bone paths exist on our rig
    if action:
        import re
        refs = set()
        fcs = []
        if hasattr(action, "fcurves") and action.fcurves is not None:
            fcs = list(action.fcurves)
        else:  # Blender 4.4+/5.x layered actions
            for layer in action.layers:
                for strip in layer.strips:
                    for cb in strip.channelbags:
                        fcs.extend(cb.fcurves)
        for fc in fcs:
            m = re.match(r'pose\.bones\["([^"]+)"\]', fc.data_path)
            if m:
                refs.add(m.group(1))
        missing = refs - {b.name for b in arm.data.bones}
        print(f"[anim] '{action.name}' range={tuple(action.frame_range)} "
              f"bones_ref={len(refs)} missing_on_rig={sorted(missing)[:6]}")
        if refs and len(missing) > len(refs) * 0.3:
            print("[anim] too many missing bones — falling back to keyframes")
            action = None
except Exception as e:
    print("[import] FAILED:", e)
finally:
    # remove imported scene objects (keep only the action)
    for o in [o for o in bpy.data.objects if o not in pre_objs]:
        bpy.data.objects.remove(o, do_unlink=True)
    print("[cleanup] scene objects now:",
          [o.name for o in bpy.data.objects if o.type in ("ARMATURE", "MESH")])

def rot_key(name, axis, deg, frame):
    """Additive world-axis rotation about the bone head, keyed at frame."""
    pb = arm.pose.bones.get(name)
    if pb is None:
        print("  !! missing bone", name)
        return
    q = Quaternion(Vector(axis), radians(deg))
    M = pb.matrix.copy()
    T = Matrix.Translation(M.translation)
    pb.matrix = T @ q.to_matrix().to_4x4() @ T.inverted() @ M
    bpy.context.view_layer.update()
    pb.keyframe_insert("rotation_quaternion", frame=frame)
    pb.keyframe_insert("location", frame=frame)

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

if action is not None:
    arm.animation_data_create()
    arm.animation_data.action = action
    try:  # Blender 4.4+/5.x slotted actions
        if action.slots:
            arm.animation_data.action_slot = action.slots[0]
    except Exception as e:
        print("[slot] note:", e)
    f0, f1 = action.frame_range
    frames = [int(f0 + (f1 - f0) * t) for t in (0.10, 0.38, 0.65, 0.92)]
    TAG = "glbanim"
else:
    # fallback: keyframe walk step -> sword swing (front = -Y)
    def clear():
        for pb in arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    # frame 1: neutral guard
    clear()
    for n in ("Hips", "Spine", "LeftUpLeg", "RightUpLeg", "LeftArm",
              "RightArm", "Head"):
        rot_key(n, X, 0, 1)
    # frame 10: left step forward, sword low behind (windup)
    clear()
    rot_key("LeftUpLeg", X, -35, 10); rot_key("LeftLeg", X, 20, 10)
    rot_key("RightUpLeg", X, 18, 10)
    rot_key("Spine", Z, -20, 10); rot_key("Spine01", Z, -10, 10)
    rot_key("RightArm", X, 45, 10); rot_key("RightForeArm", X, 25, 10)
    rot_key("LeftArm", X, -15, 10); rot_key("Head", Z, 15, 10)
    # frame 20: right step, sword swinging across (contact)
    clear()
    rot_key("RightUpLeg", X, -38, 20); rot_key("RightLeg", X, 22, 20)
    rot_key("LeftUpLeg", X, 20, 20)
    rot_key("Spine", Z, 30, 20); rot_key("Spine01", Z, 15, 20)
    rot_key("RightArm", X, -95, 20); rot_key("RightForeArm", X, -15, 20)
    rot_key("RightArm", Z, 35, 20)
    rot_key("LeftArm", X, 25, 20); rot_key("Head", Z, -10, 20)
    # frame 30: follow-through, torso wound around
    clear()
    rot_key("RightUpLeg", X, -10, 30); rot_key("LeftUpLeg", X, -25, 30)
    rot_key("LeftLeg", X, 30, 30)
    rot_key("Spine", Z, 45, 30); rot_key("Spine01", Z, 20, 30)
    rot_key("RightArm", X, -60, 30); rot_key("RightArm", Z, 70, 30)
    rot_key("LeftArm", X, 10, 30)
    frames = [1, 10, 20, 30]
    TAG = "keyed"

print(f"[frames] {TAG}: sampling {frames}")

# ── 2. procedural spring sway + GRAVITY DRAPE on phys chains ────────────────
# FIXER R3: r2 aimed EVERY link at the same world -Z target with a large K —
# under strong torso pitch all links snapped toward the same direction (flat
# board cape at f011, tangled collapse at f097). Now the bend is DISTRIBUTED:
# each link rotates only a per-link FRACTION of its remaining angle-to-down
# (fraction grows toward the hem), so the sheet bends as an ARC; and every
# link's total applied rotation (drape + sway) is HARD-CLAMPED to +/-35deg
# from its parent — no link can fold back through the body or its neighbor.
CHAIN_AMP = {"phys_robe": 5.0, "phys_cape": 6.0, "phys_hair": 6.0}
# R3b: at f097 (horizontal torso pitch) K=0.22 left the skirt a hips-locked
# tube engulfing the body from the side view — gravity must dominate under
# extreme pitch. Larger K is near-invisible at standing frames (angle-to-down
# is already ~0) but swings the whole shell toward world-down mid-leap.
# R3b2: 0.45/0.58 OVERSWEPT at f097 (accumulated ~35deg/link curled the
# skirt into shard tangles); 0.22/0.40 undershot (hips-locked tube). Middle.
DRAPE_K = {"phys_robe": 0.30, "phys_cape": 0.46, "phys_hair": 0.28}
CLAMP = radians(26.0)   # R3b3: 35 still let link stacks fold into shards at
                        # f097; 26/link (~max 208deg over 8) keeps arcs open
N_LINKS = {}
for _name in phys_bones:
    _base = _name.rsplit("_", 1)[0]
    N_LINKS[_base] = N_LINKS.get(_base, 0) + 1

def apply_sway(frame, span):
    t = (frame - span[0]) / max(1.0, span[1] - span[0])
    # reset phys pose (drape must not accumulate across sampled frames)
    for name in phys_bones:
        arm.pose.bones[name].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    inv3 = arm.matrix_world.inverted().to_3x3()
    down = (inv3 @ Vector((0, 0, -1))).normalized()
    # alphabetical order = chain-link order, so parents rotate before children
    for name in sorted(phys_bones):
        pb = arm.pose.bones[name]
        base = name.rsplit("_", 1)[0]
        link = int(name.rsplit("_", 1)[1])
        n = N_LINKS[base]
        fam = next((k for k in CHAIN_AMP if name.startswith(k)), "phys_robe")
        amp = CHAIN_AMP[fam]
        # per-link fraction of the remaining angle-to-down; grows toward the
        # hem so the rotation accumulates down the chain into a curved fold
        frac = DRAPE_K[fam] * (0.35 + 0.65 * (link + 1) / n)
        d = (pb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
        q = Quaternion()
        axis = d.cross(down)
        if axis.length > 1e-5:
            q = Quaternion(axis.normalized(), d.angle(down) * frac)
        # trailing sine wave layered on the drape
        ang = amp * (0.6 + 0.12 * link) * sin(2 * pi * (t * 1.5) - link * 0.7)
        side = 0.3 * amp * sin(2 * pi * t * 1.5 + hash(base) % 7 - link * 0.5)
        qs = (Quaternion(Vector((1, 0, 0)), radians(ang))
              @ Quaternion(Vector((0, 0, 1)), radians(side)))
        qt = qs @ q
        if qt.w < 0:
            qt.negate()                  # canonical form: angle in [0, pi]
        # HARD CLAMP: total per-link deviation from its parent <= 35 deg
        if qt.angle > CLAMP:
            qt = Quaternion(qt.axis, CLAMP)
        T = Matrix.Translation(pb.matrix.translation)
        pb.matrix = T @ qt.to_matrix().to_4x4() @ T.inverted() @ pb.matrix
        bpy.context.view_layer.update()

# ── 3. EEVEE + lights + cams ────────────────────────────────────────────────
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print("engine:", scene.render.engine)
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
scene.render.resolution_x = 900
scene.render.resolution_y = 1200
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.10, 0.10, 0.12, 1.0)
    bg.inputs[1].default_value = 1.0

def look_at(obj, target):
    d = target - Vector(obj.location)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

def sun(name, loc, energy):
    d = bpy.data.lights.new(name, "SUN"); d.energy = energy; d.angle = 0.5
    o = bpy.data.objects.new(name, d); scene.collection.objects.link(o)
    o.location = loc; look_at(o, Vector((0, 0, 1.5)))

sun("Key", (3, -4, 6), 4.0)
sun("Fill", (-4, -3, 3), 1.6)
sun("Rim", (0.5, 5, 4), 2.2)

cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 55
cam = bpy.data.objects.new("Cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam

VIEWS = {"3q": Vector((4.6, -5.2, 2.0)), "side": Vector((6.8, 0.6, 1.8))}
TARGET = Vector((0, 0, 1.45))

# FIXER R2: the Sword_Judgment clip carries strong ROOT MOTION but the camera
# was static, so dynamic frames were half out of frame. Track the Hips world
# translation each sampled frame and offset TARGET + camera by it.
rest_hips_w = (arm.matrix_world @ arm.data.bones["Hips"].head_local).copy()
span = (frames[0], frames[-1])
for f in frames:
    scene.frame_set(f)
    apply_sway(f, span)
    hips_now = (arm.matrix_world @ arm.pose.bones["Hips"].matrix).translation
    off = hips_now - rest_hips_w
    print(f"[track] f{f:03d} hips offset {tuple(round(c, 2) for c in off)}")
    for vname, loc in VIEWS.items():
        cam.location = loc + off
        look_at(cam, TARGET + off)
        scene.render.filepath = f"/tmp/eval_anim_r4_f{f:03d}_{vname}.png"
        bpy.ops.render.render(write_still=True)
        print("[render]", scene.render.filepath)

print(f"=== EVAL_ANIM_R4 DONE ({TAG}) ===")
