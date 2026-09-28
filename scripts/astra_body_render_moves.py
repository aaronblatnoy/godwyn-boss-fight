"""Render body-i02 move evidence at the existing 768-square EEVEE settings."""
import bpy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/rehost_body_i02"
JOBS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_body_i02.blend", 48),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_body_i02.blend", 36),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_body_i02.blend", 40),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_body_i02.blend", 40),
    "xslash": (ROOT / "models/astra_xslash_body_i02.blend", 55),
}


def configure(scene, motion_blur):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = motion_blur
    scene.render.motion_blur_shutter = 0.45
    scene.render.fps = 30


def render_stills():
    manifest = {}
    for name, (model, frame) in JOBS.items():
        bpy.ops.wm.open_mainfile(filepath=str(model))
        scene = bpy.context.scene
        configure(scene, False)
        scene.frame_set(frame)
        destination = OUT / f"{name}_extended.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        manifest[name] = {
            "model": str(model.relative_to(ROOT)),
            "frame": frame,
            "path": str(destination.relative_to(ROOT)),
        }
        print("BODY_MOVE_STILL", name, frame, flush=True)
    (OUT / "meshy_body_move_stills.json").write_text(json.dumps(manifest, indent=2) + "\n")


def render_animation(name):
    model, _extended = JOBS[name]
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    configure(scene, True)
    folder = OUT / f"{name}_frames"
    folder.mkdir(parents=True, exist_ok=True)
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        scene.render.filepath = str(folder / f"{frame:03d}.png")
        bpy.ops.render.render(write_still=True)
        print("BODY_MOVE_FRAME", name, frame, scene.frame_end, flush=True)
    (OUT / f"{name}_render.json").write_text(json.dumps({
        "model": str(model.relative_to(ROOT)),
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "frame_count": scene.frame_end - scene.frame_start + 1,
        "resolution": [768, 768],
        "fps": 30,
        "engine": "BLENDER_EEVEE",
        "samples": 32,
        "motion_blur": True,
        "frames": str(folder.relative_to(ROOT)),
    }, indent=2) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    args = sys.argv[sys.argv.index("--") + 1:]
    if args[0] == "stills":
        render_stills()
    elif args[0] == "animation" and args[1] in {"rising_spin", "xslash"}:
        render_animation(args[1])
    else:
        raise ValueError(args)


if __name__ == "__main__":
    main()
