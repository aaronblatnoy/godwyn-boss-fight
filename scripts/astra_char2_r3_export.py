import bpy,sys,json,struct,os
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose();bpy.context.scene.frame_set(1);reset_pose()
for o in bpy.data.objects:
 if o.type in ('MESH','ARMATURE'):o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
objects=[o for o in bpy.data.objects if o.name in ['Armature','char1','Godwyn_Sword','Astra_Undersleeves'] or o.name.startswith('AstraChar2_')]
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['char1'];o=bpy.data.objects['char1'];tri=o.modifiers.new('R3 export triangulation','TRIANGULATE');tri.min_vertices=5
p=ROOT/'models/astra_character_v2_round3_export.glb'
bpy.ops.export_scene.gltf(filepath=str(p),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_skins=True,export_normals=True,export_tangents=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
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
 mat=bpy.data.materials[material_name];im=mat.node_tree.nodes['Image Texture.001'].image;a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);metal=a.reshape(im.size[1],im.size[0],4)[:,:,2]
 mask=np.repeat((.65*(1-np.clip(metal,0,1)))[:,:,None],3,axis=2);maskpath=OUT/('r3_'+label+'_sheen.png');png(maskpath,srgb(mask));data=maskpath.read_bytes()
 while len(binary)%4:binary.append(0)
 offset=len(binary);binary.extend(data);view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(data)})
 source=len(g['images']);g['images'].append({'name':'R3 '+label+' masked velvet sheen','bufferView':view,'mimeType':'image/png'})
 texture=len(g['textures']);g['textures'].append({'source':source})
 gm=next(m for m in g['materials'] if m['name']==material_name);gm['extensions']['KHR_materials_sheen']['sheenColorTexture']={'index':texture,'texCoord':0}
while len(binary)%4:binary.append(0)
g['buffers'][0]['byteLength']=len(binary);encoded=json.dumps(g,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
with open(p,'wb') as f:f.write(struct.pack('<III',0x46546c67,2,12+8+len(encoded)+8+len(binary))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary)
r={'path':str(ROOT/'models/astra_character_v2.glb'),'bytes':p.stat().st_size,'skins':len(g.get('skins',[])),'joints':[len(s['joints']) for s in g.get('skins',[])],'animations':len(g.get('animations',[])),'extensions':g.get('extensionsUsed',[]),'hair_nodes':[n['name'] for n in g['nodes'] if 'phys_hair' in n.get('name','')],'object_material_slots':{o.name:[m.name for m in o.data.materials] for o in objects if o.type=='MESH'}}
assert r['animations']==0 and r['skins'];os.replace(p,ROOT/'models/astra_character_v2.glb')
bpy.context.scene['astra_char2_round3_quality_gate']='NOT_MET: consult ROUND3_REPORT.md';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
# Fresh import proves exported skeleton and meshes are loadable.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'models/astra_character_v2.glb'))
r['reimport_meshes']=sum(o.type=='MESH' for o in bpy.data.objects);r['reimport_armatures']={o.name:len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE'};r['reimport_actions']=len(bpy.data.actions)
(OUT/'r3_export_validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
