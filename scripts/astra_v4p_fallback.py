"""Approved feature-only fallback after full projection showed donor hair smearing."""
import bpy,sys,json,numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';O=R/'renders/astra/v4p';bpy.ops.wm.open_mainfile(filepath=str(O/('candidate.blend' if '--candidate' in sys.argv else 'face_full.blend')));data=np.load(O/'face_atlas_data.npz');world=data['world'];coverage=data['coverage'];x,y,z=world.transpose(2,0,1)
def pix(name):
 im=bpy.data.images.get('V4P_'+name) or bpy.data.images.load(str(O/('V4P_'+name+'.png')),check_existing=False);im.colorspace_settings.name='sRGB' if name.endswith('base') else 'Non-Color';a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);return a.reshape(2048,2048,4)
def oval(cx,cz,rx,rz):
 d=np.sqrt(((x-cx)/rx)**2+((z-cz)/rz)**2);return np.clip((1-d)/.22,0,1)
alpha=np.maximum(np.maximum(oval(-.056,2.920,.036,.016),oval(.054,2.920,.036,.016)),oval(-.002,2.796,.060,.025));alpha*=coverage&(pix('projected_base')[:,:,:3].max(2)>.025);alpha*=np.clip((-.475-y)/.02,0,1);alpha*=np.clip((.082-abs(x))/.010,0,1)
for channel in ['base','rough','normal']:
 orig=pix('original_'+channel);proj=pix('projected_'+channel)
 if channel=='base':
  region=coverage&(abs(x)>.03)&(abs(x)<.075)&(z>2.86)&(z<2.89)&(y<-.48);ratio=np.median(orig[region,:3],axis=0)/np.maximum(np.median(proj[region,:3],axis=0),.01);proj[:,:,:3]*=np.clip(ratio,.6,1.5)
 out=orig.copy();out[:,:,:3]=orig[:,:,:3]*(1-alpha[:,:,None])+proj[:,:,:3]*alpha[:,:,None]
 if channel=='normal':
  n=out[:,:,:3]*2-1;n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-8);out[:,:,:3]=(n+1)/2
 mask=coverage.copy()
 for _ in range(16):
  for axis,step in [(0,1),(0,-1),(1,1),(1,-1)]:
   neighbor=np.roll(mask,step,axis);take=(~mask)&neighbor;out[take]=np.roll(out,step,axis)[take];mask|=take
 im=bpy.data.images.get('V4P_face_'+channel) or bpy.data.images.load(str(O/('V4P_face_'+channel+'.png')),check_existing=False);im.colorspace_settings.name='sRGB' if channel=='base' else 'Non-Color';im.pixels.foreach_set(out.ravel());im.filepath_raw=str(O/('fallback_face_'+channel+'.png'));im.file_format='PNG';im.save();fresh=bpy.data.images.load(im.filepath_raw,check_existing=False);fresh.colorspace_settings.name=im.colorspace_settings.name;fresh.pack()
 for mat in bpy.data.materials:
  if mat.use_nodes:
   for node in mat.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image and (node.image==im or (mat.name=='V4_Face' and channel in node.image.name)):node.image=fresh
rep={'fallback':'eyes and lips only; native eyebrows retained','reason':'Full-face projection visibly mapped donor blond hair into thin dark/gold cheek streaks. Rejected by direct close-up inspection.','feature_mask':'Two feathered eye ellipses and one lip ellipse in V4 rest world coordinates; 22% radial feather. Original V4 appearance retained elsewhere.','projected_atlas_fraction':float((alpha[coverage]>.01).mean()),'body_geometry_changed':False};(O/'fallback.json').write_text(json.dumps(rep,indent=2));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/('candidate.blend' if '--candidate' in sys.argv else 'face_fallback.blend')));print('V4P_FALLBACK',json.dumps(rep),flush=True)
