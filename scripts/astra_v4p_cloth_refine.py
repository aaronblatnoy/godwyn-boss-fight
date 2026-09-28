"""Spatially uniform Laplacian cloth weights; unedited body coordinates."""
import bpy,sys,json,numpy as np,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'));import astra_v3_build as b
O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));body=bpy.data.objects['V4_Body'];pts=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);tri=np.array([list(f.vertices) for f in body.data.polygons]);uv=np.array([d.uv[:] for d in body.data.uv_layers[0].data]).reshape(-1,3,2).mean(1);cloth=b.image_array(bpy.data.images['V4 cloth_mask']);cv=cloth[(uv[:,1]*2048).astype(int)%2048,(uv[:,0]*2048).astype(int)%2048,0];cent=pts[tri].mean(1);ids=np.unique(tri[(cv>.3)&(cent[:,2]<1.72)]);allowed=['Hips','LeftUpLeg','LeftLeg','LeftFoot','LeftToeBase','RightUpLeg','RightLeg','RightFoot','RightToeBase'];names={g.index:g.name for g in body.vertex_groups};W=np.zeros((len(pts),len(allowed)))
for v in body.data.vertices:
 for g in v.groups:
  if names[g.group] in allowed:W[v.index,allowed.index(names[g.group])]=g.weight
original=W.copy();total=W.sum(1);ids=ids[total[ids]>.02]
# Include embroidered seam vertices within 12mm of blue fabric below the hip plates.
tree=KDTree(len(ids))
for i,idx in enumerate(ids):tree.insert(Vector(pts[idx]),i)
tree.balance();extra=[];chosen=set(ids.tolist())
for idx in np.where((pts[:,2]<1.45)&(total>.5))[0]:
 if idx not in chosen and tree.find(Vector(pts[idx]))[2]<.012:extra.append(idx)
ids=np.unique(np.concatenate((ids,np.array(extra,dtype=int))));values=W[ids]/total[ids,None]
# Dense source triangles must not shrink the effective smoothing radius: aggregate 20mm spatial cells.
cells,inv=np.unique(np.floor(pts[ids]/.02).astype(int),axis=0,return_inverse=True);counts=np.bincount(inv);cp=np.zeros((len(cells),3));cw=np.zeros((len(cells),len(allowed)))
np.add.at(cp,inv,pts[ids]);cp/=counts[:,None];np.add.at(cw,inv,values);cw/=counts[:,None];tree=KDTree(len(cells))
for i,p in enumerate(cp):tree.insert(Vector(p),i)
tree.balance();ix=np.zeros((len(cells),64),int);val=np.zeros_like(ix,dtype=float)
for i,p in enumerate(cp):
 for j,(_,k,d) in enumerate(tree.find_n(Vector(p),64)):ix[i,j]=k;val[i,j]=math.exp(-(d/.065)**2) if d<.13 else 0
val/=val.sum(1)[:,None]
for _ in range(8):cw=.2*cw+.8*np.sum(cw[ix]*val[:,:,None],axis=1)
# Interpolate the smooth weight field from eight cells, preserving each vertex's allowed-weight total.
for row,idx in enumerate(ids):
 found=tree.find_n(Vector(pts[idx]),8);weights=np.array([1/max(d,.005)**2 for _,_,d in found]);weights/=weights.sum();W[idx]=sum(cw[k]*weights[j] for j,(_,k,d) in enumerate(found))*total[idx]
for j,n in enumerate(allowed):
 group=body.vertex_groups[n]
 for idx in ids:
  if W[idx,j]>1e-8:group.add([int(idx)],float(W[idx,j]),'REPLACE')
  else:group.remove([int(idx)])
rep={'method':'8 uniform-space Laplacian passes on 20mm cells, 65mm Gaussian kernel, 130mm cutoff; 8-cell interpolation','vertices':len(ids),'embroidered_seam_vertices_added':len(extra),'cells':len(cells),'max_weight_change':float(abs(W-original).max()),'bones':allowed,'vertex_coordinates_unchanged':True};(O/'cloth_refine.json').write_text(json.dumps(rep,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate.blend'));print('V4P_CLOTH_REFINE',json.dumps(rep),flush=True)
