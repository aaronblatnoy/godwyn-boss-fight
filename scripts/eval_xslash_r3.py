"""
eval_xslash_r3.py — Round-3 animation evaluation render of the X-slash.

Opens models/godwyn_xslash.blend (P1 pose anim + P2 baked cape + P3 fixer r1),
verifies the cape bake is actually present (phys_* keyframes) and fails loud
if not, dresses the scene as a reflective dark-fantasy void, renders ALL
frames with EEVEE to /tmp/xslash_r3_frames/, and renders labeled key stills
to /tmp/xslash_r3_strip/.

Run:
  blender --background --python ~/godwyn-boss-fight/scripts/eval_xslash_r3.py 2>&1
Then (server):
  ffmpeg -y -framerate 30 -i /tmp/xslash_r3_frames/f%04d.png -c:v libx264 \
    -pix_fmt yuv420p /tmp/xslash_r3.mp4
  ffmpeg -y -pattern_type glob -i '/tmp/xslash_r3_strip/*.png' \
    -filter_complex tile=4x2 /tmp/xslash_r3_strip.png
"""
import bpy, os, math
from mathutils import Euler, Vector

BLEND = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_xslash.blend")
FRAMES_DIR = "/tmp/xslash_r3_frames"
STRIP_DIR = "/tmp/xslash_r3_strip"
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(STRIP_DIR, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
print(f"[r3] opened {BLEND}  frames {sc.frame_start}-{sc.frame_end}  fps {sc.render.fps}")

# ── Verify animation content (body keys + cape bake) ────────────────────────
act = arm.animation_data.action if arm.animation_data else None
assert act is not None, "[r3] FATAL: armature has no action"
fcs = []
if getattr(act, "layers", None):
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                fcs.extend(cb.fcurves)
else:
    fcs = list(getattr(act, "fcurves", []) or [])
import re
bones_keyed = set()
for fc in fcs:
    m = re.match(r'pose\.bones\["([^"]+)"\]', fc.data_path)
    if m:
        bones_keyed.add(m.group(1))
phys_keyed = sorted(b for b in bones_keyed if b.startswith("phys_"))
body_keyed = sorted(b for b in bones_keyed if not b.startswith("phys_"))
print(f"[r3] action '{act.name}': {len(fcs)} fcurves, "
      f"{len(body_keyed)} body bones keyed, {len(phys_keyed)} phys bones keyed")
assert len(body_keyed) >= 10, "[r3] FATAL: body animation missing"
assert len(phys_keyed) >= 30, "[r3] FATAL: cape bake missing (phys_* not keyed)"

# ── Reflective dark-fantasy environment ─────────────────────────────────────
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

# Warm golden key + cold blue rim
for o in bpy.data.objects:
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        o.data.color = (1.0, 0.92, 0.6)
        o.data.energy = 5.0
    if o.type == 'LIGHT' and o.data.type == 'AREA' and o.name != "Rim":
        o.data.color = (0.75, 0.82, 1.0)
        o.data.energy = 220
if bpy.data.objects.get("Rim") is None:
    bpy.ops.object.light_add(type='AREA', location=(0.5, 6.5, 3.5))
    rim = bpy.context.active_object
    rim.name = "Rim"
    rim.data.energy = 900
    rim.data.size = 5
    rim.data.color = (0.55, 0.68, 1.0)
    rim.rotation_euler = Euler((math.radians(-115), 0, 0), 'XYZ')

# ── EEVEE settings ──────────────────────────────────────────────────────────
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
try:
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Punchy'
except Exception:
    pass

# ── Full animation frames (no stamp) ────────────────────────────────────────
sc.render.use_stamp = False
sc.frame_start, sc.frame_end = 1, 64
sc.render.filepath = os.path.join(FRAMES_DIR, "f")
bpy.ops.render.render(animation=True)
print(f"[r3] animation frames -> {FRAMES_DIR}")

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
    print(f"[r3] still {sc.render.filepath}")
print("[r3] DONE")
