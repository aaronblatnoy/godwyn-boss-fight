"""Cycles OptiX portraits for the Meshy graft candidate."""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2"
CANDIDATE = ROOT / "models/astra_character_v2_meshy_i01.blend"


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


def optix(scene):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    enabled = []
    for device in prefs.devices:
        device.use = device.type == "OPTIX"
        if device.use:
            enabled.append({"name": device.name, "type": device.type})
    assert enabled and all(d["type"] == "OPTIX" for d in enabled)
    scene.cycles.device = "GPU"
    return enabled


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = next((a.split("=", 1)[1] for a in args if a.startswith("only=")), None)
    hide = next((a.split("=", 1)[1] for a in args if a.startswith("hide=")), None)
    isolate = next((a.split("=", 1)[1] for a in args if a.startswith("isolate=")), None)
    debug = "debug" in args
    global CANDIDATE
    cand = next((a.split("=", 1)[1] for a in args if a.startswith("candidate=")), None)
    if cand:
        CANDIDATE = ROOT / cand
    prefix_arg = next((a.split("=", 1)[1] for a in args if a.startswith("prefix=")), None)
    bpy.ops.wm.open_mainfile(filepath=str(CANDIDATE))
    if hide and hide in bpy.data.objects:
        bpy.data.objects[hide].hide_render = True
    if isolate:
        for ob in bpy.data.objects:
            if ob.type == "MESH" and ob.name != isolate:
                ob.hide_render = True
    if not debug and not hide and not isolate:
        keep = ("AstraChar2_Meshy_", "AstraChar2_R5_ClavicleMantle",
                "AstraChar2_R5_Cuirass", "AstraChar2_R5_Gorget",
                "AstraChar2_R5_GorgetRim", "AstraChar2_R5_Pauldron")
        for ob in list(bpy.data.objects):
            if ob.type == "MESH" and not ob.name.startswith(keep):
                bpy.data.objects.remove(ob, do_unlink=True)
    arm = bpy.data.objects["Armature"]
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    scene = bpy.context.scene
    for ob in list(scene.objects):
        if ob.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(ob, do_unlink=True)
    scene.render.engine = "BLENDER_WORKBENCH" if debug else "CYCLES"
    devices = [] if debug else optix(scene)
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 7
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("Meshy warm neutral studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.055, .052, .048, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .28
    scene.world = world
    for name, loc, power, size, color in [
        ("key", (-3, -4.5, 5), 650, 2.25, (1.0, .96, .90)),
        ("fill", (3, -3.2, 4), 135, 3.0, (.80, .86, 1.0)),
        ("rim", (1.2, 2.0, 4.5), 700, 2.0, (1.0, .90, .76)),
    ]:
        data = bpy.data.lights.new("Meshy " + name, "AREA")
        data.energy, data.size, data.color = power, size, color
        light = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(light)
        light.location = loc
        aim(light, (0, -.20, 2.88))
    camera_data = bpy.data.cameras.new("Meshy portrait camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.lens = 85
    views = {
        "front": ((0, -6, 2.885), (0, -.20, 2.885), .67),
        "side": ((6, -.27, 2.885), (0, -.27, 2.885), .67),
        "three_quarter": ((3.65, -6, 2.885), (0, -.20, 2.885), .67),
        "collar": ((1.8, -5.2, 2.72), (0, -.20, 2.72), .55),
    }
    for name, (location, target, scale) in views.items():
        if only and name != only:
            continue
        camera.location = location
        aim(camera, target)
        camera.data.ortho_scale = scale
        scene.render.resolution_x = 850
        scene.render.resolution_y = 1266
        prefix = prefix_arg or ("meshy_debug" if debug else "meshy_graft")
        scene.render.filepath = str(OUT / f"{prefix}_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("MESHY_RENDER_PASS", name, flush=True)
    (OUT / "meshy_render.json").write_text(json.dumps({"candidate": str(CANDIDATE.relative_to(ROOT)),
        "engine": "Cycles", "device": "OptiX", "samples": 64, "devices": devices,
        "views": list(views)}, indent=2) + "\n")


if __name__ == "__main__":
    main()
