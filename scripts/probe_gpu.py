"""
probe_gpu.py — Assert Cycles OptiX GPU device is available and renders.
Renders a 1x1 pixel test image; fails if no GPU device found.
"""
import bpy
import sys

# Check for CUDA/OptiX devices
prefs = bpy.context.preferences.addons.get('cycles')
if prefs:
    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
    cycles_prefs.refresh_devices()
    devices = list(cycles_prefs.devices)
    gpu_devices = [d for d in devices if d.type in ('CUDA', 'OPTIX', 'HIP') and d.use]
    all_devices = [(d.name, d.type, d.use) for d in devices]
    print(f"ALL_DEVICES: {all_devices}")
    if gpu_devices:
        print(f"GPU_ASSERT_PASS: {[(d.name, d.type) for d in gpu_devices]}")
    else:
        # Try enabling all CUDA/OptiX
        for d in devices:
            if d.type in ('CUDA', 'OPTIX'):
                d.use = True
        gpu_devices = [d for d in devices if d.type in ('CUDA', 'OPTIX') and d.use]
        if gpu_devices:
            print(f"GPU_ASSERT_PASS (enabled): {[(d.name, d.type) for d in gpu_devices]}")
        else:
            print(f"GPU_ASSERT_FAIL: no CUDA/OptiX device found. Devices: {all_devices}")
            sys.exit(1)
else:
    print("GPU_ASSERT_FAIL: cycles addon not found")
    sys.exit(1)

# Quick 1x1 Cycles render to confirm GPU actually works
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.render.resolution_x = 1
scene.render.resolution_y = 1
scene.render.filepath = '/tmp/probe_gpu_test.png'
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print("GPU_RENDER_OK: 1x1 Cycles render completed")
