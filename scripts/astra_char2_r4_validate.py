"""Compare original object/slot/rig and nonhair geometry invariants."""
import bpy,sys,json,hashlib,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
def digest(a):return hashlib.sha256(a).hexdigest()
def mesh(o,skip=False):
 d=o.data;a=np.empty(len(d.vertices)*3,np.float32);d.vertices.foreach_get('co',a)
 fs=[p for p in d.polygons if not(skip and (p.material_index==3 or (p.material_index==4 and min(d.vertices[i].co.z for i in p.vertices)>290)))]
 topology=digest(np.array([i for p in fs for i in [len(p.vertices),p.material_index,*p.vertices]],dtype=np.int32).tobytes())
 uv={}
 for layer in d.uv_layers:
  uv[layer.name]=digest(np.array([tuple(layer.data[i].uv) for p in fs for i in p.loop_indices],dtype=np.float32).tobytes())
 return {'vertices':len(d.vertices),'coordinates':digest(a.tobytes()),'faces':len(fs),'topology':topology,'uv':uv}
def snapshot(path,before):
 bpy.ops.wm.open_mainfile(filepath=str(path));r={'objects':{},'bones':{},'meshes':{}}
 for o in bpy.data.objects:
  r['objects'][o.name]={'type':o.type,'slots':[m.name if m else None for m in o.data.materials] if hasattr(o.data,'materials') else []}
  if o.type=='MESH' and not o.name.startswith(('AstraChar2_R2_Hair','AstraChar2_R3_Flow','AstraChar2_R3_Plait','AstraChar2_R4_')):r['meshes'][o.name]=mesh(o, before and o.name=='char1')
 arm=bpy.data.objects['Armature']
 for b in arm.data.bones:r['bones'][b.name]={'parent':b.parent.name if b.parent else None,'matrix':np.array(b.matrix_local).tolist(),'head':list(b.head_local),'length':b.length}
 r['actions']=len(bpy.data.actions);r['neutral']=all(np.allclose(np.array(b.matrix_basis),np.eye(4),atol=1e-6) for b in arm.pose.bones)
 return r
before=snapshot(R/'models/astra_character_v2_preround4.blend',True);after=snapshot(R/'models/astra_character_v2.blend',False)
results={'missing_original_objects':sorted(set(before['objects'])-set(after['objects'])),'changed_original_types_or_slots':[k for k,v in before['objects'].items() if after['objects'].get(k)!=v],'changed_nonhair_geometry':[k for k,v in before['meshes'].items() if after['meshes'].get(k)!=v],'bone_names_stable':set(before['bones'])==set(after['bones']),'bone_parents_stable':all(after['bones'][k]['parent']==v['parent'] for k,v in before['bones'].items()),'max_rest_matrix_difference':max(float(np.abs(np.array(v['matrix'])-np.array(after['bones'][k]['matrix'])).max()) for k,v in before['bones'].items()),'changed_bone_lengths':[k for k,v in before['bones'].items() if abs(v['length']-after['bones'][k]['length'])>1e-4],'bones':len(after['bones']),'actions':after['actions'],'neutral':after['neutral'],'details':{'before_nonhair':before['meshes'],'after_nonhair':after['meshes']}}
(O/'r4_preservation_validation.json').write_text(json.dumps(results,indent=2));print(json.dumps({k:v for k,v in results.items() if k!='details'}),flush=True)
assert not results['missing_original_objects'] and not results['changed_original_types_or_slots'] and not results['changed_nonhair_geometry']
assert results['bones']==121 and results['bone_names_stable'] and results['bone_parents_stable'] and results['actions']==0 and results['neutral']
assert all(k.startswith('phys_hair') for k in results['changed_bone_lengths'])
