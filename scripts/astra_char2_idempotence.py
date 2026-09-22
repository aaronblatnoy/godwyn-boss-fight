import bpy,sys,json,numpy as np
from pathlib import Path
from mathutils.kdtree import KDTree
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_face import apply_face
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_char2_work.blend'))
def sig():
 result={}
 for o in bpy.data.objects:
  if o.name=='char1' or o.name.startswith('AstraChar2_'):
   a=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',a)
   f=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',f)
   centers=np.array([p.center[:] for p in o.data.polygons]) if o.name.startswith('AstraChar2_') else None
   result[o.name]=(a,f,np.array(o.matrix_world),len(o.data.polygons),centers)
 return result
before=sig();apply_face();after=sig();assert before.keys()==after.keys()
rows=[]
def distance(a,b):
 tree=KDTree(len(b))
 for i,p in enumerate(b):tree.insert(p,i)
 tree.balance();return max(tree.find(p)[2] for p in a)
for name,(a,f,m,n,centers) in before.items():
 b,g,k,nn,other_centers=after[name];assert a.shape==b.shape and n==nn
 same_order=np.array_equal(f,g)
 if same_order:error=float(abs(a-b).max());center_error=0.
 else:
  error=max(distance(a.reshape(-1,3),b.reshape(-1,3)),distance(b.reshape(-1,3),a.reshape(-1,3)))
  center_error=max(distance(centers,other_centers),distance(other_centers,centers))
 matrix_error=float(abs(m-k).max());rows.append({'name':name,'local_surface_max_error':error,'face_center_max_error':center_error,'matrix_max_error':matrix_error,'same_native_vertex_order':same_order})
 assert error<1e-6 and center_error<1e-6 and matrix_error<1e-7,(name,error,center_error,matrix_error)
r={'passed':True,'objects_checked':len(before),'same_object_names_counts_surface_geometry':True,'note':'Blender native UV sphere vertex/face ordering may change; bidirectional vertex and face-center comparison checks geometric equivalence.','position_tolerance_local':1e-6,'details':rows,'scene_saved':False}
(OUT/'idempotence.json').write_text(json.dumps(r,indent=2));print('IDEMPOTENCE PASS',json.dumps(r),flush=True)
