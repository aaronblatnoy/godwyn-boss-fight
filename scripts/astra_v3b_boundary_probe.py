from pathlib import Path
from collections import defaultdict,deque
import numpy as np,json
R=Path(__file__).resolve().parents[1];O=R/'renders/astra/v3b';d=np.load(O/'raw_probe.npz');p=d['points'];f=d['faces'];_,rep,ids=np.unique(np.round(p,6),axis=0,return_index=True,return_inverse=True);q=p[rep];ff=ids[f];edges=np.sort(np.concatenate([ff[:,[0,1]],ff[:,[1,2]],ff[:,[2,0]]]),axis=1);edge,counts=np.unique(edges,axis=0,return_counts=True);adj=defaultdict(set)
for a,b in edge[counts==1]:adj[int(a)].add(int(b));adj[int(b)].add(int(a))
unseen=set(adj);rows=[];loops=[]
while unseen:
 seed=unseen.pop();seen={seed};queue=[seed]
 while queue:
  a=queue.pop()
  for b in adj[a]:
   if b in unseen:unseen.remove(b);seen.add(b);queue.append(b)
 pts=q[list(seen)];rows.append({'n':len(seen),'center':pts.mean(0).tolist(),'diagonal':float(np.linalg.norm(np.ptp(pts,axis=0))),'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'closed':all(len(adj[i])==2 for i in seen)})
 loops.append([int(rep[i]) for i in seen])
r={'boundary_edges':int((counts==1).sum()),'components':rows,'raw_vertex_ids':loops};(O/'boundary_probe.json').write_text(json.dumps(r,indent=2));print('V3B_BOUNDARY',json.dumps({'boundary_edges':r['boundary_edges'],'count':len(rows),'robe':[x for x in rows if .15<x['center'][2]<1.5 and x['center'][1]>-.1][:35]},indent=2))
