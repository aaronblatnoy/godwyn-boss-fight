"""Targeted animation-only correction of the approved final scene.

Inputs are immutable prefix + sampled action. Changes: existing rig F-curves and
existing blur-object translation keys only. No geometry/settings/camera writes.
"""
import bpy,sys,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'models/astra_xslash_v2_final_prefix.blend'
TARGET=ROOT/'models/astra_xslash_v2_final_wip.blend'
data=json.loads((ROOT/'renders/astra/naturalness_before.json').read_text()); rows=data['rows'];N=len(rows)
surf=json.loads((ROOT/'renders/astra/naturalness_surface_before.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.context.scene
rig=bpy.data.objects['Armature'];AW=rig.matrix_world.copy();AI=AW.inverted()
mesh_visibility=[(o,o.hide_viewport) for o in scene.objects if o.type=='MESH']
for o,_ in mesh_visibility:o.hide_viewport=True
rest={n:Matrix(b['matrix']) for n,b in data['rest'].items()};rh={n:m.translation for n,m in rest.items()}
fcs=[fc for la in rig.animation_data.action.layers for st in la.strips for bag in st.channelbags for fc in bag.fcurves]
fcmap={(fc.data_path,fc.array_index):fc for fc in fcs}
changed=set(); output={}; wrist_delta=[]
def update():bpy.context.view_layer.update()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def curve(f,keys):
    if f<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if f<=b:return x+(y-x)*smooth((f-a)/(b-a))
    return keys[-1][1]
def gauss(a,sigma=4):
    radius=int(sigma*3);w=np.exp(-np.arange(-radius,radius+1)**2/(2*sigma*sigma));w/=sum(w)
    pad=np.pad(np.array(a),((radius,radius),(0,0)),mode='edge')
    return np.array([sum(pad[i:i+len(w)]*w[:,None]) for i in range(len(a))])
def set_world(n,pos,q):
    rig.pose.bones[n].matrix=AI@Matrix.LocRotScale(Vector(pos),q,Vector((.01,.01,.01)));update()
def rotate_world(n,q):
    m=AW@rig.pose.bones[n].matrix
    set_world(n,m.translation,q@m.to_quaternion())
def capture(n):
    p=rig.pose.bones[n];return {'q':list(p.rotation_quaternion),'loc':list(p.location)}
def frame_basis(direction,normal):
    x=direction.normalized();y=(normal-x*normal.dot(x)).normalized();z=x.cross(y)
    return Matrix((x,y,z)).transposed()
def orient_segment(n,child,pos,end,normal,restnormal):
    delta=frame_basis(Vector(end)-pos,normal)@frame_basis(rh[child]-rh[n],restnormal).transposed()
    set_world(n,pos,(delta@rest[n].to_3x3().normalized()).to_quaternion())
def leg_solve(side,target):
    a,b,c=[side+x for x in ['UpLeg','Leg','Foot']]
    h=(AW@rig.pose.bones[a].matrix).translation;e=(AW@rig.pose.bones[b].matrix).translation
    footq=(AW@rig.pose.bones[c].matrix).to_quaternion();l1=(rh[b]-rh[a]).length;l2=(rh[c]-rh[b]).length
    v=Vector(target)-h;axis=v.normalized();d=min(v.length,l1+l2-.001)
    al=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-al*al));bend=e-h; bend=(bend-axis*bend.dot(axis)).normalized();joint=h+al*axis+height*bend
    for n,ch,end in [(a,b,joint),(b,c,h+d*axis)]:
        m=AW@rig.pose.bones[n].matrix;cur=(AW@rig.pose.bones[ch].matrix).translation-m.translation
        set_world(n,m.translation,cur.rotation_difference(end-m.translation)@m.to_quaternion())
    m=AW@rig.pose.bones[c].matrix;set_world(c,m.translation,footq)

