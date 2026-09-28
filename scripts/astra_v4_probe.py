import bpy,sys,json,hashlib,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3_build as b
import astra_v3m_publish as p
O=R/'renders/astra/v4';O.mkdir(parents=True,exist_ok=True)
assert Path('/home/aaron/godwyn-boss-fight')==R
protected=list((R/'models').glob('astra_character_v3*'))
(O/'protected_before.json').write_text(json.dumps({str(x.relative_to(R)):{'size':x.stat().st_size,'mtime_ns':x.stat().st_mtime_ns} for x in protected},indent=2))
hashes={str(x.relative_to(R)):p.sha256(x) for x in [R/'models/astra_character_v3.blend',R/'models/meshy_godwyn_full_rigged.glb',R/'models/meshy_godwyn_full.glb']}
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(R/'models/meshy_godwyn_full_rigged.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.name='Astra_V4_Rig';body=next(o for o in bpy.context.scene.objects if o.type=='MESH');body.name='V4_Body';rig.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
pts=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);ims=b.pbr_images(body.data.materials[0]);rep={'hashes':hashes,'bones':list(rig.data.bones.keys()),'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'vertices':len(pts),'triangles':sum(len(f.vertices)-2 for f in body.data.polygons),'weights':p.weight_audit([body],rig),'textures':{k:None if im is None else {'name':im.name,'size':list(im.size)} for k,im in ims.items()},'bone_positions':{x.name:list(rig.matrix_world@x.head_local) for x in rig.data.bones}}
for im in bpy.data.images:
 if im.has_data:im.pack()
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'raw.blend'))
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'models/meshy_godwyn_full.glb'));src=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');rep['source_textures']={k:None if im is None else {'name':im.name,'size':list(im.size)} for k,im in b.pbr_images(src.data.materials[0]).items()}
(O/'raw_probe.json').write_text(json.dumps(rep,indent=2));print('V4_PROBE',json.dumps(rep),flush=True)
