"""
Phase 1 — full-clip EEVEE render of the retargeted Double Combo.

Run on the grounded blend (separate invocation, fresh process):
    blender --background models/godwyn_mocap.blend --python scripts/mocap_anim_render.py
Then encode:
    ffmpeg -framerate 24 -i /tmp/godwyn_anim/a%03d.png ... /tmp/godwyn_combo.mp4
"""

import bpy
import os
import math
from mathutils import Vector

OUT = "/tmp/godwyn_anim"
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
sword = next((o for o in scene.objects if "sword" in o.name.lower()), None)
s = arm.scale.x
frames = list(range(scene.frame_start, scene.frame_end + 1))

# frame whole-motion bbox (bone heads + sword origin; tails unusable)
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
for f in frames[::4] + [frames[-1]]:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    for bn in ("Hips", "Head", "head_end", "LeftFoot", "RightFoot",
               "LeftHand", "RightHand", "LeftToeBase", "RightToeBase"):
        pb = ae.pose.bones.get(bn)
        if pb:
            p = pb.head * s
            mn = Vector(map(min, mn, p))
            mx = Vector(map(max, mx, p))
    if sword:
        p = sword.evaluated_get(dg).matrix_world.translation
        mn = Vector(map(min, mn, p))
        mx = Vector(map(max, mx, p))
center = (mn + mx) / 2
size = max(mx - mn)
print(f"anim bbox center={tuple(round(c, 2) for c in center)} size={size:.2f}")

cam = bpy.data.objects.new("AnimCam", bpy.data.cameras.new("AnimCam"))
scene.collection.objects.link(cam)
dist = size * 1.8
cam.location = center + Vector((dist * 0.75, -dist * 0.75, size * 0.22))
cam.rotation_euler = (center - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
cam.data.clip_start = 0.01
scene.camera = cam

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
sun.data.energy = 4.0
sun.rotation_euler = (math.radians(50), math.radians(-15), math.radians(30))
scene.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", 'SUN'))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), math.radians(20), math.radians(-140))
scene.collection.objects.link(fill)
if not scene.world:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.10, 0.10, 0.12, 1)

if "Ground" not in bpy.data.objects:
    pm = bpy.data.meshes.new("Ground")
    ext = size * 4
    pm.from_pydata([(-ext, -ext, 0), (ext, -ext, 0), (ext, ext, 0), (-ext, ext, 0)],
                   [], [(0, 1, 2, 3)])
    plane = bpy.data.objects.new("Ground", pm)
    scene.collection.objects.link(plane)
    gmat = bpy.data.materials.new("GroundMat")
    gmat.diffuse_color = (0.22, 0.22, 0.24, 1)
    pm.materials.append(gmat)

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
scene.render.resolution_x = 480
scene.render.resolution_y = 640
scene.render.image_settings.file_format = 'PNG'

for f in frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, f"a{f:03d}.png")
    bpy.ops.render.render(write_still=True)
print(f"rendered {len(frames)} frames to {OUT}")
print("DONE")
