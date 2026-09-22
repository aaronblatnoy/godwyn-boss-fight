"""Bank the clean R5 armor on the shipped character, without changing the head or groom."""
import sys,bpy,bmesh,json,shutil,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose
from astra_char2_r5_armor import build
from astra_char2_r5_fit import fit
from astra_char2_r5_geometry import mesh,bind,head_weights
import math
for ext in ['blend','glb']:
 p=R/f'models/astra_character_v2_preround6.{ext}'
 if not p.exists():shutil.copy2(R/f'models/astra_character_v2.{ext}',p)
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2_preround6.blend'));reset_pose();arm=bpy.data.objects['Armature'];char=bpy.data.objects['char1'];slots=list(char.data.materials)
rest={b.name:np.array(b.matrix_local) for b in arm.data.bones};original={o.name:[m.name for m in o.data.materials] for o in bpy.data.objects if hasattr(o.data,'materials')}
cloth=[tuple(p.vertices) for p in char.data.polygons if p.material_index in(1,4)];clothids=sorted({i for p in cloth for i in p});raw=np.array([char.data.vertices[i].co[:] for i in clothids])
# Replace the same R5 upper armor surfaces. Cloth panels and head/groom remain intact.
bm=bmesh.new();bm.from_mesh(char.data);old=[];zero=0;neck_removed=0
for f in bm.faces:
 c=f.calc_center_median()*.01
 if f.material_index in(0,3) and ((c.z>2.18 and abs(c.x)<.62 and c.z<2.82) or (1.98<c.z<2.82 and abs(c.x)<.30)):
  old.append(f);zero+=int(f.calc_area()<1e-8)
 elif f.material_index==2 and 2.60<c.z<2.86 and (c.z<2.79 or abs(c.x)>.14):old.append(f);neck_removed+=1
bmesh.ops.delete(bm,geom=old,context='FACES_ONLY');bm.to_mesh(char.data);bm.free()
# Old chased ornaments no longer lie on the replaced plates.
retired=[]
for ob in bpy.data.objects:
 if ob.name=='AstraChar2_R3_ChasedLaurel':ob.data.clear_geometry();retired.append(ob.name)
build(slots)
v=[];fs=[];N=128;NZ=48
for j,z in enumerate(np.linspace(2.61,2.815,NZ)):
 rx=float(np.interp(z,[2.61,2.72,2.79,2.815],[.079,.066,.068,.077]));ry=float(np.interp(z,[2.61,2.72,2.79,2.815],[.08,.09,.105,.12]));cy=-.18-.025*(z-2.61)/.205
 for i in range(N):
  a=i*math.tau/N;v.append((rx*math.sin(a),cy-ry*math.cos(a),z))
for j in range(NZ-1):
 for i in range(N):fs.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
fs.extend([tuple(reversed(range(N))),tuple((NZ-1)*N+i for i in range(N))]);neck=mesh('AstraChar2_R6_NeckGraft',v,fs,slots,2);bind(neck,head_weights)
fit_count=fit()
# Round 6 protects the ruled-correct draped garment outside the collar contact band.
vg=char.vertex_groups['AstraChar2_R5_CollarFit'];fit_count=0
for i in clothids:
 p=char.matrix_world@char.data.vertices[i].co
 w=max(0,min(1,(p.z-2.48)/.12)) if abs(p.x)<.62 else 0
 if w:vg.add([i],w,'REPLACE');fit_count+=1
 else:vg.remove([i])
# Preserve the R5 fit as a local collar/upper-armor contact correction; no cloth faces/rest vertices edited.
gold=bpy.data.materials.new('AstraChar2 R6 clean aged-brass plates');gold.use_nodes=True;bs=gold.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.48,.34,.14,1);bs.inputs['Metallic'].default_value=1;bs.inputs['Roughness'].default_value=.36
counts={'removed_inherited_armor_faces':len(old)-neck_removed,'removed_fractured_neck_faces':neck_removed,'removed_zero_area_faces':zero,'retired_ornament_objects':retired,'welded_vertices':0,'closed_boundary_loops':0,'reoriented_faces':0,'new_plate_boundary_edges':0,'new_plate_nonmanifold_edges':0}
for ob in bpy.data.objects:
 if not ob.name.startswith('AstraChar2_R5_') or ob.type!='MESH' or 'Envelope' in ob.name:continue
 ob.data.materials[0]=gold
 bm=bmesh.new();bm.from_mesh(ob.data);before=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);counts['welded_vertices']+=before-len(bm.verts)
 oldnorm={f:f.normal.copy() for f in bm.faces};bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));counts['reoriented_faces']+=sum(f.normal.dot(n)<0 for f,n in oldnorm.items())
 boundary=[e for e in bm.edges if e.is_boundary]
 if boundary:
  filled=bmesh.ops.holes_fill(bm,edges=boundary,sides=0);counts['closed_boundary_loops']+=len(filled['faces'])
 counts['new_plate_boundary_edges']+=sum(e.is_boundary for e in bm.edges);counts['new_plate_nonmanifold_edges']+=sum(len(e.link_faces)>2 for e in bm.edges)
 bm.to_mesh(ob.data);bm.free()
 # Give the new plates usable UVs without changing existing atlases/material slots.
 uv=ob.data.uv_layers.get('UVMap') or ob.data.uv_layers.new(name='UVMap')
 for poly in ob.data.polygons:
  for li in poly.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(.50+.13*p.x,.48+.1*(p.z-2.45))
reset_pose();bpy.context.view_layer.update();counts['bones']=len(arm.data.bones);counts['actions']=len(bpy.data.actions);counts['rest_matrix_error']=max(float(abs(np.array(b.matrix_local)-rest[b.name]).max()) for b in arm.data.bones)
assert counts['bones']==121 and counts['actions']==0 and counts['rest_matrix_error']==0
assert all([m.name for m in bpy.data.objects[n].data.materials]==s for n,s in original.items())
assert cloth==[tuple(p.vertices) for p in char.data.polygons if p.material_index in(1,4)] and np.array_equal(raw,np.array([char.data.vertices[i].co[:] for i in clothids]))
counts['cloth_topology_rest_vertices_unchanged']=True;counts['local_armor_contact_fit_vertices']=fit_count
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(R/'models/astra_character_r6_collar.blend'));(O/'r6_collar_counts.json').write_text(json.dumps(counts,indent=2));print(json.dumps(counts),flush=True)
