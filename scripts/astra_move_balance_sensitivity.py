"""Sword-mass sensitivity using the same evaluated COM and planted boot hull."""
import json,math,sys
from pathlib import Path
out=Path(__file__).resolve().parents[1]/'renders/astra/moves';name=sys.argv[1]
a=json.loads((out/f'{name}_metrics.json').read_text());rows=json.loads((out/f'{name}_samples.json').read_text())[::4]
def hull(points):
    pts=sorted(set(map(tuple,points)))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];hi=[]
    for seq,part in [(pts,lo),(pts[::-1],hi)]:
        for p in seq:
            while len(part)>1 and cross(part[-2],part[-1],p)<=0:part.pop()
            part.append(p)
    return lo[:-1]+hi[:-1]
def margin(p,poly):return min(((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))/max(1e-9,math.dist(a,b)) for a,b in zip(poly,poly[1:]+poly[:1]))-.02
result={'assumption':'Sword mass is 2, 4, or 6 percent of body mass; sword COM is 45 percent from hilt to tip. Kinematic sensitivity only.','cases':{}}
for ratio in [.02,.04,.06]:
    checked=[]
    for row,bal,blade in zip(rows,a['balance'],a['blade']):
        points=[]
        for side in bal['feet']:
            f=row['bones'][side+'Foot']['h'][:2];t=row['bones'][side+'ToeBase']['h'][:2];d=math.dist(f,t);axis=[(t[i]-f[i])/d for i in range(2)];lat=[-axis[1],axis[0]]
            for origin,length in [(f,-.12),(t,.09)]:
                for sign in [-1,1]:points.append([origin[i]+length*axis[i]+sign*.10*lat[i] for i in range(2)])
        sword=[.55*x+.45*y for x,y in zip(blade['grip'],blade['tip'])];com=[(x+ratio*y)/(1+ratio) for x,y in zip(bal['com'],sword)]
        checked.append({'frame':bal['frame'],'margin_m':margin(com[:2],hull(points)) if points else None})
    result['cases'][str(ratio)]={'minimum_margin_m':min(x['margin_m'] for x in checked if x['margin_m'] is not None),'outside_frames':[x['frame'] for x in checked if x['margin_m'] is not None and x['margin_m']<0],'rows':checked}
(out/f'{name}_sword_mass_sensitivity.json').write_text(json.dumps(result,indent=2));print(name,{k:{kk:vv for kk,vv in v.items() if kk!='rows'} for k,v in result['cases'].items()})
