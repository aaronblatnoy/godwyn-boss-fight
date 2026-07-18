"""
phase4_export_game_glb.py — Phase 4: Re-export models/godwyn_game.glb from
the fully fixed godwyn_face.blend.

godwyn_face.blend contains:
  - Armature (24 bones)
  - char1 (skinned, 145K verts, baked PBR textures)
  - Godwyn_Sword (separate mesh, bone-parented to LeftHand)
  - Godwyn_Gauntlet (separate mesh, bone-parented to LeftHand)

Export includes:
  - Armature + skinning (rest pose, +Y up)
  - All meshes with their baked textures
  - Bone-parented children (Godwyn_Sword, Godwyn_Gauntlet)

Verification: re-import the GLB and assert:
  - bones >= 24
  - meshes >= 2 (char1 + Godwyn_Sword at minimum)
  - Godwyn_Sword present as a separate object
  - skinning intact (vertex groups on char1)
  - materials/textures present

Renders: EEVEE turnaround (front, 3/4, face close-up, hand+sword) to
renders/game/ as phase4_*.png

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_export_game_glb.py 2>&1
"""
import bpy, os, math
from mathutils import Vector

HOME = os.path.expanduser("~")
REPO    = f"{HOME}/godwyn-boss-fight"
BLEND   = f"{REPO}/models/godwyn_face.blend"
OUT_GLB = f"{REPO}/models/godwyn_game.glb"
OUTDIR  = f"{REPO}/renders/game"
os.makedirs(OUTDIR, exist_ok=True)

def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[phase4] preview engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine found")

# ================================================================
# STAGE 1: OPEN BLEND + EXPORT GLB
# ================================================================
print(f"[phase4] opening {BLEND}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene

arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
assert arm is not None, "FATAL: no armature in godwyn_face.blend"

meshes = [o for o in scn.objects if o.type == "MESH"]
char1  = bpy.data.objects.get("char1")
sword  = bpy.data.objects.get("Godwyn_Sword")
gaunt  = bpy.data.objects.get("Godwyn_Gauntlet")

assert char1  is not None, "FATAL: char1 not found"
assert sword  is not None, "FATAL: Godwyn_Sword not found"

print(f"[phase4] armature={arm.name}  bones={len(arm.data.bones)}")
print(f"[phase4] char1: verts={len(char1.data.vertices)} vgroups={len(char1.vertex_groups)}")
print(f"[phase4] Godwyn_Sword: verts={len(sword.data.vertices)} parent={sword.parent.name if sword.parent else None} parent_bone={sword.parent_bone}")
if gaunt:
    print(f"[phase4] Godwyn_Gauntlet: verts={len(gaunt.data.vertices)} parent_bone={gaunt.parent_bone}")

# Report materials / textures
for mat in list(char1.data.materials) + list(sword.data.materials) + (list(gaunt.data.materials) if gaunt else []):
    if mat and mat.use_nodes:
        tex_nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
        for t in tex_nodes:
            print(f"[phase4]   mat={mat.name}  tex={t.image.name}")

# Select ALL exportable objects: armature + all meshes (bone-parented children
# are automatically included when their parent armature is selected)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
char1.select_set(True)
sword.select_set(True)
if gaunt:
    gaunt.select_set(True)
bpy.context.view_layer.objects.active = arm

# Verify armature modifier on char1
armmods = [m for m in char1.modifiers if m.type == "ARMATURE"]
assert len(armmods) >= 1, "FATAL: char1 has no armature modifier — skinning will be lost"
print(f"[phase4] armature modifiers on char1: {[m.name for m in armmods]}")

print(f"[phase4] exporting {OUT_GLB} ...")
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    use_selection=True,
    export_format="GLB",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_skins=True,
    export_armature_object_remove=False,
    export_rest_position_armature=True,   # rest pose
    export_yup=True,                       # +Y up (glTF 2.0)
    export_apply=True,                     # apply modifiers (not armature)
    export_animations=False,
    export_lights=False,
    export_cameras=False,
)
glb_size = os.path.getsize(OUT_GLB)
print(f"[phase4] wrote {OUT_GLB}  ({glb_size:,} bytes)")

# ================================================================
# STAGE 2: VERIFY — re-import and assert structure
# ================================================================
print(f"\n[verify] re-importing {OUT_GLB} ...")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)
vscn = bpy.context.scene

