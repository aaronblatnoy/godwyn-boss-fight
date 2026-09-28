import bpy,sys,json,numpy as np,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import astra_v3b_materials as mats
import astra_v3m_render as render
O=R/'renders/astra/v3b';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate_r5.blend'));rig=bpy.data.objects['Astra_V3_Rig'];body=bpy.data.objects['char1'];neck=bpy.data.objects['AstraChar2_Meshy_NeckBlend'];p=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);npnt=np.array([(neck.matrix_world@v.co)[:] for v in neck.data.vertices]);center=npnt[:,:2].mean(0)
print('NECK_EXTENTS',center.tolist(),npnt.min(0).tolist(),npnt.max(0).tolist(),flush=True)
# Fit outer seam against the actual preserved collar, with its own skin weights.
# Keep it in the upper interior, so the seam cannot protrude through the breastplate.
axis=np.array(json.loads((O/'build_r5.json').read_text())['measurement']['neck_axis_m']);N=72;z=2.70
faces=[tuple(f.vertices) for f in body.data.polygons if 2.50<float(p[list(f.vertices),2].mean())<2.89 and abs(float(p[list(f.vertices),0].mean()))<.31]
tree=BVHTree.FromPolygons([tuple(x) for x in p],faces,all_triangles=True)
wall=[];wall_weights=[];hit_rows=[]
for k in range(N):
 th=2*math.pi*k/N;direction=Vector((math.cos(th),math.sin(th),0));origin=Vector((axis[0],axis[1],z));hit=tree.ray_cast(origin,direction,.4)
 if hit[0] is None:raise RuntimeError(('No collar wall hit',k))
 loc,normal,fi,dist=hit;ids=faces[fi];w={}
 tri=p[list(ids)];a=tri[1]-tri[0];b=tri[2]-tri[0];q=np.array(loc)-tri[0];uv=np.linalg.lstsq(np.stack([a,b],axis=1),q,rcond=None)[0];bary=np.clip([1-uv.sum(),uv[0],uv[1]],0,1);bary/=bary.sum()
 for i,bw in zip(ids,bary):
  for g in body.data.vertices[i].groups:w[g.group]=w.get(g.group,0)+g.weight*float(bw)
 wall.append(np.array(loc));wall_weights.append(w);hit_rows.append({'angle':k,'distance':dist,'triangle':list(ids)})
wall=np.array(wall)
# Smooth coordinates by a short periodic stencil, well inside the same measured wall.
# Exact contact points retain the surface and barycentric deformation.
for k in range(N):
 v=wall[k,:2]-axis;wall[k,:2]-=.001*v/np.linalg.norm(v)
verts=[];wrows=[];zinner=2.73
# Existing neck radii at the new connection height.
nearest=npnt[np.abs(npnt[:,2]-zinner)<.045];rx=float(np.max(np.abs(nearest[:,0]-center[0])));ry=float(np.max(np.abs(nearest[:,1]-center[1])))
for j in range(6):
 t=j/5
 for k in range(N):
  th=2*math.pi*k/N;start=np.array([center[0]+rx*math.cos(th),center[1]+ry*math.sin(th),zinner]);pt=start*(1-t)+wall[k]*t;pt[2]-=.014*math.sin(math.pi*t);verts.append(pt.tolist())
  w={rig.data.bones.find('neck'):0} # actual object vertex-group indices are assigned below by name
  wrows.append((t,k))
# A short wall skirt and closed dark floor follow the same outer seam rather than flaring out.
for k in range(N):pt=wall[k].copy();pt[2]-=.14;verts.append(pt.tolist());wrows.append((1.,k))
fs=[(j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k) for j in range(6) for k in range(N)]
fs.append(tuple(reversed(range(6*N,7*N))))
old=bpy.data.objects['AstraChar2_V3B_CollarLiner'];bpy.data.objects.remove(old,do_unlink=True)
disk=bpy.data.objects['AstraChar2_V3B_CollarFloor'];bpy.data.objects.remove(disk,do_unlink=True)
m=bpy.data.meshes.new('V3B fitted collar loft');m.from_pydata(verts,[],fs);m.update();ob=bpy.data.objects.new('AstraChar2_V3B_CollarLiner',m);bpy.context.scene.collection.objects.link(ob);ob.parent=rig;ob.matrix_world.identity()
mat,_=mats.flat_neck(bpy.data.objects['AstraChar2_Meshy_HeadHair']);m.materials.append(mat);neck.data.materials.clear();neck.data.materials.append(mat)
dark=bpy.data.materials.new('V3B fitted dark collar floor');dark.use_nodes=True;bs=dark.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.013,.007,.004,1);bs.inputs['Roughness'].default_value=.85;m.materials.append(dark);m.polygons[-1].material_index=1
for f in m.polygons:f.use_smooth=True
names={g.index:g.name for g in body.vertex_groups};groups={n:ob.vertex_groups.new(name=n) for n in names.values()}
for i,(t,k) in enumerate(wrows):
 weights={names[j]:v*t for j,v in wall_weights[k].items()};weights['neck']=weights.get('neck',0)+1-t
 for n,w in weights.items():
  if w>1e-8:groups[n].add([i],w,'REPLACE')
mod=ob.modifiers.new('V3B collar seam follows body wall','ARMATURE');mod.object=rig
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate_r7.blend'))
rep={'neck_axis':axis.tolist(),'neckblend_axis':center.tolist(),'inner_z':zinner,'outer_z':z,'segments':N,'rings':7,'wall_hits':hit_rows,'outer_edge_binding':'nearest measured collar-triangle skin weights, blending to neck at inner ring; closes movement gap without changing raw body','flat_floor_closed':True}
(O/'liner_fit.json').write_text(json.dumps(rep,indent=2));print('V3B_FITTED_LINER',json.dumps({k:v for k,v in rep.items() if k!='wall_hits'}),flush=True)
