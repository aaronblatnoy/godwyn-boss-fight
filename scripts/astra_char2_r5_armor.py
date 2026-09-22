"""Clean closed collar, cuirass and layered shoulder plates; geometry only."""
import bpy,math,numpy as np
from mathutils import Vector
from astra_char2_r5_geometry import mesh,bind,torso_weights,solidify,tube
PZ=[1.98,2.06,2.20,2.36,2.47,2.56,2.62,2.67]
PX=[.225,.231,.251,.281,.288,.273,.190,.103]
PF=[.235,.251,.275,.290,.290,.245,.178,.115]
PC=[-.12,-.12,-.12,-.115,-.115,-.12,-.16,-.195]
def chest(x,z):
 w=float(np.interp(z,PZ,PX));r=float(np.interp(z,PZ,PF));cy=float(np.interp(z,PZ,PC));return cy-r*math.sqrt(max(0,1-(x/w)**2))-.008*math.exp(-(x/.035)**2)
def bevel(o,width=.002):
 bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Rounded forged edge','BEVEL');mod.width=width;mod.segments=3;mod.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=mod.name)
def build(slots):
 n=192;nz=100;v=[];f=[]
 for z in np.linspace(PZ[0],PZ[-1],nz):
  w=float(np.interp(z,PZ,PX));rf=float(np.interp(z,PZ,PF));cy=float(np.interp(z,PZ,PC))
  for i in range(n):
   a=i*math.tau/n;x=w*math.sin(a);co=math.cos(a);y=cy-rf*co
   if co>0:y-=.008*math.exp(-(x/.035)**2)*co**4
   v.append((x,y,z))
 for j in range(nz-1):
  for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 plate=mesh('AstraChar2_R5_Cuirass',v,f,slots,0);solidify(plate,.006);bevel(plate,.0015);bind(plate,torso_weights)
 # Rising hollow gorget with a softly lowered front, following the neck graft.
 n=160;rows=24;v=[];f=[]
 for j in range(rows):
  t=j/(rows-1)
  for i in range(n):
   a=i*math.tau/n;co=math.cos(a);z=2.625+t*(.121-.030*max(co,0)**10);rx=.14*(1-t)+.093*t;ry=.160*(1-t)+.108*t;cy=-.178-.018*t
   v.append((rx*math.sin(a),cy-ry*co,z))
 for j in range(rows-1):
  for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 collar=mesh('AstraChar2_R5_Gorget',v,f,slots,0);solidify(collar,.005);bevel(collar,.0015);bind(collar,lambda p:{'Spine':1})
 rim=[v[(rows-1)*n+i] for i in range(n)]+[v[(rows-1)*n]];ob=tube('AstraChar2_R5_GorgetRim',rim,.0025,slots);bind(ob,lambda p:{'Spine':1})
 # Forged clavicle mantle bridges the neck collar to the shoulder caps.
 v=[];f=[];n=160;rows=28
 for j in range(rows):
  t=j/(rows-1)
  for i in range(n):
   a=i*math.tau/n;v.append(((.09+.27*t)*math.sin(a),-.19-(.108+.095*t)*math.cos(a),2.710-t*(.060+.120*(1-abs(math.sin(a)))*max(0,math.cos(a))**.1+.04*max(-math.cos(a),0)**2)+.010*math.sin(math.pi*t)))
 for j in range(rows-1):
  for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 mantle=mesh('AstraChar2_R5_ClavicleMantle',v,f,slots,0);solidify(mantle,.007);bevel(mantle,.002);bind(mantle,lambda p:{'Spine':1})
 for side,label,bone in [(1,'L','LeftArm'),(-1,'R','RightArm')]:
  # Continuous domed pauldron, then three overlapping upper-arm lames.
  v=[];f=[];nr=42;na=128
  for j in range(nr):
   polar=.012+j/(nr-1)*1.84
   for i in range(na):
    a=i*math.tau/na;v.append((side*(.330+.178*math.sin(polar)*math.cos(a)),-.173+.210*math.sin(polar)*math.sin(a),2.586+.145*math.cos(polar)))
  for j in range(nr-1):
   for i in range(na):f.append((j*na+i,j*na+(i+1)%na,(j+1)*na+(i+1)%na,(j+1)*na+i))
  f.append(tuple(reversed(range(na))));pa=mesh('AstraChar2_R5_Pauldron_'+label,v,f,slots,0);solidify(pa,.006);bevel(pa,.0017);bind(pa,lambda p,b=bone:{b:1})
  rim=v[-na:]+[v[-na]];ob=tube('AstraChar2_R5_PauldronRim_'+label,rim,.003,slots);bind(ob,lambda p,b=bone:{b:1})
  arm=bpy.data.objects['Armature'];start=arm.matrix_world@arm.data.bones[bone].head_local;fore=('LeftForeArm' if side>0 else 'RightForeArm');end=arm.matrix_world@arm.data.bones[fore].head_local;direction=(end-start).normalized();a=direction.cross(Vector((0,1,0))).normalized();b=direction.cross(a)
  for layer in range(3):
   vs=[];fs=[];n=96;rows=12;t0=.28+.19*layer;t1=t0+.25
   for j in range(rows):
    t=t0+(t1-t0)*j/(rows-1);center=start.lerp(end,t);radius=.147-.030*t+.005*layer
    for i in range(n):
     ph=i*math.tau/n;p=center+a*(radius*math.cos(ph))+b*(radius*.92*math.sin(ph));vs.append(tuple(p))
   for j in range(rows-1):
    for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
   ob=mesh(f'AstraChar2_R5_UpperArm_{label}_{layer}',vs,fs,slots);solidify(ob,.004);bevel(ob,.0013);bind(ob,lambda p,bn=bone:{bn:1})
 # Sacred sun boss at the breastplate center; relief exists in clay.
 cx=0;cz=2.46;n=96;v=[(0,chest(0,cz)-.008,cz)];f=[]
 for ring in range(1,10):
  r=.047*ring/9
  for i in range(n):
   a=i*math.tau/n;x=r*math.cos(a);z=cz+r*math.sin(a);y=chest(x,z)-.005-.008*math.sqrt(max(0,1-(r/.047)**2));v.append((x,y,z))
 for i in range(n):f.append((0,1+i,1+(i+1)%n))
 for ring in range(8):
  for i in range(n):f.append((1+ring*n+i,1+ring*n+(i+1)%n,1+(ring+1)*n+(i+1)%n,1+(ring+1)*n+i))
 ob=mesh('AstraChar2_R5_SacredEmblem',v,f,slots);solidify(ob,.003);bind(ob,torso_weights)
 for i in range(16):
  angle=i*math.tau/16;pts=[]
  for j in range(24):
   t=j/23;r=.045+.039*t;ang=angle+.06*math.sin(t*math.pi);x=r*math.cos(ang);z=cz+r*math.sin(ang);pts.append((x,chest(x,z)-.006,z))
  ob=tube('AstraChar2_R5_SunRay_'+str(i),pts,np.linspace(.0026,.0005,24),slots);bind(ob,torso_weights)
 return plate,collar
