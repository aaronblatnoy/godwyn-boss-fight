"""Correct floor sinking using only existing distal cloth-bone location keys."""
import bpy,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'models/astra_xslash_v2_final_wip.blend'
bpy.ops.wm.open_mainfile(filepath=str(TARGET));s=bpy.context.scene
r=bpy.data.objects['Armature'];body=bpy.data.objects['char1'];AW=r.matrix_world.copy();AI=AW.inverted()
floor=max((bpy.data.objects['Astra_Stage'].matrix_world@v.co).z for v in bpy.data.objects['Astra_Stage'].data.vertices)
names={g.index:g.name for g in body.vertex_groups};families={}
for p in r.pose.bones:
    if p.name.startswith(('phys_robe','phys_cape')):
        fam=p.name.rsplit('_',1)[0];families.setdefault(fam,{'bones':[],'vertices':[]})['bones'].append(p.name)
for v in body.data.vertices:
    if (body.matrix_world@v.co).z>.40:continue
    weights={}
    for g in v.groups:
        n=names[g.group];fam=n.rsplit('_',1)[0]
        if fam in families:weights[fam]=weights.get(fam,0)+g.weight
    for fam,w in weights.items():
        if w>.58:families[fam]['vertices'].append(v.index)
families={f:d for f,d in families.items() if len(d['vertices'])>20}
for d in families.values():d['bones'].sort();d['needed']=[]
for f in range(1,91):
    s.frame_set(f);ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh()
    co=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3);M=np.array(ob.matrix_world);co=co@M[:3,:3].T+M[:3,3]
    for d in families.values():d['needed'].append(max(0,float(floor+.002-co[d['vertices'],2].min())))
    ob.to_mesh_clear()
# Smooth spatial folding/compaction over the bottom half of each hanging panel.
# Roots and first three links stay attached to the waist/spine exactly.
visibility=[(o,o.hide_viewport) for o in s.objects if o.type=='MESH']
for o,_ in visibility:o.hide_viewport=True
out={};maxloc={}
for qf in range(4,361):
    f=qf/4;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    for fam,d in families.items():
        needed=float(np.interp(f,np.arange(1,91),d['needed']))
        prev=0;last=len(d['bones'])-1
        for depth,n in enumerate(d['bones']):
            t=max(0,(depth-2)/(last-2));cumulative=needed*t*t*(3-2*t);inc=cumulative-prev;prev=cumulative
            if depth<=2:continue
            p=r.pose.bones[n];m=AW@p.matrix;m.translation.z+=inc;p.matrix=AI@m;bpy.context.view_layer.update()
            out.setdefault(n,[]).append(list(p.location));maxloc[n]=max(maxloc.get(n,0),inc)
for la in r.animation_data.action.layers:
    for st in la.strips:
        for bag in st.channelbags:
            for fc in bag.fcurves:
                for n,values in out.items():
                    if fc.data_path==r.pose.bones[n].path_from_id('location'):
                        assert len(values)==len(fc.keyframe_points)
                        for kp,v in zip(fc.keyframe_points,values):
                            kp.co.y=v[fc.array_index];kp.handle_left_type=kp.handle_right_type='AUTO_CLAMPED'
                        fc.update()
for o,hidden in visibility:o.hide_viewport=hidden
s.frame_set(1);bpy.context.view_layer.update();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
report={f:{'vertices':len(d['vertices']),'max_cumulative_lift_m':max(d['needed']),'per_frame_lift_m':d['needed']} for f,d in families.items()}
history_path=ROOT/'renders/astra/naturalness_cloth_floor_history.json'
history=json.loads(history_path.read_text()) if history_path.exists() else [json.loads((ROOT/'renders/astra/naturalness_cloth_floor_fix.json').read_text())]
history.append(report);history_path.write_text(json.dumps(history,indent=2))
(ROOT/'renders/astra/naturalness_cloth_floor_fix.json').write_text(json.dumps(report,indent=2))
print('CLOTH GROUND',json.dumps({f:d['max_cumulative_lift_m'] for f,d in report.items()}),flush=True)
