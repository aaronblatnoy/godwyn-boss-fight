import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3_build as b
import astra_v3m_render as v
O=R/'renders/astra/v3b'
a,ob=b.import_rigged(R/'models/meshy_body_godA_fists_rigged.glb');bpy.context.view_layer.update()
p=np.array([(ob.matrix_world@x.co)[:] for x in ob.data.vertices]);gn={g.index:g.name for g in ob.vertex_groups}
w=np.zeros((len(p),len(gn)))
for x in ob.data.vertices:
 for g in x.groups:w[x.index,g.group]=g.weight
np.savez_compressed(O/'weights.npz',weights=w,names=np.array(list(gn.values())))
rep={}
for n in ['neck','Head']:
 ids=np.where(w[:,ob.vertex_groups[n].index]>.5)[0]
 rep[n]={'count':len(ids),'bounds':[p[ids].min(0).tolist(),p[ids].max(0).tolist()],'bands':[]}
 for lo,hi in [(2.5,2.65),(2.65,2.70),(2.70,2.75),(2.75,2.8),(2.8,2.85),(2.85,2.95)]:
  q=p[ids];q=q[(q[:,2]>=lo)&(q[:,2]<hi)]
  rep[n]['bands'].append({'z':[lo,hi],'n':len(q),'mean':q.mean(0).tolist() if len(q) else None,'bounds':[q.min(0).tolist(),q.max(0).tolist()] if len(q) else None})
(O/'neck_measure.json').write_text(json.dumps(rep,indent=2));print(json.dumps(rep),flush=True)
s=bpy.context.scene;c=v.studio(s);v.configure(s,1200,1800,32)
v.set_camera(c,(0,-3,3.2),(0,-.28,2.75),.8);v.render(s,O/'diagnostic_raw_collar.png')
v.set_camera(c,(0,-2.3,4.6),(0,-.3,2.6),.9);v.render(s,O/'diagnostic_raw_top.png')
