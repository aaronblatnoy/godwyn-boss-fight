"""
EVAL R2 — full-clip EEVEE render, HIPS-TRACKING camera, native 24 fps.

  blender --background models/godwyn_mocap.blend --python scripts/mocap_combo_render_r2.py

Fixes vs r1: camera follows a heavily-smoothed Hips path with a constant
offset (character stays large in frame instead of a whole-clip bbox wide shot);
scene stays 24 fps and the shell encode must use -framerate 24.

Outputs:
  /tmp/godwyn_mocap_r2/frames/f%03d.png   every scene frame
  /tmp/godwyn_mocap_r2/strip/s*_f%03d.png 8 labeled frames
"""
import bpy
import os
from mathutils import Vector

OUT = "/tmp/godwyn_mocap_r2"
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
os.makedirs(os.path.join(OUT, "strip"), exist_ok=True)

scene = bpy.context.scene
assert scene.render.fps == 24, f"expected 24fps scene, got {scene.render.fps}"
arm = next(o for o in scene.objects if o.type == "ARMATURE")
s = arm.scale.x
frames = list(range(scene.frame_start, scene.frame_end + 1))
sword = next((o for o in scene.objects if "sword" in o.name.lower()), None)
print(f"clip {frames[0]}..{frames[-1]} @ {scene.render.fps}fps")

for g in ("CapeGrid", "RobeGrid"):
    pc = bpy.data.objects[g].modifiers["Cloth"].point_cache
    print(f"{g}: cache {pc.frame_start}..{pc.frame_end} baked={pc.is_baked}")

# idempotent env cleanup
for name in ("EvalCam", "TrackCam", "KeyLight", "RimLight", "FillLight",
             "GroundR1", "GroundR2", "Cam", "Sun", "Fill", "Ground"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# ── hips path + per-frame character radius ───────────────────────
BONES = ("Hips", "Head", "head_end", "LeftFoot", "RightFoot", "LeftHand",
         "RightHand", "LeftToeBase", "RightToeBase")
hips = {}
radius = 0.0
for f in frames:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    hp = (ae.pose.bones["Hips"].head * s).copy()
    hips[f] = hp
    for bn in BONES:
        pb = ae.pose.bones.get(bn)
        if pb:
            radius = max(radius, ((pb.head * s) - hp).length)
    if sword:
        sw = sword.evaluated_get(dg).matrix_world.translation
        radius = max(radius, (sw - hp).length)
print(f"character radius (bones+sword sweep) = {radius:.2f} m")

# heavy smoothing: 8 passes of a 5-tap gaussian, edge-clamped
K = (1.0, 4.0, 6.0, 4.0, 1.0)
sm = dict(hips)
for _ in range(8):
    nx = {}
    for f in frames:
        acc = Vector((0, 0, 0))
        wacc = 0.0
        for k, w in zip(range(-2, 3), K):
            fk = min(max(f + k, frames[0]), frames[-1])
            acc += w * sm[fk]
            wacc += w
        nx[f] = acc / wacc
    sm = nx

# ── tracking camera: constant offset from smoothed hips ──────────
cam_data = bpy.data.cameras.new("TrackCam")
cam = bpy.data.objects.new("TrackCam", cam_data)
scene.collection.objects.link(cam)
cam_data.lens = 45
cam_data.clip_start = 0.01
cam_data.clip_end = 800
dist = radius * 3.1
off = Vector((0.8, -0.85, 0.30)).normalized() * dist
look_dz = Vector((0.0, 0.0, radius * 0.10))
cam.rotation_euler = (look_dz - off).normalized().to_track_quat(
    '-Z', 'Y').to_euler()
for f in frames:
    cam.location = sm[f] + off
    cam.keyframe_insert(data_path="location", frame=f)
scene.camera = cam
print(f"tracking cam: dist={dist:.2f} keys={len(frames)}")

# ── dark-fantasy env (as r1): glossy dark floor + moody lights ───
pc = sum((hips[f] for f in frames), Vector()) / len(frames)  # path center
L = radius * 2.2
gm = bpy.data.materials.get("GroundR1Mat") or bpy.data.materials.new("GroundR1Mat")
gm.use_nodes = True
bsdf = gm.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.016, 1)
bsdf.inputs["Metallic"].default_value = 0.85
bsdf.inputs["Roughness"].default_value = 0.12
pm = bpy.data.meshes.new("GroundR2")
ext = L * 10
pm.from_pydata([(-ext + pc.x, -ext + pc.y, 0), (ext + pc.x, -ext + pc.y, 0),
                (ext + pc.x, ext + pc.y, 0), (-ext + pc.x, ext + pc.y, 0)],
               [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("GroundR2", pm)
scene.collection.objects.link(plane)
pm.materials.append(gm)

def add_light(name, energy, color, loc, sz):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.color = color
    ld.size = sz
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    d = (pc + Vector((0, 0, radius * 0.5)) - Vector(loc)).normalized()
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(ob)

add_light("KeyLight", 2600, (1.0, 0.85, 0.55),
          pc + Vector((L * 0.9, -L * 0.9, L * 1.1)), L * 0.9)
add_light("RimLight", 1500, (0.45, 0.6, 1.0),
          pc + Vector((-L * 1.0, L * 1.1, L * 0.8)), L * 0.7)
add_light("FillLight", 350, (0.8, 0.82, 0.9),
          pc + Vector((-L * 0.6, -L * 1.2, L * 0.4)), L * 1.2)

if not scene.world:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.008, 0.008, 0.012, 1)
    bg.inputs[1].default_value = 1.0

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
print(f"engine: {scene.render.engine}")
ee = scene.eevee
if hasattr(ee, "use_raytracing"):
    ee.use_raytracing = True
if hasattr(ee, "taa_render_samples"):
    ee.taa_render_samples = 32

scene.render.resolution_x = 960
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

only = os.environ.get("ONLY_FRAMES")
render_frames = [int(x) for x in only.split(",")] if only else frames

scene.render.use_stamp = False
for f in render_frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, "frames", f"f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
print(f"rendered {len(render_frames)} frames")
if only:
    print("RENDER R2 DONE (subset) ->", OUT)
    import sys
    sys.exit(0)

n = len(frames)
strip = [frames[0], frames[n // 7], frames[2 * n // 7], frames[3 * n // 7],
         frames[4 * n // 7], frames[5 * n // 7], frames[6 * n // 7], frames[-1]]
scene.render.use_stamp = True
scene.render.use_stamp_frame = True
for flag in ("date", "time", "render_time", "filename", "camera", "scene"):
    setattr(scene.render, f"use_stamp_{flag}", False)
scene.render.stamp_font_size = 28
scene.render.stamp_foreground = (1, 1, 1, 1)
scene.render.stamp_background = (0, 0, 0, 0.6)
for i, f in enumerate(strip):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, "strip", f"s{i}_f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
print("strip frames:", strip)
print("RENDER R2 DONE ->", OUT)
