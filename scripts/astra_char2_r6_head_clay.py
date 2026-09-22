"""Three-view depth gate, neutral diffuse only, long-lens portrait framing."""
import sys,bpy,json,subprocess,shutil
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose,aim
from astra_char2_render import configure
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_r6_head.blend'));reset_pose();s=configure();s.cycles.samples=48;s.render.resolution_x=1080;s.render.resolution_y=1620
for ob in list(bpy.data.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True);continue
 if ob.name.startswith(('AstraChar2_R4_','AstraChar2_R2_Hair','AstraChar2_R3_Flow','AstraChar2_R3_Plait')) or 'ClothFitEnvelope' in ob.name:ob.hide_render=True
m=bpy.data.materials.new('R6 anatomical clay, no textures no emission');m.use_nodes=True;m.node_tree.nodes.clear();out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');d=m.node_tree.nodes.new('ShaderNodeBsdfDiffuse');d.inputs[0].default_value=(.35,.35,.35,1);d.inputs[1].default_value=.45;m.node_tree.links.new(d.outputs[0],out.inputs[0]);s.view_layers[0].material_override=m
world=bpy.data.worlds.new('R6 neutral clay world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.08,.08,.08,1);world.node_tree.nodes['Background'].inputs[1].default_value=.3;s.world=world
for name,loc,power,size in [('key',(-3,-4.5,5),650,2.0),('fill',(3,-3,4),80,3),('rim',(1,2,4.5),650,2)]:
 d=bpy.data.lights.new('R6 head '+name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;aim(o,(0,-.2,2.9))
s.camera.data.type='PERSP';s.camera.data.lens=240;s.camera.data.sensor_fit='VERTICAL';s.camera.data.sensor_height=24
it=json.loads(sorted(O.glob('r6_head_iter*_build.json'))[-1].read_text())['iteration']
for label,loc,target in [('front',(0,-6.4,2.885),(0,-.2,2.885)),('side',(6,-.25,2.96),(0,-.25,2.96)),('three_quarter',(3.1,-5.57,2.885),(0,-.2,2.885))]:
 s.camera.location=loc;aim(s.camera,target);s.render.filepath=str(O/f'r6_head_iter{it:02}_{label}.png');bpy.ops.render.render(write_still=True)
 dest={'front':'clay_face.png','side':'clay_head_side.png','three_quarter':'clay_face_three_quarter.png'}[label];shutil.copy2(s.render.filepath,O/dest)
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(R/'face-concepts/godwyn_face_APPROVED.png'),'-i',str(O/f'r6_head_iter{it:02}_front.png'),'-filter_complex','[0:v]scale=-1:1620,setsar=1[a];[a][1:v]hstack=inputs=2','-frames:v','1','-y',str(O/f'r6_head_iter{it:02}_comparison.png')],check=True)
print('THREE VIEW CLAY COMPLETE',it,flush=True)
