"""Match cyclic F-curve endpoint tangents without changing authored key values."""
import sys
from pathlib import Path
import bpy

def close_tangents(action):
    mismatch=0
    for la in action.layers:
        for st in la.strips:
            for bag in st.channelbags:
                for fc in bag.fcurves:
                    k=fc.keyframe_points
                    if len(k)<4:continue
                    offset=k[-1].co.y-k[0].co.y;dt=k[1].co.x-k[0].co.x
                    slope=(k[1].co.y-(k[-2].co.y-offset))/(2*dt)
                    for p in [k[0],k[-1]]:
                        p.handle_left_type=p.handle_right_type='FREE'
                        p.handle_left=(p.co.x-dt/3,p.co.y-slope*dt/3);p.handle_right=(p.co.x+dt/3,p.co.y+slope*dt/3)
                    fc.update()
    return mismatch
if __name__=='__main__':
    name=sys.argv[sys.argv.index('--')+1];root=Path(__file__).resolve().parents[1];path=root/f'models/astra_move_{name}_wip.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path));close_tangents(bpy.data.objects['Armature'].animation_data.action);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
