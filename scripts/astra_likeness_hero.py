"""Exercise the actual hero assembly loader against the final likeness candidate."""
import bpy
import sys
import json
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
sys.path.insert(0, str(ROOT / 'scripts'))

import astra_cine_hero_render as hero


def reset(arm):
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def main(source):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'models/astra_character_v2_collar_banked.blend'))
    arm = bpy.data.objects['Armature']
    reset(arm)
    for ob in list(bpy.data.objects):
        if ob != arm:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    bone = arm.pose.bones['Head']
    bone.rotation_mode = 'XYZ'
    bone.rotation_euler = (0, 0, 0)
    bone.keyframe_insert('rotation_euler', frame=1)
    bone.rotation_euler.z = .10
    bone.keyframe_insert('rotation_euler', frame=2)
    bpy.context.scene.frame_set(1)
    fixture = Path('/tmp/astra_likeness_hero_fixture.blend')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(fixture))
    scene, result = hero.assemble_inputs(fixture, ROOT / source)
    result['test_fixture'] = 'Synthetic two-key Head rotation on the approved banked 121-bone rig.'
    result['head_present'] = 'AstraChar2_Mpfb_Head' in scene.objects
    result['bones'] = len(scene.objects['Armature'].data.bones)
    rig = scene.objects['Armature']
    result['armature_modifier_targets_valid'] = all(m.object == rig for ob in scene.objects for m in ob.modifiers if m.type == 'ARMATURE')
    result['native_curve_controls_valid'] = all(
        node.inputs['Object'].default_value.name in scene.objects
        for ob in scene.objects if ob.type == 'CURVES'
        for mod in ob.modifiers if mod.type == 'NODES'
        for node in mod.node_group.nodes
        if node.bl_idname == 'GeometryNodeObjectInfo' and node.inputs['Object'].default_value
    )
    assert result['armature_modifier_targets_valid'] and result['native_curve_controls_valid']
    assert result['head_present'] and result['bones'] == 121 and result['rest_transform_max_error'] == 0
    (OUT / 'likeness_final_hero_assembly.json').write_text(json.dumps(result, indent=2) + '\n')
    print('LIKENESS_HERO_PASS', flush=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    main(args[0])
