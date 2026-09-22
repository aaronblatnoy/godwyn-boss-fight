"""Encode all 90 new EEVEE frames and retain focused before/after evidence."""
import json,shutil,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/v2_final_on_char';FINAL=ROOT/'renders/astra/godwyn_xslash_v2_final.mp4'
frames=list(range(1,91));focus=[36,37,38,39,40,41,44,45,46,47,48,49,50,51,52,53]
def ff(args):subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','error','-y']+args,check=True)
def sheet(files,dest,cols,size=320):
 temp=Path('/tmp')/('astra_xslash_'+dest.stem);temp.mkdir(exist_ok=True)
 for i,p in enumerate(files):shutil.copy2(p,temp/f'{i:03d}.png')
 rows=(len(files)+cols-1)//cols
 ff(['-framerate','1','-i',str(temp/'%03d.png'),'-vf',f'scale={size}:{size},tile={cols}x{rows}:nb_frames={len(files)}:padding=4:margin=8:color=0x171b22','-frames:v','1',str(dest)])
log=(ROOT/'renders/astra/naturalness_render_armfix.log').read_text()
assert 'NATURALNESS RENDER COMPLETE after' in log
assert sum('NATURALNESS FRAME after ' in x for x in log.splitlines())==90
assert all((OUT/'video_frames'/f'{f:03d}.png').exists() for f in frames)
after=OUT/'armfix_after';after.mkdir(exist_ok=True)
for f in focus:shutil.copy2(OUT/'video_frames'/f'{f:03d}.png',after/f'{f:03d}.png')
fixes={'wrist':[44,45,46,47,48,49,50,51,52,53],'cascade':[36,37,38,39,40,41]}
for name,fs in fixes.items():
 for label in ['before','after']:
  sheet([OUT/f'armfix_{label}'/f'{f:03d}.png' for f in fs],OUT/f'armfix_{name}_{label}.png',5 if name=='wrist' else 3)
 # Paired rows before/after, at the three diagnostic frames, in that order.
 pairfs=[46,47,48] if name=='wrist' else [38,39,40]
 sheet([OUT/f'armfix_{label}'/f'{f:03d}.png' for label in ['before','after'] for f in pairfs],OUT/f'armfix_{name}_comparison.png',3,480)
ff(['-framerate','30','-start_number','1','-i',str(OUT/'video_frames/%03d.png'),'-frames:v','90','-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',str(FINAL)])
ff(['-v','error','-xerror','-i',str(FINAL),'-f','null','-'])
ff(['-i',str(FINAL),'-vf','scale=320:320,tile=5x3:nb_frames=15:padding=4:margin=8:color=0x171b22','-fps_mode','vfr',str(OUT/'armfix_decoded_%02d.png')])
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(FINAL)],text=True));st=next(x for x in probe['streams'] if x['codec_type']=='video')
assert int(st['nb_read_frames'])==90 and st['r_frame_rate']=='30/1' and st['width']==st['height']==640
meta={'final_mp4':str(FINAL.relative_to(ROOT)),'sha256':hashlib.sha256(FINAL.read_bytes()).hexdigest(),'scene_sha256':hashlib.sha256((ROOT/'models/astra_xslash_v2_final_wip.blend').read_bytes()).hexdigest(),'frames':90,'fps':30,'duration':float(probe['format']['duration']),'resolution':[640,640],'codec':st['codec_name'],'pixel_format':st['pix_fmt'],'full_decode_error_free':True,'camera':'unchanged saved camera','engine':'BLENDER_EEVEE','evaluation_frames':focus,'evidence_frame_order':fixes,'comparison_order':'Top row before; bottom row after. Wrist: F46/F47/F48; cascade: F38/F39/F40.','decoded_sheets':[f'armfix_decoded_{i:02d}.png' for i in range(1,7)]}
(OUT/'armfix_video_verification.json').write_text(json.dumps(meta,indent=2));manifest=json.loads((OUT/'manifest.json').read_text());manifest['armfix_revision']=meta;(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('ARMFIX PACKAGE',json.dumps(meta),flush=True)
