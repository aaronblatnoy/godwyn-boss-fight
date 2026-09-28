import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'));import astra_v3m_audit as a
O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];sword=bpy.data.objects['Godwyn_Sword'];names={g.index:g.name for g in body.vertex_groups};hv={v.index for v in body.data.vertices if sum(g.weight for g in v.groups if names[g.group]=='RightHand')>.5};faces=[tuple(f.vertices) for f in body.data.polygons if not all(i in hv for i in f.vertices)];hf=[tuple(f.vertices) for f in body.data.polygons if all(i in hv for i in f.vertices)];sf=[tuple(f.vertices) for f in sword.data.polygons];src=np.array([v.vector[:] for v in sword.data.attributes['astra_sword_source'].data]);fit=np.linalg.lstsq(np.column_stack((src,np.ones(len(src)))),np.array([v.co[:] for v in sword.data.vertices]),rcond=None)[0];hilt=sword.matrix_world@Vector(np.array([61.2,-66.3,167,1.])@fit);axis=sword.matrix_world.to_3x3()@Vector(-fit[2]);axis.normalize();rest=rig.matrix_world@rig.data.bones['RightHand'].matrix_local;pts=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);ht=a.tree(pts,hf);frames=sorted(set(r['frame'] for r in json.loads((O/'collision_probe.json').read_text())));cache=[]
for frame in frames:
 a.assign(rig,bpy.data.actions['sword_slash_r'],frame);bp,_=a.evaluated(body);sp,_=a.evaluated(sword);D=(rig.matrix_world@rig.pose.bones['RightHand'].matrix)@rest.inverted();cache.append((frame,a.tree(bp,faces),sp,np.array(D.to_3x3())))
rows=[]
for distance in [0,.005,.01,.015,.02,.025,.03]:
 delta=np.array(axis)*distance;p=hilt+Vector(delta);near=ht.find_nearest(p);depth=-float((p-near[0]).dot(near[1]));pairs=[len(tree.overlap(a.tree(sp+rot@delta,sf))) for frame,tree,sp,rot in cache];rows.append({'distance_m':distance,'delta_m':delta.tolist(),'signed_depth_mm':depth*1000,'non_grip_pairs':pairs})
ok=[r for r in rows if max(r['non_grip_pairs'],default=0)==0 and r['signed_depth_mm']>1];best=min(ok,key=lambda r:r['distance_m']) if ok else None
if best:
 local=sword.matrix_world.to_3x3().inverted()@Vector(best['delta_m'])
 for vert in sword.data.vertices:vert.co+=local
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate.blend'))
rep={'source':'Pommel crossed wrist/forearm at slash frames; translate rigid sword along handle toward blade, retain palm contact.','frames':frames,'candidates':rows,'chosen':best};(O/'grip_refine.json').write_text(json.dumps(rep,indent=2));print('V4P_GRIP_REFINE',json.dumps(rep),flush=True)
