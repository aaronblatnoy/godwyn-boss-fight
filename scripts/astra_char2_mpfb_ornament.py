"""Small raised laurel and scroll geometry on the replacement forged plates."""
import bpy,math,numpy as np
from astra_char2_r5_geometry import mesh,bind,torso_weights
from astra_char2_r5_armor import chest

class Relief:
    def __init__(self):self.v=[];self.f=[]
    def path(self,points,r=.00085,sides=6):
        p=np.asarray(points,float);t=np.gradient(p,axis=0);t/=np.maximum(np.linalg.norm(t,axis=1,keepdims=True),1e-9)
        a=np.cross(t,[0,1,0]);a/=np.maximum(np.linalg.norm(a,axis=1,keepdims=True),1e-9);b=np.cross(t,a);ph=np.arange(sides)*math.tau/sides
        rr=np.broadcast_to(np.array(r),len(p));v=p[:,None,:]+rr[:,None,None]*(a[:,None,:]*np.cos(ph)[None,:,None]+b[:,None,:]*np.sin(ph)[None,:,None])
        off=len(self.v);self.v.extend(v.reshape(-1,3).tolist())
        for i in range(len(p)-1):
            for j in range(sides):self.f.append((off+i*sides+j,off+i*sides+(j+1)%sides,off+(i+1)*sides+(j+1)%sides,off+(i+1)*sides+j))
    def object(self,name,slots,weight):
        ob=mesh(name,self.v,self.f,slots);bind(ob,weight);ob['mpfb_forged_relief']=True;return ob

def decorate():
    slots=list(bpy.data.objects['char1'].data.materials);t=np.linspace(0,1,30);r=Relief()
    def chestpath(x,z,radius=.0008):r.path(np.stack([x,np.array([chest(a,b)-.009 for a,b in zip(x,z)]),z],1),radius)
    for side in [-1,1]:
        z=np.linspace(2.08,2.61,180);x=side*(.125+.050*np.sin((z-2.08)/.53*math.pi))
        chestpath(x,z,.0013)
        for j in range(18):
            zz=2.095+j*.028;xx=side*(.125+.05*math.sin((zz-2.08)/.53*math.pi))
            for s in [-1,1]:
                # Almond laurel outline and vein, relief rather than a printed gold patch.
                a=np.linspace(0,math.tau,42);leafx=xx+side*s*(.008*(1-np.cos(a)))+side*.004*np.sin(a)
                leafz=zz+.012*np.sin(a)+.008*(1-np.cos(a))
                chestpath(leafx,leafz,.00070)
                chestpath(xx+side*s*.016*t,zz+.016*t,.00048)
        for j in range(6):
            zz=2.13+j*.058;xx=side*(.052+.025*math.sin(j*.8));a=np.linspace(0,math.tau*1.5,70);rad=.016*(1-a/(math.tau*1.75))
            chestpath(xx+side*rad*np.cos(a),zz+rad*np.sin(a),.0007)
    # Concentric sacred medallion detail within the existing sun boss.
    for rad in [.012,.023,.034,.044]:
        a=np.linspace(0,math.tau,128);x=rad*np.cos(a);z=2.46+rad*np.sin(a)
        p=np.stack([x,np.array([chest(xx,zz)-.017 for xx,zz in zip(x,z)]),z],1);r.path(p,.00075)
    obs=[r.object('AstraChar2_Mpfb_BreastplateLaurel',slots,torso_weights)]
    for side,label,bone in [(1,'L','LeftArm'),(-1,'R','RightArm')]:
        rr=Relief()
        def surface(theta,phi):
            return np.column_stack([side*(.330+.180*np.sin(theta)*np.cos(phi)),-.173+.212*np.sin(theta)*np.sin(phi),2.586+.147*np.cos(theta)])
        for offset in [-.83,0,.83]:
            th=np.linspace(.18,1.75,120);ph=-math.pi/2+offset+.06*np.sin(th*3)
            rr.path(surface(th,ph),.0013)
            for j in range(11):
                c=.28+j*.13;phi=-math.pi/2+offset+.06*math.sin(c*3)
                for sign in [-1,1]:
                    a=np.linspace(0,math.tau,32);theta=c+.042*np.sin(a)+.035*(1-np.cos(a));angle=phi+sign*.050*(1-np.cos(a))
                    rr.path(surface(theta,angle),.00085)
        for th in [1.61,1.71,1.79]:
            ph=np.linspace(-math.pi,0,150);rr.path(surface(np.full(len(ph),th),ph),.0011)
        obs.append(rr.object('AstraChar2_Mpfb_PauldronLaurel_'+label,slots,lambda p,bn=bone:{bn:1}))
    rr=Relief()
    def collar(a,t):
        co=np.cos(a);rx=.14*(1-t)+.093*t;ry=.16*(1-t)+.108*t
        return np.stack([(rx+.001)*np.sin(a),-.178-.018*t-(ry+.001)*co,2.625+t*(.121-.030*np.maximum(co,0)**10)],1)
    for j in range(27):
        a0=-1.45+j*2.90/26;a=np.linspace(0,math.tau,32)
        rr.path(collar(a0+.035*np.sin(a),.53+.15*np.cos(a)),.00065)
    for height in [.25,.80]:
        a=np.linspace(-1.60,1.60,160);rr.path(collar(a,np.full(len(a),height)),.001)
    obs.append(rr.object('AstraChar2_Mpfb_GorgetLaurel',slots,lambda p:{'Spine':1}))
    return {'objects':len(obs),'vertices':sum(len(o.data.vertices) for o in obs),'faces':sum(len(o.data.polygons) for o in obs)}
