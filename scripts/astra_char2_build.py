import bpy,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_face import apply_face
from astra_char2_skin import apply_skin
from astra_char2_render import render
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_prechar2.blend'))
reset_pose();apply_face();apply_skin();reset_pose()
for o in bpy.data.objects:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2_char2_work.blend'))
# Work file is reviewable before promotion to the shared stable model path.
render('draft8',['face','face_three_quarter'])
