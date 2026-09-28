"""Surface-conforming chased laurel relief, skinned from underlying breastplate."""
import sys,math,json
sys.dont_write_bytecode=True
import bpy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_face import strands,material
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));o=bpy.data.objects['char1'];me=o.data
name='AstraChar2_R3_ChasedLaurel'
if name in bpy.data.objects:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
coords=[o.matrix_world@v.co for v in me.vertices];faces=[tuple(p.vertices) for p in me.polygons if p.material_index==0];tree=BVHTree.FromPolygons(coords,faces);kd=KDTree(len(coords))
for i,p in enumerate(coords):kd.insert(p,i)
kd.balance();paths=[]
def project(path):
 out=[]
 for x,z in path:
  p,n,idx,d=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),1.2)
  if p is None:return
  p.y-=.00075
  if out and (p-Vector(out[-1])).length>.03:return
  out.append(tuple(p))
 paths.append(out)
for s in [-1,1]:
 def stem(t):return s*(.06+.065*math.sin(t*math.pi*.82)),2.34+.285*t
 project([stem(i/99) for i in range(100)])
 for k in range(12):
  t=.08+k*.071;x,z=stem(t)
  for outward in [-1,1]:
   project([(x+s*outward*(.017*math.sin(math.pi*j/24)+.002*j/24),z+.023*j/24) for j in range(25)]+[(x+s*outward*(.004*math.sin(math.pi*j/24)+.002*(1-j/24)),z+.023*(1-j/24)) for j in range(1,25)])
mat,bs=material('AstraChar2 R3 chased antique brass',(.33,.22,.075),.42,1)
ob=strands(name,paths,mat,.00065);ob.vertex_groups.clear()
groups={g.index:ob.vertex_groups.new(name=g.name) for g in o.vertex_groups}
for v in ob.data.vertices:
 _,i,_=kd.find(v.co)
 for g in me.vertices[i].groups:groups[g.group].add([v.index],g.weight,'REPLACE')
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
(OUT/'r3_relief.json').write_text(json.dumps({'chased_paths':len(paths),'radius_m':.00065,'surface':'breastplate gold; vertex weights copied from nearest original plate vertex','existing_baked_relief':'gold +/-0.35mm, cloth trim +0.6mm sampled into original tessellation'},indent=2))
