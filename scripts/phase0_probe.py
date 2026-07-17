"""
Phase 0 Probe Script — godwyn-boss-fight
- Verify Blender version + Cycles/OptiX GPU availability
- Import godwyn_game.glb
- Report armature: name, bone count, key bone names
- Report skinned mesh + vertex groups
- Report baked image textures present
- Locate sword region (vertices far from body center)
- Locate face/head region (vertices above neck bone)
- Commit report to stdout (no render)
"""

import bpy
import sys
import os
import math

print("=" * 60)
print("PHASE 0 PROBE — godwyn-boss-fight")
print("=" * 60)

# ── 1. Blender + GPU info ──────────────────────────────────────
import bpy
print(f"\n[BLENDER VERSION] {bpy.app.version_string}")

bpy.context.preferences.addons['cycles'].preferences.refresh_devices()
prefs = bpy.context.preferences.addons['cycles'].preferences

print(f"[CYCLES] Compute device types available:")
all_devices = []
for device_type in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI', 'NONE'):
    try:
        prefs.compute_device_type = device_type
        prefs.refresh_devices()
        devs = [d for d in prefs.devices]
        if devs:
            for d in devs:
                print(f"  [{device_type}] {d.name}  use={d.use}  type={d.type}")
                all_devices.append((device_type, d.name, d.use))
    except Exception as e:
        pass

# Force OptiX
try:
    prefs.compute_device_type = 'OPTIX'
    prefs.refresh_devices()
    gpu_devs = [d for d in prefs.devices if d.type != 'CPU']
    for d in gpu_devs:
        d.use = True
    print(f"[GPU] OptiX devices enabled: {[d.name for d in gpu_devs]}")
    if gpu_devs:
        print("[GPU] ASSERT PASS — GPU available via OptiX")
    else:
        print("[GPU] WARNING — no OptiX GPU devices found, falling back to CPU")
except Exception as e:
    print(f"[GPU] ERROR setting OptiX: {e}")

# ── 2. Clear default scene + import GLB ──────────────────────────
print("\n[IMPORT] Clearing scene...")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

glb_path = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
print(f"[IMPORT] Loading {glb_path}")
bpy.ops.import_scene.gltf(filepath=glb_path)
print(f"[IMPORT] Done. Objects in scene: {[o.name for o in bpy.data.objects]}")

# ── 3. Armature info ─────────────────────────────────────────────
print("\n[ARMATURE]")
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if not armatures:
    print("  ERROR: No armature found!")
else:
    for arm_obj in armatures:
        arm = arm_obj.data
        bones = arm.bones
        print(f"  Name: {arm_obj.name}")
        print(f"  Bone count: {len(bones)}")
        bone_names = [b.name for b in bones]
        print(f"  All bones: {bone_names}")
        # Key bones
        key_patterns = ['hand', 'forearm', 'arm', 'head', 'neck', 'spine', 'hip',
                        'shoulder', 'foot', 'leg', 'finger', 'thumb', 'wrist',
                        'sword', 'weapon', 'root', 'pelvis']
        print("  Key bone matches:")
        for name in bone_names:
            nl = name.lower()
            for pat in key_patterns:
                if pat in nl:
                    b = bones[name]
                    print(f"    {name}  head={tuple(round(x,4) for x in b.head_local)}  tail={tuple(round(x,4) for x in b.tail_local)}")
                    break

# ── 4. Skinned mesh + vertex groups ─────────────────────────────
print("\n[MESH]")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if not meshes:
    print("  ERROR: No mesh found!")
else:
    for mesh_obj in meshes:
        me = mesh_obj.data
        vg_names = [vg.name for vg in mesh_obj.vertex_groups]
        print(f"  Mesh: {mesh_obj.name}  verts={len(me.vertices)}  faces={len(me.polygons)}")
        print(f"  Vertex groups ({len(vg_names)}): {vg_names[:40]}{'...' if len(vg_names)>40 else ''}")

# ── 5. Baked image textures ─────────────────────────────────────
print("\n[TEXTURES]")
images = bpy.data.images
if not images:
    print("  No images/textures found!")
else:
    for img in images:
        print(f"  Image: {img.name}  size={img.size[0]}x{img.size[1]}  source={img.source}  packed={img.packed_file is not None}")

# Also check materials
print("\n[MATERIALS]")
for mat in bpy.data.materials:
    print(f"  Material: {mat.name}")
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                img = node.image
                print(f"    -> TexImage node: {img.name}  {img.size[0]}x{img.size[1]}")

