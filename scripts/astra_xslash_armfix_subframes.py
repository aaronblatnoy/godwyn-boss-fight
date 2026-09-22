"""Check blade binding between the existing quarter-frame keys, at 1/64 frame."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Quaternion,Vector
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
times=[33+i/64 for i in range(21*64+1)]
sets=[]
for name in ['astra_xslash_v2_final_prefix2.blend','astra_xslash_v2_armfix_trial.blend']:
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models'/name));s=bpy.context.scene;r=bpy.data.objects['Armature']
 for o in s.objects:
  if o.type=='MESH':o.hide_viewport=True
 rows=[]
 for f in times:
  s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();p=r.pose.bones
  mats={n:r.matrix_world@p[n].matrix for n in ['RightArm','RightForeArm','RightHand']}
  S,E,W=[mats[n].translation.copy() for n in mats];q=mats['RightHand'].to_quaternion();fore=(W-E).normalized();d=q.inverted()@fore
  rows.append({'f':f,'pos':list(W),'hand_q':list(q),'upper_q':list(mats['RightArm'].to_quaternion()),'fore_q':list(mats['RightForeArm'].to_quaternion()),'deviation':math.degrees(math.atan2(d.x,math.hypot(d.y,d.z))),'elbow':math.degrees((E-S).angle(W-E))})
 sets.append(rows)
def angle(a,b):
 q=Quaternion(b)@Quaternion(a).inverted();return math.degrees(2*math.atan2(Vector((q.x,q.y,q.z)).length,abs(q.w)))
def peak(rows,n):
 vals=[(angle(a[n],b[n])*64,b['f']) for a,b in zip(rows,rows[1:]) if 34<b['f']<=44];v,f=max(vals);return {'frame':f,'speed_deg_frame':v}
errs=[{'f':a['f'],'position_m':(Vector(a['pos'])-Vector(b['pos'])).length,'rotation_deg':angle(a['hand_q'],b['hand_q'])} for a,b in zip(*sets)]
result={'sampling_frames':times,'max_hand_position_error':max(errs,key=lambda x:x['position_m']),'max_hand_rotation_error':max(errs,key=lambda x:x['rotation_deg']),'before_peaks':{n:peak(sets[0],n) for n in ['upper_q','fore_q','hand_q']},'after_peaks':{n:peak(sets[1],n) for n in ['upper_q','fore_q','hand_q']},'after_min_deviation':min(sets[1],key=lambda x:x['deviation']),'after_max_elbow':max(x['elbow'] for x in sets[1])}
(ROOT/'renders/astra/naturalness_armfix_subframes.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='sampling_frames'},indent=2))
assert result['max_hand_position_error']['position_m']<.0001
assert result['max_hand_rotation_error']['rotation_deg']<.01
assert result['after_max_elbow']<=150
