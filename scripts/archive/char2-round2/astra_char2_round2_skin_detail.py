"""Seamless world-registered skin maps; approved portrait microstructure without broad lighting."""
import bpy,numpy as np,math
from pathlib import Path
from astra_char2_skin import png,srgb
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
def apply():
 o=bpy.data.objects['char1'];me=o.data;m=me.materials[2];nodes=m.node_tree.nodes;uv=me.uv_layers['AstraChar2FaceUV']
 for f in me.polygons:
  if f.material_index==2:
   for li in f.loop_indices:
    p=o.matrix_world@me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=((p.x+.16)/.32,(p.z-2.76)/.47)
    if me.loops[li].vertex_index>=253776:me.uv_layers[0].data[li].uv=uv.data[li].uv
 im=bpy.data.images.load(str(ROOT/'face-concepts/godwyn_face_APPROVED.png'),check_existing=True)
 a=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(a);a=a.reshape(im.size[1],im.size[0],4)[::-1,:,:3]
 a=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
 H,W=a.shape[:2];lum=np.maximum(a@np.array([.2126,.7152,.0722]),.02)
 fy=np.fft.fftfreq(H)[:,None];fx=np.fft.rfftfreq(W)[None,:]
 detail=np.clip(np.log(lum)-np.fft.irfft2(np.fft.rfft2(np.log(lum))*np.exp(-2*math.pi**2*22**2*(fx*fx+fy*fy)),s=lum.shape),-.24,.24)
 N=2048;x,z=np.meshgrid((np.arange(N)+.5)/N*.32-.16,(np.arange(N)+.5)/N*.47+2.76)
 px=424+x*1944.6;py=(3.225-z)*1944.6
 ix=np.clip(px,0,W-2).astype(int);iy=np.clip(py,0,H-2).astype(int)
 sample=detail[iy,ix]
 reference_chroma=np.clip((a/np.maximum(lum[:,:,None],.02))[iy,ix]/np.array([1.48,.84,.54]),.78,1.22)
 def g(cx,cz,sx,sz):return np.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
 mask=np.clip((.105-abs(x))/.02,0,1)*np.clip((z-2.805)/.014,0,1)*np.clip((3.116-z)/.02,0,1)
 for s in [-1,1]:
  mask*=1-np.clip(g(s*.055,2.996,.032,.013)*3,0,1)
  mask*=1-np.clip(g(s*.055,3.023,.038,.010)*3,0,1)
 mask*=1-np.clip(g(0,2.875,.052,.015)*3,0,1);mask*=1-np.clip(g(0,2.918,.027,.009)*3,0,1)
 rng=np.random.default_rng(992);broad=np.zeros_like(x);fine=np.zeros_like(x)
 for i in range(16):
  t=rng.uniform(0,6.28);f=rng.uniform(35,350);broad+=np.sin(x*f*np.cos(t)+z*f*np.sin(t)+rng.uniform(0,6.28))/16
 for i in range(22):
  t=rng.uniform(0,6.28);f=rng.uniform(3000,18000);fine+=np.sin(x*f*np.cos(t)+z*f*np.sin(t)+rng.uniform(0,6.28))/22
 col=np.ones((*x.shape,3))*[.34,.192,.122];col*=np.exp((sample*mask*.8+broad*.10+fine*.06)[:,:,None]);col*=1+(reference_chroma-1)*mask[:,:,None]*.65
 cellx=(x+.2)/.0011;cellz=(z-2.5)/.0011;ixc=np.floor(cellx).astype(int);izc=np.floor(cellz).astype(int)
 jitter=rng.uniform(.25,.75,(800,800,2));rr=jitter[izc,ixc]
 pore=np.exp(-((cellx-ixc-rr[:,:,0])**2+(cellz-izc-rr[:,:,1])**2)/.17**2)
 col*=1-pore[:,:,None]*.035
 blush=g(0,2.930,.027,.032)*.23
 sockets=np.zeros_like(x);cool=np.zeros_like(x)
 for s in [-1,1]:
  blush+=g(s*.065,2.953,.039,.03)*.08
  sockets+=g(s*.055,3.000,.033,.022)*.42
  cool+=g(s*.085,2.89,.025,.058)*.12+g(s*.096,3.025,.02,.03)*.12
 col=col*(1-blush[:,:,None])+np.array([.38,.13,.085])*blush[:,:,None]
 col=col*(1-sockets[:,:,None])+np.array([.20,.078,.046])*sockets[:,:,None]
 col=col*(1-cool[:,:,None])+np.array([.245,.16,.112])*cool[:,:,None]
 u=x/.044;fall=np.maximum(0,1-u*u)**.65;seam=2.875+.0010*np.cos(u*math.pi)-.00035*u
 top=seam+fall*(.0075+.0025*np.exp(-((abs(x)-.012)/.009)**2)-.0017*np.exp(-(x/.005)**2));bottom=seam-fall*.009
 lip=np.clip(np.minimum((top-z)/.0015,(z-bottom)/.0015),0,1)*(abs(x)<.044)
 col=col*(1-lip[:,:,None])+np.array([.32,.115,.088])*(1+fine[:,:,None]*.12)*lip[:,:,None]
 crease=np.exp(-((z-seam)/.0007)**2)*fall*(abs(x)<.044);col*=1-crease[:,:,None]*.38
 rough=np.clip(.48+broad*.2+fine*.25+sample*mask*.25-g(0,2.945,.025,.06)*.06-lip*.03,.26,.68)
 height=fine*.00007+sample*mask*.00015+broad*.000025-pore*.000045+lip*np.sin(x*5700+np.sin(z*800))*.000014
 dz,dx=np.gradient(height,.47/N,.32/N);normal=np.stack([-dx,-dz,np.ones_like(x)],-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
 glow=.007+.026*np.clip((abs(x)-.07)/.07,0,1);glow*=1-.5*sockets-.5*lip
 arrays={'basecolor':srgb(col),'normal':normal*.5+.5,'orm':np.stack([np.ones_like(x),rough,np.zeros_like(x)],-1),'emission':srgb(np.stack([glow,glow*.88,glow*.45],-1))}
 for key,a in arrays.items():
  path=OUT/('r2_skin_'+key+'.png');png(path,a);im=bpy.data.images.load(str(path),check_existing=False);im.colorspace_settings.name='sRGB' if key in ['basecolor','emission'] else 'Non-Color';im.pack();nodes['AstraChar2 '+key].image=im
 m['emission_rebalance']='Nonzero spatial epidermal transmission approximately 0.4–3.3%; canonical golden color and emission strength 2.5 retained.'
 m['round2_skin_detail']='Continuous current-geometry UV projection; only approved portrait high-frequency skin structure. Broad lighting and facial organs excluded. 2048 maps.'
