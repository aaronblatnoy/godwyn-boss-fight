"""A new volumetric groom rooted on the replacement scalp; geometry clay stage."""
import bpy,sys,math,json,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_r5_groom_geometry import interp,build_group,smooth
from astra_char2_r5_head import front,hermite,W,BACK
from astra_char2_r5_armor import chest,PZ,PX,PF,PC
from astra_character_common import reset_pose
rng=np.random.default_rng(520260906)
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r5_clay.blend'));reset_pose()
for ob in list(bpy.data.objects):
 if ob.name.startswith(('AstraChar2_R5_Curves_','AstraChar2_R5_Control_','AstraChar2_R5_Strands_')):bpy.data.objects.remove(ob,do_unlink=True)

def collision(path,section):
 # Conservative scalp and armor envelopes. Roots remain exactly on the scalp.
 for j,p in enumerate(path):
  if j<2:continue
  x,y,z=p
  if 2.79<z<3.16 and abs(x)<hermite(z,W):
   fy=front(x,z);by=hermite(z,BACK)
   if fy<y<by:
    if section=='Back':p[1]=by+.002
    else:p[1]=fy-.002
  for side in [-1,1]:
   q=(p-np.array([side*.330,-.173,2.586]))/np.array([.19,.225,.16]);d=np.linalg.norm(q)
   if d<1.04 and p[2]>2.44:p[:]=np.array([side*.330,-.173,2.586])+q/max(d,1e-6)*np.array([.19,.225,.16])*1.04
  x,y,z=p
  if 1.99<z<2.66 and abs(x)<float(np.interp(z,PZ,PX)):
   cy=float(np.interp(z,PZ,PC));fy=chest(x,z)
   if section=='Front' and y>fy-.009:p[1]=fy-.009
   if section=='Back' and y<cy+(cy-fy)+.015:p[1]=cy+(cy-fy)+.015
 return path

