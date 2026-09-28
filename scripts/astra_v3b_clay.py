import bpy,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3m_render as v
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate_r2.blend'));s=bpy.context.scene;rig=bpy.data.objects['Astra_V3_Rig'];v.assign_action(rig,bpy.data.actions['Combat_Stance'],1);body=bpy.data.objects['char1'];m=body.data.materials[0];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for link in list(bs.inputs['Normal'].links):m.node_tree.links.remove(link)
c=v.studio(s);v.configure(s,1200,1800,48);v.set_camera(c,(2.5,6.5,1.5),(0,0,1.4),3.4);v.render(s,O/'robe_no_normal.png')
for sock in ['Base Color','Metallic','Roughness']:
 for link in list(bs.inputs[sock].links):m.node_tree.links.remove(link)
bs.inputs['Base Color'].default_value=(.25,.3,.34,1);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.6
v.render(s,O/'robe_clay.png')
