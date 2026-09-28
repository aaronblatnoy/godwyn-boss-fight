import bpy,sys,json,collections
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r5_clay.blend'))
o=bpy.data.objects['char1'];bm=o.data;vp=collections.defaultdict(list)
for f in bm.polygons:
 for v in f.vertices:vp[v].append(f.index)
seen=set();rows=[]
for f in bm.polygons:
 if f.index in seen:continue
 todo=[f.index];seen.add(f.index);component=[]
 while todo:
  fi=todo.pop();component.append(fi)
  for v in bm.polygons[fi].vertices:
   for n in vp[v]:
    if n not in seen:seen.add(n);todo.append(n)
 ids={v for fi in component for v in bm.polygons[fi].vertices};ps=[o.matrix_world@bm.vertices[i].co for i in ids]
 if max(p.z for p in ps)>2.64:rows.append({'faces':len(component),'slots':dict(collections.Counter(bm.polygons[fi].material_index for fi in component)),'min':[min(p[k] for p in ps) for k in range(3)],'max':[max(p[k] for p in ps) for k in range(3)]})
(R/'renders/astra/char2/r5_fragment_audit.json').write_text(json.dumps(sorted(rows,key=lambda x:-x['faces']),indent=2));print('COMPONENTS ABOVE COLLAR',len(rows),flush=True)
