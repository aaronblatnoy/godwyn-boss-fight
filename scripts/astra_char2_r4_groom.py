"""Native hair curves + skinned point controls + matching portable strand meshes.
Always rebuild from the immutable pre-round-4 asset. No changes to face/armor/cloth.
"""
import sys,math,json,hashlib
sys.dont_write_bytecode=True
import bpy,bmesh,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_character_common import reset_pose
rng=np.random.default_rng(74028)

def smooth(a):return np.clip(a,0,1)**2*(3-2*np.clip(a,0,1))
def interp(P,count):
 P=np.array(P,float);t=np.linspace(0,len(P)-1,count);i=np.minimum(t.astype(int),len(P)-2);u=(t-i)[:,None];a=P[np.maximum(0,i-1)];b=P[i];c=P[i+1];d=P[np.minimum(len(P)-1,i+2)]
 return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u**3)
def mat(name,color,native):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;n.clear();out=n.new('ShaderNodeOutputMaterial')
 if native:
  bs=n.new('ShaderNodeBsdfHairPrincipled');bs.model='CHIANG';bs.parametrization='MELANIN';bs.inputs['Melanin'].default_value=.24+(.57-color[0])*.22;bs.inputs['Melanin Redness'].default_value=.12;bs.inputs['Tint'].default_value=(.94,.86,.72,1);bs.inputs['Roughness'].default_value=.38;bs.inputs['Radial Roughness'].default_value=.46;bs.inputs['Random Roughness'].default_value=.14;bs.inputs['Random Color'].default_value=.18;info=n.new('ShaderNodeHairInfo');m.node_tree.links.new(info.outputs['Random'],bs.inputs['Random'])
 else:
  bs=n.new('ShaderNodeBsdfPrincipled');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.36;bs.inputs['Anisotropic'].default_value=.72;bs.inputs['Anisotropic Rotation'].default_value=0;bs.inputs['IOR'].default_value=1.55
 m.node_tree.links.new(bs.outputs[0],out.inputs['Surface']);return m

def bind(o,weights,names):
 arm=bpy.data.objects['Armature'];o.parent=arm;o.matrix_parent_inverse=arm.matrix_world.inverted()
 for j,name in enumerate(names):
  vg=o.vertex_groups.new(name=name);valid=np.flatnonzero(weights[:,j]>1e-6)
  # Quantized weights give large batch assignments without appreciable deformation error.
  vals=np.round(weights[valid,j]*1024).astype(np.int32)
  for val in np.unique(vals):
   if val:vg.add(valid[vals==val].tolist(),float(val)/1024,'REPLACE')
 mod=o.modifiers.new('Hair bone chains','ARMATURE');mod.object=arm

def weights(points,chain):
 arm=bpy.data.objects['Armature'];names=['Head']+['phys_hair_'+chain+'_'+str(i).zfill(2) for i in range(4)];heads=np.array([arm.matrix_world@arm.data.bones[n].head_local for n in names[1:]])
 z=points[:,2];w=np.zeros((len(points),5),np.float32)
 # Smooth weights between adjacent joints; roots above first hair joint stay attached to head.
 ztop=3.08 if chain!='back' else 3.11;keys=np.r_[ztop,heads[:,2]]
 for i in range(4):
  m=(z<=keys[i])&(z>=keys[i+1]);t=np.clip((keys[i]-z[m])/(keys[i]-keys[i+1]),0,1);w[m,i]=1-t;w[m,i+1]=t
 w[z>keys[0],0]=1;w[z<keys[-1],-1]=1
 return w,names

