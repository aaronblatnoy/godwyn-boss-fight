"""Check the saved action, subframe paths, planted feet, and motion timing."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_v2_wip.blend'))
s=bpy.context.scene;r=bpy.data.objects['Armature'];sw=bpy.data.objects['Godwyn_Sword']
TIP=min(sw.data.vertices,key=lambda v:v.co.z).co.copy()
names=['Hips','Spine02','Spine01','Spine','RightShoulder','RightArm','RightForeArm','RightHand']
rows=[]
for i in range(4,361):
 f=i/4;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 rows.append({'f':f,'tip':sw.matrix_world@TIP,'q':{n:(r.matrix_world@r.pose.bones[n].matrix).to_quaternion() for n in names},'feet':{n:(r.matrix_world@r.pose.bones[n+'Foot'].matrix).translation.copy() for n in ['Left','Right']},'hip':(r.matrix_world@r.pose.bones['Hips'].matrix).translation.copy()})
for a,b in zip(rows,rows[1:]):
 dt=(b['f']-a['f'])/30;b['tip_speed']=(b['tip']-a['tip']).length/dt
 b['angular_speed']={n:math.degrees(2*math.acos(min(1,abs(a['q'][n].dot(b['q'][n])))))/dt for n in names}
def interval(a,b):return [x for x in rows if a<x['f']<=b]
def stats(a,b):
 rr=interval(a,b);ss=[x['tip_speed'] for x in rr]
 return {'mean_tip_m_s':sum(ss)/len(ss),'peak_tip_m_s':max(ss)}
def arc(a,b):
 rr=[x for x in rows if a<=x['f']<=b];p0=rr[0]['tip'];p1=rr[-1]['tip'];axis=(p1-p0).normalized()
 return {'length_m':sum((y['tip']-x['tip']).length for x,y in zip(rr,rr[1:])), 'chord_m':(p1-p0).length,'max_deviation_from_chord_m':max(((x['tip']-p0)-axis*(x['tip']-p0).dot(axis)).length for x in rr), 'points':[list(x['tip']) for x in rr]}
result={'frames':s.frame_end,'fps':s.render.fps,'engine':s.render.engine,'motion_blur':s.render.use_motion_blur,'shutter':s.render.motion_blur_shutter,
 'speed':{'anticipation':stats(1,31),'cut1':stats(37,42),'connector':stats(43,53),'cut2':stats(54,59),'heavy_recovery':stats(60,73),'settle':stats(83,90)},
 'arcs':{'cut1':arc(37,42),'cut2':arc(54,59)},
 'peak_world_rotation_frame':{label:{n:max(interval(a,b),key=lambda x:x['angular_speed'][n])['f'] for n in names} for label,a,b in [('first',30,43),('second',47,60)]},
 'planted_foot_drift_m':{n:max((x['feet'][n]-rows[156]['feet'][n]).length for x in rows if x['f']>=40) for n in ['Left','Right']},
 'left_foot_contact':list(next(x for x in rows if x['f']==40)['feet']['Left']),
 'hip_contact_heights':{str(f):next(x for x in rows if x['f']==f)['hip'].z for f in [1,34,40,46,57,65,79,84,90]}}
counts={}
act=r.animation_data.action
for layer in act.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:counts[k.interpolation]=counts.get(k.interpolation,0)+1
result['rig_key_interpolation']=counts
result['animated_secondary_bones']=len([p for p in r.pose.bones if p.name.startswith('phys_')])
assert set(counts)=={'BEZIER'},counts
assert result['planted_foot_drift_m']['Left']<.001
assert result['planted_foot_drift_m']['Right']<.001
assert all(x['max_deviation_from_chord_m']>.25 for x in result['arcs'].values())
(OUT/'v2_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='arcs'},indent=2),flush=True)