# Collect edited trunk/shoulder/feet and hand targets before solving arm poles.
frames=[]
for i,row in enumerate(rows):
    f=row['f'];scene.frame_set(int(f),subframe=f%1);update()
    if i%80==0:print('BASE',f,flush=True)
    # Wind-up counterweight: 3.5 deg distributed through the existing spine.
    fade=curve(f,[(1,0),(12,.6),(22,1),(30,1),(37,0),(90,0)])
    if fade:
        # Blade is upper-left during this window: lean away in world +X, with
        # a small rearward component. Existing forward pull during cuts stays.
        axis=Vector((.18,1,0)).normalized()
        for n,part in [('Spine02',.5),('Spine01',.3),('Spine',.2)]:
            rotate_world(n,Quaternion(axis,math.radians(3.5*fade*part)));changed.add(n)
    # Separate clavicle timing by 2 frames. Keep the off-hand target independent.
    p=rig.pose.bones['LeftShoulder']
    for j in range(4):p.rotation_quaternion[j]=fcmap[(p.path_from_id('rotation_quaternion'),j)].evaluate(max(1,f-2))
    update();changed.add(p.name)
    # Sole clearance correction: grounded windows only, smoothly carried into
    # the swing. Re-solving the two links retains segment lengths and toe axes.
    for side in ['Left','Right']:
        base=np.array([z['feet'][side+'Foot']['min_clearance_m'] for z in surf['rows']])
        # 1.5mm clearance; avoid chasing tiny skin noise with unfiltered keys.
        corr=np.interp(f,np.arange(1,91),.0015-base)
        if side=='Left' and 29<f<40:
            corr=curve(f,[(29,.0015-base[28]),(40,.0015-base[39])])
        target=Vector(row['bones'][side+'Foot']['head']);target.z+=corr
        leg_solve(side,target)
        changed.update(side+x for x in ['UpLeg','Leg','Foot'])
    hands={};deltas={}
    for side in ['Left','Right']:
        h=Vector(row['bones'][side+'Hand']['head']);hq=Quaternion(row['bones'][side+'Hand']['world_q'])
        if side=='Right' and f>=80:
            # One damped arrival from F80 to F90, replacing the F82/F86/F90 bob.
            first=Vector(rows[316]['bones']['RightHand']['head']);last=Vector(rows[-1]['bones']['RightHand']['head'])
            vel=(Vector(rows[316]['bones']['RightHand']['head'])-Vector(rows[315]['bones']['RightHand']['head']))*4
            t=(f-80)/10;h=(2*t**3-3*t*t+1)*first+(t**3-2*t*t+t)*10*vel+(-2*t**3+3*t*t)*last
        shoulder=(AW@rig.pose.bones[side+'Arm'].matrix).translation.copy()
        # Correct the momentary 166.5-degree fold at cut 1. A smooth forward
        # extension gives the armored elbow space; it changes no mesh data.
        if side=='Right':h.y-=curve(f,[(1,0),(36.5,0),(38.5,.18),(39.5,.18),(42,0),(90,0)])
        hands[side]={'pos':h,'q':hq,'shoulder':shoulder,'old_elbow':Vector(row['bones'][side+'ForeArm']['head'])}
        deltas[side]=h-Vector(row['bones'][side+'Hand']['head'])
    frames.append({'f':f,'base':{n:capture(n) for n in changed},'hands':hands})
    wrist_delta.append(list(deltas['Right']))

