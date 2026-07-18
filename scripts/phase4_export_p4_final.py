"""
Phase 4 Final Export: godwyn_game.glb
- Source: godwyn_p2_robe.blend (121 bones: Mixamo + robe/cape/hair chains)
- Appends Godwyn_Sword + Godwyn_Gauntlet from godwyn_sword.blend
- Parents sword to RightHand bone
- Exports with baked textures, +Y up, rest pose (armature NOT applied)
"""
import bpy
import os
import sys
import math

BLEND_MAIN   = "/home/aaron/godwyn-boss-fight/models/godwyn_p2_robe.blend"
BLEND_SWORD  = "/home/aaron/godwyn-boss-fight/models/godwyn_sword.blend"
OUT_GLB      = "/home/aaron/godwyn-boss-fight/models/godwyn_game.glb"

# ── 1. Open the main rig blend ──────────────────────────────────────────────
bpy.ops.wm.open_mainfile(filepath=BLEND_MAIN)

# ── 2. Remove stray helper objects ──────────────────────────────────────────
to_remove = [o for o in bpy.data.objects if o.type not in ('MESH', 'ARMATURE')]
for obj in to_remove:
    bpy.data.objects.remove(obj, do_unlink=True)

# ── 3. Find the armature and the right-hand bone ────────────────────────────
arm_obj = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm_obj is None:
    print("ERROR: no armature found"); sys.exit(1)

print(f"Armature: {arm_obj.name}  bones={len(arm_obj.data.bones)}")

# Identify right-hand bone (Mixamo naming)
RHAND_CANDIDATES = ['RightHand', 'mixamorig:RightHand', 'Hand_R', 'hand.R']
rhand_bone = None
for name in RHAND_CANDIDATES:
    if name in arm_obj.data.bones:
        rhand_bone = name
        break
print(f"Right-hand bone: {rhand_bone}")

# ── 4. Append Godwyn_Sword from sword blend ─────────────────────────────────
pre_objects = set(bpy.data.objects.keys())
bpy.ops.wm.append(
    filepath=BLEND_SWORD + "/Object/Godwyn_Sword",
    directory=BLEND_SWORD + "/Object/",
    filename="Godwyn_Sword",
    link=False,
    do_reuse_local_id=False,
)
sword_objs_after = set(bpy.data.objects.keys()) - pre_objects
print(f"Appended objects: {sword_objs_after}")

# Also append gauntlet
pre2 = set(bpy.data.objects.keys())
try:
    bpy.ops.wm.append(
        filepath=BLEND_SWORD + "/Object/Godwyn_Gauntlet",
        directory=BLEND_SWORD + "/Object/",
        filename="Godwyn_Gauntlet",
        link=False,
        do_reuse_local_id=False,
    )
except Exception as e:
    print(f"Gauntlet append warning: {e}")
gauntlet_objs_after = set(bpy.data.objects.keys()) - pre2 - sword_objs_after
print(f"Gauntlet objects: {gauntlet_objs_after}")

# Grab the sword object
sword_obj = None
for name in list(sword_objs_after):
    obj = bpy.data.objects.get(name)
    if obj and obj.type == 'MESH':
        sword_obj = obj
        break
if sword_obj is None:
    sword_obj = bpy.data.objects.get("Godwyn_Sword")
print(f"Sword object: {sword_obj.name if sword_obj else 'NOT FOUND'}")

# ── 5. Clean up sword's old armature constraint/parent (from sword.blend) ───
if sword_obj:
    # Remove any existing armature modifiers (from the sword blend's armature)
    for mod in list(sword_obj.modifiers):
        if mod.type == 'ARMATURE':
            sword_obj.modifiers.remove(mod)
    # Clear parent but keep world transform
    if sword_obj.parent:
        bpy.ops.object.select_all(action='DESELECT')
        sword_obj.select_set(True)
        bpy.context.view_layer.objects.active = sword_obj
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

