"""Analyze sampled quaternions without bpy; --cached explicitly marks inherited evidence.

Run with Blender's bundled Python (numpy), PYTHONDONTWRITEBYTECODE=1.
No blend files are written. Hand X/Z are imported anatomical AXIS PROXIES,
not certified palm axes; retain total bend independently of this decomposition.
"""
import sys, json, math, hashlib
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'renders/astra/armaudit'
CHAIN = ['RightShoulder','RightArm','RightForeArm','RightHand']

def unit(x):
    x=np.asarray(x,dtype=float); return x/max(np.linalg.norm(x),1e-14)

def qm(q):
    w,x,y,z=unit(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def qmul(a,b):
    w,x,y,z=a; W,X,Y,Z=b
    return np.array([w*W-x*X-y*Y-z*Z,w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W])

def qlog(a,b):
    a=unit(a);b=unit(b); q=unit(qmul(b,a*np.array([1,-1,-1,-1])))
    if q[0]<0:q=-q
    mag=np.linalg.norm(q[1:]); return q[1:]*(math.degrees(2*math.atan2(mag,q[0]))/mag if mag>1e-12 else 0)

def angle(a,b): return math.degrees(math.acos(float(np.clip(unit(a)@unit(b),-1,1))))

def ranges(frames, step=1):
    if not frames:return []
    result=[];start=last=frames[0]
    for f in frames[1:]:
        if abs(f-last-step)>1e-7:result.append([start,last]);start=f
        last=f
    result.append([start,last]);return result

def hull(points):
    pts=sorted(set(map(tuple,points)))
    def cr(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];hi=[]
    for p in pts:
        while len(lo)>1 and cr(lo[-2],lo[-1],p)<=0:lo.pop()
        lo.append(p)
    for p in pts[::-1]:
        while len(hi)>1 and cr(hi[-2],hi[-1],p)<=0:hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]

def margin(p,poly):
    return min(((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))/np.linalg.norm(np.array(b)-a) for a,b in zip(poly,poly[1:]+poly[:1]))

def support(row):
    h={n:np.array(v['h']) for n,v in row['bones'].items()}
    seg=[('Hips','neck',.497,.5),('Head','head_end',.081,.5)]
    for side in ['Left','Right']:
        seg += [(side+'UpLeg',side+'Leg',.1,.433),(side+'Leg',side+'Foot',.0465,.433),(side+'Foot',side+'ToeBase',.0145,.5),(side+'Arm',side+'ForeArm',.028,.436),(side+'ForeArm',side+'Hand',.016,.43),(side+'Hand',side+'Hand',.006,0)]
    com=sum((h[a]*(1-t)+h[b]*t)*w for a,b,w,t in seg)
    pts=[]
    for side in (['Right'] if 30<=row['frame']<40 else ['Right','Left']):
        a=h[side+'Foot'][:2];b=h[side+'ToeBase'][:2];ax=unit(b-a);lat=np.array([-ax[1],ax[0]])
        pts += [a-ax*.12+lat*.10,a-ax*.12-lat*.10,b+ax*.09+lat*.10,b+ax*.09-lat*.10]
    return com,hull(pts)

