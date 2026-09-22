"""Deterministic, packed 1.5K face maps and layered demigod skin, no dependencies installed."""
import bpy,math,struct,zlib,numpy as np
from pathlib import Path
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';UV='AstraChar2FaceUV'
def gauss(x,z,cx,cz,sx,sz):return np.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
def lip_bounds(x):
 u=x/.038;fall=np.maximum(0,1-u*u)**.65
 seam=2.8475+.0013*np.cos(u*math.pi)-.0010*u
 top=seam+fall*(.0044+.0027*np.exp(-((np.abs(x)-.010)/.007)**2)-.0016*np.exp(-(x/.004)**2))
 bottom=seam-fall*.0070
 return seam,top,bottom

def png(path,a):
 a=np.clip(a,0,1);h,w=a.shape[:2];a=np.uint8(a*255+.5)
 def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
 raw=b''.join(b'\0'+row.tobytes() for row in a[::-1])
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
def srgb(a):return np.where(a<.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
def reference_detail(x,z):
 """Extract skin microstructure from approved art, with broad lighting removed.
 Eyes, brows, mouth, nostrils and hair are excluded: geometry supplies features.
 """
 im=bpy.data.images.load(str(ROOT/'face-concepts/godwyn_face_APPROVED.png'),check_existing=True)
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);a=a.reshape(im.size[1],im.size[0],4)[::-1,:,:3]
 lum=np.maximum(.2126*a[:,:,0]+.7152*a[:,:,1]+.0722*a[:,:,2],.025)
 h,w=lum.shape;fy=np.fft.fftfreq(h)[:,None];fx=np.fft.rfftfreq(w)[None,:]
 kernel=np.exp(-2*math.pi**2*16**2*(fx*fx+fy*fy))
 blur=np.fft.irfft2(np.fft.rfft2(np.log(lum))*kernel,s=lum.shape)
 detail=np.clip(np.log(lum)-blur,-.20,.20)
 px=420+x*2090;py=np.interp(z,[2.785,2.815,2.849,2.885,2.952,2.975,3.105],[837,775,680,598,443,396,195])
 ix=np.clip(px,0,w-2).astype(int);iy=np.clip(py,0,h-2).astype(int);tx=px-ix;ty=py-iy
 sampled=(detail[iy,ix]*(1-tx)+detail[iy,ix+1]*tx)*(1-ty)+(detail[iy+1,ix]*(1-tx)+detail[iy+1,ix+1]*tx)*ty
 width=.086-.033*np.clip((z-2.98)/.070,0,1)
 mask=np.clip((width-abs(x))/.020,0,1)*np.clip((z-2.797)/.016,0,1)*np.clip((3.096-z)/.020,0,1)
 mask*=1-np.clip(gauss(abs(x),z,.055,2.953,.032,.011)*2,0,1)
 mask*=1-np.clip(gauss(abs(x),z,.058,2.980,.036,.008)*2,0,1)
 mask*=1-np.clip(gauss(x,z,0,2.849,.045,.013)*2,0,1)
 mask*=1-np.clip(gauss(x,z,0,2.885,.024,.010)*2,0,1)
 return sampled*mask

