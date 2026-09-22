"""Preserve the authored idle action, rebind to stable prechar2; render one test."""
import sys,json,hashlib,shutil
from pathlib import Path
sys.dont_write_bytecode=True
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_move_common import Builder,ROOT,OUT
path=ROOT/'models/astra_move_idle_guard_wip.blend'
snapshot=Path('/tmp/astra_move_idle_action_source.blend');shutil.copyfile(path,snapshot)
bpy.ops.wm.open_mainfile(filepath=str(snapshot));old=bpy.data.objects['Armature'];action_name=old.animation_data.action.name
oldrest={b.name:[list(x) for x in b.matrix_local] for b in old.data.bones}
def digest(act):
    h=hashlib.sha256();count=0
    for la in act.layers:
        for st in la.strips:
            for bag in st.channelbags:
                for fc in bag.fcurves:
                    h.update(repr((fc.data_path,fc.array_index)).encode())
                    for k in fc.keyframe_points:h.update(repr((tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation)).encode());count+=1
    return [h.hexdigest(),count]
before=digest(old.animation_data.action)
b=Builder('idle_guard',97,True);b.meta=json.loads((OUT/'idle_guard_manifest.json').read_text())
with bpy.data.libraries.load(str(snapshot),link=False) as (src,dst):dst.actions=[action_name]
b.r.animation_data_create();b.r.animation_data.action=dst.actions[0];b.r.animation_data.action_slot=dst.actions[0].slots[0]
err=max(abs(b.r.data.bones[n].matrix_local[i][j]-oldrest[n][i][j]) for n in oldrest for i in range(4) for j in range(4))
print('REST MATRIX ERROR',err,'ACTION',before,digest(b.r.animation_data.action),flush=True)
assert err<.001;assert digest(b.r.animation_data.action)==before
for o,hidden in b.visible:o.hide_viewport=hidden
b.stage();b.s.frame_set(1);b.update();b.s['astra_move']='idle_guard';b.s['source_sha256']=b.sha;b.s['loop_period_frames']=96;b.s['cycle_root_displacement']=[0,0,0]
b.s.render.resolution_x=b.s.render.resolution_y=768;b.s.eevee.taa_render_samples=32;b.s.render.use_motion_blur=False
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
b.meta['source_sha256']=b.sha;b.meta['source']='models/astra_character_v2_prechar2.blend';(OUT/'idle_guard_manifest.json').write_text(json.dumps(b.meta,indent=2))
(OUT/'idle_guard_rebind.json').write_text(json.dumps({'source':b.meta['source'],'sha256':b.sha,'action_before':before,'action_after':digest(b.r.animation_data.action),'max_rest_error':err},indent=2))
b.s.render.resolution_x=b.s.render.resolution_y=512;b.s.eevee.taa_render_samples=24;b.s.render.filepath=str(OUT/'idle_guard_stable_source_test.png');bpy.ops.render.render(write_still=True)
