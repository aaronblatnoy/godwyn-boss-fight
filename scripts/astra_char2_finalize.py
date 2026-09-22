import bpy,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
m=bpy.data.objects['char1'].data.materials[2]
m['emission_rebalance']='Nonzero epidermal transmission map, approximately 0.6–8.4% of canonical radiance. Canonical strength remains 2.5.'
m['base_color_note']='Canonical .95/.90/.82 retained as Principled default/reference; linked epidermal albedo supplies warmer, darker spatial reflectance.'
bpy.context.scene['AstraChar2_quality_gate']='NOT MET. Facial features and skin detail improved; the face still reads synthetic/waxy and does not match the approved photographic likeness.'
bpy.context.scene['AstraChar2_review_report']=str(OUT/'REPORT.md')
assert not bpy.data.actions[:];assert bpy.context.scene.render.engine=='CYCLES';assert bpy.context.scene.cycles.device=='GPU'
assert abs(bpy.context.scene.view_settings.exposure+.35)<1e-5
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
r=json.loads((OUT/'validation.json').read_text());r['quality_gate']={'status':'NOT_MET','visible_improvement':['Defined brows, irises/pupils, corneal glints, eyelid aperture and wet corners','Distinct lip contours, chin/cheek planes, philtrum, nasal openings','Warmer skin with pigment/roughness variation and microdetail','Reduced forehead-to-lower-face proportion mismatch'],'remaining':['Not a photographic likeness of the approved man','Orbital transitions and lower lids remain simplified; eye integration is synthetic','Nose/alar/philtrum anatomy needs finer reconstruction; openings are not fully convincing','Skin still reads too smooth/waxy under the mandated evaluation lighting','Preserved hair shell and material boundary defects further limit overall realism, outside this round']};r['environment_blockers']=[];r['final_blend_engine']='CYCLES';r['final_blend_device']='GPU / local METAL';r['tangents_present_all_char1_glb_primitives']=True;r['final_blend_actions']=len(bpy.data.actions);(OUT/'validation.json').write_text(json.dumps(r,indent=2))
print('FINAL METADATA SAVED; VISUAL GATE NOT MET',flush=True)
