"""Cycles/OptiX renders for the V3 mocap and head-attachment pass.

All invocations are intended for black-sky.  Modes:
  before -- two diagnostic renders from the published pre-fix blend
  heroes -- final Combat_Stance heroes
  film <clip> -- all frames for one clip at 768 square
"""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/v3m"


def cli():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("before", "heroes", "film"))
    parser.add_argument("clip", nargs="?")
    parser.add_argument("--blend", default="models/astra_character_v3.blend")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--step", type=int, default=1)
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def assign_action(rig, action, frame):
    animation = rig.animation_data_create()
    animation.action = action
    if action.slots:
        animation.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


def enable_optix(scene):
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "OPTIX"
    preferences.get_devices()
    enabled = []
    for device in preferences.devices:
        device.use = device.type == "OPTIX"
        if device.use:
            enabled.append({"name": device.name, "type": device.type})
    assert enabled and all(row["type"] == "OPTIX" for row in enabled), enabled
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    print("V3M_OPTIX_ASSERT", json.dumps(enabled), flush=True)
    return enabled


def studio(scene):
    for ob in list(scene.objects):
        if ob.type in {"CAMERA", "LIGHT"} or ob.name.startswith("V3M_Render_"):
            bpy.data.objects.remove(ob, do_unlink=True)
    world = bpy.data.worlds.new("V3M_Render_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.018, 0.023, 0.038, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.18
    scene.world = world
    lights = [
        ("Key", (-3.8, -4.8, 5.6), 1050.0, 2.5, (1.0, 0.90, 0.76), (0, 0, 1.9)),
        ("Fill", (4.2, -2.8, 3.8), 420.0, 3.0, (0.64, 0.77, 1.0), (0, 0, 1.8)),
        ("Rim", (1.4, 3.4, 5.0), 1200.0, 2.2, (1.0, 0.65, 0.32), (0, 0, 2.1)),
        ("Face", (-0.7, -2.5, 3.2), 280.0, 0.9, (1.0, 0.79, 0.68), (0, -0.1, 2.9)),
    ]
    for name, location, energy, size, color, target in lights:
        data = bpy.data.lights.new(f"V3M_Render_{name}", "AREA")
        data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        ob = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(ob)
        ob.location = location
        aim(ob, target)
    camera_data = bpy.data.cameras.new("V3M_Render_Camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.lens = 85
    scene.camera = camera
    floor_mat = bpy.data.materials.new("V3M_Render_Floor_Material")
    floor_mat.use_nodes = True
    floor_bsdf = floor_mat.node_tree.nodes["Principled BSDF"]
    floor_bsdf.inputs["Base Color"].default_value = (0.018, 0.022, 0.035, 1.0)
    floor_bsdf.inputs["Roughness"].default_value = 0.52
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "V3M_Render_Floor"
    floor.data.materials.append(floor_mat)
    return camera


def configure(scene, width, height, samples):
    devices = enable_optix(scene)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = 30
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 3
    scene.view_settings.look = "AgX - Medium High Contrast"
    return devices


def set_camera(camera, location, target, scale):
    camera.location = Vector(location)
    aim(camera, target)
    camera.data.ortho_scale = scale


def render(scene, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    assert path.exists() and path.stat().st_size > 0
    print("V3M_RENDER", str(path.relative_to(ROOT)), path.stat().st_size, flush=True)


def bounds(objects):
    points = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        evaluated = ob.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    array = np.asarray(points, dtype=np.float32)
    return array.min(axis=0), array.max(axis=0)


def action_by_name(rig, requested=None):
    if requested:
        action = bpy.data.actions.get(requested)
        assert action is not None, (requested, [item.name for item in bpy.data.actions])
        return action
    for name in ("Combat_Stance", "Godwyn_V3_idle_guard"):
        if bpy.data.actions.get(name):
            return bpy.data.actions[name]
    assert rig.animation_data and rig.animation_data.action
    return rig.animation_data.action


def before(scene, camera, rig):
    action = action_by_name(rig)
    assign_action(rig, action, int(round(action.frame_range[0])))
    devices = configure(scene, 1200, 1800, 64)
    set_camera(camera, (4.6, -5.7, 2.25), (0.03, -0.06, 1.67), 3.75)
    render(scene, OUT / "before_three_quarter.png")
    set_camera(camera, (2.0, -4.0, 2.82), (0.03, -0.14, 2.73), 0.82)
    render(scene, OUT / "before_collar_closeup.png")
    return {"mode": "before", "action": action.name, "samples": 64, "devices": devices}


def heroes(scene, camera, rig, assets, samples):
    action = action_by_name(rig, "Combat_Stance")
    assign_action(rig, action, int(round(action.frame_range[0])))
    devices = configure(scene, 1200, 1800, samples)
    low, high = bounds(assets)
    center = (low + high) * 0.5
    target = Vector((center[0], center[1], (low[2] + high[2]) * 0.5))
    scale = max(3.55, float(high[2] - low[2]) * 1.10)
    views = {
        "hero_combat_stance_front.png": ((target.x, target.y - 7.0, target.z), target, scale),
        "hero_combat_stance_side.png": ((target.x + 7.0, target.y, target.z), target, scale),
        "hero_combat_stance_three_quarter.png": ((target.x + 4.7, target.y - 6.0, target.z), target, scale),
        "hero_comparison_model.png": ((target.x, target.y - 7.0, target.z), target, scale),
    }
    for filename, (location, view_target, view_scale) in views.items():
        set_camera(camera, location, view_target, view_scale)
        render(scene, OUT / filename)
    set_camera(camera, (2.0, -4.0, 2.78), (0.03, -0.14, 2.71), 0.78)
    render(scene, OUT / "hero_collar_closeup.png")
    head_low, head_high = bounds([bpy.data.objects["AstraChar2_Meshy_HeadHair"]])
    head_center = (head_low + head_high) * 0.5
    face_target = Vector((head_center[0], head_center[1], head_center[2] + 0.015))
    set_camera(camera, (face_target.x, face_target.y - 4.0, face_target.z), face_target,
               max(0.62, float(head_high[2] - head_low[2]) * 1.18))
    render(scene, OUT / "hero_face_closeup.png")
    return {"mode": "heroes", "action": action.name, "frame": 1, "samples": samples, "devices": devices}


def film(scene, camera, rig, assets, clip, samples, step):
    action = action_by_name(rig, clip)
    start, end = [int(round(value)) for value in action.frame_range]
    assign_action(rig, action, start)
    devices = configure(scene, 768, 768, samples)
    low, high = bounds(assets)
    target = Vector(((low[0] + high[0]) * 0.5, (low[1] + high[1]) * 0.5, 1.60))
    camera_location = Vector((target.x + 4.8, target.y - 6.4, 2.25))
    set_camera(camera, camera_location, target, 4.15)
    hips_start = rig.matrix_world @ rig.pose.bones["Hips"].head
    folder = OUT / f"{clip}_frames"
    folder.mkdir(parents=True, exist_ok=True)
    source_frames = list(range(start, end + 1, step))
    if source_frames[-1] != end:
        source_frames.append(end)
    for output_index, frame in enumerate(source_frames, 1):
        assign_action(rig, action, frame)
        hips = rig.matrix_world @ rig.pose.bones["Hips"].head
        follow = Vector((hips.x - hips_start.x, hips.y - hips_start.y, 0.0))
        set_camera(camera, camera_location + follow, target + follow, 4.15)
        frame_path = folder / f"{output_index:04d}.png"
        if frame_path.exists() and frame_path.stat().st_size > 0:
            print("V3M_FILM_RESUME_SKIP", clip, output_index, frame_path.stat().st_size, flush=True)
        else:
            render(scene, frame_path)
        if output_index == 1 or output_index == len(source_frames) or output_index % 10 == 0:
            print("V3M_FILM_PROGRESS", clip, output_index, len(source_frames), "source_frame", frame, flush=True)
    return {
        "mode": "film", "clip": clip, "source_frames": end - start + 1,
        "rendered_frames": len(source_frames), "source_fps": 30, "render_step": step,
        "encoded_input_fps": 30.0 / step, "output_fps": 30,
        "resolution": [768, 768], "samples": samples, "devices": devices,
        "camera": "three-quarter XY root-follow; vertical root motion remains visible",
    }


def main():
    args = cli()
    bpy.ops.wm.open_mainfile(filepath=str(root_path(args.blend)), load_ui=False)
    scene = bpy.context.scene
    scene.render.fps = 30
    rig = bpy.data.objects["Astra_V3_Rig"]
    names = ["char1", "AstraChar2_Meshy_HeadHair", "AstraChar2_Meshy_NeckBlend", "Astra_V3_Collar_Occluder", "Godwyn_Sword"]
    assets = [bpy.data.objects[name] for name in names if bpy.data.objects.get(name)]
    camera = studio(scene)
    if args.mode == "before":
        report = before(scene, camera, rig)
    elif args.mode == "heroes":
        report = heroes(scene, camera, rig, assets, args.samples or 128)
    else:
        assert args.clip
        report = film(scene, camera, rig, assets, args.clip, args.samples or 12, args.step)
    path = OUT / f"render_{args.mode}{'_' + args.clip if args.clip else ''}.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_RENDER_COMPLETE", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
