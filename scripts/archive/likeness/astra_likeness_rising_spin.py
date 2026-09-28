"""Render Rising Spin F40 with the published likeness and remeasure blade clearances."""
import bpy
import json
import sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
sys.path.insert(0, str(ROOT / 'scripts'))
import astra_cine_hero_render as hero


def evaluated_mesh(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    matrix = np.array(ev.matrix_world)
    co = co @ matrix[:3, :3].T + matrix[:3, 3]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return co, faces


def evaluated_vertices(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    co = np.empty(len(ev.data.vertices) * 3, np.float32)
    ev.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    matrix = np.array(ev.matrix_world)
    return co @ matrix[:3, :3].T + matrix[:3, 3]


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
            enabled.append((device.name, device.type))
    assert enabled and all(kind == 'OPTIX' for _, kind in enabled)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    return enabled


def original_name(name):
    stem, dot, suffix = name.rpartition('.')
    return stem if dot and len(suffix) == 3 and suffix.isdigit() else name


def main():
    animation = ROOT / 'models/astra_move_rising_spin_v2_wip.blend'
    character = ROOT / 'models/astra_character_v2.blend'
    bpy.ops.wm.open_mainfile(filepath=str(character))
    character_scene = bpy.context.scene
    character_objects = [o for o in character_scene.objects if o.type not in {'LIGHT', 'CAMERA'} and o.name != 'Astra evaluation ground']
    rig = bpy.data.objects['Armature']
    with bpy.data.libraries.load(str(animation), link=False) as (src, dst):
        assert len(src.scenes) == 1
        dst.scenes = src.scenes[:]
    scene = dst.scenes[0]
    bpy.context.window.scene = scene
    appended = set(scene.objects)
    old_rig = next(o for o in appended if o.type == 'ARMATURE')
    old_body = next(o for o in appended if original_name(o.name) == 'char1')
    old_sword = next(o for o in appended if original_name(o.name) == 'Godwyn_Sword')
    old_under = next((o for o in appended if original_name(o.name) == 'Astra_Undersleeves'), None)
    source_action = old_rig.animation_data.action
    for ob in character_objects:
        scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    assert len(old_rig.data.bones) == len(rig.data.bones) == 121
    rest_error = max(abs(old_rig.data.bones[n].matrix_local[i][j] - rig.data.bones[n].matrix_local[i][j])
                     for n in old_rig.pose.bones.keys() for i in range(4) for j in range(4))
    assert rest_error == 0
    for bone in old_rig.pose.bones:
        target_bone = rig.pose.bones[bone.name]
        target_bone.rotation_mode = bone.rotation_mode
        target_bone.scale = bone.scale
    rig.animation_data_clear()
    rig.animation_data_create()
    transferred = source_action.copy()
    transferred.name = source_action.name + '_LikenessProof'
    rig.animation_data.action = transferred
    if transferred.slots:
        rig.animation_data.action_slot = transferred.slots[0]
    for ob in (old_rig, old_body, old_sword, old_under):
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.scenes.remove(character_scene)
    scene.frame_set(40)
    bpy.context.view_layer.update()
    head = scene.objects['AstraChar2_Mpfb_Head']
    sword = scene.objects['Godwyn_Sword']
    assert len(rig.data.bones) == 121 and rig.animation_data and rig.animation_data.action

    head_co, head_faces = evaluated_mesh(head)
    head_bvh = BVHTree.FromPolygons([tuple(p) for p in head_co], head_faces, all_triangles=False)
    source = np.array([p.vector[:] for p in sword.data.attributes['astra_sword_source'].data])
    sword_co, sword_faces = evaluated_mesh(sword)
    blade_ids = set(int(i) for i in np.where(source[:, 2] < 150)[0])
    blade_faces = [face for face in sword_faces if all(i in blade_ids for i in face)]
    blade_bvh = BVHTree.FromPolygons([tuple(p) for p in sword_co], blade_faces, all_triangles=False)
    overlaps = head_bvh.overlap(blade_bvh)
    head_distance = min(
        min((head_bvh.find_nearest(Vector(sword_co[i]))[3] for i in sorted(blade_ids)[::3]), default=float('inf')),
        min((blade_bvh.find_nearest(Vector(p))[3] for p in head_co[::12]), default=float('inf')),
    )
    if overlaps:
        head_distance = 0.0
    hair_samples = []
    for ob in sorted((o for o in scene.objects if o.name.startswith('AstraChar2_R5_Control_MPFB_')), key=lambda o: o.name):
        co = evaluated_vertices(ob)
        stride = max(1, len(co) // 2500)
        hair_samples.extend(co[::stride])
    hair_distance = min((blade_bvh.find_nearest(Vector(p))[3] for p in hair_samples), default=float('inf')) - .002
    assert not overlaps and head_distance > 0 and hair_distance > 0

    for ob in list(scene.objects):
        if ob.type in {'CAMERA', 'LIGHT'}:
            bpy.data.objects.remove(ob, do_unlink=True)
    devices = optix(scene)
    target = head_co.mean(axis=0)
    cam_data = bpy.data.cameras.new('Likeness Rising Spin proof camera')
    cam = bpy.data.objects.new(cam_data.name, cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 1.42
    cam.location = Vector(target) + Vector((3.15, -5.6, 1.20))
    aim(cam, target + np.array((0, 0, -.10)))
    for name, offset, energy, size, color in [
        ('key', (-3.0, -4.0, 3.0), 900, 2.5, (1.0, .94, .84)),
        ('fill', (3.0, -2.5, 1.5), 190, 3.0, (.78, .86, 1.0)),
        ('rim', (1.0, 2.0, 3.5), 850, 2.0, (1.0, .84, .62)),
    ]:
        data = bpy.data.lights.new('Likeness Rising Spin ' + name, 'AREA')
        data.energy = energy
        data.size = size
        data.color = color
        ob = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(ob)
        ob.location = Vector(target) + Vector(offset)
        aim(ob, target)
    world = bpy.data.worlds.new('Likeness Rising Spin world')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.035, .035, .035, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .22
    scene.world = world
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(OUT / 'likeness_rising_spin_f040.png')
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    bpy.ops.render.render(write_still=True)
    report = {
        'animation': str(animation.relative_to(ROOT)),
        'published_character': str(character.relative_to(ROOT)),
        'frame': 40,
        'reason': 'Existing exact blade-to-head minimum frame from the rehost audit.',
        'blade_head_exact_triangle_overlaps': len(overlaps),
        'blade_head_exact_sampled_surface_distance_m': float(head_distance),
        'blade_hair_exact_sampled_surface_clearance_m': float(hair_distance),
        'hair_fiber_radius_assumption_m': .002,
        'hair_control_points_sampled': len(hair_samples),
        'assembly_rest_transform_max_error': rest_error,
        'bones': len(rig.data.bones),
        'optix_devices': devices,
        'image': 'renders/astra/char2/likeness_rising_spin_f040.png',
    }
    (OUT / 'likeness_rising_spin_clearance.json').write_text(json.dumps(report, indent=2) + '\n')
    print('LIKENESS_RISING_SPIN_PASS', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
