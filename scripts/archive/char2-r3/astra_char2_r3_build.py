"""Round 3: immutable input, constrained mesh repair and portable material detail."""
import sys, json, math
sys.dont_write_bytecode=True
from pathlib import Path
import bpy,bmesh,numpy as np
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_skin import png,srgb
from astra_character_common import reset_pose
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_preround3.blend'));reset_pose()
r={};o=bpy.data.objects['char1'];bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
# Remove only detached slivers; preserve substantial panels and all head geometry.
seen=set();dead=[]
for v in bm.verts:
 if v in seen or not v.link_faces:continue
 stack=[v];seen.add(v);vs=[];fs=set()
 while stack:
  q=stack.pop();vs.append(q);fs.update(q.link_faces)
  for e in q.link_edges:
   z=e.other_vert(q)
   if z not in seen:seen.add(z);stack.append(z)
 if len(fs)<=6 and all(f.material_index in (0,1,4) for f in fs) and max(v.co.z for v in vs)<278:dead.extend(fs)
r['detached_sliver_faces_removed']=len(dead)
bmesh.ops.delete(bm,geom=dead,context='FACES_ONLY')
# Submillimetre seam weld limited to body. Does not touch face patch or hair.
body=[v for v in bm.verts if v.co.z<278 and v.link_faces]
old=len(bm.verts);bmesh.ops.remove_doubles(bm,verts=body,dist=.025);r['seam_vertices_welded']=old-len(bm.verts)
# Suppress high-frequency folded spikes while holding cloth boundaries and material seams.
cloth=[v for v in bm.verts if v.co.z<278 and len(v.link_faces)>2 and all(f.material_index in (1,4) for f in v.link_faces) and all(e.is_manifold for e in v.link_edges)]
r['cloth_vertices_locally_faired']=len(cloth)
origin={v:v.co.copy() for v in cloth}
for _ in range(6):
 updates={}
 for v in cloth:
  avg=sum((e.other_vert(v).co for e in v.link_edges),v.co*0)/len(v.link_edges)
  delta=(avg-v.co)*.34
  if delta.length>.16:delta.normalize();delta*=.16
  target=v.co+delta;total=target-origin[v]
  if total.length>.6:total.normalize();target=origin[v]+total*.6
  updates[v]=target
 for v,p in updates.items():v.co=p
# Orient connected surface normals consistently; preserve original topology beyond local repairs.
bmesh.ops.recalc_face_normals(bm,faces=[f for f in bm.faces if f.material_index in (0,1,4) and f.calc_center_median().z<278]);bm.to_mesh(o.data);bm.free();o.data.update()

def pixels(im):
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);return a.reshape(im.size[1],im.size[0],4)
def lin(a):return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def image(name,a,cs):
 p=OUT/(name+'.png');png(p,a);im=bpy.data.images.load(str(p),check_existing=False);im.colorspace_settings.name=cs;im.pack();return im
heights={}
for slot,name in [(0,'gold'),(1,'cloth'),(-1,'sleeves')]:
 m=o.data.materials[slot] if slot>=0 else bpy.data.objects['Astra_Undersleeves'].data.materials[0]
 n=m.node_tree.nodes;l=m.node_tree.links;bs=next(v for v in n if v.type=='BSDF_PRINCIPLED')
 base=bs.inputs['Base Color'].links[0].from_node;orm=n.get('Image Texture.001');normal=n.get('Image Texture.002')
 a=pixels(base.image);rgb=lin(a[:,:,:3]);p=pixels(orm.image)[:,:,:3].copy();metal=p[:,:,2]
 if name=='gold':
  # Preserve tonal-zone ratios and pure metal; age recesses according to existing AO.
  rgb*=np.array([.63,.62,.72]);rgb*= (.65+.35*p[:,:,0:1]);p[:,:,1]=np.clip(p[:,:,1]+.10,.28,.76);p[:,:,2]=1
 else:
  fac=metal[:,:,None];rgb=rgb*(1-fac)*np.array([.105,.045,.115])+rgb*fac*np.array([.66,.64,.74]);p[:,:,1]=p[:,:,1]*(metal)+(.78)*(1-metal)
 base.image=image('r3_'+name+'_basecolor',srgb(rgb),'sRGB');orm.image=image('r3_'+name+'_orm',p,'Non-Color')
 if name!='gold':
  bs.inputs['Sheen Weight'].default_value=.65;bs.inputs['Sheen Tint'].default_value=(.20,.13,.35,1);bs.inputs['Sheen Roughness'].default_value=.75
  inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;l.new(n['Separate Color'].outputs['Blue'],inv.inputs[1]);mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.65;l.new(inv.outputs[0],mul.inputs[0]);l.new(mul.outputs[0],bs.inputs['Sheen Weight'])
 # Recover fine relief from baked tangent slopes; high-pass removes broad atlas-island offsets.
 nm=pixels(normal.image)[:,:,:3]*2-1;H,W=nm.shape[:2];fx=np.fft.rfftfreq(W)[None,:]*2*np.pi;fy=np.fft.fftfreq(H)[:,None]*2*np.pi
 gx=-nm[:,:,0]/np.maximum(nm[:,:,2],.25);gy=-nm[:,:,1]/np.maximum(nm[:,:,2],.25)
 den=fx*fx+fy*fy;spec=(-1j*fx*np.fft.rfft2(gx)-1j*fy*np.fft.rfft2(gy))/np.maximum(den,1e-8);spec*=1-np.exp(-den*18**2/2)
 h=np.fft.irfft2(spec,s=(H,W)).astype(np.float32);h=np.clip(h/(np.percentile(abs(h),98)+1e-6),-1,1)
 if name!='gold':h=np.maximum(h,0)*metal
 heights[slot]=(h,.00035 if name=='gold' else .0006)
 hi=image('r3_'+name+'_relief',np.repeat((h*.5+.5)[:,:,None],3,axis=2),'Non-Color');tex=n.new('ShaderNodeTexImage');tex.name='R3 measured relief height';tex.image=hi
 dis=n.new('ShaderNodeDisplacement');dis.inputs['Scale'].default_value=0.0;dis.inputs['Midlevel'].default_value=.5;l.new(tex.outputs['Color'],dis.inputs['Height']);l.new(dis.outputs[0],n['Material Output'].inputs['Displacement'])
 # Geometry receives this relief below. Zero shader scale avoids double-displacement.
 m['relief_geometry_amplitude_m']=heights[slot][1];m['relief_path']='UV sampled physical vertex displacement, native + GLB; node scale zero avoids applying twice'
 r[name]={'base_multiplier':[.63,.62,.72] if name=='gold' else [.105,.045,.115],'sheen':0 if name=='gold' else .65,'relief_m':heights[slot][1]}
