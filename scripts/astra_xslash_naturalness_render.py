"""Render with the saved scene unchanged; only the output filename is set."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
label=args[0] if args else 'after'
source=ROOT/('models/astra_xslash_v2_final_prefix.blend' if label=='before' else 'models/astra_xslash_v2_final_wip.blend')
bpy.ops.wm.open_mainfile(filepath=str(source))
s=bpy.context.scene
assert s.render.engine=='BLENDER_EEVEE'
assert s.render.image_settings.file_format=='PNG'
assert s.frame_start==1 and s.frame_end==90
out=ROOT/'renders/astra/v2_final_on_char'/('naturalness_before' if label=='before' else 'video_frames')
if len(args)>1 and args[1]=='poses':out=ROOT/'renders/astra/v2_final_on_char/naturalness_after'
out.mkdir(parents=True,exist_ok=True)
frames=[1,13,27,31,34,36,38,39,40,43,46,53,54,57,61,79,80,84,86,90] if label=='before' or (len(args)>1 and args[1]=='poses') else list(range(1,91))
for f in frames:
    s.frame_set(f);s.render.filepath=str(out/f'{f:03d}.png')
    bpy.ops.render.render(write_still=True)
    print('NATURALNESS FRAME',label,f,flush=True)
print('NATURALNESS RENDER COMPLETE',label,flush=True)
