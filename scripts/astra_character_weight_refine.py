import bpy,sys,numpy as np,bmesh,json
from pathlib import Path
from mathutils.kdtree import KDTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
from astra_character_geometry import weld
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose()
old=bpy.data.objects['char1'];names=[g.name for g in old.vertex_groups if g.name!='Astra polish interior'];mat=old.data.materials[0];arm=bpy.data.objects['Armature'];matrix=old.matrix_world.copy();bpy.data.objects.remove(old,do_unlink=True)
src=np.load(OUT/'source_mesh.npz');me=bpy.data.meshes.new('Astra repaired original surface');me.from_pydata(src['positions'],[],src['triangles']);me.update();uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',src['uv'].astype(np.float32).ravel());o=bpy.data.objects.new('char1',me);bpy.context.scene.collection.objects.link(o);o.parent=arm;o.matrix_world=matrix;me.materials.append(mat)
for n in names:o.vertex_groups.new(name=n)
weld(o);p=np.array([v.co[:] for v in o.data.vertices]);n=len(p);kd=KDTree(len(src['positions']))
for i,c in enumerate(src['positions']):kd.insert(c,i)
kd.balance();near=np.array([kd.find(c)[1] for c in p]);w=src['weights'][near].copy();orig=w.copy();ids={s:i for i,s in enumerate(names)};x,y,z=p.T
edge=np.array([e.vertices[:] for e in o.data.edges]);a,b=edge.T;degree=np.bincount(np.r_[a,b],minlength=n);labels=np.zeros(n,dtype=np.int32)
def avg(v):return (np.bincount(a,weights=v[b],minlength=n)+np.bincount(b,weights=v[a],minlength=n))/np.maximum(degree,1)
armids=[]
fitted={
 'Right':[(-40,-18,263),(-46,-16,217),(-46,-24,169),(-44,-30,142)],
 'Left':[(39,-19,264),(50,-18,223),(62,-44,207),(65,-72,191)]}
armblend={}
for num,side in enumerate(['Right','Left'],1):
 gi=[ids[side+s] for s in ['Shoulder','Arm','ForeArm','Hand']];armids+=gi
 joints=np.array(fitted[side]);ds=[];ts=[]
 for i,(aa,bb) in enumerate(zip(joints[:-1],joints[1:])):
  vec=bb-aa;t=np.clip(((p-aa)@vec)/(vec@vec),0,1);ts.append(t);delta=p-aa-t[:,None]*vec
  radius=[23,17,16][i];ds.append(np.linalg.norm(delta/np.array([radius,radius,radius]),axis=1))
 mask=(np.min(ds,axis=0)<1)&(z<282)&(z>132 if side=='Right' else z>178)&(x<-24 if side=='Right' else x>24)
 if side=='Right':mask &= (y<5)&((z>173)|(y<-15))
 else:mask &= (y<8)&((z>213)|(y<-22))
 hair=orig[:,[i for i,k in enumerate(names) if 'hair' in k]].sum(1);mask &=hair<.5
 def sm(a,b,v):
  q=np.clip((v-a)/(b-a),0,1);return q*q*(3-2*q)
 fore=sm(.66,1,ts[0]);hand=sm(.65,1,ts[1]);armblend[side]=np.stack([np.zeros(n),1-fore,fore*(1-hand),fore*hand],axis=1)
 labels[mask]=num
for num,side in enumerate(['Right','Left'],1):
 gi=[ids[side+s] for s in ['Shoulder','Arm','ForeArm','Hand']];aw=armblend[side]
 aw/=np.maximum(aw.sum(1)[:,None],1e-7);sel=labels==num;w[sel]=0
 for j,k in enumerate(gi):w[sel,k]=aw[sel,j]
body=labels==0;w[np.ix_(body,armids)]=0
for i in np.where(w.sum(1)<.0001)[0]:w[i,ids['Spine' if z[i]>236 else 'Spine01' if z[i]>210 else 'Spine02' if z[i]>180 else 'Hips']]=1
w/=np.maximum(w.sum(1)[:,None],1e-8)
for i in range(n):
 inds=np.argsort(w[i])[-4:];vals=w[i,inds];vals/=vals.sum()
 for k,v in zip(inds,vals):
  if v>.00001:o.vertex_groups[int(k)].add([i],float(v),'REPLACE')
bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();fs=[f for f in bm.faces if len({int(labels[v.index]) for v in f.verts})>1];count=len(fs);area=sum(f.calc_area() for f in fs);total=sum(f.calc_area() for f in bm.faces)
bmesh.ops.delete(bm,geom=fs,context='FACES_ONLY');bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(me);bm.free();me.update()
mod=o.modifiers.new('Astra surface polish • reversible','SMOOTH');mod.factor=.3;mod.iterations=2
am=o.modifiers.new('Armature','ARMATURE');am.object=arm;am.use_deform_preserve_volume=False
data=measure_pose();data.update(bridge_faces_removed=count,bridge_surface_area_percent=area/total*100,cape_arm_influences=0)
(OUT/'weights_final.json').write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items() if k!='worst'}),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
for name in ['arms_raised','front']:render_view('r5geo',name)
