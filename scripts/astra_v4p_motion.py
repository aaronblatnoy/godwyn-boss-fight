"""V4 cloth-weight smoothing, measured rigid grip and world-space two-clip bake."""
import bpy,sys,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'))
import astra_v3_build as b
import astra_v3m_retarget_world as w
import astra_v3m_publish as pub
O=R/'renders/astra/v4p';inp=sys.argv[sys.argv.index('--input')+1] if '--input' in sys.argv else 'face_full.blend';bpy.ops.wm.open_mainfile(filepath=str(O/inp));s=bpy.context.scene;rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];sword=bpy.data.objects['Godwyn_Sword'];s.render.fps=30;rig.data.pose_position='REST';bpy.context.view_layer.update()
def geom():
 h=hashlib.sha256()
 for col,key,num,dtype in [(body.data.vertices,'co',3,np.float32),(body.data.loops,'vertex_index',1,np.int32)]:
  a=np.empty(len(col)*num,dtype);col.foreach_get(key,a);h.update(a.tobytes())
 return h.hexdigest()
original=geom();pts=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);tri=np.array([list(f.vertices) for f in body.data.polygons]);uv=np.array([d.uv[:] for d in body.data.uv_layers[0].data]).reshape(-1,3,2).mean(1);cloth=b.image_array(bpy.data.images['V4 cloth_mask']);cv=cloth[(uv[:,1]*2048).astype(int)%2048,(uv[:,0]*2048).astype(int)%2048,0];cent=pts[tri].mean(1);clothfaces=(cv>.3)&(cent[:,2]<1.72);ids=np.unique(tri[clothfaces]);names={g.index:g.name for g in body.vertex_groups};allowed=['Hips','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase'];gi={n:body.vertex_groups[n].index for n in allowed};W=np.zeros((len(pts),len(allowed)),np.float64)
for vertex in body.data.vertices:
 for g in vertex.groups:
  if names[g.group] in allowed:W[vertex.index,allowed.index(names[g.group])]=g.weight
old=W.copy();total=W.sum(1);ids=ids[total[ids]>.02]
# Spatial neighbors only among selected cloth; 35mm avoids joining distant robe panels.
tree=KDTree(len(ids))
for i,idx in enumerate(ids):tree.insert(Vector(pts[idx]),i)
tree.balance();ix=np.zeros((len(ids),32),np.int32);val=np.zeros((len(ids),32),np.float64)
for i,idx in enumerate(ids):
 found=tree.find_n(Vector(pts[idx]),32)
 for j,(_,neighbor,distance) in enumerate(found):
  ix[i,j]=neighbor;val[i,j]=math.exp(-(distance/.018)**2) if distance<=.035 else 0
val/=val.sum(1)[:,None];values=W[ids]/total[ids,None]
for iteration in range(12):
 avg=np.empty_like(values)
 for j in range(len(allowed)):avg[:,j]=(values[ix,j]*val).sum(1)
 values=.25*values+.75*avg
 print('V4P_WEIGHT_PASS',iteration+1,flush=True)
W[ids]=values*total[ids,None]
for j,n in enumerate(allowed):
 group=body.vertex_groups[n]
 for idx in ids:
  val=float(W[idx,j])
  if val>1e-8:group.add([int(idx)],val,'REPLACE')
  else:group.remove([int(idx)])
# Grip search retains the smallest adjustment satisfying 5–12mm intentional palm embed.
handids={v.index for v in body.data.vertices if sum(g.weight for g in v.groups if names[g.group]=='RightHand')>.5};handfaces=[tuple(f.vertices) for f in body.data.polygons if all(i in handids for i in f.vertices)];ht=BVHTree.FromPolygons(pts.tolist(),handfaces);src=np.array([v.vector[:] for v in sword.data.attributes['astra_sword_source'].data]);fit=np.linalg.lstsq(np.column_stack((src,np.ones(len(src)))),np.array([v.co[:] for v in sword.data.vertices]),rcond=None)[0];hilt=sword.matrix_world@Vector(np.array([61.2,-66.3,167,1.])@fit);candidates=[]
for x in [-.01,0,.01]:
 for y in [-.01,0,.01]:
  for z in [-.01,0,.01]:
   offset=Vector((x,y,z));p=hilt+offset;near=ht.find_nearest(p);depth=-float((p-near[0]).dot(near[1]));score=offset.length+10*max(0,.005-depth,depth-.012);candidates.append((score,offset,depth))
