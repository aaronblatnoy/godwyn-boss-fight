import bpy,sys,math,json,numpy as np,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
class Graph:
 def __init__(self,mat):self.nt=mat.node_tree;self.n=self.nt.nodes;self.l=self.nt.links;self.n.clear()
 def node(self,typ):return self.n.new(typ)
 def set(self,s,v):
  if isinstance(v,bpy.types.NodeSocket):self.l.new(v,s)
  else:s.default_value=(v,v,v,1) if s.type=='RGBA' and isinstance(v,(int,float)) else v
 def math(self,op,a,b=None,c=None):
  n=self.node('ShaderNodeMath');n.operation=op
  for i,v in enumerate([a,b,c]):
   if v is not None:self.set(n.inputs[i],v)
  return n.outputs[0]
 def mul(self,a,b):return self.math('MULTIPLY',a,b)
 def add(self,a,b):return self.math('ADD',a,b)
 def sub(self,a,b):return self.math('SUBTRACT',a,b)
 def ramp(self,x,a,b):
  n=self.node('ShaderNodeMapRange');self.set(n.inputs['Value'],x);n.inputs['From Min'].default_value=a;n.inputs['From Max'].default_value=b;n.clamp=True;n.interpolation_type='SMOOTHERSTEP';return n.outputs[0]
 def mix(self,f,a,b):
  n=self.node('ShaderNodeMixRGB');n.blend_type='MIX';self.set(n.inputs[0],f);self.set(n.inputs[1],a);self.set(n.inputs[2],b);return n.outputs[0]
 def noise(self,v,scale,detail=2):
  n=self.node('ShaderNodeTexNoise');self.set(n.inputs['Vector'],v);n.inputs['Scale'].default_value=scale;n.inputs['Detail'].default_value=detail;n.inputs['Roughness'].default_value=.68;return n.outputs['Fac']
 def vec(self,x,y,z):
  n=self.node('ShaderNodeCombineXYZ')
  for s,v in zip(n.inputs,[x,y,z]):self.set(s,v)
  return n.outputs[0]
 def gauss(self,v,width):return self.math('EXPONENT',self.mul(self.math('POWER',self.math('DIVIDE',v,width),2),-1))
