"""Independent before/after gate over the existing naturalness outputs."""
import json,math,sys,hashlib
from pathlib import Path
import numpy as np
from mathutils import Quaternion,Vector
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'renders/astra'
def read(n):return json.loads((D/n).read_text())
b=read('naturalness_armfix_before.json');a=read('naturalness_armfix.json')
bm=read('naturalness_metrics_armfix_before.json');am=read('naturalness_metrics_armfix.json')
bs=read('naturalness_surface_armfix_before.json');ass=read('naturalness_surface_armfix.json')
def clean(x):
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items() if k not in ['session_uid']}
 if isinstance(x,list):return [clean(v) for v in x]
 return x
inv_changes=[k for k in b['invariants'] if clean(b['invariants'][k])!=clean(a['invariants'][k])]
print('INVARIANT DIFFERENCES',inv_changes)
assert not inv_changes
changed_paths=[(x['path'],x['index']) for x,y in zip(b['curves'],a['curves']) if x!=y]
assert all(x[0] in [f'pose.bones["{n}"].rotation_quaternion' for n in ['RightArm','RightForeArm','RightHand']] for x in changed_paths)
unrelated=[];max_hand_position=0;max_hand_rotation=0;max_other_position=0
for x,y in zip(b['rows'],a['rows']):
 for n in x['bones']:
  p,q=x['bones'][n],y['bones'][n]
  if n not in ['RightArm','RightForeArm','RightHand'] and p['q']!=q['q']:unrelated.append((x['f'],n))
  if n not in ['RightForeArm']:
   e=np.linalg.norm(np.array(p['head'])-q['head']);max_other_position=max(max_other_position,e)
  if n=='RightHand':
   max_hand_position=max(max_hand_position,np.linalg.norm(np.array(p['head'])-q['head']))
   d=Quaternion(q['world_q'])@Quaternion(p['world_q']).inverted();v=Vector((d.x,d.y,d.z)).length
   max_hand_rotation=max(max_hand_rotation,math.degrees(2*math.atan2(v,abs(d.w))))
assert not unrelated
blade={n:max(float(np.linalg.norm(np.array(x[n])-y[n])) for x,y in zip(bs['rows'],ass['rows'])) for n in ['sword_tip','sword_grip']}
foot_error=max(abs(x['feet'][s]['min_clearance_m']-y['feet'][s]['min_clearance_m']) for x,y in zip(bs['rows'],ass['rows']) for s in ['LeftFoot','RightFoot'])
cloth_floor=max(abs(x['cloth_min_z']-y['cloth_min_z']) for x,y in zip(bs['rows'],ass['rows']))
cloth_same=bm['cloth']==am['cloth']
bal_deltas=[{'frame':x['frame'],'before':x['margin_m'],'after':y['margin_m'],'change_m':y['margin_m']-x['margin_m']} for x,y in zip(bm['balance'],am['balance']) if abs(y['margin_m']-x['margin_m'])>1e-8]
ranges={k:{'before':bm['sword_arm_screen']['ranges'][k],'after':am['sword_arm_screen']['ranges'][k]} for k in am['sword_arm_screen']['ranges']}
first={n:{'before':bm['momentum_cascade']['first_cut'][n],'after':am['momentum_cascade']['first_cut'][n]} for n in ['RightShoulder','RightArm','RightForeArm','RightHand']}
new_events=[e for e in am['events'] if not any(e['bone']==z['bone'] and e['frame']==z['frame'] and e['kind']==z['kind'] for z in bm['events'])]
peaks={n:{'before':bm['peaks'][n],'after':am['peaks'][n]} for n in ['RightArm','RightForeArm','RightHand']}
mins={label:{'before':min(x['margin_m'] for x in bm['balance'] if lo<=x['frame']<=hi),'after':min(x['margin_m'] for x in am['balance'] if lo<=x['frame']<=hi)} for label,lo,hi in [('whole',1,90),('low_pose',46,57)]}
endpoints={str(f):all(x['bones'][n]==y['bones'][n] for n in ['RightArm','RightForeArm','RightHand']) for x,y in zip(b['rows'],a['rows']) if (f:=x['f']) in [44,53]}
gates={'wrist_within_30':max(abs(am['sword_arm_screen']['ranges']['wrist_deviation_deg'][k]) for k in ['min','max'])<=30,'elbow_within_150':am['sword_arm_screen']['ranges']['elbow_flexion_deg']['max']<=150,'forearm_delayed':.5<=am['sword_arm_screen']['first_cut_upper_forearm_delay_frames']<=1,'hand_preserved':max_hand_position<1e-5 and max_hand_rotation<.001,'blade_preserved':max(blade.values())<1e-5,'feet_preserved':foot_error<1e-8,'cloth_preserved':cloth_same and cloth_floor<1e-8,'balance_no_new_violation_or_material_loss':mins['whole']['after']>=mins['whole']['before']-1e-6 and all(x['change_m']>=-.001 for x in bal_deltas) and not any(x['before']>=.02 and x['after']<.02 for x in bal_deltas),'endpoints_exact':all(endpoints.values()),'no_unrelated_curves':not unrelated and not inv_changes}
r={'gates':gates,'balance_comparison_tolerance_m':.001,'balance_tolerance_reason':'Approximate segment mass model; report all deltas explicitly. A sub-millimetre margin change is below this proxy precision; feet/support geometry must remain exact and no new violation is allowed.','ranges':ranges,'first_cut':first,'local_peaks':peaks,'new_integer_rotation_events':new_events,'hand_world_position_max_error_m':max_hand_position,'hand_world_rotation_max_error_deg':max_hand_rotation,'blade_max_error_m':blade,'unaffected_heads_max_error_m':max_other_position,'foot_clearance_max_error_m':foot_error,'cloth_floor_max_error_m':cloth_floor,'cloth_metrics_exactly_equal':cloth_same,'balance_minima':mins,'balance_frame_changes':bal_deltas,'endpoints_exact':endpoints,'changed_curves':changed_paths,'invariant_differences':inv_changes,'source_sha256':hashlib.sha256((ROOT/'models/astra_xslash_v2_final_prefix2.blend').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256((ROOT/'models/astra_xslash_v2_armfix_trial.blend').read_bytes()).hexdigest()}
(D/'naturalness_armfix_verification.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r,indent=2))
assert all(gates.values()),gates
