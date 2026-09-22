"""Native geometry and skinning utilities; no shader construction."""
import bpy,bmesh,math,numpy as np
from mathutils import Vector

def mesh(name,verts,faces,slots,index=0):
 old=bpy.data.objects.get(name)
 if old:
  assert old.type=='MESH';me=bpy.data.meshes.new(name+' clean topology');old.data=me;o=old
 else:
  me=bpy.data.meshes.new(name+' clean topology');o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o)
 me.from_pydata(verts,[],faces);me.update()
 for m in slots:me.materials.append(m)
 for f in me.polygons:f.material_index=index;f.use_smooth=True
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 return o

def bind(o,fn):
 arm=bpy.data.objects['Armature'];o.parent=arm;o.matrix_parent_inverse=arm.matrix_world.inverted()
 for mod in list(o.modifiers):o.modifiers.remove(mod)
 o.vertex_groups.clear()
 for g in bpy.data.objects['char1'].vertex_groups:o.vertex_groups.new(name=g.name)
 batches={}
 for v in o.data.vertices:
  for name,weight in fn(o.matrix_world@v.co).items():
   val=round(weight*1024)
   if val:batches.setdefault((name,val),[]).append(v.index)
 for (name,val),ids in batches.items():o.vertex_groups[name].add(ids,val/1024,'REPLACE')
 am=o.modifiers.new('Existing 121-bone skin','ARMATURE');am.object=arm
 return o

def torso_weights(p):
 keys=[(2.05,'Spine02'),(2.294,'Spine01'),(2.538,'Spine')]
 if p.z<=keys[0][0]:return {keys[0][1]:1}
 for (z0,n0),(z1,n1) in zip(keys,keys[1:]):
  if p.z<=z1:
   t=(p.z-z0)/(z1-z0);return {n0:1-t,n1:t}
 return {'Spine':1}

def head_weights(p):
 if p.z>=2.79:return {'Head':1}
 if p.z>=2.72:
  t=(p.z-2.72)/.07;return {'neck':1-t,'Head':t}
 t=max(0,min(1,(p.z-2.64)/.08));return {'Spine':1-t,'neck':t}

def solidify(o,thickness=.004):
 bpy.context.view_layer.objects.active=o;o.hide_set(False);o.select_set(True)
 mod=o.modifiers.new('Closed plate thickness','SOLIDIFY');mod.thickness=thickness;mod.offset=-1
 bpy.ops.object.modifier_apply(modifier=mod.name)
 return o

def sphere(name,location,scale,slots,index=0,segments=64,rings=32):
 old=bpy.data.objects.get(name);bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=location);o=bpy.context.object
 o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if old:
  me=o.data;bpy.data.objects.remove(o,do_unlink=True);old.data=me;o=old;o.matrix_world.identity();o.location=location
 else:o.name=name
 for m in slots:o.data.materials.append(m)
 for f in o.data.polygons:f.material_index=index;f.use_smooth=True
 return o

def tube(name,points,radius,slots,index=0,sides=8):
 p=np.array(points,float);t=np.gradient(p,axis=0);t/=np.maximum(np.linalg.norm(t,axis=1,keepdims=True),1e-8);a=np.cross(t,[0,1,0]);a/=np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-8);b=np.cross(t,a);angles=np.arange(sides)*math.tau/sides
 rr=np.broadcast_to(np.array(radius),len(p));v=p[:,None,:]+rr[:,None,None]*(a[:,None,:]*np.cos(angles)[None,:,None]+b[:,None,:]*np.sin(angles)[None,:,None]);f=[]
 for i in range(len(p)-1):
  for j in range(sides):f.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
 f.extend([tuple(reversed(range(sides))),tuple((len(p)-1)*sides+j for j in range(sides))]);return mesh(name,v.reshape(-1,3).tolist(),f,slots,index)
