import bpy,sys,json,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
def snapshot(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['Armature']
 return {'objects':{o.name:[m.name for m in o.data.materials] if o.type=='MESH' else None for o in bpy.data.objects},'bones':{b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones},'bone_tails':{b.name:list(b.tail_local) for b in rig.data.bones},'vertex_groups':{o.name:[g.name for g in o.vertex_groups] for o in bpy.data.objects if o.type=='MESH'}}
a=snapshot(ROOT/'models/astra_character_v2_preround3.blend');b=snapshot(ROOT/'models/astra_character_v2.blend')
r={'missing_original_objects':sorted(set(a['objects'])-set(b['objects'])),'changed_original_material_slots':[k for k in a['objects'] if a['objects'][k]!=b['objects'].get(k)],'rest_bones_identical':a['bones']==b['bones'] and a['bone_tails']==b['bone_tails'],'changed_original_group_names':[k for k in a['vertex_groups'] if a['vertex_groups'][k]!=b['vertex_groups'].get(k)],'actions':len(bpy.data.actions),'nonidentity_pose_bones':[],'hair_chains':{},'mesh_counts':{}}
rig=bpy.data.objects['Armature']
for p in rig.pose.bones:
 if not np.allclose(np.array(p.matrix_basis),np.eye(4),atol=1e-5):r['nonidentity_pose_bones'].append(p.name)
for bone in rig.data.bones:
 if 'phys_hair' in bone.name:r['hair_chains'][bone.name]={'world_length_m':float((rig.matrix_world@bone.tail_local-rig.matrix_world@bone.head_local).length),'parent':bone.parent.name if bone.parent else None}
for o in bpy.data.objects:
 if o.type=='MESH' and (o.name.startswith('AstraChar2_R3_') or o.name=='char1'):
  r['mesh_counts'][o.name]={'vertices':len(o.data.vertices),'faces':len(o.data.polygons)}
assert not r['missing_original_objects'] and not r['changed_original_material_slots'] and r['rest_bones_identical'] and not r['changed_original_group_names'] and not r['actions'] and not r['nonidentity_pose_bones']
(OUT/'r3_preservation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
