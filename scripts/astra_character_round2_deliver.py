"""Render unchanged round-1 cameras, export, verify geometry and embedded textures."""
import bpy,sys,json,struct,hashlib,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
from astra_character_round2_diagnostic import signature
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));reset_pose();s=bpy.context.scene
 report=json.loads((OUT/'round2_bake_diagnostic.json').read_text())
 now={n:signature(bpy.data.objects[n]) for n in report['preservation']}
 np.save(OUT/'round2_work/final_face_materials.npy',np.array([p.material_index for p in bpy.data.objects['char1'].data.polygons],np.int8))
 assert now==report['preservation'],'Geometry/weights/UV/modifier/transform preservation failed'
 assert sha(ROOT/'models/godwyn_game.glb')==report['source_sha256']
 record={str(p):sha(p) for pat in ['before_*.png','after_*.png'] for p in OUT.glob(pat)}
 s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=960;s.render.resolution_percentage=100
 assert s.view_settings.exposure==report['scene']['exposure']
 for name in VIEWS:render_view('round2',name)
 reset_pose();pose=measure_pose();assert pose['spike_edges']==0
 assert record=={p:sha(Path(p)) for p in record}
 s.camera.location=VIEWS['three_quarter'][0];aim(s.camera,VIEWS['three_quarter'][1]);s.camera.data.ortho_scale=VIEWS['three_quarter'][2]
 objects=[bpy.data.objects[n] for n in ['Armature','char1','Godwyn_Sword','Astra_Undersleeves']]
 used={n.image for o in objects if o.type=='MESH' for m in o.data.materials for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
 for im in used:im.pack()
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]
 p=ROOT/'models/astra_character_v2.glb'
 bpy.ops.export_scene.gltf(filepath=str(p),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_skins=True,export_normals=True,export_tangents=True,export_texcoords=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
 blob=p.read_bytes();length,kind=struct.unpack_from('<II',blob,12);doc=json.loads(blob[20:20+length]);start=28+length
 images=[]
 for im in doc['images']:
  bv=doc['bufferViews'][im['bufferView']];raw=blob[start+bv.get('byteOffset',0):start+bv.get('byteOffset',0)+bv['byteLength']];assert raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack_from('>II',raw,16);assert w==h and w in [2048,4096]
  images.append({'name':im.get('name'),'size':[w,h],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
 assert all('normalTexture' in m and 'metallicRoughnessTexture' in m['pbrMetallicRoughness'] for m in doc['materials'])
 report['delivery']={'source_unchanged':True,'geometry_weights_uvs_transforms_modifiers_unchanged':True,'round1_render_hashes_preserved':record,'views':{n:VIEWS[n] for n in VIEWS},'render_engine':s.render.engine,'resolution':[960,960],'raised_pose_spike_edges':pose['spike_edges'],'raised_pose_longest_edge_m':pose['max_edge'],'raised_pose_stretch_p99':pose['stretch_p99'],'glb_bytes':len(blob),'embedded_images':images,'materials':doc['materials'],'skins':len(doc['skins'])}
 (OUT/'round2_bake_diagnostic.json').write_text(json.dumps(report,indent=2));(OUT/'round2_exported_gltf.json').write_text(json.dumps(doc,indent=2))
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(p));setup();reset_pose()
 render_view('round2_glb_check','three_quarter');render_view('round2_glb_check','arms_raised')
 report['delivery']['glb_fresh_import_rendered']=True;(OUT/'round2_bake_diagnostic.json').write_text(json.dumps(report,indent=2))
 print('ROUND2 DELIVERED',flush=True)
if __name__=='__main__':main()
