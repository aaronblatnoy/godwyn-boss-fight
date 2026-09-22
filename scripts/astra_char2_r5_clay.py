"""Geometry gate: neutral diffuse override, white lights, no maps or emission."""
import bpy,sys,json,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import aim,reset_pose
from astra_char2_render import configure
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [];baseline='before' in args
source=R/'models'/('astra_character_v2_preround5.blend' if baseline else ('astra_character_r5_groom_clay.blend' if 'groom' in args else 'astra_character_r5_clay.blend'))
bpy.ops.wm.open_mainfile(filepath=str(source));reset_pose();s=configure();s.cycles.samples=48;s.cycles.use_denoising=True
for ob in list(bpy.data.objects):
 if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True);continue
 if ob.name.startswith(('AstraChar2_R4_','AstraChar2_R3_Flow','AstraChar2_R3_Plait','AstraChar2_R2_Hair')):ob.hide_render=True
 if ob.name.startswith(('AstraChar2_R5_ClothFitEnvelope','AstraChar2_R5_Strands_','AstraChar2_R5_Control_')):ob.hide_render=True
 if ob.name.startswith('AstraChar2_R5_Curves_'):ob.hide_render='groom' not in args
m=bpy.data.materials.new('R5 CLAY ONLY no textures no emission');m.use_nodes=True;m.node_tree.nodes.clear();out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');diff=m.node_tree.nodes.new('ShaderNodeBsdfDiffuse');diff.inputs['Color'].default_value=(.40,.40,.40,1);diff.inputs['Roughness'].default_value=.65;m.node_tree.links.new(diff.outputs[0],out.inputs['Surface']);s.view_layers[0].material_override=m
w=bpy.data.worlds.new('R5 neutral clay world');s.world=w;w.use_nodes=True;w.node_tree.nodes['Background'].inputs[0].default_value=(.10,.10,.10,1);w.node_tree.nodes['Background'].inputs[1].default_value=.35
for name,loc,power,size in [('key',(-3,-4.5,5),650,2.6),('fill',(3,-3,4),150,3),('rim',(1,2,4.5),850,2)]:
 d=bpy.data.lights.new('R5 clay '+name,'AREA');d.energy=power;d.color=(1,1,1);d.size=size;ob=bpy.data.objects.new('R5 clay '+name,d);s.collection.objects.link(ob);ob.location=loc;aim(ob,(0,-.2,2.6))
views={'face':((0,-6,2.885),(0,-.2,2.885),.60,1610),'face_three_quarter':((3.3,-6,2.94),(0,-.2,2.885),.60,1610),'head_side':((6,-.265,2.96),(0,-.265,2.96),.63,1350),'front':((0,-9,3.1),(0,0,1.61),3.75,1080),'collar':((.65,-6,2.8),(0,-.12,2.53),.90,1080)}
selected=[x for x in args if x in views] or list(views)
for label in selected:
 loc,target,scale,height=views[label];s.render.resolution_x=1080;s.render.resolution_y=height;s.camera.location=loc;aim(s.camera,target);s.camera.data.type='ORTHO';s.camera.data.ortho_scale=scale
 prefix='r5_before_clay_' if baseline else ('clay_groom_' if 'groom' in args else 'clay_');s.render.filepath=str(O/(prefix+label+'.png'));bpy.ops.render.render(write_still=True)
 if label=='face' and not baseline:
  subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(R/'face-concepts/godwyn_face_APPROVED.png'),'-i',s.render.filepath,'-filter_complex','[0:v]scale=-1:1610,setsar=1[a];[a][1:v]hstack=inputs=2[out]','-map','[out]','-frames:v','1','-y',str(O/(prefix+'reference_comparison.png'))],check=True)
print('CLAY COMPLETE',selected,flush=True)
