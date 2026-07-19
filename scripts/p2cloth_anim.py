"""
PHASE 2 — full-sequence EEVEE renders of the cloth-simmed Double Combo.
Renders every frame from CamF and CamB into /tmp/godwyn_cloth/anim/.
Reuses the camera/light/ground setup from p2cloth_render.py.
"""
import bpy
import os
import math
from mathutils import Vector

OUT = "/tmp/godwyn_cloth/anim"
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
frames = list(range(scene.frame_start, scene.frame_end + 1))

s = arm.scale.x
strip = [frames[0], frames[len(frames)//4], frames[len(frames)//2],
         frames[3*len(frames)//4], frames[-1]]
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
for f in strip:
    scene.frame_set(f)
    ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for bn in ("Hips", "Head", "LeftFoot", "RightFoot", "LeftHand", "RightHand"):
        p = ae.pose.bones[bn].head * s
        mn = Vector(map(min, mn, p))
        mx = Vector(map(max, mx, p))
center = (mn + mx) / 2
size = max(mx - mn)

for name in ("CamF", "CamB", "Sun", "Fill"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

def add_cam(name, offset):
    cd = bpy.data.cameras.new(name)
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    dist = size * 1.8
    c.location = center + Vector((offset[0] * dist, offset[1] * dist, size * 0.25))
    d = (center - c.location).normalized()
    c.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.clip_start = 0.01
    cd.clip_end = 500
    return c

cam_f = add_cam("CamF", (0.75, -0.75))
cam_b = add_cam("CamB", (-0.55, 0.9))

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), math.radians(-15), math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.8
fill.rotation_euler = (math.radians(60), math.radians(20), math.radians(-140))
scene.collection.objects.link(fill)
if not scene.world:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.12, 0.12, 0.14, 1)
if "Ground" not in bpy.data.objects:
    pm = bpy.data.meshes.new("Ground")
    ext = size * 4
    pm.from_pydata([(-ext, -ext, 0), (ext, -ext, 0), (ext, ext, 0), (-ext, ext, 0)],
                   [], [(0, 1, 2, 3)])
    plane = bpy.data.objects.new("Ground", pm)
    scene.collection.objects.link(plane)
    gm = bpy.data.materials.new("GroundMat")
    gm.diffuse_color = (0.25, 0.25, 0.27, 1)
    pm.materials.append(gm)

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.image_settings.file_format = 'PNG'

for f in frames:
    scene.frame_set(f)
    for cam, tag in ((cam_f, "F"), (cam_b, "B")):
        scene.camera = cam
        scene.render.filepath = os.path.join(OUT, f"{tag}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
    if f % 10 == 0:
        print(f"rendered up to f{f}")
print("ANIM RENDER DONE")
