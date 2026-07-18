"""
Phase 0 Probe Script: GPU check + GLB rig/mesh/UV/texture report
Blender 5.1.2 headless, Cycles + OptiX
"""
import bpy
import sys
import os

print("=" * 60)
print("PHASE 0: GPU + RIG PROBE")
print("=" * 60)

# ── 1. GPU / Cycles / OptiX check ──────────────────────────────
prefs = bpy.context.preferences
cycles_prefs = prefs.addons.get("cycles")
if cycles_prefs is None:
    print("ERROR: Cycles addon not found")
    sys.exit(1)

cp = prefs.addons["cycles"].preferences
cp.refresh_devices()

print("\n--- Compute Devices ---")
all_devices = []
for dev_type in ("OPTIX", "CUDA", "HIP", "METAL", "OPENCL"):
    try:
        cp.compute_device_type = dev_type
        cp.refresh_devices()
        devs = list(cp.devices)
        if devs:
            print(f"  Device type: {dev_type}")
            for d in devs:
                print(f"    [{d.type}] {d.name}  use={d.use}")
            all_devices.extend(devs)
            break
    except Exception as e:
        print(f"  {dev_type}: {e}")

gpu_ok = False
if all_devices:
    # Enable all GPU devices
    for d in all_devices:
        if d.type != "CPU":
            d.use = True
            gpu_ok = True
    gpu_names = [d.name for d in all_devices if d.type != "CPU"]
    print(f"\nGPU devices enabled: {gpu_names}")
else:
    print("WARNING: No GPU devices found, will use CPU")

# Set render engine
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.device = "GPU" if gpu_ok else "CPU"
print(f"Render engine: {bpy.context.scene.render.engine}")
print(f"Cycles device: {bpy.context.scene.cycles.device}")
print(f"GPU OK: {gpu_ok}")

# ── 2. Tiny GPU render test (2×2 pixels) ───────────────────────
print("\n--- Tiny GPU Render Test ---")
try:
    scene = bpy.context.scene
    scene.render.resolution_x = 2
    scene.render.resolution_y = 2
    scene.render.filepath = "/tmp/gpu_test_2x2.png"
    scene.cycles.samples = 1
    bpy.ops.render.render(write_still=True)
    print("Tiny GPU render: SUCCESS")
    assert os.path.exists("/tmp/gpu_test_2x2.png"), "Output file missing"
    print("GPU render output file confirmed.")
except Exception as e:
    print(f"Tiny GPU render FAILED: {e}")
    gpu_ok = False

# ── 3. Import godwyn_rigged_raw.glb ────────────────────────────
GLB_PATH = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_rigged_raw.glb")
print(f"\n--- Importing {GLB_PATH} ---")

# Clear existing objects first
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

try:
    bpy.ops.import_scene.gltf(filepath=GLB_PATH)
    print("Import: SUCCESS")
except Exception as e:
    print(f"Import FAILED: {e}")
    sys.exit(1)

# ── 4. Enumerate objects ────────────────────────────────────────
print("\n--- All objects in scene ---")
for obj in bpy.data.objects:
    print(f"  [{obj.type}] {obj.name}")

# ── 5. Armature report ─────────────────────────────────────────
print("\n--- Armature Report ---")
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if not armatures:
    print("ERROR: No armature found!")
else:
    for arm_obj in armatures:
        arm = arm_obj.data
        bones = arm.bones
        print(f"Armature object: {arm_obj.name}")
        print(f"Armature data:   {arm.name}")
        print(f"Bone count:      {len(bones)}")
        bone_names = [b.name for b in bones]
        print(f"All bones: {bone_names}")
        # Sample Mixamo-style humanoid bones
        mixamo_check = ["Hips", "Spine", "LeftArm", "RightArm", "LeftLeg", "RightLeg",
                        "Head", "Neck", "LeftHand", "RightHand", "LeftFoot", "RightFoot"]
        found = [b for b in mixamo_check if b in bone_names]
        missing = [b for b in mixamo_check if b not in bone_names]
        print(f"Mixamo humanoid bones found:   {found}")
        print(f"Mixamo humanoid bones missing: {missing}")

# ── 6. Mesh report ─────────────────────────────────────────────
print("\n--- Mesh Report ---")
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if not meshes:
    print("ERROR: No meshes found!")
else:
    for mesh_obj in meshes:
        mesh = mesh_obj.data
        print(f"\nMesh object: {mesh_obj.name}")
        print(f"Vert count:  {len(mesh.vertices)}")
        # Vertex groups (skinning)
        vg_names = [vg.name for vg in mesh_obj.vertex_groups]
        print(f"Vertex groups ({len(vg_names)}): {vg_names[:20]}{'...' if len(vg_names) > 20 else ''}")
        skinned = len(vg_names) > 0
        print(f"Skinned (has vertex groups): {skinned}")
        # UV maps
        uv_maps = [uv.name for uv in mesh.uv_layers]
        print(f"UV maps ({len(uv_maps)}): {uv_maps}")
        has_uv = len(uv_maps) > 0
        print(f"Has UV map: {has_uv}")
        # Materials and image textures
        print(f"Materials ({len(mesh_obj.material_slots)}):")
        for slot in mesh_obj.material_slots:
            mat = slot.material
            if mat is None:
                print(f"  (empty slot)")
                continue
            print(f"  Material: {mat.name}")
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        img = node.image
                        img_name = img.name if img else "(no image)"
                        # Try to identify channel by checking connected socket label
                        # Check what socket this node's Color output connects to
                        connected_to = []
                        for link in mat.node_tree.links:
                            if link.from_node == node:
                                connected_to.append(f"{link.to_node.name}.{link.to_socket.name}")
                        print(f"    TEX_IMAGE node '{node.label or node.name}': image={img_name}  -> {connected_to}")
            else:
                print(f"    (no node tree)")

# ── 7. Identify stray objects ──────────────────────────────────
print("\n--- Stray / Non-character Objects ---")
char_types = {'ARMATURE', 'MESH'}
stray = [o for o in bpy.data.objects if o.type not in char_types]
if stray:
    for s in stray:
        print(f"  STRAY [{s.type}] {s.name}")
else:
    print("  None (all objects are ARMATURE or MESH)")

# Also flag suspiciously named meshes (e.g. Icosphere)
suspect_names = [o.name for o in meshes if any(k in o.name.lower() for k in ["icosphere", "cube", "plane", "cylinder", "sphere"])]
if suspect_names:
    print(f"  Suspect mesh names (non-character): {suspect_names}")

print("\n" + "=" * 60)
print("PHASE 0 PROBE COMPLETE")
print(f"GPU OK: {gpu_ok}")
print("=" * 60)
