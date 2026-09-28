"""Hair-only damped spring impulse, native curves/control/portable-mesh parity.
No actions or keyframes are created. Only peak-swing and settled stills render.
"""
import bpy,sys,json,numpy as np,math
from pathlib import Path
from mathutils import Quaternion
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r3_render import shot
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2.blend'));reset_pose();arm=bpy.data.objects['Armature'];dg=bpy.context.evaluated_depsgraph_get()
def verts(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());a=np.empty(len(ev.data.vertices)*3,np.float32);ev.data.vertices.foreach_get('co',a);return a.reshape(-1,3)
def curvepoints(o):
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());a=np.empty(len(ev.data.points)*3,np.float32);ev.data.position_data.foreach_get('vector',a);return a.reshape(-1,3)
body=bpy.data.objects['char1'];bodyids=sorted({i for f in body.data.polygons for i in f.vertices});bodyrest=verts(body)[bodyids];controls=[o for o in bpy.data.objects if o.name.startswith('AstraChar2_R4_Control_')];rest={o.name:verts(o) for o in controls}
# Semi-implicit Euler damped torsion spring, impulse then settle. Units rad/sec.
theta=0.;velocity=2.0;dt=1/120;trace=[]
for k in range(721):
 trace.append((k*dt,theta,velocity));accel=-32*theta-7*velocity;velocity+=accel*dt;theta+=velocity*dt
peak=max(trace,key=lambda x:abs(x[1]));settled=trace[-1]
def pose(angle):
 reset_pose()
 for name in [b.name for b in arm.data.bones if b.name.startswith('phys_hair')]:
  bone=arm.pose.bones[name];idx=int(name[-2:]);front='front' in name;sgn=-1 if '_L_' in name else 1;axis=(0,0,1) if front else (1,0,0);bone.rotation_mode='QUATERNION';bone.rotation_quaternion=Quaternion(axis,angle*(sgn if front else 1)*(.72**idx))
 bpy.context.view_layer.update()
r={'bones':len(arm.data.bones),'spring':{'stiffness':32,'damping':7,'impulse_radians_per_second':2,'step_seconds':dt,'peak_time':peak[0],'peak_angle':peak[1],'settled_time':settled[0],'settled_angle':settled[1]},'states':{},'chain_configuration':[]}
for b in arm.data.bones:
 if b.name.startswith('phys_hair'):
  r['chain_configuration'].append({'bone':b.name,'parent':b.parent.name,'head_world':list(arm.matrix_world@b.head_local),'tail_world':list(b.get('spring_rest_tail_world',arm.matrix_world@b.tail_local)),'length_m':float(b.get('spring_segment_length_m',(arm.matrix_world@b.tail_local-arm.matrix_world@b.head_local).length)),'native_display_length_m':float((arm.matrix_world@b.tail_local-arm.matrix_world@b.head_local).length),'stiffness':32,'damping':7,'angular_limit_radians':.52,'collision_radius_m':.015})
for label,angle in [('peak',peak[1]),('settled',settled[1])]:
 pose(angle);state={'nonhair_body_max_displacement_m':float(np.linalg.norm(verts(body)[bodyids]-bodyrest,axis=1).max()*.01),'groups':{}}
 for ctl in controls:
  suffix=ctl.name.removeprefix('AstraChar2_R4_Control_');p=verts(ctl);cu=curvepoints(bpy.data.objects['AstraChar2_R4_Curves_'+suffix]);mesh=verts(bpy.data.objects['AstraChar2_R4_Strands_'+suffix]).reshape(-1,3,3).mean(1)
  state['groups'][suffix]={'max_displacement_m':float(np.linalg.norm(p-rest[ctl.name],axis=1).max()),'curve_control_error_m':float(np.linalg.norm(cu-p,axis=1).max()),'portable_center_error_m':float(np.linalg.norm(mesh-p,axis=1).max())}
 assert state['nonhair_body_max_displacement_m']<1e-6
 assert max(v['curve_control_error_m'] for v in state['groups'].values())<1e-5
 assert max(v['portable_center_error_m'] for v in state['groups'].values())<1e-5
 r['states'][label]=state
 if '--render' in sys.argv:shot('r4_hair_spring_'+label,(.3,-6,2.58),(0,-.2,2.50),1.7)
reset_pose();r['actions_after_test']=len(bpy.data.actions);r['neutral_restored']=all(np.allclose(np.array(b.matrix_basis),np.eye(4),atol=1e-6) for b in arm.pose.bones)
assert r['bones']==121 and r['actions_after_test']==0 and r['neutral_restored'];assert max(v['max_displacement_m'] for v in r['states']['settled']['groups'].values())<.0001
r['status']='SKINNED_CHAINS_AND_LOCAL_SPRING_TEST_PASS';r['engine_integration']='Engine must consume the exported bone chains and spring metadata; automatic Godot spring/collision solver is not installed by this model-only round.'
(O/'r4_hair_physics.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
