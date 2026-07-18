"""
Phase 5 critic round 1 — beauty renders for art-direction review.

Opens models/godwyn_phase1.blend (read-only judgement pass: NO scene edits are
saved), asserts a GPU (OptiX/CUDA) device is enabled (CPU fallback = hard
failure), then renders lit beauty shots from the full-body and face cameras
at review-quality samples with denoising to renders/wip/p5_r1_*.png.

Run:
  blender --background models/godwyn_phase1.blend \
      --python scripts/p5_critic_render_r1.py
"""
import os
import sys

import bpy

_REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
import lib_godwyn as G  # noqa: E402

_WIP = os.path.join(_REPO_ROOT, "renders", "wip")
os.makedirs(_WIP, exist_ok=True)

SHOTS = [
    # (camera object name, output filename, resolution (x, y))
    ("Cam_ThreeQuarter_L", "p5_r1_full.png", (1280, 1600)),
    ("Cam_Front",          "p5_r1_front.png", (1280, 1600)),
    ("Cam_Face",           "p5_r1_face.png", (1280, 1280)),
]

SAMPLES = 192


def main():
    scene = bpy.context.scene

    # --- GPU gate: fail loud on CPU fallback -------------------------------
    dev_type = G.enable_gpu(prefer_optix=True)
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpu_devs = [d for d in prefs.devices
                if d.use and d.type in ("OPTIX", "CUDA")]
    assert dev_type in ("OPTIX", "CUDA") and gpu_devs, (
        "FATAL: no GPU (OptiX/CUDA) compute device enabled — refusing CPU "
        "fallback.")
    print(f"[p5] GPU OK: {dev_type} — "
          + ", ".join(d.name for d in gpu_devs))

    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPTIX"
    except TypeError:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    missing = [name for name, _, _ in SHOTS if name not in bpy.data.objects]
    assert not missing, f"FATAL: cameras missing from .blend: {missing}"

    for cam_name, out_name, (rx, ry) in SHOTS:
        scene.camera = bpy.data.objects[cam_name]
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        scene.render.resolution_percentage = 100
        out = os.path.join(_WIP, out_name)
        scene.render.filepath = out
        print(f"[p5] rendering {cam_name} -> {out} "
              f"({rx}x{ry} @ {SAMPLES}spp, denoise on)")
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(out), f"FATAL: render missing: {out}"
        print(f"[p5] wrote {out} ({os.path.getsize(out)} bytes)")

    print("[p5] critic renders complete.")


if __name__ == "__main__":
    main()
