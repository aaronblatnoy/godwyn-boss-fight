"""Continuous anatomical front patch in char1; existing body vertices and rig retained."""
import bpy,bmesh,math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from astra_char2_face import g,smooth

def interp(z,xs,ys):
 i=max(0,min(len(xs)-2,int(np.searchsorted(xs,z)-1)));h=xs[i+1]-xs[i];t=max(0,min(1,(z-xs[i])/h))
 m0=(ys[i+1]-ys[max(0,i-1)])/(xs[i+1]-xs[max(0,i-1)])
 m1=(ys[min(len(xs)-1,i+2)]-ys[i])/(xs[min(len(xs)-1,i+2)]-xs[i])
 return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h*m0+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h*m1

def apply():
 o=bpy.data.objects['char1'];me=o.data;mw=o.matrix_world;inv=mw.inverted()
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh();oldtree=BVHTree.FromPolygons([mw@v.co for v in em.vertices],[tuple(p.vertices) for p in em.polygons]);ev.to_mesh_clear()
 def width(z):return float(interp(z,[2.786,2.799,2.81,2.83,2.86,2.90,2.95,3.00,3.07,3.14,3.16],[.026,.043,.056,.070,.083,.098,.112,.115,.119,.116,.102]))
 def surface(x,z):
  w=width(z);u=x/w
  cy=float(interp(z,[2.786,2.799,2.82,2.846,2.875,2.91,2.95,2.98,3.025,3.09,3.16],[-.345,-.400,-.416,-.420,-.429,-.435,-.434,-.437,-.445,-.437,-.414]))
  y=-.300+(cy+.300)*max(0,1-u*u)**.54
  # Continuous malar arch, submalar hollow, temple and masseter planes.
  for s in [-1,1]:
   y-=.010*g(x,z,s*.078,2.966,.026,.018)
   y+=.0028*g(x,z,s*.080,2.925,.025,.022)
   y+=.0025*g(x,z,s*.096,3.022,.018,.024)
   y-=.004*g(x,z,s*.070,2.864,.020,.020)
   y-=.004*g(x,z,s*.055,3.018,.034,.009)
   y+=.003*g(x,z,s*.055,2.998,.030,.018)
  # Nasal dorsum, tip cartilage and alar wings.
  y-=.018*g(x,z,0,2.973,.014,.038)*smooth(2.916,2.947,z)
  y-=.028*g(x,z,0,2.927,.019,.012)
  for s in [-1,1]:
   y-=.012*g(x,z,s*.019,2.924,.010,.010)
   y+=.0018*g(x,z,s*.023,2.923,.003,.010)
  # Broad orbicularis volume, soft vermilion and philtral columns.
  y-=.002*g(x,z,0,2.877,.05,.021)
  u=x/.044;fall=max(0,1-u*u)**.65;seam=2.875+.001*math.cos(u*math.pi)-.00035*u
  top=seam+fall*(.0075+.0025*math.exp(-((abs(x)-.012)/.009)**2)-.0017*math.exp(-(x/.005)**2));bottom=seam-fall*.009
  if abs(u)<1:
   if bottom<z<top:
    t=(z-seam)/max(.0001,top-seam) if z>seam else (seam-z)/max(.0001,seam-bottom)
    y-=.0048*fall*math.sin(t*math.pi)**2
   y+=.0009*fall*math.exp(-((z-seam)/.0008)**2)
  y+=.0012*g(x,z,0,2.846,.032,.005)
  y-=.002*g(x,z,0,2.824,.036,.018)
  y+=.0010*g(x,z,0,2.900,.003,.010)
  for s in [-1,1]:y-=.00065*g(x,z,s*.004,2.900,.0025,.01)
  # Deep-set eye tissue follows each real eyeball at the margin.
  for s in [-1,1]:
   cx=s*.055;cz=2.9972+(s==1)*.0009;dx=x-cx;dz=z-cz;r2=dx*dx+dz*dz
   if r2<.036**2:
    sy=-.3848-math.sqrt(max(.000020,.034**2-r2))-.0008
    ww=(1-smooth(.021,.034,abs(dx)))*(1-smooth(.007,.022 if dz>0 else .017,abs(dz)));y=y*(1-ww)+sy*ww
   u=dx/(s*.024);crease=cz+.012+.003*max(0,1-u*u)
   y+=.0012*math.exp(-((z-crease)/.0018)**2)*max(0,1-(u/1.3)**4)
  for s in [-1,1]:
   r2=(x-s*.055)**2+(z-(2.9972+(s==1)*.0009))**2
   if r2<.034**2:y=min(y,-.3848-math.sqrt(max(.000001,.033**2-r2))-.0016)
  y+=.0005*g(x,z,.075,2.931,.025,.028)
  edge=smooth(.70,.94,abs(x)/width(z))
  if edge:
   hit=oldtree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),1)[0]
   if hit:y=y*(1-edge)+(hit.y-.0015)*edge
  return y
 def hairline(x):return float(np.interp(abs(x),[0,.025,.045,.065,.085,.105,.14],[3.121,3.125,3.11,3.075,3.025,2.97,2.91]))
 def opening(x,z):
  for s in [-1,1]:
   cx=s*.055;cz=2.9972+(s==1)*.0009;u=(x-cx)/(s*.024);zz=z-cz-.002*u
   h=(.0075 if zz>0 else .0085)*max(0,1-u*u)**.66
   if abs(u)<1 and abs(zz)<h:return True
   if ((x-s*.0145)/.0053)**2+((z-2.918)/.0023)**2<1:return True
  return False
 bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();deform=bm.verts.layers.deform.verify();head=o.vertex_groups['Head'].index
 # Face-only deletion leaves original vertex indices, UV0, groups, and all cloth intact.
 old=[]
 for f in bm.faces:
  p=mw@f.calc_center_median();x,y,z=p
  if f.material_index in (1,4):continue
  if 2.791<z<min(3.163,hairline(x)+.003) and y<-.285 and abs(x)<width(z)*.90:old.append(f)
 bmesh.ops.delete(bm,geom=old,context='FACES_ONLY')
 nx=256;nz=440;grid=[]
 for j in range(nz+1):
  z=2.786+(3.16-2.786)*j/nz;w=width(z);row=[]
  for i in range(nx+1):
   x=w*(-1+2*i/nx);y=surface(x,z);v=bm.verts.new(inv@Vector((x,y,z)));v[deform][head]=1;row.append(v)
  grid.append(row)
 for j in range(nz):
  for i in range(nx):
   vv=[grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]];p=sum((mw@v.co for v in vv),Vector())/4
   if opening(p.x,p.z) or p.z>hairline(p.x)+.008:continue
   f=bm.faces.new(vv);f.material_index=2;f.smooth=True
 bm.normal_update();bm.to_mesh(me);bm.free();me.update()
 # Reset affected custom normals so surface curvature supplies the shading normals.
 cn=[tuple(n.vector) for n in me.corner_normals]
 for f in me.polygons:
  if f.material_index==2:
   f.use_smooth=True
   for li in f.loop_indices:cn[li]=(0,0,0)
 if me.has_custom_normals:me.normals_split_custom_set(cn)
 # Broader eyeball curvature keeps the inner corners seated without circular socket craters.
 for ob in bpy.data.objects:
  if ob.name.startswith('AstraChar2_Eyeball_'):
   pts=[ob.matrix_world@v.co for v in ob.data.vertices];center=Vector([(min(p[i] for p in pts)+max(p[i] for p in pts))/2 for i in range(3)]);iv=ob.matrix_world.inverted()
   for v,p in zip(ob.data.vertices,pts):q=(p-center)*(.033/.0248)+center;q.y+=.0082;v.co=iv@q
  if ob.name.startswith(('AstraChar2_Iris_','AstraChar2_Pupil_','AstraChar2_Cornea_')):
   pts=[ob.matrix_world@v.co for v in ob.data.vertices];cx=(min(p.x for p in pts)+max(p.x for p in pts))/2;cz=(min(p.z for p in pts)+max(p.z for p in pts))/2;iv=ob.matrix_world.inverted()
   for v,p in zip(ob.data.vertices,pts):
    r2=(p.x-cx)**2+(p.z-cz)**2;offset=p.y-(-.393-math.sqrt(max(.000001,.0248**2-r2)));p.y=-.3848-math.sqrt(max(.000001,.033**2-r2))+offset;v.co=iv@p
 # Locate existing brows and lacrimal tissue on the replacement surface.
 for ob in bpy.data.objects:
  if ob.name.startswith(('AstraChar2_Eyebrows_','AstraChar2_Wetline_','AstraChar2_Lashes_')):
   iv=ob.matrix_world.inverted()
   for v in ob.data.vertices:
    p=ob.matrix_world@v.co
    if ob.name.startswith(('AstraChar2_Wetline_','AstraChar2_Lashes_')):
     cz=2.9972+(ob.name.endswith('_R'))*.0009;p.z=cz+(p.z-cz)*1.28
    p.y=surface(p.x,p.z)-.00055;v.co=iv@p
  if ob.name.startswith('AstraChar2_Nostril_'):
   s=-1 if ob.name.endswith('_L') else 1;target=Vector((s*.0145,surface(s*.0145,2.918)+.006,2.918));center=sum((ob.matrix_world@v.co for v in ob.data.vertices),Vector())/len(ob.data.vertices);iv=ob.matrix_world.inverted()
   for v in ob.data.vertices:p=ob.matrix_world@v.co;v.co=iv@(p+target-center)
 o['round2_front_patch']='Continuous grid, 257 by 441 vertices, openings for eyes/nostrils; Head weights, same char1 object and material slots. Body and cloth unmodified.'
 print('CONTINUOUS FACE',len(me.vertices),len(me.polygons),flush=True)
