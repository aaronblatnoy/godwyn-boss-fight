"""Rebuild twice from immutable input and compare full geometry/skin map content."""
import bpy,sys,runpy,hashlib,array,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
def signature():
 out={}
 for o in bpy.data.objects:
  if o.type!='MESH' or not(o.name=='char1' or o.name.startswith('AstraChar2_')):continue
  a=array.array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',a)
  indices=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',indices)
  out[o.name]={'topology_sha256':hashlib.sha256(indices.tobytes()).hexdigest(),'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'coordinates_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'matrix':list(v for row in o.matrix_world for v in row),'materials':[m.name for m in o.data.materials]}
 out['maps']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('r2_skin_*.png')}
 return out
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_round2_work.blend'));before=signature()
sys.argv=['astra_char2_round2_refine.py','--no-render'];runpy.run_path(str(ROOT/'scripts/astra_char2_round2_refine.py'),run_name='__main__');after=signature()
changed=[k for k in before if before[k]!=after.get(k)]
report={'exact_geometry_and_maps_repeat':not changed,'changed':changed,'signature':after,'method':'Fresh immutable-input rebuild; all char1 and AstraChar2 mesh coordinates, counts, matrices and materials plus PNG map hashes compared.'}
(OUT/'round2_idempotence.json').write_text(json.dumps(report,indent=2));assert not changed,changed
print('IDEMPOTENCE PASSED',flush=True)
