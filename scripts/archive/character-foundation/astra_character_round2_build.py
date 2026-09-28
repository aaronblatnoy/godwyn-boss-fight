"""Round 2 material-only build; source geometry, rig, UVs and sword are immutable."""
import bpy,sys,json,time,hashlib,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
from astra_character_bake import Graph,portable_material
from astra_character_round2_diagnostic import signature
WORK=OUT/'round2_work';TEX=OUT/'textures';BACK=OUT/'round1_backup'

def tex(g,path):
 n=g.node('ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True);n.image.colorspace_settings.name='Non-Color';n.image.pack();return n.outputs['Color']

def procedural(o,kind):
 m=bpy.data.materials.new('Round2 editable procedural '+kind);m.use_nodes=True;m.use_fake_user=True;g=Graph(m)
 uv=g.node('ShaderNodeTexCoord');p=g.node('ShaderNodeVectorMath');p.operation='SCALE';g.set(p.inputs[0],uv.outputs['Object']);p.inputs[3].default_value=.01
 xyz=g.node('ShaderNodeSeparateXYZ');g.set(xyz.inputs[0],p.outputs[0]);x,y,z=xyz.outputs
 broad=g.noise(p.outputs[0],11,2);fine=g.noise(p.outputs[0],180,2)
 geo=g.node('ShaderNodeNewGeometry');curv=g.ramp(geo.outputs['Pointiness'],.465,.535)
 aosep=g.node('ShaderNodeSeparateColor');g.set(aosep.inputs[0],tex(g,WORK/'cavity_4096.png'));ao=aosep.outputs['Red']
 if kind=='sleeves':ao=1
 # Deliberate plate zones: pale shoulder gold, champagne cuirass, aged limb gold.
 upper=g.ramp(z,2.12,2.28);shoulder=g.mul(g.ramp(g.math('ABSOLUTE',x),.28,.38),g.ramp(z,2.26,2.4))
 gold=g.mix(upper,(.48,.30,.080,1),(.62,.42,.125,1));gold=g.mix(shoulder,gold,(.68,.49,.19,1))
 gold=g.mix(g.mul(g.sub(broad,.25),.10),gold,(.48,.32,.12,1))
 goldrough=g.add(.21,g.add(g.mul(g.sub(1,curv),.40),g.add(g.mul(g.sub(1,ao),.18),g.mul(g.sub(broad,.5),.07))))
 # Fine brushed field, low amplitude. No hard material mask goes into this bump.
 stretched=g.vec(g.mul(x,8),g.mul(y,8),g.mul(z,.25));brushing=g.noise(stretched,120,2)
 phase=g.math('SINE',g.add(g.mul(x,78),g.mul(g.math('SINE',g.mul(z,52)),1.3)))
 engraving=g.gauss(phase,.075)
 bs=g.node('ShaderNodeBsdfPrincipled');bs.inputs['IOR'].default_value=1.45
 normal=g.node('ShaderNodeBump');normal.inputs['Distance'].default_value=.00016;normal.inputs['Strength'].default_value=.35
 if kind=='gold':
  base=gold;rough=goldrough;metal=1.;height=g.add(g.mul(engraving,.35),g.mul(brushing,.07))
 else:
  # Linear RGB spec, small balanced thread variation; no AO/exposure multiplied into color.
  weave=g.mul(g.math('SINE',g.mul(x,1100)),g.math('SINE',g.mul(z,1100)))
  tint=g.mix(g.add(.5,g.mul(g.sub(broad,.5),.6)),(.076,.114,.3325,1),(.084,.126,.3675,1))
  trim=0 if kind=='sleeves' else tex(g,WORK/'source_trim_mask.png')
  if kind!='sleeves':
   sep=g.node('ShaderNodeSeparateColor');g.set(sep.inputs[0],trim);trim=g.ramp(sep.outputs['Red'],.23,.77)
  base=g.mix(trim,tint,(.59,.415,.16,1));rough=g.mix(trim,g.add(.63,g.mul(weave,.025)),g.add(.23,g.mul(g.sub(1,ao),.22)));metal=trim
  # Preserve crisp source ornament without boundary-normal explosions.
  height=g.mul(weave,.075);normal.inputs['Distance'].default_value=.00010
  bs.inputs['Specular IOR Level'].default_value=.16
  bs.inputs['Sheen Weight'].default_value=0
 g.set(normal.inputs['Height'],height);g.set(bs.inputs['Normal'],normal.outputs['Normal']);g.set(bs.inputs['Base Color'],base);g.set(bs.inputs['Roughness'],rough);g.set(bs.inputs['Metallic'],metal)
 orm=g.node('ShaderNodeCombineColor');g.set(orm.inputs['Red'],ao);g.set(orm.inputs['Green'],rough);g.set(orm.inputs['Blue'],metal)
 out=g.node('ShaderNodeOutputMaterial');g.set(out.inputs['Surface'],bs.outputs[0])
 for i,n in enumerate(g.n):n.location=((i%7)*220,-(i//7)*180)
 return g,m,base,orm.outputs[0],bs,out

def bake(o,kind,size,prefix):
 g,m,base,orm,bs,out=procedural(o,kind);o.data.materials.clear();o.data.materials.append(m)
 for f in o.data.polygons:f.material_index=0
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.threads_mode='FIXED';s.render.threads=6
 s.render.bake.margin=4;s.render.bake.margin_type='EXTEND';s.render.bake.use_clear=True;s.render.bake.use_selected_to_active=False;s.render.bake.use_cage=False
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
 emit=g.node('ShaderNodeEmission');emit.inputs['Strength'].default_value=1;ims={}
 for k,socket in [('basecolor',base),('orm',orm),('normal',None)]:
  path=TEX/f'{prefix}_{k}_{size}.png'
  if '--resume' in sys.argv and path.exists() and (kind!='gold' or (WORK/'gold_complete').exists()):
   im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name='sRGB' if k=='basecolor' else 'Non-Color';im.pack();ims[k]=im;print('REUSE',path.name,flush=True);continue
  im=bpy.data.images.new(f'{prefix}_{k}_{size}',width=size,height=size,alpha=False);im.colorspace_settings.name='sRGB' if k=='basecolor' else 'Non-Color'
  n=g.node('ShaderNodeTexImage');n.image=im;g.n.active=n
  for node in g.n:node.select=node==n
  if socket is None:g.set(out.inputs['Surface'],bs.outputs[0]);bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
  else:g.set(emit.inputs['Color'],socket);g.set(out.inputs['Surface'],emit.outputs[0]);bpy.ops.object.bake(type='EMIT')
  im.filepath_raw=str(path);im.file_format='PNG';im.save();im.pack();ims[k]=im;print('BAKED',path.name,flush=True)
 g.set(out.inputs['Surface'],bs.outputs[0])
 if kind=='gold':(WORK/'gold_complete').write_text('done')
 return ims

def main():
 bpy.ops.wm.open_mainfile(filepath=str(BACK/'astra_character_v2.blend'));reset_pose();s=bpy.context.scene
 char=bpy.data.objects['char1'];sleeves=bpy.data.objects['Astra_Undersleeves'];original=list(char.data.materials);classes=np.array([f.material_index for f in char.data.polygons]);before={n:signature(bpy.data.objects[n]) for n in ['char1','Godwyn_Sword','Astra_Undersleeves']}
 # Preserve original face/hair shaders and their exact packed pixel buffers.
 for im in bpy.data.images:
  if 'char1' in im.name:
   im.filepath_raw=str(BACK/'textures'/Path(im.filepath_raw).name);im.name='Round1 head '+im.name;im.use_fake_user=True
 for m in original:m.use_fake_user=True
 gold=bake(char,'gold',4096,'astra_character_char1');robe=bake(char,'robe',4096,'astra_character_char1_robe')
 char.data.materials.clear();gm=portable_material('Astra Round2 solid champagne gold',gold);rm=portable_material('Astra Round2 royal blue and continuous gold trim',robe,'cloth')
 rbs=next(n for n in rm.node_tree.nodes if n.type=='BSDF_PRINCIPLED');rbs.inputs['Sheen Weight'].default_value=0;rbs.inputs['Specular IOR Level'].default_value=.16
 for m in [gm,rm,original[2],original[0],original[1]]:char.data.materials.append(m)
 src=bpy.data.images.load(str(OUT/'source_2.png'),check_existing=True);a=np.empty(len(src.pixels),np.float32);src.pixels.foreach_get(a);a=a.reshape(src.size[1],src.size[0],4)
 cm=np.load(WORK/'classification.npz');protected=cm['protected'];trimfaces=cm['trim']
 counts={'head_faces_retained':0,'neutral_transition_faces_reclassified':0,'scrollwork_border_faces':int(trimfaces.sum())}
 for f,c in zip(char.data.polygons,classes):
  center=sum((char.matrix_world@char.data.vertices[v].co for v in f.vertices),Vector())/len(f.vertices)
  if protected[f.index]:f.material_index={0:3,1:4,2:2}[int(c)];counts['head_faces_retained']+=1
  elif trimfaces[f.index]:f.material_index=1
  elif c==2:
   uv=sum((char.data.uv_layers.active.data[i].uv for i in f.loop_indices),Vector((0,0)))/len(f.loop_indices);metal=a[min(int(uv.y*src.size[1]),src.size[1]-1),min(int(uv.x*src.size[0]),src.size[0]-1),2]
   f.material_index=0 if metal>.4 else 1;counts['neutral_transition_faces_reclassified']+=1
  else:f.material_index=int(c)
 sleeveims=bake(sleeves,'sleeves',2048,'astra_character_Astra_Undersleeves');sleeves.data.materials.clear();sm=portable_material('Astra Round2 royal blue undersleeves',sleeveims,'cloth');sbs=next(n for n in sm.node_tree.nodes if n.type=='BSDF_PRINCIPLED');sbs.inputs['Sheen Weight'].default_value=0;sbs.inputs['Specular IOR Level'].default_value=.16;sleeves.data.materials.append(sm)
 after={n:signature(bpy.data.objects[n]) for n in before};assert before==after,'Geometry, weights, modifiers, transforms or UVs changed'
 report=json.loads((OUT/'round2_bake_diagnostic.json').read_text());report['material_build']={'preservation_exact':True,'materials':counts,'gold_metallic':1,'gold_roughness_formula_range':[.125,.775],'robe_linear_target':[.08,.12,.35],'face_and_hair':'Exact round-1 shaders and maps above z=2.78m','sword':'Exact round-1 geometry, shader and three 2K maps retained, without rebaking an approved material','bake':{'engine':'CYCLES','margin':4,'margin_type':'EXTEND','selected_to_active':False,'cage':False,'isolation':'Separate gold and robe target atlases; gold procedural graph cannot emit blue or non-metal'}}
 (OUT/'round2_bake_diagnostic.json').write_text(json.dumps(report,indent=2))
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=960;s.render.resolution_percentage=100
 reset_pose();s.camera.location=VIEWS['three_quarter'][0];aim(s.camera,VIEWS['three_quarter'][1]);s.camera.data.ortho_scale=VIEWS['three_quarter'][2]
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 for v in ['three_quarter','chest','shoulder']:render_view('round2_preview',v)
if __name__=='__main__':main()
