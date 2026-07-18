"""
phase4_renders_v3.py — EEVEE turnaround from re-imported godwyn_game.glb.

The GLB stores vertices in large coordinate space. This script:
1. Imports the GLB
2. Finds the character body mesh (char1) — its bbox is authoritative for framing
3. Optionally applies a uniform scale so the character is ~2m tall in scene
4. Sets up lights + EEVEE cameras and shoots 4 turnaround frames

Shots:
  phase4_front        — full body, front
  phase4_3q           — full body, 3/4 (-45°)
  phase4_face_close   — face/head close-up
  phase4_hand_sword   — sword+hand region (mid body, left side)

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_renders_v3.py 2>&1
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

all_objs = list(scn.objects)
all_mesh = [o for o in all_objs if o.type == "MESH"]
arm      = next((o for o in all_objs if o.type == "ARMATURE"), None)

print(f"[render] meshes: {[o.name for o in all_mesh]}")
print(f"[render] armature: {arm.name if arm else None}")

# ---- Remove stray non-character objects (Icosphere etc.) ----
KEEP_MESHES = {"char1", "Godwyn_Sword", "Godwyn_Gauntlet"}
for o in all_mesh:
    if o.name not in KEEP_MESHES:
        print(f"[render] removing stray object: {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)

char_meshes = [o for o in scn.objects if o.type == "MESH"]
print(f"[render] character meshes kept: {[o.name for o in char_meshes]}")

# ---- Compute authoritative bbox from char1 (the skinned body mesh) ----
char1 = bpy.data.objects.get("char1")
if char1 is None:
    char1 = max(char_meshes, key=lambda o: len(o.data.vertices))
    print(f"[render] char1 not found, using largest mesh: {char1.name}")

# Compute bbox from char1 world coords
c1_pts   = [char1.matrix_world @ Vector(c) for c in char1.bound_box]
c1_min   = Vector((min(p.x for p in c1_pts), min(p.y for p in c1_pts), min(p.z for p in c1_pts)))
c1_max   = Vector((max(p.x for p in c1_pts), max(p.y for p in c1_pts), max(p.z for p in c1_pts)))
c1_hgt   = c1_max.z - c1_min.z
c1_ctr   = (c1_min + c1_max) / 2
print(f"[render] char1 raw bbox: H={c1_hgt:.3f}  min={tuple(round(v,1) for v in c1_min)}  max={tuple(round(v,1) for v in c1_max)}")

# ---- Normalise: scale all character objects so char1 is 2.0 units tall ----
TARGET_HEIGHT = 2.0
scl = TARGET_HEIGHT / c1_hgt if c1_hgt > 0 else 1.0
print(f"[render] raw height={c1_hgt:.3f}  scale factor={scl:.6f}")

# Apply scale to all objects (including armature) so they sit in world space correctly
for o in scn.objects:
    if o.type in ("MESH", "ARMATURE"):
        o.scale *= scl
bpy.context.view_layer.update()  # propagate

# Recompute bbox after scaling — use ALL character meshes for full extents
pts = []
for o in char_meshes:
    pts.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2
Hgt    = bb_max.z - bb_min.z
print(f"[render] normalised bbox: H={Hgt:.3f}  center={tuple(round(v,3) for v in center)}")

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

# ---- 1. Full-body front ----
lens_full = 40
fov_full  = 2 * math.atan(36.0 / (2 * lens_full))
dist_full = (Hgt / 2 * 1.22) / math.tan(fov_full / 2)
look_body = (center.x, center.y, center.z)
front_loc = (center.x, center.y - dist_full, center.z)
rendered.append(shoot("phase4_front", front_loc, look_body, lens_full))

# ---- 2. 3/4 view (-45°) ----
yaw     = math.radians(-45)
dist_3q = dist_full * 1.05
loc_3q  = (center.x + math.sin(yaw) * dist_3q,
           center.y - math.cos(yaw) * dist_3q,
           center.z)
rendered.append(shoot("phase4_3q", loc_3q, look_body, lens_full))

# ---- 3. Face close-up ----
# Head occupies top ~14% of the character's height
head_z    = bb_min.z + Hgt * 0.87
face_c    = Vector((center.x, center.y, head_z))
lens_face = 80
fov_face  = 2 * math.atan(36.0 / (2 * lens_face))
face_reg  = Hgt * 0.17   # frame this tall region
face_dist = face_reg / math.tan(fov_face / 2)
face_loc  = (face_c.x, face_c.y - face_dist, face_c.z)
rendered.append(shoot("phase4_face_close", face_loc, tuple(face_c), lens_face,
                       res_x=1024, res_y=1024))

# ---- 4. Hand + sword ----
# Sword runs from z_min up through pommel near LeftHand at ~50-60% height
# Frame lower half of character to show sword length + hand grip
sw_focus_z = bb_min.z + Hgt * 0.45
sword_c    = Vector((center.x, center.y, sw_focus_z))
lens_sw    = 55
fov_sw     = 2 * math.atan(36.0 / (2 * lens_sw))
sw_reg     = Hgt * 0.60
sw_dist    = sw_reg / math.tan(fov_sw / 2)
# shift camera slightly right and down to catch the sword on character's left
sw_loc     = (center.x + 0.15 * Hgt, center.y - sw_dist, sw_focus_z + 0.05 * Hgt)
rendered.append(shoot("phase4_hand_sword", sw_loc, tuple(sword_c), lens_sw))

print(f"\n[render] DONE. renders: {rendered}")
