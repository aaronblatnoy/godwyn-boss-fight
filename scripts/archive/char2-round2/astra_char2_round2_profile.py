import bpy,json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2_round2_work.blend')
o=bpy.data.objects['char1'];inv=o.matrix_world.inverted()
for z in [2.78,2.79,2.8,2.81,2.82,2.83,2.84,2.85,2.86,2.87,2.88,2.89,2.90,2.91,2.92,2.93,2.94,2.96,2.98,3.0,3.02,3.05,3.10,3.13]:
 vals=[]
 for x in [0,.02,.04,.06,.08,.10,.12]:
  ok,p,n,fi=o.ray_cast(inv@Vector((x,-1,z)),Vector((0,1,0)))
  vals.append(round((o.matrix_world@p).y,4) if ok else None)
 print(z,vals)
