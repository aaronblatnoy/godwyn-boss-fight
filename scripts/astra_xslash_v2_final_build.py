"""Fresh character-v2 + unchanged approved v2 motion + in-memory blue override.

Never save the character source. Only save models/astra_xslash_v2_final_wip.blend.
The metallic-mask bypass follows astra_character_round2_blue_option.py exactly.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from astra_xslash_v2_on_char_build import action_digest, sword_landmarks, sword_points

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'models/astra_character_v2.blend'
MOTION = ROOT / 'models/astra_xslash_v2_wip.blend'
TARGET = ROOT / 'models/astra_xslash_v2_final_wip.blend'
OUT = ROOT / 'renders/astra/v2_final_on_char'
TINT_MATERIALS = {
    'Astra Round2 royal blue and continuous gold trim',
    'Astra Round2 royal blue undersleeves',
}


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def material_digest(material):
    """Fingerprint the existing shader topology/defaults, without mutating it."""
    nt = material.node_tree
    nodes = []
    for node in nt.nodes if nt else []:
        inputs = []
        for socket in node.inputs:
            if not hasattr(socket, 'default_value'):
                continue
            value = socket.default_value
            if hasattr(value, '__len__') and not isinstance(value, str):
                value = list(value)
            elif not isinstance(value, (str, int, float, bool)):
                value = repr(value)
            inputs.append((socket.identifier, value))
        settings = {key: getattr(node, key) for key in
                    ['blend_type', 'operation', 'use_clamp'] if hasattr(node, key)}
        nodes.append((node.name, node.bl_idname, inputs, settings))
    links = [(x.from_node.name, x.from_socket.identifier,
              x.to_node.name, x.to_socket.identifier) for x in nt.links] if nt else []
    data = [list(material.diffuse_color), material.metallic, material.roughness, nodes, links]
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def apply_blue(tint, materials):
    applied = []
    for material in materials:
        if material.name not in TINT_MATERIALS:
            continue
        nt = material.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        color = bsdf.inputs['Base Color'].links[0].from_socket
        metallic = bsdf.inputs['Metallic'].links[0].from_socket
        scale = nt.nodes.new('ShaderNodeMixRGB')
        scale.name = 'Astra XSlash Final Deep Blue Multiply'
        scale.label = 'Render override: deep blue cloth'
        scale.blend_type = 'MULTIPLY'
        scale.inputs[0].default_value = 1.0
        scale.inputs[2].default_value = (*tint, 1.0)
        scale.location = (bsdf.location.x - 440, bsdf.location.y + 160)
        nt.links.new(color, scale.inputs[1])
        bypass = nt.nodes.new('ShaderNodeMixRGB')
        bypass.name = 'Astra XSlash Final Preserve Gold'
        bypass.label = 'Existing metallic mask preserves original gold'
        bypass.location = (bsdf.location.x - 220, bsdf.location.y + 160)
        nt.links.new(metallic, bypass.inputs[0])
        nt.links.new(scale.outputs[0], bypass.inputs[1])
        nt.links.new(color, bypass.inputs[2])
        nt.links.new(bypass.outputs[0], bsdf.inputs['Base Color'])
        assert bsdf.inputs['Metallic'].links[0].from_socket == metallic
        applied.append({'material': material.name, 'multiply_linear': list(tint),
                        'original_color': [color.node.name, color.name],
                        'unchanged_metallic_mask': [metallic.node.name, metallic.name]})
    assert {x['material'] for x in applied} == TINT_MATERIALS
    return applied


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tint', nargs=3, type=float, default=(0.025, 0.20, 0.62))
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True, exist_ok=True)
    source_hash, motion_hash = file_hash(SOURCE), file_hash(MOTION)
    # Always open the current protected character file fresh, read-only on disk.
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    character_scene = bpy.context.scene
    names = ['Armature', 'char1', 'Godwyn_Sword', 'Astra_Undersleeves']
    character = {name: bpy.data.objects[name] for name in names}
    materials = set(m for o in character.values() if o.type == 'MESH'
                    for m in o.data.materials if m)
    before_materials = {m.name: material_digest(m) for m in materials}

    # Append the complete approved staging scene so lights, world, view transform,
    # native motion blur, camera, ribbons and their keyed visibility stay intact.
    with bpy.data.libraries.load(str(MOTION), link=False) as (src, dst):
        assert len(src.scenes) == 1
        dst.scenes = src.scenes[:]
    scene = dst.scenes[0]
    bpy.context.window.scene = scene
    old = next(o for o in scene.objects if o.type == 'ARMATURE')
    old_body = next(o for o in scene.objects if o.name.startswith('char1'))
    old_sword = next(o for o in scene.objects if o.name.startswith('Godwyn_Sword'))
    source_action = old.animation_data.action
    digest = action_digest(source_action)
    for obj in character.values():
        scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    rig, sw = character['Armature'], character['Godwyn_Sword']
    assert set(old.pose.bones.keys()) == set(rig.pose.bones.keys())
    rest_error = max(abs(old.data.bones[n].matrix_local[i][j] - rig.data.bones[n].matrix_local[i][j])
                     for n in old.pose.bones.keys() for i in range(4) for j in range(4))
    assert rest_error == 0
    assert old.matrix_world == rig.matrix_world
    for bone in old.data.bones:
        other = rig.data.bones[bone.name]
        assert (bone.parent.name if bone.parent else None) == (other.parent.name if other.parent else None)
    for obj in character.values():
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    assert mod.object == rig
    assert sw.parent == rig and sw.parent_type == 'OBJECT'
    assert list(sw.vertex_groups.keys()) == ['RightHand']
    assert all(len(v.groups) == 1 and abs(v.groups[0].weight - 1) < 1e-7 for v in sw.data.vertices)
    for bone in old.pose.bones:
        other = rig.pose.bones[bone.name]
        assert not other.constraints
        other.rotation_mode = bone.rotation_mode
        other.scale = bone.scale
    rig.animation_data_clear()
    rig.animation_data_create()
    rig.animation_data.action = source_action.copy()
    rig.animation_data.action.name = 'Astra_Godwyn_XSlash_V2_Final'
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
    assert action_digest(rig.animation_data.action) == digest

    mesh_states = [(o, o.hide_viewport) for o in scene.objects if o.type == 'MESH']
    for obj, _ in mesh_states:
        obj.hide_viewport = True
    max_error = 0.0
    secondary = {p.name: 0.0 for p in rig.pose.bones if p.name.startswith('phys_')}
    for q in range(4, 361):
        frame = q / 4
        scene.frame_set(int(frame), subframe=frame % 1)
        bpy.context.view_layer.update()
        for bone in old.pose.bones:
            other = rig.pose.bones[bone.name]
            max_error = max(max_error, max(abs(bone.matrix[i][j] - other.matrix[i][j])
                                          for i in range(4) for j in range(4)))
            if bone.name in secondary:
                secondary[bone.name] = max(secondary[bone.name], math.degrees(other.rotation_quaternion.angle))
    assert max_error < 1e-6, max_error
    for obj, hidden in mesh_states:
        obj.hide_viewport = hidden
    for obj in [old_sword, old_body, old]:
        bpy.data.objects.remove(obj, do_unlink=True)
    # Drop only the unused source staging scene/objects in memory.
    bpy.data.scenes.remove(character_scene)
    retained = set(scene.objects)
    for obj in list(bpy.data.objects):
        if obj not in retained:
            bpy.data.objects.remove(obj, do_unlink=True)
    scene.name = 'Astra XSlash V2 Final'

    tip, grip, tip_index = sword_landmarks(sw)
    ribbon_count = 0
    for obj in scene.objects:
        if not obj.name.startswith('Astra_v2_blur_'):
            continue
        frame = int(obj.name.rsplit('_', 1)[1])
        ribbon_count += 1
        for j in range(13):
            t = frame - .70 + .70 * j / 12
            scene.frame_set(int(t), subframe=t % 1)
            bpy.context.view_layer.update()
            point, handle = sword_points(rig, sw, tip, grip)
            for k, radial in enumerate([.30, .88, 1.0]):
                obj.data.vertices[j * 3 + k].co = handle.lerp(point, radial)
        obj.data.update()
    assert ribbon_count == 14
    sword_error = 0.0
    for frame in [1, 30, 40, 41, 57, 60, 90]:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        point, _ = sword_points(rig, sw, tip, grip)
        evaluated = sw.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        sword_error = max(sword_error, (evaluated.matrix_world @ mesh.vertices[tip_index].co - point).length)
        evaluated.to_mesh_clear()
    assert sword_error < 1e-5, sword_error
    applied = apply_blue(args.tint, materials)
    after_materials = {m.name: material_digest(m) for m in materials}
    untouched = {name: before_materials[name] == after_materials[name]
                 for name in before_materials if name not in TINT_MATERIALS}
    assert all(untouched.values())
    scene.frame_set(1)
    scene.render.engine = 'BLENDER_EEVEE'
    assert scene.frame_start == 1 and scene.frame_end == 90 and scene.render.fps == 30
    scene['astra_final_robe_multiply_linear'] = list(args.tint)
    scene['astra_character_source_sha256'] = source_hash
    scene['astra_motion_source_sha256'] = motion_hash
    assert TARGET != SOURCE and TARGET.name.startswith('astra_xslash_')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
    assert file_hash(SOURCE) == source_hash and file_hash(MOTION) == motion_hash
    report = {
        'character_source': str(SOURCE.relative_to(ROOT)), 'character_source_sha256': source_hash,
        'motion_source': str(MOTION.relative_to(ROOT)), 'motion_source_sha256': motion_hash,
        'derived_file': str(TARGET.relative_to(ROOT)), 'source_files_unchanged': True,
        'action_data_identical': True, 'action_digest': digest,
        'bone_count': len(rig.pose.bones), 'rest_matrix_max_error': rest_error,
        'all_bones_357_subframes_max_matrix_error': max_error,
        'secondary_bones': len(secondary), 'secondary_peak_degrees': secondary,
        'retargeting': False, 'character_mesh_weight_texture_edits': False,
        'blue_override': applied, 'other_character_materials_unchanged': untouched,
        'native_sword_attachment': 'ARMATURE modifier; RightHand weight 1.0; unchanged',
        'sword_evaluator_max_error_m': sword_error, 'ribbons_resampled': ribbon_count,
        'engine': scene.render.engine, 'blender_version': bpy.app.version_string,
        'exposure': scene.view_settings.exposure, 'shutter': scene.render.motion_blur_shutter,
        'image_packing': [{'name': im.name, 'packed': bool(im.packed_file)}
                          for im in bpy.data.images if im.users],
    }
    (OUT / 'transfer_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('ASTRA FINAL BUILD COMPLETE', json.dumps({k: v for k, v in report.items()
          if k not in ['secondary_peak_degrees', 'image_packing']}), flush=True)


if __name__ == '__main__':
    main()
