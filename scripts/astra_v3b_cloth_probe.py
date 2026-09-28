from pathlib import Path
import json,numpy as np
from collections import defaultdict
R=Path(__file__).resolve().parents[1];O=R/'renders/astra/v3b';d=np.load(O/'raw_probe.npz');w=np.load(O/'weights.npz');p=d['points'];faces=d['faces'];groups=defaultdict(list)
# Connectivity across UV seams with 10-micron geometric equivalence.
_,ids=np.unique(np.round(p,5),axis=0,return_inverse=True);parent=np.arange(ids.max()+1)
def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
for a,b,c in ids[faces]:
 ra,rb,rc=find(a),find(b),find(c);parent[rb]=ra;parent[rc]=ra
for i,x in enumerate(ids):groups[find(x)].append(i)
rows=[]
for vs in sorted(groups.values(),key=len,reverse=True):
 q=p[vs];mean=w['weights'][vs].mean(0);rows.append({'vertices':len(vs),'bounds':[q.min(0).tolist(),q.max(0).tolist()],'mean':q.mean(0).tolist(),'weights':{str(w['names'][j]):float(v) for j,v in enumerate(mean) if v>.01}})
(O/'cloth_components.json').write_text(json.dumps({'component_count':len(rows),'components':rows},indent=2));print(json.dumps({'component_count':len(rows),'largest':rows[:30]},indent=2))
