import bpy,sys,json,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_preround4.blend'));o=bpy.data.objects['char1'];m=o.data
for slot in [0,3]:
 for low in [1.8,2.0,2.2,2.4,2.6,2.8,3.0]:
  pp=np.array([o.matrix_world@f.center for f in m.polygons if f.material_index==slot and low<(o.matrix_world@f.center).z<low+.2]);front=pp[(pp[:,1]<-.28)&(abs(pp[:,0])<.3)] if len(pp) else []
  if len(front):print(slot,low,len(front),'qXYZ',np.percentile(front,[0,20,50,80,100],axis=0).round(4).tolist())
print('SETTYPES',[(p.identifier,p.type,p.description) for p in bpy.types.Curves.bl_rna.functions['set_types'].parameters])
