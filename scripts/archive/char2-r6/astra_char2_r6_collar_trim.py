import sys,bpy,bmesh,json
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r6_collar.blend'));o=bpy.data.objects['char1'];bm=bmesh.new();bm.from_mesh(o.data);bad=[]
for f in bm.faces:
 c=f.calc_center_median()*.01
 if f.material_index==2 and 2.79<=c.z<2.86 and abs(c.x)>.14:bad.append(f)
n=len(bad);bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY');bm.to_mesh(o.data);bm.free();r=json.loads((O/'r6_collar_counts.json').read_text());r['removed_fractured_neck_faces']+=n;r['last_collar_strays_removed']=n
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_r6_collar.blend'));(O/'r6_collar_counts.json').write_text(json.dumps(r,indent=2));print('Removed collar strays',n,flush=True)
