import bpy, json, os, hashlib, numpy as np
from pathlib import Path
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight')
OUT=ROOT/'renders/astra/character'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.gltf(filepath=str(ROOT/'models/godwyn_game.glb'))
report={'source_sha256':hashlib.sha256((ROOT/'models/godwyn_game.glb').read_bytes()).hexdigest(),'objects':[], 'images':[], 'materials':[], 'bones':[]}
for o in bpy.context.scene.objects:
 d={'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'dimensions':list(o.dimensions)}
 if o.type=='MESH':
  d.update(vertices=len(o.data.vertices),faces=len(o.data.polygons),materials=[m.name for m in o.data.materials],uvs=[u.name for u in o.data.uv_layers],groups=[g.name for g in o.vertex_groups])
  p=np.array([v.co[:] for v in o.data.vertices]);d['local_min']=p.min(0).tolist();d['local_max']=p.max(0).tolist()
 report['objects'].append(d)
for m in bpy.data.materials:
 report['materials'].append({'name':m.name,'nodes':[{'name':n.name,'type':n.type,'image':getattr(getattr(n,'image',None),'name',None),'inputs':{s.name:list(s.default_value) if hasattr(s.default_value,'__len__') else s.default_value for s in n.inputs if hasattr(s,'default_value') and s.type in ['VALUE','RGBA']}} for n in m.node_tree.nodes], 'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]})
for im in bpy.data.images:
 if im.type=='RENDER_RESULT':continue
 a=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],4)
 report['images'].append({'name':im.name,'size':list(im.size),'colorspace':im.colorspace_settings.name,'std':a[:,:,:3].std((0,1)).tolist(),'neighbor_difference':float(np.abs(a[1:,:,:3]-a[:-1,:,:3]).mean()),'filepath':im.filepath})
 im.filepath_raw=str(OUT/('source_'+str(len(report['images']))+'.png'));im.file_format='PNG';im.save()
arm=bpy.data.objects['Armature']
for b in arm.data.bones:report['bones'].append({'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)})
obj=bpy.data.objects['char1']
np.savez_compressed(OUT/'source_mesh.npz',positions=np.array([v.co[:] for v in obj.data.vertices]),normals=np.array([v.normal[:] for v in obj.data.vertices]),triangles=np.array([p.vertices[:] for p in obj.data.polygons]),weights=np.array([[next((g.weight for g in v.groups if g.group==i),0) for i in range(len(obj.vertex_groups))] for v in obj.data.vertices],dtype=np.float32),uv=np.array([u.uv[:] for u in obj.data.uv_layers.active.data]),material=np.array([p.material_index for p in obj.data.polygons]))
(OUT/'source_inspection.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
print(json.dumps({k:report[k] for k in ['objects','images','bones']},indent=2))
