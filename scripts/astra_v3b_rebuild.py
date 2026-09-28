"""Rebuild v3b on black-sky; immutable raw topology except explicit head volume."""
import sys,json,math,hashlib
from pathlib import Path
from collections import Counter
import bpy,bmesh,numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector,Matrix
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3b_materials as materials
import astra_v3_build as b
import astra_v3m_retarget_world as rt
import astra_v3m_render as v
O=R/'renders/astra/v3b';N=72

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,d):(O/n).write_text(json.dumps(d,indent=2))
def mesh(name,verts,faces,mat,rig):
 m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.update();ob=bpy.data.objects.new(name,m);bpy.context.scene.collection.objects.link(ob);m.materials.append(mat);b.bind_rigid(ob,rig,'neck','Neck skin');return ob

def main():
 raw=R/'models/meshy_body_godA_fists_rigged.glb';snapshot=O/'source_snapshot.blend'
 rig,body=b.import_rigged(raw);bpy.context.view_layer.update()
 d=np.load(O/'raw_probe.npz');ww=np.load(O/'weights.npz');p=d['points'];faces=d['faces'];weights=ww['weights'];names=list(ww['names'])
 assert np.array_equal(faces,np.array([list(x.vertices) for x in body.data.polygons]))
 axis=p[weights[:,names.index('neck')]>.5,:2].mean(0)
 rr=np.linalg.norm(p[:,:2]-axis,axis=1);ang=np.mod(np.arctan2(p[:,1]-axis[1],p[:,0]-axis[0]),2*np.pi);sectors=np.floor(ang/(2*np.pi)*N).astype(int)%N
 # Measure the inner wall from source high-torso plate vertices, excluding the head crown.
 collar_faces=(d['plate'])&(p[faces].mean(1)[:,2]>=2.48)&(p[faces].mean(1)[:,2]<=2.73)&(np.abs(p[faces].mean(1)[:,0])<.30)
 collar_ids=np.unique(faces[collar_faces]);collar_ids=collar_ids[(rr[collar_ids]<.36)&(p[collar_ids,2]>=2.48)]
 rim=float(p[collar_ids,2].max());floor=float(p[collar_ids,2].min())
 radii=[];samples=[]
 for k in range(N):
  ids=collar_ids[sectors[collar_ids]==k]
  if len(ids)==0:
   delta=np.abs(np.angle(np.exp(1j*(ang[collar_ids]-(k+.5)*2*np.pi/N))));ids=collar_ids[np.argsort(delta)[:12]]
  radii.append(float(rr[ids].min()));samples.append(len(ids))
 radii=np.array(radii);cut_r=radii-.008
 fc=p[faces].mean(1)
 rgb=d['base']
 collar_high=d['plate']&(fc[:,2]>2.73)&(fc[:,2]<2.90)&(np.abs(fc[:,0])<.30)&(weights[faces,names.index('Head')].mean(1)<.5)&(rgb[:,0]-rgb[:,2]>.175)&(rgb[:,1]-rgb[:,2]>.085)
 collar_protected=collar_faces|collar_high
 regions={'cape':d['blue']&(fc[:,2]>1.5)&(fc[:,1]>-.15),'upper_back':(fc[:,2]>1.65)&(fc[:,2]<2.75)&(fc[:,1]>-.1),'collar':collar_protected,'collar_original_measured':collar_faces,'collar_high_guard':collar_high,'pauldrons':(fc[:,2]>2.35)&(np.abs(fc[:,0])>.28),'rear_hem':(fc[:,2]<.45)&(fc[:,1]>0),'all_plates':d['plate'],'entire_body':np.ones(len(faces),bool)}
 protected=np.logical_or.reduce([regions[k] for k in ('cape','upper_back','collar','pauldrons','rear_hem')])
 # Owner clarification: i02 HAIR COLOR test, constrained by the supplied geometry volume.
 rgb=d['base'];luma=rgb@np.array([.2126,.7152,.0722])
 hair_color=(luma<=.665)&((rgb[:,0]-rgb[:,2])>=.175)&((rgb[:,1]-rgb[:,2])>=.085)
 va=(p[:,2]>rim-.005)&(rr<.28)
 vb=(p[:,2]>2.55)&(rr<.20)
 eligible=(va[faces]|(hair_color[:,None]&vb[faces])).all(1)
 remove=eligible&~protected
 assert not (remove&protected).any()
 head_top=float(p[weights[:,names.index('Head')]>.5,2].max())
 # Original face IDs survive bmesh, enabling a full geometry/UV/weight proof.
 a=body.data.attributes.new('astra_v3b_raw_face','INT','FACE');a.data.foreach_set('value',np.arange(len(faces),dtype=np.int32))
 for name,mask in [('astra_v3_plate_mask',d['plate']),('astra_v3_cloth_mask',d['blue']&~d['plate'])]:
  a=body.data.color_attributes.new(name=name,type='FLOAT_COLOR',domain='CORNER')
  vals=np.ones((len(body.data.loops),4),np.float32);vals[:,:3]=np.repeat(mask,3)[:,None];a.data.foreach_set('color',vals.ravel())
 bm=bmesh.new();bm.from_mesh(body.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[i] for i in np.where(remove)[0]],context='FACES');bm.to_mesh(body.data);bm.free();body.data.update()
 kept=np.array([x.value for x in body.data.attributes['astra_v3b_raw_face'].data]);assert set(kept)==set(np.where(~remove)[0])
 current=np.array([(body.matrix_world@x.co)[:] for x in body.data.vertices]);old_geom=p[faces[kept]];new_geom=np.array([current[list(x.vertices)] for x in body.data.polygons]);assert np.array_equal(old_geom,new_geom)
 counts={k:{'before':int(mask.sum()),'after':int((mask&~remove).sum()),'removed':int((mask&remove).sum()),'outside_volume_before':int((mask&~eligible).sum()),'outside_volume_after':int((mask&~eligible&~remove).sum())} for k,mask in regions.items()}
 for name in ('cape','upper_back','collar','pauldrons','rear_hem'):assert counts[name]['removed']==0
 imgs=b.import_source_pbr(body.data.materials[0],R/'models/meshy_body_godA_fists.glb');look=b.install_body_material(body.data.materials[0],imgs)
 with bpy.data.libraries.load(str(snapshot),link=False) as (src,dst):dst.objects=['AstraChar2_Meshy_HeadHair','AstraChar2_Meshy_NeckBlend','Godwyn_Sword','Astra_V3_Rig'];dst.actions=['Combat_Stance']
 donor=next(x for x in dst.objects if x.type=='ARMATURE');parts=[x for x in dst.objects if x.type=='MESH']
 for ob in dst.objects:
  if ob.name not in bpy.context.scene.objects:bpy.context.scene.collection.objects.link(ob)
 bpy.context.view_layer.update()
 rest_error=max(float(np.max(np.abs(np.asarray(rig.matrix_world@x.matrix_local)-np.asarray(donor.matrix_world@donor.data.bones[x.name].matrix_local)))) for x in rig.data.bones);assert rest_error<1e-8
 transforms={}
 for ob in parts:
  world=ob.matrix_world.copy();binding=list(ob.vertex_groups.keys());ob.parent=rig;ob.matrix_world=world
  for mod in ob.modifiers:
   if mod.type=='ARMATURE':mod.object=rig
  transforms[ob.name]={'matrix_max_error':float(np.max(np.abs(np.array(ob.matrix_world)-np.array(world)))),'binding':binding}
 head=next(x for x in parts if 'HeadHair' in x.name);neck=next(x for x in parts if 'NeckBlend' in x.name)
 hair=rt.delete_small_hair_components(head)
 flat,skin_report=materials.flat_neck(head)
 neck.data.materials.clear();neck.data.materials.append(flat)
 action=dst.actions[0];rig.animation_data_clear();rig.animation_data_create();rig.animation_data.action=action
 if action.slots:rig.animation_data.action_slot=action.slots[0]
 for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
 max_pose=0.
 for frame in range(1,52):
  rt.assign(donor,action,frame);rt.assign(rig,action,frame)
  max_pose=max(max_pose,max(float(np.max(np.abs(np.asarray(rig.matrix_world@x.matrix)-np.asarray(donor.matrix_world@donor.pose.bones[x.name].matrix)))) for x in rig.pose.bones))
 bpy.data.objects.remove(donor,do_unlink=True)
 for act in list(bpy.data.actions):
  if act!=action:bpy.data.actions.remove(act)
 action.name='Combat_Stance';action.use_fake_user=True
 # Funnel closes the annulus around the existing neck, with a closed floor underneath.
 npnt=np.array([(neck.matrix_world@x.co)[:] for x in neck.data.vertices]);topz=min(float(npnt[:,2].max())-.008,rim-.095)
 naxis=npnt[:,:2].mean(0);inner=npnt[npnt[:,2]>topz-.02];rx=max(.035,float(np.max(np.abs(inner[:,0]-naxis[0]))));ry=max(.035,float(np.max(np.abs(inner[:,1]-naxis[1]))))
 verts=[];outer_z=min(rim-.165,topz-.07)
 # Horizontal rays measure the inner wall at the actual loft contact height.
 tree=BVHTree.FromPolygons([tuple(q) for q in p],[tuple(q) for q in faces[collar_faces]],all_triangles=True)
 wall=[]
 for k in range(N):
  th=(k+.5)*2*np.pi/N;hit=tree.ray_cast(Vector((axis[0],axis[1],outer_z)),Vector((math.cos(th),math.sin(th),0)),.6)
  wall.append(float(hit[3]) if hit[0] is not None else float(radii[k]))
 rawwall=np.array(wall);freq=np.fft.rfft(rawwall);freq[6:]=0;wall=np.fft.irfft(freq,n=N)+.008

 for j in range(5):
  t=j/4
  for k in range(N):
   th=(k+.5)*2*np.pi/N;start=naxis+np.array([rx*math.cos(th),ry*math.sin(th)]);end=axis+wall[k]*np.array([math.cos(th),math.sin(th)]);xy=start*(1-t)+end*t;verts.append((float(xy[0]),float(xy[1]),float(topz+(outer_z-topz)*(t*t*(3-2*t)))))
 fs=[(j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k) for j in range(4) for k in range(N)]
 liner=mesh('AstraChar2_V3B_CollarLiner',verts,fs,neck.data.materials[0],rig)
 # Set skin mask and valid UVs for the same approved skin material.
 for name,val in [('meshy_skin_mask',1),('meshy_hair_mask',0)]:
  attr=liner.data.color_attributes.new(name=name,type='FLOAT_COLOR',domain='CORNER')
  for x in attr.data:x.color=(val,val,val,1)
 uv=liner.data.uv_layers.new(name='UVMap');srcuv=neck.data.uv_layers.active
 uvpoint=tuple(srcuv.data[0].uv) if srcuv else (.5,.5)
 for x in uv.data:x.uv=uvpoint
 for poly in liner.data.polygons:poly.use_smooth=True
 dark=rt.material('Astra V3B collar floor',(0.015,.010,.008),0,.85)
 diskverts=[(float(axis[0]),float(axis[1]),floor+.01)]+[(float(axis[0]+(wall[k]+.004)*math.cos((k+.5)*2*np.pi/N)),float(axis[1]+(wall[k]+.004)*math.sin((k+.5)*2*np.pi/N)),floor+.01) for k in range(N)]
 disk=mesh('AstraChar2_V3B_CollarFloor',diskverts,[(0,k+1,(k+1)%N+1) for k in range(N)],dark,rig)
 # Extend funnel skirt to floor, leaving no radial escape path below the wall contact.
 bm=bmesh.new();bm.from_mesh(liner.data);bm.verts.ensure_lookup_table();bottom=[]
 for k in range(N):
  pt=Vector(verts[4*N+k]);pt.z=floor+.01;bottom.append(bm.verts.new(pt))
 bm.verts.ensure_lookup_table()
 for k in range(N):bm.faces.new((bm.verts[4*N+k],bm.verts[4*N+(k+1)%N],bottom[(k+1)%N],bottom[k]))
 bm.normal_update();bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(liner.data);bm.free()
 for poly in liner.data.polygons:poly.use_smooth=True
 liner.vertex_groups['neck'].add(range(len(liner.data.vertices)),1,'REPLACE')
 rep={'inputs':{'raw_sha256':sha(raw),'source_snapshot_sha256':sha(snapshot)},'measurement':{'neck_axis_m':axis.tolist(),'neck_vertices':int((weights[:,names.index('neck')]>.5).sum()),'rim_top_m':rim,'floor_m':floor,'head_top_m':head_top,'inner_radii_m':radii.tolist(),'sector_samples':samples,'cylinder_radii_m':cut_r.tolist(),'method':'72 angular sectors; minimum radial distance to high-torso source plate vertices z 2.48–2.73 m; 8 mm inset'},'removal':{'before':len(faces),'after':len(body.data.polygons),'removed':int(remove.sum()),'volume_A_faces':int(va[faces].all(1).sum()),'volume_B_faces':int((hair_color&vb[faces].all(1)).sum()),'protected_eligible_faces':int((eligible&protected).sum()),'regions':counts,'retained_triangle_coordinates_exact':True},'bindings':transforms,'hair':hair,'look':look,'animation':{'frames':51,'rest_matrix_max_difference':rest_error,'posed_world_matrix_max_difference':max_pose},'liner':{'rings':5,'segments':N,'neck_cut_ring_z':topz,'wall_contact_z':outer_z,'floor_z':floor+.01,'material':neck.data.materials[0].name},'strict_volume':False,'removal_policy':'owner clarification: all vertices in A or hair-colored B; protected populations override removal','skin_material':skin_report,'wall_loft':{'raw_ray_distances_m':rawwall.tolist(),'smoothed_contact_radii_m':wall.tolist(),'smoothing':'five angular Fourier harmonics; 8 mm wall overlap'}}
 dump('build_r5.json',rep);bpy.context.scene.render.fps=30;bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=51;rt.assign(rig,action,1)
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate_r5base.blend'));print('V3B_BUILD',json.dumps(rep),flush=True)
if __name__=='__main__':main()
