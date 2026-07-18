"""
Phase 4 EEVEE Motion Preview
Renders 4 frames showing Godwyn in walk/swing poses from godwyn_p2_robe.blend
using manual pose posing since no animation data exists yet.
Output: renders/game/phase4_preview_f{01-04}.png
"""
import bpy
import os
import math

BLEND_MAIN  = "/home/aaron/godwyn-boss-fight/models/godwyn_p2_robe.blend"
OUT_DIR     = "/home/aaron/godwyn-boss-fight/renders/game/"
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND_MAIN)

# ── Scene / render settings ──────────────────────────────────────────────────
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 512
scene.render.resolution_y = 768
scene.render.film_transparent = False
scene.eevee.taa_render_samples = 16

# ── Camera ───────────────────────────────────────────────────────────────────
cam_data = bpy.data.cameras.new("PreviewCam")
cam_obj  = bpy.data.objects.new("PreviewCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.location = (3.0, -3.5, 1.6)
import mathutils
cam_obj.rotation_euler = mathutils.Euler((math.radians(80), 0, math.radians(45)), 'XYZ')
cam_data.lens = 50

# ── Key light ────────────────────────────────────────────────────────────────
sun_data = bpy.data.lights.new("Sun", type='SUN')
sun_data.energy = 3.0
sun_obj = bpy.data.objects.new("Sun", sun_data)
scene.collection.objects.link(sun_obj)
sun_obj.location = (5, -5, 8)
sun_obj.rotation_euler = mathutils.Euler((math.radians(50), 0, math.radians(-30)), 'XYZ')

fill_data = bpy.data.lights.new("Fill", type='AREA')
fill_data.energy = 200
fill_obj = bpy.data.objects.new("Fill", fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (-4, 2, 3)

# ── World background ─────────────────────────────────────────────────────────
world = bpy.data.worlds.new("World")
world.use_nodes = True
scene.world = world
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = (0.05, 0.05, 0.07, 1.0)
    bg_node.inputs[1].default_value = 1.0

# ── Armature ─────────────────────────────────────────────────────────────────
arm_obj = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm_obj is None:
    print("ERROR: no armature"); import sys; sys.exit(1)

# Helper: set pose bone rotation (Euler XYZ in degrees)
def pose_bone_rot(arm, bone_name, x=0, y=0, z=0):
    pb = arm.pose.bones.get(bone_name)
    if pb:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = mathutils.Euler(
            (math.radians(x), math.radians(y), math.radians(z)), 'XYZ')

def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)

def render_frame(filename, label=""):
    scene.render.filepath = os.path.join(OUT_DIR, filename)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered: {filename}  ({label})")

# ── FRAME 1: Rest / T-pose ───────────────────────────────────────────────────
reset_pose(arm_obj)
render_frame("phase4_preview_f01_rest.png", "rest pose")

# ── FRAME 2: Walk stride left ────────────────────────────────────────────────
reset_pose(arm_obj)
# Hip lean forward
pose_bone_rot(arm_obj, 'Hips', x=-5, y=0, z=0)
# Spine curve
pose_bone_rot(arm_obj, 'Spine', x=5, y=0, z=2)
pose_bone_rot(arm_obj, 'Spine01', x=4, y=0, z=1)
# Left leg forward stride
pose_bone_rot(arm_obj, 'LeftUpLeg', x=-35, y=0, z=0)
pose_bone_rot(arm_obj, 'LeftLeg', x=15, y=0, z=0)
# Right leg back stride
pose_bone_rot(arm_obj, 'RightUpLeg', x=25, y=0, z=0)
pose_bone_rot(arm_obj, 'RightLeg', x=-10, y=0, z=0)
# Arm swing
pose_bone_rot(arm_obj, 'LeftArm', x=30, y=0, z=-15)
pose_bone_rot(arm_obj, 'RightArm', x=-25, y=0, z=15)
render_frame("phase4_preview_f02_walk.png", "walk stride")

# ── FRAME 3: Sword raise / overhead swing ────────────────────────────────────
reset_pose(arm_obj)
# Spine twist right
pose_bone_rot(arm_obj, 'Spine', x=0, y=0, z=-15)
pose_bone_rot(arm_obj, 'Spine01', x=-8, y=0, z=-12)
pose_bone_rot(arm_obj, 'Spine02', x=-5, y=0, z=-10)
# Right arm raised (sword arm)
pose_bone_rot(arm_obj, 'RightShoulder', x=0, y=0, z=20)
pose_bone_rot(arm_obj, 'RightArm', x=-80, y=-20, z=30)
pose_bone_rot(arm_obj, 'RightForeArm', x=0, y=-30, z=0)
# Left arm guard
pose_bone_rot(arm_obj, 'LeftShoulder', x=0, y=0, z=-15)
pose_bone_rot(arm_obj, 'LeftArm', x=-20, y=10, z=-10)
pose_bone_rot(arm_obj, 'LeftForeArm', x=0, y=20, z=0)
# Stance
pose_bone_rot(arm_obj, 'LeftUpLeg', x=-10, y=0, z=15)
pose_bone_rot(arm_obj, 'RightUpLeg', x=10, y=0, z=-20)
render_frame("phase4_preview_f03_swing.png", "overhead swing")

# ── FRAME 4: Half-turn 3/4 view swing follow-through ─────────────────────────
reset_pose(arm_obj)
# Camera reposition for 3/4 back view
cam_obj.location = (-3.0, -3.0, 1.5)
cam_obj.rotation_euler = mathutils.Euler((math.radians(78), 0, math.radians(-45)), 'XYZ')
# Swing follow-through
pose_bone_rot(arm_obj, 'Spine', x=5, y=0, z=25)
pose_bone_rot(arm_obj, 'Spine01', x=5, y=0, z=20)
pose_bone_rot(arm_obj, 'Spine02', x=3, y=0, z=15)
# Right arm swept forward/down
pose_bone_rot(arm_obj, 'RightShoulder', x=0, y=0, z=10)
pose_bone_rot(arm_obj, 'RightArm', x=20, y=20, z=40)
pose_bone_rot(arm_obj, 'RightForeArm', x=0, y=-15, z=0)
# Left arm balance
pose_bone_rot(arm_obj, 'LeftArm', x=-15, y=-10, z=-25)
# Robe phys chain drape hint — tilt the robe root chains slightly
for col in ('C', 'L', 'R'):
    bn = f'phys_robe_back_{col}_00'
    pose_bone_rot(arm_obj, bn, x=8, y=0, z=0)
    bn2 = f'phys_robe_front_{col}_00'
    pose_bone_rot(arm_obj, bn2, x=-4, y=0, z=0)
# Cape flow
for i in range(7):
    pose_bone_rot(arm_obj, f'phys_cape_C_{i:02d}', x=-(i*4), y=0, z=0)
    pose_bone_rot(arm_obj, f'phys_cape_L_{i:02d}', x=-(i*3), y=0, z=10)
    pose_bone_rot(arm_obj, f'phys_cape_R_{i:02d}', x=-(i*3), y=0, z=-10)
render_frame("phase4_preview_f04_followthru.png", "swing follow-through + robe drape")

print("All 4 preview frames rendered.")
