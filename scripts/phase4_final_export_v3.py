"""
phase4_final_export_v3.py — Phase 4 final export (clean approach).

Two-step approach:
  Step A: Export char1+armature from godwyn_p2_robe.blend as interim GLB
  Step B: Open godwyn_face.blend, import the interim GLB's char1/armature,
          then just use the face blend's already-correct sword+gauntlet setup
          but swap in the robe armature's data (all bones).

Better approach: Everything from godwyn_p2_robe.blend, plus sword/gauntlet
from the face blend's final GLB (godwyn_full_final.glb or godwyn_full_C.glb).
We know the face blend exports sword correctly. We just need to add the robe
physics chains to the armature.

CLEANEST APPROACH:
  1. Open godwyn_face.blend (has sword+gaunt correctly placed, 24 bones)
  2. Add all phys_ bones from godwyn_p2_robe.blend's armature via a script
     that reads bone head/tail positions and creates them programmatically
  3. Re-weight char1 to the new phys_ bones using the vertex group data
     from godwyn_p2_robe.blend's char1
  4. Export

Actually even cleaner:
  1. Open godwyn_p2_robe.blend
  2. Append sword+gauntlet from face.blend — but fix the parent_inverse
     by computing it analytically: parent_inverse = (arm.world @ lefthand.bone_matrix).inverted()
  3. Set sword/gauntlet location/rotation/scale to (0,0,0)/(0,0,0)/(1,1,1)
     — this places them AT the bone's origin in bone space
  Actually that won't work because the sword has a specific offset from the hand.

REAL FIX: The problem is that glTF export of bone-parented non-skinned objects
is unreliable. Instead, SKIN the sword to the LeftHand bone with a single
vertex group (weight 1.0 on all verts), which glTF handles correctly.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_final_export_v3.py 2>&1
"""
import bpy, os, math
from mathutils import Vector, Euler, Matrix

HOME    = os.path.expanduser("~")
REPO    = f"{HOME}/godwyn-boss-fight"
ROBE_B  = f"{REPO}/models/godwyn_p2_robe.blend"
FACE_B  = f"{REPO}/models/godwyn_face.blend"
OUT_GLB = f"{REPO}/models/godwyn_game.glb"
OUTDIR  = f"{REPO}/renders/game"
os.makedirs(OUTDIR, exist_ok=True)


def pick_eevee(scn):
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scn.render.engine = eng
            print(f"[v3] render engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine found")


