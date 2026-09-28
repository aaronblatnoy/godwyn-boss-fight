import bpy,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3m_render as v
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate_final.blend'));v.OUT=O/'film';s=bpy.context.scene;rig=bpy.data.objects['Astra_V3_Rig'];rig.data.pose_position='POSE';c=v.studio(s);assets=[o for o in s.objects if o.type=='MESH' and not o.name.startswith('V3M_Render')];rep=v.film(s,c,rig,assets,'Combat_Stance',24,1);(O/'film.json').write_text(json.dumps(rep,indent=2))
