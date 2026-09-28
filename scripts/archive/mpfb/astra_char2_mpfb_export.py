"""Export only the rest character and portable skinned fibers; retain all rig joints."""
import bpy,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_mpfb_validate import reset

def main(source,out):
 bpy.ops.wm.open_mainfile(filepath=str(R/source));arm=bpy.data.objects['Armature'];reset(arm);assert len(arm.data.bones)==121 and len(bpy.data.actions)==0
 bpy.ops.object.select_all(action='DESELECT');selected=[]
 for ob in bpy.context.scene.objects:
  asset=ob.name.startswith('AstraChar2_') or ob.name in {'char1','Astra_Undersleeves','Godwyn_Sword'}
  include=ob==arm or (asset and ob.type=='MESH' and len(ob.data.polygons)>0 and not ob.hide_render)
  if ob.name.startswith('AstraChar2_R5_Strands_MPFB_'):include=True
  if ob.name.startswith(('AstraChar2_R5_Control_','AstraChar2_R4_Control_')):include=False
  if include:ob.hide_set(False);ob.hide_render=False;ob.hide_viewport=False;ob.select_set(True);selected.append(ob.name)
 bpy.context.view_layer.objects.active=arm
 options=dict(filepath=str(R/out),export_format='GLB',use_selection=True,export_animations=False,export_skins=True,export_def_bones=False,export_leaf_bone=False,export_apply=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_all_influences=False,export_cameras=False,export_lights=False)
 valid=bpy.ops.export_scene.gltf.get_rna_type().properties.keys();options={k:v for k,v in options.items() if k in valid}
 bpy.ops.export_scene.gltf(**options)
 (O/'mpfb_export.json').write_text(json.dumps({'source':source,'output':out,'selected_objects':selected,'options':options,'actions':len(bpy.data.actions)},indent=2))
 print('MPFB_EXPORT_DONE',flush=True)
if __name__=='__main__':
 a=sys.argv[sys.argv.index('--')+1:];main(a[0],a[1])
