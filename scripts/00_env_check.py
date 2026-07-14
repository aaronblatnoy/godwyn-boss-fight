"""
00_env_check.py — Phase 0 environment check for the Godwyn headless pipeline.

Validates:
  1. Blender version is 4.x or newer
  2. Cycles computes on GPU (OptiX preferred, CUDA fallback)
  3. At least 1 RTX 3060 Ti device is ENABLED
  4. A 1080p test frame (single cube) renders to /tmp/godwyn_env_test.png
     and the output file is non-empty

Exits 0 on success, 1 on any GPU or render failure (INV-2: fail loud).

Usage (headless):
  blender --background --python ~/godwyn-boss-fight/scripts/00_env_check.py 2>&1
"""

import sys
import os
import bpy
import mathutils

# ---------------------------------------------------------------------------
# 0. Blender version check
# ---------------------------------------------------------------------------
ver = bpy.app.version
ver_str = ".".join(str(v) for v in ver)
print(f"\n[00_env_check] Blender version: {ver_str}")
# Accept 4.x AND 5.x (mossad has 5.1.2)
if ver[0] < 4:
    print(f"[00_env_check] FATAL: Blender {ver_str} is < 4.0. Need Blender 4+.",
          file=sys.stderr)
    sys.exit(1)
print(f"[00_env_check] Version check PASSED ({ver_str} >= 4.0)\n")

# ---------------------------------------------------------------------------
# 1. Import shared library
# ---------------------------------------------------------------------------
# Add scripts/ dir to path so lib_godwyn is importable
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

import lib_godwyn as lg

# ---------------------------------------------------------------------------
# 2. Reset scene to a clean slate
# ---------------------------------------------------------------------------
lg.reset_scene()

# ---------------------------------------------------------------------------
# 3. Enable GPU + print device table (INV-2 validation)
# ---------------------------------------------------------------------------
active_gpu_type = lg.enable_gpu(prefer_optix=True)
# enable_gpu() already sys.exit(1) if no GPU found; if we reach here, >=1 GPU

# ---------------------------------------------------------------------------
# 4. Build a minimal test scene: 1 cube + 1 area light + 1 camera
# ---------------------------------------------------------------------------
scene = bpy.context.scene
scene.name = "GodwynEnvTest"

# Cube
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "TestCube"

# Simple grey material on the cube
mat = bpy.data.materials.new("TestMat")
mat.use_nodes = True
nt = mat.node_tree
nt.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
cube.data.materials.append(mat)

# Key light (warm, from above-right)
bpy.ops.object.light_add(type="AREA", location=(4, -3, 6))
key_light = bpy.context.active_object
key_light.name = "TestKeyLight"
key_light.data.energy = 500
key_light.data.size = 3.0
key_light.data.color = (1.0, 0.95, 0.85)
key_light.rotation_euler = (0.8, 0.2, 0.5)

# Camera
bpy.ops.object.camera_add(location=(5, -5, 3.5))
cam = bpy.context.active_object
cam.name = "TestCam"
cam.rotation_euler = (1.1, 0.0, 0.785)
scene.camera = cam

# ---------------------------------------------------------------------------
# 5. Configure Cycles GPU render (1080p test — fast)
# ---------------------------------------------------------------------------
lg.configure_cycles(
    scene=scene,
    samples=32,           # quick test — just enough to show GPU is working
    resolution_x=1920,
    resolution_y=1080,
    use_denoiser=True,
    film_transparent=False,
)

# ---------------------------------------------------------------------------
# 6. Render test frame -> /tmp/godwyn_env_test.png
# ---------------------------------------------------------------------------
OUT_PATH = "/tmp/godwyn_env_test.png"
print(f"[00_env_check] Rendering 1080p GPU test frame -> {OUT_PATH}")

# render_to_path asserts GPU device is still set before rendering
lg.render_to_path(OUT_PATH, scene=scene)

# ---------------------------------------------------------------------------
# 7. Assert output is non-empty
# ---------------------------------------------------------------------------
if not os.path.exists(OUT_PATH):
    print(f"[00_env_check] FATAL: output PNG not found at {OUT_PATH}",
          file=sys.stderr)
    sys.exit(1)

size_bytes = os.path.getsize(OUT_PATH)
if size_bytes == 0:
    print(f"[00_env_check] FATAL: output PNG at {OUT_PATH} is 0 bytes",
          file=sys.stderr)
    sys.exit(1)

print(f"\n[00_env_check] Test PNG: {OUT_PATH}  ({size_bytes:,} bytes)  OK")

# ---------------------------------------------------------------------------
# 8. Final summary
# ---------------------------------------------------------------------------
prefs = bpy.context.preferences
cprefs = prefs.addons["cycles"].preferences
enabled_gpus = [d.name for d in cprefs.devices
                if d.use and d.type in ("OPTIX", "CUDA")]

print("\n" + "=" * 60)
print("[00_env_check] PHASE 0 VALIDATION SUMMARY")
print("=" * 60)
print(f"  Blender version : {ver_str}")
print(f"  GPU type active : {active_gpu_type}  (Using {active_gpu_type})")
print(f"  GPUs enabled    : {len(enabled_gpus)}")
for g in enabled_gpus:
    print(f"    - {g}")
print(f"  Test render     : {OUT_PATH}  ({size_bytes:,} bytes)")
print(f"  Scene device    : {scene.cycles.device}")
print("=" * 60)
print("[00_env_check] ALL CHECKS PASSED — Phase 0 environment is GO.\n")

sys.exit(0)
