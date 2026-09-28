"""Rest/weights, independent synthetic stress poses, and glTF round-trip verification.
Does not load any project moveset or finalized animation asset.
"""
import bpy,sys,json,math,numpy as np,struct
from pathlib import Path
from mathutils import Vector,Quaternion
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_mpfb_clay import studio
from astra_char2_mpfb_recombine import mesh_digest
from astra_character_common import aim

def reset(arm):
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.view_layer.update()
def rotate(arm,name,axis,angle):
 b=arm.pose.bones[name];v=(arm.matrix_world.to_3x3()@b.bone.matrix_local.to_3x3()).inverted()@Vector(axis)
 b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion(v.normalized(),math.radians(angle))
def pose(arm,label):
 reset(arm)
 if label=='arms_raised':
  rotate(arm,'LeftArm',(0,1,0),-105);rotate(arm,'RightArm',(0,1,0),105)
  rotate(arm,'Head',(0,0,1),10)
 else:
  rotate(arm,'Spine',(0,0,1),24);rotate(arm,'Head',(0,0,1),-18)
  rotate(arm,'LeftArm',(1,0,0),-78);rotate(arm,'RightArm',(0,1,0),65)
  rotate(arm,'LeftForeArm',(0,0,1),55);rotate(arm,'RightForeArm',(1,0,0),-60)
  rotate(arm,'LeftUpLeg',(1,0,0),-18);rotate(arm,'RightUpLeg',(1,0,0),15)
  for b in arm.pose.bones:
   if b.name.startswith('phys_hair_'):rotate(arm,b.name,(1,0,0),8)
 bpy.context.view_layer.update()
def vertices(ob):
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());a=np.empty(len(ev.data.vertices)*3,np.float32);ev.data.vertices.foreach_get('co',a)
 return a.reshape(-1,3)@np.array(ev.matrix_world.to_3x3()).T+np.array(ev.matrix_world.translation)
def draw(label):
 s=studio(False,32,900);s.render.resolution_x=s.render.resolution_y=1100;s.camera.location=(3,-8,3.5);aim(s.camera,(0,-.05,1.75));s.camera.data.ortho_scale=4.1
 s.render.filepath=str(O/f'{label}.png');bpy.ops.render.render(write_still=True)
def weights_check(obs,arm):
 total=0;bad=0;maximum=0;used=set();examples=[]
 for ob in obs:
  if ob.type!='MESH' or not any(m.type=='ARMATURE' for m in ob.modifiers):continue
  deform={g.index:g.name for g in ob.vertex_groups if g.name in arm.data.bones}
  referenced={v for p in ob.data.polygons for v in p.vertices}
  for i in referenced:
   gs=[g for g in ob.data.vertices[i].groups if g.group in deform and g.weight>0]
   total+=1;err=abs(sum(g.weight for g in gs)-1);maximum=max(maximum,err)
   if not gs or err>.003:
    bad+=1
    if len(examples)<12:examples.append([ob.name,i,err])
   used.update(deform[g.group] for g in gs)
 return {'referenced_skinned_vertices':total,'unweighted_or_bad_sum_vertices':bad,'weight_sum_max_error':maximum,'bad_examples':examples,'hair_bones_used':sorted(n for n in used if n.startswith('phys_hair_'))}
def stresses(arm,label):
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render and (o.name.startswith(('AstraChar2_Mpfb_Head','AstraChar2_R5_Gorget','AstraChar2_R5_Cuirass','AstraChar2_R5_Pauldron_')))]
 reset(arm);rest={o.name:vertices(o) for o in obs};edges={o.name:np.array([e.vertices[:] for e in o.data.edges],int) for o in obs};out={}
 for p in ['arms_raised','combat_stress']:
  pose(arm,p);out[p]={}
  for ob in obs:
   a=rest[ob.name];b=vertices(ob);e=edges[ob.name]
   assert np.isfinite(b).all() and np.max(np.abs(b))<10
   before=np.linalg.norm(a[e[:,0]]-a[e[:,1]],axis=1);after=np.linalg.norm(b[e[:,0]]-b[e[:,1]],axis=1);rat=after[before>.0003]/before[before>.0003]
   out[p][ob.name]={'edge_stretch_max':float(rat.max()),'edge_stretch_p99':float(np.quantile(rat,.99))}
   assert rat.max()<4, (ob.name,p,float(rat.max()))
  draw(label+'_'+p)
 reset(arm);return out

