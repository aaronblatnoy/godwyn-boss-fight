"""Comparable 1080p collar diagnostics: hair held out, identical cameras/lights."""
import bpy,sys,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_character_common import reset_pose,aim
from astra_char2_render import configure
for stage in (['after'] if '--after-only' in sys.argv else ['before','after']):
 bpy.ops.wm.open_mainfile(filepath=str(R/'models'/('astra_character_v2_preround6.blend' if stage=='before' else 'astra_character_r6_collar.blend')));reset_pose();s=configure();s.cycles.samples=32;s.render.resolution_x=s.render.resolution_y=1080
 for ob in list(bpy.data.objects):
  if ob.type=='LIGHT':bpy.data.objects.remove(ob,do_unlink=True);continue
  if ob.name.startswith(('AstraChar2_R4_','AstraChar2_R2_Hair','AstraChar2_R3_Flow','AstraChar2_R3_Plait')) or 'ClothFitEnvelope' in ob.name:ob.hide_render=True
 for name,loc,power,size in [('key',(-3,-4.5,5),650,2.6),('fill',(3,-3,4),150,3),('rim',(1,2,4.5),850,2)]:
  d=bpy.data.lights.new('R6 '+name,'AREA');d.energy=power;d.size=size;ob=bpy.data.objects.new(d.name,d);s.collection.objects.link(ob);ob.location=loc;aim(ob,(0,-.2,2.6))
 m=bpy.data.materials.new('R6 neutral clay');m.use_nodes=True;m.node_tree.nodes.clear();out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');bs=m.node_tree.nodes.new('ShaderNodeBsdfDiffuse');bs.inputs[0].default_value=(.4,.4,.4,1);m.node_tree.links.new(bs.outputs[0],out.inputs[0])
 for kind in ['clay','textured']:
  s.view_layers[0].material_override=m if kind=='clay' else None
  for view,loc in [('front',(0,-3.8,2.70)),('three_quarter',(2.2,-3.6,2.80))]:
   s.camera.location=loc;aim(s.camera,(0,-.12,2.56));s.camera.data.type='PERSP';s.camera.data.lens=125;s.render.filepath=str(O/f'r6_collar_{stage}_{kind}_{view}.png');bpy.ops.render.render(write_still=True)
for kind in ['clay','textured']:
 for view in ['front','three_quarter']:
  subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(O/f'r6_collar_before_{kind}_{view}.png'),'-i',str(O/f'r6_collar_after_{kind}_{view}.png'),'-filter_complex','hstack=inputs=2','-frames:v','1','-y',str(O/f'r6_collar_comparison_{kind}_{view}.png')],check=True)
