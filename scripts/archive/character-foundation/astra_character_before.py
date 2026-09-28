import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
reset_pose();setup()
for o in [bpy.data.objects['char1'],bpy.data.objects['Godwyn_Sword']]:print('WORLD',o.name,[tuple(o.matrix_world@Vector(c)) for c in o.bound_box], 'parent',o.parent.name if o.parent else None,o.parent_type,o.parent_bone,flush=True)
(OUT/'weights_before.json').write_text(json.dumps(measure_pose(),indent=2))
for name in VIEWS:render_view('before',name)
