"""
phase4_fix_glb.py — Fix the existing godwyn_game.glb in-place.

Problems with current GLB:
  1. Stray Icosphere mesh
  2. Godwyn_Sword has wrong vertex groups (all robe/hair/cape bones)
     — should have ONLY LeftHand

Approach: import GLB, fix issues, re-export to same path.

Headless:
  blender --background --python ~/godwyn-boss-fight/scripts/phase4_fix_glb.py 2>&1
"""
import bpy, os
from mathutils import Vector

HOME    = os.path.expanduser("~")
REPO    = f"{HOME}/godwyn-boss-fight"
IN_GLB  = f"{REPO}/models/godwyn_game.glb"
OUT_GLB = f"{REPO}/models/godwyn_game.glb"  # overwrite in-place

print(f"\n[fix] === importing {IN_GLB} ({os.path.getsize(IN_GLB):,} bytes) ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=IN_GLB)
scn = bpy.context.scene
bpy.context.view_layer.update()

# ----------------------------------------------------------------
# FIX 1: Remove Icosphere
# ----------------------------------------------------------------
print("[fix] === FIX 1: removing Icospheres ===")
removed = 0
for o in list(scn.objects):
    if "Icosphere" in o.name or (o.data and "Icosphere" in o.data.name):
        print(f"[fix]   removing {o.name}")
        bpy.data.objects.remove(o, do_unlink=True)
        removed += 1
for me in list(bpy.data.meshes):
    if "Icosphere" in me.name and me.users == 0:
        bpy.data.meshes.remove(me)
print(f"[fix] removed {removed} icosphere objects")

bpy.context.view_layer.update()

# ----------------------------------------------------------------
# FIX 2: Sword vertex groups — keep ONLY LeftHand
# ----------------------------------------------------------------
print("[fix] === FIX 2: fixing sword vertex groups ===")
arm = next((o for o in scn.objects if o.type == "ARMATURE"), None)
assert arm, "FATAL: no armature found"

sword = next((o for o in scn.objects if "Sword" in o.name and o.type == "MESH"), None)
gaunt = next((o for o in scn.objects if "Gauntlet" in o.name and o.type == "MESH"), None)
char1 = next((o for o in scn.objects if o.name == "char1" and o.type == "MESH"), None)

print(f"[fix] arm: {arm.name}  sword: {sword.name if sword else None}  gaunt: {gaunt.name if gaunt else None}")
print(f"[fix] char1: {char1.name if char1 else None}  meshes: {[o.name for o in scn.objects if o.type == 'MESH']}")

if sword:
    before = [vg.name for vg in sword.vertex_groups]
    print(f"[fix] sword vgroups BEFORE ({len(before)}): {before[:6]}{'...' if len(before)>6 else ''}")
    # Clear all groups, keep only LeftHand
    sword.vertex_groups.clear()
    # Check if LeftHand bone exists
    lh_bone = arm.data.bones.get("LeftHand")
    if lh_bone:
        vg = sword.vertex_groups.new(name="LeftHand")
        vg.add(list(range(len(sword.data.vertices))), 1.0, 'REPLACE')
        print(f"[fix] sword: cleared all, added LeftHand on {len(sword.data.vertices)} verts")
    else:
        print("[fix] WARNING: LeftHand bone not found — using first available hand bone")
        hand_bones = [b.name for b in arm.data.bones if "Hand" in b.name]
        print(f"[fix]   available: {hand_bones}")
        if hand_bones:
            vg = sword.vertex_groups.new(name=hand_bones[0])
            vg.add(list(range(len(sword.data.vertices))), 1.0, 'REPLACE')

if gaunt:
    before_g = [vg.name for vg in gaunt.vertex_groups]
    print(f"[fix] gaunt vgroups BEFORE ({len(before_g)}): {before_g}")
    # Gauntlet should also be LeftHand only
    gaunt.vertex_groups.clear()
    lh_bone = arm.data.bones.get("LeftHand")
    if lh_bone:
        vg = gaunt.vertex_groups.new(name="LeftHand")
        vg.add(list(range(len(gaunt.data.vertices))), 1.0, 'REPLACE')
        print(f"[fix] gaunt: cleared all, added LeftHand on {len(gaunt.data.vertices)} verts")

# ----------------------------------------------------------------
# Verify armature modifiers
# ----------------------------------------------------------------
print("[fix] === verifying armature modifiers ===")
for o in scn.objects:
    if o.type == "MESH":
        has_arm = any(m.type == "ARMATURE" for m in o.modifiers)
        vg_count = len(o.vertex_groups)
        vg_names = [vg.name for vg in o.vertex_groups]
        print(f"[fix]   {o.name}: arm_mod={has_arm}  vgroups={vg_names[:3]}{'...' if len(vg_names)>3 else ''}")
        if not has_arm and vg_count > 0:
            # Add armature modifier
            mod = o.modifiers.new("Armature", "ARMATURE")
            mod.object = arm
            mod.use_vertex_groups = True
            print(f"[fix]   added armature modifier to {o.name}")

# ----------------------------------------------------------------
# Export fixed GLB
# ----------------------------------------------------------------
print(f"\n[fix] === exporting fixed GLB to {OUT_GLB} ===")
bpy.ops.object.select_all(action="DESELECT")
for o in scn.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm

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
print(f"[fix] wrote {OUT_GLB}  ({glb_size:,} bytes)")

# ----------------------------------------------------------------
# Verify via re-import
# ----------------------------------------------------------------
print(f"\n[fix] === verifying re-imported GLB ===")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)
vscn = bpy.context.scene
bpy.context.view_layer.update()

