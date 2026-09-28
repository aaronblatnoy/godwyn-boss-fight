import bpy,sys,numpy as np,json
sys.dont_write_bytecode=True
from mathutils import Vector
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2.blend')
dg=bpy.context.evaluated_depsgraph_get();o=bpy.data.objects['char1'].evaluated_get(dg);tree=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices) for f in o.data.polygons]);r=[]
for x,z in [(-.1,3.08),(-.08,3.06),(-.12,3.07),(-.09,3.11),(-.11,3.04),(0,3.19)]:
 hit,n,fi,d=tree.ray_cast(Vector((x,-.8,z)),Vector((0,1,0)),1);near=[]
 for ob in bpy.data.objects:
  if ob.type!='CURVES':continue
  cu=ob.evaluated_get(dg).data;p=np.empty(len(cu.points)*3,np.float32);cu.position_data.foreach_get('vector',p);p=p.reshape(-1,3);dist=np.hypot(p[:,0]-x,p[:,2]-z);ids=np.argsort(dist)[:3];near.extend([(float(dist[i]),list(map(float,p[i])),ob.name) for i in ids])
 near.sort();r.append({'sample':[x,z],'surface':list(hit) if hit else None,'material':o.data.polygons[fi].material_index if fi is not None else None,'strands':near[:5]})
print(json.dumps(r,indent=2))
