"""
phase4_renders_only.py — Re-render EEVEE turnaround from the re-imported GLB.
The GLB imports at a large scale (centimeter units). This script compensates
by using the actual mesh bbox to frame the camera, and normalises the scale
with bpy.ops.object.transform_apply after scaling to unit size.

Shots:
  phase4_front        — full body, front
  phase4_3q           — full body, 3/4
  phase4_face_close   — head/face close-up
  phase4_hand_sword   — hand + sword region

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_renders_only.py 2>&1
"""
import bpy, os, math
from mathutils import Vector

HOME    = os.path.expanduser("~")
REPO    = f"{HOME}/godwyn-boss-fight"
OUT_GLB = f"{REPO}/models/godwyn_game.glb"
OUTDIR  = f"{REPO}/renders/game"
os.makedirs(OUTDIR, exist_ok=True)

# ----------------------------------------------------------------
def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[render] engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine")

# ================================================================
# Import GLB
# ================================================================
print(f"[render] importing {OUT_GLB}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)
scn = bpy.context.scene

all_mesh = [o for o in scn.objects if o.type == "MESH"]
arm      = next((o for o in scn.objects if o.type == "ARMATURE"), None)
print(f"[render] meshes: {[o.name for o in all_mesh]}  arm: {arm.name if arm else None}")

# Apply transforms + normalize scale so camera math works in Blender-unit space
# After glTF import the objects may have scale ~(0.01, 0.01, 0.01) if centimetres
for o in list(scn.objects):
    if o.type in ("MESH", "ARMATURE"):
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
bpy.ops.object.transform_apply(scale=True, location=False, rotation=False)

# Recompute bbox after applying scale
pts = []
for o in all_mesh:
    pts.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2
Hgt    = bb_max.z - bb_min.z
print(f"[render] bbox after apply: H={Hgt:.3f}  min={tuple(round(v,2) for v in bb_min)}  max={tuple(round(v,2) for v in bb_max)}")
print(f"[render] center={tuple(round(v,3) for v in center)}")

# ================================================================
# Scene setup
# ================================================================
pick_eevee(scn)
scn.render.image_settings.file_format = "PNG"
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"

w = bpy.data.worlds.get("GameWorld") or bpy.data.worlds.new("GameWorld")
scn.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value    = (0.008, 0.010, 0.018, 1.0)
    bg.inputs["Strength"].default_value = 0.5

def area_light(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size, d.color, d.energy = size, color, power
    o = bpy.data.objects.new(name, d)
    scn.collection.objects.link(o)
    o.location = Vector(loc)
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

Hs  = Hgt
tgt = (center.x, center.y, center.z + 0.05 * Hs)
area_light("TKey",  (center.x - 1.0*Hs, center.y - 1.2*Hs, bb_max.z + 0.5*Hs),  tgt, 1.2*Hs, (1.0,  0.72, 0.42), 180.0*Hs*Hs)
area_light("TFill", (center.x + 1.3*Hs, center.y - 1.0*Hs, center.z),             tgt, 1.6*Hs, (0.35, 0.50, 0.95),  30.0*Hs*Hs)
area_light("TRim1", (center.x - 0.9*Hs, center.y + 1.1*Hs, bb_max.z + 0.2*Hs),   tgt, 0.8*Hs, (1.0,  0.65, 0.28), 140.0*Hs*Hs)
area_light("TRim2", (center.x + 1.0*Hs, center.y + 1.0*Hs, center.z + 0.4*Hs),   tgt, 0.8*Hs, (0.55, 0.65, 1.0),   75.0*Hs*Hs)

def shoot(name, cam_loc, look_at, focal, res_x=1024, res_y=1365):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cam = bpy.data.objects.new(name, cd)
    scn.collection.objects.link(cam)
    cam.location = Vector(cam_loc)
    direc = (Vector(look_at) - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn.camera = cam
    scn.render.resolution_x = res_x
    scn.render.resolution_y = res_y
    path = f"{OUTDIR}/{name}.png"
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sz = os.path.getsize(path)
    print(f"[render] wrote {path}  ({sz:,} bytes)")
    return path

rendered = []

# Full-body front — camera at front (y negative relative to character)
# Use 40mm lens, fit character with 120% margin
lens_full = 40
fov_full  = 2 * math.atan(36.0 / (2 * lens_full))
dist_full = (Hgt / 2 * 1.20) / math.tan(fov_full / 2)
front_loc = (center.x, center.y - dist_full, center.z)
look_body = (center.x, center.y, center.z)
rendered.append(shoot("phase4_front", front_loc, look_body, lens_full))

# 3/4 view — rotate 45° around Z (yaw -45 means clockwise from front)
yaw = math.radians(-45)
dist_3q   = dist_full * 1.05
loc_3q    = (center.x + math.sin(yaw) * dist_3q,
             center.y - math.cos(yaw) * dist_3q,
             center.z)
rendered.append(shoot("phase4_3q", loc_3q, look_body, lens_full))

# Face close-up — top 15% of character bounding box = head zone
# Character height Hgt, head starts at ~85% up
head_z  = bb_min.z + Hgt * 0.86
face_c  = Vector((center.x, center.y, head_z))
lens_face = 80
fov_face  = 2 * math.atan(36.0 / (2 * lens_face))
# frame a region that is 18% of character height
face_dist = (Hgt * 0.18) / math.tan(fov_face / 2)
face_loc  = (face_c.x, face_c.y - face_dist, face_c.z)
rendered.append(shoot("phase4_face_close", face_loc, tuple(face_c), lens_face,
                       res_x=1024, res_y=1024))

# Hand + sword — sword is planted at the left side; pommel is near LeftHand
# which is approximately at 50–60% character height.
# Frame the lower-left-mid body showing the sword running down.
sword_focus_z = bb_min.z + Hgt * 0.50   # ~mid height (pommel area)
sword_c = Vector((center.x, center.y, sword_focus_z))
lens_sw  = 55
fov_sw   = 2 * math.atan(36.0 / (2 * lens_sw))
# frame a region that is 55% of character height to see sword length
sw_dist  = (Hgt * 0.55) / math.tan(fov_sw / 2)
# camera slightly to the character's right (viewer left) to catch the sword
sw_loc   = (center.x + 0.2 * Hgt, center.y - sw_dist, sword_c.z + 0.1 * Hgt)
rendered.append(shoot("phase4_hand_sword", sw_loc, tuple(sword_c), lens_sw))

print(f"\n[render] DONE. renders: {rendered}")
