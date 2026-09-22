import bpy,sys,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_wip.blend'))
s=bpy.context.scene
for o in s.objects:
 if o.type=='MESH':o.hide_render=o.name!='Godwyn_Sword'
sw=bpy.data.objects['Godwyn_Sword'];sw.parent=None;sw.matrix_world=Matrix.Diagonal((.01,.01,.01,1))
vs=[v.co for v in sw.data.vertices];bb=[Vector(v) for v in sw.bound_box];center=sum(bb,Vector())*.01/8
print('SWORD LOCAL BOUNDS',[(min(v[i] for v in vs),max(v[i] for v in vs)) for i in range(3)])
for i in range(10):
 lo=min(v.z for v in vs);hi=max(v.z for v in vs);vv=[v for v in vs if lo+(hi-lo)*i/10<=v.z<=lo+(hi-lo)*(i+1)/10]
 print('SLICE',i,'z',lo+(hi-lo)*i/10,'width',max(v.x for v in vv)-min(v.x for v in vv))
s.camera.location=center+Vector((0,-5,0));s.camera.rotation_euler=(center-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=2.6
s.render.filepath=str(ROOT/'renders/astra/sword_inspect.png');bpy.ops.render.render(write_still=True)
