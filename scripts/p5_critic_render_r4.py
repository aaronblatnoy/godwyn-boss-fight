"""
Phase 5 critic round 4 — beauty renders for art-direction review.

Opens models/godwyn_phase1.blend (read-only judgement pass: NO scene edits are
saved), asserts a GPU (OptiX/CUDA) device is enabled (CPU fallback = hard
failure), then renders lit beauty shots from the full-body and face cameras
at review-quality samples with denoising to renders/wip/p5_r4_*.png.

Run:
  blender --background models/godwyn_phase1.blend \
      --python scripts/p5_critic_render_r4.py
"""
import os
import sys

import bpy

_REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
import lib_godwyn as G  # noqa: E402

_WIP = os.path.join(_REPO_ROOT, "renders", "wip")
os.makedirs(_WIP, exist_ok=True)

# Full-body camera: prefer "Cam_Full" if it exists, else fall back to the
# established full-body review cameras from round 1.
_FULL_CANDIDATES = ["Cam_Full", "Cam_ThreeQuarter_L", "Cam_Front"]

SAMPLES = 256


def _pick_full_cam():
    for name in _FULL_CANDIDATES:
        if name in bpy.data.objects:
            return name
    cams = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    raise AssertionError(
        f"FATAL: no full-body camera among {_FULL_CANDIDATES}; "
        f"cameras present: {cams}")


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
    print(f"[p5r4] GPU OK: {dev_type} — "
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

    full_cam = _pick_full_cam()
    assert "Cam_Face" in bpy.data.objects, (
        "FATAL: Cam_Face missing from .blend")
    print(f"[p5r4] full-body camera: {full_cam}")

    shots = [
        (full_cam,   "p5_r4_full.png", (1280, 1600)),
        ("Cam_Face", "p5_r4_face.png", (1280, 1280)),
    ]

    for cam_name, out_name, (rx, ry) in shots:
        scene.camera = bpy.data.objects[cam_name]
        scene.render.resolution_x = rx
        scene.render.resolution_y = ry
        scene.render.resolution_percentage = 100
        out = os.path.join(_WIP, out_name)
        scene.render.filepath = out
        print(f"[p5r4] rendering {cam_name} -> {out} "
              f"({rx}x{ry} @ {SAMPLES}spp, denoise on)")
        bpy.ops.render.render(write_still=True)
        assert os.path.isfile(out), f"FATAL: render missing: {out}"
        print(f"[p5r4] wrote {out} ({os.path.getsize(out)} bytes)")

    print("[p5r4] critic renders complete.")


if __name__ == "__main__":
    main()
