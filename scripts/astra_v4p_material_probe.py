import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';bpy.ops.wm.open_mainfile(filepath=str(R/'renders/astra/v4p/candidate.blend'));out={}
for ob in [bpy.data.objects['V4_Body'],bpy.data.objects['Godwyn_Sword']]:
 out[ob.name]={'uvs':[u.name for u in ob.data.uv_layers],'materials':[]}
 for mat in ob.data.materials:
  bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');out[ob.name]['materials'].append({'name':mat.name,'images':[(n.image.name,list(n.image.size)) for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image],'channels':{n.name:[(l.from_node.type,l.from_socket.name) for l in n.links] if n.is_linked else str(n.default_value) for n in bs.inputs if n.name in ['Base Color','Normal','Metallic','Roughness','Emission Color']}})
print('V4P_MATERIALS',json.dumps(out),flush=True)
