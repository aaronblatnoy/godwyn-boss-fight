"""Immutable full Meshy surface; V4 materials, source-world stance, rigid grip."""
import bpy,sys,json,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';sys.path.insert(0,str(R/'scripts'))
import astra_v3_build as b
import astra_v3m_retarget_world as w
import astra_v3m_publish as pub
O=R/'renders/astra/v4';bpy.ops.wm.open_mainfile(filepath=str(O/'raw.blend'));s=bpy.context.scene;rig=bpy.data.objects['Astra_V4_Rig'];body=bpy.data.objects['V4_Body'];s.render.fps=30

def fingerprint(ob):
 h=hashlib.sha256()
 for col,key,num,dtype in [(ob.data.vertices,'co',3,np.float32),(ob.data.loops,'vertex_index',1,np.int32),(ob.data.uv_layers.active.data,'uv',2,np.float32)]:
  a=np.empty(len(col)*num,dtype);col.foreach_get(key,a);h.update(a.tobytes())
 for v in ob.data.vertices:h.update(np.asarray([(g.group,g.weight) for g in v.groups],np.float64).tobytes())
 return h.hexdigest()
original=fingerprint(body);mat=body.data.materials[0];base=b.pbr_images(mat)['base'];basevals=b.image_array(base)
before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'models/meshy_godwyn_full.glb'));src=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');sm=src.data.materials[0];ims=b.pbr_images(sm);uvbase=b.image_array(ims['base']);atlas_mae=float(np.mean(abs(basevals[:,:,:3]-uvbase[:,:,:3])));atlas_corr=float(np.corrcoef(basevals[:,:,:3].ravel()[::13],uvbase[:,:,:3].ravel()[::13])[0,1]);print('V4_ATLAS',atlas_mae,atlas_corr,flush=True);assert atlas_mae<.04 and atlas_corr>.98,'Atlas alignment needs inspection'
mat=sm.copy();mat.name='V4 fullbody masked skin and approved gold blue';body.data.materials.clear();body.data.materials.append(mat)
for ob in list(bpy.data.objects):
 if ob not in before:bpy.data.objects.remove(ob,do_unlink=True)
nt=mat.node_tree;N=nt.nodes;L=nt.links;bs=next(n for n in N if n.type=='BSDF_PRINCIPLED');tex=next(n for n in N if n.type=='TEX_IMAGE' and n.image==ims['base']);baseout=tex.outputs['Color'];rgb=uvbase[:,:,:3];orm=b.image_array(ims['metallic']);r,g,bl=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
# Texel-based color masks. Metallic rejects gold; skin's red excess over green
# relative to green over blue rejects ochre blond hair. No mesh surgery.
skin=((r>.35)&(r>g*1.045)&(g>bl*1.03)&((r-g)>(g-bl)*1.1)&(orm[:,:,2]<.45)).astype(np.float32)
plate=(orm[:,:,2]>.65).astype(np.float32);cloth=((bl>r*1.12)&(bl>g*1.12)&(orm[:,:,2]<.35)).astype(np.float32)
# Limit skin selection to UV triangles on exposed face/ear/neck, preventing warm
# painted ornament on cloth being interpreted as skin. Classifier remains texel-based.
pts=np.array([(body.matrix_world@v.co)[:] for v in body.data.vertices]);tri=np.array([list(f.vertices) for f in body.data.polygons]);cent=pts[tri].mean(1);uv=np.array([d.uv[:] for d in body.data.uv_layers.active.data]).reshape(-1,3,2);allowed=np.zeros(skin.shape,bool)
for t in uv[(cent[:,2]>2.68)&(cent[:,2]<3.035)&(abs(cent[:,0])<.27)&((cent[:,1]<-.46)|((abs(cent[:,0])>.15)&(cent[:,2]<3.00)&(cent[:,1]<-.35)))]:
 a=t*2048;lo=np.maximum(0,np.floor(a.min(0)).astype(int)-1);hi=np.minimum(2047,np.ceil(a.max(0)).astype(int)+1)
 xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5);p=np.stack([xx,yy],-1);e0=a[1]-a[0];e1=a[2]-a[0];d=e0[0]*e1[1]-e0[1]*e1[0]
 if abs(d)<1e-8:continue
 q=p-a[0];u=(q[:,:,0]*e1[1]-q[:,:,1]*e1[0])/d;v=(e0[0]*q[:,:,1]-e0[1]*q[:,:,0])/d;allowed[lo[1]:hi[1]+1,lo[0]:hi[0]+1]|=(u>=-.01)&(v>=-.01)&(u+v<=1.01)
