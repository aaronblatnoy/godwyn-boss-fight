"""Shared moveset authoring: joint-head IK, quarter-frame baking, mesh contact.
No network/dependencies. Only new move paths are writable. Coordinates in metres.
Run per-move build with Blender 5.2.1 --background --gpu-backend metal.
"""
import sys, math, json, hashlib
from pathlib import Path
sys.dont_write_bytecode=True
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'renders/astra/moves'
Z=Vector((0,0,1)); I=Quaternion((1,0,0,0))
def smooth(t):
    t=max(0,min(1,t));return t*t*t*(10+t*(-15+6*t))
def curve(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]
def hermite(t,keys):
    if t<=keys[0][0]:return keys[0][1]+(t-keys[0][0])*keys[0][2]
    if t>=keys[-1][0]:return keys[-1][1]+(t-keys[-1][0])*keys[-1][2]
    for (a,x,m),(b,y,n) in zip(keys,keys[1:]):
        if t<=b:
            u=(t-a)/(b-a);h=b-a
            return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*h*m+(-2*u**3+3*u*u)*y+(u**3-u*u)*h*n

def vec(t,keys):return Vector([curve(t,[(f,p[k]) for f,p in keys]) for k in range(3)])
def yaw(deg):return Quaternion(Z,math.radians(deg))
def frame_basis(direction,normal):
    x=direction.normalized();y=(normal-x*normal.dot(x)).normalized();z=x.cross(y)
    return Matrix((x,y,z)).transposed()
