import subprocess,json
from pathlib import Path
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
def pair(left,right,dest,filters=''):
 graph=filters or '[0:v]scale=-1:1610,setsar=1[a];[1:v]scale=-1:1610,setsar=1[b];[a][b]hstack=inputs=2[out]'
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(left),'-i',str(right),'-filter_complex',graph,'-map','[out]','-frames:v','1','-y',str(OUT/dest)],check=True)
pair(ROOT/'face-concepts/godwyn_face_APPROVED.png',OUT/'after_face.png','sidebyside_face.png')

if (OUT/'after_hair.png').exists():pair(OUT/'r3_before_hair.png',OUT/'after_hair.png','sidebyside_hair.png','[0:v][1:v]hstack=inputs=2[out]')
else:pair(OUT/'r3_before_face.png',OUT/'after_face.png','sidebyside_hair.png')
for view in ['gold','cloth']:pair(OUT/('r3_before_'+view+'.png'),OUT/('after_'+view+'.png'),'sidebyside_'+view+'.png','[0:v][1:v]hstack=inputs=2[out]')
