"""Read-only source preservation and delivered face-density checks, black-sky only."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight'
O=R/'renders/astra/v4p';protected=json.loads((O/'protected.json').read_text());checks={}
for rel,old in protected.items():
 p=R/rel;now={'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()};checks[rel]={'unchanged':old==now,**now}
assert all(v['unchanged'] for v in checks.values())
def measure(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));ob=bpy.data.objects['V4_Body'];h=hashlib.sha256()
 for col,key,n,dt in [(ob.data.vertices,'co',3,np.float32),(ob.data.loops,'vertex_index',1,np.int32)]:
  a=np.empty(len(col)*n,dt);col.foreach_get(key,a);h.update(a.tobytes())
 return ob,h.hexdigest()
_,original=measure(R/'renders/astra/v4/candidate.blend');ob,final=measure(O/'candidate_export.blend');assert original==final
P=np.array([(ob.matrix_world@v.co)[:] for v in ob.data.vertices]);tris=np.array([list(f.vertices) for f in ob.data.polygons]);chosen=np.array([f.material_index==1 for f in ob.data.polygons]);q=P[tris[chosen]];area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)/2
def density(layer,width):
 uv=np.array([d.uv[:] for d in ob.data.uv_layers[layer].data]).reshape(-1,3,2)[chosen];uv[:,:,0]*=width;uv[:,:,1]*=2048;a=uv[:,1]-uv[:,0];b=uv[:,2]-uv[:,0];pixelarea=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
 return {'area_equivalent_texels_per_cm':float(np.sqrt(pixelarea.sum()/area.sum())/100),'median_triangle_texels_per_cm':float(np.median(np.sqrt(pixelarea/np.maximum(area,1e-20)))/100),'pixel_area':float(pixelarea.sum()),'skin_area_m2':float(area.sum())}
rep={'protected_files':checks,'geometry_sha256_original':original,'geometry_sha256_delivered':final,'body_vertices':len(ob.data.vertices),'body_polygons':len(ob.data.polygons),'face_triangles':int(chosen.sum()),'original_face_density':density(0,4096),'dedicated_face_density':density('V4FaceUV',2048),'used_materials':sorted({m.name for o in bpy.context.scene.objects if o.type=='MESH' for m in o.data.materials}),'packed_images':sum(bool(im.packed_file) for im in bpy.data.images),'all_sources_and_body_geometry_unchanged':True}
assert rep['used_materials']==['V4_BodySword','V4_Face'];(O/'finalcheck.json').write_text(json.dumps(rep,indent=2));print('V4P_FINALCHECK',json.dumps(rep),flush=True)