def analyze(name, rows, provenance, rest=None, grip_rows=None):
    fs=np.array([r['frame'] for r in rows]);dt=float(fs[1]-fs[0]); ints=[r for r in rows if r['frame']%1==0]
    out={'name':name,'provenance':provenance,'frame_range':[float(fs[0]),float(fs[-1])],'sample_step_frames':dt,'fps':30,'bone_names':list(rows[0]['bones']),'rows':[], 'kinematics':{},'ranges':{},'spikes':[], 'sequence':{},'loop':{}}
    for row in rows:
        b=row['bones']; h={n:np.array(v['h']) for n,v in b.items()}
        upper=unit(h['RightForeArm']-h['RightArm']);fore=unit(h['RightHand']-h['RightForeArm']);hand=qm(b['RightHand']['wq']);handlong=hand[:,1]
        up=unit(h['neck']-h['Hips']);right=h['RightArm']-h['LeftArm'];right=unit(right-up*(right@up));front=unit(np.cross(up,right))
        # Swing decomposition in the hand frame fixes the axes to the palm, retaining pronation separately.
        fore_in_hand=hand.T@fore
        j={'elbow_flexion_deg':angle(upper,fore),'wrist_total_bend_deg':angle(fore,handlong),
           'wrist_flexion_proxy_deg':-math.degrees(math.atan2(fore_in_hand[2],fore_in_hand[1])),
           'wrist_deviation_proxy_deg':math.degrees(math.atan2(fore_in_hand[0],math.hypot(fore_in_hand[1],fore_in_hand[2]))),
           'shoulder_elevation_deg':angle(upper,-up),
           'shoulder_flexion_projection_deg':math.degrees(math.atan2(upper@front,-upper@up)),
           'shoulder_abduction_projection_deg':math.degrees(math.atan2(upper@right,-upper@up))}
        rec={'frame':row['frame'],'joints':j,'bones':{n:b[n] for n in CHAIN}}
        if name=='xslash':
            com,poly=support(row);rec['com']={'position_m':com.tolist(),'support_polygon_m':[list(p) for p in poly],'static_margin_m':margin(com[:2],poly),'inset_margin_m':margin(com[:2],poly)-.02}
        out['rows'].append(rec)
    for key in out['rows'][0]['joints']:
        vals=[r['joints'][key] for r in out['rows']];lo=int(np.argmin(vals));hi=int(np.argmax(vals))
        out['ranges'][key]={'min':vals[lo],'min_frame':float(fs[lo]),'max':vals[hi],'max_frame':float(fs[hi])}
    out['rom_flags']={k:ranges([r['frame'] for r in out['rows'] if pred(r['joints'][k])],dt) for k,pred in {
        'elbow_flexion_deg':lambda a:a<0 or a>150,
        'wrist_flexion_proxy_deg':lambda a:abs(a)>70,
        'wrist_deviation_proxy_deg':lambda a:abs(a)>30,
        'shoulder_elevation_deg':lambda a:a>180,
        'shoulder_flexion_projection_deg':lambda a:a< -60,
    }.items()}
    for n in CHAIN:
        out['kinematics'][n]={}
        for label,rs,step in [('quarter',rows,dt),('integer',ints,1)]:
            frame=np.array([r['frame'] for r in rs])
            for space,key in [('local','q'),('world','wq')]:
                v=np.array([qlog(a['bones'][n][key],b['bones'][n][key])/step for a,b in zip(rs,rs[1:])]); speed=np.linalg.norm(v,axis=1);acc=np.linalg.norm(np.diff(v,axis=0)/step,axis=1)
                ix=int(speed.argmax());ai=int(acc.argmax())
                z={'speed_deg_frame':speed.tolist(),'velocity_vector_deg_frame':v.tolist(),'accel_deg_frame2':acc.tolist(),'interval_end_frames':frame[1:].tolist(),'max_speed':float(speed[ix]),'max_speed_frame':float(frame[ix+1]),'max_acceleration':float(acc[ai]),'max_acceleration_center_frame':float(frame[ai+1])}
                out['kinematics'][n][label+'_'+space]=z
                if space=='local':
                    for i in range(1,len(speed)-1):
                        nb=np.concatenate([speed[max(0,i-3):i],speed[i+1:i+4]]);med=float(np.median(nb));ratio=float(speed[i]/max(med,1e-9))
                        if speed[i]>4 and ratio>=10:out['spikes'].append({'bone':n,'sampling':label,'interval_end_frame':float(frame[i+1]),'speed_deg_frame':float(speed[i]),'neighbor_median':med,'ratio':ratio})
        if name in ['idle_guard','walk_stalk']:
            a=out['kinematics'][n]['quarter_local'];first=a['velocity_vector_deg_frame'][0];last=a['velocity_vector_deg_frame'][-1]
            out['loop'][n]={'endpoint_rotation_error_deg':float(np.linalg.norm(qlog(rows[-1]['bones'][n]['q'],rows[0]['bones'][n]['q']))),'velocity_mismatch_deg_s':float(np.linalg.norm(np.array(first)-last)*30),'start_speed_deg_frame':a['speed_deg_frame'][0],'end_speed_deg_frame':a['speed_deg_frame'][-1]}
    windows={'xslash':[(30,44),(47,61)],'lunge_thrust':[(10,35),(25,35),(35,44)]}.get(name,[])
    for lo,hi in windows:
        entry={}
        for n in CHAIN:
            entry[n]={}
            for space in ['local','world']:
                k=out['kinematics'][n]['quarter_'+space];ids=[i for i,f in enumerate(k['interval_end_frames']) if lo<f<=hi];i=max(ids,key=lambda j:k['speed_deg_frame'][j]);vals=np.array([k['speed_deg_frame'][j] for j in ids])
                entry[n][space]={'peak_frame':k['interval_end_frames'][i],'peak_deg_frame':k['speed_deg_frame'][i],'speed_cv':float(vals.std()/max(vals.mean(),1e-9))}
        entry['elbow_min_max_deg']=[min(r['joints']['elbow_flexion_deg'] for r in out['rows'] if lo<=r['frame']<=hi),max(r['joints']['elbow_flexion_deg'] for r in out['rows'] if lo<=r['frame']<=hi)]
        out['sequence'][f'{lo}-{hi}']=entry
    if grip_rows:
        byf={r['frame']:r for r in rows};gdata=[]
        for r in grip_rows:
            if r['frame'] not in byf:continue
            b=byf[r['frame']]['bones']['RightHand'];w=qm(b['wq']);h=np.array(b['h']);grip=np.array(r.get('hilt',r.get('sword_grip')));tip=np.array(r.get('tip',r.get('sword_tip')))
            gdata.append({'frame':r['frame'],'hilt_hand_local_m':(w.T@(grip-h)).tolist(),'blade_axis_hand_local':(w.T@unit(tip-grip)).tolist(),'hilt_wrist_distance_m':float(np.linalg.norm(grip-h))})
        ref=gdata[0]
        for r in gdata:r['translation_drift_m']=float(np.linalg.norm(np.array(r['hilt_hand_local_m'])-ref['hilt_hand_local_m']));r['axis_drift_deg']=angle(r['blade_axis_hand_local'],ref['blade_axis_hand_local'])
        out['grip']={'rows':gdata,'max_translation_drift_m':max(r['translation_drift_m'] for r in gdata),'max_axis_drift_deg':max(r['axis_drift_deg'] for r in gdata),'note':'Position plus longitudinal axis; axial roll cannot be certified from two landmarks.'}
        if name=='lunge_thrust':
            thrust=[]
            for i in range(1,len(grip_rows)-1):
                r=grip_rows[i]
                if not 25<=r['frame']<=35:continue
                delta=(grip_rows[i+1]['frame']-grip_rows[i-1]['frame'])/30
                vel=(np.array(grip_rows[i+1]['tip'])-grip_rows[i-1]['tip'])/delta;axis=unit(np.array(r['tip'])-r['hilt']);axial=float(vel@axis)
                thrust.append({'frame':r['frame'],'tip_speed_m_s':float(np.linalg.norm(vel)),'axial_speed_m_s':axial,'transverse_speed_m_s':float(np.linalg.norm(vel-axis*axial)),'velocity_axis_angle_deg':angle(vel,axis)})
            out['active_thrust_translation']=thrust
    if name=='xslash':
        for i,r in enumerate(out['rows']):
            if i==0 or i==len(rows)-1:continue
            vel=(np.array(out['rows'][i+1]['com']['position_m'])-out['rows'][i-1]['com']['position_m'])/(2*dt/30)
            com=np.array(r['com']['position_m']);omega=math.sqrt(9.81/max(.1,com[2]+.015));capture=com[:2]+vel[:2]/omega
            r['com'].update({'velocity_m_s':vel.tolist(),'lipm_capture_point_m':capture.tolist(),'capture_margin_m':margin(capture,r['com']['support_polygon_m'])})
    return out

