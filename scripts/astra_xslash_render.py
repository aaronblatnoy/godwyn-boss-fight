"""Render named 640px poses and every third frame at 320px, or full video frames.
Usage: blender -b --python scripts/astra_xslash_render.py -- --round r1 [--full]
Use scripts/astra_xslash_package.py to tile/encode with installed ffmpeg.
"""
import bpy,sys,argparse
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--round',default='final');p.add_argument('--full',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=ROOT/'renders/astra'/args.round;OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_xslash_wip.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.image_settings.file_format='PNG';s.render.resolution_percentage=100
cam=s.camera

def view(v):
    cam.location={'front':(0,-10,2.35),'three_quarter':(4,-7,3.0)}[v]
    cam.rotation_euler=(Vector((0,-.2,1.9))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=5.0;cam.data.type='PERSP' if v=='front' else 'ORTHO';cam.data.lens=68

def render(f,path,size):
    s.render.use_stamp=True
    for prop in ['date','time','render_time','frame','scene','camera','filename','memory','hostname']:
        setattr(s.render,'use_stamp_'+prop,False)
    s.render.use_stamp_note=True;s.render.stamp_note_text=f'GODWYN  /  {path.stem}  /  frame {f:02d}'
    s.render.stamp_font_size=12 if size==320 else 16
    s.render.stamp_background=(.02,.03,.05,.7)
    if path.parent.name=='video_frames':s.render.use_stamp=False
    s.frame_set(f);s.render.resolution_x=size;s.render.resolution_y=size;s.render.filepath=str(path);bpy.ops.render.render(write_still=True)
poses=[(10,'windup'),(17,'cut1'),(18,'cross'),(33,'windup2'),(40,'cut2'),(41,'cross2'),(61,'recovery')]
for v in ['front','three_quarter']:
    view(v)
    for f,label in poses:render(f,OUT/f'{v}_{label}_f{f:02}.png',640)
    d=OUT/f'contact_{v}';d.mkdir(exist_ok=True)
    for i,f in enumerate(range(1,62,3)):render(f,d/f'{i:03}.png',320)
# Both actual tip trajectories in a single dedicated evaluation image.
import json
samples=json.loads((ROOT/'renders/astra/metrics.json').read_text())['samples']
paths=[]
for start,end,color in [(13,23,(1,.3,.04,1)),(36,46,(.05,.65,1,1))]:
    mat=bpy.data.materials.new('Astra path diagnostic');mat.diffuse_color=color;mat.use_nodes=True
    node=mat.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=color;node.inputs['Emission Color'].default_value=color;node.inputs['Emission Strength'].default_value=1
    cu=bpy.data.curves.new('Astra measured path','CURVE');cu.dimensions='3D';cu.bevel_depth=.013;cu.bevel_resolution=2
    spl=cu.splines.new('POLY');spl.points.add(end-start)
    for p,frame in zip(spl.points,range(start,end+1)):p.co=(*samples[frame-1]['tip'],1)
    obj=bpy.data.objects.new(cu.name,cu);s.collection.objects.link(obj);cu.materials.append(mat);paths.append(obj)
for v in ['front','three_quarter']:
    view(v);render(18,OUT/f'measured_X_paths_{v}.png',640)
for o in paths:o.hide_render=True

if args.full:
    view('front');d=OUT/'video_frames';d.mkdir(exist_ok=True)
    for f in range(1,62):render(f,d/f'{f:03}.png',640)
print('ASTRA RENDER COMPLETE',OUT)
