"""Quick GPU re-shot of ONLY the tabard detail view (p4 r2 hem iteration).

Run: blender --background models/godwyn_phase1.blend \
        --python scripts/p4_tabard_reshot.py
"""
import os
import sys

import bpy
from mathutils import Vector

_REPO = os.path.expanduser("~/godwyn-boss-fight")
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import lib_godwyn as G  # noqa: E402

scene = bpy.context.scene
dev = G.enable_gpu(prefer_optix=True)
assert dev in ("OPTIX", "CUDA"), "FATAL: no GPU"
scene.render.engine = "CYCLES"
scene.cycles.device = "GPU"
scene.cycles.samples = 192
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = "PNG"

cam_data = bpy.data.cameras.new("Cam_TabReshot")
cam_data.lens = 55
cam = bpy.data.objects.new("Cam_TabReshot", cam_data)
scene.collection.objects.link(cam)
cam.location = Vector((0.9, -4.2, 1.05))
d = Vector((0.0, 0.0, 0.85)) - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
scene.render.resolution_x = 1400
scene.render.resolution_y = 1500
out = os.path.join(_REPO, "renders", "wip", "c_r2_tabard.png")
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
assert os.path.isfile(out) and os.path.getsize(out) > 1024
print(f"[reshot] wrote {out} ({os.path.getsize(out)//1024} KB)")
