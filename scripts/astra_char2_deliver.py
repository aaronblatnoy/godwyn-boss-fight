"""Validate, render comparison views, export portable geometry, then promote atomically."""
import bpy,sys,json,struct,shutil,os
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_render import render,configure
from astra_char2_audit import audit
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_char2_work.blend'));reset_pose();configure();report=audit()
if '--export-only' not in sys.argv:render('after',['face','front','face_three_quarter'])
reset_pose()
objects=[bpy.data.objects[n] for n in ['Armature','char1','Godwyn_Sword','Astra_Undersleeves']]+[o for o in bpy.data.objects if o.name.startswith('AstraChar2_')]
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Armature']
for o in objects:
 if o.type=='MESH':
  for m in o.data.materials:
   if m and m.use_nodes:
    for n in m.node_tree.nodes:
     if n.type=='TEX_IMAGE' and n.image:n.image.pack()
path=ROOT/'models/astra_character_v2_char2_export.glb'
tri=bpy.data.objects['char1'].modifiers.new('AstraChar2 temporary export triangulation','TRIANGULATE');tri.min_vertices=5
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_skins=True,export_normals=True,export_tangents=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
bpy.data.objects['char1'].modifiers.remove(tri)
blob=path.read_bytes();length,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+length]);assert doc.get('skins');assert not doc.get('animations')
assert any(n.get('name')=='char1' for n in doc['nodes'])
char_node=next(n for n in doc['nodes'] if n.get('name')=='char1')
assert all('TANGENT' in p['attributes'] for p in doc['meshes'][char_node['mesh']]['primitives']), 'Missing portable tangents'
skin=next(m for m in doc['materials'] if m['name']=='Astra pale golden skin final');assert 'normalTexture' in skin;assert 'emissiveTexture' in skin;assert skin['extensions']['KHR_materials_emissive_strength']['emissiveStrength']==2.5
report['glb']={'bytes':len(blob),'skins':len(doc['skins']),'animations':len(doc.get('animations',[])),'nodes':len(doc['nodes']),'images':len(doc.get('images',[])),'skin_material':skin,'extensions':doc.get('extensionsUsed',[]),'geometry_units':'meters, glTF Y up','render_roundtrip_pending':True}
(OUT/'exported_gltf.json').write_text(json.dumps(doc,indent=2));(OUT/'validation.json').write_text(json.dumps(report,indent=2))
old=ROOT/'models/astra_character_v2.glb';back=ROOT/'models/astra_character_v2_prechar2.glb'
if not back.exists():shutil.copy2(old,back)
os.replace(path,old)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
print('CHAR2 DELIVERED',flush=True)