# ── 6. Sword region — find vertices far from body center ─────────
print("\n[SWORD REGION]")
# Strategy: for each mesh, find vertices with X or Z extremes, or far from centroid
for mesh_obj in meshes:
    me = mesh_obj.data
    world_matrix = mesh_obj.matrix_world
    all_coords = [world_matrix @ v.co for v in me.vertices]
    if not all_coords:
        continue

    # Compute centroid
    cx = sum(v.x for v in all_coords) / len(all_coords)
    cy = sum(v.y for v in all_coords) / len(all_coords)
    cz = sum(v.z for v in all_coords) / len(all_coords)

    # Find vertices more than 1.5 std devs away from centroid in any axis
    import statistics
    xs = [v.x for v in all_coords]
    ys = [v.y for v in all_coords]
    zs = [v.z for v in all_coords]

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    print(f"  Mesh '{mesh_obj.name}' bounding box:")
    print(f"    X: {xmin:.4f} to {xmax:.4f}")
    print(f"    Y: {ymin:.4f} to {ymax:.4f}")
    print(f"    Z: {zmin:.4f} to {zmax:.4f}")
    print(f"    Centroid: ({cx:.4f}, {cy:.4f}, {cz:.4f})")

    # Find outlier clusters — vertices far from body in XZ plane
    # Body is roughly centered; sword extends in one direction
    # Compute distance from centroid in XZ
    dists_xz = [math.sqrt((v.x - cx)**2 + (v.z - cz)**2) for v in all_coords]
    max_dist = max(dists_xz)
    threshold = max_dist * 0.7  # top 30% of extreme vertices

    outlier_verts = [all_coords[i] for i, d in enumerate(dists_xz) if d >= threshold]
    if outlier_verts:
        ox = [v.x for v in outlier_verts]
        oy = [v.y for v in outlier_verts]
        oz = [v.z for v in outlier_verts]
        print(f"\n  SWORD CANDIDATE REGION ({len(outlier_verts)} verts, XZ dist >= {threshold:.4f}):")
        print(f"    X: {min(ox):.4f} to {max(ox):.4f}")
        print(f"    Y: {min(oy):.4f} to {max(oy):.4f}")
        print(f"    Z: {min(oz):.4f} to {max(oz):.4f}")

    # Also check vertex groups — any group with 'sword','weapon','blade','hilt'
    vg_lower = {vg.name.lower(): vg.index for vg in mesh_obj.vertex_groups}
    sword_vg_indices = [idx for name, idx in vg_lower.items()
                        if any(kw in name for kw in ['sword','weapon','blade','hilt','right_hand','righthand'])]
    if sword_vg_indices:
        print(f"  Sword-related vertex groups: {[mesh_obj.vertex_groups[i].name for i in sword_vg_indices]}")
        for vg_idx in sword_vg_indices[:2]:
            # Get verts with weight > 0 in this group
            vg_verts = []
            for v in me.vertices:
                for g in v.groups:
                    if g.group == vg_idx and g.weight > 0.1:
                        vg_verts.append(world_matrix @ v.co)
                        break
            if vg_verts:
                vx = [v.x for v in vg_verts]
                vy = [v.y for v in vg_verts]
                vz = [v.z for v in vg_verts]
                print(f"    VG '{mesh_obj.vertex_groups[vg_idx].name}' weighted verts ({len(vg_verts)}):")
                print(f"      X: {min(vx):.4f} to {max(vx):.4f}")
                print(f"      Y: {min(vy):.4f} to {max(vy):.4f}")
                print(f"      Z: {min(vz):.4f} to {max(vz):.4f}")

# ── 7. Head/face region — above neck bone ───────────────────────
print("\n[HEAD/FACE REGION]")
if armatures:
    arm_obj = armatures[0]
    arm = arm_obj.data
    # Find head/neck bone position
    head_bone = None
    neck_bone = None
    for bone in arm.bones:
        bl = bone.name.lower()
        if 'head' in bl and head_bone is None:
            head_bone = bone
        if 'neck' in bl and neck_bone is None:
            neck_bone = bone

    neck_z = None
    if neck_bone:
        neck_world = arm_obj.matrix_world @ neck_bone.head_local
        neck_z = neck_world.z
        print(f"  Neck bone '{neck_bone.name}' world Z = {neck_z:.4f}")
    if head_bone:
        head_world = arm_obj.matrix_world @ head_bone.head_local
        print(f"  Head bone '{head_bone.name}' world pos = ({head_world.x:.4f}, {head_world.y:.4f}, {head_world.z:.4f})")
        if neck_z is None:
            neck_z = head_world.z - 0.1  # fallback

    # Find mesh vertices above neck_z
    if neck_z is not None:
        for mesh_obj in meshes:
            me = mesh_obj.data
            world_matrix = mesh_obj.matrix_world
            head_verts = [world_matrix @ v.co for v in me.vertices
                          if (world_matrix @ v.co).z >= neck_z]
            if head_verts:
                hx = [v.x for v in head_verts]
                hy = [v.y for v in head_verts]
                hz = [v.z for v in head_verts]
                print(f"\n  HEAD REGION in '{mesh_obj.name}' ({len(head_verts)} verts above Z={neck_z:.4f}):")
                print(f"    X: {min(hx):.4f} to {max(hx):.4f}")
                print(f"    Y: {min(hy):.4f} to {max(hy):.4f}")
                print(f"    Z: {min(hz):.4f} to {max(hz):.4f}")
    else:
        print("  Could not determine neck/head Z threshold; checking vertex groups...")
        for mesh_obj in meshes:
            vg_lower = {vg.name.lower(): vg.index for vg in mesh_obj.vertex_groups}
            head_vg_indices = [idx for name, idx in vg_lower.items()
                               if any(kw in name for kw in ['head','face','skull','jaw'])]
            if head_vg_indices:
                print(f"  Head-related vertex groups: {[mesh_obj.vertex_groups[i].name for i in head_vg_indices]}")

# Also check if there's a separate sword/head mesh object
print("\n[OBJECT SUMMARY]")
for obj in bpy.data.objects:
    print(f"  {obj.type:10s}  {obj.name}")

print("\n" + "=" * 60)
print("PHASE 0 PROBE COMPLETE")
print("=" * 60)
