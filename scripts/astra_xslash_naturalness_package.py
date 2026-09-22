"""Package the fixed action renders; no scene or asset edits."""
import json,shutil,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/v2_final_on_char'
FINAL=ROOT/'renders/astra/godwyn_xslash_v2_final.mp4'
EVAL=[1,13,27,31,34,36,38,39,40,43,46,53,54,57,61,79,80,84,86,90]
FIXES={
 '01_arm_pops':[36,38,39,53,54],
 '02_sword_wrist':[1,13,80,90],
 '03_elbow_fold':[38,39,40],
 '04_off_arm_kink':[36,40,43,46],
 '05_shoulder_timing':[34,36,38,40],
 '06_off_hand_rigidity':[27,43,57,90],
 '07_counterlean':[13,27,31],
 '08_settle_bob':[80,84,86,90],
 '09_foot_contact':[27,46,57,90],
 '10_cloth_lag':[38,43,61,90],
 '11_hem_floor':[39,46,57,90],
}
def ff(args):subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','error','-y']+args,check=True)
def sheet(files,dest,cols):
    temp=Path('/tmp')/('astra_xslash_naturalness_'+dest.stem);temp.mkdir(exist_ok=True)
    for i,p in enumerate(files):shutil.copy2(p,temp/f'{i:03d}.png')
    rows=(len(files)+cols-1)//cols
    ff(['-framerate','1','-i',str(temp/'%03d.png'),'-vf',f'scale=320:320,tile={cols}x{rows}:nb_frames={len(files)}:padding=4:margin=8:color=0x171b22','-frames:v','1',str(dest)])
frames=[OUT/'video_frames'/f'{f:03d}.png' for f in range(1,91)]
assert all(p.exists() for p in frames)
# The recorded render log must attest to all 90 newly rendered frames.
log=(ROOT/'renders/astra/naturalness_render_final.log').read_text()
assert 'NATURALNESS RENDER COMPLETE after' in log
assert sum('NATURALNESS FRAME after ' in x for x in log.splitlines())==90
fixed=OUT/'naturalness_after';fixed.mkdir(exist_ok=True)
for f in EVAL:shutil.copy2(OUT/'video_frames'/f'{f:03d}.png',fixed/f'{f:03d}.png')
for label,folder in [('before',OUT/'naturalness_before'),('after',fixed)]:
    sheet([folder/f'{f:03d}.png' for f in EVAL],OUT/f'naturalness_{label}_evaluation_sheet.png',5)
    for fix,fs in FIXES.items():sheet([folder/f'{f:03d}.png' for f in fs],OUT/f'naturalness_{fix}_{label}.png',len(fs))
ff(['-framerate','30','-start_number','1','-i',str(OUT/'video_frames/%03d.png'),'-frames:v','90','-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',str(FINAL)])
ff(['-v','error','-xerror','-i',str(FINAL),'-f','null','-'])
ff(['-i',str(FINAL),'-vf','scale=320:320,tile=5x3:nb_frames=15:padding=4:margin=8:color=0x171b22','-fps_mode','vfr',str(OUT/'naturalness_decoded_%02d.png')])
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(FINAL)],text=True))
st=next(x for x in probe['streams'] if x['codec_type']=='video')
assert int(st['nb_read_frames'])==90 and st['r_frame_rate']=='30/1' and st['width']==st['height']==640
meta={'final_mp4':str(FINAL.relative_to(ROOT)),'sha256':hashlib.sha256(FINAL.read_bytes()).hexdigest(),'frames':90,'fps':30,'duration':float(probe['format']['duration']),'resolution':[640,640],'codec':st['codec_name'],'pixel_format':st['pix_fmt'],'full_decode_error_free':True,'camera':'unchanged saved front camera; prior MP4 temporary three-quarter override intentionally not reapplied under strict scope','evaluation_frames':EVAL,'evidence_order':FIXES,'decoded_sheets':[f'naturalness_decoded_{i:02d}.png' for i in range(1,7)]}
(OUT/'naturalness_video_verification.json').write_text(json.dumps(meta,indent=2))
manifest=json.loads((OUT/'manifest.json').read_text());manifest['naturalness_revision']=meta
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('NATURALNESS PACKAGE',json.dumps(meta),flush=True)
