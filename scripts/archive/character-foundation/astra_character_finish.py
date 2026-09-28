import bpy,sys,math,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
from astra_character_bake import bake,portable_material
def undersleeves():
 arm=bpy.data.objects['Armature'];verts=[];faces=[];uvs=[];weights=[];sides=32
 paths={
 'Right':[(-17,-17,250,12),(-30,-17,256,13),(-40,-18,256,13.5),(-44,-17,237,12.5),(-46,-16,218,10.5),(-46,-20,195,9),(-46,-24,174,7.5)],
 'Left':[(17,-17,250,12),(30,-17,257,13),(40,-18,258,13.5),(45,-18,241,12.5),(50,-18,223,11),(57,-33,213,10),(63,-51,203,8.5)]}
 for sideindex,(side,path) in enumerate(paths.items()):
  start=len(verts)
  for j,point in enumerate(path):
   center=Vector(point[:3]);tangent=Vector(path[min(j+1,len(path)-1)][:3])-Vector(path[max(j-1,0)][:3]);tangent.normalize();axis=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(axis).normalized()
   for k in range(sides):
    theta=k*math.tau/sides;v=center+(axis*math.cos(theta)+other*math.sin(theta))*(point[3]*(1+.025*math.cos(theta*6+j*.7)));verts.append(v)
    body=[1,.4,0,0,0,0,0][j];fore=[0,0,0,.04,.4,.86,1][j]
    weights.append({'Spine':body,side+'Arm':(1-body)*(1-fore),side+'ForeArm':(1-body)*fore})
  for j in range(len(path)-1):
   for k in range(sides):
    faces.append((start+j*sides+k,start+j*sides+(k+1)%sides,start+(j+1)*sides+(k+1)%sides,start+(j+1)*sides+k))
    u0=.03+sideindex*.49+.43*k/sides;u1=.03+sideindex*.49+.43*(k+1)/sides;v0=.03+.94*j/(len(path)-1);v1=.03+.94*(j+1)/(len(path)-1);uvs.extend([(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
 me=bpy.data.meshes.new('Astra tailored inner sleeve surface');me.from_pydata(verts,[],faces);me.update();uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',np.array(uvs,dtype=np.float32).ravel())
 o=bpy.data.objects.new('Astra_Undersleeves',me);bpy.context.scene.collection.objects.link(o);o.parent=arm;o.matrix_parent_inverse=Matrix.Identity(4)
 for bn in set(k for w in weights for k in w):o.vertex_groups.new(name=bn)
 for i,w in enumerate(weights):
  for bn,v in w.items():
   if v:o.vertex_groups[bn].add([i],v,'REPLACE')
 for f in me.polygons:f.use_smooth=True
 sub=o.modifiers.new('Astra sleeve silhouette','SUBSURF');sub.levels=2;sub.render_levels=2
 am=o.modifiers.new('Armature','ARMATURE');am.object=arm
 seed=bpy.data.images.new('Astra blue bake seed',width=1,height=1);seed.pixels[:]=(.0055,.01,.1,1)
 mat=bpy.data.materials.new('Astra sleeve baking source');mat.use_nodes=True;node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=seed;mat.node_tree.links.new(node.outputs[0],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color']);o.data.materials.append(mat)
 ims=bake(o,2048);o.data.materials.clear();o.data.materials.append(portable_material('Astra woven inner sleeves',ims,'cloth'))
 return o
def main():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose()
 char=bpy.data.objects['char1'];classes=[f.material_index for f in char.data.polygons]
 ims=bake(char,4096,reuse_base=True);char.data.materials.clear()
 for name,kind in [('Astra engraved royal gold final','gold'),('Astra midnight blue woven silk final','cloth'),('Astra pale golden skin final','skin')]:char.data.materials.append(portable_material(name,ims,kind))
 for f,c in zip(char.data.polygons,classes):f.material_index=c
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 sword=bpy.data.objects['Godwyn_Sword']
 # One UV set for the dedicated 2K sword bake, avoiding an implicit TEXCOORD_0 mismatch.
 if len(sword.data.uv_layers)>1:
  for uv in list(sword.data.uv_layers):
   if uv.name!='AstraSwordUV':sword.data.uv_layers.remove(uv)
  sword.data.uv_layers.active.active_render=True
  seedmat=bpy.data.materials.new('Astra sword rebake source');seedmat.use_nodes=True;n=seedmat.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images['godwyn_albedo'];sword.data.materials.clear();sword.data.materials.append(seedmat)
  ims=bake(sword,2048);sword.data.materials.clear();sword.data.materials.append(portable_material('Astra worn steel and gold hilt final',ims))
 undersleeves();s=bpy.context.scene;s.render.engine='BLENDER_EEVEE'
 # Keep smooth shading with deliberate hard edges on the sword and a gentle character angle.
 for o in [bpy.data.objects['char1'],sword]:
  if hasattr(o.data,'set_sharp_from_angle'):o.data.set_sharp_from_angle(angle=math.radians(62 if o==sword else 75))
 reset_pose();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 for name in VIEWS:render_view('after',name)
 # A dedicated hilt view and a close raised shoulder view expose the actual seams.
 VIEWS['sword']=((-.5,-6,1.65),(-.43,-.29,1.56),.48);render_view('after_hilt','sword')
 raised_pose();s.camera.location=(-3,-6,3.8);aim(s.camera,(-.45,-.1,2.6));s.camera.data.ortho_scale=1.15;s.render.filepath=str(OUT/'after_shoulder_raised.png');bpy.ops.render.render(write_still=True)
 reset_pose();s.camera.location=VIEWS['three_quarter'][0];aim(s.camera,VIEWS['three_quarter'][1]);s.camera.data.ortho_scale=VIEWS['three_quarter'][2]
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
if __name__=='__main__':main()
