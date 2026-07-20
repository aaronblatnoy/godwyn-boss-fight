"""
p0_gpu_cycles_assert.py — Assert GPU (OptiX/CUDA) is available for Cycles.
Runs a tiny 1x1 Cycles render to confirm GPU works. Prints GPU device table.
"""
import bpy
import sys

# Print device table
print("=== Blender Cycles GPU Device Table ===")
prefs = bpy.context.preferences
cprefs = prefs.addons.get("cycles")
if cprefs:
    cycles_prefs = cprefs.preferences
    cycles_prefs.refresh_devices()
    found_gpu = False
    for device_type in ("OPTIX", "CUDA", "HIP", "METAL"):
        try:
            cycles_prefs.compute_device_type = device_type
            devices = cycles_prefs.get_devices_for_type(device_type)
            if devices:
                for d in devices:
                    print(f"  [{device_type}] {d.name} use={d.use}")
                    if device_type in ("OPTIX", "CUDA"):
                        found_gpu = True
        except Exception as e:
            pass  # device type not available on this platform

    # Assert OptiX or CUDA available
    cycles_prefs.compute_device_type = "OPTIX"
    optix_devices = cycles_prefs.get_devices_for_type("OPTIX")
    if optix_devices:
        for d in optix_devices:
            d.use = True
        print("GPU_ASSERT: OptiX available -- PASS")
    else:
        cycles_prefs.compute_device_type = "CUDA"
        cuda_devices = cycles_prefs.get_devices_for_type("CUDA")
        if cuda_devices:
            for d in cuda_devices:
                d.use = True
            print("GPU_ASSERT: CUDA available (no OptiX) -- PASS")
        else:
            print("GPU_ASSERT: NO GPU FOUND -- FAIL")
            sys.exit(1)

    # Tiny 1x1 Cycles render to confirm GPU doesn't crash
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = 1
    scene.render.resolution_y = 1
    scene.render.filepath = "/tmp/p0_gpu_assert_1x1.png"
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    print("GPU_RENDER_TEST: 1x1 Cycles render completed -- PASS")
else:
    print("WARNING: cycles addon not found in preferences")
    print("GPU_ASSERT: SKIPPED (no cycles addon)")
