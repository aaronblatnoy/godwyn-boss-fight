import bpy,sys,json,shutil,collections
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from mathutils import Vector
src=ROOT/'models/astra_character_v2.blend';backup=ROOT/'models/astra_character_v2_prechar2.blend'
if not backup.exists():shutil.copy2(src,backup)
bpy.ops.wm.open_mainfile(filepath=str(backup))
def val(x):
 try:return list(x)
 except:return x if isinstance(x,(str,int,float,bool)) else str(x)
r={'objects':[],'materials':[],'images':[]}
for o in bpy.data.objects:
 d={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,'matrix_world':[list(x) for x in o.matrix_world],'modifiers':[{'name':m.name,'type':m.type} for m in o.modifiers]}
 if o.type=='MESH':
  me=o.data;pts=[o.matrix_world@v.co for v in me.vertices];d.update(vertices=len(me.vertices),edges=len(me.edges),polygons=len(me.polygons),polygon_sizes=dict(collections.Counter(len(f.vertices) for f in me.polygons)),bounds=[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(3)],materials=[m.name if m else None for m in me.materials],material_faces=dict(collections.Counter(f.material_index for f in me.polygons)),uv_layers=[{'name':u.name,'loops':len(u.data),'bounds':[[min(v.uv[i] for v in u.data),max(v.uv[i] for v in u.data)] for i in range(2)]} for u in me.uv_layers],vertex_groups=[{'name':g.name,'index':g.index} for g in o.vertex_groups])
  if o.name=='char1':
   ids={i for i,p in enumerate(pts) if p.z>2.78};faces=[f for f in me.polygons if all(i in ids for i in f.vertices)];d['head']={'vertices':len(ids),'polygons':len(faces),'bounds':[[min(pts[j][i] for j in ids),max(pts[j][i] for j in ids)] for i in range(3)],'material_faces':dict(collections.Counter(f.material_index for f in faces))}
   # World-space face sample for procedural registration.
   samples=[{'i':v.index,'p':list(pts[v.index]),'normal':list(v.normal),'groups':[(o.vertex_groups[g.group].name,g.weight) for g in v.groups]} for v in me.vertices if pts[v.index].z>2.8 and pts[v.index].y<-.1]
   (OUT/'head_samples.json').write_text(json.dumps(samples))
 if o.type=='ARMATURE':d['bones']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local)} for b in o.data.bones]
 r['objects'].append(d)
for m in bpy.data.materials:
 r['materials'].append({'name':m.name,'nodes':[{'name':n.name,'type':n.type,'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None,'inputs':{i.name:val(i.default_value) for i in n.inputs if hasattr(i,'default_value') and not i.is_linked}} for n in m.node_tree.nodes] if m.use_nodes else [],'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links] if m.use_nodes else []})
for i in bpy.data.images:r['images'].append({'name':i.name,'path':i.filepath,'size':list(i.size),'packed':bool(i.packed_file),'colorspace':i.colorspace_settings.name})
(OUT/'recon.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
