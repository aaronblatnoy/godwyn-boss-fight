"""Headless runtime assembly of canonical inputs; shared approved cine treatment.
No network, no blend saves, no copies on disk. Shared render-time blue override;
no source-file shader/mesh/key edits.
"""
import argparse, hashlib, json, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import astra_cine_render as cine
ROOT=Path(__file__).resolve().parents[1]

def signature(path):
    stat=path.stat()
    return (stat.st_size,stat.st_mtime_ns,hashlib.sha256(path.read_bytes()).hexdigest())

def action_digest(action):
    values=[]
    if action:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        values.append((curve.data_path,curve.array_index,curve.extrapolation,
                            [(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type) for k in curve.keyframe_points]))
    return hashlib.sha256(repr(values).encode()).hexdigest()

def belongs(obj,rig):
    parent=obj.parent
    while parent:
        if parent==rig:return True
        parent=parent.parent
    return any(mod.type=='ARMATURE' and mod.object==rig for mod in obj.modifiers)

def assemble_inputs(animation,character):
    """Reuse animation rig/action verbatim; bind fresh compatible character objects."""
    anim_sig,char_sig=signature(animation),signature(character)
    bpy.ops.wm.open_mainfile(filepath=str(animation))
    scene=bpy.context.scene
    rig=scene.objects.get('Armature')
    assert rig and rig.type=='ARMATURE' and rig.animation_data and rig.animation_data.action, 'CINE INPUT FAILURE: animation Armature/action missing'
    action=rig.animation_data.action;digest=action_digest(action)
    old_character=[o for o in scene.objects if belongs(o,rig)]
    with bpy.data.libraries.load(str(character),link=False) as (src,dst):
        source_names=src.objects[:];dst.objects=source_names[:]
    loaded=dict(zip(source_names,dst.objects));newrig=loaded.get('Armature')
    assert newrig and newrig.type=='ARMATURE', 'CINE INPUT FAILURE: character Armature missing'
    scene.collection.objects.link(newrig);bpy.context.view_layer.update()
    assert set(rig.data.bones.keys())==set(newrig.data.bones.keys()), 'CINE INPUT FAILURE: incompatible bone names'
    max_error=max(abs(rig.matrix_world[i][j]-newrig.matrix_world[i][j]) for i in range(4) for j in range(4))
    for bone in rig.data.bones:
        other=newrig.data.bones[bone.name]
        assert (bone.parent.name if bone.parent else None)==(other.parent.name if other.parent else None), 'CINE INPUT FAILURE: incompatible bone hierarchy'
        max_error=max(max_error,max(abs(bone.matrix_local[i][j]-other.matrix_local[i][j]) for i in range(4) for j in range(4)))
    assert max_error<1e-6, f'CINE INPUT FAILURE: character/animation rest-transform mismatch {max_error}'
    fresh={name:o for name,o in loaded.items() if o!=newrig and belongs(o,newrig)}
    assert {'char1','Godwyn_Sword'}.issubset(fresh), 'CINE INPUT FAILURE: character body/sword not rig-bound'
    unexpected=[name for name,o in loaded.items() if o.type in {'MESH','CURVE','CURVES','SURFACE','META','VOLUME'} and not o.hide_render and o not in fresh.values() and name not in cine.STUDIO and not name.startswith(cine.PREFIX) and name not in {'Icosphere','Icosphere.001'}]
    assert not unexpected, f'CINE INPUT FAILURE: unbound visible character objects require explicit attachment: {unexpected}'
    for o in old_character:bpy.data.objects.remove(o,do_unlink=True)
    for name,obj in fresh.items():
        scene.collection.objects.link(obj)
        if obj.parent==newrig:obj.parent=rig
        for mod in obj.modifiers:
            if mod.type=='ARMATURE' and mod.object==newrig:mod.object=rig
        for con in obj.constraints:
            if hasattr(con,'target') and con.target==newrig:con.target=rig
        owners=[obj,obj.data,getattr(obj.data,'shape_keys',None)]
        for owner in owners:
            ad=getattr(owner,'animation_data',None)
            for fc in ad.drivers if ad else []:
                for variable in fc.driver.variables:
                    for target in variable.targets:
                        if target.id==newrig:target.id=rig
        obj.name=name
    for o in list(loaded.values()):
        if o not in fresh.values():bpy.data.objects.remove(o,do_unlink=True)
    bpy.context.view_layer.update()
    assert rig.animation_data.action==action and action_digest(action)==digest, 'CINE INPUT FAILURE: animation action changed during assembly'
    assert signature(animation)==anim_sig and signature(character)==char_sig, 'CINE INPUT FAILURE: input changed while loading; rerun after producer finishes'
    result={'animation_path':str(animation),'animation_sha256':anim_sig[2],
            'character_path':str(character),'character_sha256':char_sig[2],
            'assembly':'in-memory fresh character objects on unchanged compatible animation rig',
            'character_objects':sorted(fresh),'rest_transform_max_error':max_error,
            'animation_action_sha256':digest,'source_files_saved':False}
    print('CINE_INPUTS '+json.dumps(result),flush=True)
    return scene,result

def phase(frame):
    if frame<31:return 'ANTICIPATION'
    if frame<37:return 'BODY LEADS'
    if frame<=42:return 'CUT 1'
    if frame<54:return 'FOLLOW / RECOIL'
    if frame<=59:return 'CUT 2'
    if frame<75:return 'RECOVERY'
    return 'SETTLE'

