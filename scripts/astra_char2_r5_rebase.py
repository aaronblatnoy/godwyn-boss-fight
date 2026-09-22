"""Carry the unchanged new groom onto the latest structural clay candidate."""
import bpy,sys,json,shutil
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r5_clay.blend'));arm=bpy.data.objects['Armature'];existing=set(bpy.data.objects)
temp=Path('/tmp/astra_char2_r5_groom_input.blend');shutil.copy2(R/'models/astra_character_r5_groom_clay.blend',temp)
with bpy.data.libraries.load(str(temp),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(('AstraChar2_R5_Curves_','AstraChar2_R5_Control_','AstraChar2_R5_Strands_'))]
for ob in dst.objects:
 bpy.context.scene.collection.objects.link(ob);ob.parent=arm;ob.matrix_parent_inverse=arm.matrix_world.inverted()
 for m in ob.modifiers:
  if m.type=='ARMATURE':m.object=arm
 if ob.type=='CURVES':ob['groom_points_per_strand']=len(ob.data.points)//int(ob['groom_strands'])
for ob in list(bpy.data.objects):
 if ob not in existing and ob not in dst.objects:bpy.data.objects.remove(ob,do_unlink=True)
reset_pose();assert len(arm.data.bones)==121 and len(bpy.data.actions)==0;bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_r5_groom_clay.blend'))
print('GROOM REBASE COMPLETE',flush=True)
