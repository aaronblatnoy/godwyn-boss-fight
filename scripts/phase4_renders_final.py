"""
phase4_renders_final.py — Fix 3/4 and hand+sword renders from godwyn_game.glb.

The front and feet renders from phase4_export_commit.py looked good.
This script re-renders all 4 shots with corrected camera math:
  p4final_front      — full body front
  p4final_3q         — full body 3/4
  p4final_handsword  — hand + sword region
  p4final_feet       — feet close-up

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_renders_final.py 2>&1
"""
import bpy, os, math
from mathutils import Vector, Matrix

HOME   = os.path.expanduser("~")
REPO   = f"{HOME}/godwyn-boss-fight"
OUTGLB = f"{REPO}/models/godwyn_game.glb"
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
    raise RuntimeError("no EEVEE engine")


# ================================================================
# Import GLB
# ================================================================
print(f"[render] importing {OUTGLB}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUTGLB)
scn = bpy.context.scene
bpy.context.view_layer.update()

meshes = [o for o in scn.objects if o.type == 'MESH']
arm    = next((o for o in scn.objects if o.type == 'ARMATURE'), None)
print(f"[render] meshes={[o.name for o in meshes]}  arm={arm.name if arm else None}")

# Remove stray Icosphere
for o in list(scn.objects):
    if o.type == 'MESH' and o.name not in {'char1', 'Godwyn_Sword', 'Godwyn_Gauntlet'}:
        print(f"[render] removing stray: {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

char1 = bpy.data.objects.get('char1')
sword = bpy.data.objects.get('Godwyn_Sword')
assert char1 is not None, "char1 missing"
assert sword is not None, "Godwyn_Sword missing"

# ================================================================
# Bounding boxes
# ================================================================
bpy.context.view_layer.update()
c1pts  = [char1.matrix_world @ Vector(c) for c in char1.bound_box]
bbmin  = Vector((min(p.x for p in c1pts), min(p.y for p in c1pts), min(p.z for p in c1pts)))
bbmax  = Vector((max(p.x for p in c1pts), max(p.y for p in c1pts), max(p.z for p in c1pts)))
H      = bbmax.z - bbmin.z
W      = bbmax.x - bbmin.x
ctr    = (bbmin + bbmax) / 2
print(f"[render] char1 bbox: H={H:.3f} W={W:.3f} center={tuple(round(v,3) for v in ctr)}")
print(f"[render] char1 bbox min={tuple(round(v,2) for v in bbmin)}  max={tuple(round(v,2) for v in bbmax)}")

# ================================================================
# Scene setup
# ================================================================
pick_eevee(scn)
scn.render.image_settings.file_format = "PNG"
scn.render.resolution_x = 1024
scn.render.resolution_y = 1024
scn.render.film_transparent = False
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"

# World — dark fantasy
w = bpy.data.worlds.new("GameWorld")
scn.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value    = (0.008, 0.010, 0.020, 1.0)
    bg.inputs["Strength"].default_value = 0.3

# Key light: strong front-left above
bpy.ops.object.light_add(type='AREA', location=(2.0, -3.0, 4.0))
key = bpy.context.active_object
key.data.energy = 1200.0
key.data.size   = 2.0
key.rotation_euler = (math.radians(40), 0, math.radians(30))

# Fill light: right, softer
bpy.ops.object.light_add(type='AREA', location=(-2.5, -2.0, 2.5))
fill = bpy.context.active_object
fill.data.energy = 400.0
fill.data.size   = 3.0

# Rim light: back-right, blue tint
bpy.ops.object.light_add(type='AREA', location=(1.5, 3.0, 3.0))
rim = bpy.context.active_object
rim.data.energy = 300.0
rim.data.size   = 2.0
rim.data.color  = (0.6, 0.7, 1.0)

# Ground fill: below, subtle
bpy.ops.object.light_add(type='AREA', location=(0, 0, -0.5))
gnd = bpy.context.active_object
gnd.data.energy = 80.0
gnd.data.size   = 4.0


def look_at_point(cam_loc, target):
    """Return euler rotation for camera at cam_loc pointing at target."""
    direction = (target - cam_loc).normalized()
    # Blender camera points -Z in local space, up is +Y
    rot_quat = direction.to_track_quat('-Z', 'Y')
    return rot_quat.to_euler()


def add_camera(name, loc, target):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = name
    cam.rotation_euler = look_at_point(Vector(loc), Vector(target))
    cam.data.clip_start = 0.01
    cam.data.clip_end   = 100.0
    return cam


def render_shot(cam_obj, outpath, lens=85):
    cam_obj.data.lens = lens
    scn.camera = cam_obj
    scn.render.filepath = outpath
    bpy.ops.render.render(write_still=True)
    print(f"[render] wrote {outpath}")


# ================================================================
# Shot 1: Full body FRONT
# ================================================================
# Character faces -Y. Camera at front (-Y side), looking +Y toward char.
dist = H * 1.35
cam_front = add_camera(
    "cam_front",
    loc=(ctr.x, ctr.y - dist, ctr.z + H * 0.04),
    target=(ctr.x, ctr.y, ctr.z + H * 0.04),
)
render_shot(cam_front, f"{OUTDIR}/p4final_front.png", lens=85)

# ================================================================
# Shot 2: Full body 3/4 (from front-left, 45 deg)
# ================================================================
angle_deg = 45
angle_rad  = math.radians(angle_deg)
# Camera swings 45 deg LEFT from front
cam3q_x = ctr.x - dist * math.sin(angle_rad)
cam3q_y = ctr.y - dist * math.cos(angle_rad)
cam3q_z = ctr.z + H * 0.06
cam_3q = add_camera(
    "cam_3q",
    loc=(cam3q_x, cam3q_y, cam3q_z),
    target=(ctr.x, ctr.y, ctr.z + H * 0.06),
)
render_shot(cam_3q, f"{OUTDIR}/p4final_3q.png", lens=85)

# ================================================================
# Shot 3: Hand + Sword — right arm/hand region
# ================================================================
# From bone probe: RightHand head world = (-0.468, -0.225, 1.661)
# Character faces -Y. The Mixamo rig has RightHand on the character's
# RIGHT which maps to world -X (because Mixamo is Y-forward).
# Hand is at z=1.661 (~waist), x=-0.468. Sword hangs down from there.
# Target the zone from hand down to include sword blade: z ~ 1.2-1.6
# Hand at world (-0.47, -0.22, 1.66). Sword hangs below ~z=0.5-1.6.
# Target the center of hand+sword region, camera pulled further left/front.
hand_target = Vector((-0.55, -0.15, 1.1))
hand_cam_loc = Vector((-0.55 - 1.0, -0.15 - 1.2, 1.1 + 0.0))
cam_sword = add_camera(
    "cam_sword",
    loc=tuple(hand_cam_loc),
    target=tuple(hand_target),
)
render_shot(cam_sword, f"{OUTDIR}/p4final_handsword.png", lens=70)

# ================================================================
# Shot 4: Feet close-up
# ================================================================
feet_target = Vector((ctr.x, ctr.y, bbmin.z + H * 0.14))
feet_cam_loc = Vector((ctr.x, ctr.y - H * 0.65, bbmin.z + H * 0.25))
cam_feet = add_camera(
    "cam_feet",
    loc=tuple(feet_cam_loc),
    target=tuple(feet_target),
)
render_shot(cam_feet, f"{OUTDIR}/p4final_feet.png", lens=90)

print(f"\n[render] === ALL RENDERS DONE ===")
print(f"  {OUTDIR}/p4final_front.png")
print(f"  {OUTDIR}/p4final_3q.png")
print(f"  {OUTDIR}/p4final_handsword.png")
print(f"  {OUTDIR}/p4final_feet.png")
