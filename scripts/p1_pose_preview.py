"""
Phase 1 pose-preview renderer (EEVEE, fast).

Applies strong test poses to the Godwyn rig and renders each to
/tmp/p1_<TAG>_<pose>.png so joint deformation can be critiqued.

Env:
  P1_SRC = "orig"  -> import models/godwyn_game.glb (baseline weights)
           "fixed" -> open models/godwyn_p1_weights.blend (default)
  P1_TAG = filename tag (default = P1_SRC)
  P1_CLOSEUP = "1" -> add close-up shots of shoulder/knee regions
"""
import bpy
import os
from math import radians
from mathutils import Vector, Matrix, Quaternion

SRC = os.environ.get("P1_SRC", "fixed")
TAG = os.environ.get("P1_TAG", SRC)
CLOSEUP = os.environ.get("P1_CLOSEUP", "0") == "1"

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_p1_weights.blend")

if SRC == "orig":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)
else:
    bpy.ops.wm.open_mainfile(filepath=BLEND)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
scene = bpy.context.scene

# ── engine: EEVEE (fallback names across versions) ───────────────────────────
eng_set = False
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        eng_set = True
        break
    except TypeError:
        continue
assert eng_set, "no EEVEE engine id worked"
print("engine:", scene.render.engine)
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
scene.render.resolution_x = 900
scene.render.resolution_y = 1200
scene.render.film_transparent = False

# ── lights + world ───────────────────────────────────────────────────────────
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.18, 0.18, 0.20, 1.0)
    bg.inputs[1].default_value = 1.0

def add_light(name, kind, loc, energy, size=3.0):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy
    if kind == "AREA":
        d.size = size
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    look_at(o, Vector((0, 0, 1.6)))
    return o

def look_at(obj, target):
    d = target - Vector(obj.location)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

key = bpy.data.lights.new("Key", "SUN"); key.energy = 4.0
ko = bpy.data.objects.new("Key", key); scene.collection.objects.link(ko)
ko.location = (3, -4, 5); look_at(ko, Vector((0, 0, 1.5)))
fill = bpy.data.lights.new("Fill", "AREA"); fill.energy = 600; fill.size = 5
fo = bpy.data.objects.new("Fill", fill); scene.collection.objects.link(fo)
fo.location = (-3.5, -3.5, 2.5); look_at(fo, Vector((0, 0, 1.5)))
rim = bpy.data.lights.new("Rim", "AREA"); rim.energy = 400; rim.size = 4
ro = bpy.data.objects.new("Rim", rim); scene.collection.objects.link(ro)
ro.location = (0.5, 4.5, 3.0); look_at(ro, Vector((0, 0, 1.8)))

cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 50
cam = bpy.data.objects.new("Cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam

# ── pose helpers ─────────────────────────────────────────────────────────────
def reset_pose():
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

def rot(bone_name, axis, deg):
    """Rotate pose bone about its own head, axis given in armature/world space."""
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        print("  !! missing bone", bone_name)
        return
    q = Quaternion(Vector(axis), radians(deg))
    M = pb.matrix.copy()
    T = Matrix.Translation(M.translation)
    pb.matrix = T @ q.to_matrix().to_4x4() @ T.inverted() @ M
    bpy.context.view_layer.update()

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

# character faces -Y; +X = character's left.
POSES = {
    # left arm raised laterally overhead + straighten elbow view
    "armraise": [
        ("LeftArm", Y, -140),
        ("LeftForeArm", Y, -20),
        ("RightArm", Y, 30),
    ],
    # right elbow hard bend, arm slightly out front
    "elbow": [
        ("RightArm", Y, 55),
        ("RightArm", X, -30),
        ("RightForeArm", X, -115),
        ("LeftArm", Y, -35),
    ],
    # deep leg step: left thigh forward, knee bent, right leg trailing
    "step": [
        ("Spine02", X, -12),
        ("LeftUpLeg", X, -75),
        ("LeftLeg", X, 85),
        ("RightUpLeg", X, 25),
        ("RightLeg", X, 15),
        ("LeftArm", Y, -25),
        ("RightArm", Y, 25),
    ],
    # isolated right elbow flex (arm stays at side -> cape stays put)
    "elbow2": [
        ("RightForeArm", X, -120),
    ],
    # left arm raised FORWARD (flexion) — avoids the lateral cape strip
    "punch": [
        ("LeftArm", X, -100),
        ("LeftForeArm", X, -25),
    ],
    # spine twist + neck turn
    "twist": [
        ("Spine02", Z, 22),
        ("Spine01", Z, 22),
        ("Spine", Z, 16),
        ("neck", Z, 18),
        ("Head", Z, 14),
        ("LeftArm", Y, -60),
        ("RightArm", Y, 60),
    ],
}

# camera setups per pose: (location, target)
CAMS = {
    "armraise": ((3.0, -5.2, 2.1), (0.2, 0, 1.9)),
    "elbow":    ((-2.6, -5.0, 1.9), (-0.2, 0, 1.7)),
    "elbow2":   ((-2.8, -4.6, 1.8), (-0.4, -0.3, 1.7)),
    "punch":    ((2.6, -4.8, 2.2), (0.3, -0.5, 2.0)),
    "step":     ((3.4, -4.8, 1.5), (0.1, 0, 1.3)),
    "twist":    ((2.8, -5.4, 2.0), (0, 0, 1.8)),
}

CLOSE_CAMS = {
    # (pose, camloc, target, lens)
    "armraise_shoulderL": ("armraise", (2.1, -3.2, 2.6), (0.35, -0.15, 2.55), 55),
    "elbow_elbowR":       ("elbow",    (-1.4, -3.4, 1.9), (-0.55, -0.55, 1.85), 55),
    "step_hipknee":       ("step",     (2.0, -2.4, 1.1), (0.25, -0.3, 1.0), 60),
    "elbow2_forearmR":    ("elbow2",   (-1.6, -2.6, 1.9), (-0.5, -0.45, 1.8), 60),
    "punch_shoulderL":    ("punch",    (1.8, -2.8, 2.5), (0.3, -0.4, 2.4), 60),
    "twist_neck":         ("twist",    (1.5, -2.2, 2.9), (0, -0.15, 2.75), 70),
}

def render(path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)

for pose_name, steps in POSES.items():
    reset_pose()
    for bone, axis, deg in steps:
        rot(bone, axis, deg)
    loc, tgt = CAMS[pose_name]
    cam.location = loc
    look_at(cam, Vector(tgt))
    cam_d.lens = 50
    render(f"/tmp/p1_{TAG}_{pose_name}.png")

if CLOSEUP:
    for shot, (pose_name, loc, tgt, lens) in CLOSE_CAMS.items():
        reset_pose()
        for bone, axis, deg in POSES[pose_name]:
            rot(bone, axis, deg)
        cam.location = loc
        look_at(cam, Vector(tgt))
        cam_d.lens = lens
        render(f"/tmp/p1_{TAG}_close_{shot}.png")

print("=== p1_pose_preview DONE ===")
