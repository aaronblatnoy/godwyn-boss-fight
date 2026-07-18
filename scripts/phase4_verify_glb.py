"""Verify the exported godwyn_game.glb — bone count, mesh count, textures, skinning."""
import bpy, sys

GLB = "/home/aaron/godwyn-boss-fight/models/godwyn_game.glb"

# Fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

print("=== VERIFY: godwyn_game.glb ===")

objects = list(bpy.data.objects)
armatures = [o for o in objects if o.type == 'ARMATURE']
meshes    = [o for o in objects if o.type == 'MESH']
print(f"\nObjects total: {len(objects)}")
print(f"Armatures: {len(armatures)}")
print(f"Meshes: {len(meshes)}")

for arm in armatures:
    bones = list(arm.data.bones)
    print(f"\nArmature '{arm.name}': {len(bones)} bones")
    # Print bone categories
    mixamo = [b.name for b in bones if not any(b.name.startswith(p) for p in ('robe_', 'cape_', 'hair_', 'phys_', 'cloth_', 'chain_'))]
    chains = [b.name for b in bones if any(b.name.startswith(p) for p in ('robe_', 'cape_', 'hair_', 'phys_', 'cloth_', 'chain_'))]
    print(f"  Mixamo-style bones: {len(mixamo)}")
    print(f"  Chain bones (robe/cape/hair): {len(chains)}")
    # Show chain bone names
    if chains:
        print(f"  Chain names (first 20): {chains[:20]}")
    # Show all bone names for full audit
    print(f"  All bones: {[b.name for b in bones]}")

for mesh_obj in meshes:
    vg_names = [vg.name for vg in mesh_obj.vertex_groups]
    skin_mods = [m for m in mesh_obj.modifiers if m.type == 'ARMATURE']
    print(f"\nMesh '{mesh_obj.name}':")
    print(f"  Vertices: {len(mesh_obj.data.vertices)}")
    print(f"  Faces: {len(mesh_obj.data.polygons)}")
    print(f"  Vertex groups (skinning): {len(vg_names)}")
    print(f"  Armature modifiers: {len(skin_mods)}")
    print(f"  Parent: {mesh_obj.parent.name if mesh_obj.parent else None}  parent_type={mesh_obj.parent_type}  parent_bone={mesh_obj.parent_bone}")
    if vg_names:
        print(f"  VG sample: {vg_names[:10]}")

print(f"\nMaterials: {[m.name for m in bpy.data.materials]}")
print(f"Textures/Images: {len(bpy.data.images)}")
for img in bpy.data.images:
    packed = img.packed_file is not None
    print(f"  {img.name}: {img.size[0]}x{img.size[1]} packed={packed}")

print("\n=== VERIFY COMPLETE ===")
