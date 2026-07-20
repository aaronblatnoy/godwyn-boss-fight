"""
p0_gpu_assert.py — GPU assertion for Phase 0.
Adds a camera, does a tiny EEVEE render (always works) then a Cycles OptiX render.
Asserts at least 1 GPU (CUDA/OptiX) device is enabled. Exits 0 on pass.
"""
import bpy
import sys

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Add a camera so render doesn't fail
bpy.ops.object.camera_add(location=(0, -5, 2))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0, 0)
scene.camera = cam

# Add a mesh and light so render has something
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))

# EEVEE render first (fast, always works)
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 4
scene.render.resolution_y = 4
scene.render.filepath = '/tmp/p0_eevee_assert.png'
scene.render.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print("GPU_ASSERT: EEVEE render OK")

# Now Cycles + OptiX
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
cprefs = bpy.context.preferences.addons['cycles'].preferences
cprefs.compute_device_type = 'OPTIX'
cprefs.get_devices()
for dev in cprefs.devices:
    if dev.type in ('CUDA', 'OPTIX'):
        dev.use = True

gpu_devices = [d.name for d in cprefs.devices if d.type in ('CUDA', 'OPTIX') and d.use]
print(f"GPU_ASSERT: active GPU devices = {gpu_devices}")
if not gpu_devices:
    print("GPU_ASSERT: FAIL — no GPU devices found")
    sys.exit(1)

scene.render.filepath = '/tmp/p0_cycles_assert.png'
bpy.ops.render.render(write_still=True)
print(f"GPU_ASSERT_PASS: Cycles OptiX render OK with {len(gpu_devices)} GPU(s): {gpu_devices}")
