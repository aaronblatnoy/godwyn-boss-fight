import bpy,sys,json,numpy as np,bmesh
from pathlib import Path
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose();o=bpy.data.objects['char1'];arm=bpy.data.objects['Armature']
p=np.array([v.co[:] for v in o.data.vertices],dtype=np.float32);names=[g.name for g in o.vertex_groups];ids={n:i for i,n in enumerate(names)};x,y,z=p.T
src=np.load(OUT/'source_mesh.npz');kd=KDTree(len(src['positions']))
for i,c in enumerate(src['positions']):kd.insert(c,i)
kd.balance();near=np.array([kd.find(c)[1] for c in p]);w=src['weights'][near].copy();original=w.copy()
label=np.zeros(len(p),dtype=np.int32);aw=np.zeros_like(w)
def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
for num,side in enumerate(['Right','Left'],1):
 sh=np.array(arm.data.bones[side+'Arm'].head_local);el=np.array(arm.data.bones[side+'ForeArm'].head_local);ha=np.array(arm.data.bones[side+'Hand'].head_local);tip=ha+(np.array(arm.data.bones[side+'Hand'].tail_local)-ha)*.006
 ds=[];ts=[]
 for a,b in [(sh,el),(el,ha),(ha,tip)]:
  v=b-a;t=np.clip(((p-a)@v)/(v@v),0,1);ts.append(t);ds.append(np.linalg.norm(p-a-t[:,None]*v,axis=1))
 closest=np.minimum(np.minimum(ds[0]/18,ds[1]/11.5),ds[2]/10)
 region=(closest<1)&(np.abs(x)>25)&(z<280)&(z>129)
 if side=='Right':region &= (x<0)&((z>207)|(y<-17.8))
 else:region &= (x>0)&((z>220)|(y<-28))
 # Independently skinned long hair is excluded from the arm component.
 hair=original[:,[i for i,n in enumerate(names) if 'hair' in n]].sum(1);region &= hair<.35
 label[region]=num
 fore=smooth(.73,1,ts[0]);hand=smooth(.65,1,ts[1]);aw[:,ids[side+'Arm']]=(1-fore)*(label==num);aw[:,ids[side+'ForeArm']]=fore*(1-hand)*(label==num);aw[:,ids[side+'Hand']]=fore*hand*(label==num)
# The reconstructed source fuses some cape and gauntlet triangles. Remove only the
# bridge faces crossing the fitted arm/cape seam; this avoids a shared cloth web.
bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();cross=[];area=0;total=sum(f.calc_area() for f in bm.faces)
for f in bm.faces:
 labs={int(label[v.index]) for v in f.verts}
 if len(labs)>1:cross.append(f);area+=f.calc_area()
removed=len(cross);bmesh.ops.delete(bm,geom=cross,context='FACES_ONLY');bm.to_mesh(o.data);bm.free()
# Body/cape is never weighted to an arm; arm geometry uses only its limb chain.
armids=[i for i,n in enumerate(names) if any(s in n for s in ['Shoulder','Arm','Hand']) and not n.startswith('phys')]
w[:,armids]=0
for i in np.where(w.sum(1)<.0001)[0]:
 if z[i]<185:
  chain='R' if x[i]<-15 else ('L' if x[i]>15 else 'C');level=int(np.clip(round((152-z[i])/18),0,7));w[i,ids[f'phys_robe_side_{chain if chain!="C" else "R"}_{level:02d}']]=1
 elif z[i]>277:w[i,ids['Head']]=1
 else:w[i,ids['Spine' if z[i]>237 else 'Spine01' if z[i]>215 else 'Spine02']]=1
w/=np.maximum(w.sum(1)[:,None],1e-8);w[label>0]=aw[label>0]
for g in o.vertex_groups:g.remove(list(range(len(p))))
for i in range(len(p)):
 for j in np.where(w[i]>.00001)[0]:o.vertex_groups[int(j)].add([i],float(w[i,j]),'REPLACE')
# Seam boundary vertices stay fixed under the reversible polish modifier.
bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();vg=o.vertex_groups.new(name='Astra polish interior');interior=[v.index for v in bm.verts if not v.is_boundary];vg.add(interior,1,'REPLACE');bm.free()
for mod in o.modifiers:
 if mod.type=='SMOOTH':mod.vertex_group=vg.name
if hasattr(o.data,'set_sharp_from_angle'):o.data.set_sharp_from_angle(angle=1.05)
data=measure_pose();data.update(bridge_faces_removed=removed,bridge_surface_area_percent=100*area/total,limb_vertices=int((label>0).sum()),cape_arm_influences=0)
(OUT/'weights_final.json').write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='worst'}),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
for name in ['arms_raised','shoulder']:render_view('r3geo',name)
