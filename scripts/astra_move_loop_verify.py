"""Measure analytical endpoint tangents; distinguish curvature from seam jumps."""
import bpy,sys,json
from pathlib import Path
n=sys.argv[sys.argv.index('--')+1];root=Path(__file__).resolve().parents[1];out=root/'renders/astra/moves'
bpy.ops.wm.open_mainfile(filepath=str(root/f'models/astra_move_{n}_wip.blend'))
r=bpy.data.objects['Armature'];worst={'location_m_s':0,'quaternion_component_s':0}
for la in r.animation_data.action.layers:
 for st in la.strips:
  for bag in st.channelbags:
   for fc in bag.fcurves:
    a,b=fc.keyframe_points[0],fc.keyframe_points[-1]
    aa=(a.handle_right.y-a.co.y)/(a.handle_right.x-a.co.x);bb=(b.co.y-b.handle_left.y)/(b.co.x-b.handle_left.x)
    key='location_m_s' if fc.data_path.endswith('location') else 'quaternion_component_s';factor=.01 if key=='location_m_s' else 1;worst[key]=max(worst[key],abs(aa-bb)*30*factor)
m=json.loads((out/f'{n}_metrics.json').read_text());m['loop']['analytical_endpoint_tangent_mismatch']=worst;m['loop']['quarter_step_note']='Opposite-sided quarter-frame differences include ordinary curve acceleration; the endpoint Bezier tangents are the C1 continuity test.';(out/f'{n}_metrics.json').write_text(json.dumps(m,indent=2));print('ENDPOINT TANGENTS',worst)
assert worst['location_m_s']<.001 and worst['quaternion_component_s']<.001
