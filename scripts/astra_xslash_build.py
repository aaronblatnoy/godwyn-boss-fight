"""Deterministic 61-frame X-slash. Run with Blender --background --python.
World -Y is forward; Godwyn's right is -X. Analytic two-link solves use
joint heads (the imported display-bone tails are incorrectly 100x long).
All output is confined to Astra paths. No external packages are needed.
"""
import bpy, math, json, sys
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from astra_xslash_probe import fresh, stage, camera
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'renders/astra'
OUT.mkdir(exist_ok=True,parents=True)
rig=fresh(); sw=bpy.data.objects['Godwyn_Sword']; scene=bpy.context.scene
AW=rig.matrix_world.copy(); AI=AW.inverted()
rest={p.name:(AW@p.matrix).copy() for p in rig.pose.bones}
heads={n:m.translation.copy() for n,m in rest.items()}
assert sw.parent==rig and sw.parent_type=='BONE' and sw.parent_bone=='RightHand'
assert not sw.constraints
bb=[Vector(c) for c in sw.bound_box]; lo=min(v.z for v in bb); hi=max(v.z for v in bb)
cx=sum(v.x for v in bb)/8; cy=sum(v.y for v in bb)/8
TIP=min(sw.data.vertices,key=lambda v:v.co.z).co.copy()
handle=[v.co for v in sw.data.vertices if 159<v.co.z<169]
GRIP=sum(handle,Vector())/len(handle); LENGTH=(TIP-GRIP).length*.01
BLADE_AXIS_FIX=(TIP-GRIP).normalized().rotation_difference(Vector((0,0,-1))).to_matrix().to_4x4()
# Put the actual handle centre in the palm, retaining the original bone parent.
sw.matrix_world=Matrix.Translation(heads['RightHand'])@Matrix.Identity(4)@Matrix.Diagonal((.01,.01,.01,1))@Matrix.Translation(-GRIP)
bpy.context.view_layer.update()
HAND_TO_SWORD=(AW@rig.pose.bones['RightHand'].matrix).inverted()@sw.matrix_world
scene=stage(); scene.frame_start=1; scene.frame_end=61
scene.world.color=(.045,.055,.08)
# Softer key exposure keeps the gold readable.
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-.7
scene.render.fps=30
for p in rig.pose.bones:p.rotation_mode='QUATERNION'
prev={}; samples=[]

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def track(f,anchors):
    if f<=anchors[0][0]:return anchors[0][1]
    for (a,x),(b,y) in zip(anchors,anchors[1:]):
        if f<=b:
            t=smooth((f-a)/(b-a));return x*(1-t)+y*t
    return anchors[-1][1]
# Repair demonstrated imported weight contamination in the WIP only: lower-robe
# vertices carried ~40% RightHand weights, and adjacent gauntlet vertices were
# bound to cape bones. The source GLB is never modified.
body=bpy.data.objects['char1']; groups={g.index:g.name for g in body.vertex_groups}
arm_names={side+n for side in ['Left','Right'] for n in ['Shoulder','Arm','ForeArm','Hand']}
arm_ids={g.index for g in body.vertex_groups if g.name in arm_names}
repaired=0
for v in body.data.vertices:
    w=body.matrix_world@v.co; weights={g.group:g.weight for g in v.groups if g.weight>1e-7}; new=None
    if w.z<1.49 and any(i in arm_ids for i in weights):
        cloth={i:a for i,a in weights.items() if groups[i].startswith('phys_robe')}
        new=cloth if sum(cloth.values())>.005 else {i:a for i,a in weights.items() if i not in arm_ids}
    else:
        side='Right' if w.x<0 else 'Left'
        a,b,c=[heads[side+n] for n in ['Arm','ForeArm','Hand']]
        end=c+(c-b).normalized()*.16
        def distance(p,a,b):
            d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return (p-a-t*d).length
        dist=min(distance(w,a,b),distance(w,b,end))
        if abs(w.x)>.30 and dist<.165 and w.z>1.49:
            # Continuous elbow and wrist blends, no cape pinning inside gauntlets.
            wrist=smooth((w.z-(c.z-.065))/.17)
            elbow=smooth((w.z-(b.z-.095))/.19)
            new={body.vertex_groups[side+'Arm'].index:elbow,
                 body.vertex_groups[side+'ForeArm'].index:(1-elbow)*wrist,
                 body.vertex_groups[side+'Hand'].index:(1-elbow)*(1-wrist)}
    if new and sum(new.values())>1e-6:
        total=sum(new.values())
        for i in weights:body.vertex_groups[i].remove([v.index])
        for i,a in new.items():
            if a>1e-6:body.vertex_groups[i].add([v.index],a/total,'REPLACE')
        repaired+=1
