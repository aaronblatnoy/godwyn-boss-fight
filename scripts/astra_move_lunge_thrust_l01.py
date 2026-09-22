"""L01 recovery timing correction: quaternion F-curves only, reproducible baseline.

Blender --python this_file -- [trial|apply]. The pre_l01 blend is read-only.
The builder can call apply_recovery() on its freshly baked original action.
"""
import sys, json, math, hashlib
from pathlib import Path
sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'renders/astra/moves'
CHAIN = ['RightArm', 'RightForeArm', 'RightHand']

def curves(action):
    return [fc for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for fc in bag.fcurves]

def hermite(t, pts):
    if t <= pts[0][0]: return pts[0][1]
    if t >= pts[-1][0]: return pts[-1][1]
    for (a,va,da),(b,vb,db) in zip(pts,pts[1:]):
        if a <= t <= b:
            u=(t-a)/(b-a)
            return (2*u**3-3*u*u+1)*va+(u**3-2*u*u+u)*(b-a)*da+(-2*u**3+3*u*u)*vb+(u**3-u*u)*(b-a)*db

def mapped_time(t, distal):
    delay=hermite(t,[(36.25,0,0),(37,.15,3/7),(44,3.15,3/7),(48,4,.2),(53,5,0),(64,0,0)])
    offset=hermite(t,[(37,0,0),(39,distal,0),(44,distal,0),(53,0,0)])
    return t+delay+offset

def snapshot():
    r=bpy.data.objects['Armature']
    return {(fc.data_path,fc.array_index):[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type) for k in fc.keyframe_points] for fc in curves(r.animation_data.action)}

def apply_recovery(original=None):
    r=bpy.data.objects['Armature']
    original=original or sample()
    def world_at(n,f):
        index=min(len(original)-1,max(0,(f-1)*4));i=int(index);u=index-i
        a=Quaternion(original[i]['bones'][n]['wq']);b=Quaternion(original[min(i+1,len(original)-1)]['bones'][n]['wq'])
        return a.slerp(b,u)
    values={n:[] for n in CHAIN}
    for row in original:
        f=row['frame'];desired={}
        for n,offset in zip(CHAIN,[0,.5,1.]):
            if f<=36.25 or f>=64:
                q=Quaternion(row['bones'][n]['q']);desired[n]=Quaternion(row['bones'][n]['wq'])
            else:
                lo=36.25;hi=64.
                for _ in range(40):
                    mid=(lo+hi)/2
                    if mapped_time(mid,offset)<f:lo=mid
                    else:hi=mid
                # Carry the blade outside the robe during the late redirection.
                # A shared world rotation preserves the distal relative grasp.
                clearance=hermite(f,[(43,0,0),(52,25,0),(56,25,0),(64,0,0)])
                forward_clearance=hermite(f,[(43,0,0),(49,-12,0),(57,-12,0),(64,0,0)])
                desired[n]=Quaternion((1,0,0),math.radians(forward_clearance))@Quaternion((0,1,0),math.radians(clearance))@world_at(n,(lo+hi)/2)
                p=r.data.bones[n];parent=p.parent.name
                parentq=desired[parent] if parent in desired else Quaternion(row['bones'][parent]['wq'])
                relation=(p.parent.matrix_local.inverted()@p.matrix_local).to_quaternion()
                q=(parentq@relation).inverted()@desired[n];q.normalize()
            if values[n] and q.dot(values[n][-1])<0:q.negate()
            values[n].append(q)
    for fc in curves(r.animation_data.action):
        for n in CHAIN:
            if fc.data_path != f'pose.bones["{n}"].rotation_quaternion':continue
            for k in fc.keyframe_points:
                if 36.25<k.co.x<64:k.co.y=values[n][round((k.co.x-1)*4)][fc.array_index]
            fc.update()

def sample():
    s=bpy.context.scene;r=bpy.data.objects['Armature'];out=[]
    for qf in range(4,257):
        f=qf/4;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
        out.append({'frame':f,'bones':{p.name:{'q':list(p.matrix_basis.to_quaternion()),'wq':list((r.matrix_world@p.matrix).to_quaternion()),'h':list((r.matrix_world@p.matrix).translation)} for p in r.pose.bones}})
    return out

