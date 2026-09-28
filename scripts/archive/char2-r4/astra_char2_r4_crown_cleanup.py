"""Idempotent final removal of misclassified old-hair fragments above the head."""
import bpy,bmesh,sys,json
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2.blend'));o=bpy.data.objects['char1'];bm=bmesh.new();bm.from_mesh(o.data)
faces=[f for f in bm.faces if f.material_index==4 and min(v.co.z for v in f.verts)>290];count=len(faces)
bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY');bm.to_mesh(o.data);bm.free();o.data.update()
r=json.loads((O/'r4_groom.json').read_text());r['removed_misclassified_crown_fragments']=r.get('removed_misclassified_crown_fragments',0)+count;(O/'r4_groom.json').write_text(json.dumps(r,indent=2))
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_v2.blend'));print('REMOVED CROWN FRAGMENTS',count,flush=True)
