"""Numerical diagnostics from sampled Blender action; no scene edits."""
import json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Quaternion, Vector
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
label=args[0] if args else 'before'
d=json.loads((ROOT/f'renders/astra/naturalness_{label}.json').read_text())
rr=d['rows'];rows=rr[::4];names=list(d['rest'])
def series(n,k,sub=False):return np.array([r['bones'][n][k] for r in (rr if sub else rows)])
def angle(a,b):return math.degrees(math.acos(np.clip(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1)))
def angular(n,k='q',sub=False):
    qs=series(n,k,sub);v=[]
    for a,b in zip(qs,qs[1:]):
        dq=Quaternion(b)@Quaternion(a).inverted();dq.normalize()
        if dq.w<0:dq.negate()
        xyz=np.array([dq.x,dq.y,dq.z]); mag=np.linalg.norm(xyz)
        v.append(xyz*(math.degrees(2*math.atan2(mag,dq.w))/mag if mag>1e-12 else 2*180/math.pi)*(4 if sub else 1))
    return np.array(v)
def hull(points):
    pts=sorted(set(map(tuple,points)))
    def cross(o,a,b):
        x=np.array(a)-o;y=np.array(b)-o;return float(x[0]*y[1]-x[1]*y[0])
    low=[]
    for p in pts:
        while len(low)>=2 and cross(low[-2],low[-1],p)<=0:low.pop()
        low.append(p)
    high=[]
    for p in reversed(pts):
        while len(high)>=2 and cross(high[-2],high[-1],p)<=0:high.pop()
        high.append(p)
    return low[:-1]+high[:-1]
def margin(p,poly):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        edge=np.array(b)-a;delta=p-np.array(a);out.append((edge[0]*delta[1]-edge[1]*delta[0])/np.linalg.norm(edge))
    return float(min(out))
# Weights sum to one; segment centers interpolate actual JOINT HEADS (display tails are invalid).
segments=[('Hips','neck',.497,.50),('Head','head_end',.081,.50)]
for s in ['Left','Right']:
    segments += [(s+'UpLeg',s+'Leg',.10,.433),(s+'Leg',s+'Foot',.0465,.433),(s+'Foot',s+'ToeBase',.0145,.5),(s+'Arm',s+'ForeArm',.028,.436),(s+'ForeArm',s+'Hand',.016,.43),(s+'Hand',s+'Hand',.006,0)]
peaks={};events=[]
for n in names:
    v=angular(n);speeds=np.linalg.norm(v,axis=1);acc=np.linalg.norm(np.diff(v,axis=0),axis=1)
    peaks[n]={'speed_deg_frame':float(max(speeds)),'frame':int(np.argmax(speeds)+2),'accel_deg_frame2':float(max(acc)),'accel_frame':int(np.argmax(acc)+2)}
    for i in range(1,len(v)):
        sa,sb=speeds[i-1:i+1];cos=np.dot(v[i-1],v[i])/(sa*sb) if min(sa,sb)>.001 else 1
        if cos<-.5 and min(sa,sb)>.5:
            events.append({'bone':n,'frame':i+1,'kind':'reversal','before_speed':float(sa),'after_speed':float(sb),'direction_dot':float(cos)})
        med=float(np.median(speeds[max(0,i-3):min(len(v),i+4)]))
        if speeds[i]>max(4,2.8*med):events.append({'bone':n,'frame':i+2,'kind':'speed_spike','speed':float(speeds[i]),'local_median':med})
        if acc[i-1]>12:events.append({'bone':n,'frame':i+1,'kind':'angular_acceleration','accel':float(acc[i-1])})
# Scalar reversals are logged but not confused with quaternion antipodes / human joint motion.
scalar=[]
for fc in d['curves']:
    if 'rotation' not in fc['path']:continue
    a=np.diff(fc['values']); dv=np.array(fc['derivatives'])
    for i in range(1,89):
        if a[i-1]*a[i]<0 and min(abs(a[i-1]),abs(a[i]))>.003:
            scalar.append({'path':fc['path'],'component':fc['index'],'frame':i+1,'delta_before':float(a[i-1]),'delta_after':float(a[i]),'derivative':float(dv[i])})