def hair_check(arm):
 report={};pose(arm,'combat_stress');dg=bpy.context.evaluated_depsgraph_get()
 for cu in bpy.context.scene.objects:
  if cu.type!='CURVES' or not cu.name.startswith('AstraChar2_R5_Curves_MPFB_'):continue
  label=cu.name.removeprefix('AstraChar2_R5_Curves_');ctl=bpy.data.objects['AstraChar2_R5_Control_'+label];tube=bpy.data.objects['AstraChar2_R5_Strands_'+label]
  ev=cu.evaluated_get(dg);a=np.empty(len(ev.data.points)*3,np.float32);ev.data.position_data.foreach_get('vector',a)
  a=a.reshape(-1,3)@np.array(ev.matrix_world.to_3x3()).T+np.array(ev.matrix_world.translation);b=vertices(ctl)
  err=float(np.max(np.abs(a-b)));assert err<1e-5,(label,err)
  n=cu['groom_strands'];k=cu['groom_points_per_strand'];index=np.unique(np.r_[np.arange(0,k,2),k-1]);centers=vertices(tube).reshape(n,len(index),3,3).mean(2)
  tubeerr=float(np.max(np.abs(centers-b.reshape(n,k,3)[:,index])));assert tubeerr<1e-5,(label,tubeerr)
  raw=np.empty(len(ctl.data.vertices)*3,np.float32);ctl.data.vertices.foreach_get('co',raw);raw=raw.reshape(n,k,3)
  before=np.linalg.norm(np.diff(raw,axis=1),axis=2);after=np.linalg.norm(np.diff(b.reshape(n,k,3),axis=1),axis=2);ratio=after[before>.0001]/before[before>.0001]
  report[label]={'native_control_max_error_m':err,'portable_center_max_error_m':tubeerr,'strands':n,'segment_stretch_max':float(ratio.max()),'segment_stretch_p99':float(np.quantile(ratio,.99))}
 reset(arm);return report

def main(source,label,roundtrip=False):
 if roundtrip:
  bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/source));arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
 else:
  bpy.ops.wm.open_mainfile(filepath=str(R/source));arm=bpy.data.objects['Armature']
 reset(arm);assert len(arm.data.bones)==121 and len(bpy.data.actions)==0
 baseline=json.loads((O/'mpfb_baseline.json').read_text())['bones'];assert set(arm.data.bones.keys())==set(baseline)
 report={'source':source,'bones':len(arm.data.bones),'actions':len(bpy.data.actions),'roundtrip':roundtrip}
 if not roundtrip:
  bank=json.loads((O/'mpfb_banked_baseline.json').read_text())['objects']
  report['existing_character_names_and_slots_preserved']=all(n in bpy.data.objects and [m.name if m else None for m in bpy.data.objects[n].data.materials]==d['slots'] for n,d in bank.items() if d['type'] in {'MESH','CURVES'})
  assert report['existing_character_names_and_slots_preserved']
  report['rest_matrix_error']=max(float(np.abs(np.array(b.matrix_local)-np.array(baseline[b.name]['rest'])).max()) for b in arm.data.bones);assert report['rest_matrix_error']==0
  hashes=json.loads((O/'mpfb_graft_i04.json').read_text())['banked_armor_mesh_and_weight_hashes'];report['banked_armor_hashes_preserved']=all(mesh_digest(bpy.data.objects[n])==h for n,h in hashes.items());assert report['banked_armor_hashes_preserved']
 else:
  errors={b.name:float(np.max(np.abs(np.array(arm.matrix_world@b.head_local)-np.array(baseline[b.name]['head'])))) for b in arm.data.bones}
  report['world_joint_position_max_error_m']=max(errors.values());report['joint_error_top10']=sorted(errors.items(),key=lambda x:-x[1])[:10]
  (O/f'{label}_validation.json').write_text(json.dumps(report,indent=2));print('ROUNDTRIP_JOINTS',report['joint_error_top10'],flush=True)
  report['world_joint_position_tolerance_m']=.00005
  assert report['world_joint_position_max_error_m']<.00005
  report['bone_names_and_hierarchy_preserved']=all((b.parent.name if b.parent else None)==baseline[b.name]['parent'] for b in arm.data.bones);assert report['bone_names_and_hierarchy_preserved']
  data=(R/source).read_bytes();n=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+n]);report['glb_skin_joint_counts']=[len(s['joints']) for s in j['skins']];report['glb_animations']=len(j.get('animations',[]));assert all(x==121 for x in report['glb_skin_joint_counts']) and not report['glb_animations']
 visible=[o for o in bpy.context.scene.objects if not o.hide_render]
 if not roundtrip:visible += [o for o in bpy.context.scene.objects if o.name.startswith('AstraChar2_R5_Strands_MPFB_')]
 report['weights']=weights_check(visible,arm);(O/f'{label}_validation.json').write_text(json.dumps(report,indent=2));assert report['weights']['unweighted_or_bad_sum_vertices']==0
 assert len(report['weights']['hair_bones_used'])==12
 if not roundtrip:
  report['hair_correspondence_combat_pose']=hair_check(arm)
  assert max(x['segment_stretch_max'] for x in report['hair_correspondence_combat_pose'].values())<4
  h=bpy.data.objects['AstraChar2_Mpfb_Head'];counts={}
  for f in h.data.polygons:
   vv=list(f.vertices)
   for a,b in zip(vv,vv[1:]+vv[:1]):
    key=tuple(sorted((a,b)));counts[key]=counts.get(key,0)+1
  report['head_topology']={'vertices':len(h.data.vertices),'faces':len(h.data.polygons),'boundary_edges':sum(v==1 for v in counts.values()),'nonmanifold_edges':sum(v>2 for v in counts.values())}
 report['poses']=stresses(arm,label)
 report['neutral_restored']=all(np.allclose(np.array(b.matrix_basis),np.eye(4),atol=1e-6) for b in arm.pose.bones)
 (O/f'{label}_validation.json').write_text(json.dumps(report,indent=2));print('MPFB_VALIDATION_PASS',label,flush=True)
if __name__=='__main__':
 a=sys.argv[sys.argv.index('--')+1:];main(a[0],a[1],len(a)>2 and a[2]=='roundtrip')
