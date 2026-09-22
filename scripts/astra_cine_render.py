"""Read-only animation input; reusable in-memory Cycles/Metal cinematography.
Never saves a blend or preferences. Outputs confined to renders/astra/cine or /tmp.
Usage: blender -b --factory-startup --debug-cycles --python-exit-code 1
 --python scripts/astra_cine_render.py -- --blend models/astra_xslash_v2_final_wip.blend
 --frames 40 --label lookdev_final
"""
import argparse, hashlib, json, math, sys, time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'renders/astra/cine'
PREFIX = 'Astra_Cine_'
STUDIO = {'Astra_Key', 'Astra_Fill', 'Astra_Rim', 'Astra_Camera', 'Astra_Stage',
          'Astra key', 'Astra fill', 'Astra rim', 'Astra face',
          'Astra evaluation camera', 'Astra evaluation ground', 'Icosphere.001'}

# Art-directed ladder B: measured tint-over-atlas, not a base-color assignment.
BLUE_TINT = (0.02, 0.03, 0.23)
BLUE_TARGETS = {'Astra Round2 royal blue and continuous gold trim',
                'Astra Round2 royal blue undersleeves'}

def apply_blue_override(scene, tint=None):
    """Use the motion mask operation with art-directed tint coefficients.
    Render-time only; recognizes existing motion nodes to avoid double tinting.
    Match library-appended material suffixes, and only alter active materials.
    """
    tint=tuple(BLUE_TINT if tint is None else tint)
    assert len(tint)==3 and all(math.isfinite(x) and 0<=x<=1 for x in tint), 'CINE BLUE FAILURE: invalid tint'
    used=set()
    for obj in scene.objects:
        if obj.type=='MESH' and not obj.hide_render:
            used.update(obj.data.materials[p.material_index] for p in obj.data.polygons
                        if p.material_index<len(obj.data.materials) and obj.data.materials[p.material_index])
    applied=[]
    for material in sorted(used,key=lambda m:m.name):
        name=material.name
        if name.rsplit('.',1)[-1].isdigit():name=name.rsplit('.',1)[0]
        if name not in BLUE_TARGETS:continue
        nt=material.node_tree
        bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        assert bsdf.inputs['Base Color'].is_linked and bsdf.inputs['Metallic'].is_linked, 'CINE BLUE FAILURE: expected atlas color and metallic mask: '+material.name
        metallic=bsdf.inputs['Metallic'].links[0].from_socket
        scale=nt.nodes.get('Astra XSlash Final Deep Blue Multiply')
        bypass=nt.nodes.get('Astra XSlash Final Preserve Gold')
        assert bool(scale)==bool(bypass), 'CINE BLUE FAILURE: incomplete existing tint pair'
        if scale:
            assert bsdf.inputs['Base Color'].links[0].from_node==bypass and scale.inputs[1].is_linked, 'CINE BLUE FAILURE: unrecognized existing tint wiring'
            color=scale.inputs[1].links[0].from_socket
        else:
            color=bsdf.inputs['Base Color'].links[0].from_socket
            scale=nt.nodes.new('ShaderNodeMixRGB');scale.name='Astra XSlash Final Deep Blue Multiply'
            bypass=nt.nodes.new('ShaderNodeMixRGB');bypass.name='Astra XSlash Final Preserve Gold'
        scale.label='Render override: deep blue cloth';scale.blend_type='MULTIPLY'
        scale.inputs[0].default_value=1.0;scale.inputs[2].default_value=(*tint,1.0)
        scale.location=(bsdf.location.x-440,bsdf.location.y+160)
        bypass.label='Existing metallic mask preserves original gold';bypass.blend_type='MIX'
        bypass.location=(bsdf.location.x-220,bsdf.location.y+160)
        nt.links.new(color,scale.inputs[1]);nt.links.new(metallic,bypass.inputs[0])
        nt.links.new(scale.outputs[0],bypass.inputs[1]);nt.links.new(color,bypass.inputs[2])
        nt.links.new(bypass.outputs[0],bsdf.inputs['Base Color'])
        assert bsdf.inputs['Metallic'].links[0].from_socket==metallic
        applied.append({'material':material.name,'canonical_material':name,'multiply_linear':list(tint),
                        'original_color':[color.node.name,color.name],
                        'unchanged_metallic_mask':[metallic.node.name,metallic.name]})
    assert {x['canonical_material'] for x in applied}==BLUE_TARGETS, 'CINE BLUE FAILURE: required cloth materials not found on visible geometry'
    print('CINE_BLUE_OVERRIDE '+json.dumps(applied),flush=True)
    return applied

