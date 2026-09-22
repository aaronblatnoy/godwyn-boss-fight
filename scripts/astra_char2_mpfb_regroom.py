"""MPFB scalp-native layered groom, using the proven R5 skin/control/export machinery."""
import bpy,sys,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_groom_geometry import build_group,interp
from astra_char2_r5_geometry import mesh,bind
from astra_char2_mpfb_clay import render_views

def main():
 bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_graft_i04.blend'));reset_pose()
 h=bpy.data.objects['AstraChar2_Mpfb_Head'];tree=BVHTree.FromObject(h,bpy.context.evaluated_depsgraph_get());rng=np.random.default_rng(604)
 for ob in bpy.data.objects:
  if ob.name.startswith(('AstraChar2_R4_Curves_','AstraChar2_R4_Strands_','AstraChar2_R4_Control_')):ob.hide_render=True;ob.hide_set(True)
 def arc(sign,y,angle):
  center=Vector((0,-.245,3.005));d=Vector((sign*.16*math.sin(angle),y+.245,.16*math.cos(angle)))
  hit,n,_,_=tree.ray_cast(center,d.normalized(),.5)
  if hit:return np.array(hit+n*(.007+.010*math.sin(angle)))
  hit,n,_,_=tree.find_nearest(center+d);return np.array(hit+n*(.007+.010*math.sin(angle)))
 def surface(x,y):
  hit,n,_,_=tree.ray_cast(Vector((x,y,3.5)),Vector((0,0,-1)),1)
  if hit:return np.array(hit+n*.0012)
  hit,n,_,_=tree.find_nearest(Vector((x,y,3.10)));return np.array(hit+n*.0012)
 def back(x,z):
  hit,n,_,_=tree.ray_cast(Vector((x,.7,z)),Vector((0,-1,0)),1.2)
  if hit:return np.array(hit+n*.004)
  hit,n,_,_=tree.find_nearest(Vector((x,-.09,z)));return np.array(hit+n*.004)
 def collide(path):
  for k,q in enumerate(path):
   if q[2]>2.90:
    hit,n,_,_=tree.find_nearest(Vector(q))
    if hit and (Vector(q)-hit).dot(n)<.0008:path[k]=np.array(hit+n*(.0008 if k==0 else .002))
  return path
 reports=[]
 for sign,side in [(-1,'L'),(1,'R')]:
  for category,count in [('Front',2400),('Side',3000),('Back',3600)]:
   paths=[];radii=[];K=64
   for g in range(count//40):
    u=(g+.5)/(count//40);phase=rng.uniform(0,math.tau)
    if category=='Front':
     y=-.375+.095*u;root=surface(sign*.003,y)
     guides=[root,(sign*.040,y+.028,3.15),(sign*.095,y+.048,3.125),
             (sign*.132,y+.042,3.025),(sign*.147,y+.022,2.93),
             (sign*(.17+.035*u),-.405,2.76),(sign*(.18+.045*u),-.44,2.52),
             (sign*(.18+.075*u),-.43,2.32),(sign*(.16+.07*u),-.405,2.12+.12*u)]
    elif category=='Side':
     y=-.275+.145*u;root=surface(sign*.002,y)
     guides=[root,arc(sign,y,.35),arc(sign,y,.75),arc(sign,y,1.15),
             (sign*.146,y+.01,2.95),(sign*.162,y+.03,2.86),(sign*(.20+.07*u),-.015+.08*u,2.73),
             (sign*(.27+.05*u),.08+.07*u,2.58),(sign*(.27+.06*u),.11+.07*u,2.34),(sign*(.24+.07*u),.08+.1*u,2.04+.12*u)]
    else:
     x=sign*(.003+.113*u);root=surface(x,-.17)
     guides=[root,back(x,min(root[2]-.014,3.085)),back(x,min(root[2]-.05,3.035)),back(x,2.985),back(x,2.93),back(x,2.86),
             (sign*(.035+.14*u),.012,2.77),(sign*(.06+.17*u),.13,2.60),(sign*(.065+.18*u),.18,2.36),
             (sign*(.06+.20*u),.16,2.05+.10*u)]
    guide=collide(interp(guides,K));t=np.linspace(0,1,K)
    for j in range(40):
     p=guide.copy();spread=rng.normal(0,.0017,3);spread[2]*=.35
     p+=spread[None,:]*(.6+.4*np.sin(t*np.pi))[:,None]
     p[:,0]+=sign*.007*np.sin(t*math.tau*2.2+phase)*np.sin(t*np.pi)**2
     p[:,1]+=.004*np.sin(t*math.tau*2+phase)*np.sin(t*np.pi)**2
     p[:,2]+=rng.normal(0,.014)*t**3
     hit,n,_,_=tree.find_nearest(Vector(p[0]));p[0]=hit+n*.0005
     p=collide(p)
     paths.append(p)
     radii.append(rng.uniform(.000045,.000067)*np.maximum(.06,1-t**5))
   label='MPFB_'+side+'_'+category;chain='front_'+side if category=='Front' else 'back'
   reports.append(build_group(label,paths,radii,chain,None))
  # Three physically interwoven bundles per braid, with fine parallel constituent hairs.
  paths=[];radii=[];K=160;t=np.linspace(0,1,K)
  for b in range(2):
   x=.085+.012*b;y=-.368+.014*b
   guides=[surface(sign*x,y),(sign*.123,y-.015,3.015),(sign*(.137+.009*b),-.40,2.92),
           (sign*(.16+.012*b),-.455,2.74),(sign*(.18+.02*b),-.475,2.55),
           (sign*(.17+.025*b),-.465,2.34),(sign*(.155+.024*b),-.445,2.18+.035*b)]
   axis=collide(interp(guides,K));amp=.0034*np.minimum(1,t*20)*np.minimum(1,(1-t)*25)
   for bundle in range(3):
    theta=t*math.tau*24+bundle*math.tau/3
    for strand in range(75):
     q=axis.copy();a=rng.uniform(0,math.tau);rr=.00155*math.sqrt(rng.random())
     q[:,0]+=amp*np.sin(theta)+rr*math.cos(a);q[:,1]+=.7*amp*np.sin(2*theta)+rr*math.sin(a)
     hit,n,_,_=tree.find_nearest(Vector(q[0]));q[0]=hit+n*.0005
     paths.append(collide(q));radii.append(np.full(K,rng.uniform(.000048,.000062))*np.maximum(.05,1-t**9))
  reports.append(build_group('MPFB_'+side+'_Braids',paths,radii,'front_'+side,None))
 # Pin actual root samples to Head even where a root lies below the historical z threshold.
 for rep in reports:
  label=rep['name'];cu=bpy.data.objects['AstraChar2_R5_Curves_'+label];n=cu['groom_strands'];k=cu['groom_points_per_strand'];ek=cu['export_points_per_strand']
  for ob,ids in [(bpy.data.objects['AstraChar2_R5_Control_'+label],list(range(0,n*k,k))),
                 (bpy.data.objects['AstraChar2_R5_Strands_'+label],[j*ek*3+c for j in range(n) for c in range(3)])]:
   for vg in ob.vertex_groups:vg.remove(ids)
   ob.vertex_groups['Head'].add(ids,1,'REPLACE')
 old=bpy.data.objects['AstraChar2_R4_Scalp'];old.data.clear_geometry();old.hide_render=True
 scalp=bpy.data.objects['AstraChar2_R4_ScalpRoots'];mats=list(scalp.data.materials)
 fs=[f for f in h.data.polygons if f.center.z>(3.13-.31*abs(f.center.x) if f.center.y<-.28 else 2.965)]
 used=sorted({i for f in fs for i in f.vertices});remap={i:j for j,i in enumerate(used)}
 scalp=mesh(scalp.name,[tuple(h.data.vertices[i].co+h.data.vertices[i].normal*.0003) for i in used],[tuple(remap[i] for i in f.vertices) for f in fs],mats)
 scalp.matrix_world.identity();bind(scalp,lambda p:{'Head':1});scalp.hide_render=True;scalp.hide_set(True)
 (O/'mpfb_groom_i10.json').write_text(json.dumps({'method':'Regenerated scalp-native guides, fine clumps and four three-bundle interwoven braids; R5 binding/export machinery','groups':reports,'total_strands':sum(r['curves'] for r in reports),'body_source':'approved collar bank + corrected graft04'},indent=2))
 bpy.context.preferences.filepaths.save_version=0;reset_pose();bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_groom_i10.blend'))
 render_views('mpfb_groom_i10_clay',('front','side','three_quarter','body'))
if __name__=='__main__':main()
