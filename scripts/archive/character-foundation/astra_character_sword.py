import bpy,bmesh,sys,math,json
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
def place_sword(o,clean=False):
 if clean:
  # The imported sword includes detached pieces of the old hand above its grip.
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.co.z>182.5],context='VERTS');bm.to_mesh(o.data);bm.free()
  # Finish the cut handle with a modest faceted gold pommel.
  mat=o.data.materials[0]
  bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=(0,0,0));pom=bpy.context.object;pom.name='Astra sword pommel temporary';pom.data.materials.append(mat)
  for v in pom.data.vertices:v.co=Vector((61.2+v.co.x*4.7,-66.3+v.co.y*3.6,181.2+v.co.z*5.0))
  # Join in the sword's local centimeter coordinates before the rigid bind.
  o.parent=None;o.matrix_world=Matrix.Identity(4);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);pom.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.join()
  for f in o.data.polygons:f.use_smooth=True
  # Dedicated UV layout gives the sword the full 2K map instead of scraps of the character atlas.
  if o.data.uv_layers.get('AstraSwordUV') is None:o.data.uv_layers.new(name='AstraSwordUV')
  o.data.uv_layers.active_index=len(o.data.uv_layers)-1
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.018);bpy.ops.object.mode_set(mode='OBJECT')
 arm=bpy.data.objects['Armature'];rot=Matrix.Rotation(math.radians(14),4,'Y');grip=Vector((61.2,-66.3,167.0));target=Vector((-45.4,-29.0,151.0))
 # Preserve source coordinates as an attribute for the portable procedural bake.
 pos=o.data.attributes.get('astra_sword_source') or o.data.attributes.new('astra_sword_source','FLOAT_VECTOR','POINT')
 for v in o.data.vertices:
  pos.data[v.index].vector=v.co.copy();v.co=target+rot.to_3x3()@((v.co-grip)*.88)
 o.parent=arm;o.parent_type='OBJECT';o.matrix_parent_inverse=Matrix.Identity(4);o.matrix_basis=Matrix.Identity(4)
 o.vertex_groups.clear();vg=o.vertex_groups.new(name='RightHand');vg.add([v.index for v in o.data.vertices],1,'REPLACE')
 for mod in list(o.modifiers):o.modifiers.remove(mod)
 mod=o.modifiers.new('Astra rigid sword attachment','ARMATURE');mod.object=arm
 bpy.context.view_layer.update()
def main():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose();o=bpy.data.objects['Godwyn_Sword'];place_sword(o,True)
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 VIEWS['sword']=((-1,-5,1.6),(-.64,-.29,.9),1.55);render_view('r2geo_bound','sword')
if __name__=='__main__':main()
