"""Actual hero assembly compatibility; no writes to motion/cine inputs."""
import sys,json,bpy
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(R/'scripts'))
import astra_cine_hero_render as hero
source=R/'models/astra_character_r6_collar.blend'
if '--canonical' in sys.argv:source=R/'models/astra_character_v2.blend'
if '--head' in sys.argv:source=R/'models/astra_character_r6_head.blend'
scene,result=hero.assemble_inputs(R/'models/astra_xslash_v2_final_wip.blend',source)
result['source']=str(source);result['visible_native_curve_objects']=sum(o.type=='CURVES' and not o.hide_render for o in scene.objects)
result['replacement_head_present']='AstraChar2_R6_MPFB_Head' in scene.objects
assert result['rest_transform_max_error']==0
(R/'renders/astra/char2'/('r6_head_hero_assembly.json' if '--head' in sys.argv else 'r6_hero_assembly.json')).write_text(json.dumps(result,indent=2));print('HERO ASSEMBLY PASS',flush=True)
