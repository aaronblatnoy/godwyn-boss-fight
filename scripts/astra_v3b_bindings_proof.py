import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3m_render as v
O=R/'renders/astra/v3b';names=['AstraChar2_Meshy_HeadHair','AstraChar2_Meshy_NeckBlend','Godwyn_Sword'];states=[]
for filename in ['source_snapshot.blend','candidate_final.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(O/filename));rig=bpy.data.objects['Astra_V3_Rig'];a=bpy.data.actions['Combat_Stance'];d={n:[] for n in names}
 for frame in [0]+list(range(1,52)):
  rig.data.pose_position='REST' if frame==0 else 'POSE';v.assign_action(rig,a,max(1,frame));dg=bpy.context.evaluated_depsgraph_get()
  for n in names:
   ob=bpy.data.objects[n];e=ob.evaluated_get(dg);m=e.to_mesh();ids=np.linspace(0,len(m.vertices)-1,240,dtype=int);d[n].append(np.array([(e.matrix_world@m.vertices[int(i)].co)[:] for i in ids]));e.to_mesh_clear()
 states.append(d)
rep={n:{'rest_sample_max_difference_m':float(np.linalg.norm(states[0][n][0]-states[1][n][0],axis=1).max()),'posed_51_frames_sample_max_difference_m':float(np.linalg.norm(np.array(states[0][n][1:])-states[1][n][1:],axis=2).max())} for n in names};(O/'bindings_final.json').write_text(json.dumps(rep,indent=2));print('V3B_BINDINGS_PROOF',json.dumps(rep),flush=True)
