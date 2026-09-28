"""Clean continuous skull/face/neck, explicit orbital and oral loops. Geometry only."""
import bpy,bmesh,math,numpy as np
from mathutils import Vector
from astra_char2_r5_geometry import mesh,bind,head_weights,sphere,solidify
Z=np.array([2.61,2.65,2.70,2.745,2.77,2.785,2.80,2.825,2.85,2.89,2.925,2.95,2.98,3.01,3.05,3.09,3.115,3.135,3.15,3.16])
W=np.array([.079,.075,.069,.066,.066,.066,.072,.083,.090,.091,.093,.095,.096,.097,.099,.106,.108,.087,.048,.001])
F=np.array([-.258,-.263,-.275,-.282,-.312,-.357,-.378,-.379,-.387,-.384,-.372,-.370,-.359,-.379,-.373,-.351,-.315,-.279,-.235,-.20])
BACK=np.array([-.095,-.095,-.098,-.105,-.12,-.125,-.123,-.120,-.115,-.105,-.094,-.086,-.080,-.078,-.080,-.092,-.119,-.155,-.202,-.25])
def hermite(z,ys):
 i=max(0,min(len(Z)-2,int(np.searchsorted(Z,z)-1)));h=Z[i+1]-Z[i];t=(z-Z[i])/h
 slope=np.gradient(ys,Z);v=(2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h*slope[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h*slope[i+1]
 if z>3.035:
  dome=math.sqrt(max(0,1-(max(0,z-3.07)/.09)**2));k=min(1,(z-3.035)/.05);k=k*k*(3-2*k)
  d=.111*dome if ys is W else (-.25-.11*dome if ys is F else -.25+.17*dome)
  v=v*(1-k)+d*k
 return v
def gauss(x,z,cx,cz,rx,rz):return math.exp(-((x-cx)/rx)**2-((z-cz)/rz)**2)
def front(x,z):
 width=max(.002,hermite(z,W));co=max(0,1-(x/width)**2)**.5;cy=-.25 if z>2.79 else float(np.interp(z,[2.61,2.79],[-.17,-.25]));y=cy+(hermite(z,F)-cy)*co**.85
 relief=0
 for side in [-1,1]:
  relief-=.021*gauss(x,z,side*.075,2.943,.028,.021)
  relief+=.014*gauss(x,z,side*.071,2.915,.026,.024)
  relief+=.008*gauss(x,z,side*.096,3.002,.017,.030)
  relief-=.010*gauss(x,z,side*.085,2.823,.023,.025)
  relief-=.008*gauss(x,z,side*.053,3.002,.034,.015)
  relief+=.006*gauss(x,z,side*.053,2.975,.027,.015)
  relief-=.027*gauss(x,z,side*.021,2.905,.013,.013)
  relief+=.003*gauss(x,z,side*.030,2.905,.005,.014)
  relief-=.0024*gauss(x,z,side*.0055,2.884,.0028,.009)
 relief-=.004*gauss(x,z,0,3.0,.022,.017)
 if 2.880<z<3.010:
  nz=np.array([2.880,2.890,2.897,2.903,2.910,2.917,2.925,2.937,2.953,2.974,2.995,3.010])
  ny=np.array([-.388,-.401,-.426,-.443,-.451,-.451,-.445,-.431,-.409,-.382,-.379,-.379])
  k=max(0,min(len(nz)-2,int(np.searchsorted(nz,z)-1)));h=nz[k+1]-nz[k];tt=(z-nz[k])/h;sl=np.gradient(ny,nz)
  target=(2*tt**3-3*tt*tt+1)*ny[k]+(tt**3-2*tt*tt+tt)*h*sl[k]+(-2*tt**3+3*tt*tt)*ny[k+1]+(tt**3-tt*tt)*h*sl[k+1]
  radius=float(np.interp(z,[2.88,2.903,2.917,2.947,2.98,3.01],[.007,.014,.018,.012,.011,.02]))
  relief+=(target-hermite(z,F))*math.exp(-(x/radius)**2)
 relief-=.010*gauss(x,z,0,2.804,.038,.019)
 relief+=.0025*gauss(x,z,0,2.825,.030,.006)
 u=x/.039
 if abs(u)<1.4:
  env=max(0,1-u*u)**.9;seam=2.863-.0012*u*u-.0004*math.exp(-(u/.23)**2)
  upper=seam+.0055+.0020*math.exp(-((abs(u)-.26)/.16)**2)
  relief-=.008*env*math.exp(-((z-upper)/.0050)**2)
  relief-=.011*env*math.exp(-((z-(seam-.0060))/.0060)**2)
  relief+=.002*env*math.exp(-((z-seam)/.00085)**2)
 if z<2.80:
  for side in [-1,1]:relief-=.004*gauss(x,z,side*(.035+.030*(z-2.66)/.14),2.73,.008,.10)
 # Slight anatomical asymmetry, far below expression-changing scale.
 relief+=.0008*gauss(x,z,.066,2.912,.032,.047)-.0005*gauss(x,z,-.04,3.025,.06,.04)
 return y+relief*min(1,max(0,co*4))

def add_opening(bm,cx,cz,rx,rz,kind):
 doomed=[]
 for f in bm.faces:
  c=f.calc_center_median()
  if c.y<-.25 and ((c.x-cx)/rx)**2+((c.z-cz)/rz)**2<1:doomed.append(f)
 bmesh.ops.delete(bm,geom=doomed,context='FACES_ONLY')
 boundary=[v for v in bm.verts if any(e.is_boundary for e in v.link_edges) and v.co.y<-.25 and ((v.co.x-cx)/rx)**2+((v.co.z-cz)/rz)**2<1.8]
 boundary.sort(key=lambda v:math.atan2((v.co.z-cz)/rz,(v.co.x-cx)/rx))
 angles=[math.atan2((v.co.z-cz)/rz,(v.co.x-cx)/rx) for v in boundary]
 for v,ang in zip(boundary,angles):
  x=cx+rx*math.cos(ang);z=cz+rz*math.sin(ang);v.co=(x,front(x,z),z)
 prev=boundary
 for row in range(1,13):
  t=row/12;cur=[]
  for ang in angles:
   ca,sa=math.cos(ang),math.sin(ang)
   if kind=='eye':
    ix=.0245*ca;iz=(.0075 if sa>=0 else .006)*sa+.0012*ca*(1 if cx>0 else -1)
    x=cx+(1-t)*rx*ca+t*ix;z=cz+(1-t)*rz*sa+t*iz
    inner_y=-.325-math.sqrt(max(.000001,.026**2-ix**2-iz**2))-.0012
    y=(1-t)*front(x,z)+t*inner_y
    if sa>0:y+=.0028*math.exp(-((t-.37)/.13)**2)*sa-.0017*math.exp(-((t-.82)/.18)**2)*sa
    else:y-=.0012*math.sin(t*math.pi)*(-sa)
   else:
    ix=.039*ca;iz=.00035*sa-.0012*ca*ca-.0004*math.exp(-(ca/.23)**2)
    x=cx+(1-t)*rx*ca+t*ix;z=cz+(1-t)*rz*sa+t*iz;y=front(x,z)
   cur.append(bm.verts.new((x,y,z)))
  for i in range(len(cur)):bm.faces.new((prev[i],prev[(i+1)%len(cur)],cur[(i+1)%len(cur)],cur[i]))
  prev=cur
 # Recessed closed socket/oral interior: no through-head voids.
 for t in [.3,.7,1.]:
  cur=[]
  for v in prev:
   p=v.co.copy();p.x=cx+(p.x-cx)*(.65 if t<1 else .18);p.z=cz+(p.z-cz)*(.65 if t<1 else .18);p.y+=.015 if kind=='eye' else .008;cur.append(bm.verts.new(p))
  for i in range(len(cur)):bm.faces.new((prev[i],prev[(i+1)%len(cur)],cur[(i+1)%len(cur)],cur[i]))
  prev=cur
 bm.faces.new(tuple(reversed(prev)))

def build(slots):
 n=256;nz=320;verts=[];faces=[]
 for z in np.linspace(Z[0],Z[-1],nz):
  w=max(.001,hermite(z,W));cy=-.25 if z>2.79 else float(np.interp(z,[2.61,2.79],[-.17,-.25]))
  for theta in np.linspace(-math.pi,math.pi,n,endpoint=False):
   x=w*math.sin(theta)
   if math.cos(theta)>=0:y=front(x,z)
   else:y=cy+(hermite(z,BACK)-cy)*(-math.cos(theta))
   verts.append((x,y,float(z)))
 for j in range(nz-1):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 faces.extend([tuple(reversed(range(n))),tuple((nz-1)*n+i for i in range(n))]);o=mesh('AstraChar2_R5_Head',verts,faces,slots,2)
 bm=bmesh.new();bm.from_mesh(o.data)
 for side in [-1,1]:add_opening(bm,side*.053,2.974+(.0005 if side>0 else 0),.034,.022,'eye')
 add_opening(bm,0,2.863,.047,.021,'mouth');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 # Actual nostril cavities, cut into the continuous nose surface.
 for side in [-1,1]:
  cutter=sphere('AstraChar2_R5_NostrilCutter',(side*.017,-.408,2.893),(.0055,.012,.009),[],segments=48,rings=24)
  cutter.rotation_euler.x=math.radians(-40);bpy.context.view_layer.objects.active=o;o.hide_set(False);mod=o.modifiers.new('Sculpted nostril cavity','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
 uv=o.data.uv_layers.new(name='UVMap')
 for f in o.data.polygons:
  f.material_index=2;f.use_smooth=True
  for li in f.loop_indices:
   p=o.data.vertices[o.data.loops[li].vertex_index].co;u=.5+math.atan2(p.x,-(p.y+.20))/math.tau;uv.data[li].uv=(u,(p.z-2.61)/.59)
 bind(o,head_weights)
 # Clean eyeballs; iris/cornea/lash detail is intentionally deferred until clay passes.
 for side,label in [(1,'L'),(-1,'R')]:
  name='AstraChar2_Eyeball_'+label;old=bpy.data.objects[name];eye=sphere(name,(side*.053,-.325,2.974+(.0005 if side>0 else 0)),(.026,.026,.026),list(old.data.materials));bind(eye,lambda p:{'Head':1})
  vs=[];fs=[];nr=32;na=96
  for j in range(nr):
   r=j/(nr-1)
   for k in range(na):
    a=k*math.tau/na;z=2.942+.045*r*math.sin(a);y=-.255+.023*r*math.cos(a)*(1+.12*math.sin(a));xx=.096+.010*r+.007*math.exp(-((r-.84)/.08)**2)*(1-.55*math.exp(-((a-math.pi)/.45)**2))
    yy=y+.255;zz=z-2.942
    xx-=.004*math.exp(-((yy+.003)/.012)**2-(zz/.016)**2)
    ridge=.004+.007*math.sin((zz+.025)/.050*math.pi)
    xx+=.005*math.exp(-((yy-ridge)/.0035)**2)*math.exp(-(zz/.026)**4)
    if zz>.008:xx+=.0035*math.exp(-((yy-(-.008+(zz-.008)*.25))/.003)**2)*math.exp(-((zz-.018)/.012)**2)
    xx+=.005*math.exp(-((yy+.018)/.004)**2-((zz+.006)/.007)**2)+.003*math.exp(-(yy/.012)**2-((zz+.035)/.008)**2)
    vs.append((side*xx,y,z))
  for j in range(nr-1):
   for k in range(na):fs.append((j*na+k,j*na+(k+1)%na,(j+1)*na+(k+1)%na,(j+1)*na+k))
  ear=mesh('AstraChar2_R5_Ear_'+label,vs,fs,slots,2);bm=bmesh.new();bm.from_mesh(ear.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bm.to_mesh(ear.data);bm.free();solidify(ear,.003);bind(ear,lambda p:{'Head':1})
 return o
