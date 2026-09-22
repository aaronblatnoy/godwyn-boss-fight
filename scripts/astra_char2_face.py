"""Local facial refinement. Re-running restores the retained base mesh and deletes owned additions."""
import bpy,bmesh,math,random,numpy as np
from mathutils import Vector
from pathlib import Path
from astra_char2_skin import UV,lip_bounds,png,srgb
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';PREFIX='AstraChar2_'
def g(x,z,cx,cz,sx,sz):return math.exp(-((x-cx)/sx)**2-((z-cz)/sz)**2)
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def eye(s):return (s*.055, -.393, 2.952+(s==1)*.0008)
def eye_edge(s,u,upper=True):
 cx,cy,cz=eye(s);x=cx+s*.024*u;z=cz+.0018*u+((.0048 if upper else -.0055)*max(0,1-u*u)**.66)
 y=cy-math.sqrt(max(.00001,.0248**2-(x-cx)**2-(z-cz)**2))-.0006
 return Vector((x,y,z))
def material(name,col,rough=.4,metal=0):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;m.node_tree.nodes.clear();n=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');o=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(n.outputs[0],o.inputs['Surface']);n.inputs['Base Color'].default_value=(*col,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;return m,n

def bind(o):
 arm=bpy.data.objects['Armature'];o.parent=arm;o.matrix_parent_inverse=arm.matrix_world.inverted();vg=o.vertex_groups.new(name='Head');vg.add(list(range(len(o.data.vertices))),1,'REPLACE');mod=o.modifiers.new('Armature','ARMATURE');mod.object=arm
 for f in o.data.polygons:f.use_smooth=True
 return o

def mesh(name,vs,fs,mat,uvs=None):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);me.materials.append(mat)
 if uvs:
  uv=me.uv_layers.new(name='UVMap')
  for p in me.polygons:
   for i in p.loop_indices:uv.data[i].uv=uvs[me.loops[i].vertex_index]
 return bind(o)

def strands(name,paths,mat,radius):
 vs=[];fs=[];sides=5
 for path in paths:
  start=len(vs)
  for j,p in enumerate(path):
   p=Vector(p);t=Vector(path[min(j+1,len(path)-1)])-Vector(path[max(j-1,0)]);t.normalize();a=t.cross(Vector((0,1,0))).normalized();b=t.cross(a).normalized();r=radius*(.9*(1-j/(len(path)-.3))+.1)
   for k in range(sides):vs.append(tuple(p+r*(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))))
  for j in range(len(path)-1):
   for k in range(sides):a=start+j*sides+k;b=start+j*sides+(k+1)%sides;fs.append((a,b,b+sides,a+sides))
 return mesh(name,vs,fs,mat)

