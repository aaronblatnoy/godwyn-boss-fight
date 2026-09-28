"""V3B neck color sampling and exportable skin helpers; no file writes."""
import bpy,numpy as np,colorsys

def flat_neck(head):
 mat=head.data.materials[0];nodes=mat.node_tree.nodes
 base=next(n.image for n in nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('Image_0'))
 vals=np.empty(len(base.pixels),np.float32);base.pixels.foreach_get(vals);tex=vals.reshape(base.size[1],base.size[0],base.channels)
 skin=head.data.color_attributes['meshy_skin_mask'];uv=head.data.uv_layers.active.data
 pos=np.array([(head.matrix_world@x.co)[:] for x in head.data.vertices]);polys=[]
 for f in head.data.polygons:
  if sum(skin.data[i].color[0] for i in f.loop_indices)/len(f.loop_indices)>.5:polys.append((float(pos[list(f.vertices),2].mean()),f))
 threshold=float(np.percentile([z for z,f in polys],15));samples=[]
 for z,f in polys:
  if z>threshold:continue
  for i in f.loop_indices:
   u,v=uv[i].uv;samples.append(tex[min(base.size[1]-1,max(0,int(v*base.size[1]))),min(base.size[0]-1,max(0,int(u*base.size[0]))),:3])
 raw=np.median(samples,axis=0)
 # Image buffers expose encoded 8-bit RGB; Principled defaults are linear.
 # The owner requested the median texture color, with skin_i01 SSS only.
 rgb=np.where(raw<=.04045,raw/12.92,((raw+.055)/1.055)**2.4)
 out=bpy.data.materials.new('Astra V3B flat sampled neck skin_i01');out.use_nodes=True;bs=out.node_tree.nodes.get('Principled BSDF');source=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*rgb,1);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.55
 copied={}
 for name in ['Subsurface Radius','Subsurface Scale','Subsurface IOR','Subsurface Anisotropy']:
  if name in source.inputs and name in bs.inputs:
   value=source.inputs[name].default_value;bs.inputs[name].default_value=value;copied[name]=list(value) if hasattr(value,'__len__') else float(value)
 gate=nodes.get('SkinLook sss gate');ss=gate.inputs[1].default_value if gate else source.inputs['Subsurface Weight'].default_value
 bs.inputs['Subsurface Weight'].default_value=ss;copied['Subsurface Weight']=ss
 if hasattr(source,'subsurface_method'):bs.subsurface_method=source.subsurface_method
 out.diffuse_color=(*rgb,1)
 return out,{'name':out.name,'head_texture':base.name,'sampling':'median RGB of skin-mask face-corner texels in lowest 15% of skin face centers (neck region), decoded from sRGB; skin_i01 subsurface settings copied without extra color tint','neck_max_z_m':threshold,'texel_samples':len(samples),'texture_median_rgb':raw.tolist(),'flat_base_rgb':rgb.tolist(),'subsurface':copied,'image_nodes':0}