def hashfile(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

class Builder:
    def __init__(self,name,N,loop=False,travel=(0,0,0)):
        self.name=name;self.N=N;self.loop=loop;self.travel=Vector(travel);OUT.mkdir(parents=True,exist_ok=True)
        self.source=ROOT/'models/astra_move_character_base.blend'
        if not self.source.exists():
            import shutil
            shutil.copyfile(ROOT/'models/astra_character_v2_prechar2.blend',self.source)
        self.sha=hashfile(self.source)
        bpy.ops.wm.open_mainfile(filepath=str(self.source))
        self.s=bpy.context.scene;self.r=bpy.data.objects['Armature'];self.body=bpy.data.objects['char1'];self.sw=bpy.data.objects['Godwyn_Sword']
        from astra_move_grip_fix import fix_grip
        fix_grip()
        self.r.animation_data_clear()
        for p in self.r.pose.bones:p.matrix_basis.identity();p.rotation_mode='QUATERNION'
        self.update();self.AW=self.r.matrix_world.copy();self.AI=self.AW.inverted()
        self.rest={p.name:(self.AW@p.matrix).copy() for p in self.r.pose.bones};self.h={n:m.translation.copy() for n,m in self.rest.items()}
        # Source sword is rigidly weighted to RightHand. Fit source-coordinate attribute.
        sw=self.sw;src=np.array([p.vector[:] for p in sw.data.attributes['astra_sword_source'].data]);loc=np.array([v.co[:] for v in sw.data.vertices])
        fit=np.linalg.lstsq(np.column_stack((src,np.ones(len(src)))),loc,rcond=None)[0]
        self.tip=sw.data.vertices[int(src[:,2].argmin())].co.copy();self.grip=Vector(np.array([61.2,-66.3,167,1])@fit)
        tip=sw.matrix_world@self.tip;grip=sw.matrix_world@self.grip
        self.blade_rest=(tip-grip).normalized();self.blade_length=(tip-grip).length
        blade=loc[(src[:,2]>30)&(src[:,2]<145)];_,_,axes=np.linalg.svd(blade-blade.mean(0),full_matrices=False)
        localD=(self.tip-self.grip).normalized();localE=Vector(axes[-1]).cross(localD).normalized()
        self.edge_rest=(sw.matrix_world.to_3x3()@localE).normalized()
        self.blade_basis=Matrix((self.edge_rest,self.blade_rest.cross(self.edge_rest),self.blade_rest)).transposed()
        self.footq={}
        for side in ['Left','Right']:
            v=self.h[side+'ToeBase']-self.h[side+'Foot'];ang=math.atan2(-v.x,-v.y)
            self.footq[side]=Quaternion(Z,ang)@self.rest[side+'Foot'].to_quaternion()
        self.visible=[(o,o.hide_viewport) for o in self.s.objects if o.type in ['MESH','CURVES']]
        for o,_ in self.visible:o.hide_viewport=True
        self.previous={};self.records=[];self.s.frame_start=1;self.s.frame_end=N if not loop else N-1;self.s.render.fps=30
        self.foot_correction={s:np.zeros(N) for s in ['Left','Right']};self.hem_correction={}
        groups={g.index:g.name for g in self.body.vertex_groups};self.soles={};self.families={}
        for side in ['Left','Right']:
            self.soles[side]=[v.index for v in self.body.data.vertices if (self.body.matrix_world@v.co).z<.13 and sum(g.weight for g in v.groups if groups[g.group] in [side+'Foot',side+'ToeBase'])>.6]
        for p in self.r.pose.bones:
            if p.name.startswith(('phys_robe','phys_cape')):self.families.setdefault(p.name.rsplit('_',1)[0],{'bones':[],'vertices':[]})['bones'].append(p.name)
        for v in self.body.data.vertices:
            if (self.body.matrix_world@v.co).z>.4:continue
            weights={}
            for g in v.groups:
                fam=groups[g.group].rsplit('_',1)[0]
                if fam in self.families:weights[fam]=weights.get(fam,0)+g.weight
            for fam,w in weights.items():
                if w>.55:self.families[fam]['vertices'].append(v.index)
        self.families={k:v for k,v in self.families.items() if len(v['vertices'])>10}
        for k,v in self.families.items():v['bones'].sort();self.hem_correction[k]=np.zeros(N)
    def update(self):bpy.context.view_layer.update()
    def world(self,n):return self.AW@self.r.pose.bones[n].matrix
    def set(self,n,pos,q):
        self.r.pose.bones[n].matrix=self.AI@Matrix.LocRotScale(Vector(pos),q,Vector((.01,.01,.01)));self.update()
    def rotate(self,n,q):
        m=self.world(n);self.set(n,m.translation,q@m.to_quaternion())
    def segment(self,n,child,pos,end,normal,restnormal):
        delta=frame_basis(Vector(end)-pos,normal)@frame_basis(self.h[child]-self.h[n],restnormal).transposed()
        self.set(n,pos,(delta@self.rest[n].to_3x3().normalized()).to_quaternion())
    def limb(self,side,kind,target,pole,handq=None):
        a,b,c=[side+x for x in (['UpLeg','Leg','Foot'] if kind=='leg' else ['Arm','ForeArm','Hand'])]
        h=self.world(a).translation;l1=(self.h[b]-self.h[a]).length;l2=(self.h[c]-self.h[b]).length
        v=Vector(target)-h;axis=v.normalized();d=max(.08,min(v.length,l1+l2-.004));end=h+d*axis
        along=(l1*l1-l2*l2+d*d)/(2*d);height=math.sqrt(max(0,l1*l1-along*along))
        bend=Vector(pole);bend=(bend-axis*bend.dot(axis)).normalized();joint=h+along*axis+height*bend
        normal=(joint-h).cross(end-joint).normalized();rn=(self.h[b]-self.h[a]).cross(self.h[c]-self.h[b]).normalized()
        self.segment(a,b,h,joint,normal,rn);self.segment(b,c,joint,end,normal,rn)
        if handq:self.set(c,end,handq)
        return (end-Vector(target)).length
    def orient_blade(self,direction,edge=None):
        if edge is not None:
            d=Vector(direction).normalized();e=(Vector(edge)-d*Vector(edge).dot(d)).normalized();n=d.cross(e)
            return (Matrix((e,n,d)).transposed()@self.blade_basis.transposed()).to_quaternion()@self.rest['RightHand'].to_quaternion()
        return self.blade_rest.rotation_difference(Vector(direction).normalized())@self.rest['RightHand'].to_quaternion()
    def sword_points(self):
        deform=self.AW@self.r.pose.bones['RightHand'].matrix@self.r.data.bones['RightHand'].matrix_local.inverted()@self.AI@self.sw.matrix_world
        return deform@self.tip,deform@self.grip
    def pose(self,f,definition):
        for p in self.r.pose.bones:p.matrix_basis.identity()
        self.update();d=definition(f);root=Vector(d['root']);angle=d['yaw'];rot=yaw(angle)
        self.set('Hips',self.h['Hips']+root,rot@Quaternion((1,0,0),math.radians(d.get('lean',0)*.3))@self.rest['Hips'].to_quaternion())
        for n,weight,lag in [('Spine02',.30,1),('Spine01',.34,2),('Spine',.36,3)]:
            dd=definition(f-lag);self.rotate(n,yaw(dd.get('twist',0)*weight)@Quaternion((1,0,0),math.radians(dd.get('lean',0)*.7*weight)))
            self.rotate(n,Quaternion((0,1,0),math.radians(dd.get('sway',0)*weight)))
        for side,lag in [('Right',4),('Left',6.25)]:
            dd=definition(f-lag);self.rotate(side+'Shoulder',yaw(dd.get('shoulder',0)*(1 if side=='Right' else .62)))
        self.rotate('neck',yaw(d.get('look',-d.get('twist',0)*.65)))
        self.rotate('Head',Quaternion((1,0,0),math.radians(d.get('head_pitch',-1))))
        for side in ['Left','Right']:
            target=Vector(d['feet'][side]);target.z+=float(np.interp(f,np.arange(1,self.N+1),self.foot_correction[side]))
            self.limb(side,'leg',target,yaw(d.get('foot_yaw',{}).get(side,angle))@Vector((0,-1,0)))
            self.set(side+'Foot',self.world(side+'Foot').translation,yaw(d.get('foot_yaw',{}).get(side,angle))@self.footq[side])
        # Desired paths are in the moving pelvis frame, preserving limb reach.
        handq=rot@(d['blade_q'] if 'blade_q' in d else self.orient_blade(d['blade']))
        right_target=root+rot@Vector(d['right']);pole=rot@Vector(d.get('right_pole',(-.48,-.75,-.5)))
        if d.get('support_wrist'):
            axis=(right_target-self.world('RightArm').translation).normalized();long=handq@Vector((0,1,0))
            natural=(pole-axis*pole.dot(axis)).normalized();supported=-(long-axis*long.dot(axis))
            if d.get('support_wrist')=='limited' and supported.length>.03:
                # Keep the natural elbow plane unless the wrist needs support.
                # Rotating to an unconstrained optimum caused elbow-circle flips
                # whenever the hand axis passed through the reach axis.
                length=(right_target-self.world('RightArm').translation).length
                l1=(self.h['RightForeArm']-self.h['RightArm']).length;l2=(self.h['RightHand']-self.h['RightForeArm']).length
                length=max(.08,min(length,l1+l2-.004));along=(l1*l1-l2*l2+length*length)/(2*length);height=math.sqrt(max(0,l1*l1-along*along))
                best=supported.normalized();turn=math.atan2(axis.dot(natural.cross(best)),natural.dot(best))
                def bend_at(u):return Quaternion(axis,turn*u)@natural
                def wrist_at(u):return math.degrees(((length-along)*axis-height*bend_at(u)).angle(long))
                limit=d.get('wrist_limit',55);amount=0
                if wrist_at(0)>limit:
                    lo=0.;hi=1.
                    if wrist_at(1)>limit:amount=1.
                    else:
                        for _ in range(20):
                            mid=(lo+hi)/2
                            if wrist_at(mid)>limit:lo=mid
                            else:hi=mid
                        amount=hi
                pole=bend_at(amount)
            else:pole=natural*.15+supported.normalized()*.85 if supported.length>.03 else natural
        self.limb('Right','arm',right_target,pole,handq)
        self.limb('Left','arm',root+rot@Vector(d['left']),rot@Vector((.6,-.5,-.8)))
        rel=self.rest['LeftForeArm'].to_quaternion().inverted()@self.rest['LeftHand'].to_quaternion()
        self.set('LeftHand',self.world('LeftHand').translation,self.world('LeftForeArm').to_quaternion()@rel@Quaternion((0,0,1),math.radians(d.get('left_wrist',0))))
        for p in self.r.pose.bones:
            if not p.name.startswith('phys_'):continue
            depth=int(p.name.rsplit('_',1)[1]);fam=p.name.rsplit('_',1)[0];cape='cape' in p.name;hair='hair' in p.name
            side=.45 if '_L_' in p.name else (1.0 if '_R_' in p.name else 0)
            def cumulative(k):
                if k<0:return (0,0,0)
                delay=2+1.1*k+side;dd=definition(f-delay)
                # Cumulative lag avoids the cancelling local pulses found in v2.
                lagangle=(dd['yaw']-d['yaw'])*.60
                if cape or hair:lagangle+=(dd.get('twist',0)-d.get('twist',0))*.65
                cap=25 if cape else (16 if hair else 19)
                lagangle=cap*math.tanh(lagangle/cap)
                drift=d.get('cloth_drift',0)*math.sin((f-delay)*2*math.pi/(self.N-1))*(k+1)/7
                trail=dd.get('trail',0)*(k+1)/7
                return lagangle+drift,trail,dd.get('cloth_sway',0)*(k+1)/7
            a=cumulative(depth);b=cumulative(depth-1);world=yaw(a[0]-b[0])@Quaternion((1,0,0),math.radians(a[1]-b[1]))@Quaternion((0,1,0),math.radians(a[2]-b[2]))
            rq=self.rest[p.name].to_quaternion();p.rotation_quaternion=rq.inverted()@world@rq
            if fam in self.hem_correction and depth>2:
                needed=float(np.interp(f,np.arange(1,self.N+1),self.hem_correction[fam]));last=len(self.families[fam]['bones'])-1
                a=smooth((depth-2)/(last-2));b=smooth((depth-3)/(last-2))
                self.update();m=self.world(p.name);m.translation.z+=needed*(a-b);self.r.pose.bones[p.name].matrix=self.AI@m
        self.update()
        return d
    def bake(self,definition):
        self.r.animation_data_clear();self.previous={}
        for qf in range(4,4*self.N+1):
            f=qf/4;self.s.frame_set(int(f),subframe=f%1);self.pose(f,definition)
            for p in self.r.pose.bones:
                q=p.rotation_quaternion.copy()
                if p.name in self.previous and q.dot(self.previous[p.name])<0:q.negate()
                self.previous[p.name]=q.copy();p.rotation_quaternion=q
                p.keyframe_insert('rotation_quaternion',frame=f);p.keyframe_insert('location',frame=f)
            if qf%120==0:print('BAKE',self.name,f,flush=True)
        act=self.r.animation_data.action;act.name='Astra_Move_'+self.name
        for la in act.layers:
            for st in la.strips:
                for bag in st.channelbags:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:kp.interpolation='BEZIER';kp.handle_left_type=kp.handle_right_type='AUTO'
                        if self.loop:
                            mod=fc.modifiers.new('CYCLES');mod.mode_before=mod.mode_after='REPEAT_OFFSET'
        if self.loop:
            from astra_move_loop_seam import close_tangents
            close_tangents(act)
    def surfaces(self):
        self.body.hide_viewport=False;out=[]
        for f in range(1,self.N+1):
            self.s.frame_set(f);self.update();ob=self.body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh()
            co=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',co);co=co.reshape(-1,3);M=np.array(ob.matrix_world);co=co@M[:3,:3].T+M[:3,3]
            out.append({'frame':f,'sole':{k:float(co[v,2].min())+.015 for k,v in self.soles.items()},'hem':{k:float(co[v['vertices'],2].min())+.015 for k,v in self.families.items()}});ob.to_mesh_clear()
        self.body.hide_viewport=True;return out
    def build(self,definition,meta):
        self.definition=definition;self.meta=meta
        if '--probe' in sys.argv:
            from astra_move_pose_probe import probe
            return probe(self,definition)
        self.bake(definition);before=self.surfaces()
        for side in ['Left','Right']:
            # Correct the measured sole through BOTH stance and swing. A constant
            # last-stance offset caused an artificial pop at the next landing.
            self.foot_correction[side]=np.array([.0025+max(0,definition(r['frame'])['feet'][side].z-self.h[side+'Foot'].z)-r['sole'][side] for r in before])
        for fam in self.families:self.hem_correction[fam]=np.array([max(0,.003-r['hem'][fam])*1.07 for r in before])
        if self.loop:
            for v in list(self.foot_correction.values())+list(self.hem_correction.values()):v[-1]=v[0]
        self.bake(definition);after=self.surfaces()
        for fam in self.families:
            self.hem_correction[fam]+=np.array([max(0,.002-r['hem'][fam])*(1.35 if self.loop else 2.2) for r in after])
        if self.loop:
            for v in self.hem_correction.values():v[-1]=v[0]
        self.bake(definition);after=self.surfaces()
        (OUT/f'{self.name}_contacts.json').write_text(json.dumps({'before':before,'after':after},indent=2))
        for o,hidden in self.visible:o.hide_viewport=hidden
        self.stage();self.ribbons(meta.get('active',[]));self.s.frame_set(1);self.update()
        self.s['astra_move']=self.name;self.s['source_sha256']=self.sha;self.s['move_meta']=json.dumps(meta)
        self.s['loop_period_frames']=self.N-1 if self.loop else 0;self.s['cycle_root_displacement']=list(self.travel)
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/f'models/astra_move_{self.name}_wip.blend'))
        assert hashfile(self.source)==self.sha
        meta['planted']={side:[bool(definition(f)['planted'][side]) for f in range(1,self.N+1)] for side in ['Left','Right']}
        meta.update(name=self.name,frames=self.s.frame_end,samples_end=self.N,loop=self.loop,travel=list(self.travel),source_sha256=self.sha)
        (OUT/f'{self.name}_manifest.json').write_text(json.dumps(meta,indent=2))
        print('BUILD SAVED',self.name,flush=True)
    def stage(self):
        s=self.s
        s.render.engine='BLENDER_EEVEE';s.render.resolution_x=768;s.render.resolution_y=768;s.render.resolution_percentage=100;s.eevee.taa_render_samples=32
        s.render.image_settings.file_format='PNG';s.render.use_motion_blur=not self.loop;s.render.motion_blur_shutter=.45;s.render.use_stamp=False
        s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=-.7
        # Same metallic-mask-preserving deep-blue render tint as approved X-slash v2.
        for material in bpy.data.materials:
            if material.name not in {'Astra Round2 royal blue and continuous gold trim','Astra Round2 royal blue undersleeves'}:continue
            nt=material.node_tree
            if nt.nodes.get('Astra Move Deep Blue'):continue
            bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
            color=bs.inputs['Base Color'].links[0].from_socket;metal=bs.inputs['Metallic'].links[0].from_socket
            mul=nt.nodes.new('ShaderNodeMixRGB');mul.name='Astra Move Deep Blue';mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(.025,.20,.62,1);nt.links.new(color,mul.inputs[1])
            mix=nt.nodes.new('ShaderNodeMixRGB');mix.name='Astra Move Preserve Gold';nt.links.new(metal,mix.inputs[0]);nt.links.new(mul.outputs[0],mix.inputs[1]);nt.links.new(color,mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
        # Replace only source staging in this derived scene; preserve every character accessory.
        for o in list(s.objects):
            if o.type in ['LIGHT','CAMERA'] or o.name=='Astra evaluation ground':bpy.data.objects.remove(o,do_unlink=True)
        bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.015));ground=bpy.context.object;ground.name='Astra_Move_Stage'
        mat=bpy.data.materials.new('Astra Move slate');mat.diffuse_color=(.055,.072,.095,1);ground.data.materials.append(mat)
        for name,pos,power,color,size in [('Key',(3,-4,6),1500,(1,.86,.7),5),('Fill',(-4,-2,3),1100,(.64,.78,1),4),('Rim',(1,3,5),1800,(1,.77,.43),3)]:
            data=bpy.data.lights.new('Astra_Move_'+name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size;o=bpy.data.objects.new(data.name,data);s.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,-.4,1.2))-o.location).to_track_quat('-Z','Y').to_euler()
        data=bpy.data.cameras.new('Astra_Move_Camera');cam=bpy.data.objects.new(data.name,data);s.collection.objects.link(cam);s.camera=cam;data.type='ORTHO';data.ortho_scale=self.meta.get('scale',4.8)
        target=Vector(self.meta.get('target',(0,-.15,1.62)));cam.location=target+Vector(self.meta.get('camera',(4.3,-8.6,2.7)));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()

        if self.meta.get('target_point'):
            p=Vector(self.meta['target_point']);p.z=-.009
            cv=bpy.data.curves.new('Astra_Move_Target_Ring','CURVE');cv.dimensions='3D';cv.bevel_depth=.008;cv.bevel_resolution=2
            sp=cv.splines.new('POLY');sp.points.add(63)
            for i,point in enumerate(sp.points):
                angle=i*2*math.pi/64;point.co=(p.x+.28*math.cos(angle),p.y+.28*math.sin(angle),p.z,1)
            sp.use_cyclic_u=True;ob=bpy.data.objects.new(cv.name,cv);s.collection.objects.link(ob)
            gold=bpy.data.materials.new('Astra Move target marker');gold.diffuse_color=(.8,.45,.09,1);cv.materials.append(gold)

        if self.meta.get('track_translation'):
            for o in [cam]+[o for o in s.objects if o.type=='LIGHT']:
                start=o.location.copy();o.keyframe_insert('location',frame=1);o.location=start+self.travel;o.keyframe_insert('location',frame=self.N);o.location=start
                for la in o.animation_data.action.layers:
                    for st in la.strips:
                        for bag in st.channelbags:
                            for fc in bag.fcurves:
                                fc.extrapolation='LINEAR'
                                for key in fc.keyframe_points:key.interpolation='LINEAR'

    def ribbons(self,windows):
        """Sub-frame exposure geometry of the actual blade, never decorative lines."""
        if not windows:return
        mat=bpy.data.materials.new('Astra Move temporal blade');mat.use_nodes=True
        nd=mat.node_tree.nodes;nd.clear();out=nd.new('ShaderNodeOutputMaterial');mix=nd.new('ShaderNodeMixShader');trans=nd.new('ShaderNodeBsdfTransparent');emit=nd.new('ShaderNodeEmission');attr=nd.new('ShaderNodeVertexColor');attr.layer_name='fade'
        emit.inputs['Color'].default_value=(.64,.49,.24,1);emit.inputs['Strength'].default_value=1.1
        li=mat.node_tree.links;li.new(attr.outputs['Alpha'],mix.inputs[0]);li.new(trans.outputs[0],mix.inputs[1]);li.new(emit.outputs[0],mix.inputs[2]);li.new(mix.outputs[0],out.inputs[0]);mat.surface_render_method='BLENDED';mat.use_transparent_shadow=False
        for start,end in windows:
            for f in range(start,end+1):
                vertices=[];faces=[];alpha=[]
                for j in range(13):
                    t=f-.65+.65*j/12;self.s.frame_set(int(t),subframe=t%1);self.update();tip,grip=self.sword_points()
                    for radial in [.25,.85,1]:vertices.append(grip.lerp(tip,radial));alpha.append((j/12)**1.5*.17*(1 if radial>.5 else 0))
                for j in range(12):
                    for k in range(2):a=j*3+k;faces.append((a,a+1,a+4,a+3))
                mesh=bpy.data.meshes.new(f'Astra_Move_blur_{f}');mesh.from_pydata(vertices,[],faces);mesh.materials.append(mat)
                col=mesh.color_attributes.new(name='fade',type='FLOAT_COLOR',domain='POINT')
                for c,a in zip(col.data,alpha):c.color=(1,1,1,a)
                ob=bpy.data.objects.new(mesh.name,mesh);self.s.collection.objects.link(ob)
                for frame,hide in [(1,True),(f-1,True),(f,False),(f+1,True)]:
                    ob.hide_render=hide;ob.hide_viewport=hide;ob.keyframe_insert('hide_render',frame=frame);ob.keyframe_insert('hide_viewport',frame=frame)
