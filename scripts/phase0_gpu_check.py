"""
Phase 0 — GPU / Blender version gate.
Checks:
  - Blender version (expect 5.1.x)
  - Cycles + OptiX enumeration of all GPU devices
  - Runs a tiny 1x1 GPU render to confirm GPU compute actually works
Prints a structured PASS/FAIL report.
"""

import sys
import bpy

print("=" * 60)
print("PHASE 0 — GPU GATE")
print("=" * 60)

# ── Blender version ────────────────────────────────────────────
v = bpy.app.version
ver_str = ".".join(str(x) for x in v)
print(f"Blender version : {ver_str}")
if v < (5, 1, 0):
    print("FAIL: need >= 5.1.0")
    sys.exit(1)
print("OK: Blender version")

# ── Cycles OptiX device enum ───────────────────────────────────
prefs = bpy.context.preferences
cprefs = prefs.addons["cycles"].preferences

cprefs.get_devices()
cprefs.compute_device_type = "OPTIX"
cprefs.get_devices()

print("\nDevice table (OptiX):")
gpu_count = 0
for dev in cprefs.devices:
    tag = "[GPU]" if dev.type in ("OPTIX", "CUDA") else "[CPU]"
    use = "USE" if dev.use else "---"
    print(f"  {use}  {tag}  {dev.name}")
    if dev.type in ("OPTIX", "CUDA"):
        dev.use = True
        gpu_count += 1

print(f"\nGPU devices found: {gpu_count}")
if gpu_count == 0:
    print("FAIL: no GPU devices detected")
    sys.exit(1)
print(f"OK: {gpu_count} GPU(s) enabled")

# ── Tiny GPU render (1×1, 1 sample) ───────────────────────────
print("\nRunning 1x1 GPU smoke test …")
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU"
scene.render.resolution_x = 1
scene.render.resolution_y = 1
scene.cycles.samples = 1
scene.render.filepath = "/tmp/phase0_gpu_smoketest.png"  # /tmp is safe on both root and user sessions
scene.render.image_settings.file_format = "PNG"

try:
    bpy.ops.render.render(write_still=True)
    print("OK: GPU smoke-test render completed")
except Exception as e:
    print(f"FAIL: GPU render error — {e}")
    sys.exit(1)

print("\n=== PHASE 0 GPU GATE: PASS ===")