def maps():
 N=1536;rng=np.random.default_rng(728);u=(np.arange(N)+.5)/N;x,z=np.meshgrid(u*.32-.16,u*.40+2.76)
 broad=np.zeros((N,N));fine=np.zeros_like(broad)
 for k in range(22):
  angle=rng.uniform(0,6.28);freq=rng.uniform(24,190);broad+=np.sin(x*freq*np.cos(angle)+z*freq*np.sin(angle)+rng.uniform(0,6.28))/22
 for k in range(28):
  angle=rng.uniform(0,6.28);freq=rng.uniform(2000,18000);fine+=np.sin(x*freq*np.cos(angle)+z*freq*np.sin(angle)+rng.uniform(0,6.28))/28
 ref=reference_detail(x,z)
 col=np.ones((N,N,3))*np.array([.34,.185,.112]);col*=np.exp(ref[:,:,None]*1.4)*(1+broad[:,:,None]*.24+fine[:,:,None]*.055)
 blush=gauss(abs(x),z,.070,2.915,.032,.032)*.15+gauss(x,z,0,2.889,.024,.02)*.18
 col=col*(1-blush[:,:,None])+np.array([.38,.145,.098])*blush[:,:,None]
 socket=gauss(abs(x),z,.056,2.956,.031,.017)*.50
 col=col*(1-socket[:,:,None])+np.array([.17,.072,.045])*socket[:,:,None]
 lower=gauss(abs(x),z,.058,2.937,.030,.007)*.07
 col*=1-lower[:,:,None]
 seam,top,bottom=lip_bounds(x);lip=np.clip(np.minimum((top-z)/.0012,(z-bottom)/.0012),0,1)*(abs(x)<.038)
 col=col*(1-lip[:,:,None])+np.array([.32,.115,.085])*(1+fine[:,:,None]*.1)*lip[:,:,None]
 crease=np.exp(-((z-seam)/.00065)**2)*np.maximum(0,1-(x/.038)**2)**.4
 col=col*(1-crease[:,:,None]*.55)
 # Tiny irregular melanin speckle, restrained enough not to read as dirt.
 freckles=np.clip((np.sin(x*4529+np.sin(z*6713))*np.sin(z*3701+np.sin(x*3456))-.82)*4,0,1)*.12
 col*=1-freckles[:,:,None]
 rough=.48+broad*.24+fine*.22+ref*.28-gauss(x,z,0,2.91,.025,.06)*.095-lip*.10
 # 30–55 micron relief, sampled at 0.21–0.26 mm per texel.
 height=fine*.00011+broad*.00004+ref*.00018
 height+=lip*np.sin(x*6000+np.sin(z*900))*.000012
 dz,dx=np.gradient(height,.40/N,.32/N);normal=np.stack([-dx,-dz,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
 # Keep canonical emission strength 2.5, filter its visible coverage through epidermis.
 # Nonzero everywhere; increased toward temples and below the jaw, reduced in features.
 glow=.014+.050*np.clip((abs(x)-.060)/.065,0,1)+.020*np.clip((2.825-z)/.06,0,1)
 glow*=1-.65*socket-.60*lip
 emission=np.stack([glow,glow*.88,glow*.45],-1)
 data={'basecolor':(srgb(col),'sRGB'),'normal':(normal*.5+.5,'Non-Color'),'orm':(np.stack([np.ones_like(x),rough,np.zeros_like(x)],-1),'Non-Color'),'emission':(srgb(emission),'sRGB')}
 images={}
 for k,(a,cs) in data.items():
  p=OUT/f'skin_{k}_1536.png';png(p,a)
  name='AstraChar2 Skin '+k
  if name in bpy.data.images:bpy.data.images.remove(bpy.data.images[name])
  im=bpy.data.images.load(str(p),check_existing=False);im.name=name;im.colorspace_settings.name=cs;im.pack();images[k]=im
 return images

def apply_skin():
 o=bpy.data.objects['char1'];m=o.data.materials[2];m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 out=n.new('ShaderNodeOutputMaterial');out.location=(600,100)
 bs=n.new('ShaderNodeBsdfPrincipled');bs.location=(300,100);bs.name='Living golden skin • canonical emission 2.5'
 bs.inputs['Base Color'].default_value=(.95,.90,.82,1);bs.inputs['Metallic'].default_value=0;bs.inputs['Roughness'].default_value=.46
 bs.inputs['Subsurface Weight'].default_value=.20;bs.inputs['Subsurface Radius'].default_value=(1,.36,.17);bs.inputs['Subsurface Scale'].default_value=.0012
 bs.inputs['IOR'].default_value=1.44;bs.inputs['Specular IOR Level'].default_value=.30
 bs.inputs['Emission Color'].default_value=(1,.88,.45,1);bs.inputs['Emission Strength'].default_value=2.5
 l.new(bs.outputs['BSDF'],out.inputs['Surface']);uv=n.new('ShaderNodeUVMap');uv.uv_map=UV;uv.location=(-750,0)
 ims=maps()
 for j,(k,im) in enumerate(ims.items()):
  t=n.new('ShaderNodeTexImage');t.name='AstraChar2 '+k;t.image=im;t.location=(-500,-j*230);t.extension='EXTEND';l.new(uv.outputs['UV'],t.inputs['Vector'])
  if k=='basecolor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
  if k=='emission':l.new(t.outputs['Color'],bs.inputs['Emission Color'])
  if k=='orm':
   sp=n.new('ShaderNodeSeparateColor');sp.location=(-160,-350);l.new(t.outputs['Color'],sp.inputs[0]);l.new(sp.outputs['Green'],bs.inputs['Roughness'])
  if k=='normal':
   nm=n.new('ShaderNodeNormalMap');nm.uv_map=UV;nm.inputs['Strength'].default_value=.85;nm.location=(-100,-120);l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
 # The canonical base remains explicit metadata; epidermal color map supplies local absorption.
 m['canonical_skin_base_linear']=[.95,.90,.82];m['canonical_emission_linear']=[1,.88,.45];m['canonical_emission_strength']=2.5
 m['emission_rebalance']='Nonzero epidermal transmission map, approximately 0.6–8.4% of canonical radiance. No lighting/exposure workaround.'
 m['subsurface_note']='1.2 mm red-channel scale, radius RGB 1/.36/.17; GLB cannot represent Cycles SSS.'
 return m
