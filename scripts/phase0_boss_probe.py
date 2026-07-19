"""
Phase 0 Boss Fight Probe
- Verify GPU (Cycles + OptiX)
- Import godwyn_game.glb
- Report: armature, bones, meshes, vertex groups, textures
- Locate SWORD vertices (bounding box)
- Locate FOOT/TOE regions and their driving bones + orientation
"""

import bpy
import sys
import os
import json
import math

print("=" * 70)
print("PHASE 0 BOSS FIGHT PROBE")
print("=" * 70)

# ── GPU CHECK ──────────────────────────────────────────────────────────────
print("\n[GPU CHECK]")
prefs = bpy.context.preferences
cprefs = prefs.addons['cycles'].preferences
cprefs.refresh_devices()

print(f"  Compute device type: {cprefs.compute_device_type}")
devices = list(cprefs.devices)
print(f"  Total devices found: {len(devices)}")
gpu_found = False
for d in devices:
    status = "ENABLED" if d.use else "disabled"
    print(f"    [{status}] {d.name}  type={d.type}")
    if d.type in ('CUDA', 'OPTIX', 'HIP'):
        d.use = True
        gpu_found = True

if not gpu_found:
    print("  WARNING: No GPU devices found!")
else:
    print("  GPU devices activated.")

# Set scene to use GPU
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
cprefs.compute_device_type = 'OPTIX'
print(f"  Render engine: CYCLES, device: GPU, OptiX activated")

# ── IMPORT GLB ─────────────────────────────────────────────────────────────
print("\n[IMPORT GLB]")
glb_path = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
print(f"  Importing: {glb_path}")

# Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.ops.import_scene.gltf(filepath=glb_path)
print("  Import complete.")

# ── SCENE INVENTORY ────────────────────────────────────────────────────────
print("\n[SCENE OBJECTS]")
all_objects = list(bpy.data.objects)
for obj in all_objects:
    print(f"  {obj.name}  type={obj.type}  parent={obj.parent.name if obj.parent else None}")

# ── ARMATURE & BONES ───────────────────────────────────────────────────────
print("\n[ARMATURE & BONES]")
armatures = [o for o in all_objects if o.type == 'ARMATURE']
if not armatures:
    print("  ERROR: No armature found!")
else:
    for arm_obj in armatures:
        arm = arm_obj.data
        bones = list(arm.bones)
        print(f"\n  Armature: '{arm_obj.name}'  ({len(bones)} bones)")

        # Print all bones with parent
        for b in bones:
            parent_name = b.parent.name if b.parent else "ROOT"
            print(f"    {b.name}  parent={parent_name}")

        # Specifically look for foot/toe bones
        print("\n  [FOOT/TOE BONES]")
        foot_keywords = ['foot', 'toe', 'ankle', 'heel']
        foot_bones = [b for b in bones if any(kw in b.name.lower() for kw in foot_keywords)]
        for b in foot_bones:
            # Head and tail in armature local space
            head = b.head_local
            tail = b.tail_local
            # Compute direction vector
            dir_vec = (tail[0]-head[0], tail[1]-head[1], tail[2]-head[2])
            length = math.sqrt(sum(x*x for x in dir_vec))
            if length > 0:
                dir_norm = tuple(x/length for x in dir_vec)
            else:
                dir_norm = (0,0,0)
            print(f"    {b.name}")
            print(f"      head={tuple(round(x,4) for x in head)}")
            print(f"      tail={tuple(round(x,4) for x in tail)}")
            print(f"      dir={tuple(round(x,3) for x in dir_norm)}")

        if not foot_bones:
            print("    (no foot/toe bones found by keyword)")

# ── SKINNED MESHES & VERTEX GROUPS ─────────────────────────────────────────
print("\n[SKINNED MESHES & VERTEX GROUPS]")
mesh_objects = [o for o in all_objects if o.type == 'MESH']
for obj in mesh_objects:
    vg_names = [vg.name for vg in obj.vertex_groups]
    print(f"\n  Mesh: '{obj.name}'  vertices={len(obj.data.vertices)}  faces={len(obj.data.polygons)}")
    print(f"    Vertex groups ({len(vg_names)}): {vg_names[:20]}{'...' if len(vg_names)>20 else ''}")
    mods = [m.type for m in obj.modifiers]
    print(f"    Modifiers: {mods}")