best=min(candidates,key=lambda r:r[0]);offset=best[1];sword.location+=offset;grip={'tested_translations':27,'search_m':[-.01,0,.01],'translation_m':list(offset),'signed_normal_depth_mm':best[2]*1000,'criterion':'Minimum translation with handle-center signed surface depth 5–12mm; positive inward. Generated fingers intentionally remain open.'}
# Fresh read of both source clips and parent-first rest-independent world rotations.
with bpy.data.libraries.load(str(R/'models/astra_character_v3.blend'),link=False) as (av,dest):dest.objects=['Astra_V3_Rig'];dest.actions=['Combat_Stance','sword_slash_r']
source=dest.objects[0];s.collection.objects.link(source);source.data.pose_position='POSE';acts=dest.actions;oldacts=[a for a in bpy.data.actions if a not in acts];w.reset(rig);rig.data.pose_position='POSE'
order=w.topological(rig);rest={n:rig.data.bones[n].matrix_local.copy() for n in order};rootdelta=(source.matrix_world@source.data.bones['Hips'].matrix_local).translation-(rig.matrix_world@rig.data.bones['Hips'].matrix_local).translation;winv=rig.matrix_world.inverted();rinv=rig.matrix_world.to_quaternion().inverted().to_matrix();report={};newacts=[];sole=w.sole_ids(body)
for act,label in zip(acts,['Combat_Stance','sword_slash_r']):
 start,end=[int(round(x)) for x in act.frame_range];new=bpy.data.actions.new('V4P_'+label);slot,bag=w.action_channelbag(new,rig);expected=[];previous={}
 for frame in range(start,end+1):
  w.assign(source,act,frame);desired={};row={}
  for n in order:
   world=source.matrix_world@source.pose.bones[n].matrix;desired[n]=rinv@world.to_quaternion().normalized().to_matrix();pa=rig.data.bones[n].parent;relative=rest[pa.name].to_3x3().inverted()@rest[n].to_3x3() if pa else rest[n].to_3x3();basis=relative.inverted()@(desired[pa.name].inverted() if pa else Matrix.Identity(3))@desired[n];q=basis.to_quaternion().normalized()
   if n in previous and q.dot(previous[n])<0:q.negate()
   previous[n]=q.copy();row[n]=world.to_quaternion().normalized()
   for i,val in enumerate(q):w.key(bag,f'pose.bones["{n}"].rotation_quaternion',i,frame-start+1,val)
  root=winv@((source.matrix_world@source.pose.bones['Hips'].matrix).translation-rootdelta);loc=rest['Hips'].to_3x3().inverted()@(root-rig.data.bones['Hips'].head_local)
  for i,val in enumerate(loc):w.key(bag,'pose.bones["Hips"].location',i,frame-start+1,val)
  expected.append(row)
 for c in bag.fcurves:c.update()
 curves={(c.data_path,c.array_index):c for c in bag.fcurves};ground=[];errors=[]
 for frame in range(1,len(expected)+1):
  w.assign(rig,new,frame);bp=w.evaluated_points(body);low=min(float(bp[ix,2].min()) for ix in sole.values());shift=.001-low;delta=rest['Hips'].to_3x3().inverted()@(rig.matrix_world.to_3x3().inverted()@Vector((0,0,shift)))
  for i in range(3):c=curves[('pose.bones["Hips"].location',i)];c.keyframe_points[frame-1].co[1]+=delta[i];c.update()
  ground.append(shift)
 for frame in range(1,len(expected)+1):
  w.assign(rig,new,frame)
  for n in order:
   q=(rig.matrix_world@rig.pose.bones[n].matrix).to_quaternion().normalized();angle=math.degrees(q.rotation_difference(expected[frame-1][n]).angle);errors.append(min(angle,abs(360-angle)))
 new.use_fake_user=True;newacts.append((new,label));report[label]={'frames':len(expected),'max_world_orientation_error_deg':max(errors),'ground_offsets_m':ground}
for ob in list(bpy.data.objects):
 if ob not in [body,rig,sword]:bpy.data.objects.remove(ob,do_unlink=True)
for act in list(bpy.data.actions):
 if act not in [x[0] for x in newacts]:bpy.data.actions.remove(act)
for act,label in newacts:act.name=label
assert geom()==original;rep={'geometry_sha256_before':original,'geometry_sha256_after':geom(),'weights':pub.weight_audit([body,sword],rig),'cloth':{'vertices_smoothed':len(ids),'passes':12,'neighbor_radius_m':.035,'neighbor_limit':32,'relaxation':.75,'bones':allowed,'maximum_weight_change':float(abs(W-old).max()),'other_bone_weights_unchanged':True,'scope':'blue cloth texels below belt, no vertex-position edits'},'grip':grip,'clips':report}
(O/'motion_build.json').write_text(json.dumps(rep,indent=2));s.frame_start=1;s.frame_end=51;w.assign(rig,bpy.data.actions['Combat_Stance'],1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate.blend'));print('V4P_MOTION',json.dumps(rep),flush=True)