def logdiff(a,b):
    q=Quaternion(b)@Quaternion(a).inverted();q.normalize()
    if q.w<0:q.negate()
    v=np.array([q.x,q.y,q.z]);l=np.linalg.norm(v)
    return v*(math.degrees(2*math.atan2(l,q.w))/l if l>1e-12 else 0)*4

def peaks(rows):
    result={}
    for n in CHAIN:
        result[n]={}
        for space,key in [('local','q'),('world','wq')]:
            vals=[{'frame':b['frame'],'speed':float(np.linalg.norm(logdiff(a['bones'][n][key],b['bones'][n][key])))} for a,b in zip(rows,rows[1:])]
            result[n][space]={label:max([v for v in vals if lo<v['frame']<=hi],key=lambda x:x['speed']) for label,lo,hi in [('active',25,35),('recovery',36.25,51),('settle',51,64),('full',1,64)]}
            velocities=[logdiff(a['bones'][n][key],b['bones'][n][key]) for a,b in zip(rows,rows[1:])]
            accel=[{'frame':rows[i+1]['frame'],'speed':float(np.linalg.norm(b-a)*4)} for i,(a,b) in enumerate(zip(velocities,velocities[1:]))]
            result[n][space]['acceleration_deg_frame2']=max(accel,key=lambda x:x['speed'])
    return result

def main():
    baseline=ROOT/'models/astra_move_lunge_thrust_pre_l01.blend'
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    visibility=[(o,o.hide_viewport) for o in bpy.context.scene.objects if o.type in ['MESH','CURVES']]
    for o,_ in visibility:o.hide_viewport=True
    before_curves=snapshot();before=sample()
    apply_recovery(before);after_curves=snapshot();after=sample()
    changed=[key for key in before_curves if before_curves[key]!=after_curves[key]]
    assert len(changed)==12 and all(any(k[0]==f'pose.bones["{n}"].rotation_quaternion' for n in CHAIN) for k in changed)
    identity_error=max(abs(x-y) for a,b in zip(before,after) if a['frame']<=36.25 or a['frame']==64 for n in a['bones'] for key in ['q','wq','h'] for x,y in zip(a['bones'][n][key],b['bones'][n][key]))
    report={'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'before':peaks(before),'after':peaks(after),'changed_fcurves':changed,'untouched_fcurve_count':len(before_curves)-12,'max_unmodified_pose_component_error':identity_error,'unchanged_pose_windows':'F1–36.25 and F64, all 121 bones; active F25–35 is unchanged.','timing':'World quaternion trajectories: old F37–44 -> F37.15–47.15, with a smooth entry starting F36.25; distal offsets 0.5/1f. Re-express in parent-local quaternion keys to retain visible sequencing. Distal offsets taper out over original F44–53. Extend later redirection slightly; reclaim original F53–64 settle; F64 preserved.','clearance_correction':'Shared upper-arm/forearm/hand world rotation ramps after F43: outward Y up to 25deg and forward X down to -12deg; smoothly returns to zero at F64. Quaternion F-curves only; no mesh, cloth, foot or root edits.'}
    if 'verify-current' in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_move_lunge_thrust_wip.blend'))
        assert snapshot()==after_curves,'Saved curves differ from reproducible retime'
        report['saved_fcurves_match_idempotent_replay']=True
    (OUT/'lunge_thrust_l01_retime.json').write_text(json.dumps(report,indent=2))
    (OUT/'lunge_thrust_l01_fresh_before_samples.json').write_text(json.dumps(before,separators=(',',':')))
    print(json.dumps(report,indent=2),flush=True)
    if 'apply' in sys.argv:
        assert identity_error<1e-5
        assert 11<=report['after']['RightArm']['local']['full']['speed']<=12
        times=[report['after'][n]['world']['full']['frame'] for n in CHAIN]
        assert times[1]-times[0]==.5 and times[2]-times[1]==.5,times
        for o,hidden in visibility:o.hide_viewport=hidden
        bpy.context.scene.frame_set(1)
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_move_lunge_thrust_wip.blend'))
    
if __name__=='__main__':main()
