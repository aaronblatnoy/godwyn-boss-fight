"""
phase4_renders_v4.py — EEVEE turnaround from re-imported godwyn_game.glb.
Uses char1's OWN bbox for all camera framing (avoids Sword/Gauntlet having
off-origin world matrices after import). Icosphere removed as stray.

Shots:
  phase4_front        — full body front
  phase4_3q           — full body 3/4 (-45°)
  phase4_face_close   — face close-up
  phase4_hand_sword   — sword + hand region

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_renders_v4.py 2>&1
"""
import bpy, os, math
from mathutils import Vector

HOME    = os.path.expanduser("~")
REPO    = f"{HOME}/godwyn-boss-fight"
OUT_GLB = f"{REPO}/models/godwyn_game.glb"
OUTDIR  = f"{REPO}/renders/game"
os.makedirs(OUTDIR, exist_ok=True)

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

# Remove stray non-character objects (Icosphere, etc.)
KEEP = {"char1", "Godwyn_Sword", "Godwyn_Gauntlet"}
for o in list(all_mesh):
    if o.name not in KEEP:
        print(f"[render] removing stray: {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

char1 = bpy.data.objects.get("char1")
assert char1 is not None, "char1 not found"

# ---- Use char1's world bbox for framing ----
c1_pts  = [char1.matrix_world @ Vector(c) for c in char1.bound_box]
bb_min  = Vector((min(p.x for p in c1_pts), min(p.y for p in c1_pts), min(p.z for p in c1_pts)))
bb_max  = Vector((max(p.x for p in c1_pts), max(p.y for p in c1_pts), max(p.z for p in c1_pts)))
Hgt     = bb_max.z - bb_min.z
center  = (bb_min + bb_max) / 2
print(f"[render] char1 bbox: H={Hgt:.3f}  center={tuple(round(v,3) for v in center)}")
print(f"[render] char1 bbox min={tuple(round(v,2) for v in bb_min)}  max={tuple(round(v,2) for v in bb_max)}")

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

# Lights — scale to character height
Hs  = Hgt
tgt = (center.x, center.y, center.z + 0.05 * Hs)

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

# 1. Full-body front
# Camera from -Y direction, 40mm, margin 1.22x
lens_f   = 40
fov_f    = 2 * math.atan(36.0 / (2 * lens_f))
dist_f   = (Hgt * 0.61) / math.tan(fov_f / 2)
look_c   = (center.x, center.y, center.z)
front_lc = (center.x, center.y - dist_f, center.z)
rendered.append(shoot("phase4_front", front_lc, look_c, lens_f))

# 2. 3/4 view
yaw     = math.radians(-45)
dist_3q = dist_f * 1.05
loc_3q  = (center.x + math.sin(yaw)*dist_3q,
           center.y - math.cos(yaw)*dist_3q,
           center.z)
rendered.append(shoot("phase4_3q", loc_3q, look_c, lens_f))

# 3. Face close-up (top 16% of height)
head_z   = bb_min.z + Hgt * 0.87
face_c   = Vector((center.x, center.y, head_z))
lens_fc  = 80
fov_fc   = 2 * math.atan(36.0 / (2 * lens_fc))
fc_reg   = Hgt * 0.17
fc_dist  = fc_reg / math.tan(fov_fc / 2)
face_lc  = (face_c.x, face_c.y - fc_dist, face_c.z)
rendered.append(shoot("phase4_face_close", face_lc, tuple(face_c), lens_fc,
                       res_x=1024, res_y=1024))

# 4. Hand + sword — lower half of body
sw_z    = bb_min.z + Hgt * 0.44  # ~mid-lower body, pommel zone
sword_c = Vector((center.x, center.y, sw_z))
lens_sw = 55
fov_sw  = 2 * math.atan(36.0 / (2 * lens_sw))
sw_reg  = Hgt * 0.60
sw_dist = sw_reg / math.tan(fov_sw / 2)
sw_lc   = (center.x + 0.12*Hgt, center.y - sw_dist, sw_z + 0.04*Hgt)
rendered.append(shoot("phase4_hand_sword", sw_lc, tuple(sword_c), lens_sw))

print(f"\n[render] Phase 4 renders complete: {rendered}")
