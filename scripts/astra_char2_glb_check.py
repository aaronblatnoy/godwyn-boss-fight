import bpy,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
import astra_character_common as c
from astra_char2_render import render,configure
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));configure();c.reset_pose();assert not bpy.data.actions[:];bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(ROOT/'models/astra_character_v2.glb'))
assert bpy.data.objects.get('Armature');assert bpy.data.objects.get('char1');assert not bpy.data.actions[:]
c.setup();render('glb_check',['face'])
r=json.loads((OUT/'validation.json').read_text());r['glb']['render_roundtrip_pending']=False;r['glb']['fresh_import_rendered']=True;r['glb']['fresh_import_actions']=len(bpy.data.actions);(OUT/'validation.json').write_text(json.dumps(r,indent=2))
