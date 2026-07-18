"""
Phase 5 fixer round 5 (r2 fixes) — verification renders (full / face / right hand).

Opens models/godwyn_phase1.blend read-only (nothing saved), asserts a GPU
(OptiX/CUDA) device (CPU fallback = hard failure), renders:
  p5_fix5_full.png  — Cam_Full (r4: 3/4-nudged so the grip reads), figure
                      vs the now-distant void crack
  p5_fix5_face.png  — Cam_Face: nose/mouth/brow relief, symmetric lidded
                      eyes with round catchlights, parted hairline + braid
  p5_fix5_hand.png  — temp camera on the right-hand sword grip

Run:
  blender --background --python scripts/p5_fixer_r4_check.py
"""
import os
import sys

import bpy
from mathutils import Vector

_REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
import lib_godwyn as G  # noqa: E402

_WIP = os.path.join(_REPO_ROOT, "renders", "wip")
os.makedirs(_WIP, exist_ok=True)

BLEND = os.path.join(_REPO_ROOT, "models", "godwyn_phase1.blend")
SAMPLES = 256


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    scene = bpy.context.scene

    dev_type = G.enable_gpu(prefer_optix=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpu_devs = [d for d in prefs.devices
                if d.use and d.type in ("OPTIX", "CUDA")]
    assert dev_type in ("OPTIX", "CUDA") and gpu_devs, \
        "FATAL: no GPU (OptiX/CUDA) device — refusing CPU fallback."
    print(f"[p5fix5] GPU OK: {dev_type}")

    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    # temp hand camera aimed at the posed sword grip
    sword = bpy.data.objects["Godwyn_Sword"]
    grip = sword.matrix_world.translation
    cam_data = bpy.data.cameras.new("_HandCam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("_HandCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = grip + Vector((0.9, -1.3, 0.35))
    d = grip - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    shots = [
        ("Cam_Full", "p5_fix5_full.png", (1280, 1600)),
        ("Cam_Face", "p5_fix5_face.png", (1280, 1280)),
        ("_HandCam", "p5_fix5_hand.png", (1024, 1024)),
    ]
    for cam_name, out_name, (rx, ry) in shots:
        scene.camera = bpy.data.objects[cam_name]
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        scene.render.resolution_percentage = 100
        out = os.path.join(_WIP, out_name)
        scene.render.filepath = out
        print(f"[p5fix5] rendering {cam_name} -> {out}")
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(out), f"FATAL: render missing: {out}"
        print(f"[p5fix5] wrote {out} ({os.path.getsize(out)} bytes)")
    print("[p5fix5] verification renders complete.")


if __name__ == "__main__":
    main()
