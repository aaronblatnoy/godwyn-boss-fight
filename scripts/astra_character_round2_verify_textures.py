"""Independent PNG decode + UV surface samples, including mip filtering."""
import json,hashlib,numpy as np
from pathlib import Path
from PIL import Image
from scipy import ndimage as nd
P=Path(__file__).resolve().parents[1]/'renders/astra/character';T=P/'textures'
def read(path):return np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)[::-1]/255
def decode(v):return np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
def stats(v):return {'count':len(v),'mean':v.mean(0).tolist(),'median':np.median(v,0).tolist(),'p05':np.quantile(v,.05,axis=0).tolist(),'p95':np.quantile(v,.95,axis=0).tolist()}
def sample(a,uv):
 n=a.shape[0];xy=np.clip(uv*n-.5,0,n-1.0001);ij=xy.astype(np.int32);f=(xy-ij).astype(np.float32);x=ij[:,0];y=ij[:,1];fx=f[:,0,None];fy=f[:,1,None]
 return (a[y,x]*(1-fx)+a[y,x+1]*fx)*(1-fy)+(a[y+1,x]*(1-fx)+a[y+1,x+1]*fx)*fy
def main():
 report=json.loads((P/'round2_bake_diagnostic.json').read_text());d=np.load(P/'round1_backup/audit_arrays.npz');uv=d['uv'].reshape(-1,3,2);m=np.load(P/'round2_work/final_face_materials.npy');centers=d['vertices'][d['triangles']].mean(1)
 result={'method':'PNG bytes explicitly sRGB-decoded for base color; ORM/normal decoded as linear data. Seven barycentric bilinear samples per selected surface triangle, plus 2x/4x/8x mip stress of isolated gold atlas.','gold':{},'robe':{}}
 weights=np.array([[1/3]*3,[.6,.2,.2],[.2,.6,.2],[.2,.2,.6],[.48,.48,.04],[.48,.04,.48],[.04,.48,.48]],np.float32)
 for kind,prefix,selected in [('gold','astra_character_char1',(m==0)),('robe','astra_character_char1_robe',(m==1)&(centers[:,2]<1.4))]:
  b=read(T/f'{prefix}_basecolor_4096.png');o=read(T/f'{prefix}_orm_4096.png');n=read(T/f'{prefix}_normal_4096.png');coords=np.einsum('ki,fij->fkj',weights,uv[selected]).reshape(-1,2);lin=decode(b);bs=sample(lin,coords);os=sample(o,coords);ns=sample(n,coords)*2-1;core=os[:,2]>.99 if kind=='gold' else os[:,2]<.01
  out={'surface_faces':int(selected.sum()),'all_surface_linear_base':stats(bs),'all_surface_orm':stats(os),'core_linear_base':stats(bs[core]),'core_orm':stats(os[core]),'normal_length':stats(np.linalg.norm(ns,axis=1)),'normal_rgb':stats((ns+1)*.5)}
  if kind=='gold':
   bad=bs[:,2]>bs[:,0]*1.35;out['blue_contaminated_samples']=int(bad.sum());out['blue_contamination_fraction']=float(bad.mean());out['fully_metallic_fraction']=float((os[:,2]>.99).mean());out['mip_blue_fractions']={}
   for factor in [2,4,8]:
    # Box-filter the actual atlas before UV sampling, mimicking a mip footprint.
    q=lin.reshape(4096//factor,factor,4096//factor,factor,3).mean((1,3));v=sample(q,coords);out['mip_blue_fractions'][str(factor)]=float((v[:,2]>v[:,0]*1.35).mean())
   assert out['blue_contaminated_samples']==0,out
   assert out['fully_metallic_fraction']>.999,out
  else:
   spec=np.array(report['robe_spec_linear']);out['core_median_delta_from_spec']=(np.median(bs[core],0)-spec).tolist();out['core_median_relative_error']=(abs(np.median(bs[core],0)-spec)/spec).tolist();assert np.max(out['core_median_relative_error'])<.04,out
  result[kind]=out
  del b,o,n,lin,bs,os,ns
 # Source UV mask comparison remains reproducible at identical coordinates.
 src=read(P/'source_1.png');sourceorm=read(P/'source_2.png');g=sourceorm[:,:,2]>.6;r=(src[:,:,2]>src[:,:,0]*1.35)&~g
 for kind,prefix,mask in [('gold','astra_character_char1',g),('robe','astra_character_char1_robe',r)]:
  mask=nd.binary_erosion(mask,iterations=3).repeat(2,0).repeat(2,1);b=read(T/f'{prefix}_basecolor_4096.png');o=read(T/f'{prefix}_orm_4096.png');valid=o[:,:,1]>.05;mm=mask&valid
  if kind=='robe':mm=mm&(o[:,:,2]<.01)
  result[kind]['source_region_inset3_linear']=stats(decode(b[mm]));result[kind]['source_region_inset3_orm']=stats(o[mm]);del b,o
 result['sword_map_sha256_preserved']={}
 for k in ['basecolor','orm','normal']:
  name=f'astra_character_Godwyn_Sword_{k}_2048.png';a=hashlib.sha256((T/name).read_bytes()).hexdigest();b=hashlib.sha256((P/'round1_backup/textures'/name).read_bytes()).hexdigest();assert a==b;result['sword_map_sha256_preserved'][k]=a
 report['round2_quantitative_verification']=result;(P/'round2_bake_diagnostic.json').write_text(json.dumps(report,indent=2));print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