def make_procedural(o,is_sword=False):
 old=o.data.materials[0];src=next(n.image for n in old.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name=='sRGB')
 if o.name=='char1':src=bpy.data.images['godwyn_albedo']
 mat=bpy.data.materials.new('Astra source for portable bake '+o.name);mat.use_nodes=True;g=Graph(mat)
 o.data.materials.clear();o.data.materials.append(mat)
 tc=g.node('ShaderNodeTexCoord');p=g.node('ShaderNodeVectorMath');p.operation='SCALE';g.set(p.inputs[0],tc.outputs['Object']);p.inputs[3].default_value=.01
 if is_sword:
  sourcepos=g.node('ShaderNodeAttribute');sourcepos.attribute_name='astra_sword_source';g.set(p.inputs[0],sourcepos.outputs['Vector'])
 xyz=g.node('ShaderNodeSeparateXYZ');g.set(xyz.inputs[0],p.outputs[0]);x,y,z=xyz.outputs
 tx=g.node('ShaderNodeTexImage');tx.image=src;sep=g.node('ShaderNodeSeparateColor');g.set(sep.inputs[0],tx.outputs[0]);red,green,blue=sep.outputs[:3]
 gold=g.math('GREATER_THAN',red,g.mul(blue,1.65));cloth=g.math('GREATER_THAN',blue,g.mul(red,1.35))
 if o.name=='char1':
  masktex=g.node('ShaderNodeTexImage');masktex.image=bpy.data.images['godwyn_metallic-godwyn_roughness'];masksep=g.node('ShaderNodeSeparateColor');g.set(masksep.inputs[0],masktex.outputs[0]);gold=g.math('GREATER_THAN',masksep.outputs['Blue'],.6);cloth=g.mul(cloth,g.sub(1,gold))
  face=g.mul(g.mul(g.sub(1,g.ramp(g.math('ABSOLUTE',x),.105,.15)),g.mul(g.ramp(z,2.80,2.85),g.sub(1,g.ramp(z,3.105,3.13)))),g.sub(1,g.ramp(y,-.38,-.32)))
  gold=g.mul(gold,g.sub(1,face));cloth=g.mul(cloth,g.sub(1,face))
 skin=g.sub(1,g.math('MAXIMUM',gold,cloth))
 attr=g.node('ShaderNodeAttribute');attr.attribute_name='astra_hair'
 hair=g.mul(gold,g.math('MAXIMUM',attr.outputs['Fac'],g.ramp(z,2.76,2.85))) if not is_sword else 0
 armor=g.mul(gold,g.sub(1,hair))
 noise=g.noise(p.outputs[0],85,3);micro=g.noise(p.outputs[0],480,2);broad=g.noise(p.outputs[0],8,3)
 geo=g.node('ShaderNodeNewGeometry');curv=g.ramp(geo.outputs['Pointiness'],.46,.55)
 ao=g.node('ShaderNodeAmbientOcclusion');ao.samples=2;ao.inside=False;ao.only_local=True;ao.inputs['Distance'].default_value=.045
 # Curving, paired vine stems and small quatrefoil medallions, projected in object space.
 phase=g.mul(z,67);sx=g.math('SINE',g.mul(x,67));sz=g.math('SINE',phase)
 flower=g.gauss(g.sub(g.math('ABSOLUTE',g.add(sx,sz)),.60),.095)
 scroll=g.gauss(g.math('SINE',g.add(g.mul(x,96),g.mul(sz,1.4))),.10)
 ornament=g.add(g.mul(flower,.27),g.mul(scroll,.46))
 if not is_sword:
  crest=g.mul(g.sub(1,g.ramp(g.math('ABSOLUTE',x),.10,.18)),g.mul(g.ramp(z,2.30,2.38),g.sub(1,g.ramp(z,2.57,2.63))))
  ornament=g.mul(ornament,g.sub(1,g.mul(crest,.9)))
 # Two woven thread directions, with alternating over/under highlights.
 warp=g.math('SINE',g.mul(x,1100));weft=g.math('SINE',g.mul(z,1100));weave=g.add(g.mul(warp,weft),g.mul(g.math('SINE',g.add(g.mul(x,550),g.mul(z,550))),.28))
 # Fine, elongated noise creates blade abrasion and hair striations.
 stretched=g.vec(g.mul(x,15),g.mul(y,15),g.mul(z,.3));scratchnoise=g.noise(stretched,75,2);scratches=g.ramp(scratchnoise,.62,.71)
 hairlines=g.math('SINE',g.add(g.mul(x,1200),g.mul(g.noise(p.outputs[0],14),8)))
 if is_sword:
  # Source grip is high on the original Z axis; blade runs toward z=0.
  blade=g.sub(1,g.ramp(z,1.45,1.51));ornament=g.mul(ornament,g.sub(1,blade))
  base=g.mix(blade,(.64,.38,.020,1),(.34,.40,.46,1));base=g.mix(g.mul(broad,.15),base,(.50,.40,.19,1))
  rough=g.add(.25,g.add(g.mul(broad,.12),g.mul(scratches,.24)));metal=.98
  height=g.add(g.mul(ornament,.55),g.add(g.mul(scratches,-.12),g.mul(noise,.022)))
 else:
  goldbase=g.mix(broad,(.56,.29,.015,1),(.72,.46,.035,1));goldbase=g.mix(g.mul(curv,.24),goldbase,(.82,.60,.095,1))
  clothbase=g.mix(broad,(.0055,.010,.073,1),(.013,.023,.125,1));clothbase=g.mix(g.mul(g.add(weave,1),.025),clothbase,(.026,.047,.16,1))
  skinbase=g.mix(g.mul(noise,.12),(.48,.35,.29,1),(.57,.42,.35,1));skinbase=g.mix(.16,skinbase,tx.outputs[0])
  base=g.mix(cloth,goldbase,clothbase);base=g.mix(skin,base,skinbase);base=g.mix(hair,base,g.mix(broad,(.30,.17,.035,1),(.57,.37,.10,1)))
  if o.name=='char1':
   eye=g.mul(face,g.math('GREATER_THAN',blue,g.mul(red,1.35)));base=g.mix(eye,base,(.035,.017,.003,1))
  rgold=g.add(.34,g.add(g.mul(g.sub(broad,.5),.15),g.mul(g.sub(.5,curv),.17)));rgold=g.add(rgold,g.mul(ornament,-.045))
  rough=g.mix(cloth,rgold,g.add(.77,g.mul(weave,.065)));rough=g.mix(skin,rough,.48);rough=g.mix(hair,rough,g.add(.38,g.mul(noise,.08)))
  metal=g.mul(gold,g.sub(.96,g.mul(hair,.76)))
  height=g.add(g.mul(armor,g.add(g.mul(ornament,.78),g.add(g.mul(noise,.045),g.mul(scratches,-.022)))),g.add(g.mul(cloth,g.mul(weave,.12)),g.add(g.mul(hair,g.mul(hairlines,.035)),g.mul(skin,g.mul(micro,.009)))))
 # Cavities retain patina; edge and groove relief is carried by baked color and roughness.
 aof=g.add(.77,g.mul(ao.outputs['AO'],.23));base=g.mix(g.sub(1,aof),base,(.025,.018,.01,1));rough=g.add(rough,g.mul(g.sub(1,ao.outputs['AO']),.12))
 orm=g.node('ShaderNodeCombineColor');g.set(orm.inputs['Red'],ao.outputs['AO']);g.set(orm.inputs['Green'],rough);g.set(orm.inputs['Blue'],metal)
 bump=g.node('ShaderNodeBump');g.set(bump.inputs['Height'],height);bump.inputs['Distance'].default_value=.0016;bump.inputs['Strength'].default_value=.65
 bs=g.node('ShaderNodeBsdfPrincipled');g.set(bs.inputs['Base Color'],base);g.set(bs.inputs['Metallic'],metal);g.set(bs.inputs['Roughness'],rough);g.set(bs.inputs['Normal'],bump.outputs['Normal'])
 out=g.node('ShaderNodeOutputMaterial');g.set(out.inputs['Surface'],bs.outputs[0])
 return g,mat,base,orm.outputs[0],bs,out
