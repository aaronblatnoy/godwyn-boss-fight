import bpy,json,sys,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
source=root/'models/astra_xslash_v2_final_wip.blend'
source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
result={}
for o in bpy.context.scene.objects:
 if o.type!='MESH' or o.name.startswith('Astra_Stage'):continue
 for m in o.data.materials:
  if not m or m.name in result:continue
  nodes=[]
  for n in m.node_tree.nodes if m.node_tree else []:
   inputs={}
   for s in n.inputs:
    if hasattr(s,'default_value'):
     v=s.default_value
     if not isinstance(v,(int,float,bool,str)): 
      try:v=list(v)
      except:v=str(v)
     inputs[s.name]={'value':v,'links':[(l.from_node.name,l.from_socket.name) for l in s.links]}
   nodes.append({'name':n.name,'type':n.type,'inputs':inputs,'image':n.image.name if hasattr(n,'image') and n.image else None,'image_size':list(n.image.size) if hasattr(n,'image') and n.image else None})
  result[m.name]={'first_object':o.name,'nodes':nodes}
(root/'renders/astra/cine/gate3_material_audit.json').write_text(json.dumps({'source_sha256':source_hash,'materials':result},indent=2))
for name,r in result.items():
 print(name,r['first_object'])
 for n in r['nodes']:
  if n['type'] in ['BSDF_PRINCIPLED','EMISSION','NORMAL_MAP','BUMP','TEX_IMAGE']:
   print(json.dumps(n))
