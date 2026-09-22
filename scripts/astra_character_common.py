import bpy, math, json
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight')
OUT=ROOT/'renders/astra/character'
def reset_pose():
 arm=bpy.data.objects['Armature'];arm.animation_data_clear()
 for b in arm.pose.bones:b.matrix_basis.identity()
 bpy.context.view_layer.update()
def raised_pose(angle=105):
 reset_pose();arm=bpy.data.objects['Armature']
 for side,sign in [('Left',-1),('Right',1)]:
  b=arm.pose.bones[side+'Arm'];axis=b.bone.matrix_local.to_3x3().inverted()@Vector((0,1,0))
  b.rotation_mode='QUATERNION';b.rotation_quaternion=Quaternion(axis,math.radians(angle)*sign)
 bpy.context.view_layer.update()
def aim(o,at):o.rotation_euler=(Vector(at)-o.location).to_track_quat('-Z','Y').to_euler()
def setup():
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=960;s.render.resolution_percentage=100
 s.render.image_settings.file_format='PNG';s.render.film_transparent=False
 if hasattr(s,'eevee'):s.eevee.taa_render_samples=64
 s.view_settings.view_transform='AgX';s.view_settings.exposure=-0.35
 world=bpy.data.worlds.new('Astra twilight');s.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(0.055,0.068,0.10,1);world.node_tree.nodes['Background'].inputs[1].default_value=0.32
 for name,loc,power,color,size in [('Astra key',(-3.5,-4.5,6),1350,(1,.92,.6),3),('Astra fill',(3,-4,3.5),680,(.52,.65,1),3.2),('Astra rim',(2,3,5),1650,(1,.8,.43),2.4),('Astra face',(0,-4,4.4),110,(1,.95,.84),1.4)]:
  d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);s.collection.objects.link(o);o.location=loc;aim(o,(0,0,1.9))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));floor=bpy.context.object;floor.name='Astra evaluation ground'
 mat=bpy.data.materials.new('Astra charcoal');mat.diffuse_color=(.012,.016,.023,1);mat.use_nodes=True;mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.012,.016,.023,1);mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.82;floor.data.materials.append(mat)
 cam=bpy.data.objects.new('Astra evaluation camera',bpy.data.cameras.new('Astra evaluation camera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.lens=60
 if 'Icosphere' in bpy.data.objects:bpy.data.objects['Icosphere'].hide_render=True;bpy.data.objects['Icosphere'].hide_set(True)
 bpy.context.preferences.filepaths.save_version=0
 return s
VIEWS={
 'front':((0,-9,3.1),(0,0,1.61),3.75),
 'side':((8,-.4,3.1),(0,0,1.61),3.75),
 'three_quarter':((5,-8,3.5),(0,0,1.62),3.8),
 'chest':((.7,-6,2.8),(0,-.24,2.41),.83),
 'face':((.42,-5,3.15),(0,-.25,2.99),.57),
 'shoulder':((-3,-5,3.2),(-.32,-.09,2.44),1.22),
 'sword':((-.6,-6,1.15),(-.65,-.31,.92),1.1),
 'arms_raised':((0,-9,4),(-.5,0,2.1),5.55),
}
def render_view(stage,name):
 if name=='arms_raised':raised_pose()
 else:reset_pose()
 s=bpy.context.scene;loc,target,scale=VIEWS[name];s.camera.location=loc;aim(s.camera,target);s.camera.data.ortho_scale=scale
 oldhide=bpy.data.objects['char1'].hide_render
 if name=='sword':bpy.data.objects['char1'].hide_render=True
 s.render.filepath=str(OUT/f'{stage}_{name}.png');bpy.ops.render.render(write_still=True)
 bpy.data.objects['char1'].hide_render=oldhide
 print('RENDERED',stage,name,flush=True)
def measure_pose():
 import numpy as np
 o=bpy.data.objects['char1'];p=np.array([o.matrix_world@v.co for v in o.data.vertices]);e=np.array([e.vertices[:] for e in o.data.edges]);rest=np.linalg.norm(p[e[:,0]]-p[e[:,1]],axis=1)
 raised_pose();ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();q=np.array([o.matrix_world@v.co for v in me.vertices]);ev.to_mesh_clear()
 posed=np.linalg.norm(q[e[:,0]]-q[e[:,1]],axis=1);ix=np.argsort(posed-rest)[-30:][::-1]
 data={'max_edge':float(posed.max()),'spike_edges':int(((posed>.20)&(rest<.12)).sum()),'stretch_p99':float(np.quantile(posed/np.maximum(rest,.0001),.99)), 'worst':[{'vertices':e[i].tolist(),'rest':float(rest[i]),'posed':float(posed[i]),'positions':p[e[i]].tolist(),'groups':[[(o.vertex_groups[g.group].name,round(g.weight,4)) for g in o.data.vertices[v].groups if g.weight>.01] for v in e[i]]} for i in ix]}
 reset_pose();return data
