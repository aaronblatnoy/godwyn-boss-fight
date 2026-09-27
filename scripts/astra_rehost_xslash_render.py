"""Render the cloth-fixed X-slash and the three worst before/after stills."""
import bpy
import json
import sys
from pathlib import Path


args = sys.argv[sys.argv.index("--") + 1:]
mode = args[0]


def configure(scene, motion_blur):
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 32
    scene.render.use_motion_blur = motion_blur


def render_at(scene, frame, path):
    scene.frame_set(int(frame), subframe=frame % 1.0)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("XSLASH CLOTH RENDER", frame, path, flush=True)


if mode == "full":
    model, output = Path(args[1]), Path(args[2])
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    assert [scene.frame_start, scene.frame_end] == [1, 90]
    configure(scene, True)
    output.mkdir(parents=True, exist_ok=True)
    for frame in range(1, 91):
        render_at(scene, float(frame), output / f"{frame:03d}.png")
elif mode == "comparisons":
    before_model, after_model, before_json, output = map(Path, args[1:5])
    worst = json.loads(before_json.read_text())["three_worst_samples"]
    frames = [float(row["frame"]) for row in worst]
    output.mkdir(parents=True, exist_ok=True)
    for label, model in (("before", before_model), ("after", after_model)):
        bpy.ops.wm.open_mainfile(filepath=str(model))
        scene = bpy.context.scene
        configure(scene, False)
        for index, frame in enumerate(frames, 1):
            render_at(scene, frame, output / f"{index:02d}_{label}.png")
    (output / "frames.json").write_text(json.dumps({
        "frames": frames,
        "left": "before: models/astra_xslash_v2_final_on_char2_wip.blend",
        "right": "after: models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
        "render": {"resolution": [768, 768], "samples": 32,
                   "engine": "BLENDER_EEVEE", "motion_blur": False},
    }, indent=2) + "\n")
else:
    raise ValueError(mode)
