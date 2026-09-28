"""Publish only the audited, visually reviewed V4 files; no Blender execution."""
from pathlib import Path
import json,hashlib,shutil,os,datetime
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';O=R/'renders/astra/v4p'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
for name in ['Combat_Stance_audit','sword_slash_r_audit','roundtrip']:
 assert json.loads((O/(name+'.json')).read_text())['mechanical_pass'],name
assert json.loads((O/'finalcheck.json').read_text())['all_sources_and_body_geometry_unchanged']
assert json.loads((O/'inspection.json').read_text())['final_visual_review_complete']
assert sha(O/'candidate.glb')==json.loads((O/'roundtrip.json').read_text())['export_sha256']
for rel,old in json.loads((O/'protected.json').read_text()).items():
 p=R/rel;assert p.stat().st_size==old['size'] and p.stat().st_mtime_ns==old['mtime_ns'] and sha(p)==old['sha256'],rel
for clip,count in [('Combat_Stance',51),('sword_slash_r',46)]:
 assert len(list((O/'film'/(clip+'_frames')).glob('*.png')))==count
 assert int(json.loads((O/'film'/(clip+'_ffprobe.json')).read_text())['streams'][0]['nb_read_frames'])==count
assert len(list((O/'final').glob('*.png')))==14
files={}
for srcname,dstname in [('candidate_export.blend','astra_character_v4.blend'),('candidate.glb','astra_character_v4.glb')]:
 src=O/srcname;dst=R/'models'/dstname;digest=sha(src)
 if dst.exists():assert sha(dst)==digest,'Refusing to overwrite a different published V4'
 else:
  temp=dst.with_suffix(dst.suffix+'.v4p-publishing');shutil.copyfile(src,temp);assert sha(temp)==digest;os.replace(temp,dst)
 files[str(dst.relative_to(R))]={'size':dst.stat().st_size,'sha256':sha(dst),'source':str(src.relative_to(R))}
rep={'published_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':'black-sky','files':files,'status':'Published with documented visual limitations; numeric gates passed'}
(O/'publication.json').write_text(json.dumps(rep,indent=2));print('V4P_PUBLISHED',json.dumps(rep),flush=True)
