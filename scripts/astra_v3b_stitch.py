"""Unify weights at coincident source seam vertices without changing geometry."""
import bpy,sys,json,numpy as np
from pathlib import Path
from collections import defaultdict
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3m_render as v
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(O/'strict_candidate.blend'))
body=bpy.data.objects['char1'];groups=defaultdict(list)
for vert in body.data.vertices:
 p=body.matrix_world@vert.co;groups[tuple(round(x,6) for x in p)].append(vert.index)
changed=0;badgroups=0;maxdiff=0
for ids in groups.values():
 if len(ids)<2:continue
 rows=np.zeros((len(ids),len(body.vertex_groups)))
 for j,i in enumerate(ids):
  for g in body.data.vertices[i].groups:rows[j,g.group]=g.weight
 avg=rows.mean(0);avg/=avg.sum();diff=float(np.max(np.abs(rows-avg)))
 if diff<1e-6:continue
 maxdiff=max(maxdiff,diff);badgroups+=1
 for g in body.vertex_groups:g.remove(ids)
 for j,w in enumerate(avg):
  if w>1e-8:body.vertex_groups[j].add(ids,float(w),'REPLACE')
 changed+=len(ids)
rep={'changed_vertices':changed,'changed_coincident_groups':badgroups,'max_weight_delta':maxdiff,'position_tolerance_m':1e-6,'faces_before_after':len(body.data.polygons),'geometry_changed':False}
(O/'stitch.json').write_text(json.dumps(rep,indent=2));print('V3B_STITCH',json.dumps(rep),flush=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'stitched_candidate.blend'))
s=bpy.context.scene;rig=bpy.data.objects['Astra_V3_Rig'];v.assign_action(rig,bpy.data.actions['Combat_Stance'],1);c=v.studio(s);v.configure(s,1200,1800,64)
v.set_camera(c,(0,7,1.65),(0,0,1.65),3.9);v.render(s,O/'stitch_back.png')
