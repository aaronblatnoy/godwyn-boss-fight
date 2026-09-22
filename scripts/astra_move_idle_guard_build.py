"""Loaded low-hang guard; 96-frame periodic cycle with duplicate F97 endpoint."""
import sys,math
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_move_common import Builder,Vector

def main():
    b=Builder('idle_guard',97,loop=True)
    def pose(f):
        t=(f-1)*2*math.pi/96
        pulse=math.sin(t)+.14*math.sin(2*t+.35)
        breath=math.sin(t-.7)
        return dict(root=(.028*pulse,-.025+.010*math.sin(t-.45),-.055+.007*breath),yaw=2.5*math.sin(t),twist=1.5*math.sin(t-.3),lean=1.7+.55*breath,sway=.65*math.sin(t-.2),shoulder=1.4*math.sin(t-.3),
            feet={'Left':b.h['LeftFoot']+Vector((.02,-.09,0)),'Right':b.h['RightFoot']+Vector((-.02,.07,0))},planted={'Left':True,'Right':True},foot_yaw={'Left':0,'Right':0},
            right=(-.60+.014*math.sin(t-.38),-.32+.016*math.sin(t-.6),1.75+.010*breath),left=(.48+.012*math.sin(t+.8),-.44+.010*math.sin(t+.25),1.96+.014*math.sin(t-.9)),
            blade=Vector((-.15+.014*math.sin(t-.65),-.10+.012*math.sin(t-.85),-1)).normalized(),left_wrist=1.4*math.sin(t-.9),cloth_drift=1.5,cloth_sway=.6*math.sin(t-.5),trail=1.5+.4*math.sin(t-.9))
    b.build(pose,{'description':'Loaded point-down low guard. Asymmetric breathing and weight transfer; periodic pose and velocity.','contact_frames':[1,9,17,25,33,41,49,57,65,73,81,89,97],'active':[],'scale':4.25})
if __name__=='__main__':main()
