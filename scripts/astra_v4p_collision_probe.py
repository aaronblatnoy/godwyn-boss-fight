import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'));import astra_v3m_audit as a
O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];sword=bpy.data.objects['Godwyn_Sword'];names={g.index:g.name for g in body.vertex_groups};hv={v.index for v in body.data.vertices if sum(g.weight for g in v.groups if names[g.group]=='RightHand')>.5};faces=[f for f in body.data.polygons if not all(i in hv for i in f.vertices)];sf=[tuple(f.vertices) for f in sword.data.polygons];rows=[]
frames=[r['frame'] for r in json.loads((O/'sword_slash_r_audit.json').read_text())['rows'] if r['sword_non_grip_body_triangle_pairs']]
for frame in frames:
 a.assign(rig,bpy.data.actions['sword_slash_r'],frame);bp,_=a.evaluated(body);sp,_=a.evaluated(sword);pairs=a.tree(bp,[tuple(f.vertices) for f in faces]).overlap(a.tree(sp,sf));hits=[]
 for bi,si in pairs:
  f=faces[bi];weights={}
  for idx in f.vertices:
   for g in body.data.vertices[idx].groups:weights[names[g.group]]=weights.get(names[g.group],0)+g.weight/len(f.vertices)
  hits.append({'body_face':f.index,'center':bp[list(f.vertices)].mean(0).tolist(),'bone_weights':weights,'sword_face':si})
 rows.append({'frame':frame,'pairs':len(pairs),'hits':hits})
(O/'collision_probe.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows[:1],indent=2),flush=True)
