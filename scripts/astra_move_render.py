"""EEVEE/Metal renders; preview or full native frame sequence, no network."""
import sys,json
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'
args=sys.argv[sys.argv.index('--')+1:];name=args[0];preview='preview' in args
m=json.loads((OUT/f'{name}_manifest.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'models/astra_move_{name}_wip.blend'))
s=bpy.context.scene
s.render.engine='BLENDER_EEVEE' ;s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100
s.render.resolution_x=s.render.resolution_y=384 if preview else 768;s.eevee.taa_render_samples=16 if preview else 32;s.render.use_motion_blur=(not preview and bool(m['active']))
if 'save-compat' in args:
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'models/astra_move_{name}_wip.blend'))
folder=OUT/name/('preview' if preview else 'frames');folder.mkdir(parents=True,exist_ok=True)
frames=m['contact_frames'] if preview else list(range(1,m['frames']+1))
for f in frames:
    s.frame_set(f);s.render.filepath=str(folder/f'{f:03d}.png');bpy.ops.render.render(write_still=True);print('MOVE RENDER',name,f,flush=True)
