"""Fresh GLB import and portrait check; no scene or model writes."""
import bpy,sys,json,shutil
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_character_common import setup
from astra_char2_round2_compare import compare
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'models/astra_character_v2.glb'))
assert 'char1' in bpy.data.objects and 'Armature' in bpy.data.objects
assert len(bpy.data.objects['char1'].data.materials)==5
assert not bpy.data.actions[:]
report={'fresh_import_loadable':True,'armature_bones':len(bpy.data.objects['Armature'].data.bones),'actions':len(bpy.data.actions),'char1_material_slots':[m.name for m in bpy.data.objects['char1'].data.materials],'objects':sorted(bpy.data.objects.keys()),'native_vs_glb':'GLB imports skin maps, tangents and emission; core glTF does not preserve Cycles subsurface scattering.'}
setup();compare('round2_glb_roundtrip')
shutil.copy2(OUT/'after_sidebyside.png',OUT/'sidebyside_face.png')
(OUT/'round2_glb_roundtrip.json').write_text(json.dumps(report,indent=2))
print('FRESH GLB IMPORT PASSED',flush=True)
