"""Fresh read-only Blender audit, intentionally separate from cached reanalysis.

Usage: PYTHONDONTWRITEBYTECODE=1 TMPDIR=/tmp blender -b --gpu-backend metal
 --python-exit-code 1 --python scripts/astra_armaudit_capture.py -- xslash
 --stills 1,27,38,39,47,48,54,61,90
For a separate short clip batch replace --stills and its value with --clip 30:44.

Render at most 20 frames per invocation; two still angles count separately.
Never saves a blend, changes action keys, or writes outside armaudit/.
"""
import sys, json, hashlib, math, argparse
from pathlib import Path
sys.dont_write_bytecode=True
import bpy
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'renders/astra/armaudit'
sys.path.insert(0,str(ROOT/'scripts'))
from astra_armaudit_analyze import analyze, unit, qm, ranges

def arr(v):return [float(x) for x in v]

def main():
    p=argparse.ArgumentParser();p.add_argument('name',choices=['xslash','idle_guard','lunge_thrust','walk_stalk']);p.add_argument('--stills',default='');p.add_argument('--clip',default='');p.add_argument('--capture-only',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);name=args.name
    source=ROOT/'models'/('astra_xslash_v2_final_wip.blend' if name=='xslash' else f'astra_move_{name}_wip.blend')
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    assert bpy.app.version[:2]==(5,2)
    s=bpy.context.scene;rig=next(o for o in s.objects if o.type=='ARMATURE');act=rig.animation_data.action
    assert abs(s.render.fps/s.render.fps_base-30)<1e-6,'Analyzer currently expects 30 fps'
    actual={suffix:next(n for n in rig.pose.bones.keys() if n.split(':')[-1]==suffix) for suffix in ['RightShoulder','RightArm','RightForeArm','RightHand']}
    # Inspect actual hierarchy before selecting the chain. Canonical names currently expected by anatomy routine.
    assert rig.data.bones[actual['RightHand']].parent.name==actual['RightForeArm']
    assert rig.data.bones[actual['RightForeArm']].parent.name==actual['RightArm']
    assert all(k==v for k,v in actual.items()),'Namespaced rig: normalize anatomy names before running'
    bones={b.name:{'parent':b.parent.name if b.parent else None,'head':arr(rig.matrix_world@b.head_local),'tail':arr(rig.matrix_world@b.tail_local),'matrix':list(map(list,rig.matrix_world@b.matrix_local)),'constraints':[c.name for c in rig.pose.bones[b.name].constraints]} for b in rig.data.bones}
    start,end=map(float,act.frame_range);assert end>start
    body=bpy.data.objects['char1'];sw=bpy.data.objects['Godwyn_Sword']
    source_attribute=np.array([p.vector[:] for p in sw.data.attributes['astra_sword_source'].data]);design=np.column_stack((source_attribute,np.ones(len(source_attribute))))
    tip_index=int(source_attribute[:,2].argmin());hilt_source=np.array([61.2,-66.3,167,1])
    torso_names={'Hips','Spine02','Spine01','Spine'};gn={g.index:g.name for g in body.vertex_groups}
    torso_ids=[];arm_ids=[]
    for v in body.data.vertices:
        weights={gn[g.group]:g.weight for g in v.groups}
        rest=body.matrix_world@v.co
        if sum(weights.get(n,0) for n in torso_names)>.65 and bones['Spine02']['head'][2]<rest.z<bones['neck']['head'][2]:torso_ids.append(v.index)
        if weights.get('RightArm',0)>.65:arm_ids.append(v.index)
    assert torso_ids and arm_ids
    armrest=np.array([body.matrix_world@body.data.vertices[i].co for i in arm_ids]);a=np.array(bones['RightArm']['head']);b=np.array(bones['RightForeArm']['head']);u=unit(b-a);t=(armrest-a)@u;radial=np.linalg.norm(armrest-a-t[:,None]*u,axis=1)
    use=(t>.2*np.linalg.norm(b-a))&(t<.9*np.linalg.norm(b-a));radius=float(np.quantile(radial[use],.95)) if use.any() else .06
    rows=[];grip=[];collision=[];previous_grip=None;render_points=[]
    for f in np.arange(start,end+.125,.25):
        s.frame_set(int(f),subframe=float(f%1));dg=bpy.context.evaluated_depsgraph_get();dg.update();er=rig.evaluated_get(dg);aw=er.matrix_world
        record={'frame':float(f),'bones':{p.name:{'q':arr(p.matrix_basis.to_quaternion()),'wq':arr((aw@p.matrix).to_quaternion()),'h':arr((aw@p.matrix).translation)} for p in er.pose.bones}}
        rows.append(record)
        if f%1:continue
        ev=sw.evaluated_get(dg);mesh=ev.to_mesh();co=np.array([ev.matrix_world@v.co for v in mesh.vertices]);fit=np.linalg.lstsq(design,co,rcond=None)[0];hilt=hilt_source@fit;tip=co[tip_index];residual=float(np.max(np.abs(design@fit-co)))
        # Three non-collinear evaluated vertices give axial-roll and full rigid-grip rotation.
        if previous_grip is None:
            ids=[tip_index,int(np.argmax(np.linalg.norm(co-co[tip_index],axis=1)))];axis=unit(co[ids[1]]-co[ids[0]]);ids.append(int(np.argmax(np.linalg.norm(np.cross(co-co[ids[0]],axis),axis=1))))
        x=unit(co[ids[1]]-co[ids[0]]);z=unit(np.cross(x,co[ids[2]]-co[ids[0]]));y=unit(np.cross(z,x));basis=np.column_stack((x,y,z));hand=record['bones']['RightHand'];hq=qm(hand['wq']);local=hq.T@basis
        if previous_grip is None:previous_grip=local.copy()
        rot=local@previous_grip.T;roll_error=math.degrees(math.acos(float(np.clip((np.trace(rot)-1)/2,-1,1))))
        grip.append({'frame':float(f),'hilt':hilt.tolist(),'tip':tip.tolist(),'full_hand_local_orientation':local.tolist(),'full_orientation_drift_deg':roll_error,'rigid_fit_residual_m':residual})
        render_points += [hilt,tip,np.array(record['bones']['RightArm']['h']),np.array(record['bones']['RightForeArm']['h'])]
        ev.to_mesh_clear()
        ev=body.evaluated_get(dg);mesh=ev.to_mesh();torso=np.array([ev.matrix_world@mesh.vertices[i].co for i in torso_ids]);q=qm(record['bones']['Spine']['wq']);origin=np.array(record['bones']['Spine']['h']);tc=(torso-origin)@q;lo=tc.min(axis=0);hi=tc.max(axis=0)
        a=np.array(record['bones']['RightArm']['h']);b=np.array(record['bones']['RightForeArm']['h']);segment=np.array([a+(b-a)*t for t in np.linspace(.2,.95,76)]);sp=(segment-origin)@q
        dist=np.linalg.norm(np.maximum(np.maximum(lo-sp,sp-hi),0),axis=1);inside=np.all((sp>=lo)&(sp<=hi),axis=1)
        collision.append({'frame':float(f),'upperarm_radius_m':radius,'torso_obb_local_bounds':[lo.tolist(),hi.tolist()],'axis_min_obb_distance_m':float(dist.min()),'capsule_obb_overlap_candidate':bool(dist.min()<radius),'arm_axis_inside_torso_obb':bool(inside.any()),'candidate_overlap_depth_m':max(0,radius-float(dist.min()))})
        ev.to_mesh_clear()
    provenance={'mode':'fresh_Blender_depsgraph','source':str(source.relative_to(ROOT)),'blend_sha256':before,'blender':bpy.app.version_string,'action':act.name,'actual_bone_names':actual,'action_range':[start,end],'scene_range':[s.frame_start,s.frame_end],'fps':s.render.fps/s.render.fps_base}
    result=analyze(name,rows,provenance,bones,grip);result['collision']={'method':'Evaluated torso/armor skin region OBB versus upperarm capsule, excluding proximal 20 percent. Coarse overlap is a candidate, not a confirmed mesh intersection.','rows':collision,'candidate_frame_ranges':ranges([x['frame'] for x in collision if x['capsule_obb_overlap_candidate']])};result['full_grip_evaluation']=grip;result['rest']=bones
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'Source changed externally during capture; discard batch'
    (OUT/f'data_{name}_fresh.json').write_text(json.dumps(result,indent=2))
    if args.capture_only:return
    frames=[int(x) for x in args.stills.split(',') if x];clip=[]
    if args.clip:lo,hi=map(int,args.clip.split(':'));clip=list(range(lo,hi+1))
    assert len(frames)*2+len(clip)<=20,'Short batches only: limit 20 renders per run'
    assert all(start<=f<=end for f in frames+clip)
    s.render.engine='BLENDER_EEVEE';s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100;s.render.use_motion_blur=False;s.render.image_settings.file_format='PNG';s.eevee.taa_render_samples=16
    # A new in-memory camera avoids camera action inheritance, preserving all source cameras.
    cd=bpy.data.cameras.new('Armaudit_Transient_Camera');cam=bpy.data.objects.new('Armaudit_Transient_Camera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO'
    for o in s.objects:
        if 'blur' in o.name.lower():o.hide_render=True
    byframe={r['frame']:r for r in rows};gmap={r['frame']:r for r in grip};manifest=[]
    def camera(f,side,stable=False):
        def points(frame):
            r=byframe[float(frame)];g=gmap[float(frame)];return [np.array(r['bones'][n]['h']) for n in ['RightShoulder','RightArm','RightForeArm','RightHand']]+[np.array(g['tip']),np.array(g['hilt'])]
        pp=np.array([x for frame in (clip if stable else [f]) for x in points(frame)]);center=Vector(pp.mean(axis=0));offset=Vector((0,-7,1.0) if side=='front' else (-7,-1.5,1.0));cam.location=center+offset;cam.rotation_euler=(-offset).to_track_quat('-Z','Y').to_euler();axes=cam.rotation_euler.to_matrix();projected=np.array([axes.transposed()@(Vector(x)-center) for x in pp]);extent=max(float(np.ptp(projected[:,0])),float(np.ptp(projected[:,1])));cd.ortho_scale=max(1.3,extent*1.22+.2)
    for f in frames:
        s.frame_set(f)
        for angle in ['front','side']:
            camera(f,angle);dest=OUT/f'stills_{name}'/f'{f:03d}_{angle}.png';dest.parent.mkdir(parents=True,exist_ok=True);s.render.filepath=str(dest);bpy.ops.render.render(write_still=True);manifest.append(str(dest.relative_to(ROOT)))
    for f in clip:
        s.frame_set(f);camera(f,'side',stable=True);dest=OUT/f'clipframes_{name}_{args.clip.replace(":","_")}'/f'{f:03d}.png';dest.parent.mkdir(parents=True,exist_ok=True);s.render.filepath=str(dest);bpy.ops.render.render(write_still=True);manifest.append(str(dest.relative_to(ROOT)))
    after=hashlib.sha256(source.read_bytes()).hexdigest();assert before==after,'Source changed externally during audit; invalidate this batch'
    (OUT/f'render_manifest_{name}_{frames[0] if frames else args.clip.replace(":","_")}.json').write_text(json.dumps({'source_sha256':before,'files':manifest,'engine':s.render.engine,'motion_blur':False},indent=2))

if __name__=='__main__':main()
