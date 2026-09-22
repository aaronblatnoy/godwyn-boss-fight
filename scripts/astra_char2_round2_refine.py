"""Deterministic round 2: immutable input, localized facial correction and hairline groom."""
import bpy,sys,math,random,json,bmesh
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');sys.path.insert(0,str(ROOT/'scripts'));OUT=ROOT/'renders/astra/char2'
from astra_char2_face import g,smooth,material,mesh,strands
from astra_char2_round2_compare import compare
from astra_char2_skin import png,srgb

def shift(z):return float(np.interp(z,[2.78,2.795,2.815,2.859,2.915,2.982,3.02,3.10,3.13],[0,.019,.020,.017,.010,.016,.008,0,0]))
def hairline(x):return float(np.interp(abs(x),[0,.025,.045,.065,.085,.105,.14],[3.121,3.125,3.11,3.075,3.025,2.97,2.91]))+.0012*math.sin(x*930)+.0007*math.sin(x*1777)
def sculpt():
 o=bpy.data.objects['char1'];mw=o.matrix_world;inv=mw.inverted();me=o.data
 protected={vi for f in me.polygons if f.material_index in (1,4) for vi in f.vertices}
 for v in me.vertices:
  if v.index in protected:continue
  p=mw@v.co;x,y,z=p
  if z<2.78 or y>-.32 or abs(x)>.145:continue
  w=smooth(-.32,-.39,y)*(1-smooth(.115,.145,abs(x)))
  d=0
  for s in [-1,1]:
   d-=.005*g(x,z,s*.082,2.951,.027,.012)
   d+=.004*g(x,z,s*.080,2.922,.026,.018)
   d+=.003*g(x,z,s*.094,3.006,.018,.027)
   d-=.003*g(x,z,s*.079,2.855,.018,.023)
   d-=.003*g(x,z,s*.055,3.008,.030,.008)
   d+=.002*g(x,z,s*.055,2.982,.027,.010)
   u=(x-s*.055)/.027
   if abs(u)<1.1:d+=.0022*math.exp(-((z-(2.995+.003*max(0,1-u*u)))/.002)**2)*max(0,1-(u/1.1)**4)
  d+=.0005*g(x,z,0,2.835,.03,.004)
  # Relax sharp philtrum and broaden lip pillows, keeping calm mouth corners.
  d+=.0015*g(abs(x),z,.004,2.881,.003,.012)
  x*=1+.25*g(x,z,0,2.810,.065,.020)*w
  x*=1+.20*g(x,z,0,2.864,.045,.014)+.20*g(x,z,0,2.912,.020,.012)
  x+=(1 if x>0 else -1)*.0025*g(abs(x),z,.083,2.95,.025,.018)*w
  p.x=x;p.y+=d*w;p.z+=shift(z)*w
  p.z+=.021*g(x,z,0,2.798,.080,.020)*w
  v.co=inv@p
 # The unchanged original UV coordinates keep all previous skin maps registered.
 for ob in bpy.data.objects:
  if not ob.name.startswith('AstraChar2_') or ob.type!='MESH':continue
  optical=any(k in ob.name for k in ['Eyeball','Iris','Pupil','Cornea'])
  coords=[ob.matrix_world@v.co for v in ob.data.vertices]
  cz=sum(p.z for p in coords)/max(1,len(coords));iv=ob.matrix_world.inverted()
  for v,p in zip(ob.data.vertices,coords):
   p.z+=shift(cz if optical else p.z)
   if optical:p.y+=0
   v.co=iv@p
 # Continuous lip and philtrum forms, with no inherited doubled ridges.
 for v in me.vertices:
  p=mw@v.co;x,y,z=p
  if y>-.38 or abs(x)>.058 or not 2.846<z<2.913:continue
  u=x/.044;fall=max(0,1-u*u)**.65;seam=2.875+.001*math.cos(u*math.pi)-.00035*u
  top=seam+fall*(.0075+.0025*math.exp(-((abs(x)-.012)/.009)**2)-.0017*math.exp(-(x/.005)**2));bottom=seam-fall*.009
  target=-.429+4*x*x+.23*(2.875-z)
  if bottom<z<top:
   t=(z-seam)/max(.0001,top-seam) if z>seam else (seam-z)/max(.0001,seam-bottom)
   target-=.005*fall*math.sin(t*math.pi)
  target+=.0012*fall*math.exp(-((z-seam)/.0008)**2)
  target+=.001*g(x,z,0,2.898,.003,.010)
  w=(1-smooth(.040,.058,abs(x)))*(1-smooth(.017,.032,abs(z-2.881)))
  p.y=y*(1-w)+target*w;v.co=inv@p
 # Enlarge the iris under the lids, keeping it curved onto the eyeball.
 for ob in bpy.data.objects:
  if not any(k in ob.name for k in ['AstraChar2_Iris_','AstraChar2_Pupil_','AstraChar2_Cornea_']):continue
  s=-1 if ob.name.endswith('_L') else 1;cx=s*.055;cz=2.98116+(s==1)*.000944;cz+=shift(cz);iv=ob.matrix_world.inverted()
  for v in ob.data.vertices:
   p=ob.matrix_world@v.co;oldr2=(p.x-cx)**2+(p.z-cz)**2;oldfront=-.393-math.sqrt(max(.000001,.0248**2-oldr2));offset=p.y-oldfront
   p.x=cx+(p.x-cx)*1.22;p.z=cz+(p.z-cz)*1.22
   p.y=-.393-math.sqrt(max(.000001,.0248**2-(p.x-cx)**2-(p.z-cz)**2))+offset;v.co=iv@p
 # Keep upper/lower lid tissue in front of the sclera; socket recess cannot cut through it.
 for v in me.vertices:
  p=mw@v.co
  if p.y>-.35:continue
  for s in [-1,1]:
   cx=s*.055;cz=2.98116+(s==1)*.000944;cz+=shift(cz)
   u=(p.x-cx)/(s*.024);zz=p.z-cz-.002*u;r2=(p.x-cx)**2+(p.z-cz)**2
   hh=(.0058 if zz>0 else .0065)*max(0,1-u*u)**.66
   if r2<.0255**2 and (abs(u)>=1 or abs(zz)>hh):
    sy=-.393-math.sqrt(max(.000001,.0248**2-r2))-.0011
    p.y=min(p.y,sy);v.co=inv@p
 # Restore skin at the central hairline where the old gold shell cut across it.
 uv=me.uv_layers['AstraChar2FaceUV']
 for f in me.polygons:
  p=mw@f.center
  if abs(p.x)<.065 and p.y<-.32 and 3.09<p.z<hairline(p.x):
   f.material_index=2
   for li in f.loop_indices:
    q=mw@me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=((q.x+.16)/.32,(q.z-2.76)/.40)
 me.update()
 tree=BVHTree.FromPolygons([mw@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons])
 for ob in bpy.data.objects:
  if 'Eyebrows_' not in ob.name:continue
  iv=ob.matrix_world.inverted()
  for v in ob.data.vertices:
   p=ob.matrix_world@v.co;hit=tree.ray_cast(Vector((p.x,-.8,p.z)),Vector((0,1,0)),.7)[0]
   if hit:p.y=hit.y-.0005;v.co=iv@p
 for f in me.polygons:
  p=mw@f.center;x,y,z=p
  # Existing fragments along the face perimeter are skin, not metal.
  if y<-.32 and 2.795<z<3.10 and abs(x)<(.063+ .052*math.sin(math.pi*max(0,min(1,(z-2.795)/.305)))):
   f.material_index=2
   for li in f.loop_indices:
    q=mw@me.vertices[me.loops[li].vertex_index].co
    if uv.data[li].uv.x<0:uv.data[li].uv=((q.x+.16)/.32,(q.z-shift(q.z)-2.76)/.40)
 cn=[tuple(n.vector) for n in me.corner_normals]
 for f in me.polygons:
  if f.material_index==2:
   f.use_smooth=True
   for li in f.loop_indices:cn[li]=(0,0,0)
 if me.has_custom_normals:me.normals_split_custom_set(cn)
 me.update()

