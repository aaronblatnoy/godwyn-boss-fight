"""
eval_xslash_r1.py — Round-1 animation evaluation render of the X-slash.

Opens models/godwyn_xslash.blend (pose anim + baked cape), dresses the scene
as a reflective dark-fantasy void (glossy dark floor, cold rim + warm key,
near-black world), renders ALL frames with EEVEE to /tmp/xslash_r1_frames/,
and renders 8 labeled key stills to /tmp/xslash_r1_strip/ for the frame strip.

Run:
  blender --background --python ~/godwyn-boss-fight/scripts/eval_xslash_r1.py 2>&1
Then (server):
  ffmpeg -y -framerate 30 -i /tmp/xslash_r1_frames/f%04d.png -c:v libx264 \
    -pix_fmt yuv420p /tmp/xslash_r1.mp4
"""
import bpy, os, math
from mathutils import Euler, Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_xslash.blend")
FRAMES_DIR = "/tmp/xslash_r1_frames"
STRIP_DIR = "/tmp/xslash_r1_strip"
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(STRIP_DIR, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
print(f"[r1] opened {BLEND}  frames {sc.frame_start}-{sc.frame_end}  fps {sc.render.fps}")

# ── Reflective dark-fantasy environment ─────────────────────────────────────
# Glossy near-black floor (reflects the golden figure — dark-fantasy arena)
ground = None
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith("Plane"):
        ground = o
        break
if ground is None:
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    ground = bpy.context.active_object
gmat = bpy.data.materials.new("VoidFloor")
gmat.use_nodes = True
bsdf = gmat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.015, 0.014, 0.016, 1)
bsdf.inputs["Metallic"].default_value = 0.85
bsdf.inputs["Roughness"].default_value = 0.12
ground.data.materials.clear()
ground.data.materials.append(gmat)

# Near-black world with a faint cold tint
world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
sc.world = world
world.use_nodes = True
wbg = world.node_tree.nodes.get("Background")
if wbg is None:
    wbg = world.node_tree.nodes.new("ShaderNodeBackground")
    out = world.node_tree.nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(wbg.outputs[0], out.inputs[0])
wbg.inputs["Color"].default_value = (0.004, 0.005, 0.010, 1)
wbg.inputs["Strength"].default_value = 1.0

# Warm golden key (existing sun retinted) + cold blue rim from behind
for o in bpy.data.objects:
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        o.data.color = (1.0, 0.92, 0.6)
        o.data.energy = 5.0
    if o.type == 'LIGHT' and o.data.type == 'AREA':
        o.data.color = (0.75, 0.82, 1.0)
        o.data.energy = 220
bpy.ops.object.light_add(type='AREA', location=(0.5, 6.5, 3.5))
rim = bpy.context.active_object
rim.data.energy = 900
rim.data.size = 5
rim.data.color = (0.55, 0.68, 1.0)
rim.rotation_euler = Euler((math.radians(-115), 0, 0), 'XYZ')

# ── EEVEE settings (raytraced reflections if available) ─────────────────────
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
ee = sc.eevee
if hasattr(ee, "use_raytracing"):
    ee.use_raytracing = True
if hasattr(ee, "taa_render_samples"):
    ee.taa_render_samples = 32
sc.render.resolution_x = 768
sc.render.resolution_y = 960
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX' if 'AgX' in [
    'AgX'] else 'Filmic'  # AgX exists in 5.x
try:
    sc.view_settings.look = 'AgX - Punchy'
except Exception:
    pass

# ── Full animation frames (no stamp) ────────────────────────────────────────
sc.render.use_stamp = False
sc.frame_start, sc.frame_end = 1, 64
sc.render.filepath = os.path.join(FRAMES_DIR, "f")
bpy.ops.render.render(animation=True)
print(f"[r1] animation frames -> {FRAMES_DIR}")

# ── Labeled key stills for the strip ────────────────────────────────────────
sc.render.use_stamp = True
for attr in ("use_stamp_date", "use_stamp_time", "use_stamp_render_time",
             "use_stamp_frame", "use_stamp_scene", "use_stamp_camera",
             "use_stamp_filename", "use_stamp_memory", "use_stamp_hostname"):
    if hasattr(sc.render, attr):
        setattr(sc.render, attr, False)
sc.render.use_stamp_note = True
sc.render.stamp_font_size = 26
sc.render.stamp_foreground = (1, 1, 1, 1)
sc.render.stamp_background = (0, 0, 0, 0.75)

STRIP = [(1,  "f01 GUARD low"),
         (16, "f16 WINDUP-1 upper-R"),
         (21, "f21 CUT-1 mid"),
         (25, "f25 CUT-1 end lower-L"),
         (38, "f38 WINDUP-2 upper-L"),
         (43, "f43 CUT-2 mid"),
         (47, "f47 CUT-2 end lower-R"),
         (64, "f64 RECOVER guard")]
for i, (f, note) in enumerate(STRIP):
    sc.frame_set(f)
    sc.render.stamp_note_text = note
    sc.render.filepath = os.path.join(STRIP_DIR, f"s{i:02d}_f{f:02d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[r1] still {sc.render.filepath}")
print("[r1] DONE")
