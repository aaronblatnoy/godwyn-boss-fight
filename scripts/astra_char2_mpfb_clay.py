"""Consistent white-light clay and textured turnarounds, independent of motion files."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
sys.path.insert(0,str(R/'scripts'))
from astra_character_common import aim

def studio(clay=True, samples=32, width=680):
    s=bpy.context.scene
    for ob in list(s.objects):
        if ob.type in {'CAMERA','LIGHT'}: bpy.data.objects.remove(ob,do_unlink=True)
    s.render.engine='CYCLES';s.cycles.samples=samples;s.cycles.use_denoising=True
    s.cycles.max_bounces=6;s.cycles.diffuse_bounces=3;s.cycles.glossy_bounces=3
    s.render.resolution_x=width;s.render.resolution_y=round(width*1.49);s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG';s.render.film_transparent=False
    s.render.threads_mode='FIXED';s.render.threads=8
    s.view_settings.view_transform='AgX';s.view_settings.exposure=0
    try:
        p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='METAL';p.get_devices()
        for d in p.devices:d.use=d.type=='METAL'
        s.cycles.device='GPU' if any(d.type=='METAL' for d in p.devices) else 'CPU'
    except Exception:s.cycles.device='CPU'
    w=bpy.data.worlds.new('MPFB neutral studio');s.world=w;w.use_nodes=True
    w.node_tree.nodes['Background'].inputs[0].default_value=(.075,.075,.075,1)
    w.node_tree.nodes['Background'].inputs[1].default_value=.32
    for name,loc,power,size in [('key',(-3,-4.5,5),700,2.7),('fill',(3,-3,4),220,3),('rim',(1,2,4.5),750,2)]:
        d=bpy.data.lights.new('MPFB studio '+name,'AREA');d.energy=power;d.size=size
        ob=bpy.data.objects.new(d.name,d);s.collection.objects.link(ob);ob.location=loc;aim(ob,(0,-.2,2.8))
    cam=bpy.data.objects.new('MPFB studio camera',bpy.data.cameras.new('MPFB studio camera'))
    s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.lens=85
    s.view_layers[0].material_override=None
    if clay:
        m=bpy.data.materials.get('MPFB neutral grey clay') or bpy.data.materials.new('MPFB neutral grey clay')
        m.use_nodes=True;m.node_tree.nodes.clear();out=m.node_tree.nodes.new('ShaderNodeOutputMaterial')
        d=m.node_tree.nodes.new('ShaderNodeBsdfDiffuse');d.inputs['Color'].default_value=(.4,.4,.4,1)
        d.inputs['Roughness'].default_value=.7;m.node_tree.links.new(d.outputs[0],out.inputs['Surface'])
        s.view_layers[0].material_override=m
    return s

def render_views(prefix, views=('front','side','three_quarter'), clay=True, samples=32, width=680):
    s=studio(clay,samples,width)
    viewspec={'front':((0,-6,2.885),(0,-.20,2.885),.67),
              'side':((6,-.27,2.885),(0,-.27,2.885),.67),
              'three_quarter':((3.65,-6,2.885),(0,-.20,2.885),.67),
              'collar':((.60,-6,2.80),(0,-.18,2.57),.92),
              'body':((0,-9,3.1),(0,0,1.61),3.75)}
    for view in views:
        loc,target,scale=viewspec[view];s.camera.location=loc;aim(s.camera,target);s.camera.data.ortho_scale=scale
        if view in {'body','collar'}:s.render.resolution_x=s.render.resolution_y=1000
        else:s.render.resolution_x=width;s.render.resolution_y=round(width*1.49)
        s.render.filepath=str(O/f'{prefix}_{view}.png');bpy.ops.render.render(write_still=True)
        print('MPFB_RENDER',prefix,view,flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    bpy.ops.wm.open_mainfile(filepath=str(R/args[0]))
    render_views(args[1],tuple(x for x in args[2:] if x!='textured') or ('front','side','three_quarter'),clay='textured' not in args)
