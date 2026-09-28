import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_preround4.blend'));target={b.name:b.matrix_local.copy() for b in bpy.data.objects['Armature'].data.bones}
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2.blend'));arm=bpy.data.objects['Armature'];lengths={b.name:b.length for b in arm.data.bones};bpy.context.view_layer.objects.active=arm;arm.hide_set(False);arm.select_set(True);history=[]
for iteration in range(12):
 actual={b.name:b.matrix_local.copy() for b in arm.data.bones};bpy.ops.object.mode_set(mode='EDIT')
 for b in arm.data.edit_bones:
  if iteration==0:b.matrix=target[b.name];b.length=lengths[b.name]
  else:
   delta=target[b.name].translation-actual[b.name].translation;b.head+=delta;b.tail+=delta
 bpy.ops.object.mode_set(mode='OBJECT');errors={b.name:float(np.abs(np.array(b.matrix_local)-np.array(target[b.name])).max()) for b in arm.data.bones};worst=max(errors,key=errors.get);history.append({'iteration':iteration,'error':errors[worst],'bone':worst});print(history[-1],flush=True)
 if errors[worst]<1e-6:break
(O/'r4_rest_compatibility.json').write_text(json.dumps({'history':history,'errors':errors},indent=2))
if errors[worst]<1e-6:
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2.blend'));print('CANONICAL COMPATIBILITY FIX SAVED',flush=True)
else:print('NO SAVE: tolerance not reached',flush=True)
