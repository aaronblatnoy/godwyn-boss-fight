import bpy,bmesh,numpy as np,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
def weld(o):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.065);bm.to_mesh(o.data);bm.free();o.data.update()
 for p in o.data.polygons:p.use_smooth=True
 if o.data.has_custom_normals:o.data.normals_split_custom_set([(0,0,0)]*len(o.data.loops))
def weight_fix(o):
 p=np.array([v.co[:] for v in o.data.vertices],dtype=np.float32);n=len(p);names=[g.name for g in o.vertex_groups];ids={k:i for i,k in enumerate(names)}
 w=np.zeros((n,len(names)),dtype=np.float32)
 for v in o.data.vertices:
  for g in v.groups:w[v.index,g.group]=g.weight
 original=w.copy();arm=bpy.data.objects['Armature'];x,y,z=p.T
 def smooth(a,b,v):
  t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
 # Analytic arm envelopes use real joint HEADS, never the importer's oversized display tails.
 for side in ['Right','Left']:
  ai=[ids[side+s] for s in ['Shoulder','Arm','ForeArm','Hand']]
  shoulder=np.array(arm.data.bones[side+'Arm'].head_local);elbow=np.array(arm.data.bones[side+'ForeArm'].head_local);hand=np.array(arm.data.bones[side+'Hand'].head_local)
  ds=[];ts=[]
  tip=hand+(np.array(arm.data.bones[side+'Hand'].tail_local)-hand)*.007
  for a,b in [(shoulder,elbow),(elbow,hand),(hand,tip)]:
   d=b-a;t=np.clip(((p-a)@d)/(d@d),0,1);ds.append(np.linalg.norm(p-a-t[:,None]*d,axis=1));ts.append(t)
  # Front of the hanging cape is separated from the wrist by a smooth depth gate.
  upper=1-smooth(12,24,ds[0]);lower=1-smooth(8,15,ds[1])
  upper*=smooth(203,227,z);lower*=1-smooth(217,237,z)
  glove=(1-smooth(8,15,ds[2]))*(1-smooth(hand[2]+1,hand[2]+16,z))
  env=np.maximum(np.maximum(upper,lower),glove)
  env*=1-smooth(-10,4,y)
  env*=smooth(22,34,np.abs(x))
  env*=smooth(102,120,z)
  env*=1-smooth(270,281,z)
  env*= (x>0) if side=='Left' else (x<0)
  # Existing hair is independently rigged and must not attach to nearby arm bones.
  hair=w[:,[i for i,k in enumerate(names) if 'hair' in k]].sum(1)
  env*=1-smooth(.1,.6,hair)
  old=w[:,ai].sum(1);affected=((old>.0001)|(env>.0001))
  base=w.copy();base[:,ai]=0
  sums=base.sum(1);empty=sums<.001
  for row in np.where(empty & affected)[0]:
   if y[row]>-8 and z[row]<243:
    chain='R' if x[row]<-15 else ('L' if x[row]>15 else 'C');level=int(np.clip(round((242-z[row])/33.43),0,6));base[row,ids[f'phys_cape_{chain}_{level:02d}']]=1
   else:base[row,ids['Spine' if z[row]>236 else 'Spine01' if z[row]>212 else 'Spine02']]=1
  base/=np.maximum(base.sum(1)[:,None],.00001)
  aW=np.zeros_like(w)
  fore=smooth(.70,1,ts[0])*(1-smooth(222,241,z));aW[:,ids[side+'Arm']]=1-fore
  h=smooth(.68,1,ts[1]);aW[:,ids[side+'ForeArm']]=fore*(1-h);aW[:,ids[side+'Hand']]=fore*h
  w[affected]=base[affected]*(1-env[affected,None])+aW[affected]*env[affected,None]
 # Diffuse on the welded surface, eliminating abrupt changes across adjacent triangles.
 edges=np.array([e.vertices[:] for e in o.data.edges]);a,b=edges.T
 degree=np.bincount(np.r_[a,b],minlength=n).astype(np.float32)
 zone=(z>100)&(z<282)&(np.abs(x)>18);zonef=zone.astype(np.float32)[:,None]*.65
 for _ in range(36):
  avg=np.empty_like(w)
  for k in range(w.shape[1]):avg[:,k]=(np.bincount(a,weights=w[b,k],minlength=n)+np.bincount(b,weights=w[a,k],minlength=n))/np.maximum(degree,1)
  w=w*(1-zonef)+avg*zonef
 # Four influences, normalized. UV split vertices have already been welded.
 ix=np.argpartition(w,-4,axis=1)[:,-4:];keep=np.zeros_like(w);np.put_along_axis(keep,ix,np.take_along_axis(w,ix,axis=1),axis=1);w=keep/np.maximum(keep.sum(1)[:,None],1e-8)
 for g in o.vertex_groups:g.remove(list(range(n)))
 for i in range(n):
  for k in np.where(w[i]>.00001)[0]:o.vertex_groups[int(k)].add([i],float(w[i,k]),'REPLACE')
 print('WEIGHTS reassigned',int((np.abs(w-original).max(1)>.01).sum()),'vertices',n,flush=True)
 (OUT/'weight_reassignment.json').write_text(json.dumps({'vertices':n,'changed_over_1_percent':int((np.abs(w-original).max(1)>.01).sum()),'max_influences':4,'graph_diffusion_iterations':36},indent=2))
def fix_sword(o):
 # Convert imported bone-tail parenting to a conventional skin with one rigid influence.
 p=np.array([v.co[:] for v in o.data.vertices]);print('SWORD profile',[(a,int(((p[:,2]>=a)&(p[:,2]<a+10)).sum()),p[(p[:,2]>=a)&(p[:,2]<a+10)].mean(0).tolist()) for a in range(0,210,10)],flush=True)
 # Sword grip is near the top of the source object; source blade points down.
 o.parent=None;o.matrix_world=Matrix.Diagonal((.01,.01,.01,1))
 o.location=(-1.3,.6,0)
def main():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'models/godwyn_game.glb'));reset_pose()
 o=bpy.data.objects['char1'];weld(o);weight_fix(o)
 smooth=o.modifiers.new('Astra surface polish • reversible','SMOOTH');smooth.factor=.36;smooth.iterations=3
 # Place surface smoothing before armature deformation.
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_move_up(modifier=smooth.name)
 sword=bpy.data.objects['Godwyn_Sword'];weld(sword);fix_sword(sword)
 setup();(OUT/'weights_round2.json').write_text(json.dumps(measure_pose(),indent=2))
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 for name in ['front','shoulder','arms_raised','face']:render_view('r2geo',name)
 # Isolate sword at its source orientation to locate grip and blade.
 o.hide_render=True;VIEWS['sword']=((-.7,-5,2),(-.69,.05,1.1),2.5);render_view('r2geo','sword')
if __name__=='__main__':main()
