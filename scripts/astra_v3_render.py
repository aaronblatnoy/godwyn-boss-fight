"""Render v3 Cycles OptiX heroes or EEVEE film frames on black-sky."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/v3"
BLEND = ROOT / "models/astra_character_v3_wip.blend"
FRAMES = {"idle_guard": 96, "walk_stalk": 72, "lunge_thrust": 64, "rising_spin": 116, "xslash": 90}


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preview", "heroes", "film"))
    parser.add_argument("move", nargs="?", choices=tuple(FRAMES))
    parser.add_argument("--blend", default=str(BLEND.relative_to(ROOT)))
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


def assign_action(rig, name, frame=1):
    action = bpy.data.actions[f"Godwyn_V3_{name}"]
    animation = rig.animation_data_create()
    animation.action = action
    animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def optix(scene):
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "OPTIX"
    preferences.get_devices()
    enabled = []
    for device in preferences.devices:
        device.use = device.type == "OPTIX"
        if device.use:
            enabled.append({"name": device.name, "type": device.type})
    assert enabled, "Cycles OptiX GPU device was not found; CPU rendering is forbidden"
    assert all(item["type"] == "OPTIX" for item in enabled)
    scene.cycles.device = "GPU"
    print("V3_OPTIX_GPU_ASSERT", json.dumps(enabled), flush=True)
    return enabled


def remove_cameras_lights(scene):
    for ob in list(scene.objects):
        if ob.type in {"CAMERA", "LIGHT"} or ob.name.startswith("Astra V3 Render"):
            bpy.data.objects.remove(ob, do_unlink=True)


def studio(scene):
    remove_cameras_lights(scene)
    world = bpy.data.worlds.new("Astra V3 warm neutral studio")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (0.025, 0.030, 0.045, 1.0)
    background.inputs[1].default_value = 0.22
    scene.world = world
    lights = [
        ("Key", (-3.8, -4.8, 5.5), 920.0, 2.6, (1.0, 0.91, 0.78)),
        ("Fill", (4.0, -2.8, 3.7), 360.0, 3.2, (0.68, 0.79, 1.0)),
        ("Rim", (1.5, 3.2, 4.8), 1100.0, 2.2, (1.0, 0.72, 0.42)),
        ("Face", (-0.8, -3.0, 3.1), 220.0, 1.0, (1.0, 0.82, 0.70)),
    ]
    for name, location, energy, size, color in lights:
        data = bpy.data.lights.new(f"Astra V3 Render {name}", "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        ob = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(ob)
        ob.location = location
        aim(ob, (0.0, -0.15, 1.85 if name != "Face" else 2.9))
    camera_data = bpy.data.cameras.new("Astra V3 Render Camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.lens = 85
    scene.camera = camera
    floor_mat = bpy.data.materials.new("Astra V3 Render Floor")
    floor_mat.use_nodes = True
    floor_bsdf = floor_mat.node_tree.nodes.get("Principled BSDF")
    floor_bsdf.inputs["Base Color"].default_value = (0.022, 0.026, 0.040, 1.0)
    floor_bsdf.inputs["Roughness"].default_value = 0.48
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "Astra V3 Render Floor"
    floor.data.materials.append(floor_mat)
    return camera


def configure_common(scene, x, y):
    scene.render.resolution_x = x
    scene.render.resolution_y = y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = 30
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0


def configure_cycles(scene, samples):
    scene.render.engine = "CYCLES"
    devices = optix(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 7
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 4
    return devices


def configure_eevee(scene):
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    assert scene.render.engine.startswith("BLENDER_EEVEE")
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = True
    if hasattr(scene.render, "motion_blur_shutter"):
        scene.render.motion_blur_shutter = 0.45


def evaluated_bounds(objects):
    points = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        evaluated = ob.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        matrix = evaluated.matrix_world
        points.extend(matrix @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    array = np.asarray(points, dtype=np.float32)
    return array.min(axis=0), array.max(axis=0)


def set_camera(camera, location, target, scale):
    camera.location = location
    aim(camera, target)
    camera.data.ortho_scale = scale


def render_one(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    assert path.exists() and path.stat().st_size > 0
    print("V3_RENDER_PASS", str(path.relative_to(ROOT)), path.stat().st_size, flush=True)


def render_preview(scene, camera, rig, assets):
    assign_action(rig, "idle_guard", 1)
    configure_common(scene, 600, 900)
    devices = configure_cycles(scene, 32)
    low, high = evaluated_bounds(assets)
    center = (low + high) * 0.5
    target = Vector((center[0], center[1], (low[2] + high[2]) * 0.5))
    set_camera(camera, Vector((target.x, target.y - 7.0, target.z)), target, max(3.55, float(high[2] - low[2]) * 1.10))
    render_one(scene, OUT / "preview_idle_front.png")
    collar = Vector((0.0, -0.24, 2.69))
    set_camera(camera, Vector((collar.x, collar.y - 4.0, collar.z)), collar, 0.72)
    render_one(scene, OUT / "preview_collar.png")
    return {"mode": "preview", "devices": devices, "resolution": [600, 900], "samples": 32}


def render_heroes(scene, camera, rig, assets):
    assign_action(rig, "idle_guard", 1)
    configure_common(scene, 1200, 1800)
    devices = configure_cycles(scene, 128)
    low, high = evaluated_bounds(assets)
    center = (low + high) * 0.5
    target = Vector((center[0], center[1], (low[2] + high[2]) * 0.5))
    scale = max(3.55, float(high[2] - low[2]) * 1.10)
    views = {
        "hero_idle_front.png": (Vector((target.x, target.y - 7.0, target.z)), target, scale),
        "hero_idle_side.png": (Vector((target.x + 7.0, target.y, target.z)), target, scale),
        "hero_idle_three_quarter.png": (Vector((target.x + 4.7, target.y - 6.0, target.z)), target, scale),
        "hero_comparison_model.png": (Vector((target.x, target.y - 7.0, target.z)), target, scale),
    }
    for filename, (location, view_target, view_scale) in views.items():
        set_camera(camera, location, view_target, view_scale)
        render_one(scene, OUT / filename)
    collar = Vector((0.0, -0.24, 2.69))
    set_camera(camera, Vector((collar.x, collar.y - 4.0, collar.z)), collar, 0.72)
    render_one(scene, OUT / "hero_collar_closeup.png")
    face = Vector((0.03, -0.25, 2.95))
    set_camera(camera, Vector((face.x, face.y - 4.0, face.z)), face, 0.68)
    render_one(scene, OUT / "hero_face_closeup.png")
    return {"mode": "heroes", "devices": devices, "resolution": [1200, 1800], "samples": 128, "frame": 1, "action": "Godwyn_V3_idle_guard"}


def render_film(scene, camera, rig, assets, name):
    count = FRAMES[name]
    assign_action(rig, name, 1)
    configure_common(scene, 768, 768)
    configure_eevee(scene)
    low, high = evaluated_bounds(assets)
    center = (low + high) * 0.5
    target = Vector((center[0], center[1], 1.62))
    camera_location = Vector((target.x + 4.8, target.y - 6.4, 2.25))
    set_camera(camera, camera_location, target, 4.05)
    hips_start = rig.matrix_world @ rig.pose.bones["Hips"].head
    folder = OUT / f"{name}_frames"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    for frame in range(1, count + 1):
        assign_action(rig, name, frame)
        hips = rig.matrix_world @ rig.pose.bones["Hips"].head
        follow = Vector((hips.x - hips_start.x, hips.y - hips_start.y, 0.0))
        set_camera(camera, camera_location + follow, target + follow, 4.05)
        path = folder / f"{frame:03d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if frame == 1 or frame == count or frame % 15 == 0:
            print("V3_FILM_FRAME", name, frame, count, flush=True)
    assert len(list(folder.glob("*.png"))) == count
    return {
        "mode": "film",
        "move": name,
        "engine": scene.render.engine,
        "resolution": [768, 768],
        "fps": 30,
        "frames": count,
        "camera": "three-quarter root-follow in XY; vertical motion remains visible",
        "frame_directory": str(folder.relative_to(ROOT)),
    }


def main():
    args = cli()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(root_path(args.blend)), load_ui=False)
    scene = bpy.context.scene
    rig = bpy.data.objects["Astra_V3_Rig"]
    asset_names = (
        "char1", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend",
        "Astra_V3_Neck_Gorget_Trim", "Godwyn_Sword",
    )
    assets = [bpy.data.objects[name] for name in asset_names if name in bpy.data.objects]
    camera = studio(scene)
    if args.mode == "preview":
        report = render_preview(scene, camera, rig, assets)
    elif args.mode == "heroes":
        report = render_heroes(scene, camera, rig, assets)
    else:
        assert args.move
        report = render_film(scene, camera, rig, assets, args.move)
    path = OUT / (f"{args.mode}_{args.move}_render.json" if args.move else f"{args.mode}_render.json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_RENDER_COMPLETE", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
