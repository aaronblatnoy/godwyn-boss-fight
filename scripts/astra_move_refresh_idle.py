"""Refresh stable idle surface audit and approved render tint; keys unchanged."""
import sys,json
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_move_common import Builder,ROOT,OUT,bpy
# Capture surface selectors from the stable base, then point the helper at the saved action.
b=Builder('idle_guard',97,True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_move_idle_guard_wip.blend'))
from astra_move_grip_fix import fix_grip
fix_grip()
b.s=bpy.context.scene;b.r=bpy.data.objects['Armature'];b.body=bpy.data.objects['char1'];b.sw=bpy.data.objects['Godwyn_Sword'];b.AW=b.r.matrix_world.copy();b.AI=b.AW.inverted();b.meta=json.loads((OUT/'idle_guard_manifest.json').read_text())
contacts=json.loads((OUT/'idle_guard_contacts.json').read_text());contacts['after']=b.surfaces();contacts['rebind_source']='models/astra_character_v2_prechar2.blend';(OUT/'idle_guard_contacts.json').write_text(json.dumps(contacts,indent=2));b.body.hide_viewport=False
# Avoid duplicate staging objects; stage() recreates them.
for o in list(b.s.objects):
 if o.name=='Astra_Move_Stage':bpy.data.objects.remove(o,do_unlink=True)
b.stage();b.s.frame_set(1);b.update();bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_move_idle_guard_wip.blend'))
b.s.render.resolution_x=b.s.render.resolution_y=512;b.s.render.use_motion_blur=False;b.s.render.filepath=str(OUT/'idle_guard_stable_source_test.png');bpy.ops.render.render(write_still=True)
