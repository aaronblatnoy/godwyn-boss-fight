"""Offline arm trial from fresh naturalness samples; no scene writes."""
import json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Quaternion,Vector
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/'renders/astra/naturalness_armfix_before.json').read_text());rows=p['rows'];ts=np.array([r['f'] for r in rows])
def norm(v):return v/np.linalg.norm(v)
def smooth(t):t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)
def env(f,a,b,c,d):return float(smooth((f-a)/(b-a))*(1-smooth((f-c)/(d-c))))
def qarr(q):return np.array(q)
def log(a,b):
 q=Quaternion(b)@Quaternion(a).inverted();q.normalize()
 if q.w<0:q.negate()
 v=np.array([q.x,q.y,q.z]);m=np.linalg.norm(v)
 return v*(math.degrees(2*math.atan2(m,q.w))/m if m>1e-12 else 0)
def speeds(qs):return np.array([np.linalg.norm(log(a,b))*4 for a,b in zip(qs,qs[1:])])
def peak(qs,lo=30,hi=44):
 sp=speeds(qs);ids=np.where((ts[1:]>lo)&(ts[1:]<=hi))[0];ix=ids[np.argmax(sp[ids])];return float(ts[ix+1]),float(sp[ix])
S=np.array([r['bones']['RightArm']['head'] for r in rows]);E=np.array([r['bones']['RightForeArm']['head'] for r in rows]);W=np.array([r['bones']['RightHand']['head'] for r in rows]);QH=[Quaternion(r['bones']['RightHand']['world_q']) for r in rows]
QA=[Quaternion(r['bones']['RightArm']['world_q']) for r in rows];QF=[Quaternion(r['bones']['RightForeArm']['world_q']) for r in rows]
newE=E.copy();theta=[];dev=[];targets=[]
for i,f in enumerate(ts):
 x=np.array(QH[i]@Vector((1,0,0)));fore=norm(W[i]-E[i]);old=math.degrees(math.asin(np.clip(fore@x,-1,1)))
 target=old+env(f,44,45.5,51.5,53)*(max(old,-25)-old);targets.append(target)
 if not 44<f<53:theta.append(0);dev.append(old);continue
 axis=norm(W[i]-S[i]);C=S[i]+axis*((E[i]-S[i])@axis);u=norm(E[i]-C);vv=np.cross(axis,u);radius=np.linalg.norm(E[i]-C);l2=np.linalg.norm(W[i]-E[i])
 A=radius*(u@x);B=radius*(vv@x);c=(W[i]-C)@x-l2*math.sin(math.radians(target));amp=math.hypot(A,B)
 phi=math.atan2(B,A);ang=math.acos(np.clip(c/amp,-1,1));roots=[(v+math.pi)%(2*math.pi)-math.pi for v in [phi+ang,phi-ang]]
 t=min(roots,key=abs);theta.append(math.degrees(t));newE[i]=C+radius*(u*math.cos(t)+vv*math.sin(t));dev.append(math.degrees(math.asin(np.clip(norm(W[i]-newE[i])@x,-1,1))))
# Rotation-minimizing transport splits forearm orientation into aim and axial roll.
axes=[Vector(norm(w-e)) for w,e in zip(W,E)];base=[QF[0].copy()]
for i in range(1,len(ts)):base.append(axes[i-1].rotation_difference(axes[i])@base[-1])
phi=[]
for ax,q,b in zip(axes,QF,base):
 dq=q@b.inverted();phi.append(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(ax),dq.w))
phi=np.unwrap(phi)
trials=[]
for delay in [.5,.625,.75,.875,1,1.125,1.25]:
 for window in [(34,37,40.5,44),(34,36,41,44),(35,37,41,44),(35,37,40,43)]:
  qs=[];offsets=[]
  for i,f in enumerate(ts):
   lag=delay*env(f,*window);roll=float(np.interp(f-lag,ts,phi)-phi[i]);offsets.append(roll);qs.append(Quaternion(axes[i],roll)@QF[i])
  pk=peak(qs);ids=np.where((ts[1:]>36)&(ts[1:]<=42))[0];v=np.array([log(x,y)*4 for x,y in zip(qs,qs[1:])]);acc=np.linalg.norm(np.diff(v,axis=0)*4,axis=1)
  trials.append({'delay':delay,'window':window,'peak':pk,'max_roll_deg':float(np.degrees(np.max(np.abs(offsets)))),'max_acceleration':float(max(acc)),'offsets':offsets})
print('BASE PEAKS',peak(QA),peak(QF),peak(QH))
for t in trials:print('TRIAL',json.dumps({k:v for k,v in t.items() if k!='offsets'}))
print('WRIST',min(dev),ts[np.argmin(dev)],'max theta',min(theta),max(theta))
print('ELBOW DELTAS',[(float(ts[i]),list(newE[i]-E[i])) for i in range(len(ts)) if ts[i] in [44,45,46,47,47.25,48,49,50,51,52,53]])
# Rank accepted delays by lowest added roll, then target 0.75f lead.
valid=[t for t in trials if 39.5<=t['peak'][0]<=40 and t['peak'][1]<70]
if not valid:raise RuntimeError('No suitable continuous forearm roll trial')
best=min(valid,key=lambda t:(t['max_roll_deg'],abs(t['peak'][0]-39.75)))
print('SELECTED', {k:v for k,v in best.items() if k!='offsets'})
plan={'times':ts.tolist(),'elbows':newE.tolist(),'theta_degrees':theta,'target_deviation':targets,'predicted_deviation':dev,'roll_offset_rad':best['offsets'],'timing_trial':{k:v for k,v in best.items() if k!='offsets'}}
(ROOT/'renders/astra/naturalness_armfix_plan.json').write_text(json.dumps(plan,indent=2))