def build_group(label,paths,radii,chain,color):
 paths=np.asarray(paths,np.float32);radii=np.asarray(radii,np.float32);n,k,_=paths.shape;points=paths.reshape(-1,3);rr=radii.reshape(-1);w,names=weights(points,chain)
 native=mat('AstraChar2 R4 Native blonde '+str(color),COLORS[color],True);portable=mat('AstraChar2 R4 Portable blonde '+str(color),COLORS[color],False)
 # One control vertex for every native curve point. Armature modifier drives both.
 me=bpy.data.meshes.new('R4 '+label+' control points');me.vertices.add(len(points));me.vertices.foreach_set('co',points.ravel());proxy=bpy.data.objects.new('AstraChar2_R4_Control_'+label,me);bpy.context.scene.collection.objects.link(proxy);bind(proxy,w,names);proxy.hide_render=True;proxy.hide_set(True)
 cu=bpy.data.hair_curves.new('R4 '+label+' native hair');cu.add_curves([k]*n);cu.position_data.foreach_set('vector',points.ravel());cu.set_types(type='CATMULL_ROM');rad=cu.attributes.new('radius','FLOAT','POINT');rad.data.foreach_set('value',rr);cu.materials.append(native)
 obj=bpy.data.objects.new('AstraChar2_R4_Curves_'+label,cu);bpy.context.scene.collection.objects.link(obj);obj.parent=bpy.data.objects['Armature'];obj.matrix_parent_inverse=obj.parent.matrix_world.inverted()
 ng=bpy.data.node_groups.new('R4 '+label+' skinned curve points','GeometryNodeTree');ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry');ns=ng.nodes;ls=ng.links
 inp=ns.new('NodeGroupInput');out=ns.new('NodeGroupOutput');info=ns.new('GeometryNodeObjectInfo');info.transform_space='RELATIVE';info.inputs['Object'].default_value=proxy;info.inputs['As Instance'].default_value=False
 pos=ns.new('GeometryNodeInputPosition');idx=ns.new('GeometryNodeInputIndex');sample=ns.new('GeometryNodeSampleIndex');sample.data_type='FLOAT_VECTOR';sample.domain='POINT';setp=ns.new('GeometryNodeSetPosition');ls.new(info.outputs['Geometry'],sample.inputs['Geometry']);ls.new(pos.outputs['Position'],sample.inputs['Value']);ls.new(idx.outputs['Index'],sample.inputs['Index']);ls.new(inp.outputs['Geometry'],setp.inputs['Geometry']);ls.new(sample.outputs['Value'],setp.inputs['Position']);ls.new(setp.outputs['Geometry'],out.inputs['Geometry']);mod=obj.modifiers.new('Hair curves follow skinned controls','NODES');mod.node_group=ng
 # Same paths and taper, represented as microscopic triangular tubes for standard glTF.
 tangent=np.gradient(paths,axis=1);tangent/=np.maximum(np.linalg.norm(tangent,axis=2,keepdims=True),1e-8);axis=np.cross(tangent,np.array([0,1,0]));axis/=np.maximum(np.linalg.norm(axis,axis=2,keepdims=True),1e-8);other=np.cross(tangent,axis);angle=np.arange(3)*math.tau/3
 xyz=paths[:,:,None,:]+radii[:,:,None,None]*(axis[:,:,None,:]*np.cos(angle)[None,None,:,None]+other[:,:,None,:]*np.sin(angle)[None,None,:,None]);xyz=xyz.reshape(-1,3)
 base=(np.arange(n)[:,None,None]*k*3+np.arange(k-1)[None,:,None]*3+np.arange(3)[None,None,:]);nxt=base-base%3+(base%3+1)%3;faces=np.stack([base,nxt,nxt+3,base+3],-1).reshape(-1,4).astype(np.int32)
 mm=bpy.data.meshes.new('R4 '+label+' portable individual strands');mm.vertices.add(len(xyz));mm.vertices.foreach_set('co',xyz.ravel());mm.loops.add(faces.size);mm.loops.foreach_set('vertex_index',faces.ravel());mm.polygons.add(len(faces));mm.polygons.foreach_set('loop_start',np.arange(len(faces),dtype=np.int32)*4);mm.polygons.foreach_set('loop_total',np.full(len(faces),4,dtype=np.int32));mm.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool));mm.materials.append(portable)
 uv=mm.uv_layers.new(name='UVMap');vi=faces.ravel();uvco=np.stack([(vi//3%k)/(k-1),(vi%3)/3],1).astype(np.float32);uv.data.foreach_set('uv',uvco.ravel());mm.update()
 export=bpy.data.objects.new('AstraChar2_R4_Strands_'+label,mm);bpy.context.scene.collection.objects.link(export);bind(export,np.repeat(w,3,axis=0),names);export.hide_render=True;export.hide_set(True);export['gltf_export_hair']=True
 obj['groom_strands']=n;obj['groom_points_per_strand']=k;obj['chain']=chain
 print('GROOM',label,n,len(points),flush=True)
 return {'name':label,'curves':n,'points':len(points),'export_vertices':len(xyz),'chain':chain}

COLORS=[(.34,.19,.065),(.46,.285,.115),(.57,.385,.18),(.67,.49,.265)]
def groom():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_preround4.blend'));reset_pose();arm=bpy.data.objects['Armature'];o=bpy.data.objects['char1'];report={}
 for ob in list(bpy.data.objects):
  if ob.name.startswith('AstraChar2_R4_'):bpy.data.objects.remove(ob,do_unlink=True)
 # Retain old object names/slot lists, but remove their old cap/fiber geometry.
 retired=[]
 for ob in bpy.data.objects:
  if ob.type=='MESH' and (ob.name.startswith('AstraChar2_R2_Hair') or ob.name.startswith('AstraChar2_R3_Flow') or ob.name.startswith('AstraChar2_R3_Plait')):
   ob.data.clear_geometry();retired.append(ob.name)
 # The inherited dedicated hair slot contains the opaque head/long-hair shell.
 bm=bmesh.new();bm.from_mesh(o.data);shell=[f for f in bm.faces if f.material_index==3 or (f.material_index==4 and min(v.co.z for v in f.verts)>290)];report['removed_shell_faces']=sum(f.material_index==3 for f in shell);report['removed_misclassified_crown_fragments']=sum(f.material_index==4 for f in shell);bmesh.ops.delete(bm,geom=shell,context='FACES_ONLY');bm.to_mesh(o.data);bm.free();o.data.update();report['retired_groom_objects']=retired
 # Preserve the exact cached rest matrices required by the animation assembly.
 # glTF stores joint transforms, not Blender display tails. Correct physical
 # segment lengths/endpoints live in explicit per-bone spring metadata.
 bones=[]
 for bone in arm.data.bones:
  if not bone.name.startswith('phys_hair'):continue
  idx=int(bone.name[-2:]);head=arm.matrix_world@bone.head_local
  if idx<3:tail=arm.matrix_world@arm.data.bones[bone.name[:-2]+str(idx+1).zfill(2)].head_local
  else:tail=head+(arm.matrix_world.to_3x3()@(bone.tail_local-bone.head_local)).normalized()*(.6 if 'back' in bone.name else .4)
  length=(tail-head).length
  bone['spring_stiffness']=32.;bone['spring_damping']=7.;bone['spring_angular_limit_radians']=.52;bone['spring_collision_radius_m']=.015;bone['spring_segment_length_m']=length;bone['spring_rest_tail_world']=list(tail)
  bones.append({'name':bone.name,'blender_display_length_m':bone.length*.01,'physical_segment_length_m':length,'physical_tail_world':list(tail)})
 report['bone_lengths']=bones;report['native_display_tail_status']='Inherited oversized display tails retained to preserve exact animation rest matrices; physical lengths and endpoints are corrected in spring metadata and GLB node extras.'
 # Remove orphaned hair-bone influences from non-hair character surfaces. This
 # makes spring motion hair-only without changing other bone-weight ratios.
 hair_ids={g.index for g in o.vertex_groups if g.name.startswith('phys_hair')};used={i for f in o.data.polygons for i in f.vertices};cleaned=0
 for i in used:
  v=o.data.vertices[i];entries=[(g.group,g.weight) for g in v.groups];amount=sum(w for gi,w in entries if gi in hair_ids)
  if amount<1e-7:continue
  rest=[(gi,w) for gi,w in entries if gi not in hair_ids and w>1e-7];total=sum(w for gi,w in rest)
  for gi,w in entries:o.vertex_groups[gi].remove([i])
  if total:
   for gi,w in rest:o.vertex_groups[gi].add([i],w/total,'REPLACE')
  else:o.vertex_groups['Head' if v.co.z>275 else 'Spine02'].add([i],1,'REPLACE')
  cleaned+=1
 report['orphan_hair_influences_cleaned']=cleaned
 from mathutils.bvhtree import BVHTree
 evaluated=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 tree=BVHTree.FromPolygons([evaluated.matrix_world@v.co for v in evaluated.data.vertices],[tuple(f.vertices) for f in evaluated.data.polygons if f.material_index==2])
 ys=np.full((200,240),.5,np.float32)
 for zi,z in enumerate(np.linspace(2.88,3.22,200)):
  for xi,x in enumerate(np.linspace(-.18,.18,240)):
   hit,nn,fi,dd=tree.ray_cast(Vector((x,-.8,z)),Vector((0,1,0)),1.)
   if hit:ys[zi,xi]=hit.y
 def clear_scalp(p):
  mask=(p[:,2]>2.89)&(p[:,2]<3.215)&(abs(p[:,0])<.176)&(p[:,1]<-.27)
  xi=np.clip(((p[mask,0]+.18)/.36*239).astype(int),0,239);zi=np.clip(((p[mask,2]-2.88)/.34*199).astype(int),0,199);surface=ys[zi,xi]
  p[mask,1]=np.minimum(p[mask,1],surface-.004-rng.uniform(0,.003))
  return p
 # A smooth anatomical scalp below the roots, not a long hair shell.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,location=(0,-.235,3.005));scalp=bpy.context.object;scalp.name='AstraChar2_R4_Scalp';scalp.scale=(.117,.174,.145);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 scalp.parent=arm;scalp.matrix_parent_inverse=arm.matrix_world.inverted();vg=scalp.vertex_groups.new(name='Head');vg.add(list(range(len(scalp.data.vertices))),1,'REPLACE');am=scalp.modifiers.new('Head attachment','ARMATURE');am.object=arm
 sm=bpy.data.materials.new('AstraChar2 R4 scalp beneath roots');sm.use_nodes=True;bs=sm.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.08,.038,.017,1);bs.inputs['Roughness'].default_value=.64;scalp.data.materials.append(sm)
 for f in scalp.data.polygons:f.use_smooth=True
 # Close-cropped root underlay follows only the anatomical scalp beneath the
 # dense frontal roots; no long-hair silhouette or face-covering sheet.
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());vv=[];ff=[]
 for face in ev.data.polygons:
  if face.material_index!=2:continue
  coords=[ev.matrix_world@ev.data.vertices[i].co for i in face.vertices];center=sum(coords,Vector())/len(coords)
  threshold=float(np.interp(center.z,[3.02,3.06,3.10,3.14],[.105,.073,.042,0]))
  if not(3.02<center.z<3.19 and threshold<abs(center.x)<.125 and center.y<-.29):continue
  ff.append(tuple(range(len(vv),len(vv)+len(coords))));vv.extend([(v.x,v.y-.0008,v.z) for v in coords])
 mm=bpy.data.meshes.new('R4 anatomical frontal scalp beneath roots');mm.from_pydata(vv,[],ff);mm.materials.append(sm);under=bpy.data.objects.new('AstraChar2_R4_ScalpRoots',mm);bpy.context.scene.collection.objects.link(under)
 bind(under,np.ones((len(vv),1),np.float32),['Head'])
 for face in mm.polygons:face.use_smooth=True

 groups=[]
 for side,label in [(-1,'R'),(1,'L')]:
  for group in ['Front','Side','Back']:
   for color in range(2):
    paths=[];radii=[];count=1400 if group=='Front' else (900 if group=='Side' else 900);K=64
    for j in range(count):
     clump=j//10;cr=np.random.default_rng(1000+(side+1)*10000+['Front','Side','Back'].index(group)*1000+clump)
     y0=cr.uniform(-.430,-.255) if group=='Front' else (cr.uniform(-.255,-.12) if group=='Side' else cr.uniform(-.12,-.045))
     if group=='Front' and j%1400<480:y0=cr.uniform(-.431,-.410)
     z0=3.124+.060*math.sin((y0+.43)/.385*math.pi);end=cr.uniform(1.84,2.23);spread=cr.uniform(-.035,.050);phase=cr.uniform(0,math.tau);layer=cr.uniform(0,.015)
     front=group=='Front';yy=-.44 if front else (.035 if group=='Side' else .19)
     fline=smooth((-y0-.345)/.085) if front else 0
     P=[(side*.0005,y0,z0),(side*(.048-.028*fline),y0-.009,z0+.001+layer*.35),(side*(.108-.063*fline),y0+.005,z0-.018-.015*fline),(side*(.148-.063*fline),y0+.020,z0-.095),(side*(.168-.025*fline-(.032 if group=='Side' else 0)),(-.385 if front else (-.20 if group=='Side' else .06)),2.92),(side*((.185 if front else (.165 if group=='Side' else .22))+spread*.4),yy,2.68),(side*((.215 if front else .245)+spread),yy+(-.065 if front else .14),2.36),(side*(.25+spread),yy+(-.05 if front else .17),end)]
     p=interp(P,K);t=np.linspace(0,1,K)
     if group=='Back':p[:,0]*=1-(1-cr.uniform(.24,1))*smooth((3.0-p[:,2])/.3)
     start=rng.uniform(.02,.32) if j%3 else 0
     if start:p=np.stack([np.interp(np.linspace(start,1,K),t,p[:,dim]) for dim in range(3)],1)
     wave=(t**1.1)*.028*np.sin(t*math.tau*2.3+phase);p[:,0]+=side*wave;p[:,1]+=.021*t*np.sin(t*math.tau*2+phase)
     # Small coherent crown irregularity breaks the combed parallel rows.
     crown=smooth((p[:,2]-2.94)/.17)*np.sin(t*math.pi)
     p[:,2]+=.0055*crown*np.sin(t*math.tau*2.7+phase)
     p[:,0]+=side*.004*crown*np.sin(t*math.tau*1.8+phase)
     # Clustered strands with individual offsets, airy tips and sparse flyaways.
     off=rng.normal(0,.0022,3);off[2]*=.45;p+=off[None,:]*(.20+.8*np.sin(t*math.pi/2))[:,None]
     p[:,0]+=rng.uniform(.00025,.00085)*np.sin(t*math.tau*8+rng.uniform(0,math.tau))*np.sin(t*math.pi);p[:,1]+=rng.uniform(.00025,.0008)*np.sin(t*math.tau*7+rng.uniform(0,math.tau))*np.sin(t*math.pi)
     fly=j%23==0
     if fly:p[:,0]+=side*.017*np.sin(t*math.pi)*np.sin(t*math.tau*1.4+phase);p[:,1]-=.008*np.sin(t*math.pi)
     # Face clearance envelope: preserve the approved exposed forehead/cheeks.
     mask=(p[:,2]<3.08)&(p[:,2]>2.77)&(p[:,1]<-.25);p[mask,0]=side*np.maximum(abs(p[mask,0]),np.interp(p[mask,2],[2.77,2.93,3.0,3.08],[.135,.12,.104,.065])+rng.uniform(0,.0035))
     rad=rng.uniform(.000060,.000090)*(.45 if fly else 1)*(1-.92*smooth((t-.63)/.37));rad[:4]*=np.linspace(.45,1,4)
     if front:p=clear_scalp(p)
     paths.append(p);radii.append(rad)
    chain='front_'+label if group=='Front' else 'back';groups.append(build_group(label+'_'+group+'_'+str(color),paths,radii,chain,color+1))
  # Three thin plaits on each side, each made of three interwoven fiber bundles.
  paths=[];radii=[];K=256
  for braid in range(3):
   center=interp([(side*(.115+braid*.022),-.39+braid*.018,3.045-braid*.035),(side*(.135+braid*.018),-.40+braid*.025,2.92),(side*(.175+braid*.018),-.475+braid*.022,2.70),(side*(.205+braid*.022),-.54+braid*.022,2.42),(side*(.23+braid*.025),-.52+braid*.02,2.04-braid*.075)],K);t=np.linspace(0,1,K);turns=32+braid*2
   for bundle in range(3):
    for strand in range(48):
     ph=math.tau*bundle/3;phase=t*math.tau*turns+ph;rr=.0028*(1-.7*smooth((t-.84)/.16));off=rng.uniform(0,math.tau);orad=.00165*math.sqrt(rng.uniform());p=center.copy();p[:,0]+=rr*np.sin(phase)+orad*np.cos(off);p[:,1]+=.52*rr*np.sin(2*phase)+orad*np.sin(off)
     # Fine endings unwind instead of terminating in a flat braid cut.
     p[:,0]+=side*.009*smooth((t-.94)/.06)*np.sin(off);p[:,2]-=rng.uniform(0,.025)*smooth((t-.95)/.05)
     p=clear_scalp(p);paths.append(p);radii.append(rng.uniform(.000065,.000085)*(1-.94*smooth((t-.92)/.08)))
  groups.append(build_group(label+'_Braids',paths,radii,'front_'+label,1))
 report['groups']=groups;report['total_native_curves']=sum(g['curves'] for g in groups);report['native_points']=sum(g['points'] for g in groups);report['portable_vertices']=sum(g['export_vertices'] for g in groups)
 reset_pose();bpy.context.scene.frame_set(1);reset_pose();bpy.context.preferences.filepaths.save_version=0;bpy.context.scene['astra_char2_round4']='Native hair-curves groom; portable strand meshes hidden in native render';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));(OUT/'r4_groom.json').write_text(json.dumps(report,indent=2));print('SAVED',report['total_native_curves'],flush=True)
if __name__=='__main__':groom()
