"""Secondary lag relative to the actual attachment: robe/hips, cape/spine."""
import json,math,sys
from pathlib import Path
out=Path(__file__).resolve().parents[1]/'renders/astra/moves';name=sys.argv[1];rows=json.loads((out/f'{name}_samples.json').read_text())[::4]
def mul(q,p):
 w,x,y,z=q;a,b,c,d=p;return [w*a-x*b-y*c-z*d,w*b+x*a+y*d-z*c,w*c-x*d+y*a+z*b,w*d+x*c-y*b+z*a]
def inv(q):return [q[0],-q[1],-q[2],-q[3]]
def yaw(q):
 w,x,y,z=q;return math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)))
def vel(n):
 result=[]
 for a,b in zip(rows,rows[1:]):
  dq=mul(b['bones'][n]['wq'],inv(a['bones'][n]['wq']))
  if dq[0]<0:dq=[-x for x in dq]
  s=math.sqrt(sum(x*x for x in dq[1:]));result.append(math.degrees(2*math.atan2(s,dq[0]))*dq[3]/s if s>1e-9 else 0)
 return result
result={}
for child,parent in [('phys_robe_front_C_06','Hips'),('phys_cape_C_06','Spine')]:
 a=vel(parent);b=vel(child);correlations={}
 for lag in range(-10,21):
  x=a[max(0,-lag):min(len(a),len(a)-lag)];y=b[max(0,lag):min(len(b),len(b)+lag)];mx=sum(x)/len(x);my=sum(y)/len(y);vx=sum((v-mx)**2 for v in x);vy=sum((v-my)**2 for v in y)
  if vx*vy>1e-12:correlations[lag]=sum((u-mx)*(v-my) for u,v in zip(x,y))/math.sqrt(vx*vy)
 offsets=[]
 for r in rows:
  dy=yaw(mul(r['bones'][parent]['wq'],inv(rows[0]['bones'][parent]['wq'])))-yaw(mul(r['bones'][child]['wq'],inv(rows[0]['bones'][child]['wq'])))
  offsets.append({'frame':r['frame'],'trailing_yaw_deg':(dy+180)%360-180})
 result[child]={'attachment':parent,'best_delay_frames':max(correlations,key=correlations.get),'correlations':correlations,'trailing_offset_range_deg':[min(x['trailing_yaw_deg'] for x in offsets),max(x['trailing_yaw_deg'] for x in offsets)],'end_offset_deg':offsets[-1]['trailing_yaw_deg'],'rows':offsets}
(out/f'{name}_secondary_attachment_audit.json').write_text(json.dumps(result,indent=2));print({k:{kk:vv for kk,vv in v.items() if kk not in ['rows','correlations']} for k,v in result.items()})
