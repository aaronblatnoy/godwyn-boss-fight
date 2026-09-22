"""Final offline delivery gate. Does not modify inputs or animation assets."""
import json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'
names=['idle_guard','walk_stalk','lunge_thrust','rising_spin']
def digest(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
source=digest(ROOT/'models/astra_character_v2_prechar2.blend');assert digest(ROOT/'models/astra_move_character_base.blend')==source
result={'stable_input':'models/astra_character_v2_prechar2.blend','frozen_snapshot':'models/astra_move_character_base.blend','source_sha256':source,'moves':{}}
for name in names:
 manifest=json.loads((OUT/f'{name}_manifest.json').read_text());metrics=json.loads((OUT/f'{name}_metrics.json').read_text());grip=json.loads((OUT/f'{name}_grip_metrics.json').read_text())
 assert manifest['source_sha256']==source==metrics['source_sha256']
 assert metrics['bone_count']==121 and grip['quarter_samples']==manifest['samples_end']*4-3
 assert grip['max_hand_local_hilt_drift_m']<.001 and grip['max_evaluated_tip_error_m']<.001 and grip['max_closed_finger_hand_local_drift_m']<.001
 if name=='rising_spin':assert grip['max_edge_vs_cut_deg']<25 and metrics['peak_hips_yaw_deg_s']<360.1
 required=[ROOT/f'scripts/astra_move_{name}_build.py',ROOT/f'models/astra_move_{name}_wip.blend',OUT/f'{name}.mp4',OUT/f'{name}_contact_sheet.png']
 for p in required:assert p.is_file() and p.stat().st_size>100
 for f in grip['grip_frames']:assert (OUT/name/'grip'/f'{f:03d}.png').is_file()
 video=json.loads(subprocess.check_output([(__import__('shutil').which('ffprobe') or '/opt/homebrew/bin/ffprobe'),'-v','error','-count_frames','-show_streams','-of','json',str(OUT/f'{name}.mp4')],text=True));v=video['streams'][0]
 assert v['codec_name']=='h264' and v['pix_fmt']=='yuv420p' and v['width']==v['height']==768 and v['r_frame_rate']=='30/1' and int(v['nb_read_frames'])==manifest['frames']
 assert f'## {name} — completed' in (OUT/'physics_audit.md').read_text()
 result['moves'][name]={'frames':manifest['frames'],'deliverables':[str(p.relative_to(ROOT)) for p in required],'sha256':{str(p.relative_to(ROOT)):digest(p) for p in required},'grip_closeups':[str((OUT/name/'grip'/f'{f:03d}.png').relative_to(ROOT)) for f in grip['grip_frames']]}
for p in (ROOT/'scripts').glob('astra_move_*.py'):compile(p.read_text(),str(p),'exec')
result['audit']='renders/astra/moves/physics_audit.md';(OUT/'delivery_verification.json').write_text(json.dumps(result,indent=2));print('DELIVERY VERIFIED',', '.join(names))
