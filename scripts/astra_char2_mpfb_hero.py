"""Run the actual hero loader against a scratch animation on the banked compatible rig.
No excluded moveset/animation files are read or executed.
"""
import bpy,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose

def check(source,label):
    import astra_cine_hero_render as hero
    bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_collar_banked.blend'));reset_pose();arm=bpy.data.objects['Armature']
    for ob in list(bpy.data.objects):
        if ob!=arm:bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)
    bone=arm.pose.bones['Head'];bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.keyframe_insert('rotation_euler',frame=1)
    bone.rotation_euler.z=.10;bone.keyframe_insert('rotation_euler',frame=2)
    bpy.context.scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0
    fixture=Path('/tmp/astra_char2_mpfb_hero_fixture.blend');bpy.ops.wm.save_as_mainfile(filepath=str(fixture))
    scene,result=hero.assemble_inputs(fixture,source)
    result['test_fixture']='Synthetic two-key Head rotation on the approved banked 121-bone rig; excluded animation inputs untouched.'
    result['head_present']='AstraChar2_Mpfb_Head' in scene.objects
    result['bones']=len(scene.objects['Armature'].data.bones)
    rig=scene.objects['Armature'];result['armature_modifier_targets_valid']=all(m.object==rig for o in scene.objects for m in o.modifiers if m.type=='ARMATURE')
    assert result['armature_modifier_targets_valid']
    result['native_curve_controls_valid']=all(node.inputs['Object'].default_value.name in scene.objects for o in scene.objects if o.type=='CURVES' for mod in o.modifiers if mod.type=='NODES' for node in mod.node_group.nodes if node.bl_idname=='GeometryNodeObjectInfo' and node.inputs['Object'].default_value)
    assert result['native_curve_controls_valid']
    assert result['head_present'] and result['bones']==121 and result['rest_transform_max_error']==0
    (O/f'{label}_hero_assembly.json').write_text(json.dumps(result,indent=2));print('MPFB_HERO_PASS',label,flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:];check(R/args[0],args[1])