def groom():
 for ob in list(bpy.data.objects):
  if ob.name.startswith('AstraChar2_R2_'):
   data=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
   if data.users==0:bpy.data.meshes.remove(data)
 o=bpy.data.objects['char1'];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh();vs=[o.matrix_world@v.co for v in em.vertices];fs=[tuple(p.vertices) for p in em.polygons]
 tree=BVHTree.FromPolygons(vs,fs,all_triangles=False)
 def surf(x,z):
  hit=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),1.1)[0]
  return hit.y-.0012 if hit and hit.y<-.22 else None
 rng=random.Random(811)
 mats=[material('AstraChar2 R2 hair '+str(i),c,.48,0)[0] for i,c in enumerate([(.20,.11,.035),(.38,.23,.085),(.53,.36,.16),(.65,.48,.25)])]
 # Continuous dark roots cover the reflective old cap, with a softly irregular edge.
 vv=[];valid=[];ff=[];nx=160;nz=40
 for i in range(nx+1):
  x=-.171+.342*i/nx;h=hairline(x)
  top=3.0+.205*math.sqrt(max(0,1-(x/.180)**2))-.002
  for j in range(nz+1):
   z=h+(top-h)*j/nz;yy=surf(x,z);vv.append((x,(yy-.0007) if yy is not None else -.33,z));valid.append(yy is not None)
 for i in range(nx):
  for j in range(nz):
   a=i*(nz+1)+j;face=(a,a+nz+1,a+nz+2,a+1)
   if all(valid[k] for k in face) and max(vv[k][1] for k in face)-min(vv[k][1] for k in face)<.012:ff.append(face)
 mesh('AstraChar2_R2_HairRoots',vv,ff,mats[0])
 buckets=[[] for m in mats]
 for i in range(5200):
  s=1 if i%2 else -1
  rootx=s*rng.uniform(.001,.122);startx=rootx;startz=hairline(rootx)+rng.uniform(.001,.043)
  if i<2200:startx=s*rng.uniform(.001,.030);startz=rng.uniform(3.135,3.200)
  endx=s*min(.174,abs(rootx)+rng.uniform(.035,.12));endz=hairline(endx)-rng.uniform(.0,.045)
  if i<2200:endx=s*rng.uniform(.115,.174);endz=rng.uniform(3.0,3.14)
  path=[];segments=[]
  for j in range(27):
   t=j/26;x=startx+(endx-startx)*(t*t*(3-2*t))
   z=startz*(1-t)+endz*t+.047*math.sin(math.pi*t)
   z=min(z,3.0+.205*math.sqrt(max(0,1-(x/.180)**2))-.002)
   yy=surf(x,z);offset=.0015+.004*math.sin(math.pi*t)+rng.uniform(0,.00025)
   point=(x,yy-offset,z) if yy is not None else None
   if point is None or (path and (Vector(point)-Vector(path[-1])).length>.015):
    if len(path)>=4:segments.append(path)
    path=[]
   if point is not None:path.append(point)
  if len(path)>=4:segments.append(path)
  buckets[rng.choices(range(4),[2,5,5,2])[0]].extend(segments)
 for i,paths in enumerate(buckets):strands('AstraChar2_R2_HairFibers_'+str(i),paths,mats[i],.000095)
 # Fine wisps overlap the forehead, with tapered ends rather than a hard cap border.
 paths=[]
 for i in range(260):
  x=rng.uniform(-.12,.12);h=hairline(x);path=[]
  for j in range(13):
   t=j/12;xx=x+(1 if x>0 else -1)*.005*t;z=h+.014*(1-t)-rng.uniform(.003,.010)*t
   yy=surf(xx,z)
   if yy is None or (path and abs(yy-.0017-path[-1][1])>.012):
    if len(path)>=4:paths.append(path)
    path=[]
   else:path.append((xx,yy-.0017,z))
  if len(path)>=4:paths.append(path)
 strands('AstraChar2_R2_HairlineWisps',paths,mats[2],.00006)

