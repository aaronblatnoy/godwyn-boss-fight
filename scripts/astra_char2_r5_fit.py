"""Local upper-cloth interpenetration repair, preserving every panel vertex and face.
A rest-space inward shrinkwrap sits before armature deformation. No garment retopology.
"""
import bpy,math
from mathutils import Vector
from mathutils import Matrix

def fit():
 char=bpy.data.objects['char1'];arm=bpy.data.objects['Armature'];v=[];f=[]
 for ob in bpy.data.objects:
  if not ob.name.startswith(('AstraChar2_R5_ClavicleMantle','AstraChar2_R5_Cuirass','AstraChar2_R5_Gorget','AstraChar2_R5_Pauldron_','AstraChar2_R5_UpperArm_')):continue
  if ob.type!='MESH':continue
  off=len(v);v.extend([tuple(ob.matrix_world@x.co) for x in ob.data.vertices])
  for poly in ob.data.polygons:
   ids=list(poly.vertices);p=ob.matrix_world@poly.center;normal=ob.matrix_world.to_3x3()@poly.normal
   if 'Pauldron_' in ob.name:radial=p-Vector((.330 if ob.name.endswith('_L') else -.330,-.173,2.586))
   elif 'UpperArm_' in ob.name:
    side=1 if '_L_' in ob.name else -1;bn='LeftArm' if side>0 else 'RightArm';en='LeftForeArm' if side>0 else 'RightForeArm';a=arm.matrix_world@arm.data.bones[bn].head_local;b=arm.matrix_world@arm.data.bones[en].head_local;d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));radial=p-(a+t*d)
   elif 'Clavicle' in ob.name:radial=p-Vector((0,-.19,2.53))
   else:radial=Vector((p.x,p.y+.18,0))
   if normal.dot(radial)<0:ids.reverse()
   f.append(tuple(off+i for i in ids))
 me=bpy.data.meshes.new('R5 rest-space collar fit envelope');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new('AstraChar2_R5_ClothFitEnvelope',me);bpy.context.scene.collection.objects.link(o);o.parent=arm;o.matrix_parent_inverse=arm.matrix_world.inverted();o.hide_render=True;o.hide_set(True)
 vg=char.vertex_groups.get('AstraChar2_R5_CollarFit') or char.vertex_groups.new(name='AstraChar2_R5_CollarFit');ids={i for p in char.data.polygons if p.material_index in(1,4) for i in p.vertices};count=0
 for i in ids:
  p=char.matrix_world@char.data.vertices[i].co
  if p.z<=1.99 or abs(p.x)>.64:continue
  weight=min(1,max(0,(p.z-1.99)/.09));vg.add([i],weight,'REPLACE');count+=1
 mod=char.modifiers.new('AstraChar2 R5 collar cloth containment','SHRINKWRAP');mod.target=o;mod.vertex_group=vg.name;mod.wrap_method='NEAREST_SURFACEPOINT';mod.wrap_mode='ABOVE_SURFACE';mod.offset=-.024
 # Rest-space containment must precede the shipped pose deformation.
 idx=char.modifiers.find(mod.name);armidx=next(i for i,m in enumerate(char.modifiers) if m.type=='ARMATURE');bpy.context.view_layer.objects.active=char
 while idx>armidx:bpy.ops.object.modifier_move_up(modifier=mod.name);idx-=1
 return count