def cached():
    inventory=json.loads((OUT/'source_inventory.json').read_text());xf=ROOT/'renders/astra/naturalness_after.json';xd=json.loads(xf.read_text());verification=json.loads((ROOT/'renders/astra/naturalness_verification.json').read_text())
    summaries={}
    for name in inventory['targets']:
        path=xf if name=='xslash' else ROOT/f'renders/astra/moves/{name}_samples.json'
        raw=json.loads(path.read_text())
        rows=[{'frame':r['f'],'bones':{n:{'q':v['q'],'wq':v['world_q'],'h':v['head']} for n,v in r['bones'].items()}} for r in raw['rows']] if name=='xslash' else raw
        gp=ROOT/('renders/astra/naturalness_surface_after.json' if name=='xslash' else f'renders/astra/moves/{name}_grip_metrics.json');grip=json.loads(gp.read_text())['rows']
        prov={'mode':'inherited_samples_reanalysis_NOT_fresh_depsgraph','sample_file':str(path.relative_to(ROOT)),'sample_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'blend_sha256_at_start':inventory['targets'][name]['sha256'],'blend_hash_matches_prior_verification':inventory['targets'][name]['sha256']==verification['fixed_blend_sha256'] if name=='xslash' else None,'limitation':'Blender startup segfault before Python. Moveset cached samples lack a matching audited-blend hash; current-file attribution is provisional.'}
        d=analyze(name,rows,prov,xd['rest'] if name=='xslash' else None,grip)
        (OUT/f'data_{name}.json').write_text(json.dumps(d,indent=2))
        summaries[name]={k:v for k,v in d.items() if k not in ['rows','kinematics','grip']}
        summaries[name]['peaks']={n:{k:{a:b for a,b in v.items() if not isinstance(b,list)} for k,v in kv.items()} for n,kv in d['kinematics'].items()}
        summaries[name]['grip']={k:v for k,v in d.get('grip',{}).items() if k!='rows'}
        print(name,json.dumps(summaries[name]),flush=True)
    (OUT/'summary.json').write_text(json.dumps(summaries,indent=2))

if __name__=='__main__':
    if '--cached' not in sys.argv:raise SystemExit('Use --cached explicitly; fresh samples are produced by astra_armaudit_capture.py.')
    cached()
