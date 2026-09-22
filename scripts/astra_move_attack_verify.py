"""Additional attack checks from evaluated skeleton/blade samples, stdlib only."""
import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'renders/astra/moves';name=sys.argv[1]
m=json.loads((out/f'{name}_manifest.json').read_text());a=json.loads((out/f'{name}_metrics.json').read_text());rs=json.loads((out/f'{name}_samples.json').read_text());g=json.loads((out/f'{name}_grip_metrics.json').read_text())
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def mul(q,p):
    w,x,y,z=q;a,b,c,d=p;return [w*a-x*b-y*c-z*d,w*b+x*a+y*d-z*c,w*c-x*d+y*a+z*b,w*d+x*c-y*b+z*a]
def inv(q):return [q[0],-q[1],-q[2],-q[3]]
def rot(q,p):return mul(mul(q,[0]+list(p)),inv(q))[1:]
ints=rs[::4];hip=[x['bones']['Hips']['h'] for x in ints]
report={'name':name,'hips_yaw_peak_deg_s':a['peak_hips_yaw_deg_s'],'airborne_frames':a['support_summary']['airborne_frames'],'end_root_velocity_m_s':[x*120 for x in sub(rs[-1]['bones']['Hips']['h'],rs[-2]['bones']['Hips']['h'])]}
if m.get('target_point'):
    delta=mul(ints[-1]['bones']['Hips']['wq'],inv(ints[0]['bones']['Hips']['wq']));forward=rot(delta,[0,-1,0]);to=sub(m['target_point'],hip[-1]);forward[2]=to[2]=0
    report['end_facing_vs_target_deg']=math.degrees(math.acos(max(-1,min(1,dot(forward,to)/norm(forward)/norm(to)))))
    report['end_blade_dot_forward']=dot(g['rows'][-1]['direction'],forward)/norm(forward)
    report['vertical_hip_acceleration_m_s2']=[{'frame':i+1,'az':(hip[i+1][2]-2*hip[i][2]+hip[i-1][2])*900} for i in range(m['flight'][0],m['flight'][1]-1)]
    report['max_ballistic_gravity_error_m_s2']=max(abs(x['az']+9.81) for x in report['vertical_hip_acceleration_m_s2'])
    assert report['end_facing_vs_target_deg']>135,report
    assert report['end_blade_dot_forward']<0,report
    assert norm(report['end_root_velocity_m_s'])>.1,report
if name=='rising_spin':
    assert report['hips_yaw_peak_deg_s']<=360.1,report
    start,end=m['body_turn_frames'];selected=[r for r in rs if start<=r['frame']<=end];base=selected[0]['bones']['Hips']['wq'];angles=[]
    for row in selected:
        w,x,y,z=mul(row['bones']['Hips']['wq'],inv(base));angles.append(math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))))
    report['measured_body_turn_degrees']=sum((b-a+180)%360-180 for a,b in zip(angles,angles[1:]));report['body_turn_duration_s']=(end-start)/30
    assert abs(report['measured_body_turn_degrees']-360)<.1,report
report['outside_support_events']=[]
for b in a['balance']:
    if b['margin_m'] is None or b['margin_m']>=0:continue
    future=next((x for x in a['balance'] if x['frame']>b['frame'] and x['margin_m'] is not None and x['margin_m']>=0),None)
    catch=min((i+1 for side in ['Left','Right'] if side not in b['feet'] for i in range(b['frame'],m['samples_end']) if m['planted'][side][i]),default=None)
    report['outside_support_events'].append({'frame':b['frame'],'margin_m':b['margin_m'],'next_supported_frame':future['frame'] if future else None,'next_additional_foot_contact':catch})
(out/f'{name}_attack_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
