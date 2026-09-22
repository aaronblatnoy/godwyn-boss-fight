"""Read-only assembly check against the cinematography agent's real loader."""
import sys,json
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(R/'scripts'))
import astra_cine_hero_render as hero
scene,result=hero.assemble_inputs(R/'models/astra_xslash_v2_final_wip.blend',R/'models/astra_character_v2.blend')
result['visible_native_curve_objects']=sum(o.type=='CURVES' and not o.hide_render for o in scene.objects)
result['visible_portable_strand_objects']=sum(o.name.startswith('AstraChar2_R4_Strands_') and not o.hide_render for o in scene.objects)
assert result['visible_native_curve_objects']==14 and result['visible_portable_strand_objects']==0
(R/'renders/astra/char2/r4_hero_assembly.json').write_text(json.dumps(result,indent=2));print('HERO ASSEMBLY PASS',flush=True)