def loose(side,section,count):
 K=64;paths=[];rads=[];t=np.linspace(0,1,K)
 for group in range(count//50):
  u,v=rng.random(2);phase=rng.uniform(0,math.tau)
  if section=='Front':
   x0=.002+.094*u;z0=3.088-.041*u*u+.035*v*(1-.60*u);z0=min(z0,3.142-.030*u*u)
   x0=min(x0,hermite(z0,W)*.90);y0=front(side*x0,z0)-.0006
   depth=rng.uniform(-.038,.023);length=rng.uniform(2.15,2.57);width=rng.uniform(.11,.17)
   guide=[[x0,y0,z0],[x0+.018,y0-.008,z0+.018*(1-2*u)],[.103+.011*u,-.337+depth,3.098-.035*u],[.108+.025*u,-.358+depth,2.99],[.109+.035*u,-.391+depth,2.86],[.135+.045*u,-.424+depth,2.70],[.16+.06*u,-.473+depth,2.51],[.18+.10*u,-.48+depth,length]]
  elif section=='Side':
   z0=rng.uniform(3.035,3.135);x0=hermite(z0,W)*rng.uniform(.88,.99);y0=-.24+rng.uniform(-.05,.05)
   crown=group%2==0
   if crown:
    z0=rng.uniform(3.115,3.157);x0=hermite(z0,W)*rng.uniform(.035,.94);y0=front(side*x0,z0)-.0006
   frontside=rng.random()<.58;depth=rng.uniform(-.04,.05);length=rng.uniform(1.94,2.43);outer=rng.uniform(.26,.42)
   gy=-.40 if frontside else .095
   guide=[[x0,y0,z0],[x0+.012,y0+.006,z0+(.006-.020*u if crown else -.009)],[.132+u*.023,-.23+depth,3.035],[.185+u*.032,gy*.6+depth,2.84],[.26+u*.055,gy+depth,2.70],[outer,gy+depth,2.52],[outer+.025*math.sin(phase),gy+depth,2.28],[outer-.04,gy+.04+depth,length]]
  else:
   z0=rng.uniform(3.04,3.15);x0=hermite(z0,W)*rng.uniform(.05,.90);y0=hermite(z0,BACK)+.001
   depth=rng.uniform(-.025,.08);length=rng.uniform(1.86,2.32);outer=rng.uniform(.10,.34)
   guide=[[x0,y0,z0],[x0+.012,y0+.018,z0-.012],[.13+u*.035,.025+depth,2.99],[.16+u*.08,.10+depth,2.80],[outer,.19+depth,2.65],[outer+.035,.235+depth,2.43],[outer+.045,.25+depth,2.18],[outer-.025,.22+depth,length]]
  guide=np.asarray(guide);guide[:,0]*=side;base=interp(guide,K)
  waveamp=rng.uniform(.003,.012);freq=rng.uniform(1.3,3.3)
  base[:,0]+=side*waveamp*np.sin(t*math.tau*freq+phase)*smooth(t*4)
  base[:,1]+=waveamp*.7*np.sin(t*math.tau*freq+phase+.9)*smooth(t*4)
  base=collision(base,section)
  for strand in range(50):
   p=base.copy();a,b=rng.normal(0,.0023,2);spread=.6+.7*np.sin(math.pi*t)**2
   p[:,0]+=a*spread;p[:,1]+=b*spread
   p[:,2]+=rng.normal(0,.0014)*(1-t)
   micro=rng.uniform(.00025,.0012);ph=rng.uniform(0,math.tau)
   p[:,0]+=micro*np.sin(t*math.tau*rng.uniform(4,8)+ph)*smooth(t*5)
   p[:,1]+=micro*np.cos(t*math.tau*rng.uniform(3,7)+ph)*smooth(t*5)
   # A distributed tip length prevents a hard terminator line.
   p[-10:,2]-=smooth(np.linspace(0,1,10))*rng.uniform(0,.055)
   if section=='Front':
    mask=(p[:,2]<3.015)&(p[:,2]>2.78);p[mask,0]=side*np.maximum(abs(p[mask,0]),.096+.008*np.clip((3.015-p[mask,2])/.15,0,1))
   p=collision(p,section)
   radius=rng.uniform(.000045,.000075)*(1-.92*t**2.8);radius*=np.minimum(1,.5+8*t)
   paths.append(p);rads.append(radius)
 return np.asarray(paths),np.asarray(rads)

report=[]
for side,label in [(1,'L'),(-1,'R')]:
 for section,count in [('Front',4500),('Side',7000),('Back',6500)]:
  p,r=loose(side,section,count);chain='back' if section=='Back' else 'front_'+label
  report.append(build_group(label+'_'+section,p,r,chain,0));del p,r
 # Three tightly interwoven bundles in each of three visible thin plaits.
 paths=[];radii=[];K=144;t=np.linspace(0,1,K)
 for braid in range(3):
  bx=.117+.027*braid;by=-.394+.028*braid;end=2.35+.095*braid
  axis=interp([[side*(.072+.013*braid),-.318,3.10-.015*braid],[side*bx,by,3.005],[side*(bx+.009),by-.022,2.88],[side*(bx+.025),-.446,2.70],[side*(bx+.040),-.485,2.50],[side*(bx+.055),-.48,end]],K)
  amp=.0035 if braid==0 else .0027;turns=28 if braid==0 else 25
  for bundle in range(3):
   phase=t*math.tau*turns+bundle*math.tau/3
   spine=axis.copy();spine[:,0]+=amp*np.sin(phase);spine[:,1]+=amp*.66*np.sin(2*phase)
   for strand in range(150):
    p=spine.copy();ang=rng.uniform(0,math.tau);rr=math.sqrt(rng.random())*amp*.58
    p[:,0]+=rr*np.cos(ang+phase*.08);p[:,1]+=rr*np.sin(ang+phase*.08)
    p[:,0]+=.00015*np.sin(t*math.tau*42+rng.uniform(0,6.28));p=collision(p,'Front')
    paths.append(p);radii.append(rng.uniform(.000044,.000065)*(1-.83*t**9))
 report.append(build_group(label+'_Braids',np.array(paths),np.array(radii),'front_'+label,0))
reset_pose();assert len(bpy.data.objects['Armature'].data.bones)==121 and len(bpy.data.actions)==0
bpy.context.preferences.filepaths.save_version=0;bpy.context.scene['astra_char2_round5']='New structural head and volumetric native groom. CLAY GATE PENDING.'
bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_r5_groom_clay.blend'))
(O/'r5_groom.json').write_text(json.dumps({'groups':report,'native_strands':sum(g['curves'] for g in report),'braid_count':6,'interwoven_bundles_per_braid':3,'materials':'Existing hair materials referenced unchanged; all gates rendered with diffuse clay override.','rig':'Original 121 bones and rest transforms preserved.'},indent=2));print('NEW GROOM COMPLETE',flush=True)
