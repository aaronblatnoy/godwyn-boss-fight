"""Fast authoring probe: evaluated joints before surface correction or key baking."""
import math,json
from mathutils import Vector
from pathlib import Path

def probe(b,definition):
    rows=[];last={};max_step={}
    for f in range(1,b.N+1):
        b.s.frame_set(f);d=b.pose(f,definition);row={'frame':f,'wrist':{},'elbow':{},'foot_error':{},'steps':{},'right_debug':{}}
        for side in ['Left','Right']:
            h={k:b.world(side+k).translation for k in ['Arm','ForeArm','Hand','Foot']};a=h['ForeArm']-h['Arm'];v=h['Hand']-h['ForeArm'];long=b.world(side+'Hand').to_quaternion()@Vector((0,1,0))
            
            if side=='Right':row['right_debug']={'shoulder':list(h['Arm']),'hand':list(h['Hand']),'long':list(long),'q':list(b.world(side+'Hand').to_quaternion())}
            row['wrist'][side]=math.degrees(v.angle(long));row['elbow'][side]=math.degrees(a.angle(v));row['foot_error'][side]=(h['Foot']-d['feet'][side]).length
        for p in b.r.pose.bones:
            q=p.rotation_quaternion.copy()
            if p.name in last:
                dq=q@last[p.name].inverted();dq.normalize();step=math.degrees(2*math.acos(min(1,abs(dq.w))));max_step[p.name]=max(max_step.get(p.name,0),step);row['steps'][p.name]=step
            last[p.name]=q
        tip,grip=b.sword_points();axis=tip-grip;axis.z=0;axis.normalize();torso=b.world('neck').translation-b.world('Hips').translation
        row['counterlean_deg']=math.degrees(math.atan2(torso.dot(axis),torso.z))
        rows.append(row)
    result={'max_step_deg':max_step,'rows':rows,'wrist_range':{s:[min(r['wrist'][s] for r in rows),max(r['wrist'][s] for r in rows)] for s in ['Left','Right']},'unreachable_feet':[{ 'frame':r['frame'],**r['foot_error']} for r in rows if max(r['foot_error'].values())>.002]}
    p=Path(__file__).resolve().parents[1]/'renders/astra/moves'/f'{b.name}_pose_probe.json';p.write_text(json.dumps(result,indent=2));print('PROBE',json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
