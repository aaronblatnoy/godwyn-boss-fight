import bpy,sys,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_render import configure
from astra_char2_round2_compare import portrait_lights
from astra_character_common import aim,reset_pose

def house():
 for name,loc,power,color,size in [('Astra key',(-3.5,-4.5,6),1350,(1,.92,.6),3),('Astra fill',(3,-4,3.5),680,(.52,.65,1),3.2),('Astra rim',(2,3,5),1650,(1,.8,.43),2.4),('Astra face',(0,-4,4.4),110,(1,.95,.84),1.4)]:
  o=bpy.data.objects[name];o.location=loc;o.data.energy=power;o.data.color=color;o.data.size=size;aim(o,(0,0,1.9))
 bg=bpy.context.scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.055,.068,.10,1);bg.inputs[1].default_value=.32
 bpy.data.objects['Astra evaluation ground'].hide_render=False

def shot(name,loc,target,scale,portrait=False):
 s=configure();s.cycles.samples=24;s.render.resolution_x=1080;s.render.resolution_y=1610 if portrait else 1080
 (portrait_lights if portrait else house)();s.camera.location=loc;aim(s.camera,target);s.camera.data.type='ORTHO';s.camera.data.ortho_scale=scale;s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
def views(stage):
 reset_pose()
 shot(stage+'_face',(0,-5,2.9),(0,-.3,2.9),.65,True)
 shot(stage+'_gold',(.7,-6,2.8),(0,-.24,2.41),.95)
 shot(stage+'_cloth',(0,-7,1.05),(0,-.1,1.05),2.0)
 if stage=='after':
  shot('after_face_three_quarter',(2.9,-5,3.15),(0,-.25,2.99),.65,True)
  shot('after_front',(0,-9,3.1),(0,0,1.61),3.75)
if __name__=='__main__':
 stage=sys.argv[-1];bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models'/('astra_character_v2_preround3.blend' if stage=='r3_before' else 'astra_character_v2.blend')));views(stage)
