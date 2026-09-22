"""Native curves, skin-point controls, and individual skinned glTF fibers. No shader work."""
import bpy,math,numpy as np
def smooth(a):return np.clip(a,0,1)**2*(3-2*np.clip(a,0,1))

def interp(P,count):
 P=np.array(P,float);t=np.linspace(0,len(P)-1,count);i=np.minimum(t.astype(int),len(P)-2);u=(t-i)[:,None];a=P[np.maximum(0,i-1)];b=P[i];c=P[i+1];d=P[np.minimum(len(P)-1,i+2)]
 return .5*((2*b)+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u**3)

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
 paths=np.asarray(paths,np.float32);radii=np.asarray(radii,np.float32);n,k,_=paths.shape;native_k=k;points=paths.reshape(-1,3);rr=radii.reshape(-1);w,names=weights(points,chain)
 native=next(m for m in bpy.data.materials if m.name.startswith('AstraChar2 R4 Native blonde'))
 portable=next(m for m in bpy.data.materials if m.name.startswith('AstraChar2 R4 Portable blonde'))
 # One control vertex for every native curve point. Armature modifier drives both.
 me=bpy.data.meshes.new('R5 '+label+' control points');me.vertices.add(len(points));me.vertices.foreach_set('co',points.ravel());proxy=bpy.data.objects.new('AstraChar2_R5_Control_'+label,me);bpy.context.scene.collection.objects.link(proxy);bind(proxy,w,names);proxy.hide_render=True;proxy.hide_set(True)
 cu=bpy.data.hair_curves.new('R5 '+label+' native hair');cu.add_curves([k]*n);cu.position_data.foreach_set('vector',points.ravel());cu.set_types(type='CATMULL_ROM');rad=cu.attributes.new('radius','FLOAT','POINT');rad.data.foreach_set('value',rr);cu.materials.append(native)
 obj=bpy.data.objects.new('AstraChar2_R5_Curves_'+label,cu);bpy.context.scene.collection.objects.link(obj);obj.parent=bpy.data.objects['Armature'];obj.matrix_parent_inverse=obj.parent.matrix_world.inverted()
 ng=bpy.data.node_groups.new('R5 '+label+' skinned curve points','GeometryNodeTree');ng.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');ng.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry');ns=ng.nodes;ls=ng.links
 inp=ns.new('NodeGroupInput');out=ns.new('NodeGroupOutput');info=ns.new('GeometryNodeObjectInfo');info.transform_space='RELATIVE';info.inputs['Object'].default_value=proxy;info.inputs['As Instance'].default_value=False
 pos=ns.new('GeometryNodeInputPosition');idx=ns.new('GeometryNodeInputIndex');sample=ns.new('GeometryNodeSampleIndex');sample.data_type='FLOAT_VECTOR';sample.domain='POINT';setp=ns.new('GeometryNodeSetPosition');ls.new(info.outputs['Geometry'],sample.inputs['Geometry']);ls.new(pos.outputs['Position'],sample.inputs['Value']);ls.new(idx.outputs['Index'],sample.inputs['Index']);ls.new(inp.outputs['Geometry'],setp.inputs['Geometry']);ls.new(sample.outputs['Value'],setp.inputs['Position']);ls.new(setp.outputs['Geometry'],out.inputs['Geometry']);mod=obj.modifiers.new('Hair curves follow skinned controls','NODES');mod.node_group=ng
 # Same paths and taper, represented as microscopic triangular tubes for standard glTF.
 export_index=np.unique(np.r_[np.arange(0,k,2),k-1]);paths=paths[:,export_index];radii=radii[:,export_index];k=len(export_index);w,names=weights(paths.reshape(-1,3),chain)
 tangent=np.gradient(paths,axis=1);tangent/=np.maximum(np.linalg.norm(tangent,axis=2,keepdims=True),1e-8);axis=np.cross(tangent,np.array([0,1,0]));axis/=np.maximum(np.linalg.norm(axis,axis=2,keepdims=True),1e-8);other=np.cross(tangent,axis);angle=np.arange(3)*math.tau/3
 xyz=paths[:,:,None,:]+radii[:,:,None,None]*(axis[:,:,None,:]*np.cos(angle)[None,None,:,None]+other[:,:,None,:]*np.sin(angle)[None,None,:,None]);xyz=xyz.reshape(-1,3)
 base=(np.arange(n)[:,None,None]*k*3+np.arange(k-1)[None,:,None]*3+np.arange(3)[None,None,:]);nxt=base-base%3+(base%3+1)%3;faces=np.stack([base,nxt,nxt+3,base+3],-1).reshape(-1,4).astype(np.int32)
 mm=bpy.data.meshes.new('R5 '+label+' portable individual strands');mm.vertices.add(len(xyz));mm.vertices.foreach_set('co',xyz.ravel());mm.loops.add(faces.size);mm.loops.foreach_set('vertex_index',faces.ravel());mm.polygons.add(len(faces));mm.polygons.foreach_set('loop_start',np.arange(len(faces),dtype=np.int32)*4);mm.polygons.foreach_set('loop_total',np.full(len(faces),4,dtype=np.int32));mm.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool));mm.materials.append(portable)
 uv=mm.uv_layers.new(name='UVMap');vi=faces.ravel();uvco=np.stack([(vi//3%k)/(k-1),(vi%3)/3],1).astype(np.float32);uv.data.foreach_set('uv',uvco.ravel());mm.update()
 export=bpy.data.objects.new('AstraChar2_R5_Strands_'+label,mm);bpy.context.scene.collection.objects.link(export);bind(export,np.repeat(w,3,axis=0),names);export.hide_render=True;export.hide_set(True);export['gltf_export_hair']=True
 obj['groom_strands']=n;obj['groom_points_per_strand']=native_k;obj['export_points_per_strand']=k;obj['chain']=chain
 print('GROOM',label,n,len(points),flush=True)
 return {'name':label,'curves':n,'points':len(points),'export_vertices':len(xyz),'chain':chain}
