import bpy,bmesh,sys,json,numpy as np
from pathlib import Path
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3m_retarget_world as rt
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate_r7.blend'));head=bpy.data.objects['AstraChar2_Meshy_HeadHair'];comps=rt.welded_components(head);hair=head.data.color_attributes['meshy_hair_mask'];hairids=set()
for f in head.data.polygons:
 if np.mean([hair.data[i].color[0] for i in f.loop_indices])>=.5:hairids.update(f.vertices)
rows=[];doomed=set()
for c in comps:
 if not(c&hairids):continue
 unique={tuple(round(float(v),4) for v in head.data.vertices[i].co) for i in c};delete=len(unique)<40
 rows.append({'source_vertices':len(c),'welded_vertices':len(unique),'delete':delete})
 if delete:doomed.update(c)
before=[len(head.data.vertices),len(head.data.polygons)]
if doomed:
 bm=bmesh.new();bm.from_mesh(head.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in doomed],context='VERTS');bm.to_mesh(head.data);bm.free();head.data.update()
rep={'method':'Count unique geometric vertices after 0.1 mm weld, not duplicate UV/normal vertices. Prior 30 mm distance test retained all components.','components':rows,'deleted_source_vertices':len(doomed),'before':before,'after':[len(head.data.vertices),len(head.data.polygons)]};(O/'hair_final.json').write_text(json.dumps(rep,indent=2));print('V3B_HAIR',json.dumps(rep),flush=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate_final.blend'))