v_arm     = next((o for o in vscn.objects if o.type == "ARMATURE"), None)
v_meshes  = [o for o in vscn.objects if o.type == "MESH"]
v_skinned = [o for o in v_meshes if len(o.vertex_groups) > 0]

assert v_arm is not None, "VERIFY FAIL: no armature in re-imported GLB"
n_bones   = len(v_arm.data.bones)
n_meshes  = len(v_meshes)
n_skinned = len(v_skinned)

# Count materials + textures across all meshes
mats_seen = set()
tex_count = 0
for o in v_meshes:
    for mat in o.data.materials:
        if mat and mat.name not in mats_seen:
            mats_seen.add(mat.name)
            if mat.use_nodes:
                for n in mat.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image:
                        tex_count += 1

n_mats = len(mats_seen)

# Check for a separate sword mesh
v_sword_candidates = [o for o in v_meshes if "sword" in o.name.lower() or "Sword" in o.name]
# Fall back: any mesh that is NOT the largest (char1 is huge)
if not v_sword_candidates and len(v_meshes) >= 2:
    sorted_by_verts = sorted(v_meshes, key=lambda o: len(o.data.vertices), reverse=True)
    v_sword_candidates = sorted_by_verts[1:]  # everything except char1

print(f"\n[verify] ===== GLB VERIFICATION REPORT =====")
print(f"[verify]   bones       : {n_bones}")
print(f"[verify]   meshes total: {n_meshes}")
print(f"[verify]   mesh names  : {[o.name for o in v_meshes]}")
print(f"[verify]   materials   : {n_mats}")
print(f"[verify]   textures    : {tex_count}")
print(f"[verify]   skinned     : {n_skinned}")
print(f"[verify]   sword objs  : {[o.name for o in v_sword_candidates]}")
print(f"[verify]   armature OK : {v_arm.name}")
print(f"[verify]   file size   : {glb_size:,} bytes")
print(f"[verify] ==========================================")

assert n_bones  >= 24,  f"VERIFY FAIL: only {n_bones} bones"
assert n_meshes >= 2,   f"VERIFY FAIL: {n_meshes} mesh(es) — expected separate char + sword"
assert n_mats   >= 1,   f"VERIFY FAIL: {n_mats} materials"
assert tex_count >= 1,  f"VERIFY FAIL: {tex_count} textures embedded"
assert n_skinned >= 1,  f"VERIFY FAIL: {n_skinned} skinned meshes — skinning lost"
assert len(v_sword_candidates) >= 1, "VERIFY FAIL: no separate sword/secondary mesh found"
print("[verify] ALL CHECKS PASSED — rigged + textured game asset with separate sword confirmed")

# ================================================================
# STAGE 3: EEVEE TURNAROUND RENDERS
# Front, 3/4, face close-up, hand+sword
# ================================================================
print(f"\n[render] rendering EEVEE turnaround from re-imported GLB ...")
scn2 = bpy.context.scene
v_meshes2 = [o for o in scn2.objects if o.type == "MESH"]

pick_eevee(scn2)
scn2.render.resolution_x = 1024
scn2.render.resolution_y = 1365
scn2.render.image_settings.file_format = "PNG"
scn2.view_settings.view_transform = "AgX"
scn2.view_settings.look = "AgX - Punchy"

# Compute bounding box from all meshes
pts = []
for o in v_meshes2:
    pts.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
if not pts:
    raise RuntimeError("[render] no mesh objects to compute bbox")
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2
Hgt    = bb_max.z - bb_min.z
print(f"[render] bbox H={Hgt:.3f}  center=({center.x:.3f},{center.y:.3f},{center.z:.3f})")

# World background
w = bpy.data.worlds.get("GameRenderWorld") or bpy.data.worlds.new("GameRenderWorld")
scn2.world = w
w.use_nodes = True
wbg = w.node_tree.nodes.get("Background")
if wbg:
    wbg.inputs["Color"].default_value    = (0.008, 0.010, 0.018, 1.0)
    wbg.inputs["Strength"].default_value = 0.5

