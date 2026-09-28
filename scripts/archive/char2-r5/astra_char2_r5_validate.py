"""Geometry, rig, hair deformation and native/portable correspondence checks."""
import bpy,sys,json,math,numpy as np,bmesh
from pathlib import Path
from mathutils import Quaternion
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r5_groom_clay.blend'));reset_pose();arm=bpy.data.objects['Armature']
def verts(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());v=np.empty(len(ev.data.vertices)*3,np.float32);ev.data.vertices.foreach_get('co',v);return v.reshape(-1,3)
def points(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());v=np.empty(len(ev.data.points)*3,np.float32);ev.data.position_data.foreach_get('vector',v);return v.reshape(-1,3)
head=bpy.data.objects['AstraChar2_R5_Head'];bm=bmesh.new();bm.from_mesh(head.data)
r={'bones':len(arm.data.bones),'actions':len(bpy.data.actions),'head':{'vertices':len(head.data.vertices),'faces':len(head.data.polygons),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_surface_edges':sum(len(e.link_faces)>2 for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-12 for f in bm.faces)},'hair_groups':{},'spring_test':{}}
bm.free();controls=[o for o in bpy.data.objects if o.name.startswith('AstraChar2_R5_Control_')];rest={o.name:verts(o) for o in controls};body=bpy.data.objects['char1'];bodyrest=verts(body)
theta=0.;velocity=2.;trace=[];dt=1/120
for k in range(721):
 trace.append((k*dt,theta,velocity));velocity+=(-32*theta-7*velocity)*dt;theta+=velocity*dt
peak=max(trace,key=lambda x:abs(x[1]));settled=trace[-1];r['spring_test']={'peak':peak,'settled':settled,'stiffness_s2':32,'damping_s':7,'step_s':dt,'states':{}}
for label,angle in [('neutral',0),('peak',peak[1]),('settled',settled[1])]:
 reset_pose()
 for b in arm.pose.bones:
  if b.name.startswith('phys_hair'):
   i=int(b.name[-2:]);b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion((1,0,0) if 'back' in b.name else (0,0,1),angle*(.72**i)*(-1 if '_L_' in b.name else 1))
 bpy.context.view_layer.update();state={}
 for ctl in controls:
  suffix=ctl.name.removeprefix('AstraChar2_R5_Control_');cu=bpy.data.objects['AstraChar2_R5_Curves_'+suffix];p=verts(ctl);cp=points(cu);n=int(cu['groom_strands']);K=len(p)//n;idx=np.unique(np.r_[np.arange(0,K,2),K-1]);expected=p.reshape(n,K,3)[:,idx].reshape(-1,3)
  mesh=verts(bpy.data.objects['AstraChar2_R5_Strands_'+suffix]).reshape(-1,3,3).mean(1)
  state[suffix]={'native_strands':n,'native_points_per_strand':K,'portable_points_per_strand':len(idx),'curve_control_max_error_m':float(np.linalg.norm(cp-p,axis=1).max()),'portable_center_max_error_m':float(np.linalg.norm(mesh-expected,axis=1).max()),'max_displacement_m':float(np.linalg.norm(p-rest[ctl.name],axis=1).max())}
  assert state[suffix]['curve_control_max_error_m']<1e-5 and state[suffix]['portable_center_max_error_m']<1e-5
  cu['groom_points_per_strand']=K
 state['body_max_displacement_m']=float(np.linalg.norm(verts(body)-bodyrest,axis=1).max()*.01);assert state['body_max_displacement_m']<1e-6
 r['spring_test']['states'][label]=state;print('HAIR VALIDATED',label,flush=True)
reset_pose();r['neutral_restored']=all(np.allclose(np.array(b.matrix_basis),np.eye(4),atol=1e-6) for b in arm.pose.bones);r['hair_bone_chains']='SKINNING_AND_LOCAL_DAMPED_IMPULSE_VALIDATED; ENGINE_SPRING_AND_COLLISION_INTEGRATION_OUTSTANDING'
r['rig_display_tail_limit']='Exact rest matrices preserved. Inherited oversized Blender display tails remain; exported physical endpoints use existing explicit spring metadata, not display tails.'
assert r['bones']==121 and r['actions']==0 and r['neutral_restored'];assert r['head']['boundary_edges']==0 and r['head']['nonmanifold_surface_edges']==0
(O/'r5_geometry_validation.json').write_text(json.dumps(r,indent=2));print('GEOMETRY VALIDATION PASS',flush=True)
