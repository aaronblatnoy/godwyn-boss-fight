import sys,bpy,subprocess,shutil
from pathlib import Path
sys.dont_write_bytecode=True
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2';sys.path.insert(0,str(R/'scripts'))
from astra_char2_r3_render import house
from astra_char2_render import configure
from astra_char2_round2_compare import portrait_lights
from astra_character_common import aim
def shot(name,loc,target,scale,portrait=False):
 s=configure();s.cycles.samples=128;s.cycles.use_denoising=False;s.render.resolution_x=1080;s.render.resolution_y=1610 if portrait else 1080
 (portrait_lights if portrait else house)();s.camera.location=loc;aim(s.camera,target);s.camera.data.type='ORTHO';s.camera.data.ortho_scale=scale;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
from astra_character_common import reset_pose
stage=sys.argv[-1];before=stage=='before';bpy.ops.wm.open_mainfile(filepath=str(R/'models'/('astra_character_v2_preround4.blend' if before else 'astra_character_v2.blend')));reset_pose()
if not before:
 for ob in bpy.data.objects:
  if ob.name.startswith(('AstraChar2_R4_Strands_','AstraChar2_R4_Control_')):ob.hide_render=True
if before:
 shot('r4_before_hair',(.3,-6,2.58),(0,-.2,2.50),1.7)
 if not (O/'r4_before_face.png').exists():shutil.copy2(O/'after_face.png',O/'r4_before_face.png')
else:
 if stage!='body':
  shot('after_face',(0,-5,2.9),(0,-.3,2.9),.65,True)
  subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(R/'face-concepts/godwyn_face_APPROVED.png'),'-i',str(O/'after_face.png'),'-filter_complex','[0:v]scale=-1:1610,setsar=1[a];[a][1:v]hstack=inputs=2[out]','-map','[out]','-frames:v','1','-y',str(O/'sidebyside_face.png')],check=True)
 if stage!='face':
  shot('after_hair',(.3,-6,2.58),(0,-.2,2.50),1.7)
  subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(O/'r4_before_hair.png'),'-i',str(O/'after_hair.png'),'-filter_complex','[0:v][1:v]hstack=inputs=2[out]','-map','[out]','-frames:v','1','-y',str(O/'sidebyside_hair.png')],check=True)
  shot('after_front',(0,-9,3.1),(0,0,1.61),3.75)
  shot('after_face_three_quarter',(2.9,-5,3.15),(0,-.25,2.99),.65,True)