print('ASTRA WIP WEIGHT REPAIRS',repaired,flush=True)
# Spatially continuous blend across the contaminated binding boundaries.
# A coarse weight field prevents adjacent triangles being pinned to unrelated
# arm/cape bones. Geometry, UVs and textures remain the imported asset's.
from mathutils.kdtree import KDTree
cell=.075; buckets={}
for v in body.data.vertices:
    w=body.matrix_world@v.co
    if .24<w.z<2.8:
        key=tuple(math.floor(c/cell) for c in w)
        if key not in buckets:buckets[key]=[Vector(),0,{}]
        pos,count,weights=buckets[key];pos+=w;buckets[key][1]+=1
        for g in v.groups:weights[g.group]=weights.get(g.group,0)+g.weight
field=[]
for pos,count,weights in buckets.values():field.append((pos/count,{i:a/count for i,a in weights.items()}))
kd=KDTree(len(field))
for i,(pos,_) in enumerate(field):kd.insert(pos,i)
kd.balance(); changed=0
for v in body.data.vertices:
    w=body.matrix_world@v.co
    if not (.30<w.z<2.74 and abs(w.x)>.23):continue
    mixed={}
    for pos,i,d in kd.find_n(w,12):
        fac=math.exp(-d*d/(2*.07*.07))
        for j,wt in field[i][1].items():mixed[j]=mixed.get(j,0)+fac*wt
    total=sum(mixed.values());blend=smooth((abs(w.x)-.23)/.09)*smooth((w.z-.30)/.12)*smooth((2.74-w.z)/.12)
    original={g.group:g.weight for g in v.groups}
    out={i:a*(1-blend) for i,a in original.items()}
    for i,a in mixed.items():out[i]=out.get(i,0)+blend*a/total
    out=dict(sorted(out.items(),key=lambda kv:kv[1],reverse=True)[:8]);total=sum(out.values())
    for i in original:body.vertex_groups[i].remove([v.index])
    for i,a in out.items():body.vertex_groups[i].add([v.index],a/total,'REPLACE')
    changed+=1
print('ASTRA SMOOTH BINDINGS',changed,flush=True)


def vec(f,items):return Vector(tuple(track(f,[(a,p[i]) for a,p in items]) for i in range(3)))
def update():bpy.context.view_layer.update()
def rotate_world(n,axis,deg):
    p=rig.pose.bones[n]; m=AW@p.matrix; t=Matrix.Translation(m.translation)
    p.matrix=AI@t@Matrix.Rotation(math.radians(deg),4,axis)@t.inverted()@m;update()
def aim(n,child,target):
    p=rig.pose.bones[n]; m=AW@p.matrix; h=m.translation
    cur=(AW@rig.pose.bones[child].matrix).translation-h
    q=cur.rotation_difference(Vector(target)-h)
    p.matrix=AI@Matrix.Translation(h)@q.to_matrix().to_4x4()@Matrix.Translation(-h)@m;update()
def solve(a,b,c,target,pole):
    h=(AW@rig.pose.bones[a].matrix).translation; v=Vector(target)-h
    l1=(heads[b]-heads[a]).length;l2=(heads[c]-heads[b]).length
    d=min(v.length,l1+l2-.004); axis=v.normalized(); end=h+axis*d
    along=(l1*l1-l2*l2+d*d)/(2*d); height=math.sqrt(max(0,l1*l1-along*along))
    bend=Vector(pole)-h; bend=(bend-axis*bend.dot(axis)).normalized()
    joint=h+axis*along+bend*height
    aim(a,b,joint);aim(b,c,end)
    return (end-Vector(target)).length