joints=[];balance=[]
for i,row in enumerate(rows):
    h={n:np.array(v['head']) for n,v in row['bones'].items()};rec={'frame':i+1}
    for side in ['Left','Right']:
        arm=h[side+'ForeArm']-h[side+'Arm'];fore=h[side+'Hand']-h[side+'ForeArm']
        hand=np.array(Quaternion(row['bones'][side+'Hand']['world_q'])@Vector((0,1,0)))
        rec[side+'_elbow_flexion']=angle(arm,fore)
        rec[side+'_wrist_bend']=angle(fore,hand)
        # Swing relative to rest, removing twist around longitudinal local Y.
        q=Quaternion(row['bones'][side+'Hand']['q']);tw=Quaternion((q.w,0,q.y,0));tw.normalize();sw=q@tw.inverted()
        rec[side+'_wrist_swing_rest']=math.degrees(min(sw.angle,2*math.pi-sw.angle))
        rec[side+'_knee_flexion']=angle(h[side+'Leg']-h[side+'UpLeg'],h[side+'Foot']-h[side+'Leg'])
    joints.append(rec)
    com=sum((h[a]*(1-t)+h[b]*t)*w for a,b,w,t in segments)
    support=[];feet=[]
    for side in ['Left','Right']:
        # Compare vertical displacement to that foot's initial planted height.
        lift=h[side+'Foot'][2]-rows[0]['bones'][side+'Foot']['head'][2]
        if side=='Right' or i+1<=29 or i+1>=40:
            feet.append(side);a=h[side+'Foot'][:2];b=h[side+'ToeBase'][:2];axis=(b-a)/np.linalg.norm(b-a);lat=np.array([-axis[1],axis[0]])
            # Heel extends 12 cm behind ankle; toes 9 cm past toe-base; width 20 cm.
            support.extend([a-axis*.12+lat*.10,a-axis*.12-lat*.10,b+axis*.09+lat*.10,b+axis*.09-lat*.10])
    poly=hull(support)
    balance.append({'frame':i+1,'com':list(com),'feet':feet,'polygon':poly,'margin_m':margin(com[:2],poly),'com_with_3pct_sword_proxy':list((com+.03*(h['RightHand']+np.array([0,-.25,0])))/1.03)})
sym={}
for a,b in [('LeftShoulder','RightShoulder'),('LeftArm','RightArm'),('LeftForeArm','RightForeArm'),('LeftHand','RightHand'),('LeftUpLeg','RightUpLeg')]:
    av=np.linalg.norm(angular(a),axis=1);bv=np.linalg.norm(angular(b),axis=1)
    cors={str(lag):(float(np.corrcoef(av[max(0,lag):min(89,89+lag)],bv[max(0,-lag):min(89,89-lag)])[0,1]) if min(np.std(av),np.std(bv))>1e-7 else None) for lag in range(-5,6)}
    sym[a+'/'+b]={'speed_correlation_zero_lag':cors['0'],'best_lag':(max(cors,key=lambda k:cors[k]) if cors['0'] is not None else None),'correlations':cors}
windows={}
for start,end in [(13,27),(80,90)]:
    windows[f'{start}-{end}']={}
    for n in ['Hips','LeftHand','RightHand','LeftForeArm','RightForeArm']:
        pos=series(n,'head')[start-1:end];speed=np.linalg.norm(np.diff(pos,axis=0),axis=1)
        windows[f'{start}-{end}'][n]={'speed_m_frame':list(speed),'cv':float(np.std(speed)/np.mean(speed)) if np.mean(speed)>1e-7 else 0,'travel_m':float(sum(speed))}
cloth={}
hips=angular('Hips','world_q')[:,2]
for n in names:
    if 'phys_' not in n:continue
    v=angular(n,'world_q')[:,2]
    cors={str(lag):float(np.corrcoef(hips[max(0,-lag):min(60,60-lag)],v[max(0,-lag)+lag:min(60,60-lag)+lag])[0,1]) for lag in range(-10,21)}
    cloth[n]={'yaw_velocity_best_delay':int(max(cors,key=lambda k:cors[k])),'max_correlation':max(cors.values()),'local_peak':peaks[n],
              'searched_lags_frames':[-10,20],
              'end_speed_deg_frame':float(np.linalg.norm(angular(n)[-1])), 'end_world_speed_deg_frame':float(np.linalg.norm(angular(n,'world_q')[-1]))}
out={'label':label,'bone_count':len(names),'curve_count':len(d['curves']),'key_count':sum(x['keys'] for x in d['curves']), 'max_key_gap':max(x['max_gap'] for x in d['curves']),'peaks':peaks,'events':events,'scalar_reversals':scalar,'joints':joints,'balance':balance,'symmetry':sym,'windows':windows,'cloth':cloth}

# Additional audit measures reuse the already captured 357 action samples.
major=[n for n in names if not n.startswith('phys_')]
translation={}
for n in major:
    pos=series(n,'head');vel=np.diff(pos,axis=0);acc=np.diff(vel,axis=0)
    sp=np.linalg.norm(vel,axis=1);ap=np.linalg.norm(acc,axis=1)
    sq=np.linalg.norm(angular(n,sub=True),axis=1)
    translation[n]={'peak_head_step_m':float(max(sp)),'step_frame':int(np.argmax(sp)+2),'peak_head_accel_m_frame2':float(max(ap)),'accel_frame':int(np.argmax(ap)+2),'quarter_frame_peak_rotation_deg_frame':float(max(sq)),'quarter_frame_peak_at':float(rr[int(np.argmax(sq))+1]['f'])}
cascade={}
for start,end,label2 in [(30,44,'first_cut'),(47,61,'second_cut')]:
    cascade[label2]={}
    for n in ['Hips','Spine02','Spine01','Spine','RightShoulder','LeftShoulder','RightArm','RightForeArm','RightHand']:
        vals=np.linalg.norm(angular(n,sub=True),axis=1);wv=np.linalg.norm(angular(n,'world_q',sub=True),axis=1)
        ids=[i for i in range(len(vals)) if start<rr[i+1]['f']<=end]
        peak=max(ids,key=lambda i:vals[i]);wp=max(ids,key=lambda i:wv[i])
        cascade[label2][n]={'local_peak_frame':rr[peak+1]['f'],'local_peak_deg_frame':float(vals[peak]),'world_peak_frame':rr[wp+1]['f'],'world_peak_deg_frame':float(wv[wp])}
