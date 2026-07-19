"""
phase4_renders_v5.py — EEVEE motion preview of the newly exported godwyn_game.glb.

Re-imports the GLB, auto-fits camera properly, renders 6 frames showing
the full rig including robe/cape/hair chains.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_renders_v5.py 2>&1
"""
import bpy, os, math
from mathutils import Vector, Euler

HOME   = os.path.expanduser("~")
REPO   = f"{HOME}/godwyn-boss-fight"
GLB    = f"{REPO}/models/godwyn_game.glb"
OUTDIR = f"{REPO}/renders/game"
os.makedirs(OUTDIR, exist_ok=True)

def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[render] engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine found")

# ----------------------------------------------------------------
# Import GLB
# ----------------------------------------------------------------
print(f"[render] importing {GLB}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scn = bpy.context.scene

arm      = next((o for o in scn.objects if o.type == "ARMATURE"), None)
meshes   = [o for o in scn.objects if o.type == "MESH"]
print(f"[render] armature={arm.name if arm else None}  bones={len(arm.data.bones) if arm else 0}")
print(f"[render] meshes: {[o.name for o in meshes]}")

# ----------------------------------------------------------------
# Apply scene units sanity: force metre scale
# ----------------------------------------------------------------
scn.unit_settings.system = 'METRIC'
scn.unit_settings.scale_length = 1.0

# ----------------------------------------------------------------
# Compute bounding box from ALL mesh objects (in world space)
# ----------------------------------------------------------------
# First update the view layer so matrix_world is current
bpy.context.view_layer.update()

pts = []
for o in meshes:
    for co in o.bound_box:                        # 8 corners in local space
        pts.append(o.matrix_world @ Vector(co))

if not pts:
    raise RuntimeError("no mesh verts to compute bbox")

bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2.0
Hgt    = bb_max.z - bb_min.z
Width  = max(bb_max.x - bb_min.x, bb_max.y - bb_min.y)

print(f"[render] bbox min={tuple(round(v,3) for v in bb_min)}")
print(f"[render] bbox max={tuple(round(v,3) for v in bb_max)}")
print(f"[render] bbox center={tuple(round(v,3) for v in center)}  H={Hgt:.3f}  W={Width:.3f}")

# Sanity: if character looks implausibly sized (e.g. 69 units tall),
# it's likely in centimeters. Try to detect and use a manual fallback.
if Hgt > 20.0 or Hgt < 0.5:
    print(f"[render] WARNING: unusual height {Hgt:.2f} — bounding box may be unreliable")
    # Still use the computed center and height; camera dist will scale accordingly

# ----------------------------------------------------------------
# Render setup
# ----------------------------------------------------------------
pick_eevee(scn)
scn.render.resolution_x = 768
scn.render.resolution_y = 1024
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
try:
    scn.view_settings.look = "AgX - Punchy"
except Exception:
    pass

# World
w = bpy.data.worlds.get("RenderWorld") or bpy.data.worlds.new("RenderWorld")
scn.world = w
try:
    w.use_nodes = True
    wbg = w.node_tree.nodes.get("Background")
    if wbg:
        wbg.inputs["Color"].default_value    = (0.005, 0.006, 0.012, 1.0)
        wbg.inputs["Strength"].default_value = 0.3
except Exception:
    pass

# ----------------------------------------------------------------
# Lights  (scaled to character height)
# ----------------------------------------------------------------
def area_light(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size, d.color, d.energy = size, color, power
    o = bpy.data.objects.new(name, d)
    scn.collection.objects.link(o)
    o.location = Vector(loc)
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

# Scale lights to character size
S  = Hgt              # scale factor
cx, cy, cz = center.x, center.y, center.z
top_z = bb_max.z

area_light("LKey",  (cx - 1.0*S, cy - 1.2*S, top_z + 0.5*S),  center, 1.2*S, (1.0,  0.72, 0.42), 200*S*S)
area_light("LFill", (cx + 1.3*S, cy - 1.0*S, cz),             center, 1.6*S, (0.35, 0.50, 0.95),  40*S*S)
area_light("LRim1", (cx - 0.9*S, cy + 1.1*S, top_z + 0.2*S), center, 0.8*S, (1.0,  0.65, 0.28), 160*S*S)
area_light("LRim2", (cx + 1.0*S, cy + 1.0*S, cz + 0.4*S),    center, 0.8*S, (0.55, 0.65, 1.0),   80*S*S)

# ----------------------------------------------------------------
# Camera helper
# ----------------------------------------------------------------
cam_data = bpy.data.cameras.new("RenderCam")
cam_data.lens = 50
cam_obj  = bpy.data.objects.new("RenderCam", cam_data)
scn.collection.objects.link(cam_obj)
scn.camera = cam_obj

FOCAL_MM  = 50.0
SENSOR_MM = 36.0
fov_h     = 2 * math.atan(SENSOR_MM / (2 * FOCAL_MM))

# Distance to fit the full character height with 10% margin
MARGIN    = 1.15
dist_full = (Hgt / 2 * MARGIN) / math.tan(fov_h / 2)

print(f"[render] camera dist_full={dist_full:.3f}  for H={Hgt:.3f}")

def render_shot(name, yaw_deg, pitch_deg, dist_mult=1.0, look_z_off=0.0, focal=50, res_x=768, res_y=1024):
    yaw_r = math.radians(yaw_deg)
    pit_r = math.radians(pitch_deg)
    d     = dist_full * dist_mult
    cam_x = cx + math.sin(yaw_r) * d * math.cos(pit_r)
    cam_y = cy - math.cos(yaw_r) * d * math.cos(pit_r)
    cam_z = cz + math.sin(pit_r) * d + look_z_off

    cam_data.lens      = focal
    cam_obj.location   = Vector((cam_x, cam_y, cam_z))
    look_at            = Vector((cx, cy, cz + look_z_off))
    direc              = (look_at - cam_obj.location).normalized()
    cam_obj.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

    scn.render.resolution_x = res_x
    scn.render.resolution_y = res_y
    path = f"{OUTDIR}/{name}.png"
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sz = os.path.getsize(path)
    print(f"[render] {name}.png  ({sz:,} bytes)  cam=({cam_x:.2f},{cam_y:.2f},{cam_z:.2f})")
    return path

rendered = []

# Frame 1: Front, full body
rendered.append(render_shot("phase4_v5_f01_front",     yaw_deg=0,    pitch_deg=5))

# Frame 2: 3/4 left
rendered.append(render_shot("phase4_v5_f02_3q_left",   yaw_deg=-40,  pitch_deg=8))

# Frame 3: Back — cape/robe chains
rendered.append(render_shot("phase4_v5_f03_back",      yaw_deg=180,  pitch_deg=5))

# Frame 4: Side
rendered.append(render_shot("phase4_v5_f04_side",      yaw_deg=-90,  pitch_deg=6))

# Frame 5: Face close-up (top 15% of height = head zone, +80mm lens)
face_off = Hgt * 0.35
rendered.append(render_shot("phase4_v5_f05_face",      yaw_deg=-10,  pitch_deg=5,
                              dist_mult=0.28, look_z_off=face_off, focal=80,
                              res_x=768, res_y=768))

# Frame 6: 3/4 right — shows sword
rendered.append(render_shot("phase4_v5_f06_3q_right",  yaw_deg=45,   pitch_deg=8))

print(f"\n[render] ===== DONE =====")
for r in rendered:
    print(f"[render]   {r}")
