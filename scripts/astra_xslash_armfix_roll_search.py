"""Search smaller forearm roll corrections while keeping the weapon world-locked."""
import sys,json,math
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/'renders/astra/naturalness_armfix_before.json').read_text());rows=p['rows'];ts=np.array([r['f'] for r in rows]);QF=[Quaternion(r['bones']['RightForeArm']['world_q']) for r in rows];QL=[Quaternion(r['bones']['RightForeArm']['q']) for r in rows]
axes=[(Vector(r['bones']['RightHand']['head'])-Vector(r['bones']['RightForeArm']['head'])).normalized() for r in rows]
def log(a,b):
 q=b@a.inverted();q.normalize()
 if q.w<0:q.negate()
 v=np.array([q.x,q.y,q.z]);m=np.linalg.norm(v);return v*(math.degrees(2*math.atan2(m,q.w))/m if m>1e-12 else 0)
def smooth(t):t=np.clip(t,0,1);return t**3*(10-15*t+6*t*t)
def env(f,a,b,c,d):return smooth((f-a)/(b-a))*(1-smooth((f-c)/(d-c)))
base=[QF[0].copy()]
for i in range(1,len(ts)):base.append(axes[i-1].rotation_difference(axes[i])@base[-1])
phi=np.unwrap([2*math.atan2(Vector(((q@b.inverted()).x,(q@b.inverted()).y,(q@b.inverted()).z)).dot(ax),(q@b.inverted()).w) for q,b,ax in zip(QF,base,axes)])
trials=[]
for delay in np.arange(.25,1.51,.125):
 for gain in np.arange(.2,1.01,.1):
  lag=delay*env(ts,34,37,40.5,44);offset=gain*(np.interp(ts-lag,ts,phi)-phi)
  qs=[Quaternion(ax,float(o))@q for ax,o,q in zip(axes,offset,QF)]
  speed=np.array([np.linalg.norm(log(a,b))*4 for a,b in zip(qs,qs[1:])]);ii=np.where((ts[1:]>30)&(ts[1:]<=44))[0];ix=ii[np.argmax(speed[ii])];peak=ts[ix+1]
  if not 39.5<=peak<=39.75:continue
  qlocal=[ql@old.inverted()@new for ql,old,new in zip(QL,QF,qs)];qints=qlocal[::4];vel=np.array([log(a,b) for a,b in zip(qints,qints[1:])]);acc=np.linalg.norm(np.diff(vel,axis=0),axis=1)
  worldvel=np.array([log(a,b)*4 for a,b in zip(qs,qs[1:])]);wacc=np.linalg.norm(np.diff(worldvel,axis=0)*4,axis=1)
  trials.append({'delay':float(delay),'gain':float(gain),'peak':float(peak),'speed':float(speed[ix]),'max_roll':float(np.max(abs(offset))*180/math.pi),'max_local_acc':float(max(acc)),'max_world_acc':float(max(wacc)),'offsets':offset.tolist()})
trials.sort(key=lambda t:(t['max_local_acc'],t['max_roll']))
for t in trials[:10]:print({k:v for k,v in t.items() if k!='offsets'})
if trials:
 best=trials[0];(ROOT/'renders/astra/naturalness_armfix_roll_search.json').write_text(json.dumps(best,indent=2))