def sculpt():
 o=bpy.data.objects['char1'];base=bpy.data.meshes.get('AstraChar2 retained original char1')
 if base is None:base=o.data.copy();base.name='AstraChar2 retained original char1';base.use_fake_user=True
 old=o.data;o.data=base.copy();o.data.name='AstraChar2 refined char1'
 if old!=base and old.users==0:bpy.data.meshes.remove(old)
 for ob in list(bpy.data.objects):
  if ob.name.startswith(PREFIX):
   me=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
   if me.users==0:bpy.data.meshes.remove(me)
 bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table();mw=o.matrix_world
 region=[]
 # Recover actual skin from the shared baked albedo, including forehead faces
 # incorrectly carried in the old gold slot. The blue/red ratio separates skin
 # from blonde hair without imposing a rectangular facial mask.
 mat=o.data.materials[3];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 im=bs.inputs['Base Color'].links[0].from_node.image;pix=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(pix);pix=pix.reshape(im.size[1],im.size[0],4)
 olduv=bm.loops.layers.uv.get(o.data.uv_layers.active.name)
 for f in bm.faces:
  p=mw@f.calc_center_median();x,y,z=p
  fix=(abs(x)<.078 and 2.810<z<3.092 and y<-.39)
  if 2.775<z<3.15 and y<-.32 and abs(x)<.14:
   uv=sum((loop[olduv].uv for loop in f.loops),Vector((0,0)))/len(f.loops)
   rgb=pix[min(im.size[1]-1,max(0,int(uv.y*im.size[1]))),min(im.size[0]-1,max(0,int(uv.x*im.size[0]))),:3]
   if rgb[2]>.60*rgb[0] and rgb[1]>.64*rgb[0]:fix=True
  if (f.material_index==2 and z>2.775 and y<-.30) or fix:
   f.material_index=2;region.append(f)
 edges=list({e for f in region for e in f.edges});bmesh.ops.subdivide_edges(bm,edges=edges,cuts=7,use_grid_fill=True,smooth=.8,use_smooth_even=True)
 bm.verts.ensure_lookup_table();selected={v for f in bm.faces if f.material_index==2 for v in f.verts if (mw@v.co).z>2.785 and (mw@v.co).y<-.33}
 # Relax tessellation while preserving silhouette and UVs; no voxel remesh of a skinned asset.
 interior=[v for v in selected if all(e.other_vert(v) in selected for e in v.link_edges)]
 for k in range(40):bmesh.ops.smooth_vert(bm,verts=interior,factor=.45,use_axis_x=True,use_axis_y=True,use_axis_z=True)
 inv=mw.inverted()
 for v in selected:
  p=mw@v.co;x,y,z=p;front=smooth(-.33,-.395,y) if False else smooth(-.33,-.395,y)
  # Shape changes are millimetric, registered to existing head volume.
  d=0
  for s in [-1,1]:
   d-=.0060*g(x,z,s*.066,2.929,.032,.021)
   d-=.0085*g(x,z,s*.055,2.936,.032,.019) # malar prominence
   d+=.0040*g(x,z,s*.078,2.890,.024,.026) # submalar hollow
   d-=.0028*g(x,z,s*.060,2.976,.037,.010) # supraorbital arch
   d+=.0010*g(x,z,s*.052,2.957,.026,.014)
   u=(x-s*.055)/.025
   if abs(u)<1.18:
    crease_z=2.952+.012+.004*max(0,1-u*u)
    d+=.0017*math.exp(-((z-crease_z)/.0015)**2)*max(0,1-(u/1.18)**4) # deep orbit
   d+=.0010*g(x,z,s*.021,2.899,.005,.017) # alar crease
   d-=.0040*g(x,z,s*.015,2.887,.008,.007) # nose wings
   d+=.0030*g(x,z,s*.012,2.882,.004,.0028) # nostril recess
  d-=.002*g(x,z,0,2.813,.027,.014) # chin plane
  d+=.002*g(x,z,0,2.828,.028,.004) # labiomental sulcus
  d-=.0015*g(x,z,0,2.914,.009,.025) # defined bridge
  d-=.0020*g(x,z,0,2.894,.011,.008) # tip cartilage
  # Cupid's bow, lip pillows, vermilion edge, mouth seam and philtrum.
  if abs(x)<.043 and 2.832<z<2.875:
   seam,top,bottom=map(float,lip_bounds(np.array(x)))
   fall=max(0,1-(x/.038)**2)**.65
   if bottom<z<top:
    if z>seam:t=(z-seam)/max(.0001,top-seam);d-=fall*(.0004+.0043*math.sin(t*math.pi))
    else:t=(seam-z)/max(.0001,seam-bottom);d-=fall*(.0004+.0050*math.sin(t*math.pi))
   d+=.0020*fall*math.exp(-((z-seam)/.00065)**2)
   d+=.0015*g(x,z,0,2.869,.0028,.009)
   for s in [-1,1]:d-=.0014*g(x,z,s*.004,2.867,.002,.009)
  d+=.0006*g(x,z,.04,2.917,.018,.023)-.00045*g(x,z,-.05,2.982,.028,.02)
  y+=d*front
  # Replace the inherited broad triangular forehead undulations with a continuous
  # cranial arc. Preserve hairline/temple boundaries through a smooth falloff.
  fw=smooth(2.985,3.010,z)*(1-smooth(3.085,3.115,z))*(1-smooth(.085,.120,abs(x)))
  fy=-.444+.095*(z-3.0)+4.2*x*x+100*x**4
  y=y*(1-fw)+fy*fw
  # Sculpt eyelid aperture: interior retreats behind an actual eyeball;
  # its edge follows the sphere, and an outer annulus blends back into the face.
  for s in [-1,1]:
   cx,cy,cz=eye(s);u=(x-cx)/(s*.024);zz=z-cz-.0018*u
   height=(.0048 if zz>=0 else .0055)*max(0,1-u*u)**.66
   if abs(u)<1.42 and abs(zz)<.036:
    inside=height-abs(zz)
    corner=(1-abs(u))*.016
    dist=min(inside,corner)
    radius2=(x-cx)**2+(z-cz)**2
    sphere=cy-math.sqrt(max(.000003,.0248**2-radius2))
    if radius2<.0258**2:
     if dist>=0:target=sphere-.00065+.020*smooth(0,.0017,dist)
     else:target=min(y,sphere-.0010)
     blend=1-smooth(.0240,.0258,math.sqrt(radius2))
     y=y*(1-blend)+target*blend
  v.co=inv@Vector((x*(1+.12*g(x,z,0,2.811,.070,.024)),y,z))
 bm.normal_update();bm.to_mesh(o.data);bm.free();o.data.update()
 # Imported custom corner normals must not survive a sculpt at their old directions.
 skinverts={vi for f in o.data.polygons if f.material_index==2 for vi in f.vertices}
 for e in o.data.edges:
  if all(i in skinverts for i in e.vertices):e.use_edge_sharp=False
 cn=[tuple(n.vector) for n in o.data.corner_normals]
 for f in o.data.polygons:
  if f.material_index==2:
   f.use_smooth=True
   for li in f.loop_indices:cn[li]=(0,0,0)
 if o.data.has_custom_normals:o.data.normals_split_custom_set(cn)
 o.data.update()
 # Preserve existing UV layers. Add a dedicated high-resolution face atlas as UV1.
 uv=o.data.uv_layers.get(UV) or o.data.uv_layers.new(name=UV)
 for f in o.data.polygons:
  for li in f.loop_indices:
   p=mw@o.data.vertices[o.data.loops[li].vertex_index].co
   uv.data[li].uv=((p.x+.16)/.32,(p.z-2.76)/.40) if f.material_index==2 else (-2,-2)
  if f.material_index==2:f.use_smooth=True
 # Actual nostril openings with recessed tissue liners, not decals on the tip.
 for side in [-1,1]:
  xx=side*.0118;zz=2.8825
  ok,loc,nn,fi=o.ray_cast(inv@Vector((xx,-.60,zz)),Vector((0,1,0)))
  yy=(mw@loc).y if ok else -.460
  o['astra_char2_nostril_'+str(side)]=[xx,yy+.004,zz]
 bm=bmesh.new();bm.from_mesh(o.data);holes=[]
 for f in bm.faces:
  if f.material_index!=2:continue
  p=mw@f.calc_center_median()
  if p.y<-.435 and ((abs(p.x)-.0118)/.0040)**2+((p.z-2.8825)/.0018)**2<1:holes.append(f)
 bmesh.ops.delete(bm,geom=holes,context='FACES');bm.normal_update();bm.to_mesh(o.data);bm.free();o.data.update()
 print('FACE SCULPT',len(o.data.vertices),'vertices; local refined vertices',len(selected),flush=True)
 return o

