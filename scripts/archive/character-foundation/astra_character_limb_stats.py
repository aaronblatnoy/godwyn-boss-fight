import numpy as np,json
from pathlib import Path
P=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/character')
d=np.load(P/'source_mesh.npz');p=d['positions'];w=d['weights'];n=json.loads((P/'source_inspection.json').read_text())['objects'][1]['groups']
for side in ['Right','Left']:
 for part in ['Arm','ForeArm','Hand']:
  q=p[w[:,n.index(side+part)]>.6];print(side+part,len(q),np.quantile(q,[.05,.25,.5,.75,.95],axis=0).round(1).tolist(),flush=True)
 for lo in range(140,280,15):
  mask=(p[:,2]>lo)&(p[:,2]<lo+15)&(p[:,0]<-30 if side=='Right' else p[:,0]>30)&(p[:,1]<-10)
  q=p[mask];print('SLICE',side,lo,len(q),np.quantile(q,[.1,.5,.9],axis=0).round(1).tolist(),flush=True)
