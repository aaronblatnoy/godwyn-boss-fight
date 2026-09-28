import bpy,sys,json,shutil,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
src=ROOT/'models/astra_character_v2.blend';backup=ROOT/'models/astra_character_v2_r3_preweights.blend'

if not backup.exists() or '--fresh' in sys.argv:shutil.copy2(src,backup)
bpy.ops.wm.open_mainfile(filepath=str(backup));o=bpy.data.objects['char1'];me=o.data;N=len(me.vertices);G=len(o.vertex_groups)
W=np.zeros((N,G),np.float32)
for v in me.vertices:
 for g in v.groups:W[v.index,g.group]=g.weight
hair=[g.index for g in o.vertex_groups if g.name.startswith('phys_hair')];hairweight=W[:,hair].sum(1);reassigned=0
for f in me.polygons:
 if f.material_index==0 and np.mean(hairweight[list(f.vertices)])>.55:f.material_index=3;reassigned+=1
p=np.array([o.matrix_world@v.co for v in me.vertices]);used={v for f in me.polygons for v in f.vertices};mask=(p[:,2]>2.10)&(p[:,2]<2.78)&(abs(p[:,0])<.8)
# Diffuse discontinuities only through existing surface edges. No proximity bridges
# between independently simulated layers and no changes to garment geometry.
edge_set={tuple(sorted(e)) for f in me.polygons for e in f.edge_keys};edges=np.array([e for e in edge_set if mask[e[0]] and mask[e[1]]],np.int32)
ids=np.flatnonzero(mask);lookup=np.full(N,-1,dtype=np.int32);lookup[ids]=np.arange(len(ids));e=lookup[edges];w=W[ids].copy();original=w.copy();length=np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1);factor=np.exp(-(length/.03)**2).astype(np.float32)
count=np.zeros(len(ids),np.float32);np.add.at(count,e[:,0],factor);np.add.at(count,e[:,1],factor);count=np.maximum(count,1e-8)
for _ in range(40):
 acc=np.zeros_like(w)
 np.add.at(acc,e[:,0],w[e[:,1]]*factor[:,None]);np.add.at(acc,e[:,1],w[e[:,0]]*factor[:,None]);avg=acc/count[:,None];valid=count>1e-7;w[valid]=w[valid]*.45+avg[valid]*.55
# Blend the repair back into unchanged weights at the regional border.
blend=np.minimum(np.clip((p[ids,2]-2.1)/.06,0,1),np.clip((2.78-p[ids,2])/.06,0,1));w=original*(1-blend[:,None])+w*blend[:,None]
# Preserve all existing influences; exporter normalizes its four strongest influences.
w[w<1e-5]=0;order=np.argsort(w,axis=1)[:,:-4];np.put_along_axis(w,order,0,axis=1);w/=np.maximum(w.sum(1)[:,None],1e-8);changed=np.sum(abs(w-original),1)>.001
for row in np.flatnonzero(changed):
 vi=int(ids[row]);v=me.vertices[vi]
 for gi in [g.group for g in v.groups]:o.vertex_groups[gi].remove([vi])
 for g in np.flatnonzero(w[row]>0):o.vertex_groups[int(g)].add([vi],float(w[row,g]),'REPLACE')
from mathutils.kdtree import KDTree
relief=bpy.data.objects.get('AstraChar2_R3_ChasedLaurel')
if relief:
 kd=KDTree(N)
 for vi,pnt in enumerate(p):kd.insert(pnt,vi)
 kd.balance()
 for v in relief.data.vertices:
  _,vi,_=kd.find(v.co)
  for gi in [g.group for g in v.groups]:relief.vertex_groups[gi].remove([v.index])
  for g in me.vertices[vi].groups:relief.vertex_groups[g.group].add([v.index],g.weight,'REPLACE')
r={'weight_vertices_smoothed':int(changed.sum()),'iterations':40,'world_region':'2.10 < z < 2.78m; |x| < 0.8m, 6cm feather','geometry_changed':False,'hair_faces_reassigned_to_existing_hair_slot':reassigned,'max_influences':int((w>0).sum(1).max())}
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(src));(OUT/'r3_weightfix.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
