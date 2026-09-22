import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_wip.blend'))
s=bpy.context.scene;s.frame_set(10);o=bpy.data.objects['char1'];dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);me=ev.to_mesh()
vs=o.data.vertices;ws=[o.matrix_world@v.co for v in vs];ps=[o.matrix_world@v.co for v in me.vertices]
items=[]
for e in o.data.edges:
 a,b=e.vertices;before=(ws[a]-ws[b]).length;after=(ps[a]-ps[b]).length
 if after>.22 and before<.12:items.append((after-before,a,b,before,after))
items.sort(reverse=True)
for _,a,b,before,after in items[:24]:
 print('EDGE',round(before,3),round(after,3))
 for i in [a,b]:print('VERT',i,tuple(round(v,3) for v in ws[i]),[(o.vertex_groups[g.group].name,round(g.weight,3)) for g in vs[i].groups if g.weight>.01])
print('BAD EDGES',len(items));ev.to_mesh_clear()