def aim(obj, point):
    obj.rotation_euler = (Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()

def area(scene, name, loc, target, power, color, width, height):
    data = bpy.data.lights.new(PREFIX+name, 'AREA')
    data.energy, data.color, data.shape = power, color, 'RECTANGLE'
    data.size, data.size_y = width, height
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    aim(obj, target)
    return obj

def configure_device(scene, requested='AUTO', allow_cpu=False):
    """Bind only the requested backend. AUTO tries GPU backends, never CPU."""
    scene.render.engine='CYCLES'
    prefs=bpy.context.preferences.addons['cycles'].preferences
    requested=requested.upper()
    if requested=='CPU':
        if not allow_cpu:
            raise RuntimeError('CINE DEVICE FAILURE: CPU requires --device CPU --allow-cpu; silent CPU fallback is forbidden')
        prefs.compute_device_type='NONE';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='CPU'
        scene.cycles.device='CPU'
        selected='CPU'
        assert any(d.use and d.type=='CPU' for d in prefs.devices), 'CINE DEVICE FAILURE: no CPU device enumerated'
    else:
        selected=None;errors=[]
        for backend in (['OPTIX','CUDA','METAL'] if requested=='AUTO' else [requested]):
            try:
                prefs.compute_device_type=backend;prefs.get_devices()
            except (TypeError,ValueError,RuntimeError) as exc:
                errors.append(f'{backend}: {exc}');continue
            candidates=[d for d in prefs.devices if d.type==backend and '07:00' not in d.id]
            if not candidates:
                errors.append(f'{backend}: no matching device enumerated');continue
            for d in prefs.devices:d.use=d in candidates
            scene.cycles.device='GPU';selected=backend
            break
        if selected is None:
            message=f'CINE DEVICE FAILURE: requested {requested}; no matching GPU backend/device bound. CPU fallback is FORBIDDEN. '+ ' | '.join(errors)
            print(message,flush=True)
            raise RuntimeError(message)
    assert_device(scene,selected)
    proof={'requested_device':requested,'bound_backend':selected,'engine':scene.render.engine,
           'device':scene.cycles.device,'enabled_compute_devices':[{'name':d.name,'type':d.type} for d in prefs.devices if d.use]}
    print('CINE_DEVICE_BOUND '+json.dumps(proof),flush=True)
    return proof

def assert_device(scene, backend):
    prefs=bpy.context.preferences.addons['cycles'].preferences
    active=[d for d in prefs.devices if d.use]
    expected='CPU' if backend=='CPU' else 'GPU'
    assert scene.render.engine=='CYCLES' and scene.cycles.device==expected, 'CINE DEVICE FAILURE: engine/device changed'
    assert active and all(d.type==backend and (backend=='CPU' or '07:00' not in d.id) for d in active), f'CINE DEVICE FAILURE: enabled devices do not match {backend}'
    assert prefs.compute_device_type==('NONE' if backend=='CPU' else backend), 'CINE DEVICE FAILURE: requested backend did not bind'

def enforce_local_hold(frames):
    if sys.platform=='darwin' and len(frames)>3:
        raise RuntimeError('CINE HARD HOLD: Mac runs are limited to three frames. The 90-frame hero belongs on the Linux GPU server.')

def configure(scene, args):
    blue_override=apply_blue_override(scene,getattr(args,'tint',None))
    stage = next((scene.objects.get(n) for n in ['Astra_Stage','Astra evaluation ground',PREFIX+'Floor'] if scene.objects.get(n)),None)
    floor_z = float(stage.matrix_world.translation.z) if stage else -.015
    if scene.world and scene.world.name.startswith(PREFIX): scene.world = None
    for obj in list(bpy.data.objects):
        if obj.name in STUDIO or obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    for col in list(bpy.data.collections):
        if col.name.startswith(PREFIX): bpy.data.collections.remove(col)
    for datablocks in (bpy.data.worlds,bpy.data.materials,bpy.data.lights,bpy.data.cameras,bpy.data.meshes):
        for data in list(datablocks):
            if data.name.startswith(PREFIX) and data.users == 0: datablocks.remove(data)
    assert not [o.name for o in scene.objects if o.type in {'LIGHT','CAMERA'}], 'Unknown staging: explicitly audit names before removal'
    scene.render.engine = 'CYCLES'
    device_proof = configure_device(scene, getattr(args,'device','METAL'), getattr(args,'allow_cpu',False))
    prefs = bpy.context.preferences.addons['cycles'].preferences
    enabled = device_proof['enabled_compute_devices']
    if device_proof['bound_backend']=='METAL' and hasattr(scene.cycles,'use_auto_tile'):
        scene.cycles.use_auto_tile=True
        scene.cycles.tile_size=512
    scene.cycles.samples = args.samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = args.threshold
    scene.cycles.adaptive_min_samples = min(32,args.samples)
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    if hasattr(scene.cycles,'denoising_use_gpu'): scene.cycles.denoising_use_gpu = scene.cycles.device=='GPU'
    scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 16
    scene.cycles.volume_bounces = 1
    scene.cycles.seed = 17
    scene.render.use_persistent_data = True
    scene.render.resolution_x,scene.render.resolution_y = args.width,args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '16'
    scene.render.film_transparent = False
    scene.render.use_stamp = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = .4
    for obj in scene.objects:
        if obj.name.startswith('Astra_v2_blur_'):
            obj.visible_camera=False
            obj.visible_glossy=False
        if obj.type == 'MESH' and hasattr(obj,'cycles'):
            obj.cycles.use_motion_blur = True
            obj.cycles.use_deform_motion = True
            obj.cycles.motion_steps = 3
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -.35
    scene.view_settings.gamma = 1
    world = bpy.data.worlds.new(PREFIX+'Void')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.0005,.0006,.0009,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .12
    scene.world = world
    # Character-scaled staging uses read-only evaluated bounds, never source edits.
    scene.frame_set(scene.frame_start)
    body = bpy.data.objects['char1']
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    points = [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    zmin,zmax = min(p.z for p in points),max(p.z for p in points)
    h=zmax-zmin
    scale=h/3.2
    cx=(min(p.x for p in points)+max(p.x for p in points))/2
    cy=(min(p.y for p in points)+max(p.y for p in points))/2
    def pos(x,y,z): return (cx+x*scale,cy+y*scale,zmin+z*scale)
    area(scene,'Warm_Key',pos(-2.5,-4.5,4.8),pos(0,0,1.85),1100*scale**2*args.key,(1.0,.92,.6),2.4*scale,3.5*scale)
    rim=area(scene,'Cold_Rim',pos(2.4,1.8,4.4),pos(0,-.1,1.9),1700*scale**2*args.rim,(.42,.62,1),1.0*scale,3.3*scale)
    left_rim=area(scene,'Cold_Left_Rim',pos(-2.7,1.0,3.1),pos(0,0,1.7),1100*scale**2,(.5,.68,1),.8*scale,3.4*scale)
    bounce=area(scene,'Floor_Bounce',pos(.15,-3.0,.75),pos(0,0,2.1),150*scale**2*args.fill,(1,.92,.6),3.0*scale,1.1*scale)
    rake=area(scene,'Engraving_Rake',pos(-3.8,-.7,2.8),pos(0,0,2.1),500*scale**2*args.rake,(1,.92,.6),.3*scale,1.8*scale)
    receivers=bpy.data.collections.new(PREFIX+'Character_Light_Receivers')
    for obj in scene.objects:
        if obj.type in {'MESH','CURVE','CURVES','SURFACE','META','VOLUME'} and not obj.name.startswith(PREFIX): receivers.objects.link(obj)
    for light in (rim,left_rim,bounce,rake): light.light_linking.receiver_collection=receivers
    bpy.ops.mesh.primitive_plane_add(size=160*scale,location=(cx,cy,floor_z))
    floor=bpy.context.object; floor.name=PREFIX+'Floor'; floor.data.name=PREFIX+'Floor'
    mat=bpy.data.materials.new(PREFIX+'Obsidian'); mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(.005,.006,.008,1)
    bs.inputs['Roughness'].default_value=.3
    bs.inputs['Metallic'].default_value=.22
    diff=mat.node_tree.nodes.new('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value=(.003,.004,.006,1)
    mix=mat.node_tree.nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.10
    mat.node_tree.links.new(diff.outputs[0],mix.inputs[1]);mat.node_tree.links.new(bs.outputs[0],mix.inputs[2])
    mat.node_tree.links.new(mix.outputs[0],mat.node_tree.nodes.get('Material Output').inputs['Surface'])
    floor.data.materials.append(mat)
    if args.haze:
        bpy.ops.mesh.primitive_cube_add(size=1,location=pos(0,1,1.5))
        fog=bpy.context.object;fog.name=PREFIX+'Haze';fog.data.name=PREFIX+'Haze'
        fog.scale=(14*scale,12*scale,3*scale)
        mat=bpy.data.materials.new(PREFIX+'Haze');mat.use_nodes=True
        nt=mat.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial')
        vol=nt.nodes.new('ShaderNodeVolumePrincipled')
        vol.inputs['Density'].default_value=args.haze/scale
        vol.inputs['Color'].default_value=(.85,.65,.1,1)
        vol.inputs['Anisotropy'].default_value=.15
        nt.links.new(vol.outputs['Volume'],out.inputs['Volume']);fog.data.materials.append(mat)
    camera=bpy.data.objects.new(PREFIX+'Camera',bpy.data.cameras.new(PREFIX+'Camera'))
    scene.collection.objects.link(camera);scene.camera=camera
    camera.data.type='PERSP';camera.data.lens=42;camera.data.sensor_width=36
    camera.data.clip_end=250*scale
    camera.data.dof.use_dof=True;camera.data.dof.aperture_fstop=5.6
    focus=bpy.data.objects.new(PREFIX+'Focus',None);scene.collection.objects.link(focus)
    focus.location=pos(0,-.05,2.1);camera.data.dof.focus_object=focus
    target=Vector(pos(0,-.15,1.60));az=math.radians(args.azimuth)
    camera.data.shift_x=-.02
    camera_height=floor_z+.68*scale
    def place(distance):
        camera.location=Vector((target.x+math.sin(az)*distance,target.y-math.cos(az)*distance,camera_height))
        aim(camera,target)
    # Fit BODY at the cut, deliberately allowing the blade to leave frame.
    scene.frame_set(40);dg=bpy.context.evaluated_depsgraph_get();bounds=[]
    for obj in scene.objects:
        if obj.type!='MESH' or obj.hide_render or obj.name.startswith(PREFIX) or obj.name.startswith(('Godwyn_Sword','Astra_v2_blur_')): continue
        e=obj.evaluated_get(dg);mesh=e.to_mesh()
        xyz=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',xyz)
        xyz=xyz.reshape(-1,3);matrix=np.array(e.matrix_world)
        bounds.append(xyz@matrix[:3,:3].T+matrix[:3,3]);e.to_mesh_clear()
    bounds=np.concatenate(bounds)
    distance=8.5*scale
    for _ in range(14):
        place(distance);bpy.context.view_layer.update()
        matrix=np.array(camera.matrix_world.inverted());local=bounds@matrix[:3,:3].T+matrix[:3,3]
        depth=-local[:,2]
        y=.5+local[:,1]/depth*camera.data.lens/camera.data.sensor_width*args.width/args.height
        extent=float(y.max()-y.min());center=float((y.max()+y.min())/2)
        distance*=extent/.86
        target.z+=(center-.50)*distance*camera.data.sensor_width/camera.data.lens*args.height/args.width
    # Reference fit is mid-clip: endpoints vary only +/-2% around this distance.
    distance/=(1-.04*(40-scene.frame_start)/(scene.frame_end-scene.frame_start))
    for f,d in [(scene.frame_start,distance),(scene.frame_end,distance*.96)]:
        place(d);camera.keyframe_insert('location',frame=f);camera.keyframe_insert('rotation_euler',frame=f)
    for layer in camera.animation_data.action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    # Fixed reflection strip, light-linked only to the real sword. Derive its
    # placement from the input blade plane at the reference cut, never edit it.
    scene.frame_set(40);bpy.context.view_layer.update()
    sword=bpy.data.objects['Godwyn_Sword']
    e=sword.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=e.to_mesh()
    xyz=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',xyz)
    xyz=xyz.reshape(-1,3);mw=np.array(e.matrix_world);xyz=xyz@mw[:3,:3].T+mw[:3,3]
    center=xyz.mean(axis=0);_,axes=np.linalg.eigh(np.cov((xyz-center).T))
    normal=Vector(axes[:,0]);point=Vector(center)
    to_camera=(camera.matrix_world.translation-point).normalized()
    reflected=(2*normal.dot(to_camera)*normal-to_camera).normalized()
    blade_light=area(scene,'Steel_Reflection',point+reflected*3.5*scale,point,
                     1000*scale**2,(.72,.85,1),1.8*scale,3.0*scale)
    sword_receivers=bpy.data.collections.new(PREFIX+'Sword_Only')
    sword_receivers.objects.link(sword)
    blade_light.light_linking.receiver_collection=sword_receivers
    e.to_mesh_clear()
    print('CINE_BLADE_LIGHT',list(blade_light.location),'plane_normal',list(normal),flush=True)
    proof={'blue_override':blue_override,'bound_backend':device_proof['bound_backend'],'requested_device':device_proof['requested_device'],'engine':scene.render.engine,'device':scene.cycles.device,'compute_backend':prefs.compute_device_type,'enabled_compute_devices':enabled,
           'all_devices':[{'name':d.name,'type':d.type,'enabled':d.use} for d in prefs.devices],
           'resolution':[args.width,args.height],'samples_max':args.samples,'adaptive_threshold':args.threshold,'denoiser':scene.cycles.denoiser,
           'haze_density':args.haze,'camera_distance_start':distance,'camera_push_percent':4,'camera_lens':42,'camera_height_m':camera_height,'camera_aim_height_m':target.z,'body_reference_frame':40,'body_reference_height_fraction':extent,'horizontal_shift':-.02,'camera_upward_angle_degrees':math.degrees(math.atan2(target.z-camera_height,distance)),'fill_multiplier':args.fill,'rake_multiplier':args.rake,'fstop':5.6,'shutter':.4,
           'view_transform':scene.view_settings.view_transform,'exposure':-.35,'key_linear_rgb':[1,.92,.6]}
    print('CINE_GPU_PROOF '+json.dumps(proof),flush=True)
    return proof

def main():
    p=argparse.ArgumentParser();p.add_argument('--blend',type=Path,required=True)
    p.add_argument('--frames',default='40');p.add_argument('--label',default='lookdev_final')
    p.add_argument('--width',type=int,default=1920);p.add_argument('--height',type=int,default=1080)
    p.add_argument('--tint',nargs=3,type=float,default=BLUE_TINT)
    p.add_argument('--samples',type=int,default=512);p.add_argument('--threshold',type=float,default=.01)
    p.add_argument('--fill',type=float,default=.6);p.add_argument('--rake',type=float,default=.6)
    p.add_argument('--haze',type=float,default=0);p.add_argument('--key',type=float,default=1)
    p.add_argument('--rim',type=float,default=1);p.add_argument('--azimuth',type=float,default=16)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);assert Path(a.label).name==a.label
    OUT.mkdir(parents=True,exist_ok=True)
    enforce_local_hold([int(x) for x in a.frames.split(',')])
    source=a.blend.resolve();before=source.stat()
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    after=source.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns),'Input changed during load; rerun after producer finishes'
    report=configure(bpy.context.scene,a);report.update(source=str(source),source_sha256=digest,blender=bpy.app.version_string,frames=[])
    scene=bpy.context.scene
    for f in [int(x) for x in a.frames.split(',')]:
        assert scene.frame_start<=f<=scene.frame_end
        scene.frame_set(f);scene.render.filepath=str(OUT/f'{a.label}_f{f:03d}.png')
        assert_device(scene,report['bound_backend'])
        start=time.perf_counter();bpy.ops.render.render(write_still=True);elapsed=time.perf_counter()-start
        result={'frame':f,'wall_seconds':elapsed,'path':scene.render.filepath}
        report['frames'].append(result);print('CINE_FRAME '+json.dumps(result),flush=True)
        (OUT/f'{a.label}_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CINE_COMPLETE no blend files or preferences saved',flush=True)
if __name__=='__main__':main()