def bake(o,size,reuse_base=False):
 started=time.time();g,mat,base,orm,bs,out=make_procedural(o,o.name=='Godwyn_Sword');s=bpy.context.scene
 s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.threads_mode='FIXED';s.render.threads=8;s.render.bake.margin=12;s.render.bake.use_clear=True
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 images={};emit=g.node('ShaderNodeEmission');emit.inputs['Strength'].default_value=1
 for kind,socket in [('basecolor',base),('orm',orm),('normal',None)]:
  if kind=='basecolor' and reuse_base:
   im=bpy.data.images.load(str(OUT/'textures'/f'astra_character_{o.name}_{kind}_{size}.png'),check_existing=False);im.colorspace_settings.name='sRGB';im.pack();images[kind]=im;print('REUSED completed 4K base',flush=True);continue
  name=f'astra_character_{o.name}_{kind}_{size}';im=bpy.data.images.new(name,width=size,height=size,alpha=False,float_buffer=False);im.colorspace_settings.name='sRGB' if kind=='basecolor' else 'Non-Color'
  n=g.node('ShaderNodeTexImage');n.image=im;g.n.active=n
  for node in g.n:node.select=node==n
  if socket is not None:
   g.set(emit.inputs['Color'],socket);g.set(out.inputs['Surface'],emit.outputs[0]);bpy.ops.object.bake(type='EMIT')
  else:
   # Normal baking needs only the bump field; remove AO evaluation from the shader.
   for ao in [node for node in g.n if node.type=='AMBIENT_OCCLUSION']:
    for sock in ao.outputs:
     for link in list(sock.links):
      dest=link.to_socket;g.l.remove(link);g.set(dest,1)
   g.set(out.inputs['Surface'],bs.outputs[0]);bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
  im.filepath_raw=str(OUT/'textures'/f'{name}.png');im.file_format='PNG';im.save();im.pack();images[kind]=im
  print('BAKED',name,'elapsed',round(time.time()-started),flush=True)
 return images