for _ in range(6):allowed=allowed|np.roll(allowed,1,0)|np.roll(allowed,-1,0)|np.roll(allowed,1,1)|np.roll(allowed,-1,1)
skin*=allowed
for _ in range(2):skin=(skin+np.roll(skin,1,0)+np.roll(skin,-1,0)+np.roll(skin,1,1)+np.roll(skin,-1,1))/5
# Hair is unmodified by either material adjustment; metallic gold pixels high
# above the collar are excluded from the gold tint to preserve its native look.
hairuv=np.zeros(skin.shape,bool)
for t in uv[cent[:,2]>2.77]:
 a=t*2048;lo=np.maximum(0,np.floor(a.min(0)).astype(int));hi=np.minimum(2047,np.ceil(a.max(0)).astype(int));hairuv[lo[1]:hi[1]+1,lo[0]:hi[0]+1]=True
plate[hairuv]=0

def mask(name,arr):
 im=bpy.data.images.new('V4 '+name,2048,2048,alpha=True);im.colorspace_settings.name='Non-Color';rgba=np.ones((2048,2048,4),np.float32);rgba[:,:,:3]=arr[:,:,None];im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(O/(name+'.png'));im.file_format='PNG';im.save();im.pack();n=N.new('ShaderNodeTexImage');n.name='V4 '+name;n.image=im;return n.outputs['Color']
sk=mask('skin_mask',skin);pl=mask('plate_mask',plate);cl=mask('cloth_mask',cloth)
def mix(name,fac,a,col,blend='MIX'):
 n=N.new('ShaderNodeMixRGB');n.name=name;n.blend_type=blend
 if isinstance(fac,(float,int)):n.inputs[0].default_value=fac
 else:L.new(fac,n.inputs[0])
 L.new(a,n.inputs[1]);n.inputs[2].default_value=col;return n
mul=mix('V4 skin SPEC multiply',.35,baseout,(.95,.90,.82,1),'MULTIPLY');hsv=N.new('ShaderNodeHueSaturation');hsv.inputs['Hue'].default_value=.492;hsv.inputs['Saturation'].default_value=1.28;hsv.inputs['Value'].default_value=1.;L.new(mul.outputs[0],hsv.inputs['Color']);rosy=mix('V4 skin rosy',.10,hsv.outputs[0],(.85,.42,.38,1),'SOFT_LIGHT');smix=mix('V4 masked skin',sk,baseout,(0,0,0,1));L.new(rosy.outputs[0],smix.inputs[2]);gold=mix('V4 gold25',.25,baseout,(.82,.65,.15,1));pm=mix('V4 masked plates',pl,smix.outputs[0],(0,0,0,1));L.new(gold.outputs[0],pm.inputs[2]);blue=mix('V4 blue30',.30,baseout,(0,.03,.23,1));cm=mix('V4 masked cloth',cl,pm.outputs[0],(0,0,0,1));L.new(blue.outputs[0],cm.inputs[2]);L.new(cm.outputs[0],bs.inputs['Base Color'])
rough=bs.inputs['Roughness'].links[0].from_socket;rm=mix('V4 plates roughness',pl,rough,(.35,.35,.35,1));L.new(rm.outputs[0],bs.inputs['Roughness']);sss=N.new('ShaderNodeMath');sss.operation='MULTIPLY';sss.inputs[1].default_value=.32;L.new(sk,sss.inputs[0]);L.new(sss.outputs[0],bs.inputs['Subsurface Weight']);bs.inputs['Subsurface Radius'].default_value=(1,.35,.2);bs.inputs['Subsurface Scale'].default_value=.008
for im in {x for x in ims.values() if x}:im.pack()
# Append v3 read-only for its exact world orientations and rigid grip.
with bpy.data.libraries.load(str(R/'models/astra_character_v3.blend'),link=False) as (avail,dest):
 dest.objects=['Astra_V3_Rig','Godwyn_Sword'];dest.actions=['Combat_Stance']