def orient(n,rotation):
    m=AW@rig.pose.bones[n].matrix
    rig.pose.bones[n].matrix=AI@Matrix.LocRotScale(m.translation,rotation, m.to_scale());update()

# Rest splay is corrected once; both toe axes then point world-forward.
foot_rot={}
for side in ['Left','Right']:
    v=heads[side+'ToeBase']-heads[side+'Foot']; yaw=math.atan2(-v.x,-v.y)
    foot_rot[side]=Quaternion((0,0,1),yaw)@rest[side+'Foot'].to_quaternion()

wrist_anchors=[(1,(-.52,-.65,2.15)),(9,(-.62,-.52,2.63)),(13,(-.62,-.52,2.63)),(23,(.23,-.74,1.94)),(26,(.23,-.74,1.94)),(33,(.29,-.67,2.65)),(36,(.29,-.67,2.65)),(46,(-.65,-.68,1.87)),(50,(-.65,-.68,1.87)),(61,(-.53,-.62,2.15))]
tip_anchors=[(1,(-1.1,2.75)),(9,(-1.45,3.5)),(13,(-1.45,3.5)),(23,(1.4,1.2)),(26,(1.4,1.2)),(33,(1.45,3.5)),(36,(1.45,3.5)),(46,(-1.4,1.2)),(50,(-1.4,1.2)),(61,(-1.1,2.75))]
for f in range(1,62):
    scene.frame_set(f)
    for p in rig.pose.bones:p.matrix_basis.identity()
    update()
    yaw=track(f,[(1,0),(9,-8),(12,-2),(21,8),(30,8),(33,8),(36,2),(44,-8),(53,-5),(61,0)])
    shift=vec(f,[(1,(0,0,-.025)),(11,(.03,-.12,-.055)),(23,(.045,-.15,-.08)),(34,(.01,-.15,-.045)),(46,(-.025,-.15,-.07)),(61,(0,-.15,-.035))])
    p=rig.pose.bones['Hips'];p.matrix=AI@Matrix.Translation(shift)@rest['Hips'];update();rotate_world('Hips','Z',yaw)
    torso=track(f,[(1,0),(9,-28),(12,-10),(21,30),(30,30),(33,30),(36,10),(44,-28),(53,-14),(61,0)])
    for n,fac in [('Spine02',.25),('Spine01',.35),('Spine',.4)]:rotate_world(n,'Z',torso*fac)
    rotate_world('RightShoulder','Z',torso*.12);rotate_world('LeftShoulder','Z',torso*.10)
    rotate_world('neck','Z',-(yaw+torso)*.6)
    # Forward stepping left foot lifts only before the first contact window.
    step=track(f,[(1,0),(4,0),(11,1)])
    lift=.075*math.sin(math.pi*step)
    for side in ['Left','Right']:
        target=heads[side+'Foot']+Vector((0,-.26*step if side=='Left' else 0,lift if side=='Left' else 0))
        solve(side+'UpLeg',side+'Leg',side+'Foot',target,heads[side+'Leg']+Vector((0,-2,0)))
        orient(side+'Foot',foot_rot[side])
    wrist=vec(f,wrist_anchors)
    err=solve('RightArm','RightForeArm','RightHand',wrist,(-1.2,-.25,2.1))
    grip=(AW@rig.pose.bones['RightHand'].matrix).translation
    tx=track(f,[(a,p[0]) for a,p in tip_anchors]);tz=track(f,[(a,p[1]) for a,p in tip_anchors])
    dx=tx-grip.x;dz=tz-grip.z
    dy=-math.sqrt(max(.05,LENGTH*LENGTH-dx*dx-dz*dz))
    direction=Vector((dx,dy,dz)).normalized()
    sword_rotation=direction.to_track_quat('-Z','Y').to_matrix().to_4x4()@BLADE_AXIS_FIX
    desired=Matrix.Translation(grip)@sword_rotation@Matrix.Diagonal((.01,.01,.01,1))@Matrix.Translation(-GRIP)
    rig.pose.bones['RightHand'].matrix=AI@desired@HAND_TO_SWORD.inverted();update()
    # Free hand counterbalances close to the chest, avoiding a dangling rest arm.
    left=vec(f,[(1,(.52,-.65,2.2)),(12,(.55,-.62,2.3)),(23,(.65,-.48,2.25)),(34,(.6,-.62,2.3)),(46,(.55,-.55,2.22)),(61,(.52,-.65,2.2))])
    solve('LeftArm','LeftForeArm','LeftHand',left,(1.1,-.25,2.1))
    # Restrained delayed follow-through; no simulation or floor-directed chains.
    lag=track(f-3,[(1,0),(9,-28),(21,30),(30,30),(44,-28),(61,0)])-torso
    for p in rig.pose.bones:
        if p.name.startswith('phys_') and p.name.endswith('_00'):
            p.rotation_quaternion=Quaternion((0,1,0),math.radians(lag*.045))
    for p in rig.pose.bones:
        q=p.rotation_quaternion.copy()
        if p.name in prev and q.dot(prev[p.name])<0:q.negate()
        p.rotation_quaternion=q;prev[p.name]=q.copy()
        p.keyframe_insert('rotation_quaternion',frame=f)
        p.keyframe_insert('location',frame=f)
    update()
    samples.append({'frame':f,'hips_yaw':yaw,'torso_yaw':torso,'tip':list(sw.matrix_world@TIP),'grip':list(sw.matrix_world@GRIP),'wrist_reach_error':err,'feet':{s:list((AW@rig.pose.bones[s+'Foot'].matrix).translation) for s in ['Left','Right']},'toes':{s:list((AW@rig.pose.bones[s+'ToeBase'].matrix).translation) for s in ['Left','Right']}})
