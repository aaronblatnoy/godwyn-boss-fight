import bpy,sys,json,numpy as np,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'))
import astra_v3m_render as v
O=R/'renders/astra/v4p';O.mkdir(exist_ok=True)
protected=[R/'renders/astra/v4/candidate.blend',*sorted((R/'models').glob('astra_character_v3*'))]
(O/'protected.json').write_text(json.dumps({str(p.relative_to(R)):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in protected if p.is_file()},indent=2))
rep={}
for label,path,rname,oname in [('v4','renders/astra/v4/candidate.blend','Astra_V4_Rig','V4_Body'),('v3','models/astra_character_v3.blend','Astra_V3_Rig','AstraChar2_Meshy_HeadHair')]:
 bpy.ops.wm.open_mainfile(filepath=str(R/path));s=bpy.context.scene;rig=bpy.data.objects[rname];rig.data.pose_position='REST';bpy.context.view_layer.update();ob=bpy.data.objects[oname];pts=np.array([(ob.matrix_world@x.co)[:] for x in ob.data.vertices]);head=rig.matrix_world@rig.data.bones['Head'].head_local
 rep[label]={'head':list(head),'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'materials':[m.name for m in ob.data.materials],'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},'body_matrix':list(map(list,ob.matrix_world))}
 np.savez_compressed(O/(label+'_probe.npz'),points=pts,tri=np.array([list(f.vertices) for f in ob.data.polygons]))
 c=v.studio(s);v.configure(s,1000,1200,16);target=(0,-.45,2.9);v.set_camera(c,(0,-4.45,2.9),target,.6)
 # Lighting-independent flat-color landmarks, preserving source skin_i01 graph.
 for mat in ob.data.materials:
  nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');em=nt.nodes.new('ShaderNodeEmission');nt.links.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color']);nt.links.new(em.outputs[0],out.inputs['Surface'])
 v.render(s,O/(label+'_landmarks.png'))
(O/'probe.json').write_text(json.dumps(rep,indent=2));print('V4P_PROBE',json.dumps(rep),flush=True)