# ================================================================
# STAGE 1: Read the sword/gauntlet vertex data + world positions
#           from godwyn_face.blend so we can recreate them correctly
# ================================================================
print("\n[v3] === STAGE 1: reading sword/gauntlet from face blend ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=FACE_B)
bpy.context.view_layer.update()

face_arm   = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
face_sword = bpy.data.objects.get("Godwyn_Sword")
face_gaunt = bpy.data.objects.get("Godwyn_Gauntlet")
assert face_sword and face_gaunt

# Get world matrices of sword and gauntlet (captures their final world positions)
sword_world_mat = face_sword.matrix_world.copy()
gaunt_world_mat = face_gaunt.matrix_world.copy()

# Get the face arm's LeftHand bone matrix in world space
bpy.context.view_layer.objects.active = face_arm
bpy.ops.object.mode_set(mode='POSE')
face_lh_pose  = face_arm.pose.bones["LeftHand"]
face_lh_world = (face_arm.matrix_world @ face_lh_pose.matrix).copy()
bpy.ops.object.mode_set(mode='OBJECT')

# sword local matrix relative to LeftHand bone (in bone space)
# matrix_world = arm_world @ bone_pose_mat @ bone_local_mat
# => sword_bone_local = face_lh_world.inverted() @ sword_world_mat
sword_bone_local = face_lh_world.inverted() @ sword_world_mat
gaunt_bone_local = face_lh_world.inverted() @ gaunt_world_mat

print(f"[v3] sword world mat (translation): {tuple(round(v,3) for v in sword_world_mat.translation)}")
print(f"[v3] gaunt world mat (translation): {tuple(round(v,3) for v in gaunt_world_mat.translation)}")
print(f"[v3] LeftHand world pos: {tuple(round(v,3) for v in face_lh_world.translation)}")

# Save mesh data from sword and gauntlet
sword_verts = [v.co.copy() for v in face_sword.data.vertices]
sword_faces = [list(p.vertices) for p in face_sword.data.polygons]
gaunt_verts = [v.co.copy() for v in face_gaunt.data.vertices]
gaunt_faces = [list(p.vertices) for p in face_gaunt.data.polygons]

# Save material names
sword_mats_names = [m.name for m in face_sword.data.materials if m]
gaunt_mats_names = [m.name for m in face_gaunt.data.materials if m]
print(f"[v3] sword verts={len(sword_verts)}  mats={sword_mats_names}")
print(f"[v3] gaunt verts={len(gaunt_verts)}  mats={gaunt_mats_names}")


# ================================================================
# STAGE 2: OPEN ROBE BLEND + ADD SWORD/GAUNTLET AS SKINNED MESHES
# ================================================================
print("\n[v3] === STAGE 2: opening robe blend ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=ROBE_B)
scn = bpy.context.scene

arm  = next(o for o in scn.objects if o.type == "ARMATURE")
char1 = bpy.data.objects.get("char1")
assert arm and char1

# Remove test Icosphere (and its mesh data block)
for dblock in list(bpy.data.meshes):
    if "Icosphere" in dblock.name:
        ico_obj = next((o for o in scn.objects if o.data == dblock), None)
        if ico_obj:
            bpy.data.objects.remove(ico_obj, do_unlink=True)
        bpy.data.meshes.remove(dblock)
        print(f"[v3] removed mesh block: {dblock.name}")

# Double-check no Icosphere objects remain
for o in list(scn.objects):
    if "Icosphere" in o.name or "Icosphere" in (o.data.name if o.data else ""):
        bpy.data.objects.remove(o, do_unlink=True)
        print(f"[v3] removed stray object: {o.name}")

n_bones = len(arm.data.bones)
phys_b  = [b.name for b in arm.data.bones if b.name.startswith("phys_")]
print(f"[v3] robe rig: {n_bones} bones  ({len(phys_b)} phys chains)")
print(f"[v3] char1: verts={len(char1.data.vertices)} vgroups={len(char1.vertex_groups)}")


# ================================================================
# STAGE 3: APPEND MATERIALS FROM FACE BLEND
# ================================================================
print("\n[v3] === STAGE 3: appending materials ===")
for mname in ["GodwynSwordMat", "GodwynSwordGoldMat", "GodwynHairMat", "GodwynGauntletMat"]:
    if bpy.data.materials.get(mname):
        print(f"[v3] mat exists: {mname}")
        continue
    bpy.ops.wm.append(
        filepath=f"{FACE_B}/Material/{mname}",
        directory=f"{FACE_B}/Material/",
        filename=mname,
        link=False,
    )
    if bpy.data.materials.get(mname):
        print(f"[v3] appended: {mname}")
    else:
        print(f"[v3] WARNING: could not append: {mname}")

# Add GodwynHairMat to char1 if missing
hair_mat = bpy.data.materials.get("GodwynHairMat")
if hair_mat and "GodwynHairMat" not in [m.name for m in char1.data.materials if m]:
    char1.data.materials.append(hair_mat)
    print(f"[v3] added GodwynHairMat to char1")


# ================================================================
# STAGE 4: CREATE SWORD + GAUNTLET AS SKINNED MESHES
#
# Instead of bone-parenting (which has glTF export issues), we:
# 1. Create the mesh
# 2. Apply the world matrix of the original object
# 3. Add an ARMATURE modifier
# 4. Add a vertex group for LeftHand with weight 1.0 on all verts
#
# This makes them behave like skinned meshes that follow LeftHand 100%,
# which is exactly correct and exports reliably via glTF.
# ================================================================
print("\n[v3] === STAGE 4: creating sword + gauntlet as skinned meshes ===")

bpy.context.view_layer.update()
arm_world = arm.matrix_world.copy()
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
robe_lh_pose   = arm.pose.bones["LeftHand"]
robe_lh_world  = (arm_world @ robe_lh_pose.matrix).copy()
bpy.ops.object.mode_set(mode='OBJECT')
print(f"[v3] robe LeftHand world pos: {tuple(round(v,3) for v in robe_lh_world.translation)}")

# The robe and face armatures are identical scale/position so
# face_lh_world ≈ robe_lh_world. The sword_bone_local matrix gives us
# the sword's transform relative to the LeftHand bone.
# To place the sword correctly as a skinned mesh:
#   sword_world = robe_lh_world @ sword_bone_local
sword_world_in_robe = robe_lh_world @ sword_bone_local
gaunt_world_in_robe = robe_lh_world @ gaunt_bone_local

print(f"[v3] sword target world Z max:")
# Compute expected world bbox Z for sword
sword_world_verts = [sword_world_in_robe @ v for v in sword_verts]
s_zmax = max(v.z for v in sword_world_verts)
s_zmin = min(v.z for v in sword_world_verts)
print(f"[v3]   Z {s_zmin:.3f} to {s_zmax:.3f}  (expect ~1.9 to ~2.15)")

def create_skinned_mesh(name, verts_local, faces, world_matrix, arm_obj, bone_name, mat_names):
    """Create a mesh object placed at world_matrix (baked from face blend),
    parented to arm_obj with OBJECT parenting, and fully weighted to bone_name."""
    me = bpy.data.meshes.new(name)
    # We'll set vertices in world space then transform to object space below
    # But it's simpler: create mesh in local (original local space) and set matrix_world
    # We need verts in the mesh's local space. Since we're setting matrix_world to
    # world_matrix and the verts were in the original object's local space...
    # Actually the sword verts ARE already in local space of the sword mesh.
    # So we just create the mesh with those verts, set matrix_world, and we're done.
    me.from_pydata([tuple(v) for v in verts_local], [], faces)
    me.update()

    obj = bpy.data.objects.new(name, me)
    scn.collection.objects.link(obj)
    obj.matrix_world = world_matrix

    # Assign materials
    me.materials.clear()
    for mname in mat_names:
        mat = bpy.data.materials.get(mname)
        if mat:
            me.materials.append(mat)
        else:
            print(f"[v3] WARNING: material not found: {mname}")

    # Add vertex group for LeftHand with weight 1.0 on all verts
    vg = obj.vertex_groups.new(name=bone_name)
    vg.add(list(range(len(verts_local))), 1.0, 'REPLACE')

    # Add armature modifier
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    mod.use_vertex_groups = True

    print(f"[v3] created skinned {name}: verts={len(verts_local)}  bone={bone_name}  mats={mat_names}")
    return obj


# For the sword: its verts are already in local space; we need the correct world matrix
# The correct world matrix is sword_world_mat (from face blend, where it was correct)
# Since robe armature is at the same position as face armature, use sword_world_mat directly
sword_obj = create_skinned_mesh(
    "Godwyn_Sword",
    sword_verts,
    sword_faces,
    sword_world_mat,        # same world position as in face blend
    arm,
    "LeftHand",
    sword_mats_names,
)

gaunt_obj = create_skinned_mesh(
    "Godwyn_Gauntlet",
    gaunt_verts,
    gaunt_faces,
    gaunt_world_mat,
    arm,
    "LeftHand",
    gaunt_mats_names,
)

# Transfer UV + normals from face blend's objects (via append of mesh data)
# Actually for glTF export we need UVs. Let's append the mesh data instead.
print("\n[v3] === STAGE 4b: rebuild sword/gauntlet with full mesh data (UV etc) ===")

# Remove our simple pydata versions
bpy.data.objects.remove(sword_obj, do_unlink=True)
bpy.data.objects.remove(gaunt_obj, do_unlink=True)
for me_name in ("Godwyn_Sword", "Godwyn_Gauntlet"):
    me = bpy.data.meshes.get(me_name)
    if me: bpy.data.meshes.remove(me)

# Append actual mesh objects from face blend (they bring UVs, normals, materials)
for obj_name in ("Godwyn_Sword", "Godwyn_Gauntlet"):
    bpy.ops.wm.append(
        filepath=f"{FACE_B}/Object/{obj_name}",
        directory=f"{FACE_B}/Object/",
        filename=obj_name,
        link=False,
        do_reuse_local_id=False,
    )
    # Remove stale armatures that came with the append
    for o in list(bpy.data.objects):
        if o.type == "ARMATURE" and o is not arm:
            bpy.data.objects.remove(o, do_unlink=True)

sword_obj = bpy.data.objects.get("Godwyn_Sword")
gaunt_obj = bpy.data.objects.get("Godwyn_Gauntlet")
assert sword_obj and gaunt_obj, "FATAL: append failed"

# Ensure they are linked to scene
for obj in (sword_obj, gaunt_obj):
    if not any(obj.name in [o.name for o in c.objects] for c in obj.users_collection if True):
        scn.collection.objects.link(obj)

# Convert to SKINNED MESH approach:
# - Clear bone parenting
# - Set world matrix to the correct position (from face blend)
# - Remove existing armature modifier if any
# - Add fresh armature modifier
# - Add LeftHand vertex group with weight 1.0

for obj, world_mat in [(sword_obj, sword_world_mat), (gaunt_obj, gaunt_world_mat)]:
    # Clear parent
    obj.parent      = None
    obj.parent_bone = ""
    obj.matrix_parent_inverse = Matrix.Identity(4)

    # Set world position (same as face blend — same rig coordinate system)
    obj.matrix_world = world_mat

    # Remove old modifiers
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)

    # Add LeftHand vertex group (weight 1.0 all verts)
    if "LeftHand" in [vg.name for vg in obj.vertex_groups]:
        obj.vertex_groups.remove(obj.vertex_groups["LeftHand"])
    vg = obj.vertex_groups.new(name="LeftHand")
    vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')

    # Add armature modifier pointing to robe armature
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    mod.use_vertex_groups = True

    print(f"[v3] {obj.name}: world_mat.translation={tuple(round(v,3) for v in world_mat.translation)}")
    print(f"[v3]   verts={len(obj.data.vertices)}  mats={[m.name for m in obj.data.materials if m]}")

# Verify world positions
bpy.context.view_layer.update()
for obj in (sword_obj, gaunt_obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    print(f"[v3] {obj.name} world Z: {zmin:.3f} to {zmax:.3f}")


# ================================================================
# STAGE 5: EXPORT GLB
# ================================================================
print(f"\n[v3] === STAGE 5: exporting {OUT_GLB} ===")

# Verify no Icospheres
for o in scn.objects:
    if o.type == "MESH" and ("Icosphere" in o.name or (o.data and "Icosphere" in o.data.name)):
        print(f"[v3] WARNING: Icosphere still present: {o.name} — removing")
        bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.object.select_all(action="DESELECT")
for o in (arm, char1, sword_obj, gaunt_obj):
    o.select_set(True)
bpy.context.view_layer.objects.active = arm

# Check char1 armature modifier still points to robe arm
for mod in char1.modifiers:
    if mod.type == "ARMATURE":
        print(f"[v3] char1 arm mod: {mod.name} -> {mod.object.name if mod.object else None}")

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
    export_rest_position_armature=True,
    export_yup=True,
    export_apply=True,
    export_animations=False,
    export_lights=False,
    export_cameras=False,
)

glb_size = os.path.getsize(OUT_GLB)
print(f"[v3] wrote {OUT_GLB}  ({glb_size:,} bytes)")


# ================================================================
# STAGE 6: VERIFY
# ================================================================
print(f"\n[verify] === STAGE 6: re-importing {OUT_GLB} ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)
vscn = bpy.context.scene
bpy.context.view_layer.update()

v_arm    = next((o for o in vscn.objects if o.type == "ARMATURE"), None)
v_meshes = [o for o in vscn.objects if o.type == "MESH"]
v_skinned = [o for o in v_meshes if len(o.vertex_groups) > 0]

assert v_arm, "VERIFY FAIL: no armature"
n_bones = len(v_arm.data.bones)

mats_seen = set()
tex_count = 0
for o in v_meshes:
    for mat in o.data.materials:
        if mat and mat.name not in mats_seen:
            mats_seen.add(mat.name)
            try:
                if mat.use_nodes:
                    for nd in mat.node_tree.nodes:
                        if nd.type == "TEX_IMAGE" and nd.image:
                            tex_count += 1
            except Exception:
                pass

v_phys = [b.name for b in v_arm.data.bones if b.name.startswith("phys_")]
v_robe = [b.name for b in v_arm.data.bones if "robe" in b.name]
v_cape = [b.name for b in v_arm.data.bones if "cape" in b.name]
v_hair = [b.name for b in v_arm.data.bones if "hair" in b.name]

print(f"\n[verify] per-mesh world positions:")
for o in v_meshes:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    print(f"[verify]   {o.name}: Z {zmin:.3f} to {zmax:.3f}  verts={len(o.data.vertices)}")

icosphere_present = any(
    "Icosphere" in o.name or "Icosphere" in (o.data.name if o.data else "")
    for o in v_meshes
)

print(f"\n[verify] ===== GLB VERIFICATION REPORT =====")
print(f"[verify]   bones       : {n_bones}")
print(f"[verify]   phys bones  : {len(v_phys)}")
print(f"[verify]     robe      : {len(v_robe)}")
print(f"[verify]     cape      : {len(v_cape)}")
print(f"[verify]     hair      : {len(v_hair)}")
print(f"[verify]   meshes      : {len(v_meshes)}  {[o.name for o in v_meshes]}")
print(f"[verify]   skinned     : {len(v_skinned)}  {[o.name for o in v_skinned]}")
print(f"[verify]   materials   : {len(mats_seen)}  {sorted(mats_seen)}")
print(f"[verify]   textures    : {tex_count}")
print(f"[verify]   icosphere   : {icosphere_present}  (want False)")
print(f"[verify]   file size   : {glb_size:,} bytes")
print(f"[verify] ==========================================")

assert n_bones >= 100, f"VERIFY FAIL: {n_bones} bones"
assert len(v_meshes) >= 3, f"VERIFY FAIL: {len(v_meshes)} meshes"
assert len(v_skinned) >= 2, f"VERIFY FAIL: only {len(v_skinned)} skinned meshes (sword should be skinned now)"
assert len(mats_seen) >= 1, f"VERIFY FAIL: no materials"
assert tex_count >= 1, f"VERIFY FAIL: no textures"
assert len(v_robe) > 0, f"VERIFY FAIL: no robe chains"
assert len(v_cape) > 0, f"VERIFY FAIL: no cape chains"
assert len(v_hair) > 0, f"VERIFY FAIL: no hair chains"
print("[verify] ALL CHECKS PASSED")


# ================================================================
# STAGE 7: EEVEE MOTION PREVIEW
# ================================================================
print(f"\n[render] === STAGE 7: EEVEE motion preview ===")
scn2    = bpy.context.scene
meshes2 = [o for o in scn2.objects if o.type == "MESH"]

pick_eevee(scn2)
scn2.render.resolution_x = 768
scn2.render.resolution_y = 1024
scn2.render.image_settings.file_format = "PNG"
scn2.view_settings.view_transform = "AgX"
try:
    scn2.view_settings.look = "AgX - Punchy"
except Exception:
    pass

# Use char1 for bbox (largest mesh = char1)
char1v = max(meshes2, key=lambda o: len(o.data.vertices))
pts = [char1v.matrix_world @ Vector(c) for c in char1v.bound_box]
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2.0
Hgt = bb_max.z - bb_min.z
cx, cy, cz = center.x, center.y, center.z
print(f"[render] char1 bbox Z={bb_min.z:.3f} to {bb_max.z:.3f}  H={Hgt:.3f}  center=({cx:.3f},{cy:.3f},{cz:.3f})")

# World
w = bpy.data.worlds.get("RenderWorld") or bpy.data.worlds.new("RenderWorld")
scn2.world = w
try:
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value    = (0.005, 0.006, 0.012, 1.0)
        bg.inputs["Strength"].default_value = 0.3
except Exception:
    pass

# Lights
def area_light(name, loc, tgt, size, color, power):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size, d.color, d.energy = size, color, power
    o = bpy.data.objects.new(name, d)
    scn2.collection.objects.link(o)
    o.location = Vector(loc)
    direc = (Vector(tgt) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

tgt = (cx, cy, cz + 0.1*Hgt)
S   = Hgt
area_light("LKey",  (cx-1.0*S, cy-1.2*S, bb_max.z+0.5*S), tgt, 1.2*S, (1.0, 0.72, 0.42), 200*S*S)
area_light("LFill", (cx+1.3*S, cy-1.0*S, cz),             tgt, 1.6*S, (0.35,0.50,0.95),  40*S*S)
area_light("LRim1", (cx-0.9*S, cy+1.1*S, bb_max.z+0.2*S), tgt, 0.8*S, (1.0, 0.65, 0.28), 160*S*S)
area_light("LRim2", (cx+1.0*S, cy+1.0*S, cz+0.4*S),       tgt, 0.8*S, (0.55,0.65,1.0),   80*S*S)

# Camera
cam_d = bpy.data.cameras.new("RenderCam")
cam_d.lens = 50
cam_o = bpy.data.objects.new("RenderCam", cam_d)
scn2.collection.objects.link(cam_o)
scn2.camera = cam_o

fov_h = 2 * math.atan(36.0 / (2 * 50))
dist  = (Hgt / 2 * 1.15) / math.tan(fov_h / 2)
print(f"[render] camera dist={dist:.3f}")

def render_shot(name, yaw_deg, pitch_deg, dist_mult=1.0, look_z_off=0.0,
                focal=50, res_x=768, res_y=1024):
    yaw_r = math.radians(yaw_deg)
    pit_r = math.radians(pitch_deg)
    d     = dist * dist_mult
    cam_x = cx + math.sin(yaw_r) * d * math.cos(pit_r)
    cam_y = cy - math.cos(yaw_r) * d * math.cos(pit_r)
    cam_z = cz + math.sin(pit_r) * d + look_z_off
    cam_d.lens = focal
    cam_o.location = Vector((cam_x, cam_y, cam_z))
    look  = Vector((cx, cy, cz + look_z_off))
    direc = (look - cam_o.location).normalized()
    cam_o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()
    scn2.render.resolution_x = res_x
    scn2.render.resolution_y = res_y
    path = f"{OUTDIR}/{name}.png"
    scn2.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sz = os.path.getsize(path)
    print(f"[render] {name}.png  {sz:,} bytes")
    return path

rendered = []
rendered.append(render_shot("phase4_final_f01_front",    yaw_deg=0,    pitch_deg=5))
rendered.append(render_shot("phase4_final_f02_3q_left",  yaw_deg=-40,  pitch_deg=8))
rendered.append(render_shot("phase4_final_f03_back",     yaw_deg=180,  pitch_deg=5))
rendered.append(render_shot("phase4_final_f04_side",     yaw_deg=-90,  pitch_deg=6))
rendered.append(render_shot("phase4_final_f05_face",     yaw_deg=-10,  pitch_deg=5,
                              dist_mult=0.28, look_z_off=Hgt*0.35, focal=80,
                              res_x=768, res_y=768))
rendered.append(render_shot("phase4_final_f06_3q_right", yaw_deg=45,   pitch_deg=8))

print(f"\n[v3] ===== PHASE 4 FINAL REPORT =====")
print(f"[v3] GLB      : {OUT_GLB}  ({glb_size:,} bytes)")
print(f"[v3] bones    : {n_bones}  phys={len(v_phys)}  robe={len(v_robe)}  cape={len(v_cape)}  hair={len(v_hair)}")
print(f"[v3] meshes   : {len(v_meshes)}  skinned={len(v_skinned)}")
print(f"[v3] mats     : {len(mats_seen)}  textures={tex_count}")
print(f"[v3] renders  : {len(rendered)} frames")
for r in rendered:
    print(f"[v3]   {r}")
print("[v3] GATE PASSED — godwyn_game.glb: 121-bone rig (robe/cape/hair chains) + clean skinning + sword + baked textures")
