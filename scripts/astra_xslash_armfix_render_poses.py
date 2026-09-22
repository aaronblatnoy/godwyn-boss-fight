"""Evaluate the corrected poses using the scene's saved camera and EEVEE settings."""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_v2_armfix_trial.blend'))
s=bpy.context.scene
assert s.render.engine=='BLENDER_EEVEE' and s.render.image_settings.file_format=='PNG'
out=ROOT/'renders/astra/v2_final_on_char/armfix_after';out.mkdir(exist_ok=True)
for f in [36,37,38,39,40,41,44,45,46,47,48,49,50,51,52,53]:
 s.frame_set(f);s.render.filepath=str(out/f'{f:03d}.png');bpy.ops.render.render(write_still=True)
 print('ARMFIX POSE',f,flush=True)
