"""Texture-only donor projection. Temporary bake meshes never replace V4 geometry."""
import bpy,sys,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'))
import astra_v3_build as b
import astra_v3m_render as v
O=R/'renders/astra/v4p';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(R/'renders/astra/v4/candidate.blend'));s=bpy.context.scene;rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];rig.data.pose_position='REST';bpy.context.view_layer.update();v.enable_optix(s);s.cycles.samples=4;s.render.bake.margin=16

def geometry_hash(ob):
 h=hashlib.sha256()
 for coll,prop,n,dtype in [(ob.data.vertices,'co',3,np.float32),(ob.data.loops,'vertex_index',1,np.int32)]:
  a=np.empty(len(coll)*n,dtype);coll.foreach_get(prop,a);h.update(a.tobytes())
 return h.hexdigest()
original=geometry_hash(body)
def points(ob):return np.array([(ob.matrix_world@x.co)[:] for x in ob.data.vertices])
def image(name,noncolor=False):
 im=bpy.data.images.new('V4P_'+name,2048,2048,alpha=False,float_buffer=False);im.colorspace_settings.name='Non-Color' if noncolor else 'sRGB';return im
def save(im,name):
 im.filepath_raw=str(O/(name+'.png'));im.file_format='PNG';im.save();im.pack()
def pixels(im):
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);return a.reshape(im.size[1],im.size[0],4)
def target_node(ob,im):
 for mat in ob.data.materials:
  nt=mat.node_tree;node=nt.nodes.new('ShaderNodeTexImage');node.image=im;nt.nodes.active=node
 return node
def bake(target,im,typ='EMIT',source=None):
 bpy.ops.object.select_all(action='DESELECT');target.select_set(True);bpy.context.view_layer.objects.active=target;target_node(target,im)
 if source:source.select_set(True)
 s.render.bake.use_selected_to_active=bool(source);s.render.bake.cage_extrusion=.032;s.render.bake.max_ray_distance=.075
 bpy.ops.object.bake(type=typ);save(im,im.name)
def emit_channel(ob,channel):
 restore=[]
 for mat in ob.data.materials:
  nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output);old=out.inputs['Surface'].links[0].from_socket;em=nt.nodes.new('ShaderNodeEmission');feed=bs.inputs[channel]
  if feed.is_linked:nt.links.new(feed.links[0].from_socket,em.inputs[0])
  else:
   val=feed.default_value;em.inputs[0].default_value=tuple(val) if hasattr(val,'__len__') else (val,val,val,1)
  nt.links.new(em.outputs[0],out.inputs['Surface']);restore.append((nt,out,old,em))
 return restore
def restore(rows):
 for nt,out,old,em in rows:nt.links.new(old,out.inputs['Surface']);nt.nodes.remove(em)
# Append protected donor objects; pose is disabled for geometric landmark fitting.
with bpy.data.libraries.load(str(R/'models/astra_character_v3.blend'),link=False) as (av,dest):dest.objects=['AstraChar2_Meshy_HeadHair','Astra_V3_Rig']
for ob in dest.objects:s.collection.objects.link(ob)
donor=bpy.data.objects['AstraChar2_Meshy_HeadHair'];sr=bpy.data.objects['Astra_V3_Rig'];sr.data.pose_position='REST';bpy.context.view_layer.update()
# Bake skin_i01 graph to flat RGB before changing donor alignment.
flat=image('donor_skin_i01_flat');rows=emit_channel(donor,'Base Color');bake(donor,flat);restore(rows)
nt=donor.data.materials[0].node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');tex=nt.nodes.new('ShaderNodeTexImage');tex.image=flat;nt.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
P=points(body);Q=points(donor);skin=donor.data.color_attributes['meshy_skin_mask'];df=[tuple(f.vertices) for f in donor.data.polygons if np.mean([skin.data[i].color[0] for i in f.loop_indices])>.5];bt=BVHTree.FromPolygons(P.tolist(),[tuple(f.vertices) for f in body.data.polygons]);dt=BVHTree.FromPolygons(Q.tolist(),[tuple(f.vertices) for f in donor.data.polygons])
def landmark(tree,pixel):
 x=(pixel[0]-500)*.0005;z=2.9+(600-pixel[1])*.0005;hit=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
 assert hit[0] is not None,(pixel,x,z);return np.array(hit[0])
labels=['eye_image_left','eye_image_right','nose_tip','chin','ear_image_left','ear_image_right']
vp=[(386,562),(604,561),(495,719),(495,924),(224,474),(774,474)]
dp=[(575,364),(761,363),(668,476),(667,665)]
A=[landmark(dt,p) for p in dp];B=[landmark(bt,p) for p in vp]
# Donor ears are hair-occluded in the front view: nearest skin at anatomical lateral ear estimates.
for x in [-.030,.199]:A.append(np.array(dt.find_nearest(Vector((x,-.13,3.022)))[0]))
A=np.array(A);B=np.array(B);weights=np.array([1,1,1,.65,.2,.2]);weights/=weights.sum();am=(A*weights[:,None]).sum(0);bm=(B*weights[:,None]).sum(0);aa=A-am;bb=B-bm;u,d,vt=np.linalg.svd((aa*weights[:,None]).T@bb);rot=vt.T@u.T
if np.linalg.det(rot)<0:vt[-1]*=-1;rot=vt.T@u.T
scale=float(np.sum(weights*np.sum(bb*(aa@rot.T),axis=1))/np.sum(weights*np.sum(aa*aa,axis=1)));trans=bm-scale*rot@am;xf=Matrix.Identity(4)
for i in range(3):
 for j in range(3):xf[i][j]=scale*rot[i,j]
 xf[i][3]=trans[i]
