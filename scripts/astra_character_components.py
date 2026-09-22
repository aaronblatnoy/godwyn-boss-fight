import bpy,sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
o=bpy.data.objects['char1'];p=np.array([v.co[:] for v in o.data.vertices]);parent=np.arange(len(p))
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for e in o.data.edges:
 a,b=(find(i) for i in e.vertices)
 if a!=b:parent[a]=b
roots=np.array([find(i) for i in range(len(p))]);unique,counts=np.unique(roots,return_counts=True);order=np.argsort(counts)[::-1];out=[]
for k in order[:80]:
 ids=np.where(roots==unique[k])[0];ps=p[ids];wg={}
 for i in ids:
  for g in o.data.vertices[i].groups:wg[o.vertex_groups[g.group].name]=wg.get(o.vertex_groups[g.group].name,0)+g.weight
 out.append({'root':int(unique[k]),'count':int(counts[k]),'min':ps.min(0).tolist(),'max':ps.max(0).tolist(),'weights':sorted(wg.items(),key=lambda x:-x[1])[:8]})
np.savez_compressed(OUT/'components.npz',roots=roots,positions=p)
(OUT/'components.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[:25],indent=2))