# ── TEXTURES / MATERIALS ───────────────────────────────────────────────────
print("\n[MATERIALS & TEXTURES]")
for mat in bpy.data.materials:
    print(f"  Material: '{mat.name}'")
    if mat.node_tree:
        img_nodes = [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']
        for n in img_nodes:
            if n.image:
                print(f"    Image: {n.image.name}  size={n.image.size[:]}")

# ── SWORD LOCATION ─────────────────────────────────────────────────────────
print("\n[SWORD SEARCH]")
sword_keywords = ['sword', 'blade', 'hilt', 'weapon', 'weap', 'judg']
sword_objects = [o for o in all_objects if any(kw in o.name.lower() for kw in sword_keywords)]
print(f"  Objects matching sword keywords: {[o.name for o in sword_objects]}")

# Also try to find sword via bounding box — it should be a long thin element near a hand bone
# Check all meshes for long thin objects
print("\n  Checking all mesh bounding boxes for sword-like geometry:")
for obj in mesh_objects:
    # Get world-space bounding box
    bbox_corners = [obj.matrix_world @ bpy.context.scene.cursor.location.__class__(v) for v in obj.bound_box]
    # Actually compute from vertices for accuracy
    verts_world = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not verts_world:
        continue
    xs = [v.x for v in verts_world]
    ys = [v.y for v in verts_world]
    zs = [v.z for v in verts_world]
    x_range = max(xs) - min(xs)
    y_range = max(ys) - min(ys)
    z_range = max(zs) - min(zs)
    dims = sorted([x_range, y_range, z_range])
    ratio = dims[2] / max(dims[0], 0.001)  # long axis to short axis ratio
    print(f"    '{obj.name}': X={x_range:.3f} Y={y_range:.3f} Z={z_range:.3f}  ratio(long/short)={ratio:.1f}")
    if ratio > 5:
        print(f"      ^^^ SWORD CANDIDATE (ratio {ratio:.1f})")
        print(f"      bbox: X[{min(xs):.3f}, {max(xs):.3f}] Y[{min(ys):.3f}, {max(ys):.3f}] Z[{min(zs):.3f}, {max(zs):.3f}]")

# ── FOOT VERTEX REGIONS ────────────────────────────────────────────────────
print("\n[FOOT VERTEX REGIONS]")
# For each mesh, find vertices weighted to foot/toe bones
for obj in mesh_objects:
    foot_vg_names = [vg.name for vg in obj.vertex_groups
                     if any(kw in vg.name.lower() for kw in ['foot', 'toe', 'ankle', 'heel'])]
    if not foot_vg_names:
        continue
    print(f"\n  Mesh '{obj.name}' has foot vertex groups: {foot_vg_names}")
    for vg_name in foot_vg_names:
        vg_idx = obj.vertex_groups[vg_name].index
        # Gather vertices with weight > 0.1
        foot_verts = []
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group == vg_idx and g.weight > 0.1:
                    co_world = obj.matrix_world @ v.co
                    foot_verts.append(co_world)
        if foot_verts:
            xs = [v.x for v in foot_verts]
            ys = [v.y for v in foot_verts]
            zs = [v.z for v in foot_verts]
            print(f"    '{vg_name}': {len(foot_verts)} verts")
            print(f"      bbox: X[{min(xs):.3f}, {max(xs):.3f}] Y[{min(ys):.3f}, {max(ys):.3f}] Z[{min(zs):.3f}, {max(zs):.3f}]")
            # Check toe splay - if toe X range >> Z range (height), toes are splayed
            x_span = max(xs) - min(xs)
            z_span = max(zs) - min(zs)
            print(f"      X-span={x_span:.3f} Z-span={z_span:.3f}  (wide X vs short Z may indicate splay)")

# ── PHYSICS CHAIN BONES ────────────────────────────────────────────────────
print("\n[PHYSICS/CHAIN BONES (robe, cape, hair)]")
if armatures:
    for arm_obj in armatures:
        arm = arm_obj.data
        chain_keywords = ['robe', 'cape', 'cloak', 'hair', 'tail', 'tendril', 'cloth', 'skirt', 'mantle', 'veil', 'dread', 'braid']
        chain_bones = [b for b in arm.bones if any(kw in b.name.lower() for kw in chain_keywords)]
        if chain_bones:
            print(f"  Found {len(chain_bones)} chain/physics bones:")
            for b in chain_bones:
                print(f"    {b.name}")
        else:
            print("  No explicit robe/cape/hair chain bones found by keyword")
            # Show any bones that aren't standard Mixamo
            mixamo_prefixes = ['mixamorig', 'Hips', 'Spine', 'Chest', 'Neck', 'Head', 'Shoulder',
                               'Arm', 'ForeArm', 'Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Pinky',
                               'UpLeg', 'Leg', 'Foot', 'ToeBase']
            non_mixamo = [b for b in arm.bones if not any(b.name.startswith(p) or p.lower() in b.name.lower() for p in mixamo_prefixes)]
            if non_mixamo:
                print(f"  Non-standard bones ({len(non_mixamo)}): {[b.name for b in non_mixamo[:30]]}")

print("\n" + "=" * 70)
print("PROBE COMPLETE")
print("=" * 70)