def skin():
 m=bpy.data.objects['char1'].data.materials[2];n=m.node_tree.nodes;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
 bs.inputs['Subsurface Weight'].default_value=.24;bs.inputs['Subsurface Scale'].default_value=.0015
 bs.inputs['Subsurface Radius'].default_value=(1,.36,.17)
 # Modify packed maps in their existing UV registration, retaining physically small relief.
 for key in ['basecolor','normal','orm','emission']:
  node=n.get('AstraChar2 '+key);im=node.image;w,h=im.size;a=np.empty(w*h*4,np.float32);im.pixels.foreach_get(a);a=a.reshape(h,w,4)
  x,z=np.meshgrid((np.arange(w)+.5)/w*.32-.16,(np.arange(h)+.5)/h*.4+2.76)
  zone=np.exp(-((x/.025)**2+((z-2.889)/.025)**2))
  cool=np.exp(-((abs(x)-.087)/.029)**2-((z-2.90)/.08)**2)
  if key=='basecolor':
   a[:,:,:3]*=1+zone[:,:,None]*np.array([.09,-.08,-.06])+cool[:,:,None]*np.array([-.05,.035,.045])
  if key=='normal':
   a[:,:,:2]=.5+(a[:,:,:2]-.5)*1.55
  if key=='orm':a[:,:,1]=np.clip(a[:,:,1]+.045*np.sin(x*3761+np.sin(z*3191))*np.sin(z*4331),.27,.66)
  if key=='emission':a[:,:,:3]*=.65
  # Preserve encoded PNG samples; do not apply a second sRGB conversion.
  path=OUT/('r2_skin_'+key+'.png');png(path,a[:,:,:3])
  ni=bpy.data.images.load(str(path),check_existing=False);ni.colorspace_settings.name='sRGB' if key in ['basecolor','emission'] else 'Non-Color';ni.pack();node.image=ni
 for m in bpy.data.materials:
  if 'sclera' in m.name.lower():
   b=next((x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
   if b:b.inputs['Base Color'].default_value=(.075,.083,.066,1)

if __name__=='__main__':
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_round2_input.blend'))
 sculpt()
 from astra_char2_round2_surface import apply as surface_apply
 surface_apply();skin()
 from astra_char2_round2_skin_detail import apply
 apply();groom()
 for o in bpy.data.objects:o.animation_data_clear()
 for a in list(bpy.data.actions):bpy.data.actions.remove(a)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_character_v2_round2_work.blend'))
 if '--no-render' not in sys.argv:compare('r2_iteration11')