act=rig.animation_data.action;act.name='Astra_Godwyn_XSlash'
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for k in fc.keyframe_points:k.interpolation='LINEAR'
maxyaw=max(abs(b['hips_yaw']-a['hips_yaw'])*30 for a,b in zip(samples,samples[1:]))
metrics={'fps':30,'frames':61,'duration_seconds':61/30,'max_hips_yaw_deg_s':maxyaw,'blade_length':LENGTH,'max_wrist_reach_error':max(s['wrist_reach_error'] for s in samples),'samples':samples}
(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2))
# Brief tip afterimages, generated from the measured blade trajectory only.
# They last three frames, making direction readable without hiding the pose.
trail_mat=bpy.data.materials.new('Astra blade afterimage');trail_mat.diffuse_color=(1,.52,.08,1)
trail_mat.use_nodes=True;bs=trail_mat.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(1,.54,.12,1);bs.inputs['Emission Color'].default_value=(1,.30,.025,1);bs.inputs['Emission Strength'].default_value=1.5
for start,end in [(13,23),(36,46)]:
    for f in range(start+1,end+1):
        curve=bpy.data.curves.new(f'Astra_tip_trail_{f}','CURVE');curve.dimensions='3D';curve.bevel_depth=.012;curve.bevel_resolution=2
        sp=curve.splines.new('POLY');sp.points.add(1)
        for p,co in zip(sp.points,[samples[f-2]['tip'],samples[f-1]['tip']]):p.co=(*co,1)
        obj=bpy.data.objects.new(curve.name,curve);scene.collection.objects.link(obj);curve.materials.append(trail_mat)
        for frame,hide in [(1,True),(f-1,True),(f,False),(f+3,True)]:
            obj.hide_render=hide;obj.hide_viewport=hide
            obj.keyframe_insert('hide_render',frame=frame);obj.keyframe_insert('hide_viewport',frame=frame)

scene.frame_set(1);camera('front',5.0,(0,-.2,1.9))
scene.camera.location=(0,-10,2.35);scene.camera.rotation_euler=(Vector((0,-.2,1.9))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.type='PERSP';scene.camera.data.lens=68
# Disable backup files; save only to the authorized WIP path.
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_xslash_wip.blend'))
print('ASTRA BUILD',json.dumps({k:v for k,v in metrics.items() if k!='samples'}))
