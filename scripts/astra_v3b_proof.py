import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3_build as b
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate_final.blend'));ob=bpy.data.objects['char1'];ids=np.array([x.value for x in ob.data.attributes['astra_v3b_raw_face'].data]);p=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);f=np.array([list(x.vertices) for x in ob.data.polygons]);uv=np.array([list(x.uv) for x in ob.data.uv_layers.active.data]).reshape(-1,3,2);geo=p[f];names=[g.name for g in ob.vertex_groups];w=np.zeros((len(p),len(names)))
for v in ob.data.vertices:
 for g in v.groups:w[v.index,g.group]=g.weight
cornw=w[f];rig,raw=b.import_rigged(R/'models/meshy_body_godA_fists_rigged.glb');bpy.context.view_layer.update();rp=np.array([(raw.matrix_world@v.co)[:] for v in raw.data.vertices]);rf=np.array([list(x.vertices) for x in raw.data.polygons]);ruv=np.array([list(x.uv) for x in raw.data.uv_layers.active.data]).reshape(-1,3,2);rw=np.zeros((len(rp),len(names)))
for v in raw.data.vertices:
 for g in v.groups:rw[v.index,names.index(raw.vertex_groups[g.group].name)]=g.weight
rep={'source_faces':len(rf),'candidate_faces':len(f),'retained_face_ids_unique':len(set(ids))==len(ids),'all_retained_ordered_triangle_coordinates_exact':bool(np.array_equal(geo,rp[rf[ids]])),'all_retained_face_corner_UVs_exact':bool(np.array_equal(uv,ruv[ids])),'weight_changed_face_count':int(np.any(np.abs(cornw-rw[rf[ids]])>1e-7,axis=(1,2)).sum()),'weight_change_note':'Deliberate robe skin-weight smoothing; rest geometry and UVs unchanged. Region counts and explicit removal predicate are in build_r5.json.'}
assert rep['all_retained_ordered_triangle_coordinates_exact'];assert rep['all_retained_face_corner_UVs_exact'];(O/'preservation_final.json').write_text(json.dumps(rep,indent=2));print('V3B_FINAL_PROOF',json.dumps(rep),flush=True)
