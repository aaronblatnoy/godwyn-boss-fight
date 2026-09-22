import bpy,sys,math,json,numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_face import strands

def apply():
 o=bpy.data.objects['char1'];arm=bpy.data.objects['Armature'];me=o.data
 fs=[tuple(f.vertices) for f in me.polygons if f.material_index==3]
 tree=BVHTree.FromPolygons([o.matrix_world@v.co for v in me.vertices],fs,all_triangles=False)
 r={'new_fibers':0,'braid_bundles':0,'bone_chain_names':[]}
 for name in [x.name for x in bpy.data.objects if x.name.startswith('AstraChar2_R3_')]:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
 rng=np.random.default_rng(728)
 for side,label in [(-1,'R'),(1,'L')]:
  chains=[arm.data.bones.get('phys_hair_front_'+label+'_'+str(i).zfill(2)) for i in range(4)];chains=[b for b in chains if b];r['bone_chain_names'] += [b.name for b in chains]
  for kind in ['Flow','Plait']:
   paths=[]
   for k in range(360 if kind=='Flow' else 90):
    path=[];off=rng.uniform(-.045,.035);phase=k%3*2*math.pi/3;micro=rng.uniform(0,2*math.pi);rad=rng.uniform(0,.0015)
    for j in range(120):
     t=j/119;z=2.94-t*(.72 if kind=='Flow' else .67);x=side*(.151+.045*t+off*(1-.4*t)+.005*math.sin(10*t+k*.08))
     hit,nn,idx,dist=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),1.5)
     if hit is None or hit.y>.06:
      if len(path)>5:paths.append(path)
      path=[];continue
     p=hit+Vector((0,-.0013,0))
     if kind=='Plait':
      # Three interweaving bundles, each comprising 30 fine fibers.
      x=side*(.157+.04*t);hit,nn,idx,dist=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),1.5)
      if hit is None:continue
      p=hit+Vector((.004*math.sin(t*math.tau*8+phase)+rad*math.cos(micro),-.005-.0025*math.sin(t*math.tau*16+phase)+rad*math.sin(micro),0))
     if path and (p-Vector(path[-1])).length>.025:
      if len(path)>5:paths.append(path)
      path=[]
     path.append(tuple(p))
    if len(path)>5:paths.append(path)
   if not paths:continue
   ob=strands('AstraChar2_R3_'+kind+'_'+label,paths,bpy.data.materials['AstraChar2 R2 hair 1'],.00016 if kind=='Plait' else .00011)
   ob.vertex_groups.clear();groups=[ob.vertex_groups.new(name=b.name) for b in chains]
   roots=[arm.matrix_world@b.head_local for b in chains]
   for v in ob.data.vertices:
    ds=sorted(((abs(v.co.z-p.z),i) for i,p in enumerate(roots)))[:2];vals=[1/max(d,.02)**2 for d,i in ds];tot=sum(vals)
    for (d,i),w in zip(ds,vals):groups[i].add([v.index],w/tot,'REPLACE')
   uv=ob.data.uv_layers.new(name='UVMap');start=0;coord={}
   for path in paths:
    for j in range(len(path)):
     for k in range(5):coord[start+j*5+k]=(k/5,j/max(1,len(path)-1))
    start+=len(path)*5
   for l in ob.data.loops:uv.data[l.index].uv=coord[l.vertex_index]
   r['new_fibers']+=len(paths)
   if kind=='Plait':r['braid_bundles']+=3
 # Longitudinal tangent on new strand UVs; existing roots keep their former UV convention.
 m=bpy.data.materials['AstraChar2 R2 hair 1'];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Anisotropic Rotation'].default_value=.25
 r['limitation']='Existing bone rest transforms preserved; adding weighted fibers does not validate spring/jiggle dynamics. Old underlying solid hair remains.'
 (OUT/'r3_hair.json').write_text(json.dumps(r,indent=2));return r
if __name__=='__main__':
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));print(apply());bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
