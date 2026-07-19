"""
Phase 2 preview harness — EEVEE renders of godwyn_p2_robe.blend.

Modes (env P2_MODE):
  rest  — rest pose, front/side/3q            -> /tmp/p2_rest_*.png
  step  — walking step + torso turn, NO chain rotation (cloth must hang
          from waist/chest/head and NOT stretch with the legs)
                                              -> /tmp/p2_step_*.png
  sway  — step pose + physics-chain sway (robe swings back, cape billows,
          hair swings)                        -> /tmp/p2_sway_*.png
"""
import bpy
import os
import math
from math import radians
from mathutils import Matrix, Vector

MODE = os.environ.get("P2_MODE", "rest")
BLEND = os.path.expanduser(os.environ.get(
    "P2_OUT", "~/godwyn-boss-fight/models/godwyn_p2_robe.blend"))
bpy.ops.wm.open_mainfile(filepath=BLEND)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
scene = bpy.context.scene

# ── EEVEE setup ─────────────────────────────────────────────────────────────
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
scene.render.resolution_x = 900
scene.render.resolution_y = 1200
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.015, 0.013, 0.011, 1.0)
    bg.inputs[1].default_value = 1.0

def add_sun(name, rot, energy):
    d = bpy.data.lights.new(name, "SUN")
    d.energy = energy
    d.angle = 0.4
    o = bpy.data.objects.new(name, d)
    o.rotation_euler = rot
    scene.collection.objects.link(o)

add_sun("Key", (radians(55), 0, radians(35)), 4.0)
add_sun("Fill", (radians(70), 0, radians(-120)), 1.5)
add_sun("Rim", (radians(-60), 0, radians(180)), 2.0)

cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 60
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

def look_at(obj, target):
    d = target - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

TARGET = Vector((0, 0, 1.55))
VIEWS = {  # front = -Y
    "front": Vector((0.0, -7.5, 1.7)),
    "side": Vector((7.5, 0.0, 1.7)),
    "3q": Vector((5.0, -5.6, 1.9)),
}

# ── posing helpers ──────────────────────────────────────────────────────────
def rot_world(name, axis, deg):
    """Rotate pose bone about a WORLD axis through its own head."""
    pb = arm.pose.bones[name]
    head = (arm.matrix_world @ pb.matrix).translation
    R = (Matrix.Translation(head) @ Matrix.Rotation(radians(deg), 4, axis)
         @ Matrix.Translation(-head))
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()

def pose_step():
    # Front is -Y: negative world-X rotation swings a limb forward.
    rot_world("LeftUpLeg", "X", -32)     # left leg stepping forward
    rot_world("LeftLeg", "X", 14)        # knee bend
    rot_world("RightUpLeg", "X", 18)     # right leg trailing back
    rot_world("Spine", "Z", 18)          # torso turn
    rot_world("Head", "Z", 22)           # head turn further
    rot_world("LeftArm", "X", 20)
    rot_world("RightArm", "X", -18)

def pose_sway():
    # Rotate the new physics chains as spring-bone physics would:
    # robe trails the step, cape billows back (+Y), hair swings.
    sway = {
        "phys_robe_front_L": ("X", -6),   # front panels kick forward
        "phys_robe_front_R": ("X", -5),
        "phys_robe_side_L": ("Y", -4),
        "phys_robe_side_R": ("Y", 4),
        "phys_robe_back": ("X", 4),       # back skirt trails
        "phys_cape_L": ("X", 5),          # cape billows backward
        "phys_cape_C": ("X", 6),
        "phys_cape_R": ("X", 5),
        "phys_hair_front_L": ("X", -7),
        "phys_hair_front_R": ("X", -7),
        "phys_hair_back": ("X", 8),
    }
    for pb in arm.pose.bones:
        for chain, (axis, deg) in sway.items():
            if pb.name.startswith(chain + "_"):
                rot_world(pb.name, axis, deg)  # per-link -> curls the chain

if MODE in ("step", "sway"):
    pose_step()
if MODE == "sway":
    pose_sway()

# ── render ──────────────────────────────────────────────────────────────────
for vname, loc in VIEWS.items():
    cam.location = loc
    look_at(cam, TARGET)
    scene.render.filepath = f"/tmp/p2_{MODE}_{vname}.png"
    bpy.ops.render.render(write_still=True)
    print(f"[ok] wrote {scene.render.filepath}")
print("=== PREVIEW DONE ===")