for ob in dest.objects:s.collection.objects.link(ob)
source=bpy.data.objects['Astra_V3_Rig'];sword=bpy.data.objects['Godwyn_Sword'];act=next(a for a in dest.actions if a);source.data.pose_position='REST';bpy.context.view_layer.update();grip=b.attach_sword(sword,source,rig);source.data.pose_position='POSE';w.assign(source,act,1)
order=w.topological(rig);rest={n:rig.data.bones[n].matrix_local.copy() for n in order};src_rest=source.matrix_world@source.data.bones['Hips'].matrix_local;target_rest=rig.matrix_world@rig.data.bones['Hips'].matrix_local;rootdelta=src_rest.translation-target_rest.translation;winv=rig.matrix_world.inverted();rinv=rig.matrix_world.to_quaternion().inverted().to_matrix();start,end=map(lambda x:int(round(x)),act.frame_range);new=bpy.data.actions.new('V4_Combat_Stance');slot,bag=w.action_channelbag(new,rig);expected=[];previous={}
for frame in range(start,end+1):
 w.assign(source,act,frame);desired={};row={}
 for n in order:
  world=source.matrix_world@source.pose.bones[n].matrix;desired[n]=rinv@world.to_quaternion().normalized().to_matrix();pa=rig.data.bones[n].parent;relative=rest[pa.name].to_3x3().inverted()@rest[n].to_3x3() if pa else rest[n].to_3x3();basis=relative.inverted()@(desired[pa.name].inverted() if pa else Matrix.Identity(3))@desired[n];q=basis.to_quaternion().normalized()
  if n in previous and q.dot(previous[n])<0:q.negate()
  previous[n]=q.copy();row[n]=world.to_quaternion().normalized()
  for i,val in enumerate(q):w.key(bag,f'pose.bones["{n}"].rotation_quaternion',i,frame-start+1,val)
 root=winv@((source.matrix_world@source.pose.bones['Hips'].matrix).translation-rootdelta);loc=rest['Hips'].to_3x3().inverted()@(root-rig.data.bones['Hips'].head_local)
 for i,val in enumerate(loc):w.key(bag,'pose.bones["Hips"].location',i,frame-start+1,val)
 expected.append(row)
for f in bag.fcurves:f.update()
for ob in list(bpy.data.objects):
 if ob not in [rig,body,sword]:bpy.data.objects.remove(ob,do_unlink=True)
for a in list(bpy.data.actions):
 if a!=new:bpy.data.actions.remove(a)
new.name='Combat_Stance';new.use_fake_user=True;w.reset(rig);sole=w.sole_ids(body);errors=[];ground=[]
# Root-only per-frame Z grounding retains every source world bone orientation.
curves={(c.data_path,c.array_index):c for c in bag.fcurves}
for frame in range(1,len(expected)+1):
 w.assign(rig,new,frame);bp=w.evaluated_points(body);low=min(float(bp[ix,2].min()) for ix in sole.values());shift=.001-low;delta=rest['Hips'].to_3x3().inverted()@(rig.matrix_world.to_3x3().inverted()@Vector((0,0,shift)))
 for i in range(3):
  c=curves[('pose.bones["Hips"].location',i)];c.keyframe_points[frame-1].co[1]+=delta[i];c.update()
 ground.append(shift)
for frame in range(1,len(expected)+1):
 w.assign(rig,new,frame)
 for n in order:
  q=(rig.matrix_world@rig.pose.bones[n].matrix).to_quaternion().normalized();angle=math.degrees(q.rotation_difference(expected[frame-1][n]).angle);errors.append(min(angle,abs(360-angle)))
assert fingerprint(body)==original
rep={'surface_fingerprint_before':original,'surface_fingerprint_after':fingerprint(body),'unchanged':'positions, ordered face corners, UV coordinates, vertex weights; no cuts, grafts, deletions or smoothing','material_maps_restored':[k for k,v in ims.items() if v],'base_atlas_max_difference':float(np.max(abs(basevals-uvbase))),'base_atlas_mean_difference':atlas_mae,'base_atlas_correlation':atlas_corr,'mask_texels':{'skin':int(skin.sum()),'plates':int(plate.sum()),'cloth':int(cloth.sum())},'grip':grip,'grip_translation_adjustment_m':[0,0,0],'frames':len(expected),'max_world_orientation_error_deg':max(errors),'ground_root_offsets_m':ground,'weights':pub.weight_audit([body,sword],rig)}
s.frame_start=1;s.frame_end=len(expected);w.assign(rig,new,1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'candidate.blend'));(O/'build.json').write_text(json.dumps(rep,indent=2));print('V4_BUILD',json.dumps({k:v for k,v in rep.items() if k!='grip'}),flush=True)
