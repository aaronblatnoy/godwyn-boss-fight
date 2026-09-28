import bpy,sys,json,struct,hashlib,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose()
lining=bpy.data.objects['Astra_Undersleeves']
if not lining.get('astra_recessed'):
 for v in lining.data.vertices:v.co.x+=6 if v.co.x<0 else -6
 lining.data.update();lining['astra_recessed']=True
s=bpy.context.scene
if '--skip-renders' not in sys.argv:
 for name in VIEWS:render_view('after',name)
 lining.hide_render=True;default_sword=VIEWS['sword'];VIEWS['sword']=((-.5,-6,1.65),(-.43,-.29,1.56),.48);render_view('after_hilt','sword');VIEWS['sword']=default_sword;lining.hide_render=False
 raised_pose();s.camera.location=(-3,-6,3.8);aim(s.camera,(-.45,-.1,2.6));s.camera.data.ortho_scale=1.15;s.render.filepath=str(OUT/'after_shoulder_raised.png');bpy.ops.render.render(write_still=True);reset_pose()
s.camera.location=VIEWS['three_quarter'][0];aim(s.camera,VIEWS['three_quarter'][1]);s.camera.data.ortho_scale=VIEWS['three_quarter'][2]
objects=[bpy.data.objects[n] for n in ['Armature','char1','Godwyn_Sword','Astra_Undersleeves']]
used={node.image for o in objects if o.type=='MESH' for mat in o.data.materials for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image}
stats=[]
for im in used:
 im.pack();a=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(a);a=a.reshape(im.size[1],im.size[0],4);mask=a[:,:,:3].max(2)>.04
 stats.append({'name':im.name,'size':list(im.size),'packed':bool(im.packed_file),'colorspace':im.colorspace_settings.name,'rgb_std_on_nonblack':a[:,:,:3][mask].std(0).tolist(),'nonblack_fraction':float(mask.mean())})
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Armature']
path=ROOT/'models/astra_character_v2.glb'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_skins=True,export_normals=True,export_tangents=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
blob=path.read_bytes();length,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+length]);binstart=20+length+8
images=[]
for im in doc.get('images',[]):
 bv=doc['bufferViews'][im['bufferView']];raw=blob[binstart+bv.get('byteOffset',0):binstart+bv.get('byteOffset',0)+bv['byteLength']];assert raw[:8]==b'\x89PNG\r\n\x1a\n';width,height=struct.unpack_from('>II',raw,16)
 images.append({'name':im.get('name'),'mimeType':im['mimeType'],'bufferView':im['bufferView'],'embedded_bytes':len(raw),'width':width,'height':height,'sha256':hashlib.sha256(raw).hexdigest()})
assert len(images)>=9 and all(i['width'] in [2048,4096] and i['height'] in [2048,4096] for i in images)
assert all('normalTexture' in m and 'metallicRoughnessTexture' in m['pbrMetallicRoughness'] for m in doc['materials'])
original=json.loads((OUT/'source_inspection.json').read_text())['source_sha256'];current=hashlib.sha256((ROOT/'models/godwyn_game.glb').read_bytes()).hexdigest();assert original==current
report={'source_sha256_unchanged':current,'glb_bytes':len(blob),'images':images,'materials':doc['materials'],'skins':len(doc.get('skins',[])),'mesh_names':[m.get('name') for m in doc['meshes']],'texture_statistics':stats,'extensionsUsed':doc.get('extensionsUsed',[])}
(OUT/'export_verification.json').write_text(json.dumps(report,indent=2));(OUT/'exported_gltf.json').write_text(json.dumps(doc,indent=2))
print(json.dumps({'images':images,'skins':report['skins'],'source_unchanged':True},indent=2),flush=True)
# Retain the evaluation rig, clean packed image materials, and a rest pose in the .blend.
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
# Fresh GLB import checks the exported representation, including texture links and the rigid sword skin.
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(path));setup();reset_pose()
roundtrip={'images':[{'name':i.name,'size':list(i.size)} for i in bpy.data.images if i.type!='RENDER_RESULT'],'meshes':[{ 'name':o.name,'vertices':len(o.data.vertices),'materials':[m.name for m in o.data.materials]} for o in bpy.data.objects if o.type=='MESH' and o.name!='Astra evaluation ground']}
(OUT/'roundtrip_verification.json').write_text(json.dumps(roundtrip,indent=2))
render_view('glb_check','three_quarter');render_view('glb_check','arms_raised')