def eyes_and_hair():
 sclera,bs=material('AstraChar2 living sclera',(.13,.135,.115),.30);bs.inputs['Subsurface Weight'].default_value=.12;bs.inputs['Subsurface Scale'].default_value=.0005
 iris,ib=material('AstraChar2 hazel green iris',(.13,.14,.055),.30)
 N=768;H=128;u,v=np.meshgrid(np.arange(N)/N,np.arange(H)/(H-1));rng=np.random.default_rng(451)
 radial=.5+.22*np.sin(u*math.tau*127+np.sin(v*19+u*73))+.14*np.sin(u*math.tau*249+v*11)+.1*np.sin(u*math.tau*53-v*23)
 green=np.array([.075,.095,.043]);amber=np.array([.15,.090,.026]);a=np.clip(1-v*2.3,0,1)[:,:,None];col=green*(1-a)+amber*a;col=col*(.62+radial[:,:,None]*.72);col*=1-.70*np.clip((v-.85)/.15,0,1)[:,:,None]
 path=OUT/'iris_hazel_768.png';png(path,srgb(col))
 if 'AstraChar2 Hazel radial stroma' in bpy.data.images:bpy.data.images.remove(bpy.data.images['AstraChar2 Hazel radial stroma'])
 im=bpy.data.images.load(str(path),check_existing=False);im.name='AstraChar2 Hazel radial stroma';im.pack();t=iris.node_tree.nodes.new('ShaderNodeTexImage');t.image=im;iris.node_tree.links.new(t.outputs['Color'],ib.inputs['Base Color'])
 pupil,pb=material('AstraChar2 pupil',(.0012,.0015,.0010),.2)
 cornea,cb=material('AstraChar2 cornea',(.98,.99,1),.035);cb.inputs['Transmission Weight'].default_value=1;cb.inputs['IOR'].default_value=1.376
 wet,wb=material('AstraChar2 lacrimal wetline',(.33,.10,.074),.15);wb.inputs['Coat Weight'].default_value=.65;wb.inputs['Subsurface Weight'].default_value=.25;wb.inputs['Subsurface Scale'].default_value=.00035
 brow,bb=material('AstraChar2 warm blonde eyebrows',(.20,.105,.030),.48);bb.inputs['Coat Weight'].default_value=.12
 lash,lb=material('AstraChar2 blonde lashes',(.105,.058,.023),.40)
 nostril,nb=material('AstraChar2 nostril interior',(.095,.025,.015),.52)
 for s in [-1,1]:
  cx,cy,cz=eye(s);tag='L' if s<0 else 'R'
  bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=40,radius=.0248,location=(cx,cy,cz));o=bpy.context.object;o.name=PREFIX+'Eyeball_'+tag;o.data.materials.append(sclera);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bind(o)
  # Eye inserts are world-space meshes so their head weights transform identically.
  for name,r0,r1,mat,offset in [('Iris',.0030,.0076,iris,-.00018),('Pupil',0,.00305,pupil,-.00025),('Cornea',0,.0080,cornea,-.00052)]:
   vs=[];fs=[];uvs=[];rings=12;seg=128
   for j in range(rings+1):
    r=r0+(r1-r0)*j/rings
    for k in range(seg+1):
     ang=k/seg*math.tau;x=cx+r*math.cos(ang);z=cz+r*math.sin(ang);y=cy-math.sqrt(.0248**2-r*r)+offset
     if name=='Cornea':y-=.0010*(1-(r/r1)**2)
     vs.append((x,y,z));uvs.append((k/seg,j/rings))
   for j in range(rings):
    for k in range(seg):a=j*(seg+1)+k;fs.append((a,a+seg+1,a+seg+2,a+1))
   mesh(PREFIX+name+'_'+tag,vs,fs,mat,uvs)
  wetpaths=[]
  for upper in [True,False]:wetpaths.append([eye_edge(s,-.98+1.96*k/64,upper) for k in range(65)])
  strands(PREFIX+'Wetline_'+tag,wetpaths,wet,.00042)
  p=eye_edge(s,-.91,False);bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=p);o=bpy.context.object;o.name=PREFIX+'TearCorner_'+tag;o.scale=(.0017,.001,.001);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(wet);bind(o)
  # Individual tapered brow hairs with slight irregularity; no painted black strips.
  rng=random.Random(82+s);paths=[]
  for i in range(430):
   u=rng.random();x=s*(.027+u*.065);z=2.975+.006*math.sin(u*math.pi)-.003*u+rng.uniform(-.0024,.0024);y=-.444+((abs(x)/.11)**2)*.041
   # Raycast onto the sculpt gives proper contact on the nonplanar brow ridge.
   ob=bpy.data.objects['char1'];inv=ob.matrix_world.inverted();ok,loc,n,fi=ob.ray_cast(inv@Vector((x,-.6,z)),Vector((0,1,0)))
   if ok:y=(ob.matrix_world@loc).y-.0004
   length=rng.uniform(.003,.006);paths.append([(x+s*length*t*.65,y-.00065*math.sin(t*math.pi),z+length*t*(1-u*.75)) for t in [0,.25,.5,.75,1]])
  strands(PREFIX+'Eyebrows_'+tag,paths,brow,.000095)
  paths=[]
  for upper,count in [(True,54),(False,27)]:
   for i in range(count):
    u=-.84+1.77*i/(count-1);p=eye_edge(s,u,upper);length=rng.uniform(.0018,.0038)*(1 if upper else .65)
    paths.append([tuple(p+Vector((s*u*length*t,-length*.65*t,(1 if upper else -1)*length*(t*t*.65)))) for t in [0,.25,.5,.75,1]])
  strands(PREFIX+'Lashes_'+tag,paths,lash,.000075)
  # Recessed dark lumen under each modeled alar wing.
  bpy.ops.mesh.primitive_uv_sphere_add(segments=28,ring_count=16,radius=1,location=bpy.data.objects['char1']['astra_char2_nostril_'+str(s)]);o=bpy.context.object;o.name=PREFIX+'Nostril_'+tag;o.scale=(.0050,.003,.0030);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(nostril);bind(o)

