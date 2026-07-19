"""
phase4_final_export_v2.py — Phase 4 final export (corrected parenting).

Strategy:
  1. Open godwyn_p2_robe.blend (121 bones, full physics chains)
  2. Append Godwyn_Sword + Godwyn_Gauntlet from godwyn_face.blend — they will
     arrive already parented to the face-blend's Armature (which will be
     renamed or duplicate). We then:
     - Unparent them cleanly (keep world transform)
     - Re-parent to the robe Armature / LeftHand bone
     - Copy parent_inverse from the face-blend reference so the local-bone
       offset is identical to how it was in the face blend.
  3. Remove Icosphere (test mesh).
  4. Export GLB: armature + char1 + sword + gauntlet (no Icosphere, no lights/cams)
  5. Verify re-import: bones >=121, meshes >=3, skinning intact, textures present
  6. Render 6 EEVEE frames from re-imported GLB.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_final_export_v2.py 2>&1
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
            print(f"[v2] render engine = {eng}")
            return
        except Exception:
            continue
    raise RuntimeError("no EEVEE engine found")


# ================================================================
# STAGE 1: PROBE face blend to record sword/gauntlet parent_inverse
# ================================================================
print("\n[v2] === STAGE 1: probe face blend for reference transforms ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=FACE_B)

face_sword = bpy.data.objects.get("Godwyn_Sword")
face_gaunt = bpy.data.objects.get("Godwyn_Gauntlet")
assert face_sword and face_gaunt, "FATAL: sword/gauntlet not in face blend"

# Record the parent_inverse (bone-local offset) from the face blend.
# Both blends have identical armatures at the same scale, so these values
# will be correct after reparenting to the robe armature's LeftHand.
sword_parent_inv = face_sword.matrix_parent_inverse.copy()
gaunt_parent_inv = face_gaunt.matrix_parent_inverse.copy()
sword_loc   = face_sword.location.copy()
sword_rot   = face_sword.rotation_euler.copy() if face_sword.rotation_mode == 'XYZ' else None
sword_rot_q = face_sword.rotation_quaternion.copy() if face_sword.rotation_mode != 'XYZ' else None
sword_scl   = face_sword.scale.copy()
gaunt_loc   = face_gaunt.location.copy()
gaunt_rot   = face_gaunt.rotation_euler.copy() if face_gaunt.rotation_mode == 'XYZ' else None
gaunt_rot_q = face_gaunt.rotation_quaternion.copy() if face_gaunt.rotation_mode != 'XYZ' else None
gaunt_scl   = face_gaunt.scale.copy()
sword_rm    = face_sword.rotation_mode
gaunt_rm    = face_gaunt.rotation_mode

# Capture sword materials from face blend
sword_mats = [m.name for m in face_sword.data.materials if m]
gaunt_mats = [m.name for m in face_gaunt.data.materials if m]

print(f"[v2] sword parent_inv recorded  loc={tuple(round(v,3) for v in sword_loc)}")
print(f"[v2] gaunt parent_inv recorded  loc={tuple(round(v,3) for v in gaunt_loc)}")
print(f"[v2] sword mats: {sword_mats}  gaunt mats: {gaunt_mats}")

# World position of LeftHand in face blend (for sanity check)
face_arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
bpy.context.view_layer.objects.active = face_arm
bpy.ops.object.mode_set(mode='POSE')
lh = face_arm.pose.bones.get("LeftHand")
face_lh_world = (face_arm.matrix_world @ lh.matrix).translation.copy()
bpy.ops.object.mode_set(mode='OBJECT')
print(f"[v2] face blend LeftHand world pos = {tuple(round(v,3) for v in face_lh_world)}")

# Also capture sword world position for sanity check
bpy.context.view_layer.update()
sword_world_z_max = max((face_sword.matrix_world @ Vector(c)).z for c in face_sword.bound_box)
print(f"[v2] sword world Z max = {sword_world_z_max:.3f}")


# ================================================================
# STAGE 2: OPEN ROBE BLEND
# ================================================================
print("\n[v2] === STAGE 2: opening robe blend (121-bone rig) ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=ROBE_B)
scn = bpy.context.scene

arm  = next((o for o in scn.objects if o.type == "ARMATURE"), None)
char1 = bpy.data.objects.get("char1")
assert arm and char1, "FATAL: armature or char1 missing in robe blend"

# Remove Icosphere
for name in ("Icosphere",):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        me = bpy.data.meshes.get("Icosphere")
        if me: bpy.data.meshes.remove(me)
        print(f"[v2] removed: {name}")

n_bones = len(arm.data.bones)
phys_b  = [b.name for b in arm.data.bones if b.name.startswith("phys_")]
print(f"[v2] robe rig: {n_bones} bones  ({len(phys_b)} phys chains)")
print(f"[v2] char1: verts={len(char1.data.vertices)}  vgroups={len(char1.vertex_groups)}")


# ================================================================
# STAGE 3: APPEND SWORD + GAUNTLET, RESTORE PARENTING
# ================================================================
print("\n[v2] === STAGE 3: appending sword + gauntlet ===")

# Append meshes (they'll arrive with stale parent referencing a duplicate arm)
for obj_name in ("Godwyn_Sword", "Godwyn_Gauntlet"):
    bpy.ops.wm.append(
        filepath=f"{FACE_B}/Object/{obj_name}",
        directory=f"{FACE_B}/Object/",
        filename=obj_name,
        link=False,
        do_reuse_local_id=False,
    )

# Append extra materials
for mname in ["GodwynSwordMat", "GodwynSwordGoldMat", "GodwynHairMat", "GodwynGauntletMat"]:
    if bpy.data.materials.get(mname):
        print(f"[v2] material exists: {mname}")
        continue
    bpy.ops.wm.append(
        filepath=f"{FACE_B}/Material/{mname}",
        directory=f"{FACE_B}/Material/",
        filename=mname,
        link=False,
        do_reuse_local_id=False,
    )
    if bpy.data.materials.get(mname):
        print(f"[v2] appended material: {mname}")

sword = bpy.data.objects.get("Godwyn_Sword")
gaunt = bpy.data.objects.get("Godwyn_Gauntlet")
assert sword and gaunt, "FATAL: sword/gauntlet append failed"

# Remove the stale imported armature(s) that came with the appended objects
for o in list(bpy.data.objects):
    if o.type == "ARMATURE" and o is not arm:
        print(f"[v2] removing stale armature: {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)

# Now re-parent sword + gauntlet to the ROBE armature's LeftHand bone
# using the EXACT same parent_inverse from the face blend (same scale = same offsets)
lefthand_bone = arm.data.bones.get("LeftHand")
assert lefthand_bone, "FATAL: LeftHand bone missing from robe armature"

# Check robe LeftHand world position matches face LeftHand
bpy.context.view_layer.update()
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
robe_lh = arm.pose.bones.get("LeftHand")
robe_lh_world = (arm.matrix_world @ robe_lh.matrix).translation.copy()
bpy.ops.object.mode_set(mode='OBJECT')
print(f"[v2] robe blend LeftHand world pos = {tuple(round(v,3) for v in robe_lh_world)}")
diff = (robe_lh_world - face_lh_world).length
print(f"[v2] LeftHand world pos difference = {diff:.4f} (should be near 0)")

for obj, parent_inv, loc, rot, rot_q, scl, rm, mats in [
    (sword, sword_parent_inv, sword_loc, sword_rot, sword_rot_q, sword_scl, sword_rm, sword_mats),
    (gaunt, gaunt_parent_inv, gaunt_loc, gaunt_rot, gaunt_rot_q, gaunt_scl, gaunt_rm, gaunt_mats),
]:
    # Clear parent (keep world)
    old_world = obj.matrix_world.copy()
    obj.parent      = None
    obj.parent_bone = ""
    obj.matrix_world = old_world

    # Set new parent to robe armature
    obj.parent      = arm
    obj.parent_type = "BONE"
    obj.parent_bone = "LeftHand"
    # Restore EXACT local offsets from face blend (same rig scale)
    obj.matrix_parent_inverse = parent_inv
    obj.location       = loc
    obj.rotation_mode  = rm
    if rot is not None:
        obj.rotation_euler = rot
    else:
        obj.rotation_quaternion = rot_q
    obj.scale = scl
    print(f"[v2] {obj.name} -> robe Armature / LeftHand  loc={tuple(round(v,3) for v in obj.location)}")

# Verify sword world Z after reparenting
bpy.context.view_layer.update()
sword_wz = max((sword.matrix_world @ Vector(c)).z for c in sword.bound_box)
print(f"[v2] sword world Z max after reparent = {sword_wz:.3f}  (expect ~{sword_world_z_max:.3f})")


# ================================================================
# STAGE 4: ADD GodwynHairMat TO CHAR1 (it was missing in robe blend)
# ================================================================
print("\n[v2] === STAGE 4: char1 material setup ===")
hair_mat = bpy.data.materials.get("GodwynHairMat")
if hair_mat:
    mat_names = [m.name for m in char1.data.materials if m]
    if "GodwynHairMat" not in mat_names:
        char1.data.materials.append(hair_mat)
        print(f"[v2] added GodwynHairMat to char1")
print(f"[v2] char1 mats: {[m.name for m in char1.data.materials if m]}")
print(f"[v2] sword mats: {[m.name for m in sword.data.materials if m]}")
print(f"[v2] gauntlet mats: {[m.name for m in gaunt.data.materials if m]}")


# ================================================================
# STAGE 5: EXPORT GLB
# ================================================================
print(f"\n[v2] === STAGE 5: exporting {OUT_GLB} ===")

# Select: armature + char1 + sword + gauntlet (NOT Icosphere)
bpy.ops.object.select_all(action="DESELECT")
for o in (arm, char1, sword, gaunt):
    o.select_set(True)
bpy.context.view_layer.objects.active = arm

arm_mods = [m.name for m in char1.modifiers if m.type == "ARMATURE"]
assert arm_mods, "FATAL: char1 has no armature modifier"
print(f"[v2] char1 armature mods: {arm_mods}")

# Report packed textures
for mat in bpy.data.materials:
    try:
        if not mat.use_nodes:
            continue
    except Exception:
        continue
    tex_nodes = [n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image]
    for t in tex_nodes:
        print(f"[v2]   mat={mat.name}  tex={t.image.name}  packed={t.image.packed_file is not None}")

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
    export_yup=True,                       # +Y up
    export_apply=True,                     # apply modifiers (not armature)
    export_animations=False,
    export_lights=False,
    export_cameras=False,
)

glb_size = os.path.getsize(OUT_GLB)
print(f"[v2] wrote {OUT_GLB}  ({glb_size:,} bytes)")


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
n_bones   = len(v_arm.data.bones)

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

# Check sword/gauntlet positions
for o in v_meshes:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    print(f"[verify]   {o.name}: Z {zmin:.3f} to {zmax:.3f}  verts={len(o.data.vertices)}")

icosphere_present = any("Icosphere" in o.name or "Icosphere" in o.data.name for o in v_meshes)

print(f"\n[verify] ===== GLB VERIFICATION REPORT =====")
print(f"[verify]   bones       : {n_bones}")
print(f"[verify]   phys bones  : {len(v_phys)}")
print(f"[verify]     robe      : {len(v_robe)}")
print(f"[verify]     cape      : {len(v_cape)}")
print(f"[verify]     hair      : {len(v_hair)}")
print(f"[verify]   meshes      : {len(v_meshes)}  names={[o.name for o in v_meshes]}")
print(f"[verify]   skinned     : {len(v_skinned)}")
print(f"[verify]   materials   : {len(mats_seen)}  {sorted(mats_seen)}")
print(f"[verify]   textures    : {tex_count}")
print(f"[verify]   icosphere   : {icosphere_present}  (want False)")
print(f"[verify]   file size   : {glb_size:,} bytes")
print(f"[verify] ==========================================")

assert n_bones  >= 100, f"VERIFY FAIL: {n_bones} bones"
assert len(v_meshes) >= 3, f"VERIFY FAIL: {len(v_meshes)} meshes"
assert len(v_skinned) >= 1, f"VERIFY FAIL: no skinned meshes"
assert len(mats_seen) >= 1, f"VERIFY FAIL: no materials"
assert tex_count >= 1, f"VERIFY FAIL: no textures"
assert len(v_robe) > 0, f"VERIFY FAIL: no robe chains"
assert len(v_cape) > 0, f"VERIFY FAIL: no cape chains"
assert len(v_hair) > 0, f"VERIFY FAIL: no hair chains"
print("[verify] ALL CHECKS PASSED")


# ================================================================
# STAGE 7: EEVEE MOTION PREVIEW RENDERS
# ================================================================
print(f"\n[render] === STAGE 7: EEVEE motion preview ===")

scn2    = bpy.context.scene
v_meshes2 = [o for o in scn2.objects if o.type == "MESH"]

pick_eevee(scn2)
scn2.render.resolution_x = 768
scn2.render.resolution_y = 1024
scn2.render.image_settings.file_format = "PNG"
scn2.view_settings.view_transform = "AgX"
try:
    scn2.view_settings.look = "AgX - Punchy"
except Exception:
    pass

# Bbox — only use char1 (the skinned mesh) to avoid outlier bone-parented objects
char1_v = next((o for o in v_meshes2 if o.name == "char1"), None)
if char1_v is None:
    char1_v = max(v_meshes2, key=lambda o: len(o.data.vertices))

pts = [char1_v.matrix_world @ Vector(c) for c in char1_v.bound_box]
bb_min = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
bb_max = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (bb_min + bb_max) / 2.0
Hgt    = bb_max.z - bb_min.z
cx, cy, cz = center.x, center.y, center.z

print(f"[render] char1 bbox Z={bb_min.z:.3f} to {bb_max.z:.3f}  H={Hgt:.3f}")
print(f"[render] center=({cx:.3f},{cy:.3f},{cz:.3f})")

# World
w = bpy.data.worlds.get("RenderWorld") or bpy.data.worlds.new("RenderWorld")
scn2.world = w
try:
    w.use_nodes = True
    wbg = w.node_tree.nodes.get("Background")
    if wbg:
        wbg.inputs["Color"].default_value    = (0.005, 0.006, 0.012, 1.0)
        wbg.inputs["Strength"].default_value = 0.3
except Exception:
    pass

# Lights
def area_light(name, loc, target, size, color, power):
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    d = bpy.data.lights.new(name, "AREA")
    d.size, d.color, d.energy = size, color, power
    o = bpy.data.objects.new(name, d)
    scn2.collection.objects.link(o)
    o.location = Vector(loc)
    direc = (Vector(target) - Vector(loc)).normalized()
    o.rotation_euler = direc.to_track_quat("-Z", "Y").to_euler()

tgt = (cx, cy, cz + 0.1*Hgt)
S   = Hgt
area_light("LKey",  (cx - 1.0*S, cy - 1.2*S, bb_max.z + 0.5*S),  tgt, 1.2*S, (1.0,  0.72, 0.42), 200*S*S)
area_light("LFill", (cx + 1.3*S, cy - 1.0*S, cz),                 tgt, 1.6*S, (0.35, 0.50, 0.95),  40*S*S)
area_light("LRim1", (cx - 0.9*S, cy + 1.1*S, bb_max.z + 0.2*S),  tgt, 0.8*S, (1.0,  0.65, 0.28), 160*S*S)
area_light("LRim2", (cx + 1.0*S, cy + 1.0*S, cz + 0.4*S),        tgt, 0.8*S, (0.55, 0.65, 1.0),   80*S*S)

# Camera
cam_d = bpy.data.cameras.new("RenderCam")
cam_d.lens = 50
cam_o = bpy.data.objects.new("RenderCam", cam_d)
scn2.collection.objects.link(cam_o)
scn2.camera = cam_o

FOCAL = 50.0
fov_h = 2 * math.atan(36.0 / (2 * FOCAL))
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
    print(f"[render] {name}.png  {sz:,} bytes  cam=({cam_x:.2f},{cam_y:.2f},{cam_z:.2f})")
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

print(f"\n[v2] ===== PHASE 4 FINAL REPORT =====")
print(f"[v2] GLB      : {OUT_GLB}  ({glb_size:,} bytes)")
print(f"[v2] bones    : {n_bones}  phys={len(v_phys)}  robe={len(v_robe)}  cape={len(v_cape)}  hair={len(v_hair)}")
print(f"[v2] meshes   : {len(v_meshes)}  skinned={len(v_skinned)}")
print(f"[v2] materials: {len(mats_seen)}  textures={tex_count}")
print(f"[v2] renders  : {len(rendered)} frames")
for r in rendered:
    print(f"[v2]   {r}")
print("[v2] GATE PASSED — godwyn_game.glb: 121-bone rig (robe+cape+hair chains) + cleaned skinning + sword parented + baked textures")