def portable_material(name,ims,kind='gold'):
 m=bpy.data.materials.new(name);m.use_nodes=True;g=Graph(m);out=g.node('ShaderNodeOutputMaterial');bs=g.node('ShaderNodeBsdfPrincipled');g.set(out.inputs['Surface'],bs.outputs[0])
 tx={}
 for key,im in ims.items():
  n=g.node('ShaderNodeTexImage');n.image=im;n.label=key+' • baked and packed';tx[key]=n
 g.set(bs.inputs['Base Color'],tx['basecolor'].outputs[0]);sep=g.node('ShaderNodeSeparateColor');g.set(sep.inputs[0],tx['orm'].outputs[0]);g.set(bs.inputs['Roughness'],sep.outputs['Green']);g.set(bs.inputs['Metallic'],sep.outputs['Blue'])
 normal=g.node('ShaderNodeNormalMap');g.set(normal.inputs['Color'],tx['normal'].outputs[0]);g.set(bs.inputs['Normal'],normal.outputs[0])
 # Recognized glTF occlusion socket, reusing the packed ORM red channel.
 ng=bpy.data.node_groups.get('glTF Material Output')
 if ng is None:
  ng=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');ng.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
 oc=g.node('ShaderNodeGroup');oc.node_tree=ng;g.set(oc.inputs['Occlusion'],sep.outputs['Red'])
 if kind=='cloth':bs.inputs['Sheen Weight'].default_value=.18;bs.inputs['Sheen Roughness'].default_value=.7;bs.inputs['Sheen Tint'].default_value=(.10,.14,.30,1)
 if kind=='skin':
  bs.inputs['Subsurface Weight'].default_value=.075;bs.inputs['Subsurface Radius'].default_value=(1,.42,.20);bs.inputs['Subsurface Scale'].default_value=.018
  bs.inputs['Emission Color'].default_value=(1,.65,.15,1);bs.inputs['Emission Strength'].default_value=.014
 for i,n in enumerate(g.n):n.location=((i%4)*240,-(i//4)*240)
 return m
def main():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose()
 char=bpy.data.objects['char1'];sword=bpy.data.objects['Godwyn_Sword'];sword.hide_render=False
 hair=char.data.attributes.new('astra_hair','FLOAT','POINT')
 hairids=[v.index for v in char.vertex_groups if 'hair' in v.name]
 for v in char.data.vertices:hair.data[v.index].value=min(1,sum(w.weight for w in v.groups if w.group in hairids))
 # Keep a vertex-level material classification sampled from the source atlas before replacing it.
 src=bpy.data.images['godwyn_albedo'];arr=np.empty(len(src.pixels),dtype=np.float32);src.pixels.foreach_get(arr);arr=arr.reshape(src.size[1],src.size[0],4)
 classes=[]
 for f in char.data.polygons:
  uv=sum((char.data.uv_layers.active.data[i].uv for i in f.loop_indices),Vector((0,0)))/len(f.loop_indices);c=arr[int(uv.y*(src.size[1]-1))%src.size[1],int(uv.x*(src.size[0]-1))%src.size[0]]
  classes.append(1 if c[2]>c[0]*1.35 else (2 if c[0]<c[2]*1.65 else 0))
 charims=bake(char,4096);swordims=bake(sword,2048)
 char.data.materials.clear()
 for name,kind in [('Astra engraved royal gold','gold'),('Astra midnight blue woven silk','cloth'),('Astra pale golden skin','skin')]:char.data.materials.append(portable_material(name,charims,kind))
 for f,c in zip(char.data.polygons,classes):f.material_index=c
 sword.data.materials.clear();sword.data.materials.append(portable_material('Astra worn steel and gold hilt',swordims))
 s=bpy.context.scene;s.render.engine='BLENDER_EEVEE'
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 for name in ['front','chest','face','shoulder']:render_view('r2',name)
if __name__=='__main__':main()
