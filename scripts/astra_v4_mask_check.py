import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3_build as b
O=R/'renders/astra/v4';bpy.ops.wm.open_mainfile(filepath=str(O/'candidate.blend'));ob=bpy.data.objects['V4_Body'];pts=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);tri=np.array([list(f.vertices) for f in ob.data.polygons]);cent=pts[tri].mean(1);uv=np.array([d.uv[:] for d in ob.data.uv_layers.active.data]).reshape(-1,3,2).mean(1);tex=b.image_array(bpy.data.images['V4 skin_mask']);vals=tex[(uv[:,1]*2048).astype(int)%2048,(uv[:,0]*2048).astype(int)%2048,0];rep={}
for name,mask in {'back_hair':(cent[:,2]>2.78)&(cent[:,1]>-.35),'top_hair':cent[:,2]>3.065,'front_face':(cent[:,2]>2.77)&(cent[:,2]<3.04)&(abs(cent[:,0])<.14)&(cent[:,1]<-.48)}.items():rep[name]={'count':int(mask.sum()),'masked_fraction':float(vals[mask].mean())}
print('V4_MASK_CHECK',json.dumps(rep),flush=True);(O/'mask_check.json').write_text(json.dumps(rep,indent=2))
