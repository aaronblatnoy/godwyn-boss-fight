"""
Phase 0 Probe — Godwyn Boss Fight
Verifies: Blender 5.1.2, Cycles + OptiX GPU, imports godwyn_game.glb,
reports rig/skin/regions.
"""

import bpy
import sys
import os
import json

# ── 0. Blender version ──────────────────────────────────────────────────────
ver = bpy.app.version
ver_str = ".".join(str(v) for v in ver)
print(f"\n=== PHASE 0 PROBE ===")
print(f"Blender version: {ver_str}")
assert ver >= (5, 1, 2), f"FAIL: expected 5.1.2+, got {ver_str}"
print("  [OK] Blender 5.1.2+")

# ── 1. GPU / Cycles / OptiX ──────────────────────────────────────────────────
prefs = bpy.context.preferences
cprefs = prefs.addons["cycles"].preferences

# Force OptiX
cprefs.compute_device_type = "OPTIX"
bpy.context.preferences.addons["cycles"].preferences.get_devices()

devices = list(cprefs.devices)
print(f"\nGPU device table ({len(devices)} devices found):")
optix_enabled = []
for d in devices:
    enabled = d.use
    print(f"  [{'+' if enabled else ' '}] {d.name}  type={d.type}")
    if d.type == "OPTIX":
        d.use = True
        optix_enabled.append(d.name)

# Confirm at least one OptiX GPU
assert len(optix_enabled) > 0 or any(d.type == "OPTIX" for d in devices), \
    "FAIL: No OptiX devices found"

# Enable all OptiX devices
for d in devices:
    if d.type == "OPTIX":
        d.use = True
        if d.name not in optix_enabled:
            optix_enabled.append(d.name)

print(f"  [OK] OptiX devices enabled: {optix_enabled}")

# Quick GPU render test — needs a camera in scene
bpy.ops.scene.new(type="EMPTY")
test_scene = bpy.context.scene
test_scene.render.engine = "CYCLES"
test_scene.cycles.device = "GPU"
test_scene.render.resolution_x = 16
test_scene.render.resolution_y = 16
test_scene.render.filepath = "/tmp/phase0_gpucheck.png"
# Add a minimal camera so Cycles can render
cam_data = bpy.data.cameras.new("TestCam")
cam_obj = bpy.data.objects.new("TestCam", cam_data)
test_scene.collection.objects.link(cam_obj)
test_scene.camera = cam_obj
bpy.ops.render.render(write_still=True)
assert os.path.exists("/tmp/phase0_gpucheck.png"), "FAIL: GPU test render produced no output"
print("  [OK] GPU Cycles render test passed")

# ── 2. Import godwyn_game.glb ────────────────────────────────────────────────
GLB_PATH = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
print(f"\nImporting: {GLB_PATH}")
assert os.path.exists(GLB_PATH), f"FAIL: GLB not found at {GLB_PATH}"

# Start fresh scene
bpy.ops.scene.new(type="EMPTY")
bpy.ops.import_scene.gltf(filepath=GLB_PATH)
print("  [OK] GLB imported")

# ── 3. Inventory the scene ───────────────────────────────────────────────────
scene = bpy.context.scene
all_objects = list(bpy.data.objects)

print(f"\nTotal objects in scene: {len(all_objects)}")
for obj in all_objects:
    print(f"  {obj.type:12s}  '{obj.name}'  parent='{obj.parent.name if obj.parent else None}'")

# ── 4. Armature + bones ──────────────────────────────────────────────────────
armatures = [o for o in all_objects if o.type == "ARMATURE"]
print(f"\nArmatures found: {len(armatures)}")
assert len(armatures) >= 1, "FAIL: No armature found"

for arm_obj in armatures:
    arm = arm_obj.data
    bones = list(arm.bones)
    print(f"\n  Armature: '{arm_obj.name}'  ({len(bones)} bones)")
    for b in bones:
        print(f"    bone: '{b.name}'  parent='{b.parent.name if b.parent else None}'")

# ── 5. Skinned meshes + vertex groups ────────────────────────────────────────
meshes = [o for o in all_objects if o.type == "MESH"]
print(f"\nMesh objects: {len(meshes)}")
for m in meshes:
    vg_names = [vg.name for vg in m.vertex_groups]
    modifiers = [mod.type for mod in m.modifiers]
    print(f"\n  Mesh: '{m.name}'")
    print(f"    Vertex groups ({len(vg_names)}): {vg_names}")
    print(f"    Modifiers: {modifiers}")
    # Check armature modifier
    arm_mods = [mod for mod in m.modifiers if mod.type == "ARMATURE"]
    if arm_mods:
        print(f"    -> Skinned to armature: '{arm_mods[0].object.name if arm_mods[0].object else 'NONE'}'")

# ── 6. Godwyn_Sword: separate parented object? ───────────────────────────────
print("\n--- Sword check ---")
sword_objects = [o for o in all_objects if "sword" in o.name.lower() or "Sword" in o.name]
if sword_objects:
    for s in sword_objects:
        print(f"  Sword object: '{s.name}'  type={s.type}  parent='{s.parent.name if s.parent else None}'")
else:
    print("  No dedicated Sword object found (may be merged into body mesh)")

# ── 7. Baked textures ────────────────────────────────────────────────────────
print("\n--- Baked textures / materials ---")
for m in meshes:
    if m.data.materials:
        for mat in m.data.materials:
            if mat is None:
                continue
            print(f"  Mesh '{m.name}'  mat='{mat.name}'")
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == "TEX_IMAGE" and node.image:
                        img = node.image
                        print(f"    texture: '{img.name}'  size={img.size[0]}x{img.size[1]}  src='{img.filepath}'")

