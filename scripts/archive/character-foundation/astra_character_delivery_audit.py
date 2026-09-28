import bpy,sys,json,struct,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
pose=measure_pose();(OUT/'weights_delivered.json').write_text(json.dumps(pose,indent=2));assert pose['spike_edges']==0
for name in VIEWS:
 for stage in ['before','after']:
  p=OUT/f'{stage}_{name}.png';data=p.read_bytes();assert struct.unpack_from('>II',data,16)==(960,960)
for p in [ROOT/'models/astra_character_v2.blend',ROOT/'models/astra_character_v2.glb']:assert p.stat().st_size>1000000
ex=json.loads((OUT/'export_verification.json').read_text());assert len(ex['images'])==9;assert len(json.loads((OUT/'roundtrip_verification.json').read_text())['images'])>=9
assert hashlib.sha256((ROOT/'models/godwyn_game.glb').read_bytes()).hexdigest()==ex['source_sha256_unchanged']
audit={'required_comparison_stills':16,'resolution':[960,960],'embedded_images':9,'source_unchanged':True,'final_spike_edges':pose['spike_edges'],'final_longest_edge_m':pose['max_edge'],'final_stretch_p99':pose['stretch_p99'],'blend_bytes':(ROOT/'models/astra_character_v2.blend').stat().st_size,'glb_bytes':(ROOT/'models/astra_character_v2.glb').stat().st_size}
(OUT/'delivery_audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
