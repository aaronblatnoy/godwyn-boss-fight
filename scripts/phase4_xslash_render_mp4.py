"""
phase4_xslash_render_mp4.py — Re-render the X-slash animation with a
reflective environment (HDRI-style world + metallic ground plane) at
EEVEE speed, then encode xslash.mp4 via ffmpeg at 30fps.

Source: models/godwyn_xslash.blend (produced by anim_xslash.py).
Output: renders/game/xslash.mp4

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_xslash_render_mp4.py 2>&1
"""
import bpy, os, math, subprocess, sys
from mathutils import Vector, Euler

HOME   = os.path.expanduser("~")
REPO   = f"{HOME}/godwyn-boss-fight"
BLEND  = f"{REPO}/models/godwyn_xslash.blend"
ANIMDIR = f"{REPO}/renders/game/xslash_frames"
OUT_MP4 = f"{REPO}/renders/game/xslash.mp4"
os.makedirs(ANIMDIR, exist_ok=True)

# ── Open the xslash blend ────────────────────────────────────────────────────
print(f"[render] opening {BLEND}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc = bpy.context.scene

# ── Switch to EEVEE ──────────────────────────────────────────────────────────
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        print(f"[render] engine = {eng}")
        break
    except Exception:
        continue

# ── Reflective world environment ─────────────────────────────────────────────
# Build a procedural sky: dark base + warm horizon glow for golden reflections.
w = bpy.data.worlds.new("XslashEnv")
sc.world = w
w.use_nodes = True
nt = w.node_tree
nt.nodes.clear()

coord  = nt.nodes.new("ShaderNodeTexCoord")
grad   = nt.nodes.new("ShaderNodeTexGradient")
grad.gradient_type = "SPHERICAL"
mix    = nt.nodes.new("ShaderNodeMixRGB")
mix.inputs["Color1"].default_value = (0.004, 0.005, 0.012, 1)   # deep dark sky
mix.inputs["Color2"].default_value = (0.32, 0.22, 0.08, 1)      # warm golden horizon
bg     = nt.nodes.new("ShaderNodeBackground")
bg.inputs["Strength"].default_value = 0.8
out    = nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(coord.outputs["Normal"], grad.inputs["Vector"])
nt.links.new(grad.outputs["Color"], mix.inputs["Fac"])
nt.links.new(mix.outputs["Color"], bg.inputs["Color"])
nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

# ── Replace / upgrade ground plane to metallic reflective material ────────────
ground = bpy.data.objects.get("Plane")
if ground is None:
    # Look for any plane
    for o in sc.objects:
        if o.type == "MESH" and "lane" in o.name.lower():
            ground = o
            break
if ground is None:
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Plane"

gmat = bpy.data.materials.new("GroundReflective")
gmat.use_nodes = True
nodes = gmat.node_tree.nodes
nodes.clear()
pbsdf = nodes.new("ShaderNodeBsdfPrincipled")
pbsdf.inputs["Base Color"].default_value   = (0.06, 0.05, 0.04, 1)
pbsdf.inputs["Metallic"].default_value     = 0.85
pbsdf.inputs["Roughness"].default_value    = 0.15
pbsdf.inputs["Specular IOR Level"].default_value = 1.0 if "Specular IOR Level" in pbsdf.inputs else 0.5
out_n = nodes.new("ShaderNodeOutputMaterial")
gmat.node_tree.links.new(pbsdf.outputs["BSDF"], out_n.inputs["Surface"])
# Assign to ground
if ground.data.materials:
    ground.data.materials[0] = gmat
else:
    ground.data.materials.append(gmat)

# ── Upgrade lights: key + fill + rim for metallic reflections ────────────────
# Remove old lights, add well-positioned ones
for o in list(sc.objects):
    if o.type == "LIGHT":
        bpy.data.objects.remove(o, do_unlink=True)

def add_light(ltype, name, loc, energy, color=(1,1,1), size=4):
    ld = bpy.data.lights.new(name, ltype)
    ld.energy = energy
    ld.color  = color
    if ltype == "AREA":
        ld.size = size
    lo = bpy.data.objects.new(name, ld)
    sc.collection.objects.link(lo)
    lo.location = loc
    return lo

# Key: warm golden above-right
kl = add_light("SUN", "KeySun", (5, -4, 8), energy=6.0, color=(1.0, 0.88, 0.58))
kl.rotation_euler = Euler((math.radians(48), 0, math.radians(28)), 'XYZ')

# Fill: cool blue-silver from left
fl = add_light("AREA", "FillArea", (-5, -4, 3), energy=600, color=(0.45, 0.60, 1.0), size=6)

# Rim from behind: warm amber
rl = add_light("AREA", "RimArea", (0, 6, 4), energy=800, color=(1.0, 0.72, 0.3), size=4)

# ── Camera: keep existing (near-frontal from anim_xslash.py) ────────────────
cam = sc.camera
if cam is None:
    existing_cams = [o for o in sc.objects if o.type == "CAMERA"]
    cam = existing_cams[0] if existing_cams else None
if cam is None:
    bpy.ops.object.camera_add(location=(1.2, -7.4, 2.1))
    cam = bpy.context.active_object
    target = Vector((0.0, 0.0, 1.8))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
print(f"[render] camera = {cam.name}  loc = {tuple(round(v,2) for v in cam.location)}")

# ── Render settings ──────────────────────────────────────────────────────────
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.use_stamp = False
sc.render.fps = 30
sc.frame_start = 1
sc.frame_end = 64

sc.render.filepath = os.path.join(ANIMDIR, "f")
print(f"[render] rendering {sc.frame_end - sc.frame_start + 1} frames to {ANIMDIR} ...")
bpy.ops.render.render(animation=True)
frame_count = len([f for f in os.listdir(ANIMDIR) if f.endswith(".png")])
print(f"[render] rendered {frame_count} PNG frames")

# ── Encode MP4 via ffmpeg ────────────────────────────────────────────────────
# ffmpeg pattern: ANIMDIR/f0001.png .. f0064.png
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-framerate", "30",
    "-i", os.path.join(ANIMDIR, "f%04d.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "18",
    "-movflags", "+faststart",
    OUT_MP4,
]
print(f"[ffmpeg] {' '.join(ffmpeg_cmd)}")
result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
print(result.stdout[-2000:] if result.stdout else "")
print(result.stderr[-2000:] if result.stderr else "")
if result.returncode != 0:
    print(f"[ffmpeg] FAILED (returncode={result.returncode})")
    sys.exit(1)
mp4_size = os.path.getsize(OUT_MP4)
print(f"[ffmpeg] wrote {OUT_MP4}  ({mp4_size:,} bytes)")
print("[render] DONE — xslash.mp4 complete")
