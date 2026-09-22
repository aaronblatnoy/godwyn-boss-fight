import bpy,sys,json,shutil,collections,numpy as np,bmesh
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
for ext in ['blend','glb']:
 src=ROOT/f'models/astra_character_v2.{ext}';dst=ROOT/f'models/astra_character_v2_preround3.{ext}'
 if not dst.exists():shutil.copy2(src,dst)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_preround3.blend'))
r={'objects':[],'materials':{},'hair_bones':[]}
for o in bpy.data.objects:
 if o.type!='MESH':continue
 d={'name':o.name,'verts':len(o.data.vertices),'polys':len(o.data.polygons),'materials':[m.name for m in o.data.materials],'modifiers':[(m.name,m.type) for m in o.modifiers]}
 if o.name=='char1':
  bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();comps=[]
  for v in bm.verts:
   if v in seen:continue
   st=[v];seen.add(v);vv=[]
   while st:
    p=st.pop();vv.append(p)
    for e in p.link_edges:
     q=e.other_vert(p)
     if q not in seen:seen.add(q);st.append(q)
   faces={f for q in vv for f in q.link_faces}
   if faces:
    pos=np.array([o.matrix_world@q.co for q in vv]);comps.append({'verts':len(vv),'faces':len(faces),'mats':dict(collections.Counter(f.material_index for f in faces)),'min':pos.min(0).tolist(),'max':pos.max(0).tolist()})
  d['components']=sorted(comps,key=lambda c:c['faces'],reverse=True);d['boundary_edges']=sum(e.is_boundary for e in bm.edges);d['nonmanifold_edges']=sum(not e.is_manifold for e in bm.edges);d['degenerate_faces']=sum(f.calc_area()<1e-10 for f in bm.faces);d['custom_normals']=o.data.has_custom_normals;bm.free()
 r['objects'].append(d)
for m in bpy.data.materials:
 if not m.use_nodes or not m.users:continue
 r['materials'][m.name]={'nodes':[{'name':n.name,'type':n.type,'image':n.image.name if n.type=='TEX_IMAGE' and n.image else None,'image_size':list(n.image.size) if n.type=='TEX_IMAGE' and n.image else None,'inputs':{i.name:list(i.default_value) if hasattr(i.default_value,'__len__') and not isinstance(i.default_value,str) else i.default_value for i in n.inputs if hasattr(i,'default_value') and not i.is_linked}} for n in m.node_tree.nodes],'links':[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in m.node_tree.links]}
arm=bpy.data.objects['Armature'];r['hair_bones']=[{'name':b.name,'head':list(arm.matrix_world@b.head_local),'tail':list(arm.matrix_world@b.tail_local)} for b in arm.data.bones if 'hair' in b.name.lower()]
(OUT/'r3_recon.json').write_text(json.dumps(r,indent=2));print('HAIR BONES',r['hair_bones']);print('CHAR TOPOLOGY',json.dumps(next(x for x in r['objects'] if x['name']=='char1')))
