import bpy,numpy as np,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(R/'renders/astra/v3b/candidate_final.blend'))
for name in ['AstraChar2_Meshy_HeadHair','AstraChar2_Meshy_NeckBlend']:
 ob=bpy.data.objects[name];p=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);mask=ob.data.color_attributes.get('meshy_skin_mask');ids=set()
 if mask:
  for f in ob.data.polygons:
   if np.mean([mask.data[i].color[0] for i in f.loop_indices])>.5:ids.update(f.vertices)
 else:ids=set(range(len(p)))
 q=p[list(ids)];print(name,'world',list(ob.matrix_world),'parentinverse',list(ob.matrix_parent_inverse),'bounds',q.min(0),q.max(0),flush=True)
 for z in np.arange(2.7,3.1,.025):
  x=q[(q[:,2]>=z)&(q[:,2]<z+.025)]
  if len(x):print('SLICE',z,len(x),x[:,:2].min(0),x[:,:2].max(0),x[:,:2].mean(0),flush=True)