# Stable elbow circles: select a continuous path with anatomical wrist and
# torso-clearance costs. Dynamic programming avoids singular per-frame IK poles.
for side in ['Right','Left']:
    candidates=[];costs=[];axes=[];centres=[];heights=[]
    a,b,c=[side+x for x in ['Arm','ForeArm','Hand']]
    l1=(rh[b]-rh[a]).length;l2=(rh[c]-rh[b]).length
    angles=np.arange(96)*2*math.pi/96
    for rec in frames:
        hh=rec['hands'][side];s=np.array(hh['shoulder']);w=np.array(hh['pos']);v=w-s;d=np.linalg.norm(v);axis=v/d
        al=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(.000001,l1*l1-al*al));center=s+al*axis
        preferred=np.array([-.12 if side=='Right' else .7,-.65,-1.0]);u=preferred-axis*np.dot(preferred,axis);u/=np.linalg.norm(u);vv=np.cross(axis,u)
        cand=center+height*(np.cos(angles)[:,None]*u+np.sin(angles)[:,None]*vv)
        if side=='Right':
            hand=np.array(hh['q']@Vector((0,1,0)));fore=w-cand;fore/=np.linalg.norm(fore,axis=1)[:,None]
            bends=np.degrees(np.arccos(np.clip(fore@hand,-1,1)))
            # Bend <=65 preferred; 70 deg hard-looking bend penalized heavily.
            cost=12*np.maximum((bends-65)/20,0)**2+.12*(1-np.cos(angles))
            # Favor the front of the torso over burying the elbow in the ribs.
            cost+=4*np.maximum((cand[:,1]-(s[1]-.06))/.22,0)**2
            cost+=2*np.maximum((cand[:,2]-(s[2]-.07))/.20,0)**2
        else:
            cost=np.sum((cand-np.array(hh['old_elbow']))**2,axis=1)/.09**2+.15*(1-np.cos(angles))
        candidates.append(cand);costs.append(cost);axes.append(axis);centres.append(center);heights.append(height)
    parents=[];score=costs[0].copy()
    for i in range(1,N):
        dist=np.sum((candidates[i][:,None,:]-candidates[i-1][None,:,:])**2,axis=2)
        trans=score[None,:]+dist/.028**2*2
        pick=trans.argmin(axis=1);score=costs[i]+trans[np.arange(96),pick];parents.append(pick)
    selected=[int(score.argmin())]
    for par in reversed(parents):selected.append(int(par[selected[-1]]))
    selected.reverse()
    elbows=gauss([candidates[i][k] for i,k in enumerate(selected)],sigma=3.0 if side=='Right' else 4.5)
    for i,rec in enumerate(frames):
        v=elbows[i]-centres[i];axis=axes[i];v-=axis*np.dot(v,axis);v/=np.linalg.norm(v)
        rec['hands'][side]['elbow']=Vector(centres[i]+v*heights[i])

# Bake edited transforms onto the EXISTING quarter-frame channels.
# Every unchanged bone keeps its exact original F-curves.
for i,rec in enumerate(frames):
    if i%80==0:print('ARMS',rec['f'],flush=True)
    f=rec['f'];scene.frame_set(int(f),subframe=f%1)
    for n,state in rec['base'].items():
        p=rig.pose.bones[n];p.rotation_quaternion=state['q'];p.location=state['loc']
    update()
    for side in ['Right','Left']:
        a,b,c=[side+x for x in ['Arm','ForeArm','Hand']];hh=rec['hands'][side]
        s,e,w=hh['shoulder'],hh['elbow'],hh['pos']
        norm=(e-s).cross(w-e).normalized();rn=(rh[b]-rh[a]).cross(rh[c]-rh[b]).normalized()
        orient_segment(a,b,s,e,norm,rn);orient_segment(b,c,e,w,norm,rn)
        if side=='Right':set_world(c,w,hh['q'])
        else:
            # Preserve its neutral anatomical rest relation; add a small delayed
            # off-hand response (the original wrist was constant for 90 frames).
            rel=rest[b].to_quaternion().inverted()@rest[c].to_quaternion()
            fq=(AW@rig.pose.bones[b].matrix).to_quaternion()
            offset=curve(f,[(1,0),(27,-2),(37,-2),(45,2.5),(55,-1.5),(65,1),(80,.3),(90,0)])
            set_world(c,w,fq@rel@Quaternion((0,0,1),math.radians(offset)))
        changed.update([a,b,c])
    for n in changed:output.setdefault(n,[]).append(capture(n))

