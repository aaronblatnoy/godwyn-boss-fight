import bpy,sys,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2.blend'))
for name in ['AstraChar2_R4_Curves_L_Front_0','AstraChar2_R4_Control_L_Front_0','AstraChar2_R4_Strands_L_Front_0']:
 o=bpy.data.objects[name];print(name,o.type,'hide_render',o.hide_render,'matrix',list(o.matrix_world),'scale',list(o.scale))
 if o.type=='CURVES':
  for d in [o.data,o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data]:
   a=np.empty(len(d.points),np.float32);d.attributes['radius'].data.foreach_get('value',a);print('RADIUS',np.percentile(a,[0,50,100]).tolist(),'POS',list(d.points[100].position))
print('CYCLES',[(p.identifier,str(getattr(bpy.context.scene.cycles,p.identifier))) for p in bpy.context.scene.cycles.bl_rna.properties if 'hair' in p.identifier or 'curve' in p.identifier])
