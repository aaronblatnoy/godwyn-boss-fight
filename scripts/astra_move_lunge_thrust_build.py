"""Jump-lunge: landing is the stab; overshoot remains loaded, back to target."""
import sys,math
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_move_common import Builder,Vector,curve,hermite,vec,smooth

def main():
    if '--retime-l01' in sys.argv:
        # Curve-only repair of the saved pre-L01 action; no character rebuild.
        from astra_move_lunge_thrust_l01 import main as retime
        if 'apply' not in sys.argv:sys.argv.append('apply')
        return retime()
    b=Builder('lunge_thrust',64)
    def pose(f):
        y=hermite(f,[(1,0,0),(11,.10,0),(15,-.08,-.10),(29,-2.0,-.135),(38,-2.80,-.045),(50,-3.08,-.012),(64,-3.24,-.010)])
        if f<15:z=hermite(f,[(1,-.10,0),(10,-.235,0),(15,-.16,2.6/30)])
        elif f<=31:
            dt=(f-15)/30;z=-.16+2.6*dt-4.905*dt*dt
        else:z=hermite(f,[(31,-.168533333,-.08773),(35,-.28,0),(43,-.20,.002),(55,-.19,0),(64,-.17,-.002)])
        feet={};planted={}
        for side,x,y0,yland in [('Right',-.27,-.18,-2.65),('Left',.27,.16,-2.05)]:
            u=max(0,min(1,(f-15)/16))
            fy=hermite(f,[(15,y0,0),(23,(-1.43 if side=='Right' else -.91),-.16),(31,yland,0)]) if 15<f<31 else (y0 if f<=15 else yland)
            lift=(-.16+2.6*(u*16/30)-4.905*(u*16/30)**2)-(-.16+(-.168533333+.16)*u)+.12*math.sin(math.pi*u)**2
            if side=='Left' and f>31:
                u=smooth((f-31)/8);fy=yland+(-3.24-yland)*u;lift=.10*math.sin(math.pi*u)**2
            if side=='Right' and f>41:
                u=smooth((f-41)/14);fy=yland+(-3.65-yland)*u;lift=.11*math.sin(math.pi*u)**2
            feet[side]=Vector((x,fy,b.h[side+'Foot'].z+lift))
            planted[side]=(f<=15 or f>=31) if side=='Right' else (f<=15 or f>=39)
            if side=='Right' and 41<f<55:planted[side]=False
        d=vec(f,[(1,(-.14,-.14,-1)),(17,(0,-.96,-.28)),(25,(0,-1,-.04)),(34,(0,-1,-.04)),(45,(.35,-.15,-.92)),(56,(.25,.84,-.48)),(64,(.32,.84,-.43))]).normalized()
        return dict(root=(curve(f,[(1,0),(15,-.05),(31,-.24),(35,-.24),(41,.23),(55,.23),(61,-.08),(64,-.10)]),y,z),yaw=curve(f,[(1,0),(12,-9),(31,8),(49,24),(64,30)]),twist=curve(f,[(1,0),(14,-11),(33,13),(51,-16),(64,-20)]),lean=curve(f,[(1,3),(12,-4),(23,8),(33,11),(43,5),(64,4)]),sway=curve(f,[(1,0),(15,2),(34,-4),(50,2),(64,1)]),shoulder=curve(f,[(1,0),(15,-8),(34,9),(64,-8)]),look=curve(f,[(1,0),(34,-3),(64,-37)]),feet=feet,planted=planted,foot_yaw={'Left':curve(f,[(31,0),(39,20),(64,20)]),'Right':curve(f,[(41,0),(55,28)])},right=vec(f,[(1,(-.60,-.34,1.78)),(16,(-.59,-.27,2.03)),(24,(-.45,-.54,2.12)),(33,(-.38,-1.02,2.15)),(42,(-.57,-.55,2.06)),(53,(-.62,.04,1.98)),(64,(-.62,.19,2.00))]),left=vec(f,[(1,(.49,-.38,2.0)),(17,(.61,-.34,2.15)),(31,(.73,.18,2.04)),(45,(.53,-.2,2.01)),(64,(.62,-.19,2.05))]),blade=d,support_wrist=True,left_wrist=curve(f,[(1,0),(17,2),(33,-2),(64,1)]),cloth_drift=.7,cloth_sway=curve(f,[(1,0),(16,2),(30,-5),(43,3),(64,-1)]),trail=curve(f,[(1,1),(15,-2),(24,21),(34,26),(43,12),(54,5),(64,4)]))
    b.build(pose,{'description':'Compressed takeoff, airborne gap close, landing thrust, overshoot into loaded BACK TO PLAYER. No idle tail.','cut_type':'thrust','contact_frames':[1,11,17,21]+list(range(23,50,2))+[53,57,61,64],'grip_frames':[1,17,29,33,37,41,45,49,57,64],'active':[[25,35]],'cascade_window':[10,34],'target_point':[0,-1.80,1.5],'end_state':'BACK TO PLAYER','flight':[15,31],'scale':7.0,'target':(0,-2.15,1.50),'camera':(7,-1.7,3.2)})
    if '--probe' not in sys.argv:
        from astra_move_lunge_thrust_l01 import apply_recovery
        import bpy
        apply_recovery()
        bpy.context.scene.frame_set(1)
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(__file__).resolve().parents[1]/'models/astra_move_lunge_thrust_wip.blend'))
if __name__=='__main__':main()
