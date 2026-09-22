import sys,json,collections
sys.dont_write_bytecode=True
import bpy,bmesh,numpy as np
from pathlib import Path
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_skin import png,srgb
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'));o=bpy.data.objects['char1'];bm=bmesh.new();bm.from_mesh(o.data)
# Merge cracks up to 1 mm only on original body; this is a local repair, not a remesh.
vs=[v for v in bm.verts if v.co.z<278 and v.link_faces];old=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=vs,dist=.1);weld=old-len(bm.verts)
# Fill small closed boundary loops. Keep panel hems and all large openings.
seen=set();filled=0;rejected=0
for e in list(bm.edges):
 if e in seen or not e.is_boundary:continue
 stack=[e];component=[];seen.add(e)
 while stack:
  q=stack.pop();component.append(q)
  for v in q.verts:
   for x in v.link_edges:
    if x.is_boundary and x not in seen:seen.add(x);stack.append(x)
 vv={v for e in component for v in e.verts}
 if not (3<=len(component)<=32) or max(v.co.z for v in vv)>278:continue
 pos=np.array([tuple(v.co) for v in vv]);span=np.linalg.norm(pos.max(0)-pos.min(0))
 if span>6:rejected+=1;continue
 if any(sum(e.is_boundary for e in v.link_edges)!=2 for v in vv):continue
 adjacent={f for e in component for f in e.link_faces};mat=collections.Counter(f.material_index for f in adjacent).most_common(1)[0][0]
 if mat not in (0,1,4):continue
 uvdata={}
 for uv in bm.loops.layers.uv.values():
  uvdata[uv]={v:next((l[uv].uv.copy() for f in v.link_faces for l in f.loops if l.vert==v),None) for v in vv}
 ordered=[component[0].verts[0]];previous=None;current=ordered[0];allowed=set(component)
 while True:
  candidates=[e.other_vert(current) for e in current.link_edges if e in allowed and e.other_vert(current)!=previous]
  nxt=candidates[0]
  if nxt==ordered[0]:break
  ordered.append(nxt);previous,current=current,nxt
  if len(ordered)>len(vv):break
 try:newface=bm.faces.new(ordered)
 except ValueError:continue
 newface.normal_update();average=sum((f.normal for f in adjacent),newface.normal*0)
 if newface.normal.dot(average)<0:newface.normal_flip()
 made=[newface]
 for f in made:
  f.material_index=mat;f.smooth=True
  for l in f.loops:
   for uv,values in uvdata.items():
    if values.get(l.vert) is not None:l[uv].uv=values[l.vert]
 filled+=len(made)
# Fair jagged border vertices locally without collapsing hems or plate silhouettes.
cloth=[v for v in bm.verts if v.co.z<278 and len(v.link_faces)>2 and all(f.material_index in (1,4) for f in v.link_faces)]
origin={v:v.co.copy() for v in cloth}
for _ in range(5):
 changes={}
 for v in cloth:
  others=[e.other_vert(v) for e in v.link_edges if e.other_vert(v).link_faces]
  if not others:continue
  avg=sum((q.co for q in others),v.co*0)/len(others);delta=(avg-v.co)*.28
  if delta.length>.12:delta.normalize();delta*=.12
  target=v.co+delta;total=target-origin[v]
  if total.length>.4:total.normalize();target=origin[v]+total*.4
  changes[v]=target
 for v,p in changes.items():v.co=p
bm.normal_update();bm.to_mesh(o.data);bm.free();o.data.update()
# Dark indigo nap: retain atlas features and metallic trim mask.
for name in ['Astra Round2 royal blue and continuous gold trim','Astra Round2 royal blue undersleeves']:
 m=bpy.data.materials[name];n=m.node_tree.nodes;bs=next(n for n in n if n.type=='BSDF_PRINCIPLED');bs.inputs['Sheen Tint'].default_value=(.035,.020,.090,1)
 tex=bs.inputs['Base Color'].links[0].from_node;im=tex.image;a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);a=a.reshape(im.size[1],im.size[0],4)[:,:,:3]
 orm=n['Image Texture.001'].image;p=np.empty(len(orm.pixels),np.float32);orm.pixels.foreach_get(p);mask=p.reshape(orm.size[1],orm.size[0],4)[:,:,2:3]
 linear=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4);linear*=mask+(1-mask)*.4
 path=OUT/('r3_'+('cloth' if 'continuous' in name else 'sleeves')+'_basecolor.png');png(path,srgb(linear));im.filepath=str(path);im.reload();im.pack()
# Reduce the raised vermilion ridge without changing lip landmarks or mouth silhouette.
me=o.data;coords=np.array([tuple(v.co) for v in me.vertices]);mw=o.matrix_world
# New facial patch is identified by skin material and world-space position, not mutable indices.
ids={vi for f in me.polygons if f.material_index==2 for vi in f.vertices};count=0
for i in ids:
 v=me.vertices[i];p=mw@v.co
 if abs(p.x)<.046 and 2.855<p.z<2.9 and p.y<-.38:
  # Submillimetre softening across the lip-border relief only.
  amount=.0007*np.exp(-((p.z-2.877)/.012)**2)*max(0,1-(p.x/.046)**2)
  v.co.y+=amount/.01;count+=1
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
(OUT/'r3_repair2.json').write_text(json.dumps({'welded_vertices':weld,'small_holes_filled':filled,'large_loops_preserved':rejected,'cloth_border_vertices_faired':len(cloth),'lip_vertices_softened':count},indent=2))
