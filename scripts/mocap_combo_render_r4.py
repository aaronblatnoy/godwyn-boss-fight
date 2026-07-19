"""
EVAL R4 — full-clip EEVEE render, per-frame TRACKED-AIM camera, native 24 fps.

  blender --background models/godwyn_mocap.blend --python scripts/mocap_combo_render_r4.py

Fixes vs r3 (round-3 flaw 3):
  - r3 used a FIXED rotation aimed via look_dz = +Z*rmax*0.10 from a camera
    sitting 0.30*dist ABOVE the hips -> it looked over the character's head,
    dropping the subject into the bottom ~30% of frame. r4 keys BOTH location
    and rotation per frame: aim target = sm_hips(f) + (0,0,0.9) (chest), so
    the subject is centered every frame.
  - size pulsing: sm_rad smoothing 10 -> 20 passes PLUS a per-frame clamp on
    the rate of change of dist (max 0.06 m/frame).
  - camera elevation lowered (off_dir z 0.30 -> 0.18) for a more level,
    heroic read.
Encode stays native 24 fps: ffmpeg -framerate 24 -start_number 1 -i f%03d.png
"""
import bpy
import os
from mathutils import Vector

OUT = "/tmp/godwyn_mocap_r4"
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)

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
    assert pc.is_baked, f"{g} cloth cache not baked"

for name in ("EvalCam", "TrackCam", "KeyLight", "RimLight", "FillLight",
             "GroundR1", "GroundR2", "GroundR3", "GroundR4", "Cam", "Sun",
             "Fill", "Ground"):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

# ── hips path + per-frame character radius ───────────────────────
BONES = ("Hips", "Head", "head_end", "LeftFoot", "RightFoot", "LeftHand",
         "RightHand", "LeftToeBase", "RightToeBase")
hips = {}
rad = {}
for f in frames:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    hp = (ae.pose.bones["Hips"].head * s).copy()
    hips[f] = hp
    r = 0.0
    for bn in BONES:
        pb = ae.pose.bones.get(bn)
        if pb:
            r = max(r, ((pb.head * s) - hp).length)
    if sword:
        sw = sword.evaluated_get(dg).matrix_world.translation
        r = max(r, (sw - hp).length)
    rad[f] = r
rmax = max(rad.values())
print(f"per-frame radius: min={min(rad.values()):.2f} max={rmax:.2f} m")


def smooth(d, passes):
    K = (1.0, 4.0, 6.0, 4.0, 1.0)
    sm = dict(d)
    for _ in range(passes):
        nx = {}
        for f in frames:
            acc = sm[frames[0]] * 0.0
            wacc = 0.0
            for k, w in zip(range(-2, 3), K):
                fk = min(max(f + k, frames[0]), frames[-1])
                acc = acc + w * sm[fk]
                wacc += w
            nx[f] = acc / wacc
        sm = nx
    return sm


sm_hips = smooth(hips, 8)
sm_rad = smooth(rad, 20)

# dist: smoothed radius * 2.4, then rate-clamped (<= 0.06 m/frame)
dist = {f: max(3.5, sm_rad[f] * 2.4) for f in frames}
for f0, f1 in zip(frames, frames[1:]):        # forward pass
    dist[f1] = min(max(dist[f1], dist[f0] - 0.06), dist[f0] + 0.06)
for f1, f0 in zip(reversed(frames[:-1]), reversed(frames)):  # backward pass
    dist[f1] = min(max(dist[f1], dist[f0] - 0.06), dist[f0] + 0.06)

# ── tracking camera: keyed location AND aim ──────────────────────
cam_data = bpy.data.cameras.new("TrackCam")
cam = bpy.data.objects.new("TrackCam", cam_data)
scene.collection.objects.link(cam)
cam_data.lens = 45
cam_data.clip_start = 0.01
cam_data.clip_end = 800
off_dir = Vector((0.8, -0.85, 0.18)).normalized()
AIM_DZ = Vector((0.0, 0.0, 0.9))
prev_eul = None
dmin, dmax = 1e9, 0.0
for f in frames:
    d = dist[f]
    dmin, dmax = min(dmin, d), max(dmax, d)
    loc = sm_hips[f] + off_dir * d
    cam.location = loc
    cam.keyframe_insert(data_path="location", frame=f)
    aim = (sm_hips[f] + AIM_DZ - loc).normalized()
    eul = aim.to_track_quat('-Z', 'Y').to_euler('XYZ')
    if prev_eul is not None:
        eul.make_compatible(prev_eul)
    prev_eul = eul
    cam.rotation_euler = eul
    cam.keyframe_insert(data_path="rotation_euler", frame=f)
scene.camera = cam
print(f"tracking cam: dist {dmin:.2f}..{dmax:.2f} m, keys={len(frames)} "
      f"(loc+rot)")

# ── dark-fantasy env (as r3): glossy dark floor + moody lights ───
pc = sum((hips[f] for f in frames), Vector()) / len(frames)
L = rmax * 2.2
gm = bpy.data.materials.get("GroundR1Mat") or bpy.data.materials.new("GroundR1Mat")
gm.use_nodes = True
bsdf = gm.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.012, 0.012, 0.016, 1)
bsdf.inputs["Metallic"].default_value = 0.85
bsdf.inputs["Roughness"].default_value = 0.12
pm = bpy.data.meshes.new("GroundR4")
ext = L * 10
pm.from_pydata([(-ext + pc.x, -ext + pc.y, 0), (ext + pc.x, -ext + pc.y, 0),
                (ext + pc.x, ext + pc.y, 0), (-ext + pc.x, ext + pc.y, 0)],
               [], [(0, 1, 2, 3)])
plane = bpy.data.objects.new("GroundR4", pm)
scene.collection.objects.link(plane)
pm.materials.append(gm)


def add_light(name, energy, color, loc, sz):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.color = color
    ld.size = sz
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    d = (pc + Vector((0, 0, rmax * 0.5)) - Vector(loc)).normalized()
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
print("RENDER R4 DONE ->", OUT)
