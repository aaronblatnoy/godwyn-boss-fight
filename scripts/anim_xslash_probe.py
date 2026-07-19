"""
anim_xslash_probe.py — static pose candidates to find blade orientations
for WINDUP2 (blade must point UP-LEFT), GUARD (blade visible low-front),
and CUT1_MID (blade lateral, not at camera).
"""
import bpy, os, math
from mathutils import Euler, Vector

REPO   = os.path.expanduser("~/godwyn-boss-fight")
GLB    = os.path.join(REPO, "models", "godwyn_game.glb")
OUTDIR = os.path.join(REPO, "renders", "xslash", "probe")
os.makedirs(OUTDIR, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')

sc = bpy.context.scene
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
bpy.ops.object.light_add(type='SUN', location=(4, -6, 10))
sun = bpy.context.active_object
sun.data.energy = 6.0
sun.rotation_euler = Euler((math.radians(50), 0, math.radians(30)), 'XYZ')
bpy.ops.object.light_add(type='AREA', location=(-3, -5, 4))
fill = bpy.context.active_object
fill.data.energy = 300
fill.data.size = 4
bpy.ops.object.camera_add(location=(3.4, -6.6, 2.2))
cam = bpy.context.active_object
cam.rotation_euler = (Vector((0, 0, 1.6)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam

try:
    sc.render.engine = 'BLENDER_EEVEE'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 480
sc.render.resolution_y = 600
sc.render.image_settings.file_format = 'PNG'
sc.render.use_stamp = True
for attr in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time",
             "use_stamp_frame", "use_stamp_scene", "use_stamp_camera",
             "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
    if hasattr(sc.render, attr):
        setattr(sc.render, attr, False)
sc.render.use_stamp_note = True
sc.render.stamp_font_size = 20
sc.render.stamp_background = (0, 0, 0, 0.7)

for pb in arm.pose.bones:
    pb.rotation_mode = 'XYZ'

def set_pose(pose):
    for pb in arm.pose.bones:
        pb.rotation_euler = Euler((0, 0, 0), 'XYZ')
    for n, (rx, ry, rz) in pose.items():
        pb = arm.pose.bones.get(n)
        if pb:
            pb.rotation_euler = Euler((math.radians(rx), math.radians(ry),
                                       math.radians(rz)), 'XYZ')
    bpy.context.view_layer.update()

SPINE_L = {"Spine": (0, 0, 18), "Spine01": (0, 0, 10), "Hips": (0, 0, 6)}

CANDS = {
    # WINDUP2: arm raised across to his LEFT, blade must point UP
    "w2_A": dict(SPINE_L, **{"RightShoulder": (0, 0, 16),
        "RightArm": (-65, 0, 60), "RightForeArm": (-45, 0, 0),
        "RightHand": (-20, 0, -10)}),
    "w2_B": dict(SPINE_L, **{"RightShoulder": (0, 0, 16),
        "RightArm": (-65, 40, 60), "RightForeArm": (-30, -28, 0),
        "RightHand": (-12, 0, -14)}),
    "w2_C": dict(SPINE_L, **{"RightShoulder": (0, 0, 16),
        "RightArm": (-80, 0, 45), "RightForeArm": (-20, -50, 0),
        "RightHand": (-30, 0, 0)}),
    "w2_D": dict(SPINE_L, **{"RightShoulder": (0, 0, 16),
        "RightArm": (-65, -40, 60), "RightForeArm": (-30, 20, 0),
        "RightHand": (-12, 30, 0)}),
    "w2_E": dict(SPINE_L, **{"RightShoulder": (0, 0, 16),
        "RightArm": (-90, 0, 60), "RightForeArm": (-60, 0, 0),
        "RightHand": (0, 0, 0)}),
    # GUARD: blade visible, low, angled forward
    "gd_A": {"RightArm": (28, 0, -14), "RightForeArm": (-60, 15, 0),
             "RightHand": (-10, 0, 5)},
    "gd_B": {"RightArm": (35, 0, -20), "RightForeArm": (-45, 30, 0),
             "RightHand": (-30, 0, 10)},
    "gd_C": {"RightArm": (15, 0, -25), "RightForeArm": (-75, 0, 0),
             "RightHand": (0, 0, 0)},
    # CUT1_MID: blade sweeping lateral through center
    "m1_A": {"RightArm": (-25, 0, -10), "RightForeArm": (-10, 15, 0),
             "RightHand": (0, 40, 0)},
    "m1_B": {"RightArm": (-25, 40, -10), "RightForeArm": (-10, 15, 0),
             "RightHand": (0, 0, 4)},
    "m1_C": {"RightArm": (-25, 0, -10), "RightForeArm": (-40, 15, 0),
             "RightHand": (0, 0, 0)},
}

for name, pose in CANDS.items():
    set_pose(pose)
    sc.render.stamp_note_text = name
    sc.render.filepath = os.path.join(OUTDIR, f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[probe] rendered {name}")
print("[probe] DONE")
