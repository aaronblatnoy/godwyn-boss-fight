"""Structural replacement from immutable round-5 input. No rig edits, no shader work."""
import bpy,bmesh,sys,json,hashlib,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_head import build as head
from astra_char2_r5_armor import build as armor
from astra_char2_r5_fit import fit
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_preround5.blend'));reset_pose();arm=bpy.data.objects['Armature'];char=bpy.data.objects['char1'];slots=list(char.data.materials)
bones={b.name:np.array(b.matrix_local) for b in arm.data.bones};parents={b.name:b.parent.name if b.parent else None for b in arm.data.bones}
original={o.name:[m.name for m in o.data.materials] for o in bpy.data.objects if hasattr(o.data,'materials')}
protected=[f for f in char.data.polygons if f.material_index==1 or (f.material_index==4 and sum(char.data.vertices[i].co.z for i in f.vertices)/len(f.vertices)<277)]
ids=sorted({i for f in protected for i in f.vertices});raw=np.array([char.data.vertices[i].co[:] for i in ids]);ev=char.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated=np.array([ev.data.vertices[i].co[:] for i in ids]);cloth_indices=[tuple(f.vertices) for f in protected]
# Retain externally referenced objects and their slot lists, with old geometry removed.
retired=[]
for ob in list(bpy.data.objects):
 if ob.name.startswith('AstraChar2_R5_'):bpy.data.objects.remove(ob,do_unlink=True);continue
 if not ob.name.startswith('AstraChar2_'):continue
 if ob.type=='MESH':ob.data.clear_geometry();ob.hide_render=True;retired.append(ob.name)
 elif ob.type=='CURVES':
  old=ob.data;fresh=bpy.data.hair_curves.new(ob.name+' retired empty')
  for m in old.materials:fresh.materials.append(m)
  ob.data=fresh;bpy.data.hair_curves.remove(old);ob.hide_render=True;retired.append(ob.name)
# Old head and upper armor surfaces are removed in full, not repaired.
# FACES_ONLY preserves protected cloth vertex indices and its smoothing edge graph.
bm=bmesh.new();bm.from_mesh(char.data);removed={};faces=[]
for f in bm.faces:
 c=f.calc_center_median()*.01;m=f.material_index;replace=(m==2 and c.z>2.60) or (m in (0,3) and ((c.z>2.18 and abs(c.x)<.62) or (c.z>1.98 and abs(c.x)<.30))) or (m==4 and c.z>2.77)
 if replace:faces.append(f);removed[str(m)]=removed.get(str(m),0)+1
bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY');bm.to_mesh(char.data);bm.free();char.data.update()
head_obj=head(slots);armor(slots)
for ob in bpy.data.objects:
 if ob.name.startswith('AstraChar2_R5_') or ob.name.startswith('AstraChar2_Eyeball_'):ob.hide_render=False;ob.hide_set(False)
fit_vertices=fit()
reset_pose();bpy.context.view_layer.update();ev=char.evaluated_get(bpy.context.evaluated_depsgraph_get());after=np.array([ev.data.vertices[i].co[:] for i in ids]);afterraw=np.array([char.data.vertices[i].co[:] for i in ids])
rest_error=max(float(np.abs(np.array(b.matrix_local)-bones[b.name]).max()) for b in arm.data.bones)
assert rest_error==0 and len(arm.data.bones)==121 and len(bpy.data.actions)==0
assert all([m.name for m in bpy.data.objects[name].data.materials]==names for name,names in original.items())
cloth_polys=[tuple(f.vertices) for f in char.data.polygons if f.material_index==1 or (f.material_index==4 and sum(char.data.vertices[i].co.z for i in f.vertices)/len(f.vertices)<277)]
assert cloth_polys==cloth_indices and np.array_equal(raw,afterraw)
r={'stage':'GEOMETRY_ONLY_CLAY_GATE_PENDING','removed_old_surface_faces_by_slot':removed,'retired_objects':retired,'bones':len(arm.data.bones),'actions':len(bpy.data.actions),'rest_matrix_error':rest_error,'original_names_and_slots_preserved':True,'protected_cloth_vertices':len(ids),'cloth_raw_exact':True,'cloth_evaluated_max_displacement_m':float(np.linalg.norm(after-evaluated,axis=1).max()*.01),'new_head_vertices':len(head_obj.data.vertices),'new_head_faces':len(head_obj.data.polygons),'new_objects':{o.name:{'vertices':len(o.data.vertices),'faces':len(o.data.polygons)} for o in bpy.data.objects if o.name.startswith('AstraChar2_R5_') and o.type=='MESH'}}
r['collar_fit_vertices']=fit_vertices
r['cloth_connectivity_and_rest_vertices_preserved']=True
r['cloth_fit']='Upper cloth constrained inside replacement armor with rest-space Shrinkwrap before Armature; no panel restructuring.'
low=[j for j,i in enumerate(ids) if raw[j,2]<199]
r['lower_cloth_evaluated_max_displacement_m']=float(np.linalg.norm(after[low]-evaluated[low],axis=1).max()*.01)
assert r['lower_cloth_evaluated_max_displacement_m']<1e-6
bpy.context.scene['astra_char2_round5']='Structural candidate. CLAY GATE PENDING. No material work.';bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_r5_clay.blend'));(O/'r5_structure.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
