"""Read-only round-1 audit. Must run before material edits."""
import bpy, numpy as np, json, hashlib, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import ROOT, OUT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pixels(im):
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a)
 return a.reshape(im.size[1],im.size[0],4)[:,:,:3].copy()
def decode(x):return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def stats(a):
 return dict(count=len(a),mean=a.mean(0).tolist(),median=np.median(a,0).tolist(),p05=np.quantile(a,.05,axis=0).tolist(),p95=np.quantile(a,.95,axis=0).tolist()) if len(a) else {}
def erode(m,n):
 for _ in range(n):m=m&np.roll(m,1,0)&np.roll(m,-1,0)&np.roll(m,1,1)&np.roll(m,-1,1)
 return m
def signature(o):
 me=o.data;v=np.array([v.co[:] for v in me.vertices],np.float32);p=np.array([l.vertex_index for l in me.loops],np.int32);w=[[(g.group,g.weight) for g in v.groups] for v in me.vertices]
 return dict(vertices=len(v),polygons=len(me.polygons),positions=hashlib.sha256(v.tobytes()).hexdigest(),topology=hashlib.sha256(p.tobytes()).hexdigest(),weights=hashlib.sha256(json.dumps(w).encode()).hexdigest(),groups=[g.name for g in o.vertex_groups],uvs=[{'name':u.name,'hash':hashlib.sha256(np.array([q.uv[:] for q in u.data],np.float32).tobytes()).hexdigest()} for u in me.uv_layers],modifiers=[{'name':m.name,'type':m.type} for m in o.modifiers],matrix_world=[list(r) for r in o.matrix_world])

def main():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
 report={'stage':'round1_before_any_edits','source_sha256':sha(ROOT/'models/godwyn_game.glb'),'round1_blend_sha256':sha(ROOT/'models/astra_character_v2.blend'),'stress_pose_check':{'available':False,'missing':['scripts/astra_xslash_v2_poses.py','renders/astra/pose_stress_windup.png','renders/astra/pose_stress_cross.png','renders/astra/pose_stress_follow.png'],'checked_once':True},'preservation':{},'images':[],'regions':{},'robe_spec_linear':[.08,.12,.35]}
 for o in bpy.data.objects:
  if o.type=='MESH' and o.name in ['char1','Godwyn_Sword','Astra_Undersleeves']:report['preservation'][o.name]=signature(o)
 for im in bpy.data.images:
  if im.type=='RENDER_RESULT':continue
  report['images'].append({'name':im.name,'size':list(im.size),'colorspace':im.colorspace_settings.name,'packed':bool(im.packed_file)})
 src=pixels(bpy.data.images.load(str(OUT/'source_1.png'),check_existing=False));mr=pixels(bpy.data.images.load(str(OUT/'source_2.png'),check_existing=False))
 # PNG byte buffers are encoded RGB; retain both values and explicit sRGB decode.
 base=bpy.data.images.load(str(OUT/'textures/astra_character_char1_basecolor_4096.png'),check_existing=False)
 b=pixels(base);orm=pixels(bpy.data.images.load(str(OUT/'textures/astra_character_char1_orm_4096.png'),check_existing=False));normal=pixels(bpy.data.images.load(str(OUT/'textures/astra_character_char1_normal_4096.png'),check_existing=False))
 gold=mr[:,:,2]>.6;robe=(src[:,:,2]>src[:,:,0]*1.35)&~gold
 for label,mask in [('gold',gold),('robe',robe)]:
  for inset in [0,3,8]:
   m=erode(mask,inset).repeat(2,0).repeat(2,1);v=b[m];o=orm[m];n=normal[m]*2-1
   report['regions'][f'{label}_source_inset_{inset}px']={'source_rgb_encoded':stats(src[erode(mask,inset)]),'round1_rgb_encoded':stats(v),'round1_rgb_linear':stats(decode(v)),'round1_orm':stats(o),'normal_length':stats(np.linalg.norm(n,axis=1)),'blue_in_gold_fraction':float((v[:,2]>v[:,0]*1.35).mean()) if label=='gold' else None,'gold_in_robe_fraction':float(((v[:,0]>v[:,2]*1.65)&(o[:,2]>.6)).mean()) if label=='robe' else None,'low_metallic_on_gold_fraction':float((o[:,2]<.9).mean()) if label=='gold' else None}
 # UV-linked samples locate known material regions and quantify wrong material classes.
 char=bpy.data.objects['char1'];uv=np.array([d.uv[:] for d in char.data.uv_layers.active.data],np.float32);verts=np.array([char.matrix_world@v.co for v in char.data.vertices]);centers=[];tex=[];mats=[]
 for f in char.data.polygons:
  centers.append(verts[list(f.vertices)].mean(0));tex.append(uv[list(f.loop_indices)].mean(0));mats.append(f.material_index)
 centers=np.array(centers);tex=np.array(tex);mats=np.array(mats);ij=np.minimum((tex*[4096,4096]).astype(int),4095);v=b[ij[:,1],ij[:,0]];o=orm[ij[:,1],ij[:,0]]
 report['uv_samples']={}
 for name,m in [('chest_gold',(mats==0)&(centers[:,2]>2.15)&(centers[:,2]<2.65)&(abs(centers[:,0])<.29)&(centers[:,1]<-.12)),('lower_robe',(mats==1)&(centers[:,2]<1.4)),('face',(mats==2)&(centers[:,2]>2.8)),('shoulder_gold',(mats==0)&(centers[:,2]>2.30)&(centers[:,2]<2.7)&(abs(centers[:,0])>.29))]:
  ids=np.where(m)[0];report['uv_samples'][name]={'faces':len(ids),'base_linear':stats(decode(v[m])),'orm':stats(o[m]),'blue_fraction':float((v[m,2]>v[m,0]*1.35).mean()),'samples':[{'face':int(i),'uv':tex[i].tolist(),'position':centers[i].tolist(),'encoded':v[i].tolist(),'linear':decode(v[i]).tolist(),'orm':o[i].tolist()} for i in ids[::max(1,len(ids)//12)][:12]]}
 report['scene']={'engine':bpy.context.scene.render.engine,'exposure':bpy.context.scene.view_settings.exposure,'view_transform':bpy.context.scene.view_settings.view_transform,'camera':bpy.context.scene.camera.name,'lights':[{'name':o.name,'energy':o.data.energy,'color':list(o.data.color)} for o in bpy.data.objects if o.type=='LIGHT']}
 report['uv_layers']=[{'name':u.name,'active_render':u.active_render,'range_min':uv.min(0).tolist(),'range_max':uv.max(0).tolist()} for u in char.data.uv_layers]
 report['round1_bake_settings']={'margin':bpy.context.scene.render.bake.margin,'margin_type':bpy.context.scene.render.bake.margin_type,'selected_to_active':bpy.context.scene.render.bake.use_selected_to_active,'cage':bpy.context.scene.render.bake.use_cage}
 np.savez_compressed(OUT/'round1_backup/audit_arrays.npz',source=src,source_orm=mr,base=b,orm=orm,normal=normal,uv=uv,vertices=verts,triangles=np.array([f.vertices[:] for f in char.data.polygons],np.int32),face_material=mats)
 (OUT/'round2_bake_diagnostic.json').write_text(json.dumps(report,indent=2))
 print(json.dumps({k:report[k] for k in ['regions','uv_layers','round1_bake_settings','scene']},indent=2),flush=True)
if __name__=='__main__':main()