# ── 8. Robe/Cape + Hair vertex region analysis ───────────────────────────────
print("\n--- ROBE / CAPE / HAIR vertex region analysis ---")

# Keywords to identify robe/cape/hair bone influence
ROBE_BONE_KEYWORDS = ["robe", "cape", "skirt", "cloak", "cloth", "mantle", "hem", "dress", "coat", "lower"]
HAIR_BONE_KEYWORDS = ["hair", "veil", "braid", "strand"]
LEG_PELVIS_KEYWORDS = ["leg", "pelvis", "hip", "thigh", "shin", "knee", "foot", "toe", "calf"]

def bone_category(name):
    n = name.lower()
    if any(k in n for k in ROBE_BONE_KEYWORDS):
        return "ROBE/CAPE"
    if any(k in n for k in HAIR_BONE_KEYWORDS):
        return "HAIR"
    if any(k in n for k in LEG_PELVIS_KEYWORDS):
        return "LEG/PELVIS"
    return "OTHER"

for mesh_obj in meshes:
    mesh = mesh_obj.data
    vg_names = [vg.name for vg in mesh_obj.vertex_groups]
    if not vg_names:
        continue

    # Build vg index -> name map
    vg_idx_to_name = {vg.index: vg.name for vg in mesh_obj.vertex_groups}

    # Collect per-vertex dominant group
    robe_verts = []
    hair_verts = []

    for vert in mesh.vertices:
        if not vert.groups:
            continue
        # Dominant group = highest weight
        dominant = max(vert.groups, key=lambda g: g.weight)
        dom_name = vg_idx_to_name.get(dominant.group, "?")
        cat = bone_category(dom_name)
        if cat == "ROBE/CAPE":
            robe_verts.append((vert.index, dom_name, dominant.weight))
        elif cat == "HAIR":
            hair_verts.append((vert.index, dom_name, dominant.weight))

    total_verts = len(mesh.vertices)
    print(f"\n  Mesh '{mesh_obj.name}'  ({total_verts} vertices total)")
    print(f"    Robe/Cape dominant verts: {len(robe_verts)}")
    print(f"    Hair dominant verts:      {len(hair_verts)}")

    # Summarise which bones the robe/cape verts are actually weighted to
    # (ALL groups, not just dominant) — look for leg/pelvis contamination
    print(f"\n    --- Robe/Cape verts: all influencing bones ---")
    robe_bone_influence = {}  # bone_name -> total weight sum
    for vert in mesh.vertices:
        # Identify if this vertex has any robe-keyword bone OR is in bottom Z
        # Strategy: look at ALL verts, tally per-bone total weight
        for g in vert.groups:
            bname = vg_idx_to_name.get(g.group, "?")
            if bone_category(bname) in ("ROBE/CAPE", "OTHER", "LEG/PELVIS"):
                pass  # will tally below

    # Tally per-bone total weight contribution
    bone_weight_sum = {}
    bone_vert_count = {}
    for vert in mesh.vertices:
        for g in vert.groups:
            bname = vg_idx_to_name.get(g.group, "?")
            bone_weight_sum[bname] = bone_weight_sum.get(bname, 0.0) + g.weight
            bone_vert_count[bname] = bone_vert_count.get(bname, 0) + 1

    # Sort by total weight desc
    sorted_bones = sorted(bone_weight_sum.items(), key=lambda x: -x[1])
    print(f"    Top bones by total weight sum across ALL verts:")
    for bname, wsum in sorted_bones[:30]:
        cat = bone_category(bname)
        count = bone_vert_count.get(bname, 0)
        flag = " <-- LEG/PELVIS (STRETCH RISK)" if cat == "LEG/PELVIS" else \
               " <-- ROBE/CAPE" if cat == "ROBE/CAPE" else \
               " <-- HAIR" if cat == "HAIR" else ""
        print(f"      {bname:40s}  wsum={wsum:8.2f}  verts={count:5d}  [{cat}]{flag}")

    print(f"\n    --- Hair verts: influencing bones ---")
    hair_bone_weight_sum = {}
    hair_bone_vert_count = {}
    for vert in mesh.vertices:
        for g in vert.groups:
            bname = vg_idx_to_name.get(g.group, "?")
            # aggregate only if this vertex is "hair dominant"
    # Simpler: just show top bones for verts whose dominant group is HAIR
    hv_indices = {v[0] for v in hair_verts}
    h_bone_wsum = {}
    h_bone_vcnt = {}
    for vert in mesh.vertices:
        if vert.index not in hv_indices:
            continue
        for g in vert.groups:
            bname = vg_idx_to_name.get(g.group, "?")
            h_bone_wsum[bname] = h_bone_wsum.get(bname, 0.0) + g.weight
            h_bone_vcnt[bname] = h_bone_vcnt.get(bname, 0) + 1
    if h_bone_wsum:
        for bname, wsum in sorted(h_bone_wsum.items(), key=lambda x: -x[1])[:20]:
            cat = bone_category(bname)
            flag = " <-- LEG/PELVIS (STRETCH RISK)" if cat == "LEG/PELVIS" else ""
            print(f"      {bname:40s}  wsum={wsum:8.2f}  verts={h_bone_vcnt.get(bname,0):5d}  [{cat}]{flag}")
    else:
        print("      (no hair-dominant verts found by keyword matching)")

print("\n=== PHASE 0 PROBE COMPLETE ===\n")