# ── 6. Parent sword to armature via bone ────────────────────────────────────
# Use Python direct assignment (no ops needed, avoids active-bone requirement)
def parent_to_bone(obj, arm, bone_name):
    """Parent obj to arm's bone_name, preserving no existing transform."""
    # Clear existing parent
    obj.parent = None
    obj.parent_type = 'OBJECT'
    # Remove any stray armature mods
    for mod in list(obj.modifiers):
        if mod.type == 'ARMATURE':
            obj.modifiers.remove(mod)
    # Reset matrix so it sits at the bone
    import mathutils
    obj.matrix_world = mathutils.Matrix.Identity(4)
    # Assign bone parent
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = bone_name
    # Zero out local transform so it follows the bone cleanly
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)

if sword_obj and rhand_bone:
    parent_to_bone(sword_obj, arm_obj, rhand_bone)
    print(f"Sword parented to bone: {rhand_bone}")
else:
    print(f"WARNING: sword={sword_obj} rhand_bone={rhand_bone} — skipping parent")

# Do same for gauntlet if it exists
for gname in list(gauntlet_objs_after):
    gobj = bpy.data.objects.get(gname)
    if gobj and gobj.type == 'MESH' and rhand_bone:
        parent_to_bone(gobj, arm_obj, rhand_bone)
        print(f"Gauntlet {gname} parented to bone: {rhand_bone}")

# ── 7. Remove extra/stray objects ─────────────────────────────────────────────
KEEP = {arm_obj.name, 'char1', 'Godwyn_Sword', 'Godwyn_Gauntlet'}
for obj in list(bpy.data.objects):
    if obj.name not in KEEP:
        extra_name = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)
        print(f"Removed stray object: {extra_name}")

# ── 7b. Ensure scene contains all objects ────────────────────────────────────
scene = bpy.context.scene
for obj in bpy.data.objects:
    if obj.name not in [o.name for o in scene.collection.all_objects]:
        scene.collection.objects.link(obj)

# ── 8. Report scene state before export ─────────────────────────────────────
print("\n=== PRE-EXPORT SUMMARY ===")
for obj in bpy.data.objects:
    print(f"  {obj.name}: {obj.type}  parent={obj.parent.name if obj.parent else None}  parent_bone={getattr(obj,'parent_bone','')}")

arm_data = arm_obj.data
total_bones  = len(arm_data.bones)
deform_bones = sum(1 for b in arm_data.bones if b.use_deform)
print(f"\nArmature: {total_bones} total bones, {deform_bones} deform bones")
print(f"Materials: {[m.name for m in bpy.data.materials]}")
print(f"Images (packed): {[(i.name, i.packed_file is not None) for i in bpy.data.images]}")

# ── 9. Export glTF ──────────────────────────────────────────────────────────
print(f"\nExporting to: {OUT_GLB}")
export_kwargs = dict(
    filepath=OUT_GLB,
    export_format='GLB',
    # Include
    use_selection=False,
    use_visible=True,
    use_renderable=False,
    use_active_collection=False,
    # Mesh
    export_apply=False,             # Do NOT apply modifiers (preserves armature)
    export_texcoords=True,
    export_normals=True,
    # Armature
    export_skins=True,
    export_all_influences=False,
    export_def_bones=True,          # Export only deform bones
    export_armature_object_remove=False,
    export_rest_position_armature=True,   # Rest pose
    # Materials / textures
    export_materials='EXPORT',
    export_image_format='AUTO',
    # Axes
    export_yup=True,
    # Animations — none; retargeted Mixamo mocap applied later
    export_animations=False,
    # Extras
    export_cameras=False,
    export_lights=False,
)
# Remove any kwargs the operator doesn't accept (version compat)
import bpy.ops as _ops
valid_props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
export_kwargs = {k: v for k, v in export_kwargs.items() if k in valid_props}
print(f"Export kwargs used: {list(export_kwargs.keys())}")
bpy.ops.export_scene.gltf(**export_kwargs)

size = os.path.getsize(OUT_GLB)
print(f"\nEXPORT COMPLETE: {OUT_GLB}  ({size:,} bytes)")
print("Phase 4 export done.")
