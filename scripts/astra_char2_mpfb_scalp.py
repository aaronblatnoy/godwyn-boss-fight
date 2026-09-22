"""Fine short scalp layers soften the roots of the long center-part groom."""
import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_r5_groom_geometry import build_group
from astra_char2_mpfb_clay import render_views
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_groom_i10.blend'));reset_pose()
h=bpy.data.objects['AstraChar2_Mpfb_Head'];tree=BVHTree.FromObject(h,bpy.context.evaluated_depsgraph_get());rng=np.random.default_rng(611)
fs=[]
for f in h.data.polygons:
 p=f.center;threshold=max(3.04,3.108-.5*abs(p.x)) if p.y<-.29 else (3.035 if p.y<-.17 else 2.99)
 if p.z>threshold:fs.append(f)
prob=np.array([f.area for f in fs]);prob/=prob.sum();paths=[];radii=[];N=14000;K=18;t=np.linspace(0,1,K)
for i in range(N):
 f=fs[rng.choice(len(fs),p=prob)];vv=[np.array(h.data.vertices[j].co) for j in f.vertices];u,v=rng.random(2);root=(1-u)*(1-v)*vv[0]+u*(1-v)*vv[1]+u*v*vv[2]+(1-u)*v*vv[-1]
 hit,normal,_,_=tree.find_nearest(Vector(root));root=np.array(hit);n=np.array(normal)
 desired=np.array((np.sign(root[0])*.45,.65,-.20 if root[1]>-.2 else .20));tan=desired-n*np.dot(desired,n);tan/=max(np.linalg.norm(tan),.01)
 length=rng.uniform(.018,.05);path=[];height=rng.uniform(.002,.007)
 for k,a in enumerate(t):
  q=root+tan*length*a;loc,no,_,_=tree.find_nearest(Vector(q));path.append(np.array(loc)+np.array(no)*(.00025+height*np.sin(a*np.pi*.65)))
 paths.append(path);radii.append(rng.uniform(.000045,.000067)*np.maximum(.05,1-t**3))
r=build_group('MPFB_ScalpBed',paths,radii,'back',None)
for name in ['AstraChar2_R5_Control_MPFB_ScalpBed','AstraChar2_R5_Strands_MPFB_ScalpBed']:
 ob=bpy.data.objects[name];ids=list(range(len(ob.data.vertices)))
 for vg in ob.vertex_groups:vg.remove(ids)
 ob.vertex_groups['Head'].add(ids,1,'REPLACE')
(O/'mpfb_groom_i11.json').write_text(json.dumps({'source':'groom_i10','addition':r,'short_layers':'14,000 fine scalp-rooted strands, 18–50 mm, attached to Head; long groom retains all 12 hair bones.'},indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2_mpfb_groom_i11.blend'))
render_views('mpfb_groom_i11_clay',('front','side','three_quarter','body'))
