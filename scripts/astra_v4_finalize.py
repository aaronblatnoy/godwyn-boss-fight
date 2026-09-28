from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';O=R/'renders/astra/v4'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
raw=json.loads((O/'raw_probe.json').read_text());hashes={p:sha(R/p) for p in raw['hashes']};old=json.loads((O/'protected_before.json').read_text());changed=[]
for p,d in old.items():
 x=R/p
 if not x.exists() or x.stat().st_size!=d['size'] or x.stat().st_mtime_ns!=d['mtime_ns']:changed.append(p)
rep={'input_hashes_unchanged':hashes==raw['hashes'],'input_hashes_after':hashes,'protected_v3_metadata_changed_since_start':changed,'release_paths_exist':{str(p.relative_to(R)):p.exists() for p in [R/'models/astra_character_v4.blend',R/'models/astra_character_v4.glb']},'publication':'WITHHELD: inferior facial detail/likeness, open sword hand, severe robe deformation.','scope':'Only V4 scripts, V4 evidence and candidates, V4_REPORT.md and codex_v4.log were written by this run.'};(O/'final_verification.json').write_text(json.dumps(rep,indent=2));print(json.dumps(rep,indent=2))
files=[p for p in O.rglob('*') if p.is_file() and p.name!='artifact_hashes.txt'];(O/'artifact_hashes.txt').write_text(''.join(sha(p)+'  '+str(p.relative_to(O))+'\n' for p in sorted(files)))
