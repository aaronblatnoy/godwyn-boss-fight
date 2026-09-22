import bpy,sys,json,numpy as np
from mathutils import Vector
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2_prechar2.blend')
o=bpy.data.objects['char1'];me=o.data;mw=o.matrix_world
ims={}
for i in [2,3,4]:
 m=me.materials[i];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');im=bs.inputs['Base Color'].links[0].from_node.image;a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);ims[i]=a.reshape(im.size[1],im.size[0],4)
res=[]
for f in me.polygons:
 p=mw@f.center
 if p.z>2.78 and p.y<-.32 and abs(p.x)<.135:
  uv=sum((me.uv_layers.active.data[i].uv for i in f.loop_indices),Vector((0,0)))/len(f.loop_indices)
  if f.material_index not in ims:continue
  a=ims[f.material_index];col=a[min(len(a)-1,int(uv.y*len(a))),min(a.shape[1]-1,int(uv.x*a.shape[1])),:3]
  res.append({'i':f.index,'p':list(p),'mat':f.material_index,'rgb':list(map(float,col))})
Path('/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/surface_samples.json').write_text(json.dumps(res))
