"""Fluid 90-frame X-slash v2. Run with Blender --background --python.
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
scene=stage(); scene.frame_start=1; scene.frame_end=90
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

# Timing is authored in frames, with cubic Hermite tangents in value/frame.
# Connected tangents preserve momentum between follow-through and next coil.
VERSION='r4'
N=90
CUTS=[(37,42),(54,59)]
def curve(f, keys):
    if f<=keys[0][0]:return keys[0][1]
    if f>=keys[-1][0]:return keys[-1][1]
    for (a,x,m),(b,y,n) in zip(keys,keys[1:]):
        if f<=b:
            t=(f-a)/(b-a);h=b-a
            return (2*t**3-3*t*t+1)*x+(t**3-2*t*t+t)*h*m+(-2*t**3+3*t*t)*y+(t**3-t*t)*h*n

def path(f, keys):
    return Vector([curve(f,[(a,p[i],v[i]) for a,p,v in keys]) for i in range(3)])
Z=(0,0,0)
# Hips fire first. Each successive segment releases one frame later.
turn=[(1,0,0),(20,-1,0),(29,-1.12,0),(31,-1.1,.025),(37,.85,.08),(44,1.1,0),(48,1.0,-.03),(54,-.94,-.07),(63,-1.13,0),(74,-.3,.07),(83,.055,0),(90,0,0)]
def drive(f,lag=0):return curve(f-lag,turn)
# The hand starts uncoiling before the blade. The connector travels outward
# and behind the left shoulder; it never freezes at the first cut endpoint.
hand_keys=[
 (1,(-.53,-.62,2.06),Z),(17,(-.70,-.40,2.60),(-.003,.012,.025)),
 (27,(-.74,-.22,2.77),Z),(34,(-.76,-.20,2.78),Z),
 (37,(-.62,-.55,2.63),(.13,-.15,-.10)),
 (40,(.05,-.90,2.18),(.17,-.025,-.14)),
 (43,(.38,-.72,1.89),(.015,.08,-.025)),
 (46,(.39,-.45,1.97),(-.008,.08,.10)),
 (51,(.26,-.36,2.57),(-.015,-.005,.045)),
 (53,(.19,-.41,2.64),(-.04,-.07,-.015)),
 (56,(-.18,-.88,2.31),(-.16,-.06,-.17)),
 (60,(-.68,-.62,1.72),(-.025,.08,-.045)),
 (65,(-.69,-.30,1.71),Z),(72,(-.66,-.35,1.82),(.015,-.025,.035)),
 (82,(-.51,-.64,2.22),Z),(86,(-.54,-.60,2.17),Z),(90,(-.53,-.62,2.20),Z)]
# Blade rotation uses an oblique circular plane, not independently traced X/Z.
u1=Vector((-.7071,0,.7071)).normalized();v1=Vector((.09,-.9919,.09)).normalized()
u2=Vector((.7071,0,.7071)).normalized();v2=Vector((-.08,-.9936,.08)).normalized()
def circ(u,v,angle):
    t=math.radians(angle);return (u*math.cos(t)+v*math.sin(t)).normalized()
a1=[(1,14,0),(21,-8,0),(29,-13,0),(36,-11,2),(37,-5,12),(39,55,45),(41,137,29),(42,159,17),(45,185,3)]
a2=[(51,-16,0),(53,-10,3),(54,-4,12),(56,59,45),(58,140,29),(59,162,17),(64,193,0),(70,187,-2)]
def blade(f):
    if f<=45:return circ(u1,v1,curve(f,a1))
    if f<53:
        # Cubic tangent-matched bridge: carry the first cut's momentum
        # backward and around into the next coil without a velocity corner.
        t=(f-45)/8
        start=circ(u1,v1,185);end=circ(u2,v2,-10)
        def tangent(u,v,degrees,speed):
            a=math.radians(degrees)
            return (-u*math.sin(a)+v*math.cos(a))*math.radians(speed)
        m=tangent(u1,v1,185,3)*8;n=tangent(u2,v2,-10,3)*8
        return ((2*t**3-3*t*t+1)*start+(t**3-2*t*t+t)*m+(-2*t**3+3*t*t)*end+(t**3-t*t)*n).normalized()
    if f<=70:return circ(u2,v2,curve(f,a2))
    t=curve(f,[(70,0,0),(83,1.035,0),(90,1,0)])
    start=circ(u2,v2,187);end=circ(u1,v1,14)
    q=start.rotation_difference(end)
    return Quaternion(q.axis,q.angle*t)@start

# Rotation-minimizing blade frame. Transport the edge normal along the
# direction curve so the wrist never rolls to chase a global up-vector.
blade_frames={};last_d=blade(1)
normal=u1.cross(v1).normalized();z=-last_d;x=normal.cross(z).normalized();y=z.cross(x)
last_q=Matrix((x,y,z)).transposed().to_quaternion()
first_q=last_q.copy()
for qframe in range(4,4*N+1):
    d=blade(qframe/4)
    last_q=last_d.rotation_difference(d)@last_q
    blade_frames[qframe]=last_q.copy();last_d=d
# Ease the accumulated transport twist back to the original guard roll.
twist=first_q@last_q.inverted();axis=blade(90)
roll=2*math.atan2(Vector((twist.x,twist.y,twist.z)).dot(axis),twist.w)
if roll>math.pi:roll-=2*math.pi
if roll< -math.pi:roll+=2*math.pi
for qframe,q in blade_frames.items():
    blend=curve(qframe/4,[(1,0,0),(70,0,0),(90,1,0)])
    blade_frames[qframe]=Quaternion(blade(qframe/4),roll*blend)@q

def quat_key(p,f):
    q=p.rotation_quaternion.copy()
    if p.name in prev and q.dot(prev[p.name])<0:q.negate()
    p.rotation_quaternion=q;prev[p.name]=q.copy()
    p.keyframe_insert('rotation_quaternion',frame=f)
    p.keyframe_insert('location',frame=f)

secondary=[p for p in rig.pose.bones if p.name.startswith('phys_')]
# Avoid evaluating the dense body mesh during every intermediate IK update.
body.hide_viewport=True
for quarter in range(4,4*N+1):
    f=quarter/4
    scene.frame_set(math.floor(f),subframe=f%1)
    for p in rig.pose.bones:p.matrix_basis.identity()
    update()
    yaw=25*drive(f)
    shift=path(f,[(1,(0,0,-.035),Z),(26,(.055,.04,-.075),Z),
       (34,(.045,-.02,-.035),(.001,-.022,-.003)),
       (40,(.075,-.28,-.17),Z),(46,(.07,-.30,-.11),Z),
       (57,(-.045,-.30,-.19),Z),(65,(-.065,-.31,-.14),Z),
       (79,(.015,-.29,-.045),Z),(84,(.006,-.29,-.071),Z),(90,(.01,-.29,-.060),Z)])
    p=rig.pose.bones['Hips'];p.matrix=AI@Matrix.Translation(shift)@rest['Hips'];update()
    rotate_world('Hips','Z',yaw)
    lean=curve(f,[(1,0,0),(29,-3,0),(40,10,0),(48,3,0),(58,11,0),(66,8,0),(81,-.6,0),(90,0,0)])
    rotate_world('Hips','X',lean*.35)
    torso=0
    for n,fac,lag in [('Spine02',.28,1),('Spine01',.34,2),('Spine',.38,3)]:
        ang=28*fac*drive(f,lag);torso+=ang
        rotate_world(n,'Z',ang);rotate_world(n,'X',lean*fac*.65)
        rotate_world(n,'Y',-drive(f,lag)*2*fac)
    rotate_world('RightShoulder','Z',6*drive(f,4))
    rotate_world('LeftShoulder','Z',4*drive(f,4))
    rotate_world('neck','Z',-(yaw+torso)*.62)
    rotate_world('Head','X',lean*.1)
    step=curve(f,[(1,0,0),(29,0,0),(35,.48,.11),(40,1,0)])
    lift=.13*math.sin(math.pi*step)
    for side in ['Left','Right']:
        target=heads[side+'Foot']+Vector((.09*step if side=='Left' else 0,-.49*step if side=='Left' else 0,lift if side=='Left' else 0))
        solve(side+'UpLeg',side+'Leg',side+'Foot',target,heads[side+'Leg']+Vector((0,-2,0)))
        orient(side+'Foot',foot_rot[side])
    wrist=path(f,hand_keys)
    pole=Vector((-1.25,-.25,2.20))+Vector((.25*drive(f,3),-.25*drive(f,3),.10*drive(f,3)))
    err=solve('RightArm','RightForeArm','RightHand',wrist,pole)
    grip=(AW@rig.pose.bones['RightHand'].matrix).translation
    direction=blade(f)
    sword_rotation=blade_frames[quarter].to_matrix().to_4x4()@BLADE_AXIS_FIX
    desired=Matrix.Translation(grip)@sword_rotation@Matrix.Diagonal((.01,.01,.01,1))@Matrix.Translation(-GRIP)
    rig.pose.bones['RightHand'].matrix=AI@desired@HAND_TO_SWORD.inverted();update()
    left=path(f,[(1,(.47,-.57,2.13),Z),(29,(.34,-.61,2.32),Z),
      (42,(.79,.03,1.94),(.0,.015,-.01)),(50,(.63,-.30,2.11),Z),
      (59,(.37,-.50,2.10),Z),(70,(.49,-.43,1.99),Z),(90,(.47,-.57,2.13),Z)])
    left_err=solve('LeftArm','LeftForeArm','LeftHand',left,(1.0,.10,1.94))
    # Root lag is 3f and each child is 2f later; damped follow-through is
    # driven by the difference between delayed and current body rotation.
    for p in secondary:
        depth=int(p.name.rsplit('_',1)[1]);delay=3+2*depth
        source=drive(f,delay)-drive(f,delay-3)
        family='hair' if 'hair' in p.name else ('cape' if 'cape' in p.name else 'robe')
        amp={'hair':8,'cape':10,'robe':5}[family]*(1-.055*depth)
        amp*=curve(f,[(1,1,0),(72,1,0),(90,0,0)])
        wave=source*amp
        # Taper motion near the floor, but keep all 97 joints alive.
        recovery=math.exp(-max(0,f-delay-60)/8)*math.sin(max(0,f-delay-60)*.42)*1.4 if f-delay>60 else 0
        worldq=Quaternion((0,0,1),math.radians(wave+recovery*curve(f,[(1,1,0),(72,1,0),(90,0,0)])))@Quaternion((1,0,0),math.radians(abs(source)*amp*.3))
        rq=rest[p.name].to_quaternion()
        p.rotation_quaternion=rq.inverted()@worldq@rq
    for p in rig.pose.bones:quat_key(p,f)
    update()
    if f%1==0:samples.append({'frame':int(f),'hips_yaw':yaw,'torso_yaw':torso,'tip':list(sw.matrix_world@TIP),'grip':list(sw.matrix_world@GRIP),'wrist_reach_error':err,'left_reach_error':left_err,
      'joints':{n:list((AW@rig.pose.bones[n].matrix).translation) for n in ['Hips','Spine02','Spine01','Spine','RightShoulder','RightArm','RightForeArm','RightHand']},
      'feet':{s:list((AW@rig.pose.bones[s+'Foot'].matrix).translation) for s in ['Left','Right']}})
body.hide_viewport=False
update()
act=rig.animation_data.action;act.name='Astra_Godwyn_XSlash_V2'
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for k in fc.keyframe_points:
                    k.interpolation='BEZIER';k.handle_left_type='AUTO_CLAMPED';k.handle_right_type='AUTO_CLAMPED'

# A fine temporal ribbon of the ACTUAL evaluated blade. No decorative X lines.
# It is visible for only its own frame, like a 0.7-frame shutter, and fades
# towards the old sample and the handle. EEVEE native blur is also enabled.
scene.render.use_motion_blur=True
scene.render.motion_blur_shutter=.55
print('MOTION_BLUR',scene.render.use_motion_blur,flush=True)
mat=bpy.data.materials.new('Astra V2 temporal blade blur');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear();o=nodes.new('ShaderNodeOutputMaterial');mix=nodes.new('ShaderNodeMixShader');trans=nodes.new('ShaderNodeBsdfTransparent');emit=nodes.new('ShaderNodeEmission');attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='fade'
emit.inputs['Color'].default_value=(.7,.45,.16,1);emit.inputs['Strength'].default_value=1.2
mat.node_tree.links.new(attr.outputs['Alpha'],mix.inputs[0]);mat.node_tree.links.new(trans.outputs[0],mix.inputs[1]);mat.node_tree.links.new(emit.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],o.inputs[0])
mat.surface_render_method='BLENDED';mat.use_transparent_shadow=False
for start,end in CUTS:
    for f in range(start+1,end+3):
        verts=[];faces=[];alphas=[]
        for j in range(13):
            t=f-.70+.70*j/12
            scene.frame_set(math.floor(t),subframe=t%1);update()
            g=sw.matrix_world@GRIP;tip=sw.matrix_world@TIP
            for radial in [.30,.88,1.0]:
                verts.append(g.lerp(tip,radial));alphas.append((j/12)**1.5*.20*(1 if radial>.5 else .0))
        for j in range(12):
            for k in range(2):a=j*3+k;faces.append((a,a+1,a+4,a+3))
        mesh=bpy.data.meshes.new(f'Astra_v2_blur_{f}');mesh.from_pydata(verts,[],faces);mesh.materials.append(mat)
        col=mesh.color_attributes.new(name='fade',type='FLOAT_COLOR',domain='POINT')
        for c,a in zip(col.data,alphas):c.color=(1,1,1,a)
        obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj)
        for frame,hide in [(1,True),(f-1,True),(f,False),(f+1,True)]:
            obj.hide_render=hide;obj.hide_viewport=hide;obj.keyframe_insert('hide_render',frame=frame);obj.keyframe_insert('hide_viewport',frame=frame)
metrics={'version':VERSION,'fps':30,'frames':N,'duration_seconds':N/30,'cuts':CUTS,'secondary_bones':len(secondary),'blade_length':LENGTH,'max_wrist_reach_error':max(s['wrist_reach_error'] for s in samples),'max_left_reach_error':max(s['left_reach_error'] for s in samples),'samples':samples}
(OUT/'v2_metrics.json').write_text(json.dumps(metrics,indent=2))
scene.frame_set(1);camera('front',5.6,(0,-.2,2.0))
scene.camera.location=(0,-11,2.5);scene.camera.rotation_euler=(Vector((0,-.2,2.0))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.type='ORTHO';scene.camera.data.ortho_scale=5.4
scene.render.engine='BLENDER_EEVEE'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'models/astra_xslash_v2_wip.blend'))
print('ASTRA V2 BUILD',json.dumps({k:v for k,v in metrics.items() if k!='samples'}),flush=True)
