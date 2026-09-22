"""Read-only in-memory rig/material/topology audit; writes only char2 report files."""
import bpy,bmesh,json,hashlib,struct,math,numpy as np
from pathlib import Path
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
def audit():
 r=json.loads((OUT/'recon.json').read_text());o=bpy.data.objects['char1'];base=bpy.data.meshes['AstraChar2 retained original char1'];mw=o.matrix_world
 orig=next(q for q in r['objects'] if q['name']=='char1');arm=bpy.data.objects['Armature'];rig=next(q for q in r['objects'] if q['name']=='Armature')
 assert [m.name for m in o.data.materials]==orig['materials']
 assert [g.name for g in o.vertex_groups]==[g['name'] for g in orig['vertex_groups']]
 assert [(b.name,b.parent.name if b.parent else None) for b in arm.data.bones]==[(b['name'],b['parent']) for b in rig['bones']]
 for b,old in zip(arm.data.bones,rig['bones']):
  assert max(abs(a-v) for a,v in zip(b.head_local,old['head']))<1e-6
  assert max(abs(a-v) for a,v in zip(b.tail_local,old['tail']))<1e-6
 assert not bpy.data.actions[:]
 assert all(not ob.animation_data or not ob.animation_data.action for ob in bpy.data.objects)
 assert all(max(abs(b.matrix_basis[i][j]-(1 if i==j else 0)) for i in range(4) for j in range(4))<1e-6 for b in arm.pose.bones)
 from mathutils.kdtree import KDTree
 tree=KDTree(len(o.data.vertices))
 for v in o.data.vertices:tree.insert(v.co,v.index)
 tree.balance()
 outside_error=max(tree.find(v.co)[2] for v in base.vertices if v.co.z*.01<=2.775)
 # Subdivision does not move original nonfacial vertices or discard skinning.
 assert outside_error<1e-5,(outside_error,'Body vertex coordinates changed')
 missing=[ob.name for ob in bpy.data.objects if ob.name.startswith('AstraChar2_') and ob.type=='MESH' and (not ob.vertex_groups.get('Head') or not any(m.type=='ARMATURE' and m.object==arm for m in ob.modifiers))]
 assert not missing,missing
 bm=bmesh.new();bm.from_mesh(base)
 fs=[f for f in bm.faces if f.material_index==2 and (mw@f.calc_center_median()).z>2.78];es={e for f in fs for e in f.edges};lengths=np.array([(mw@e.verts[0].co-mw@e.verts[1].co).length for e in es])
 report={'original_face_skin_triangles_above_2_78':len(fs),'original_face_edge_median_m':float(np.median(lengths)),'original_face_edge_p95_m':float(np.quantile(lengths,.95)),'original_topology':'Irregular triangulated combined body/head mesh, not facial animation edge loops. Local subdivision needed for anatomical detail; whole-character remesh would risk UVs and skinning.','original_head_boundary_edges':sum(not e.is_manifold for e in es),'new_char1_vertices':len(o.data.vertices),'new_char1_faces':len(o.data.polygons),'added_uv': 'AstraChar2FaceUV, planar front face atlas; original UV retained/interpolated','original_material_slots_preserved':True,'original_object_names_preserved':all(x['name'] in bpy.data.objects for x in r['objects']),'armature_bones_rest_positions_preserved':True,'original_vertex_group_names_preserved':True,'body_original_vertex_max_change_local':outside_error,'actions':len(bpy.data.actions),'all_bone_basis_identity':True,'new_meshes_head_weighted':True,'render':{'engine':'Cycles','device':'local METAL Apple M1 Pro; no network','samples':32,'view_transform':'AgX','exposure':-.35},'portable_limit':'GLB carries skin albedo/normal/roughness/emission and eye transmission; Cycles random-walk subsurface has no exact core glTF equivalent.'}
 bm.free();(OUT/'validation.json').write_text(json.dumps(report,indent=2));r['facial_density_assessment']={k:v for k,v in report.items() if k.startswith('original_face') or k=='original_topology'};(OUT/'recon.json').write_text(json.dumps(r,indent=2))
 with (OUT/'recon.log').open('a') as f:f.write('\nFACE DENSITY ASSESSMENT\n'+json.dumps(r['facial_density_assessment'],indent=2)+'\n')
 print('VALIDATED',json.dumps(report),flush=True);return report
