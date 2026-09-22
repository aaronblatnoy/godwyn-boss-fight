"""Numerical acceptance evidence from the baked animation's sampled transforms."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra'
m=json.loads((OUT/'metrics.json').read_text());s={x['frame']:x for x in m['samples']}
def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def intersect(a,b,c,d):
 ux,uz=b[0]-a[0],b[2]-a[2];vx,vz=d[0]-c[0],d[2]-c[2];den=ux*vz-uz*vx
 if abs(den)<1e-9:return None
 t=((c[0]-a[0])*vz-(c[2]-a[2])*vx)/den;v=((c[0]-a[0])*uz-(c[2]-a[2])*ux)/den
 if 0<=t<=1 and 0<=v<=1:return ([a[k]+t*(b[k]-a[k]) for k in range(3)],[c[k]+v*(d[k]-c[k]) for k in range(3)])
hits=[]
for i in range(13,23):
 for j in range(36,46):
  h=intersect(s[i]['tip'],s[i+1]['tip'],s[j]['tip'],s[j+1]['tip'])
  if h:hits.append({'cut1_frame_interval':[i,i+1],'cut2_frame_interval':[j,j+1],'points_world':h,'depth_difference_m':abs(h[0][1]-h[1][1])})
foot_drift={side:max(dist(s[f]['feet'][side],s[11]['feet'][side]) for f in range(11,62)) for side in ['Left','Right']}
toe_yaw={side:max(abs(math.degrees(math.atan2(s[f]['toes'][side][0]-s[f]['feet'][side][0],-(s[f]['toes'][side][1]-s[f]['feet'][side][1])))) for f in range(1,62)) for side in ['Left','Right']}
report={'duration_s':m['duration_seconds'],'cut1_tip_delta_xz':[s[23]['tip'][k]-s[13]['tip'][k] for k in [0,2]],'cut2_tip_delta_xz':[s[46]['tip'][k]-s[36]['tip'][k] for k in [0,2]],'crossings':hits,'max_hips_yaw_deg_s':m['max_hips_yaw_deg_s'],'planted_foot_drift_m':foot_drift,'max_toe_yaw_from_forward_deg':toe_yaw,'step_forward_m':s[1]['feet']['Left'][1]-s[11]['feet']['Left'][1],'torso_prelead_degrees':[s[12]['torso_yaw']-s[9]['torso_yaw'],s[36]['torso_yaw']-s[33]['torso_yaw']],'blade_tip_movement_during_prelead_m':[dist(s[9]['tip'],s[12]['tip']),dist(s[33]['tip'],s[36]['tip'])],'max_wrist_target_error_m':m['max_wrist_reach_error']}
assert len(hits)>0
assert report['max_hips_yaw_deg_s']<360
assert max(foot_drift.values())<.001
assert max(toe_yaw.values())<1
assert report['cut1_tip_delta_xz'][0]>1 and report['cut1_tip_delta_xz'][1]<-1
assert report['cut2_tip_delta_xz'][0]<-1 and report['cut2_tip_delta_xz'][1]<-1
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