# UV-sample and apply actual relief to existing tessellation; no subdivision of simulation panels.
for obj,slots in [(o,(0,1)),(bpy.data.objects['Astra_Undersleeves'],(-1,))]:
 me=obj.data;uv=me.uv_layers.active.data;acc=np.zeros(len(me.vertices));cnt=np.zeros(len(me.vertices))
 for f in me.polygons:
  slot=f.material_index if obj==o else -1
  if slot not in slots:continue
  h,amp=heights[slot];H,W=h.shape
  for li in f.loop_indices:
   vi=me.loops[li].vertex_index
   if obj==o and me.vertices[vi].co.z>278:continue
   u,v=uv[li].uv;acc[vi]+=float(h[int(v*H)%H,int(u*W)%W])*amp;cnt[vi]+=1
 normals=[v.normal.copy() for v in me.vertices]
 for v in me.vertices:
  if cnt[v.index]:v.co+=normals[v.index]*(acc[v.index]/cnt[v.index]/obj.scale.x)
 me.update()
# Anisotropic fine existing fibers. Preserve their geometry, slots, and rig attachments.
for m in bpy.data.materials:
 if m.name.startswith('AstraChar2 R2 hair') or m.name=='AstraChar2 warm blonde eyebrows':
  bs=next((v for v in m.node_tree.nodes if v.type=='BSDF_PRINCIPLED'),None)
  if bs:bs.inputs['Anisotropic'].default_value=.72;bs.inputs['Roughness'].default_value=.36
# Head's inherited hair material: dielectrics, not metallic gold hair.
m=o.data.materials[3];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for key in ['Metallic','Base Color','Roughness']:
 for link in list(bs.inputs[key].links):m.node_tree.links.remove(link)
bs.inputs['Metallic'].default_value=0;bs.inputs['Base Color'].default_value=(.32,.19,.065,1);bs.inputs['Roughness'].default_value=.38;bs.inputs['Anisotropic'].default_value=.72
# Stronger but controlled skin microdetail. Keep prior landmark geometry untouched.
m=o.data.materials[2];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Subsurface Weight'].default_value=.18;bs.inputs['Subsurface Scale'].default_value=.0013;bs.inputs['Subsurface Radius'].default_value=(1,.36,.17)
nm=next(n for n in m.node_tree.nodes if n.type=='NORMAL_MAP');nm.inputs['Strength'].default_value=1.35
bs.inputs['Specular IOR Level'].default_value=.27
em=bs.inputs['Emission Color'].links[0].from_node;ee=lin(pixels(em.image)[:,:,:3]);r['emission']={'strength':2.5,'map_red_min_median_max':np.percentile(ee[:,:,0],[0,50,100]).tolist(),'effective_red_min_median_max':np.percentile(ee[:,:,0]*2.5,[0,50,100]).tolist(),'interpretation':'Intentional textured attenuation, NOT uniform spec radiance 2.5; strength remains 2.5. Central skin about 0.014-0.018 effective red.'}
for side in ['L','R']:
 ob=bpy.data.objects['AstraChar2_Nostril_'+side]
 # Retain names and mesh; move liner 2mm deeper into nasal cavity.
 ob.location.y+=.002
mat=bpy.data.materials['AstraChar2 nostril interior'];b=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(.022,.005,.003,1)
r['hair_bones']=[b.name for b in bpy.data.objects['Armature'].data.bones if 'hair' in b.name.lower()]
r['hair_weighted_vertices']={}
for ob in [o]+[x for x in bpy.data.objects if x.name.startswith('AstraChar2_R2_Hair')]:
 ids={g.index for g in ob.vertex_groups if 'hair' in g.name.lower()};r['hair_weighted_vertices'][ob.name]=sum(any(g.group in ids and g.weight>.001 for g in v.groups) for v in ob.data.vertices)
reset_pose();bpy.context.preferences.filepaths.save_version=0;bpy.context.scene['astra_char2_round3_quality_gate']='PENDING VISUAL REVIEW';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
(OUT/'r3_changes.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