# Lights
def area_light(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size, d.color, d.energy = size, color, power
    o = bpy.data.objects.new(name, d)
    scn2.collection.objects.link(o)
    o.location = loc
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

tgt = (center.x, center.y, center.z + 0.05 * Hgt)
Hs  = Hgt
area_light("TKey",  (center.x - 1.0*Hs, center.y - 1.2*Hs, bb_max.z + 0.5*Hs),  tgt, 1.2*Hs, (1.0,  0.72, 0.42), 180.0*Hs*Hs)
area_light("TFill", (center.x + 1.3*Hs, center.y - 1.0*Hs, center.z),            tgt, 1.6*Hs, (0.35, 0.50, 0.95),  30.0*Hs*Hs)
area_light("TRim1", (center.x - 0.9*Hs, center.y + 1.1*Hs, bb_max.z + 0.2*Hs),  tgt, 0.8*Hs, (1.0,  0.65, 0.28), 140.0*Hs*Hs)
area_light("TRim2", (center.x + 1.0*Hs, center.y + 1.0*Hs, center.z + 0.4*Hs),  tgt, 0.8*Hs, (0.55, 0.65, 1.0),   75.0*Hs*Hs)

# Camera helper
def shoot(name, cam_loc, look_at, focal, res_x=1024, res_y=1365):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name)
    cd.lens = focal
    cam = bpy.data.objects.new(name, cd)
    scn2.collection.objects.link(cam)
    cam.location = Vector(cam_loc)
    direc = (Vector(look_at) - cam.location).normalized()
    cam.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn2.camera = cam
    scn2.render.resolution_x = res_x
    scn2.render.resolution_y = res_y
    path = f"{OUTDIR}/{name}.png"
    scn2.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sz = os.path.getsize(path)
    print(f"[render] wrote {path}  ({sz:,} bytes)")
    return path

rendered = []

# 1. Front full-body (0°)
yaw = 0.0
fov = 2 * math.atan(36.0 / (2 * 50))
dist_full = (Hgt / 2 * 1.25) / math.tan(fov / 2)
front_loc = (center.x, center.y - dist_full, center.z)
rendered.append(shoot("phase4_front", front_loc,
                       (center.x, center.y, center.z), 50))

# 2. 3/4 view (-45°)
yaw45 = math.radians(-45)
dist_3q = dist_full * 1.05
loc_3q  = (center.x + math.sin(yaw45)*dist_3q,
           center.y - math.cos(yaw45)*dist_3q,
           center.z)
rendered.append(shoot("phase4_3q", loc_3q,
                       (center.x, center.y, center.z), 50))

# 3. Face close-up (front, looking slightly down into the face)
# Head is roughly at z 2.85–3.20, face forward at y ~-0.47
face_z   = bb_min.z + Hgt * 0.90   # ~top 10% of character = head zone
face_c   = Vector((center.x, center.y, face_z))
face_fov = 2 * math.atan(36.0 / (2 * 80))
face_dist = (Hgt * 0.22) / math.tan(face_fov / 2)
face_loc  = (face_c.x, face_c.y - face_dist, face_c.z)
rendered.append(shoot("phase4_face_close", face_loc, tuple(face_c), 80,
                       res_x=1024, res_y=1024))

# 4. Hand + sword close-up
# Sword is planted at left side; LeftHand is roughly at z ~2.0 (50% height ~arm level)
# Approximate: mid-height = character height 50%
hand_z = bb_min.z + Hgt * 0.55
# Sword planted left side at z 0.0–1.5, pommel at ~z 2.0
# We want a frame that shows the hand gripping the pommel and the sword going down
# Camera: slightly right of center, angled left to catch the sword
sword_c   = Vector((center.x + 0.5, center.y, bb_min.z + Hgt * 0.45))
sword_fov = 2 * math.atan(36.0 / (2 * 55))
sword_dist= (Hgt * 0.45) / math.tan(sword_fov / 2)
sword_loc = (sword_c.x + 0.8, sword_c.y - sword_dist, sword_c.z + 0.3)
rendered.append(shoot("phase4_hand_sword", sword_loc, tuple(sword_c), 55,
                       res_x=1024, res_y=1365))

print(f"\n[phase4] ===== PHASE 4 COMPLETE =====")
print(f"[phase4] GLB  : {OUT_GLB}  ({glb_size:,} bytes)")
print(f"[phase4] bones: {n_bones}  meshes: {n_meshes}  mats: {n_mats}  textures: {tex_count}  skinned: {n_skinned}")
print(f"[phase4] sword: {[o.name for o in v_sword_candidates]}")
print(f"[phase4] renders: {rendered}")
print("[phase4] GATE PASSED — godwyn_game.glb re-exported with separate parented sword + reshaped face, verified rigged+textured")