# Cloth: preserve the belt/spine hierarchy and use cumulative delayed yaw
# compensation instead of summing a pulse that cancels down the entire chain.
hipq=[Quaternion(row['bones']['Hips']['world_q']) for row in rows]
spineq=[Quaternion(row['bones']['Spine']['world_q']) for row in rows]
def yaw_signal(qs):
    vals=[]
    for q in qs:
        dq=q@qs[0].inverted();vals.append(2*math.atan2(dq.z,dq.w))
    return np.unwrap(vals)
def cloth_response(yaw,delay,cap):
    # Causal critically damped response at quarter-frame sampling.
    x=0.;vel=0.;ans=[];omega=.42
    for i,y in enumerate(yaw):
        target=float(np.interp(i-delay*4,np.arange(N),yaw))
        vel+=(omega*omega*(target-x)-2*omega*vel)*.25;x+=vel*.25
        ans.append(cap*math.tanh(.62*(x-y)/cap))
    return np.array(ans)
hy=yaw_signal(hipq);sy=yaw_signal(spineq)
for n in data['rest']:
    if not (n.startswith('phys_robe') or n.startswith('phys_cape')):continue
    depth=int(n.rsplit('_',1)[1]);cape='cape' in n;yaw=sy if cape else hy
    cap=math.radians(24 if cape else 18)
    side_delay=.35 if '_L_' in n else (.85 if '_R_' in n else 0)
    cumulative=cloth_response(yaw,.8+side_delay+depth*.8,cap)
    parent=cloth_response(yaw,.8+side_delay+(depth-1)*.8,cap) if depth else np.zeros(N)
    delta=cumulative-parent;rq=rest[n].to_quaternion()
    for i,rec in enumerate(frames):
        # Replace the pulse/late jiggle with a damped yaw response.
        world=Quaternion((0,0,1),float(delta[i]))
        q=rq.inverted()@world@rq
        # A slow residual fade reaches rest without a forced oscillatory wobble.
        fade=1-smooth((rec['f']-76)/14)
        q=Quaternion((1,0,0,0)).slerp(q,fade)
        output.setdefault(n,[]).append({'q':list(q),'loc':rows[i]['bones'][n]['loc']})
    changed.add(n)

for n,states in output.items():
    previous=None
    for state in states:
        q=Quaternion(state['q']);q.normalize()
        if previous and q.dot(previous)<0:q.negate()
        state['q']=list(q);previous=q
    for channel,key,length in [('rotation_quaternion','q',4),('location','loc',3)]:
        for j in range(length):
            fc=fcmap[(rig.pose.bones[n].path_from_id(channel),j)]
            assert len(fc.keyframe_points)==N
            for kp,state in zip(fc.keyframe_points,states):
                kp.co.y=state[key][j];kp.interpolation='BEZIER';kp.handle_left_type='AUTO_CLAMPED';kp.handle_right_type='AUTO_CLAMPED'
            fc.update()
# Existing temporal ribbons follow the corrected grip translation. Geometry,
# topology/material and visibility are untouched. Use the shutter midpoint.
for obj in scene.objects:
    if obj.name.startswith('Astra_v2_blur_'):
        f=int(obj.name.rsplit('_',1)[1]);t=f-.35
        delta=Vector([np.interp(t,[r['f'] for r in rows],np.array(wrist_delta)[:,j]) for j in range(3)])
        if delta.length>.00001:
            obj.location=delta;obj.keyframe_insert('location',frame=f)
rig.animation_data.action.name='Astra_Godwyn_XSlash_V2_Final_Naturalness'
for o,hidden in mesh_visibility:o.hide_viewport=hidden
scene.frame_set(1);update()
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))
report={'source':str(BASE),'target':str(TARGET),'changed_bones':sorted(changed),'quarter_samples':N,'blade_grip_corrections':[{'frame':r['f'],'delta':d} for r,d in zip(rows,wrist_delta) if r['f'].is_integer() and Vector(d).length>.0001], 'scope':'existing rig and blur-object animation keys only; saved camera/render/material/mesh untouched'}
(ROOT/'renders/astra/naturalness_fix_log.json').write_text(json.dumps(report,indent=2))
print('NATURALNESS FIX',json.dumps(report),flush=True)
