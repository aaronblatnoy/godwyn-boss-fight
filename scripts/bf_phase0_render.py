"""
Boss Fight Phase 0 — EEVEE test render: pose right arm and confirm sword follows.
"""
import bpy, os, math
from mathutils import Euler

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
OUT = os.path.expanduser("~/godwyn-boss-fight/renders/bf_phase0_sword_test.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ── Clear & import ───────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arm_obj = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
sword   = bpy.data.objects.get("Godwyn_Sword")

print(f"Armature: {arm_obj.name if arm_obj else 'MISSING'}")
print(f"Sword parent: {sword.parent.name if sword and sword.parent else 'MISSING'}")
sword_pb = sword.parent_bone if sword else 'MISSING'
print(f"Sword parent_bone: {sword_pb}")

# ── Lighting ─────────────────────────────────────────────────────────────────
bpy.ops.object.light_add(type='SUN', location=(4, -6, 10))
sun = bpy.context.active_object
sun.data.energy = 6.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(30)), 'XYZ')

# Fill light
bpy.ops.object.light_add(type='AREA', location=(-3, -4, 4))
fill = bpy.context.active_object
fill.data.energy = 200
fill.data.size = 3

# ── Camera — side view to see torso and raised right arm + sword ─────────────
# Character is ~3m tall. Upper body is between Z=1.5 and Z=2.8
# Place camera to the right and slightly in front, aimed at chest height
bpy.ops.object.camera_add(location=(3.5, -3.0, 2.2))
cam = bpy.context.active_object
# Aim camera at roughly chest/arm area: looking slightly left and down
import mathutils
cam_target = mathutils.Vector((0.0, 0.0, 2.0))
cam_pos    = mathutils.Vector((3.5, -3.0, 2.2))
direction   = cam_target - cam_pos
rot_quat    = direction.to_track_quat('-Z', 'Y')
cam.rotation_euler = rot_quat.to_euler()
bpy.context.scene.camera = cam

# ── Pose: right arm swings sword up-and-forward ──────────────────────────────
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')

swing_poses = [
    # Bone name,          X deg,  Y deg,  Z deg
    ("RightShoulder",      0,      0,      -15),  # pull shoulder back
    ("RightArm",         -80,      0,      -40),  # raise upper arm high
    ("RightForeArm",     -30,     25,        0),  # extend forearm
    ("RightHand",        -10,      0,       10),  # wrist angle
    ("Spine02",            8,      0,        0),  # lean forward from chest
    ("Spine01",            5,      0,        0),
    ("Hips",               5,      0,        0),  # hip coil
]

for bone_name, rx, ry, rz in swing_poses:
    pb = arm_obj.pose.bones.get(bone_name)
    if pb:
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler = Euler([math.radians(a) for a in (rx, ry, rz)], 'XYZ')
        pb.keyframe_insert(data_path='rotation_euler', frame=1)
        print(f"  Posed: {bone_name} ({rx}, {ry}, {rz})")
    else:
        print(f"  MISS:  {bone_name}")

bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# ── Render (EEVEE) ────────────────────────────────────────────────────────────
scene = bpy.context.scene

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT
scene.frame_set(1)

print(f"Rendering with engine: {scene.render.engine}")
print(f"Output: {OUT}")
bpy.ops.render.render(write_still=True)
print("RENDER COMPLETE")
