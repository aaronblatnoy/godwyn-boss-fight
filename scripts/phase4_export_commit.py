"""
phase4_export_commit.py — Phase 4: Clean re-export from godwyn_st_feet.blend.

Source: godwyn_st_feet.blend
  - 121 bones: 24 Mixamo + 97 phys_ chains (robe/cape/hair)
  - char1 skinned with 121 vertex groups
  - Godwyn_Sword parented to RightHand bone
  - Feet fixed at 6 deg natural outward toe
  - GodwynGameMat + godwyn_albedo + godwyn_metallic-roughness textures

Export: godwyn_game.glb
  - glTF 2.0, +Y up, rest pose, armature NOT applied
  - Baked textures embedded

Then: EEVEE turnaround (front, 3/4, hand+sword, feet) -> renders/game/

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_export_commit.py 2>&1
"""
import bpy, os, math
from mathutils import Vector

HOME   = os.path.expanduser("~")
REPO   = f"{HOME}/godwyn-boss-fight"
SRC    = f"{REPO}/models/godwyn_st_feet.blend"
OUTGLB = f"{REPO}/models/godwyn_game.glb"
OUTDIR = f"{REPO}/renders/game"
os.makedirs(OUTDIR, exist_ok=True)


def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[export] render engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine found")


# ================================================================
# STAGE 1: Open source blend, verify, export
# ================================================================
print(f"\n[export] === STAGE 1: opening {SRC} ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=SRC)
scn = bpy.context.scene
bpy.context.view_layer.update()

arm   = next((o for o in scn.objects if o.type == 'ARMATURE'), None)
char1 = bpy.data.objects.get('char1')
sword = bpy.data.objects.get('Godwyn_Sword')

assert arm   is not None, "FATAL: no armature"
assert char1 is not None, "FATAL: no char1 mesh"
assert sword is not None, "FATAL: no Godwyn_Sword"

n_bones  = len(arm.data.bones)
n_chains = sum(1 for b in arm.data.bones if any(b.name.startswith(p) for p in ('phys_', 'robe_', 'cape_', 'hair_', 'cloth_')))
n_vg     = len(char1.vertex_groups)

print(f"[export] armature: {arm.name}  total_bones={n_bones}  chain_bones={n_chains}")
print(f"[export] char1 vgroups={n_vg}  verts={len(char1.data.vertices)}")
print(f"[export] Godwyn_Sword parent={sword.parent.name if sword.parent else None}  parent_type={sword.parent_type}  parent_bone={sword.parent_bone}")
print(f"[export] materials: {[m.name for m in bpy.data.materials]}")
print(f"[export] images: {[(i.name, i.size[:]) for i in bpy.data.images]}")

# Sanity checks
assert n_bones == 121,  f"Expected 121 bones, got {n_bones}"
assert n_vg    >= 100,  f"Expected >=100 vertex groups, got {n_vg}"
assert sword.parent_type == 'BONE', f"Sword must be BONE-parented, got {sword.parent_type}"
assert sword.parent_bone == 'RightHand', f"Sword parent_bone must be RightHand, got {sword.parent_bone}"

# Verify feet fix
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for side in ('Left', 'Right'):
    tbn = side + 'ToeBase'
    if tbn in arm.pose.bones:
        pb = arm.pose.bones[tbn]
        d  = (arm.matrix_world @ pb.tail) - (arm.matrix_world @ pb.head)
        d.z = 0.0
        if d.length > 0:
            d   = d.normalized()
            ang = math.degrees(math.atan2(d.x, -d.y))
            print(f"[export] {tbn} splay = {ang:.1f} deg (expect ~6 or ~-6)")
bpy.ops.object.mode_set(mode='OBJECT')

# ================================================================
# STAGE 2: Export GLB
# ================================================================
print(f"\n[export] === STAGE 2: exporting {OUTGLB} ===")

# Pack images so they embed in the GLB
for img in bpy.data.images:
    if img.source == 'FILE' and not img.packed_file:
        try:
            img.pack()
            print(f"[export] packed image: {img.name}")
        except Exception as e:
            print(f"[export] WARNING: could not pack {img.name}: {e}")

bpy.ops.export_scene.gltf(
    filepath=OUTGLB,
    export_format="GLB",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_skins=True,
    export_armature_object_remove=False,
    export_rest_position_armature=True,
    export_yup=True,
    export_apply=False,          # do NOT apply armature modifier
    export_animations=False,
    export_lights=False,
    export_cameras=False,
)

glb_size = os.path.getsize(OUTGLB)
print(f"[export] wrote {OUTGLB}  ({glb_size:,} bytes)")
assert glb_size > 5_000_000, f"GLB too small ({glb_size:,} bytes) — likely missing data"

# ================================================================
# STAGE 3: Verify by re-import
# ================================================================
print(f"\n[export] === STAGE 3: verifying re-import ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUTGLB)

objects   = list(bpy.data.objects)
armatures = [o for o in objects if o.type == 'ARMATURE']
meshes    = [o for o in objects if o.type == 'MESH']
materials = list(bpy.data.materials)
images    = list(bpy.data.images)

print(f"[verify] objects={len(objects)}  armatures={len(armatures)}  meshes={len(meshes)}")
print(f"[verify] materials={[m.name for m in materials]}")
print(f"[verify] images={len(images)}: {[(i.name, f'{i.size[0]}x{i.size[1]}', 'packed' if i.packed_file else 'extern') for i in images]}")

for arm2 in armatures:
    bones2 = list(arm2.data.bones)
    chains2 = [b for b in bones2 if any(b.name.startswith(p) for p in ('phys_', 'robe_', 'cape_', 'hair_', 'cloth_'))]
    print(f"[verify] armature '{arm2.name}': total={len(bones2)}  chain={len(chains2)}")
    assert len(bones2) == 121, f"Expected 121 bones in re-import, got {len(bones2)}"

for mo in meshes:
    skin = [m for m in mo.modifiers if m.type == 'ARMATURE']
    vg   = list(mo.vertex_groups)
    print(f"[verify] mesh '{mo.name}': verts={len(mo.data.vertices)} vgroups={len(vg)} arm_mods={len(skin)} parent={mo.parent.name if mo.parent else None} parent_type={mo.parent_type} parent_bone={mo.parent_bone}")

sword2 = bpy.data.objects.get('Godwyn_Sword')
assert sword2 is not None, "FATAL: Godwyn_Sword missing from re-import"
assert sword2.parent_type == 'BONE', f"Sword parent_type in re-import: {sword2.parent_type}"
assert sword2.parent_bone == 'RightHand', f"Sword parent_bone in re-import: {sword2.parent_bone}"
print(f"[verify] Godwyn_Sword OK: parent_type=BONE parent_bone=RightHand")
assert len(images) >= 1, "No textures in re-import"
print(f"[verify] textures OK: {len(images)} images")
print("[verify] ALL CHECKS PASSED")

# ================================================================
# STAGE 4: EEVEE Turnaround renders from re-imported GLB
# ================================================================
print(f"\n[export] === STAGE 4: EEVEE turnaround renders ===")
scn = bpy.context.scene
pick_eevee(scn)
scn.render.image_settings.file_format = "PNG"
scn.render.resolution_x = 1024
scn.render.resolution_y = 1024
scn.render.film_transparent = False
scn.view_settings.view_transform = "AgX"
scn.view_settings.look = "AgX - Punchy"

# World
w = bpy.data.worlds.new("GameWorld")
scn.world = w
w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value    = (0.008, 0.010, 0.018, 1.0)
    bg.inputs["Strength"].default_value = 0.4

# Key light
bpy.ops.object.light_add(type='AREA', location=(2.5, -2.0, 3.5))
key = bpy.context.active_object
key.data.energy = 800.0
key.data.size   = 2.0
key.rotation_euler = (math.radians(45), 0, math.radians(30))

# Fill light
bpy.ops.object.light_add(type='AREA', location=(-2.5, -1.5, 2.0))
fill = bpy.context.active_object
fill.data.energy = 300.0
fill.data.size   = 3.0

# Rim light
bpy.ops.object.light_add(type='AREA', location=(0, 2.5, 2.5))
rim = bpy.context.active_object
rim.data.energy = 200.0
rim.data.color  = (0.6, 0.7, 1.0)

# Char bbox for framing
char1b = bpy.data.objects.get('char1')
assert char1b is not None, "char1 missing after re-import"
bpy.context.view_layer.update()
pts   = [char1b.matrix_world @ Vector(c) for c in char1b.bound_box]
bbmin = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bbmax = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
H     = bbmax.z - bbmin.z
ctr   = (bbmin + bbmax) / 2
print(f"[render] char1 bbox H={H:.3f}  center={tuple(round(v,3) for v in ctr)}")

def add_camera(name, loc, rot_euler):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = name
    cam.rotation_euler = rot_euler
    cam.data.lens = 85
    cam.data.clip_start = 0.01
    cam.data.clip_end   = 100.0
    return cam

def render_shot(cam_obj, outpath):
    scn.camera = cam_obj
    scn.render.filepath = outpath
    bpy.ops.render.render(write_still=True)
    print(f"[render] wrote {outpath}")

# ---- Shot 1: Full body FRONT ----
dist1 = H * 1.3
cam_front = add_camera(
    "cam_front",
    loc=(0, -dist1, ctr.z + H * 0.05),
    rot_euler=(math.radians(90), 0, 0),
)
render_shot(cam_front, f"{OUTDIR}/p4final_front.png")

# ---- Shot 2: Full body 3/4 ----
ang = math.radians(-45)
cam_3q = add_camera(
    "cam_3q",
    loc=(dist1 * math.sin(-ang), -dist1 * math.cos(-ang), ctr.z + H * 0.1),
    rot_euler=(math.radians(80), 0, math.radians(-45)),
)
render_shot(cam_3q, f"{OUTDIR}/p4final_3q.png")

# ---- Shot 3: Hand + Sword close-up ----
# Right hand region - upper body right side
swd_obj = bpy.data.objects.get('Godwyn_Sword')
if swd_obj:
    spts  = [swd_obj.matrix_world @ Vector(c) for c in swd_obj.bound_box]
    sctr  = (Vector((min(p.x for p in spts), min(p.y for p in spts), min(p.z for p in spts))) +
             Vector((max(p.x for p in spts), max(p.y for p in spts), max(p.z for p in spts)))) / 2
else:
    sctr = ctr + Vector((0.3, 0, H * 0.2))
cam_sword = add_camera(
    "cam_sword",
    loc=(sctr.x + 0.5, sctr.y - 1.0, sctr.z + 0.1),
    rot_euler=(math.radians(85), 0, math.radians(30)),
)
cam_sword.data.lens = 120
render_shot(cam_sword, f"{OUTDIR}/p4final_handsword.png")

# ---- Shot 4: Feet close-up ----
feet_ctr = Vector((ctr.x, ctr.y, bbmin.z + H * 0.12))
cam_feet = add_camera(
    "cam_feet",
    loc=(0, -H * 0.7, bbmin.z + H * 0.2),
    rot_euler=(math.radians(75), 0, 0),
)
cam_feet.data.lens = 85
render_shot(cam_feet, f"{OUTDIR}/p4final_feet.png")

print(f"\n[export] === PHASE 4 COMPLETE ===")
print(f"  GLB:     {OUTGLB}  ({glb_size:,} bytes)")
print(f"  Renders: {OUTDIR}/p4final_{{front,3q,handsword,feet}}.png")
print(f"  Bones:   121 (24 Mixamo + 97 chains)")
print(f"  Sword:   Godwyn_Sword parented to RightHand bone")
print(f"  Feet:    fixed 6 deg natural outward toe")
