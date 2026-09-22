"""Rigid sword/grip audit at quarter frames, evaluated vertices, close-up renders."""
import sys,json,math
from pathlib import Path
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'
args=sys.argv[sys.argv.index('--')+1:];name=args[0];render='render' in args
m=json.loads((OUT/f'{name}_manifest.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'models/astra_move_{name}_wip.blend'))
s=bpy.context.scene;r=bpy.data.objects['Armature'];sw=bpy.data.objects['Godwyn_Sword'];AW=r.matrix_world;AI=AW.inverted();bone=r.data.bones['RightHand'];bind=bone.matrix_local.inverted()@AI@sw.matrix_world
src=np.array([p.vector[:] for p in sw.data.attributes['astra_sword_source'].data]);loc=np.array([v.co[:] for v in sw.data.vertices]);fit=np.linalg.lstsq(np.column_stack((src,np.ones(len(src)))),loc,rcond=None)[0]
tip_index=int(src[:,2].argmin());tip=sw.data.vertices[tip_index].co.copy();grip=Vector(np.array([61.2,-66.3,167,1])@fit)
blade=loc[(src[:,2]>30)&(src[:,2]<145)];_,_,axes=np.linalg.svd(blade-blade.mean(0),full_matrices=False)
normal=Vector(axes[-1]);direction=(tip-grip).normalized();edge=normal.cross(direction).normalized()
assert sw.parent==r and sw.parent_type=='OBJECT';assert len(sw.constraints)==0
assert list(sw.vertex_groups.keys())==['RightHand'];weights=[g.weight for v in sw.data.vertices for g in v.groups]
assert all(len(v.groups)==1 for v in sw.data.vertices) and min(weights)>.999999
armmods=[mod for mod in sw.modifiers if mod.type=='ARMATURE'];assert len(armmods)==1 and armmods[0].object==r
assert not sw.animation_data or not sw.animation_data.action
visibility=[(o,o.hide_viewport) for o in s.objects if o.type in ['MESH','CURVES']]
for o,_ in visibility:o.hide_viewport=True
rows=[];rigid_errors=[];reference=bind@grip
for qf in range(4,4*m['samples_end']+1):
    f=qf/4;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();hand=AW@r.pose.bones['RightHand'].matrix;deform=hand@bind
    g=deform@grip;t=deform@tip;e=(deform.to_3x3()@edge).normalized();d=(t-g).normalized();hl=hand.inverted()@g
    rigid_errors.append((hl-reference).length*.01)
    rows.append({'frame':f,'hilt':list(g),'wrist':list(hand.translation),'hilt_wrist_distance_m':(g-hand.translation).length,'tip':list(t),'edge':list(e),'direction':list(d)})
# Test the actual deformed mesh, not merely the formula used to construct targets.
sw.hide_viewport=False;eval_error=0
for i in range(0,len(rows),4):
    rec=rows[i];s.frame_set(int(rec['frame']));bpy.context.view_layer.update();ev=sw.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();actual=ev.matrix_world@mesh.vertices[tip_index].co;eval_error=max(eval_error,(actual-Vector(rec['tip'])).length);ev.to_mesh_clear()
roll=[];thrust=[]
for i in range(1,len(rows)-1):
    rec=rows[i];f=rec['frame']
    if not any(a<=f<=b for a,b in m.get('edge_check_windows',m['active'])):continue
    d=Vector(rec['direction']);v=(Vector(rows[i+1]['tip'])-Vector(rows[i-1]['tip']))*60;cut=v-d*v.dot(d)
    if m.get('cut_type')=='thrust':
        thrust.append({'frame':f,'tip_speed_m_s':v.length,'axial_tip_speed_m_s':v.dot(d),'tip_velocity_vs_axis_deg':math.degrees(math.acos(max(-1,min(1,v.normalized().dot(d)))))})
        continue
    if cut.length<.75:continue
    cosine=abs(Vector(rec['edge']).dot(cut.normalized()));err=math.degrees(math.acos(max(-1,min(1,cosine))))
    roll.append({'frame':f,'edge_vs_cut_deg':err,'transverse_tip_speed_m_s':cut.length})
# Actual closed-finger mesh follows the same rigid hand transform at every frame.
body=bpy.data.objects['char1'];gi=body.vertex_groups['RightHand'].index;finger_ids=[]
for v in body.data.vertices:
    p=body.matrix_world@v.co;w=sum(g.weight for g in v.groups if g.group==gi)
    if w>.999999 and 1.34<p.z<1.60 and -.60<p.x<-.30:finger_ids.append(v.index)
finger_reference=[bone.matrix_local.inverted()@AI@body.matrix_world@body.data.vertices[i].co for i in finger_ids]
body.hide_viewport=False;finger_error=0;finger_nominal_offset=0
for f in range(1,m['samples_end']+1):
    s.frame_set(f);bpy.context.view_layer.update();hand=AW@r.pose.bones['RightHand'].matrix;ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();mat=hand.inverted()@ev.matrix_world
    current=[mat@mesh.vertices[idx].co for idx in finger_ids]
    if f==1:
        finger_nominal_offset=max(((a-b).length*.01 for a,b in zip(current,finger_reference)),default=0);finger_reference=[p.copy() for p in current]
    for p,ref in zip(current,finger_reference):finger_error=max(finger_error,(p-ref).length*.01)
    ev.to_mesh_clear()
grip_cleanup={k:body[k] for k in ['astra_move_gold_palm_faces','astra_move_palm_sliver_faces','astra_move_closed_finger_vertices','astra_move_max_finger_adjustment_m','astra_move_hilt_envelope_m'] if k in body}
report={'thrust_samples':thrust,'pre_armature_surface_polish_offset_m':finger_nominal_offset,'closed_finger_mesh_samples':len(finger_ids),'max_closed_finger_hand_local_drift_m':finger_error,'derived_grip_correction':grip_cleanup,'binding':'OBJECT parent Armature + one ARMATURE modifier; every sword vertex RightHand=1.0; no sword action or constraints','quarter_samples':len(rows),'hilt_wrist_distance_range_m':[min(x['hilt_wrist_distance_m'] for x in rows),max(x['hilt_wrist_distance_m'] for x in rows)],'max_hand_local_hilt_drift_m':max(rigid_errors),'max_evaluated_tip_error_m':eval_error,'cut_roll_samples':roll,'max_edge_vs_cut_deg':max((x['edge_vs_cut_deg'] for x in roll),default=None),'rows':rows,'two_handed':False,'grip_frames':m.get('grip_frames',[1,(m['samples_end']+1)//2,m['samples_end']])}
(OUT/f'{name}_grip_metrics.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['rows','cut_roll_samples']},indent=2),flush=True)
assert max(rigid_errors)<.001 and eval_error<.001 and finger_error<.001
if render:
    for o,hidden in visibility:o.hide_viewport=hidden
    folder=OUT/name/'grip';folder.mkdir(parents=True,exist_ok=True)
    s.camera.animation_data_clear()
    s.render.engine='BLENDER_EEVEE';s.render.resolution_x=s.render.resolution_y=512;s.render.resolution_percentage=100;s.render.use_motion_blur=False;s.eevee.taa_render_samples=32
    for ob in s.objects:
        if ob.name.startswith('Astra_Move_blur_'):ob.hide_render=True
    restq=(AW@bone.matrix_local).to_quaternion()
    for f in report['grip_frames']:
        s.frame_set(f);bpy.context.view_layer.update();hand=AW@r.pose.bones['RightHand'].matrix;g=hand@bind@grip;rot=hand.to_quaternion()@restq.inverted()
        target=g+rot@Vector((0,0,.04));offset=rot@Vector((-.3,-4,.7));offset.z=max(.35,offset.z);s.camera.location=target+offset;s.camera.rotation_euler=(target-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.62;s.render.filepath=str(folder/f'{f:03d}.png');bpy.ops.render.render(write_still=True)
