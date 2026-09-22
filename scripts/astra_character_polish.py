import bpy,sys,numpy as np,bmesh,json
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
from astra_character_bake import bake,portable_material
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose();o=bpy.data.objects['char1'];classes=[f.material_index for f in o.data.polygons]
ims=bake(o,4096);o.data.materials.clear()
for name,kind in [('Astra engraved royal gold final','gold'),('Astra midnight blue woven silk final','cloth'),('Astra pale golden skin final','skin')]:o.data.materials.append(portable_material(name,ims,kind))
for f,c in zip(o.data.polygons,classes):f.material_index=c
sleeve=bpy.data.objects['Astra_Undersleeves']
if not sleeve.get('astra_final_fit'):
 for start in range(0,len(sleeve.data.vertices),32):
  ring=list(sleeve.data.vertices)[start:start+32];center=sum((v.co for v in ring),Vector())/32
  for v in ring:v.co=center+(v.co-center)*.50
 sleeve['astra_final_fit']=True
# Remove tiny unbound scan fragments left beside the arm/cape seam.
bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();seen=set();trash=[];armids={g.index for g in o.vertex_groups if g.name in ['RightArm','RightForeArm','RightHand','LeftArm','LeftForeArm','LeftHand']}
for v in bm.verts:
 if v.index in seen:continue
 stack=[v];comp=[];seen.add(v.index)
 while stack:
  q=stack.pop();comp.append(q)
  for e in q.link_edges:
   r=e.other_vert(q)
   if r.index not in seen:seen.add(r.index);stack.append(r)
 if len(comp)>180:continue
 center=sum((q.co for q in comp),Vector())/len(comp)
 if not (138<center.z<248 and abs(center.x)>28 and center.y<-8):continue
 if any(any(g.group in armids and g.weight>.02 for g in o.data.vertices[q.index].groups) for q in comp):continue
 trash.extend(comp)
removed=len(trash);bmesh.ops.delete(bm,geom=trash,context='VERTS');bm.to_mesh(o.data);bm.free();o.data.update();(OUT/'surface_cleanup.json').write_text(json.dumps({'unbound_fragment_vertices_removed':removed,'inner_sleeve_radial_fit':.50},indent=2))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
for name in VIEWS:render_view('after',name)
# Hide all non-sword character meshes for the isolated hilt close-up.
sleeve.hide_render=True;VIEWS['sword']=((-.5,-6,1.65),(-.43,-.29,1.56),.48);render_view('after_hilt','sword');sleeve.hide_render=False
raised_pose();s.camera.location=(-3,-6,3.8);aim(s.camera,(-.45,-.1,2.6));s.camera.data.ortho_scale=1.15;s.render.filepath=str(OUT/'after_shoulder_raised.png');bpy.ops.render.render(write_still=True)
reset_pose();s.camera.location=VIEWS['three_quarter'][0];aim(s.camera,VIEWS['three_quarter'][1]);s.camera.data.ortho_scale=VIEWS['three_quarter'][2];bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
