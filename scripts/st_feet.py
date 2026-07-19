"""
st_feet.py — Boss-fight Phase 2: FEET. Fix outward toe splay.

Ground truth (st_feet_probe.py on godwyn_st_sword.blend):
  - Character faces -Y. Toe bones (rest, world XY dir):
      LeftToeBase  ~(+0.34, -0.94) -> ~20 deg splayed OUT
      RightToeBase ~(-0.39, -0.92) -> ~23 deg splayed OUT
  - Leg/foot pose bones are all identity (arm pose from st_sword untouched).
  - Rig: 121 bones = 24 Mixamo + 97 phys_* chains. NEVER add/remove/rename.
  - Fix = POSE-space world-Z yaw on LeftFoot/RightFoot about the ankle
    (toe bones ride along as children). No mesh/vertex edits, no weights,
    no UVs, no materials touched. Face/upper body untouched.

Target: slight natural out-toe of TARGET_OUT_DEG per side (0 = dead forward).

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/st_feet.py 2>&1
"""
import bpy
import os
import math
from mathutils import Vector, Matrix

REPO = os.path.expanduser("~/godwyn-boss-fight")
BLEND_IN = os.path.join(REPO, "models", "godwyn_st_sword.blend")
BLEND_OUT = os.path.join(REPO, "models", "godwyn_st_feet.blend")
OUT = "/tmp/st_feet"
os.makedirs(OUT, exist_ok=True)

# ── TUNABLES ───────────────────────────────────────────────────────────────
TARGET_OUT_DEG = 6.0     # desired outward toe angle per foot (natural stance)
EXTRA = dict(LeftFoot=0.0, RightFoot=0.0)  # per-foot manual trim (deg, +out)

bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
char1 = bpy.data.objects["char1"]
n_bones0 = len(arm.data.bones)
n_vg0 = len(char1.vertex_groups)
n_phys0 = sum(1 for b in arm.data.bones if b.name.startswith("phys_"))
print(f"[IN] bones={n_bones0} (phys={n_phys0}) vgroups={n_vg0}")

bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
pbs = arm.pose.bones


def toe_world_dir(side):
    """World XY direction of the toe bone under current pose."""
    pb = pbs[side + "ToeBase"]
    d = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head)
    d.z = 0.0
    return d.normalized()


def yaw_from_forward(d):
    """Signed angle (deg) of XY dir d from forward (-Y). + = toward +X."""
    return math.degrees(math.atan2(d.x, -d.y))


def rotate_foot_world_z(side, deg):
    """Yaw the whole foot (Foot bone, toe rides along) about the ankle, world Z."""
    pb = pbs[side + "Foot"]
    head_w = arm.matrix_world @ pb.head
    R = (Matrix.Translation(head_w)
         @ Matrix.Rotation(math.radians(deg), 4, 'Z')
         @ Matrix.Translation(-head_w))
    pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
    bpy.context.view_layer.update()


for side, out_sign in (("Left", +1.0), ("Right", -1.0)):
    d0 = toe_world_dir(side)
    yaw0 = yaw_from_forward(d0)                       # +x-ward angle
    target = out_sign * (TARGET_OUT_DEG + EXTRA[side + "Foot"])
    delta = target - yaw0
    print(f"[{side}] toe yaw {yaw0:+.1f} deg -> target {target:+.1f}, rotating {delta:+.1f}")
    rotate_foot_world_z(side, delta)
    d1 = toe_world_dir(side)
    print(f"[{side}] after: toe yaw {yaw_from_forward(d1):+.1f} deg")

bpy.ops.object.mode_set(mode='OBJECT')

# ── VERIFY RIG/MAT INTACT ─────────────────────────────────────────────────
assert len(arm.data.bones) == n_bones0, "bone count changed!"
assert sum(1 for b in arm.data.bones if b.name.startswith("phys_")) == n_phys0, "phys chains changed!"
assert len(char1.vertex_groups) == n_vg0, "vgroups changed!"
imgs = [i.name for i in bpy.data.images if i.size[0] > 0]
print(f"[RIG OK] bones={len(arm.data.bones)} vgroups={len(char1.vertex_groups)} images={imgs}")

# ── SAVE ───────────────────────────────────────────────────────────────────
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
print(f"[SAVED] {BLEND_OUT}")

# ── RENDERS (EEVEE) ────────────────────────────────────────────────────────
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.view_settings.view_transform = 'Filmic'
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.03, 0.03, 0.035, 1)
scene.world = world
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.data.color = (1.0, 0.92, 0.6)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), 0, math.radians(-140))
scene.collection.objects.link(fill)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
scene.collection.objects.link(cam)
scene.camera = cam


def shoot(name, target, dist, elev, azim, lens=50):
    cam.data.lens = lens
    el, a = math.radians(elev), math.radians(azim)
    off = Vector((dist * math.cos(el) * math.sin(a),
                  -dist * math.cos(el) * math.cos(a),
                  dist * math.sin(el)))
    cam.location = target + off
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print(f"  wrote {scene.render.filepath}")


feet_c = Vector((0.0, -0.30, 0.12))
shoot("f_full_front.png", Vector((0, 0, 1.6)), 8.0, 5, 0, 35)
shoot("f_feet_front.png", feet_c, 2.2, 8, 0, 55)
shoot("f_feet_low3q.png", feet_c, 2.4, 4, -35, 55)
shoot("f_feet_top.png", Vector((0.0, -0.35, 0.05)), 2.6, 70, 0, 45)
print("ST_FEET DONE")
