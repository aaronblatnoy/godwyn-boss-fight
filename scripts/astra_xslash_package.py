"""Tile evaluation frames and encode H.264 with the preinstalled ffmpeg."""
import argparse, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--round',default='final');p.add_argument('--full',action='store_true');a=p.parse_args();out=ROOT/'renders/astra'/a.round
for v in ['front','three_quarter']:
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','1','-i',str(out/f'contact_{v}'/'%03d.png'),'-vf','tile=5x5:nb_frames=21:padding=4:margin=8:color=0x19202b','-frames:v','1',str(out/f'contact_sheet_{v}.png')],check=True)
if a.full:
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','30','-start_number','1','-i',str(out/'video_frames'/'%03d.png'),'-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',str(ROOT/'renders/astra/godwyn_xslash_astra.mp4')],check=True)

 # Decode the deliverable itself into four sheets covering all 61 video frames.
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(ROOT/'renders/astra/godwyn_xslash_astra.mp4'),'-vf','scale=320:320,tile=4x4:nb_frames=16:padding=4:margin=8:color=0x19202b','-fps_mode','vfr',str(out/'decoded_sheet_%02d.png')],check=True)
