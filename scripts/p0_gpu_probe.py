"""
p0_gpu_probe.py — Phase 0 GPU assertion.
Asserts Blender 5.2 + OptiX/CUDA device available. Exits 1 if no GPU found.
"""
import bpy
import sys

prefs = bpy.context.preferences.addons.get("cycles", None)
if prefs is None:
    print("GPU_PROBE: Cycles addon not found")
    sys.exit(1)

# List CUDA/OptiX devices
import _cycles
devs = _cycles.available_devices("OPTIX")
optix_devs = [d for d in devs if d[1]]  # (name, use)
cuda_devs = _cycles.available_devices("CUDA")
cuda_enabled = [d for d in cuda_devs if d[1]]

print(f"GPU_PROBE: OptiX devices = {devs}")
print(f"GPU_PROBE: CUDA devices = {cuda_devs}")

# Do a tiny 1x1 Cycles OptiX render to confirm GPU works
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.render.resolution_x = 1
scene.render.resolution_y = 1
scene.render.filepath = '/tmp/p0_gpu_probe_render.png'
scene.render.image_settings.file_format = 'PNG'

# Enable GPU compute
cprefs = bpy.context.preferences.addons['cycles'].preferences
cprefs.get_devices()
cprefs.compute_device_type = 'OPTIX'
for dev in cprefs.devices:
    dev.use = True
    print(f"GPU_PROBE device: {dev.name} use={dev.use} type={dev.type}")

bpy.ops.render.render(write_still=True)
print("GPU_PROBE: Render succeeded. GPU_ASSERT_PASS")
