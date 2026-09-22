"""Ground-loaded rising diagonal and one readable 360-degree stepped rotation."""
import sys,math
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_move_common import Builder,Vector,curve,vec,smooth,yaw,np,hermite

def main():
    b=Builder('rising_spin',116)
    U=Vector((-.55,0,-.835)).normalized();V=Vector((.16,-.982,-.105));V=(V-U*V.dot(U)).normalized()
    guard=Vector((-.14,-.14,-1)).normalized();guardq=b.orient_blade(guard)
    C=Vector((0,-.18,0));initial={'Right':0.,'Left':0.}
    def spin(f):return 360*smooth((f-20)/84)
    def feet_at(f):
        deg=spin(f);feet={};planted={}
        for side,base in [('Right',Vector((-.27,0,0))),('Left',Vector((.27,0,0)))]:
            ang=0.;lift=0;planted[side]=True
            for i in range(6):
                if side!=('Right' if i%2==0 else 'Left'):continue
                start=8+60*i;end=52+60*i;target=end-12
                if deg<=start:break
                u=smooth((deg-start)/(end-start));ang=ang+(target-ang)*u
                if deg<end:lift=.085*math.sin(math.pi*u)**2;planted[side]=False;break
            p=C+yaw(ang)@base;p.z=b.h[side+'Foot'].z+lift;feet[side]=p
        return feet,planted
    def trajectory(f):
        deg=spin(f);angle=curve(f,[(1,0),(16,-12),(20,-12)])+deg
        feet,planted=feet_at(f);w=.5+.5*math.cos(math.pi*(deg-30)/60)
        offset=((feet['Left']-C)*w+(feet['Right']-C)*(1-w))*.70;offset.z=0
        root=Vector((offset.x,offset.y,curve(f,[(1,-.10),(17,-.24),(24,-.21),(38,-.14),(62,-.19),(94,-.17),(116,-.12)])))
        th=math.radians(hermite(f,[(1,0,0),(24,0,0),(34,140,12),(42,182,3),(104,360,0),(116,360,0)]));D=U*math.cos(th)+V*math.sin(th)
        right=vec(f,[(1,(-.60,-.34,1.78)),(20,(-.65,-.29,1.79)),(24,(-.65,-.42,1.85)),(31,(-.38,-.76,2.20)),(38,(.10,-.65,2.65)),(46,(-.18,-.56,2.90)),(56,(-.76,-.30,2.90)),(68,(-.90,.20,2.43)),(84,(-.62,-.17,2.05)),(104,(-.64,-.34,1.83)),(116,(-.60,-.34,1.79))])
        return root,angle,right,D,th,feet,planted
    # A double-edged blade has the same cutting plane after 180 degrees of roll.
    # Unwrap that plane before baking so a velocity reversal cannot flip the hand.
    grid=np.arange(1,116.001,.25);raw=[]
    def tip(t):
        rr,aa,hh,dd,*_=trajectory(t);return rr+yaw(aa)@(hh+dd*b.blade_length)
    for f in grid:
        t=max(27,min(100,float(f)));rr,aa,hh,dd,th,*_=trajectory(t);rot=yaw(aa)
        tangent=(tip(t+.015)-tip(t-.015))/.03;D=rot@dd;tangent-=D*tangent.dot(D)
        E0=-U*math.sin(th)+V*math.cos(th);N0=dd.cross(E0)
        e=rot.inverted()@tangent.normalized() if tangent.length>.003 else E0
        raw.append(math.atan2(e.dot(N0),e.dot(E0)))
    rolls=np.unwrap(np.array(raw)*2)/2
    rolls=np.convolve(np.pad(rolls,(2,2),mode='edge'),np.array([1,4,6,4,1])/16,mode='valid')
    def pose(f):
        root,angle,right,D,th,feet,planted=trajectory(f)
        roll=float(np.interp(f,grid,rolls));E0=-U*math.sin(th)+V*math.cos(th);E=E0*math.cos(roll)+D.cross(E0)*math.sin(roll)
        q=b.orient_blade(D,E)
        # Prepare the edge with the whole wrist, then relax into the same low hold.
        prep=smooth((f-8)/14);q=guardq.slerp(q,prep)
        if f>104:q=q.slerp(guardq,smooth((f-104)/12))
        return dict(root=root,yaw=angle,twist=curve(f,[(1,0),(19,-14),(39,17),(62,8),(89,-5),(116,0)]),lean=curve(f,[(1,3),(19,-6),(36,5),(57,3),(92,2),(116,3)]),sway=curve(f,[(1,0),(20,3.5),(37,3.5),(67,-2),(102,1),(116,0)]),shoulder=curve(f,[(1,0),(20,-9),(39,11),(67,4),(100,-3),(116,0)]),look=curve(f,[(1,0),(20,8),(42,-10),(86,-5),(116,0)]),feet=feet,planted=planted,foot_yaw={'Left':angle,'Right':angle},right=right,left=vec(f,[(1,(.48,-.38,2.0)),(22,(.58,-.34,2.10)),(38,(.76,.12,2.03)),(61,(.69,.18,2.11)),(85,(.58,-.24,2.06)),(116,(.49,-.38,2.0))]),blade=D,blade_q=q,support_wrist='limited',wrist_limit=55,right_pole=(0,0,-1),left_wrist=curve(f,[(1,0),(27,2.5),(47,-2),(85,1.5),(116,0)]),cloth_drift=.65,cloth_sway=curve(f,[(1,0),(24,-3),(43,4),(71,2),(98,-2),(116,0)]),trail=curve(f,[(1,1),(20,-2),(38,9),(65,15),(90,10),(104,5),(116,1)]))
    b.build(pose,{'description':'Loaded low-to-high diagonal; one 360-degree readable body rotation on alternating short pivot steps; returns toward low hang.','cut_type':'slash','contact_frames':[1,16,22]+list(range(24,41,2))+[48,60,72,84,96,104,116],'grip_frames':[1,24,30,36,60,84,116],'active':[[24,40]],'edge_check_windows':[[24,104]],'cascade_window':[20,40],'body_turn_degrees':360,'body_turn_frames':[20,104],'scale':6.1,'target':(0,-.2,1.82),'camera':(4.3,-8.6,2.7)})
if __name__=='__main__':main()
