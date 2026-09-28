"""Render-only visual alternative; does not save or alter the specified delivery RGB."""
import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from astra_character_common import *
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2.blend'))
for obj in ['char1','Astra_Undersleeves']:
 for m in bpy.data.objects[obj].data.materials:
  if m.name not in ['Astra Round2 royal blue and continuous gold trim','Astra Round2 royal blue undersleeves']:continue
  nt=m.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');color=bs.inputs['Base Color'].links[0].from_socket;metal=bs.inputs['Metallic'].links[0].from_socket
  scale=nt.nodes.new('ShaderNodeMixRGB');scale.blend_type='MULTIPLY';scale.inputs[0].default_value=1;nt.links.new(color,scale.inputs[1]);scale.inputs[2].default_value=(.025,.20,.62,1)
  mix=nt.nodes.new('ShaderNodeMixRGB');nt.links.new(metal,mix.inputs[0]);nt.links.new(scale.outputs[0],mix.inputs[1]);nt.links.new(color,mix.inputs[2]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
render_view('round2_deepblue_option','three_quarter')
