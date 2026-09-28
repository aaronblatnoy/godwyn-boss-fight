import bpy, sys, json, numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3_build as b
O=R/'renders/astra/v3b';O.mkdir(exist_ok=True,parents=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'source_snapshot.blend'))
src=bpy.data.objects['Astra_V3_Rig']; sr={x.name:np.asarray(src.matrix_world@x.matrix_local).tolist() for x in src.data.bones}
rep={'source_objects':[{ 'name':x.name,'type':x.type,'matrix':b.json_matrix(x.matrix_world),'materials':[m.name for m in x.data.materials] if x.type=='MESH' else []} for x in bpy.context.scene.objects], 'source_actions':[x.name for x in bpy.data.actions]}
a,ob=b.import_rigged(R/'models/meshy_body_godA_fists_rigged.glb')
imgs=b.import_source_pbr(ob.data.materials[0],R/'models/meshy_body_godA_fists.glb')
rows=b.face_samples(ob,b.image_array(imgs['base']),b.image_array(imgs['orm']))
p=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);gn={g.index:g.name for g in ob.vertex_groups}
print('RAW_BOUNDS',p.min(0),p.max(0),flush=True)
print('NECK_BONE',list(a.matrix_world@a.data.bones['neck'].head_local),flush=True)
print('GROUPS',[(n, sum(any(g.group==i and g.weight>.05 for g in v.groups) for v in ob.data.vertices)) for i,n in gn.items() if n in ('neck','Head')],flush=True)
neck=[v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if gn[g.group] in ('neck','Head'))>.25 and 2.50<p[v.index,2]<2.65 and abs(p[v.index,0])<.18 and -.4<p[v.index,1]<.08]
assert neck
axis=p[neck,:2].mean(0);r=np.linalg.norm(p[:,:2]-axis,axis=1)
rep.update({'raw_bounds':[p.min(0).tolist(),p.max(0).tolist()],'neck_vertex_count':len(neck),'neck_axis':axis.tolist(),'neck_bounds':[p[neck].min(0).tolist(),p[neck].max(0).tolist()],'rest_matrix_maxdiff':max(float(np.max(np.abs(np.array(sr[x.name])-np.array(a.matrix_world@x.matrix_local)))) for x in a.data.bones)})
rep['bands']=[]
for z in np.arange(2.45,3.25,.025):
 rr=[x for x in rows if z<=x['center'].z<z+.025]
 pp=[x for x in rr if x['plate']]
 rep['bands'].append({'z':float(z),'faces':len(rr),'plate':len(pp),'r_plate_percentiles':np.percentile([np.linalg.norm(np.array(x['center'][:2])-axis) for x in pp],[0,10,50,90,100]).tolist() if pp else []})
# Store exact pre-cut samples for measurement and proof on server.
np.savez_compressed(O/'raw_probe.npz',points=p,faces=np.array([list(x.vertices) for x in ob.data.polygons]),plate=np.array([x['plate'] for x in rows]),blue=np.array([x['blue'] for x in rows]),base=np.array([x['base'] for x in rows]),orm=np.array([x['orm'] for x in rows]),axis=axis)
(O/'probe.json').write_text(json.dumps(rep,indent=2));print('V3B_PROBE',json.dumps({k:v for k,v in rep.items() if k!='source_objects'}),flush=True)
