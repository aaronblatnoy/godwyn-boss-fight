"""Build visual review sheets; encode and decode the exact deliverable."""
import argparse,subprocess,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--round',default='v2_r1');p.add_argument('--full',action='store_true');a=p.parse_args();out=ROOT/'renders/astra'/a.round
m=json.loads((out/'manifest.json').read_text())
def run(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y']+args,check=True)
for v in ['front','three_quarter']:
 for kind,frames in [('cuts',m['cut_frames']),('flow',m['flow_frames']),('poses',m['poses'])]:
  td=Path('/tmp')/f'astra_v2_{a.round}_{v}_{kind}';td.mkdir(exist_ok=True)
  for i,f in enumerate(frames):
   source=out/f'{v}_pose_f{f:02d}.png' if kind=='poses' else out/f'contact_{v}'/f'{f:03d}.png'
   shutil.copy2(source,td/f'{i:03d}.png')
  cols=4 if kind=='poses' else 7;rows=2
  run(['-framerate','1','-i',str(td/'%03d.png'),'-vf',f'tile={cols}x{rows}:nb_frames={len(frames)}:padding=4:margin=8:color=0x171b22','-frames:v','1',str(out/f'{kind}_sheet_{v}.png')])
if a.full:
 final=ROOT/'renders/astra/godwyn_xslash_v2.mp4'
 run(['-framerate','30','-start_number','1','-i',str(out/'video_frames'/'%03d.png'),'-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',str(final)])
 run(['-i',str(final),'-vf','scale=320:320,tile=5x3:nb_frames=15:padding=4:margin=8:color=0x171b22','-fps_mode','vfr',str(out/'decoded_sheet_%02d.png')])
 result=subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)],text=True)
 (out/'video_verification.json').write_text(result)
