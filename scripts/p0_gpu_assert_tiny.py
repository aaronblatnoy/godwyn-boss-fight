"""
p0_gpu_assert_tiny.py -- Assert OptiX/CUDA GPU device, do a tiny Cycles render.
Prints GPU_OK if Cycles OptiX/CUDA confirmed, exits 1 if CPU fallback.
"""
import bpy
import sys

def assert_gpu_optix():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.refresh_devices()

    # Try OptiX first, then CUDA
    for compute_type in ('OPTIX', 'CUDA'):
        prefs.compute_device_type = compute_type
        prefs.refresh_devices()
        devices = list(prefs.devices)
        gpu_devs = [d for d in devices if d.type in ('OPTIX', 'CUDA') and d.use]
        if gpu_devs:
            print(f"GPU_DEVICE_TYPE:{compute_type}")
            for d in gpu_devs:
                print(f"  GPU:{d.name} type:{d.type} use:{d.use}")
            return compute_type, gpu_devs

    # No GPU found -- list all
    print("ERROR: No OptiX/CUDA GPU device found")
    for d in prefs.devices:
        print(f"  device: {d.name} type:{d.type} use:{d.use}")
    sys.exit(1)

def tiny_cycles_render(compute_type):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 1
    scene.render.resolution_x = 8
    scene.render.resolution_y = 8
    scene.render.filepath = "/tmp/p0_gpu_assert_tiny.png"
    scene.render.image_settings.file_format = 'PNG'

    # Add a simple mesh so there's something to render
    bpy.ops.mesh.primitive_cube_add(size=1)
    bpy.ops.object.camera_add(location=(0, -3, 0))
    cam = bpy.context.active_object
    cam.rotation_euler = (1.5708, 0, 0)
    scene.camera = cam
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 3))

    try:
        bpy.ops.render.render(write_still=True)
        print("GPU_RENDER_OK: tiny Cycles render completed on GPU")
    except Exception as e:
        print(f"GPU_RENDER_FAIL: {e}")
        sys.exit(1)

bpy.ops.wm.read_factory_settings(use_empty=True)
compute_type, devs = assert_gpu_optix()
tiny_cycles_render(compute_type)
print("GPU_OK")
