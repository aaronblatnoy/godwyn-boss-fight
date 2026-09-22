"""Comparable before/after quaternion-log, anatomy, grip-axis and blade-roll data."""
import sys,json,math,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
from astra_armaudit_analyze import analyze,angle,qm
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'
def read(name):return json.loads((OUT/name).read_text())
before=read('lunge_thrust_l01_fresh_before_samples.json');after=read('lunge_thrust_samples.json')
retime=read('lunge_thrust_l01_retime.json')
base=analyze('lunge_thrust',before,{'fresh_baseline_sha256':retime['baseline_sha256']})
current=analyze('lunge_thrust',after,{'fresh_blend_sha256':hashlib.sha256((ROOT/'models/astra_move_lunge_thrust_wip.blend').read_bytes()).hexdigest()})
g=read('lunge_thrust_grip_metrics.json');gb=read('lunge_thrust_l01_before_grip_metrics.json')
def blade_checks(grip,skeleton):
    result={};rs=grip['rows'];rotation=[]
    for r,b in zip(rs,skeleton):
        rotation.append(qm(b['bones']['RightHand']['wq']).T@np.array(r['direction']))
    result['max_blade_axis_hand_local_drift_deg']=max(angle(rotation[0],v) for v in rotation)
    result['hilt_wrist_variation_mm']=1000*(max(r['hilt_wrist_distance_m'] for r in rs)-min(r['hilt_wrist_distance_m'] for r in rs))
    for label,lo,hi in [('active',25,35),('recovery',37,64)]:
        samples=[]
        for i in range(1,len(rs)-1):
            r=rs[i];f=r['frame']
            if not lo<=f<=hi:continue
            d=np.array(r['direction']);v=(np.array(rs[i+1]['tip'])-rs[i-1]['tip'])*60;transverse=v-d*np.dot(v,d)
            if np.linalg.norm(transverse)<.75:continue
            samples.append({'frame':f,'edge_vs_transverse_cut_plane_deg':math.degrees(math.acos(float(np.clip(abs(np.dot(r['edge'],transverse/np.linalg.norm(transverse))),0,1)))),'transverse_speed_m_s':float(np.linalg.norm(transverse))})
        result[label+'_roll']={'samples':samples,'range_deg':[min(x['edge_vs_transverse_cut_plane_deg'] for x in samples),max(x['edge_vs_transverse_cut_plane_deg'] for x in samples)] if samples else None,'interpretation':'Diagnostic transverse plane only: this clip contains a point-first stab and non-striking recovery, not an edge-led slash.'}
    return result
unchanged={}
for label,names in [('secondary',[n for n in before[0]['bones'] if n.startswith('phys_')]),('ground_chain',['Hips','Spine02','Spine01','Spine','RightShoulder','LeftShoulder','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase'])]:
    unchanged[label]=max(abs(x-y) for a,b in zip(before,after) for n in names for key in ['wq','h'] for x,y in zip(a['bones'][n][key],b['bones'][n][key]))
result={'before':base,'after':current,'before_blade_checks':blade_checks(gb,before),'after_blade_checks':blade_checks(g,after),'unchanged_world_pose_component_errors':unchanged,'baseline_grip_provenance':'Prior grip landmarks cross-checked against freshly loaded baseline hand quaternions; final grip audit freshly evaluates current sword and closed-hand meshes.'}
(OUT/'lunge_thrust_l01_comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'before_ranges':base['ranges'],'after_ranges':current['ranges'],'before_spikes':base['spikes'],'after_spikes':current['spikes'],'invariants':unchanged,'blade':{phase:{k:v for k,v in result[phase+'_blade_checks'].items() if not k.endswith('_roll')} for phase in ['before','after']},'roll_ranges':{phase:{k:v['range_deg'] for k,v in result[phase+'_blade_checks'].items() if k.endswith('_roll')} for phase in ['before','after']}},indent=2))
assert not current['spikes']
assert max(unchanged.values())<.00001
assert result['after_blade_checks']['hilt_wrist_variation_mm']<.01
assert result['after_blade_checks']['max_blade_axis_hand_local_drift_deg']<.001
