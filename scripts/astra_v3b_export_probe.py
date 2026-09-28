import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(R/'renders/astra/v3b/candidate_final.blend'))
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 print('MESH',ob.name,'max_influences',max(len(v.groups) for v in ob.data.vertices),flush=True)
 for mat in ob.data.materials:
  print('MAT',mat.name,flush=True)
  for n in mat.node_tree.nodes:
   if n.type=='BSDF_PRINCIPLED':print('BSDF',n.name,[(i.name,[l.from_node.name for l in i.links]) for i in n.inputs if i.is_linked],flush=True)
   if n.type=='TEX_IMAGE' and n.image:print('TEX',n.name,n.image.name,list(n.image.size),n.image.colorspace_settings.name,flush=True)
print('OPTIONS',[(p.identifier,p.default) for p in bpy.ops.export_scene.gltf.get_rna_type().properties if 'influ' in p.identifier],flush=True)
