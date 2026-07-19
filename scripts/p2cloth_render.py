"""
PHASE 2 — eval renders + numeric smoothness probe for the cape cloth sim.

Run:
  blender --background models/godwyn_mocap.blend --python scripts/p2cloth_render.py -- [tag]

- Numeric: per-frame mean/max vertex displacement of the CapeProxy evaluated
  mesh (explosions/jitter show up as spikes), plus min proxy Z (floor sanity).
- Visual: EEVEE renders of spread frames from front-quarter and back-quarter.
"""
import bpy
import os
import sys
import math
from mathutils import Vector

argv = sys.argv
tag = argv[argv.index("--") + 1] if "--" in argv and argv.index("--") + 1 < len(argv) else "r1"
OUT = f"/tmp/godwyn_cloth/{tag}"
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
proxy = (bpy.data.objects.get("CapeProxy") or bpy.data.objects["RobeGrid"])
proxy2 = bpy.data.objects.get("CapeGrid")
char = bpy.data.objects["char1"]
sd = char.modifiers.get("CapeSD")
print(f"SD bound: {sd is not None and sd.is_bound}")

frames = list(range(scene.frame_start, scene.frame_end + 1))

# ── numeric smoothness probe on the proxy ────────────────────────
prev = None
worst = []
for f in frames:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = proxy.evaluated_get(dg)
    co = [v.co.copy() for v in ev.data.vertices]
    zmin = min(v.z for v in co)
    if prev is not None and len(prev) == len(co):
        d = [(a - b).length for a, b in zip(co, prev)]
        mean_d = sum(d) / len(d)
        max_d = max(d)
        worst.append((max_d, f))
        print(f"f{f:3d}: mean_disp={mean_d*100:6.2f}cm max_disp={max_d*100:6.2f}cm "
              f"zmin={zmin:6.3f}")
    prev = co
worst.sort(reverse=True)
print("TOP-5 max per-frame displacement:",
      [(f, round(m * 100, 1)) for m, f in worst[:5]], "cm")

# ── camera framing from bone bbox across the clip ────────────────
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

REND = [1, 12, 22, 32, 42, 52, 60, 68]
for f in REND:
    scene.frame_set(f)
    for cam, ctag in ((cam_f, "F"), (cam_b, "B")):
        scene.camera = cam
        scene.render.filepath = os.path.join(OUT, f"{ctag}_f{f:03d}.png")
        bpy.ops.render.render(write_still=True)
    print(f"rendered f{f}")

# proxy-only views (raw sim, no SurfaceDeform in the way)
proxy.hide_render = False
if proxy2:
    proxy2.hide_render = False
char.hide_render = True
sw = bpy.data.objects.get("Godwyn_Sword")
if sw:
    sw.hide_render = True
for f in (1, 22, 42, 60):
    scene.frame_set(f)
    scene.camera = cam_b
    scene.render.filepath = os.path.join(OUT, f"PROXY_f{f:03d}.png")
    bpy.ops.render.render(write_still=True)
proxy.hide_render = True
if proxy2:
    proxy2.hide_render = True
char.hide_render = False
if sw:
    sw.hide_render = False
print("P2CLOTH RENDER DONE ->", OUT)
