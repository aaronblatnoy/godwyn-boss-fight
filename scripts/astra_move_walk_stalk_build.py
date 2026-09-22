"""Predatory forward stalk: 72-frame root-motion cycle, 1.08 m per cycle."""
import sys,math
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_move_common import Builder,Vector,smooth

def main():
    b=Builder('walk_stalk',73,True,(0,-1.08,0))
    def pose(f):
        t=(f-1)/72;p=t%1;a=2*math.pi*t
        if p<.08:x=.22-.44*smooth((p+.07)/.15)
        elif p<.43:x=-.22
        elif p<.58:x=-.22+.44*smooth((p-.43)/.15)
        elif p<.93:x=.22
        else:x=.22-.44*smooth((p-.93)/.15)
        feet={};planted={}
        for side,offset in [('Left',0),('Right',.5)]:
            q=t+offset;cyc=math.floor(q);u=q-cyc;step=smooth((u-.08)/.35)
            feet[side]=Vector((.25 if side=='Left' else -.25,-.05-1.08*(cyc+step)+offset*1.08,b.h[side+'Foot'].z+.135*math.sin(math.pi*step)**2))
            planted[side]=not(.08<u<.43)
        return dict(root=(x+.008*math.sin(a-.3),-.23-1.08*t,-.13+.010*math.cos(2*a-.2)+.003*math.sin(a)),yaw=3.5*math.sin(a-.2),twist=-2.1*math.sin(a-.45),lean=4.5+.45*math.sin(2*a-.7),sway=-1.1*math.sin(a-.35),shoulder=1.3*math.sin(a-.55),feet=feet,planted=planted,foot_yaw={'Left':0,'Right':0},
            right=(-.60+.015*math.sin(a-.4),-.34+.018*math.sin(a-.6),1.79+.012*math.cos(2*a-.55)),left=(.48+.014*math.sin(a+.55),-.41+.026*math.sin(a+.9),1.98+.017*math.sin(a-.25)),blade=Vector((-.14+.025*math.sin(a-.7),-.14+.018*math.sin(a-.95),-1)).normalized(),left_wrist=2*math.sin(a-.9),cloth_drift=1.8,cloth_sway=-2.1*math.sin(a-.45),trail=6+1.6*math.sin(2*a-.8))
    b.build(pose,{'description':'Watchful low-guard forward stalk; deliberate alternating footfalls, no idle arm swing.','contact_frames':list(range(1,74,6)),'grip_frames':[1,19,37,55,73],'active':[],'scale':4.5,'target':(0,-.38,1.58),'track_translation':True})
if __name__=='__main__':main()
