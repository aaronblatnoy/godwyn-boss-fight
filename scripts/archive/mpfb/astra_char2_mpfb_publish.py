"""Publish only after native, hero-loader and GLB round-trip checks have passed."""
import bpy,sys,json,hashlib,shutil,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_mpfb_recombine import mesh_digest
from astra_char2_mpfb_clay import studio
from astra_character_common import reset_pose,aim

def main(src,glb):
 for f in ['mpfb_final_validation.json','mpfb_roundtrip_validation.json']:
  d=json.loads((O/f).read_text());assert d['bones']==121 and d['actions']==0 and d['neutral_restored'];assert d['weights']['unweighted_or_bad_sum_vertices']==0
 d=json.loads((O/'mpfb_final_validation.json').read_text());assert d['source']==src
 assert json.loads((O/'mpfb_roundtrip_validation.json').read_text())['source']==glb
 assert d['rest_matrix_error']==0 and d['banked_armor_hashes_preserved']
 hero=json.loads((O/'mpfb_final_hero_assembly.json').read_text());assert hero['rest_transform_max_error']==0 and hero['character_path']==str(R/src)
 canonical=R/'models/astra_character_v2.blend';assert hashlib.sha256(canonical.read_bytes()).hexdigest()=='68cf6f8cacd807822238f66bbed73faa98afa0308f8c516c7292b1a65085b56e'
 bpy.ops.wm.open_mainfile(filepath=str(R/src));reset_pose();hashes=json.loads((O/'mpfb_graft_i04.json').read_text())['banked_armor_mesh_and_weight_hashes'];assert all(mesh_digest(bpy.data.objects[n])==v for n,v in hashes.items())
 s=bpy.context.scene;s.view_layers[0].material_override=None;s.render.engine='CYCLES';s.cycles.samples=64;s.render.resolution_x=850;s.render.resolution_y=1266;s.render.resolution_percentage=100;s.camera.data.type='ORTHO';s.camera.location=(3.65,-6,2.885);aim(s.camera,(0,-.2,2.885));s.camera.data.ortho_scale=.67
 for ob in s.objects:
  if ob.type=='LIGHT':ob.data.energy=0
 for name,loc,power,size in [('Astra key',(-3,-4.5,5),700,2.0),('Astra fill',(3,-3,4),75,3),('Astra rim',(1,2,4.5),750,2)]:
  ob=bpy.data.objects[name];ob.data.type='AREA';ob.data.energy=power;ob.data.size=size;ob.data.color=(1,1,1);ob.location=loc;aim(ob,(0,-.2,2.8))
 s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.075,.075,.075,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.32
 s.view_settings.view_transform='AgX';s.view_settings.exposure=0;s.render.film_transparent=False
 bpy.context.preferences.filepaths.save_version=0;assert len(bpy.data.actions)==0
 bpy.ops.wm.save_as_mainfile(filepath=str(canonical));shutil.copyfile(R/glb,R/'models/astra_character_v2.glb')
 result={n:hashlib.sha256((R/'models'/n).read_bytes()).hexdigest() for n in ['astra_character_v2.blend','astra_character_v2.glb']};result['validated_candidate']=src;result['roundtrip_glb']=glb
 (O/'mpfb_published.json').write_text(json.dumps(result,indent=2));print('MPFB_PUBLISHED',result,flush=True)
if __name__=='__main__':
 a=sys.argv[sys.argv.index('--')+1:];main(a[0],a[1])