aligned=A@(scale*rot).T+trans;res=np.linalg.norm(aligned-B,axis=1)
# Apply the rigid+uniform transform to a temporary donor only.
for mod in list(donor.modifiers):donor.modifiers.remove(mod)
donor.parent=None;donor.matrix_world=xf@donor.matrix_world
# Delete donor hair faces in temporary source after flattening the color-attribute graph.
import bmesh
bmsh=bmesh.new();bmsh.from_mesh(donor.data);bmsh.faces.ensure_lookup_table();remove=[f for f in bmsh.faces if np.mean([skin.data[i].color[0] for i in donor.data.polygons[f.index].loop_indices])<=.5 and not (abs(float(np.mean(Q[list(donor.data.polygons[f.index].vertices),0]))-.084)<.075 and 2.87<float(np.mean(Q[list(donor.data.polygons[f.index].vertices),2]))<3.09 and float(np.mean(Q[list(donor.data.polygons[f.index].vertices),1]))<-.23)];bmesh.ops.delete(bmsh,geom=remove,context='FACES');bmsh.to_mesh(donor.data);bmsh.free()
# Select continuous front skin, including eyes/brows/lips, with skin-colored ear/neck triangles.
tri=np.array([list(f.vertices) for f in body.data.polygons]);cent=P[tri].mean(1);uv0=np.array([d.uv[:] for d in body.data.uv_layers.active.data]);uvcent=uv0.reshape(-1,3,2).mean(1);im=b.image_array(bpy.data.images['V4 skin_mask']);sm=im[(uvcent[:,1]*2048).astype(int)%2048,(uvcent[:,0]*2048).astype(int)%2048,0]
core=(cent[:,2]>2.74)&(cent[:,2]<3.027)&(abs(cent[:,0])<.112)&(cent[:,1]<-.477)
sel=((sm>.16)&(cent[:,2]>2.68)&(cent[:,2]<3.04))|core
ids=np.where(sel)[0];loops=np.concatenate([np.array(body.data.polygons[int(i)].loop_indices) for i in ids]);verts=np.unique(tri[ids]);mapping={int(x):i for i,x in enumerate(verts)}
mesh=bpy.data.meshes.new('V4P temporary face atlas');mesh.from_pydata(P[verts].tolist(),[],[[mapping[int(x)] for x in tri[i]] for i in ids]);temp=bpy.data.objects.new('V4P temporary face bake',mesh);s.collection.objects.link(temp);mat=bpy.data.materials.new('V4P bake target');mat.use_nodes=True;mesh.materials.append(mat)
for f in mesh.polygons:f.use_smooth=True
uv=mesh.uv_layers.new(name='V4FaceUV');bpy.ops.object.select_all(action='DESELECT');temp.select_set(True);bpy.context.view_layer.objects.active=temp;bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
newuv=np.array([x.uv[:] for x in uv.data]);uvbody=body.data.uv_layers.new(name='V4FaceUV');uvbody.data.foreach_set('uv',uv0.ravel())
for i,li in enumerate(loops):uvbody.data[int(li)].uv=newuv[i]
body.data.uv_layers.active_index=0
# Bake original appearance and tangent normals onto the new atlas, then aligned donor.
images={}
for source,label in [(body,'original'),(donor,'projected')]:
 for channel,name in [('Base Color','base'),('Roughness','rough')]:
  rows=emit_channel(source,channel);im=image(label+'_'+name,name!='base');bake(temp,im,source=source);restore(rows);images[label+'_'+name]=im
 im=image(label+'_normal',True);bake(temp,im,'NORMAL',source);images[label+'_normal']=im
