import bpy,numpy as np
from pathlib import Path
P=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/character')
d=np.load(P/'source_mesh.npz');pos=d['positions'];tris=d['triangles'];uv=d['uv'];coord=pos[tris].mean(1);keep=(np.abs(coord[:,0])<8)&(coord[:,1]<-37)&(coord[:,2]>286)&(coord[:,2]<306)
u=uv.reshape(-1,3,2).mean(1)[keep]
for name in ['source_1.png','source_2.png','textures/astra_character_char1_basecolor_4096.png']:
 im=bpy.data.images.load(str(P/name));a=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(a);a=a.reshape(im.size[1],im.size[0],4);c=a[np.clip((u[:,1]*im.size[1]).astype(int),0,im.size[1]-1),np.clip((u[:,0]*im.size[0]).astype(int),0,im.size[0]-1),:3]
 print(name,'median',np.median(c,0),'quantile',np.quantile(c,[.1,.9],axis=0),flush=True)
