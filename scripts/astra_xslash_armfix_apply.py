"""Two bounded sword-arm corrections, baked as rotation F-curves only.
The original scene is immutable. World hand transform is solved again at 1/32
frame so changing the parent's rotation cannot displace the blade between keys.
"""
import bpy,sys,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'models/astra_xslash_v2_final_prefix2.blend';target=ROOT/'models/astra_xslash_v2_armfix_trial.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene
assert scene.render.engine=='BLENDER_EEVEE'
rig=bpy.data.objects['Armature'];AW=rig.matrix_world.copy();AI=AW.inverted();names=['RightArm','RightForeArm','RightHand']
fcs=[fc for la in rig.animation_data.action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves]
paths={rig.pose.bones[n].path_from_id('rotation_quaternion'):n for n in names}
def digest_unedited():
 return hashlib.sha256(repr([(fc.data_path,fc.array_index,[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type) for k in fc.keyframe_points]) for fc in fcs if fc.data_path not in paths]).encode()).hexdigest()
def smooth(t):t=max(0,min(1,t));return t**3*(10-15*t+6*t*t)
def env(f,a,b,c,d):return smooth((f-a)/(b-a))*(1-smooth((f-c)/(d-c)))
def norm(v):return v/np.linalg.norm(v)
before_digest=digest_unedited();vis=[(o,o.hide_viewport) for o in scene.objects if o.type=='MESH']
for o,_ in vis:o.hide_viewport=True
times=np.array([33+i/32 for i in range(21*32+1)]);original=[]
for f in times:
 scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 original.append({n:(AW@rig.pose.bones[n].matrix).copy() for n in names})
axes=[(m['RightHand'].translation-m['RightForeArm'].translation).normalized() for m in original]
QF=[m['RightForeArm'].to_quaternion() for m in original];base=[QF[0].copy()]
for i in range(1,len(times)):base.append(axes[i-1].rotation_difference(axes[i])@base[-1])
phi=[]
for ax,q,b in zip(axes,QF,base):
 dq=q@b.inverted();phi.append(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(ax),dq.w))
phi=np.unwrap(phi);outputs={};maxerr=0;maxpole=0;maxroll=0
for i,f in enumerate(times):
 if not 34<f<53:continue
 lag=.5*env(f,34,37,40.5,44);roll=.9*float(np.interp(f-lag,times,phi)-phi[i]);old=original[i]
 S,E,W=[old[n].translation.copy() for n in names];newE=E.copy();pole=0
 if 44<f<53:
  x=np.array(old['RightHand'].to_quaternion()@Vector((1,0,0)));s,e,w=map(np.array,[S,E,W]);fore=norm(w-e)
  deviation=math.degrees(math.asin(np.clip(fore@x,-1,1)));desired=deviation+env(f,44,46,51,53)*(max(deviation,-25)-deviation)
  if abs(desired-deviation)>1e-8:
   axis=norm(w-s);C=s+axis*((e-s)@axis);u=norm(e-C);v=np.cross(axis,u);radius=np.linalg.norm(e-C);l2=np.linalg.norm(w-e)
   A=radius*(u@x);B=radius*(v@x);c=(w-C)@x-l2*math.sin(math.radians(desired));p=math.atan2(B,A);ang=math.acos(np.clip(c/math.hypot(A,B),-1,1))
   pole=min([(z+math.pi)%(2*math.pi)-math.pi for z in [p+ang,p-ang]],key=abs);newE=Vector(C+radius*(u*math.cos(pole)+v*math.sin(pole)))
 scene.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
 state={n:(rig.pose.bones[n].location.copy(),rig.pose.bones[n].scale.copy(),rig.pose.bones[n].rotation_quaternion.copy()) for n in names}
 def set_rotation(n,q):
  p=rig.pose.bones[n];p.matrix=AI@Matrix.LocRotScale(old[n].translation,q,old[n].to_scale())
  p.location=state[n][0];p.scale=state[n][1];bpy.context.view_layer.update()
 if abs(pole)>1e-9:set_rotation('RightArm',(E-S).rotation_difference(newE-S)@old['RightArm'].to_quaternion())
 fq=(W-E).rotation_difference(W-newE)@old['RightForeArm'].to_quaternion()
 if abs(roll)>1e-9:fq=Quaternion((W-newE).normalized(),roll)@fq
 set_rotation('RightForeArm',fq);set_rotation('RightHand',old['RightHand'].to_quaternion())
 err=((AW@rig.pose.bones['RightHand'].matrix).translation-W).length;maxerr=max(maxerr,err);assert err<.00001,(f,err)
 outputs[float(f)]={}
 for n in names:
  if n=='RightArm' and f<=44:continue
  q=rig.pose.bones[n].rotation_quaternion.copy();q.normalize()
  if q.dot(state[n][2])<0:q.negate()
  outputs[float(f)][n]=list(q)
 maxpole=max(maxpole,abs(math.degrees(pole)));maxroll=max(maxroll,abs(math.degrees(roll)))
count=0;added=0
for fc in fcs:
 if fc.data_path not in paths:continue
 n=paths[fc.data_path];start=44 if n=='RightArm' else 34;stop=53
 existing={float(k.co.x):k for k in fc.keyframe_points}
 # Preserve the outside-window interpolation handles exactly.
 lh=existing[start].handle_left.copy();rh=existing[stop].handle_right.copy()
 for f,out in outputs.items():
  if n in out and f not in [44,53] and f in existing:
   existing[f].co.y=out[n][fc.array_index];count+=1
 existing_times=set(existing)
 for f,out in outputs.items():
  if n in out and f not in [44,53] and f not in existing_times:
   k=fc.keyframe_points.insert(f,out[n][fc.array_index],options={'FAST'});k.interpolation='BEZIER';k.handle_left_type=k.handle_right_type='AUTO_CLAMPED';added+=1
 fc.update()
 # Reacquire references after insertion reallocates the key array.
 keys={float(k.co.x):k for k in fc.keyframe_points}
 keys[start].handle_left_type='FREE';keys[start].handle_left=lh
 keys[stop].handle_right_type='FREE';keys[stop].handle_right=rh
 fc.update()
assert digest_unedited()==before_digest
for o,v in vis:o.hide_viewport=v
scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(target))
result={'source':str(source),'target':str(target),'changed_existing_quaternion_values':count,'added_quaternion_keys':added,'unchanged_curve_sha256':before_digest,'max_hand_head_error_during_solve_m':maxerr,'edited_bones':names,'edit_windows':{'roll':[34,44],'pole':[44,53]},'bake_spacing_frames':1/32,'max_elbow_pole_rotation_deg':maxpole,'max_roll_offset_deg':maxroll,'geometry_settings_edits':False}
(ROOT/'renders/astra/naturalness_armfix_apply.json').write_text(json.dumps(result,indent=2));print('ARMFIX APPLY',json.dumps(result),flush=True)
