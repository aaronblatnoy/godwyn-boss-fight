import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'));import astra_v3m_retarget_world as w
O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];rows=[]
for clip in ['Combat_Stance','sword_slash_r']:
 for frame in range(1,int(bpy.data.actions[clip].frame_range[1])+1):
  w.assign(rig,bpy.data.actions[clip],frame);p=w.evaluated_points(body);idx=int(p[:,2].argmin());rows.append({'clip':clip,'frame':frame,'min_z':float(p[idx,2]),'vertex':idx,'rest':list(body.matrix_world@body.data.vertices[idx].co),'weights':{body.vertex_groups[g.group].name:g.weight for g in body.data.vertices[idx].groups}})
(O/'floor_probe.json').write_text(json.dumps(rows,indent=2));print('V4P_FLOOR',json.dumps(sorted(rows,key=lambda r:r['min_z'])[:4]),flush=True)
