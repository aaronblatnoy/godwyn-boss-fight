import bpy,sys,json,shutil,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
for ext in ['blend','glb']:
 p=R/f'models/astra_character_v2_preround5.{ext}'
 if not p.exists():shutil.copy2(R/f'models/astra_character_v2.{ext}',p)
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_preround5.blend'));a=bpy.data.objects['Armature'];c=bpy.data.objects['char1'];r={'bones':{b.name:{'head':list(a.matrix_world@b.head_local),'tail':list(a.matrix_world@b.tail_local)} for b in a.data.bones if b.name in ['Head','Neck','Spine','Spine01','Spine02','LeftArm','RightArm','LeftShoulder','RightShoulder']},'slots':[m.name for m in c.data.materials],'modifiers':[(m.name,m.type) for m in c.modifiers],'regions':{}}
for lo,hi in [(2.0,2.2),(2.2,2.4),(2.4,2.6),(2.6,2.78),(2.78,3.3)]:
 for slot in range(5):
  ids={i for f in c.data.polygons if f.material_index==slot for i in f.vertices if lo<c.data.vertices[i].co.z*.01<hi}
  if ids:
   p=np.array([c.matrix_world@c.data.vertices[i].co for i in ids]);r['regions'][f'{lo}-{hi} slot{slot}']={'n':len(ids),'min':p.min(0).tolist(),'max':p.max(0).tolist()}
(O/'r5_recon.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
