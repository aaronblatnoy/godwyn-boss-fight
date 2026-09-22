"""640px stills, cut-window/whole-clip contact frames, and optional final frames."""
import bpy,sys,argparse,json,math
sys.dont_write_bytecode=True
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from astra_xslash_v2_on_char_build import sword_landmarks, sword_points
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--round',default='v2_on_char');p.add_argument('--full',action='store_true');p.add_argument('--video-only',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
assert args.round == 'v2_on_char', 'This renderer only writes v2_on_char'
OUT=ROOT/'renders/astra'/args.round;OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_v2_on_char_wip.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100
s.eevee.taa_render_samples=24
cam=s.camera
CUT=[33,35,37,39,41,43,45,48,50,52,54,56,58,60]
FLOW=[1,13,25,31,36,40,46,50,54,57,64,70,80,90]
POSES=[27,36,40,46,53,57,64,90]
def view(v):
    cam.location={'front':(0,-11,2.5),'three_quarter':(4.8,-8.6,3.3)}[v]
    cam.rotation_euler=(Vector((0,-.2,2.0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.25;cam.data.type='ORTHO'
def phase(f):
    if f<31:return 'ANTICIPATION'
    if f<37:return 'BODY LEADS'
    if f<=42:return 'CUT 1'
    if f<54:return 'FOLLOW / RECOIL'
    if f<=59:return 'CUT 2'
    if f<75:return 'RECOVERY'
    return 'SETTLE'
def render(f,path,size,stamp=True):
    s.render.use_stamp=stamp
    for prop in ['date','time','render_time','frame','scene','camera','filename','memory','hostname']:setattr(s.render,'use_stamp_'+prop,False)
    s.render.use_stamp_note=True;s.render.stamp_note_text=f'{phase(f)}  |  F{f:02d}'
    s.render.stamp_font_size=12 if size==320 else 18;s.render.stamp_background=(.015,.02,.03,.85)
    s.frame_set(f);s.render.resolution_x=size;s.render.resolution_y=size;s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
if not args.video_only:
    for v in ['front','three_quarter']:
        view(v)
        for f in POSES:render(f,OUT/f'{v}_pose_f{f:02d}.png',640)
        d=OUT/f'contact_{v}';d.mkdir(exist_ok=True)
        for f in sorted(set(CUT+FLOW)):render(f,d/f'{f:03d}.png',320)
    # Measured subframe blade-tip paths rendered as cubic curves, not chords.
    sw=bpy.data.objects['Godwyn_Sword'];rig=bpy.data.objects['Armature'];tip,grip,_=sword_landmarks(sw);paths=[]
    for a,b,color in [(37,42,(1,.3,.06,1)),(54,59,(.05,.55,1,1))]:
        mat=bpy.data.materials.new('Astra V2 diagnostic');mat.diffuse_color=color;mat.use_nodes=True
        n=mat.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=color;n.inputs['Emission Color'].default_value=color;n.inputs['Emission Strength'].default_value=1
        cu=bpy.data.curves.new('Astra V2 measured arc','CURVE');cu.dimensions='3D';cu.bevel_depth=.013;cu.bevel_resolution=2
        sp=cu.splines.new('BEZIER');sp.bezier_points.add(40)
        for i,p in enumerate(sp.bezier_points):
            f=a+(b-a)*i/40;s.frame_set(math.floor(f),subframe=f%1);bpy.context.view_layer.update();p.co=sword_points(rig,sw,tip,grip)[0];p.handle_left_type='AUTO';p.handle_right_type='AUTO'
        o=bpy.data.objects.new(cu.name,cu);s.collection.objects.link(o);cu.materials.append(mat);paths.append(o)
    for v in ['front','three_quarter']:
        view(v);render(40,OUT/f'curved_paths_{v}.png',640)
    for o in paths:o.hide_render=True
if args.full or args.video_only:
    view('three_quarter');d=OUT/'video_frames';d.mkdir(exist_ok=True)
    s.eevee.taa_render_samples=48
    for f in range(1,91):render(f,d/f'{f:03d}.png',640,False)
(OUT/'manifest.json').write_text(json.dumps({'cut_frames':CUT,'flow_frames':FLOW,'poses':POSES},indent=2))
print('ASTRA V2 RENDER COMPLETE',OUT,flush=True)