def treatment_state(scene):
    own=sorted((o.name,o.type) for o in scene.objects if o.name.startswith(cine.PREFIX))
    assert not any(name.rsplit('.',1)[-1].isdigit() for name,_ in own), 'CINE IDEMPOTENCE FAILURE: suffixed duplicate objects'
    return {'objects':own,'camera':scene.camera.name,
            'blue':[(m.name,len(m.node_tree.nodes),len(m.node_tree.links)) for m in bpy.data.materials if m.node_tree and m.node_tree.nodes.get('Astra XSlash Final Deep Blue Multiply')],
            'lights':{o.name:(tuple(o.location),tuple(o.rotation_euler),o.data.energy,tuple(o.data.color)) for o in scene.objects if o.type=='LIGHT'}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blend',type=Path,default=ROOT/'models/astra_xslash_v2_final_wip.blend')
    parser.add_argument('--character-blend',type=Path,default=ROOT/'models/astra_character_v2.blend')
    parser.add_argument('--device',choices=['AUTO','OPTIX','CUDA','METAL','CPU'],default='AUTO')
    parser.add_argument('--allow-cpu',action='store_true',help='Must accompany --device CPU; never enables automatic CPU fallback')
    parser.add_argument('--output',type=Path,default=cine.OUT/'hero')
    parser.add_argument('--width',type=int,default=1920);parser.add_argument('--height',type=int,default=1080)
    parser.add_argument('--tint',nargs=3,type=float,default=cine.BLUE_TINT)
    parser.add_argument('--samples',type=int,default=512);parser.add_argument('--threshold',type=float,default=.01)
    parser.add_argument('--frame-start',type=int);parser.add_argument('--frame-end',type=int);parser.add_argument('--frame-step',type=int,default=1)
    parser.add_argument('--frames',help='Explicit comma-separated still frames instead of a range')
    parser.add_argument('--label',default='hero');parser.add_argument('--verify-idempotence',action='store_true')
    parser.add_argument('--haze',type=float,default=0);parser.add_argument('--key',type=float,default=1)
    parser.add_argument('--rim',type=float,default=1);parser.add_argument('--fill',type=float,default=.6)
    parser.add_argument('--rake',type=float,default=.6);parser.add_argument('--azimuth',type=float,default=16)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    assert bpy.app.background, 'CINE LAUNCH FAILURE: use blender --background --python-exit-code 1 --python'
    assert min(args.width,args.height,args.samples,args.frame_step)>0 and 0<args.threshold<=1, 'CINE ARGUMENT FAILURE: invalid quality/range'
    assert Path(args.label).name==args.label and args.label not in {'','..','.'}, 'CINE ARGUMENT FAILURE: invalid label'
    bound=cine.configure_device(bpy.context.scene,args.device,args.allow_cpu)
    args.device=bound['bound_backend']
    if args.frames:
        assert args.frame_start is None and args.frame_end is None, 'Choose --frames OR frame range'
        requested=[int(f) for f in args.frames.split(',')]
        cine.enforce_local_hold(requested)
    else:requested=None
    output=args.output.expanduser().resolve()
    allowed=[cine.OUT.resolve(),Path('/tmp').resolve()] if sys.platform=='darwin' else [cine.OUT.resolve()]
    assert any(output==p or output.is_relative_to(p) for p in allowed), 'CINE OUTPUT FAILURE: outputs must stay under renders/astra/cine (or /tmp for local Mac tests)'
    scene,inputs=assemble_inputs(args.blend.expanduser().resolve(),args.character_blend.expanduser().resolve())
    frames=requested if requested is not None else list(range(args.frame_start if args.frame_start is not None else scene.frame_start,(args.frame_end if args.frame_end is not None else scene.frame_end)+1,args.frame_step))
    assert frames and all(scene.frame_start<=f<=scene.frame_end for f in frames), 'CINE FRAME FAILURE: empty/out-of-scene frame range'
    cine.enforce_local_hold(frames)
    proof=cine.configure(scene,args)
    if args.verify_idempotence:
        first=treatment_state(scene)
        proof=cine.configure(scene,args)
        second=treatment_state(scene)
        assert first==second, 'CINE IDEMPOTENCE FAILURE: treatment drifted on second application'
        print('CINE IDEMPOTENCE PASS: second application identical; no duplicate objects',flush=True)
    output.mkdir(parents=True,exist_ok=True)
    report={'inputs':inputs,'settings':proof,'frames':[],'fps':scene.render.fps,'idempotence_verified':args.verify_idempotence}
    manifest=output/f'{args.label}_metrics.json'
    for frame in frames:
        scene.frame_set(frame);bpy.context.view_layer.update()
        cine.assert_device(scene,args.device)
        path=output/f'{args.label}_f{frame:03d}.png'
        scene.render.filepath=str(path)
        start=time.perf_counter();bpy.ops.render.render(write_still=True);elapsed=time.perf_counter()-start
        cine.assert_device(scene,args.device)
        item={'frame':frame,'phase':phase(frame),'path':str(path),'wall_seconds':elapsed,
              'camera_location':list(scene.camera.location),'camera_rotation':list(scene.camera.rotation_euler)}
        report['frames'].append(item);manifest.write_text(json.dumps(report,indent=2)+'\n')
        print('CINE_HERO_FRAME '+json.dumps(item),flush=True)
    print('CINE_HERO_COMPLETE '+str(manifest)+'; no input files saved',flush=True)

if __name__=='__main__':main()
