import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3_build as b
O=R/'renders/astra/v4';bpy.ops.wm.open_mainfile(filepath=str(O/'raw.blend'));ob=bpy.data.objects['V4_Body'];pts=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);tri=np.array([list(f.vertices) for f in ob.data.polygons]);cent=pts[tri].mean(1);uv=np.array([d.uv[:] for d in ob.data.uv_layers.active.data]).reshape(-1,3,2);im=b.pbr_images(ob.data.materials[0])['base'];tex=b.image_array(im);tuv=uv.mean(1);rgb=tex[(tuv[:,1]*2048).astype(int)%2048,(tuv[:,0]*2048).astype(int)%2048,:3];worldarea=np.linalg.norm(np.cross(pts[tri[:,1]]-pts[tri[:,0]],pts[tri[:,2]]-pts[tri[:,0]]),axis=1)/2;uva=abs(((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0])))/2
regions={'head_above_2.75':cent[:,2]>2.75,'face':(cent[:,2]>2.77)&(cent[:,2]<3.04)&(abs(cent[:,0])<.14)&(cent[:,1]<-.48),'chest':(cent[:,2]>2.1)&(cent[:,2]<2.5)&(abs(cent[:,0])<.3)&(cent[:,1]<-.4),'hair_back':(cent[:,2]>2.78)&(cent[:,1]>-.35)}
rep={}
for name,mask in regions.items():
 rep[name]={'triangles':int(mask.sum()),'surface_cm2':float(worldarea[mask].sum()*1e4),'uv_area':float(uva[mask].sum()),'texels_per_cm':float(np.sqrt(uva[mask].sum()*2048**2/(worldarea[mask].sum()*1e4))),'rgb_percentiles':np.percentile(rgb[mask],[10,50,90],axis=0).tolist()}
(O/'resolution.json').write_text(json.dumps(rep,indent=2));print('V4_RESOLUTION',json.dumps(rep),flush=True)
