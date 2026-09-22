import bpy,json
from pathlib import Path
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_prechar2.blend'))
o=bpy.data.objects['char1'];me=o.data;uv=me.uv_layers.active;heads=[f for f in me.polygons if all((o.matrix_world@me.vertices[i].co).z>2.78 for i in f.vertices)];parent={f.index:f.index for f in heads};edges={}
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
area=0;coords=[];skinarea=0
for f in heads:
 loops=list(f.loop_indices);points=[uv.data[i].uv.copy() for i in loops];coords+=points
 a=abs(sum(points[j].x*points[(j+1)%len(points)].y-points[(j+1)%len(points)].x*points[j].y for j in range(len(points)))/2);area+=a
 if f.material_index==2:skinarea+=a
 for j,li in enumerate(loops):
  a=tuple(round(v,6) for v in points[j]);b=tuple(round(v,6) for v in points[(j+1)%len(points)]);key=(me.loops[li].edge_index,*sorted([a,b]))
  if key in edges:parent[root(f.index)]=root(edges[key])
  else:edges[key]=f.index
r=json.loads((OUT/'recon.json').read_text());r['head_uv_layout']={'layer':'UVMap','head_polygons':len(heads),'uv_continuous_components_within_head_subset':len({root(f.index) for f in heads}),'bounds':[[min(p[i] for p in coords),max(p[i] for p in coords)] for i in [0,1]],'summed_head_uv_area':area,'summed_original_skin_slot_uv_area':skinarea,'note':'Head shares the original full-character 4K atlas. Component count is within the clipped head subset, not a whole-body UV island count. Skin-colored forehead triangles also occur in original gold slot.'};(OUT/'recon.json').write_text(json.dumps(r,indent=2))
with (OUT/'recon.log').open('a') as f:f.write('\nHEAD UV LAYOUT\n'+json.dumps(r['head_uv_layout'],indent=2)+'\n')
print(json.dumps(r['head_uv_layout']),flush=True)
