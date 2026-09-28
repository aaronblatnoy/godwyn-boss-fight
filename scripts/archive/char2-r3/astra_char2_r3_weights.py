import bpy,json,sys,collections,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));o=bpy.data.objects['char1'];r={}
for mat in [0,1,2,3,4]:
 ids={vi for f in o.data.polygons if f.material_index==mat for vi in f.vertices};counts=collections.Counter()
 for i in ids:
  v=o.data.vertices[i];p=o.matrix_world@v.co
  if 2.2<p.z<2.75 and abs(p.x)<.42:
   for g in v.groups:counts[o.vertex_groups[g.group].name]+=g.weight
 r[mat]=counts.most_common(18)
(OUT/'r3_weight_audit.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