# Rasterize world-space mask with feathering at selected-face borders and donor hit coverage.
world=np.zeros((2048,2048,3),np.float32);coverage=np.zeros((2048,2048),bool)
for k,fi in enumerate(ids):
 a=newuv[k*3:k*3+3]*2048;lo=np.maximum(0,np.floor(a.min(0)).astype(int));hi=np.minimum(2047,np.ceil(a.max(0)).astype(int));xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5);p=np.stack([xx,yy],-1);e=a[1]-a[0];f=a[2]-a[0];den=e[0]*f[1]-e[1]*f[0]
 if abs(den)<1e-8:continue
 q=p-a[0];u=(q[:,:,0]*f[1]-q[:,:,1]*f[0])/den;vv=(e[0]*q[:,:,1]-e[1]*q[:,:,0])/den;ok=(u>=0)&(vv>=0)&(u+vv<=1);wp=P[tri[fi,0]]+(P[tri[fi,1]]-P[tri[fi,0]])*u[:,:,None]+(P[tri[fi,2]]-P[tri[fi,0]])*vv[:,:,None];tile=world[lo[1]:hi[1]+1,lo[0]:hi[0]+1];tile[ok]=wp[ok];coverage[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=ok
np.savez_compressed(O/'face_atlas_data.npz',world=world,coverage=coverage,face_ids=ids,original_uv=uv0)
# Feather with spatial fade near neck, hairline, and lateral edges. Projection validity rejects black ray misses.
x,y,z=world.transpose(2,0,1);alpha=np.clip((z-2.75)/.025,0,1)*np.clip((3.025-z)/.025,0,1)*np.clip((.145-abs(x))/.025,0,1)*np.clip((-.43-y)/.04,0,1);valid=(pixels(images['projected_base'])[:,:,:3].max(2)>.025);alpha*=coverage&valid
# Dilate colors/mask 16px so bilinear filtering at island edges never creates black seams.
for channel in ['base','rough','normal']:
 orig=pixels(images['original_'+channel]);proj=pixels(images['projected_'+channel]);out=orig.copy();out[:,:,:3]=orig[:,:,:3]*(1-alpha[:,:,None])+proj[:,:,:3]*alpha[:,:,None]
 if channel=='normal':
  n=out[:,:,:3]*2-1;n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-8);out[:,:,:3]=(n+1)/2
 mask=coverage.copy()
 for _ in range(16):
  for axis,step in [(0,1),(0,-1),(1,1),(1,-1)]:
   neighbor=np.roll(mask,step,axis);take=(~mask)&neighbor;out[take]=np.roll(out,step,axis)[take];mask|=take
 im=image('face_'+channel,channel!='base');im.pixels.foreach_set(out.ravel());save(im,im.name);images['face_'+channel]=im
face=bpy.data.materials.new('V4_Face');face.use_nodes=True;nt=face.node_tree;bs=nt.nodes.get('Principled BSDF');uvnode=nt.nodes.new('ShaderNodeUVMap');uvnode.uv_map='V4FaceUV'
for channel,socket in [('base','Base Color'),('rough','Roughness'),('normal','Normal')]:
 n=nt.nodes.new('ShaderNodeTexImage');n.image=images['face_'+channel];nt.links.new(uvnode.outputs[0],n.inputs['Vector'])
 if channel=='normal':nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='V4FaceUV';nt.links.new(n.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs[0],bs.inputs[socket])
 else:nt.links.new(n.outputs['Color'],bs.inputs[socket])
bs.inputs['Subsurface Weight'].default_value=.32;bs.inputs['Subsurface Radius'].default_value=(1,.35,.2);bs.inputs['Subsurface Scale'].default_value=.008
body.data.materials.append(face)
for i in ids:body.data.polygons[int(i)].material_index=1
# Explicit original UV graph prevents the new face layer from changing the body material.
nt=body.data.materials[0].node_tree;uvn=nt.nodes.new('ShaderNodeUVMap');uvn.uv_map=body.data.uv_layers[0].name
for node in nt.nodes:
 if node.type=='TEX_IMAGE' and not node.inputs['Vector'].is_linked:nt.links.new(uvn.outputs[0],node.inputs['Vector'])
for ob in [temp,donor,sr]:bpy.data.objects.remove(ob,do_unlink=True)
assert geometry_hash(body)==original
rep={'geometry_sha256':original,'body_geometry_unchanged':True,'face_triangles':len(ids),'face_atlas_size':[2048,2048],'new_uv':'V4FaceUV','landmarks':{name:{'donor':A[i].tolist(),'target':B[i].tolist(),'fitted':aligned[i].tolist(),'residual_mm':float(res[i]*1000),'weight':float(weights[i])} for i,name in enumerate(labels)},'ear_estimates':'Donor ears are hair-occluded; closest skin to lateral anatomical estimates, low fit weight 0.2. Other landmarks picked on unlit front views then ray cast.','scale':scale,'rotation':rot.tolist(),'translation_m':trans.tolist(),'residual_rms_mm':float(np.sqrt(np.mean(res**2))*1000),'bake':{'type':'selected-to-active EMIT base/roughness, tangent NORMAL','cage_extrusion_m':.032,'max_ray_distance_m':.075,'margin_px':16,'samples':4,'device':'OptiX'},'projected_coverage_fraction':float(np.mean(valid[coverage])),'alpha_mean':float(alpha[coverage].mean()),'source_recipe':'skin_i01 source shader flattened before projection; face SSS .32, radius 1/.35/.2, scale .008m; no double tint'}
(O/'face_build.json').write_text(json.dumps(rep,indent=2));rig.data.pose_position='POSE';v.assign_action(rig,bpy.data.actions['Combat_Stance'],1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'face_full.blend'));print('V4P_FACE',json.dumps(rep),flush=True)