counter=[]
surface_path=ROOT/f'renders/astra/naturalness_surface_{label}.json'
if surface_path.exists():
    surfaces=json.loads(surface_path.read_text())
    for row,surf in zip(rows,surfaces['rows']):
        h=row['bones'];axis=np.array(surf['sword_tip'])-surf['sword_grip'];axis[2]=0;axis/=np.linalg.norm(axis)
        torso=np.array(h['neck']['head'])-h['Hips']['head'];offset=float(np.dot(torso[:2],axis[:2]));lean=math.degrees(math.atan2(offset,torso[2]))
        counter.append({'frame':int(row['f']),'toward_blade_offset_m':offset,'toward_blade_lean_deg':lean})
    out['foot_floor']=surfaces
    for bal,surf in zip(balance,surfaces['rows']):
        weapon_com=np.array(surf['sword_grip'])*.55+np.array(surf['sword_tip'])*.45
        bal['weapon_mass_sensitivity']={str(w):margin((np.array(bal['com'])+w*weapon_com)[:2]/(1+w),bal['polygon']) for w in [0.02,0.04,0.06]}
    def yaw_values(n):
        qs=series(n,'world_q');ref=Quaternion(qs[0]).inverted();angles=[]
        for q in qs:
            dq=Quaternion(q)@ref;angles.append(2*math.atan2(dq.z,dq.w))
        return np.unwrap(angles)
    for n in cloth:
        yaw=yaw_values(n)
        cloth[n]['first_positive_extremum_frame']=int(35+np.argmax(yaw[34:51]))
        cloth[n]['second_negative_extremum_frame']=int(52+np.argmin(yaw[51:76]))
    out['hips_yaw_extrema']={'first_positive':int(35+np.argmax(yaw_values('Hips')[34:51])), 'second_negative':int(52+np.argmin(yaw_values('Hips')[51:76]))}

out['major_translation']=translation;out['momentum_cascade']=cascade;out['sword_counterlean']=counter
out['rotation_convention']='shortest quaternion log of q_next @ inverse(q_prev); rad->deg; velocities per frame; world quaternion gives world axes; local quaternion gives parent axes'

# Hand-axis screening added for the dedicated sword-arm correction. All 357
# samples are measured by this naturalness gate, not imported audit conclusions.
arm_rom=[]
for row in rr:
    bb=row['bones'];S=Vector(bb['RightArm']['head']);E=Vector(bb['RightForeArm']['head']);W=Vector(bb['RightHand']['head'])
    fore=(W-E).normalized();hand=Quaternion(bb['RightHand']['world_q']);local=hand.inverted()@fore
    arm_rom.append({'frame':row['f'],'wrist_deviation_deg':math.degrees(math.atan2(local.x,math.hypot(local.y,local.z))),
        'wrist_flexion_deg':-math.degrees(math.atan2(local.z,local.y)),
        'wrist_total_bend_deg':math.degrees(fore.angle(hand@Vector((0,1,0)))),
        'elbow_flexion_deg':math.degrees((E-S).angle(W-E))})
arm_ranges={}
for key in ['wrist_deviation_deg','wrist_flexion_deg','wrist_total_bend_deg','elbow_flexion_deg']:
    low=min(arm_rom,key=lambda x:x[key]);high=max(arm_rom,key=lambda x:x[key])
    arm_ranges[key]={'min':low[key],'min_frame':low['frame'],'max':high[key],'max_frame':high['frame']}
out['sword_arm_screen']={'axis_convention':'forearm longitudinal vector decomposed in hand frame; X transverse proxy, Z palm-normal proxy; not mesh-calibrated anatomy',
    'rows':arm_rom,'ranges':arm_ranges,'first_cut_upper_forearm_delay_frames':cascade['first_cut']['RightForeArm']['world_peak_frame']-cascade['first_cut']['RightArm']['world_peak_frame']}

(ROOT/f'renders/astra/naturalness_metrics_{label}.json').write_text(json.dumps(out,indent=2))
print('PEAKS',json.dumps(sorted(peaks.items(),key=lambda kv:kv[1]['accel_deg_frame2'],reverse=True)[:15],indent=2))
print('EVENTS',json.dumps(events,indent=2))
print('JOINT RANGES',{k:(round(min(r[k] for r in joints),1),round(max(r[k] for r in joints),1),max(joints,key=lambda r:r[k])['frame']) for k in joints[0] if k!='frame'})
print('BALANCE OUTSIDE',[(b['frame'],round(b['margin_m'],3),b['feet']) for b in balance if b['margin_m']<.02])
print('SYMMETRY',sym)
print('WINDOWS',windows)
print('CLOTH',json.dumps({n:v for n,v in cloth.items() if 'cape' in n or 'back_C' in n},indent=2))
