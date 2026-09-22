import bpy,sys,json,struct,os
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_character_common import reset_pose
source=ROOT/'models/astra_character_r6_collar.blend'
if '--head' in sys.argv:source=ROOT/'models/astra_character_r6_head.blend'
bpy.ops.wm.open_mainfile(filepath=str(source));reset_pose();bpy.context.scene.frame_set(1);reset_pose()
for o in bpy.data.objects:
 if o.type in ('MESH','ARMATURE'):o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
objects=[o for o in bpy.data.objects if o.type in ('MESH','ARMATURE') and not o.name.startswith(('AstraChar2_R4_Control_','AstraChar2_R5_Control_')) and 'ClothFitEnvelope' not in o.name and (o.type=='ARMATURE' or len(o.data.polygons)>0) and (o.name in ['Armature','char1','Godwyn_Sword','Astra_Undersleeves'] or o.name.startswith('AstraChar2_'))]
for ob in objects:
 if ob.name.startswith('AstraChar2_R4_Strands_'):ob.hide_render=False
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['char1'];o=bpy.data.objects['char1'];tri=o.modifiers.new('R4 export triangulation','TRIANGULATE');tri.min_vertices=5
p=ROOT/'models/astra_character_r6_export.glb'
bpy.ops.export_scene.gltf(filepath=str(p),export_format='GLB',export_extras=True,use_selection=True,export_apply=True,export_animations=False,export_skins=True,export_normals=True,export_tangents=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
o.modifiers.remove(tri)
with open(p,'rb') as f:
 f.read(12);size,typ=struct.unpack('<II',f.read(8));g=json.loads(f.read(size))
# The exporter omits linked arithmetic on Sheen Weight. Embed a portable RGB
# sheen mask so metallic embroidery stays free of velvet fuzz in the GLB too.
import numpy as np
from astra_char2_skin import png,srgb
with open(p,'rb') as f:
 f.read(12);jsize,jtype=struct.unpack('<II',f.read(8));f.read(jsize);bsize,btype=struct.unpack('<II',f.read(8));binary=bytearray(f.read(bsize))
for material_name,label in [('Astra Round2 royal blue and continuous gold trim','cloth'),('Astra Round2 royal blue undersleeves','sleeves')]:
 maskpath=OUT/('r3_'+label+'_sheen.png');data=maskpath.read_bytes()
 while len(binary)%4:binary.append(0)
 offset=len(binary);binary.extend(data);view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
 source=len(g['images']);g['images'].append({'name':'R3 '+label+' masked velvet sheen','bufferView':view,'mimeType':'image/png'})
 texture=len(g['textures']);g['textures'].append({'source':source})
 gm=next(m for m in g['materials'] if m['name']==material_name);gm['extensions']['KHR_materials_sheen']['sheenColorTexture']={'index':texture,'texCoord':0}
physics=json.loads((OUT/'r4_hair_physics.json').read_text());profiles={p['bone']:dict(p) for p in physics['chain_configuration']}
for profile in profiles.values():
 for key in ('head_world','tail_world'):
  x,y,z=profile[key];profile[key]=[x,z,-y]
 profile['coordinate_system']='GLTF_Y_UP_METERS'
 profile['spring_model']='unit-inertia damped angular spring; stiffness s^-2, damping s^-1'
for node in g['nodes']:
 if node.get('name') in profiles:node.setdefault('extras',{})['godwyn_hair_spring']=profiles[node['name']]
g['asset'].setdefault('extras',{})['godwyn_hair_physics']={'version':1,'bones':list(profiles),'local_test':'ENGINE_SPRING_AND_COLLISION_UNVALIDATED','engine_solver_required':True}
while len(binary)%4:binary.append(0)
g['buffers'][0]['byteLength']=len(binary);encoded=json.dumps(g,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
with open(p,'wb') as f:f.write(struct.pack('<III',0x46546c67,2,12+8+len(encoded)+8+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary)
r={'path':str(ROOT/'models/astra_character_v2.glb'),'bytes':p.stat().st_size,'skins':len(g.get('skins',[])),'joints':[len(s['joints']) for s in g.get('skins',[])],'animations':len(g.get('animations',[])),'extensions':g.get('extensionsUsed',[]),'hair_nodes':[n['name'] for n in g['nodes'] if 'phys_hair' in n.get('name','')],'object_material_slots':{o.name:[m.name for m in o.data.materials] for o in objects if o.type=='MESH'}}
hairnodes=[n for n in g['nodes'] if n.get('name','').startswith('AstraChar2_R4_Strands_')]
r['hair_skinned_mesh_nodes']=[n['name'] for n in hairnodes if 'skin' in n and 'mesh' in n]
r['spring_profiles']=len(profiles)
assert len(r['hair_skinned_mesh_nodes'])==14 and len(profiles)==12
for hn in hairnodes:
 for primitive in g['meshes'][hn['mesh']]['primitives']:
  assert {'JOINTS_0','WEIGHTS_0','POSITION'}.issubset(primitive['attributes'])
  hm=g['materials'][primitive['material']]
  assert hm['extensions']['KHR_materials_anisotropy']['anisotropyStrength']>.7
assert r['animations']==0 and r['skins'] and r['joints']==[121]

for ob in objects:
 if ob.name.startswith('AstraChar2_R4_Strands_'):ob.hide_render=True;ob.hide_set(True)
bpy.context.scene['astra_char2_round4_quality']='Native curves groom; see ROUND4_REPORT.md';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_r6_promote.blend'))
# Fresh import proves exported skeleton and meshes are loadable.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(p))
r['reimport_meshes']=sum(o.type=='MESH' for o in bpy.data.objects);r['reimport_armatures']={o.name:len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE'};r['reimport_actions']=len(bpy.data.actions)
assert list(r['reimport_armatures'].values())==[121] and r['reimport_actions']==0
os.replace(p,ROOT/'models/astra_character_v2.glb');os.replace(ROOT/'models/astra_character_r6_promote.blend',ROOT/'models/astra_character_v2.blend')
(OUT/'r6_export_validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