v_arm     = next((o for o in vscn.objects if o.type == "ARMATURE"), None)
v_meshes  = [o for o in vscn.objects if o.type == "MESH"]
v_skinned = [o for o in v_meshes if len(o.vertex_groups) > 0]
n_vbones  = len(v_arm.data.bones) if v_arm else 0

v_phys   = [b.name for b in v_arm.data.bones if b.name.startswith("phys_")] if v_arm else []
v_robe   = [b.name for b in v_arm.data.bones if "robe" in b.name] if v_arm else []
v_cape   = [b.name for b in v_arm.data.bones if "cape" in b.name] if v_arm else []
v_hair   = [b.name for b in v_arm.data.bones if "hair" in b.name] if v_arm else []
v_mixamo = [b.name for b in v_arm.data.bones if not b.name.startswith("phys_")] if v_arm else []

mats_seen, tex_count = set(), 0
for o in v_meshes:
    for mat in o.data.materials:
        if mat and mat.name not in mats_seen:
            mats_seen.add(mat.name)
            if mat.use_nodes:
                for nd in mat.node_tree.nodes:
                    if nd.type == "TEX_IMAGE" and nd.image:
                        tex_count += 1

icosphere_present = any(
    "Icosphere" in o.name or "Icosphere" in (o.data.name if o.data else "")
    for o in v_meshes
)

print(f"\n[verify] ===== GLB VERIFICATION REPORT =====")
print(f"[verify]   file size   : {glb_size:,} bytes")
print(f"[verify]   total bones : {n_vbones}  (mixamo={len(v_mixamo)}, phys={len(v_phys)})")
print(f"[verify]     robe      : {len(v_robe)}")
print(f"[verify]     cape      : {len(v_cape)}")
print(f"[verify]     hair      : {len(v_hair)}")
print(f"[verify]   meshes      : {len(v_meshes)}  {[o.name for o in v_meshes]}")
print(f"[verify]   skinned     : {len(v_skinned)}")
print(f"[verify]   materials   : {len(mats_seen)}  {sorted(mats_seen)}")
print(f"[verify]   textures    : {tex_count}")
print(f"[verify]   icosphere   : {icosphere_present}  (want False)")

for o in v_meshes:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
    vg_names = [vg.name for vg in o.vertex_groups]
    print(f"[verify]   {o.name}: Z {zmin:.3f}-{zmax:.3f}  verts={len(o.data.vertices)}  vgroups={vg_names[:4]}{'...' if len(vg_names)>4 else ''}")

# Gate
ok = True
checks = [
    (n_vbones >= 100, f"bones {n_vbones} >= 100"),
    (len(v_meshes) >= 3, f"meshes {len(v_meshes)} >= 3"),
    (len(v_robe) > 0, f"robe chain {len(v_robe)} > 0"),
    (len(v_cape) > 0, f"cape chain {len(v_cape)} > 0"),
    (len(v_hair) > 0, f"hair chain {len(v_hair)} > 0"),
    (not icosphere_present, "no icosphere"),
    (tex_count >= 1, f"textures {tex_count} >= 1"),
]
sword_v = next((o for o in v_meshes if "Sword" in o.name), None)
if sword_v:
    sword_vg = [vg.name for vg in sword_v.vertex_groups]
    checks.append((
        len(sword_vg) == 1 and sword_vg[0] == "LeftHand",
        f"Sword has only LeftHand (got {sword_vg})"
    ))

for passed, desc in checks:
    tag = "OK  " if passed else "FAIL"
    print(f"[verify]   {tag}: {desc}")
    if not passed:
        ok = False

if ok:
    print(f"\n[verify] ALL CHECKS PASSED")
else:
    print(f"\n[verify] SOME CHECKS FAILED — see above")
    raise RuntimeError("GLB gate FAILED")

print(f"\n[fix] DONE — {OUT_GLB}  ({glb_size:,} bytes)")
