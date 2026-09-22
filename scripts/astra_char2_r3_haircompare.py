import sys,bpy,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
from astra_char2_r3_render import shot
from astra_character_common import reset_pose
for stage,filename in [('r3_before','astra_character_v2_preround3.blend'),('after','astra_character_v2.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models'/filename));reset_pose();shot(stage+'_hair',(.3,-6,2.72),(0,-.2,2.64),1.35)
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(OUT/'r3_before_hair.png'),'-i',str(OUT/'after_hair.png'),'-filter_complex','[0:v][1:v]hstack=inputs=2[out]','-map','[out]','-frames:v','1','-y',str(OUT/'sidebyside_hair.png')],check=True)