def proportion_warp(z):
 if z<=2.79:return z
 if z<2.99:return 2.79+(z-2.79)*1.18
 return z+.036*(1-smooth(2.99,3.11,z))
def approved_proportions():
 o=bpy.data.objects['char1'];mw=o.matrix_world;inv=mw.inverted()
 ids={i for f in o.data.polygons if f.material_index==2 for i in f.vertices}
 for i in ids:
  v=o.data.vertices[i];p=mw@v.co
  if p.z>2.79 and p.y<-.32:
   weight=(1-smooth(.085,.13,abs(p.x)))*smooth(-.32,-.39,p.y)
   p.z+=(proportion_warp(p.z)-p.z)*weight
   p.z+=.009*g(p.x,p.z,0,2.909,.027,.025)*weight;v.co=inv@p
 o.data.update()
 for ob in bpy.data.objects:
  if not ob.name.startswith(PREFIX):continue
  # Preserve optical geometry as spheres and round irises; translate eye units.
  if any(k in ob.name for k in ['Eyeball','Iris_','Pupil_','Cornea_']):
   side=-1 if ob.name.endswith('_L') else 1;cz=eye(side)[2];ob.location.z+=proportion_warp(cz)-cz
  else:
   mw=ob.matrix_world;inv=mw.inverted()
   for v in ob.data.vertices:
    p=mw@v.co;p.z=proportion_warp(p.z)
    if 'Nostril' in ob.name:p.z+=.009*g(p.x,p.z,0,2.909,.027,.025)
    v.co=inv@p
   ob.data.update()
def apply_face():
 sculpt();eyes_and_hair();approved_proportions();bpy.context.view_layer.update()
