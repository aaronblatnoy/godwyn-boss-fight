"""Cycles OptiX portrait gate for a Godwyn likeness iteration."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def optix(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    enabled = []
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
        if device.use:
            enabled.append({'name': device.name, 'type': device.type})
    assert enabled, 'Cycles OptiX/CUDA GPU device was not found; CPU rendering is forbidden'
    assert all(d['type'] != 'CPU' for d in enabled)
    scene.cycles.device = 'GPU'
    print('LIKENESS_GPU_ASSERT', enabled, flush=True)
    return enabled


def studio():
    scene = bpy.context.scene
    for ob in list(scene.objects):
        if ob.type in {'CAMERA', 'LIGHT'}:
            bpy.data.objects.remove(ob, do_unlink=True)
    scene.render.engine = 'CYCLES'
    devices = optix(scene)
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 7
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 4
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    world = bpy.data.worlds.new('Likeness warm neutral studio')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.055, .052, .048, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .28
    scene.world = world
    lights = [
        ('key', (-3, -4.5, 5), 560, 2.25, (1.0, .96, .90)),
        ('fill', (3, -3.2, 4), 105, 3.0, (.80, .86, 1.0)),
        ('rim', (1.2, 2.0, 4.5), 640, 2.0, (1.0, .90, .76)),
    ]
    for name, loc, energy, size, color in lights:
        data = bpy.data.lights.new('Likeness ' + name, 'AREA')
        data.energy = energy
        data.size = size
        data.color = color
        ob = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(ob)
        ob.location = loc
        aim(ob, (0, -.2, 2.88))
    cam_data = bpy.data.cameras.new('Likeness portrait camera')
    cam = bpy.data.objects.new('Likeness portrait camera', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.lens = 85
    scene.view_layers[0].material_override = None
    return scene, devices


def main(iteration):
    source = ROOT / f'models/astra_character_v2_likeness_i{iteration:02}.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    arm = bpy.data.objects['Armature']
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    scene, devices = studio()
    views = {
        'front': ((0, -6, 2.885), (0, -.20, 2.885), .67),
        'side': ((6, -.27, 2.885), (0, -.27, 2.885), .67),
        'three_quarter': ((3.65, -6, 2.885), (0, -.20, 2.885), .67),
    }
    for name, (location, target, scale) in views.items():
        scene.camera.location = location
        aim(scene.camera, target)
        scene.camera.data.ortho_scale = scale
        scene.render.resolution_x = 850
        scene.render.resolution_y = 1266
        scene.render.filepath = str(OUT / f'likeness_i{iteration:02}_{name}.png')
        bpy.ops.render.render(write_still=True)
        print('LIKENESS_RENDER_PASS', iteration, name, flush=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    main(int(args[0]))
