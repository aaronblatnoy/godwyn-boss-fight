"""
EVAL R1 — full-clip EEVEE render of the retargeted DoubleCombo mocap + cloth,
with a reflective dark-fantasy environment.

Run (fresh process on the saved blend — cache replays from the file):
  blender --background models/godwyn_mocap.blend --python scripts/mocap_combo_render_r1.py

Outputs:
  /tmp/godwyn_mocap_r1/frames/f%03d.png   every scene frame (clean, no stamp)
  /tmp/godwyn_mocap_r1/strip/s_f%03d.png  8 labeled frames (Blender stamp)
Then (shell): ffmpeg -> /tmp/mocap_combo_r1.mp4 @30fps + hstack strip PNG.
"""
import bpy
import os
import math
from mathutils import Vector

OUT = "/tmp/godwyn_mocap_r1"
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
os.makedirs(os.path.join(OUT, "strip"), exist_ok=True)

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
s = arm.scale.x
frames = list(range(scene.frame_start, scene.frame_end + 1))
print(f"clip frames {frames[0]}-{frames[-1]} ({len(frames)} frames)")

# sanity: cloth caches present + baked
for name in ("CapeGrid", "RobeGrid"):
    obj = bpy.data.objects.get(name)
    if obj:
        pc = obj.modifiers["Cloth"].point_cache
        print(f"{name}: cache {pc.frame_start}..{pc.frame_end} baked={pc.is_baked}")

# ── idempotent cleanup of our env objects ────────────────────────
for name in ("EvalCam", "KeyLight", "RimLight", "FillLight", "GroundR1",
             "Cam", "CamF", "CamB", "Sun", "Fill", "Ground"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# ── camera framing: bone+sword bbox over the whole clip ──────────
sword = next((o for o in scene.objects if "sword" in o.name.lower()), None)
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
probe = frames[::6] + [frames[-1]]
for f in probe:
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
print(f"bbox center={tuple(round(c,2) for c in center)} size={size:.2f}")

cam_data = bpy.data.cameras.new("EvalCam")
cam = bpy.data.objects.new("EvalCam", cam_data)
scene.collection.objects.link(cam)
dist = size * 1.55
cam.location = center + Vector((dist * 0.85, -dist * 0.8, size * 0.22))
look = center.copy()
look.z = center.z * 0.9
cam.rotation_euler = (look - cam.location).normalized().to_track_quat(
    '-Z', 'Y').to_euler()
cam_data.lens = 42
cam_data.clip_start = 0.01
cam_data.clip_end = 800
scene.camera = cam

# ── dark-fantasy env: glossy dark floor + moody lights ───────────
gm = bpy.data.materials.get("GroundR1Mat") or bpy.data.materials.new("GroundR1Mat")
gm.use_nodes = True
bsdf = gm.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.016, 1)
bsdf.inputs["Metallic"].default_value = 0.85
bsdf.inputs["Roughness"].default_value = 0.12

pm = bpy.data.meshes.new("GroundR1")
ext = size * 8
pm.from_pydata([(-ext, -ext, 0), (ext, -ext, 0), (ext, ext, 0), (-ext, ext, 0)],
               [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("GroundR1", pm)
scene.collection.objects.link(plane)
pm.materials.append(gm)

def add_light(name, kind, energy, color, loc, rot=None, sz=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if sz and kind == 'AREA':
        ld.size = sz
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    else:
        d = (Vector((center.x, center.y, center.z)) - Vector(loc)).normalized()
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(ob)
    return ob

# golden key (Erdtree gold), cool blue rim from behind, faint fill
add_light("KeyLight", 'AREA', 2600, (1.0, 0.85, 0.55),
          center + Vector((size * 0.9, -size * 0.9, size * 1.1)), sz=size * 0.9)
add_light("RimLight", 'AREA', 1500, (0.45, 0.6, 1.0),
          center + Vector((-size * 1.0, size * 1.1, size * 0.8)), sz=size * 0.7)
add_light("FillLight", 'AREA', 350, (0.8, 0.82, 0.9),
          center + Vector((-size * 0.6, -size * 1.2, size * 0.4)), sz=size * 1.2)

if not scene.world:
    scene.world = bpy.data.worlds.new("W")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.008, 0.008, 0.012, 1)  # near-black void
    bg.inputs[1].default_value = 1.0

# ── EEVEE with raytraced reflections ─────────────────────────────
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
    print("EEVEE raytracing ON")
if hasattr(ee, "taa_render_samples"):
    ee.taa_render_samples = 32

scene.render.resolution_x = 960
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

scene.render.use_stamp = False
for f in frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, "frames", f"f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
print(f"rendered {len(frames)} frames")

# ── labeled strip frames (Blender burn-in stamp) ─────────────────
n = len(frames)
strip = [frames[0], frames[n // 7], frames[2 * n // 7], frames[3 * n // 7],
         frames[4 * n // 7], frames[5 * n // 7], frames[6 * n // 7], frames[-1]]
scene.render.use_stamp = True
scene.render.use_stamp_frame = True
scene.render.use_stamp_date = False
scene.render.use_stamp_time = False
scene.render.use_stamp_render_time = False
scene.render.use_stamp_filename = False
scene.render.use_stamp_camera = False
scene.render.use_stamp_scene = False
scene.render.stamp_font_size = 28
scene.render.stamp_foreground = (1, 1, 1, 1)
scene.render.stamp_background = (0, 0, 0, 0.6)
for i, f in enumerate(strip):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, "strip", f"s{i}_f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
print("strip frames:", strip)
print("RENDER R1 DONE ->", OUT)
