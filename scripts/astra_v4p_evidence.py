from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
import sys,subprocess,json
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';O=R/'renders/astra/v4p';mode=sys.argv[1]
def sheet(paths,out,tw,th,cols):
 canvas=Image.new('RGB',(tw*cols,(th+32)*((len(paths)+cols-1)//cols)),(18,18,22));draw=ImageDraw.Draw(canvas)
 for i,p in enumerate(paths):
  im=ImageOps.contain(Image.open(p).convert('RGB'),(tw,th));x=(i%cols)*tw+(tw-im.width)//2;y=(i//cols)*(th+32);canvas.paste(im,(x,y));draw.text(((i%cols)*tw+10,y+th+8),p.stem,fill='white')
 canvas.save(out,quality=94)
if mode=='stills':
 sheet(sorted((O/'final').glob('*.png')),O/'stills_contact.jpg',400,600,4)
 sheet([R/'face-concepts/godwyn_face_APPROVED.png',R/'renders/astra/v4/final/rest_face.png',O/'final/rest_face.png'],O/'face_comparison.jpg',600,900,3)
 crops=O/'crops';crops.mkdir(exist_ok=True)
 for label,path,box in [('approved',R/'face-concepts/godwyn_face_APPROVED.png',(170,300,670,860)),('before',R/'renders/astra/v4/final/rest_face.png',(260,760,970,1430)),('after',O/'final/rest_face.png',(260,760,970,1430))]:Image.open(path).crop(box).save(crops/(label+'.png'))
 sheet([crops/(x+'.png') for x in ['approved','before','after']],O/'face_crops_comparison.jpg',600,600,3)
 sheet([R/'renders/astra/v4/final/stance_back.png',O/'final/stance_back.png'],O/'robe_comparison.jpg',600,900,2)
if mode=='film':
 folder=O/'film'
 for clip in ['Combat_Stance','sword_slash_r']:
  frames=sorted((folder/(clip+'_frames')).glob('*.png'));assert len(frames)==(51 if clip=='Combat_Stance' else 46)
  subprocess.run(['ffmpeg','-y','-framerate','30','-i',str(folder/(clip+'_frames/%04d.png')),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(folder/(clip+'.mp4'))],check=True)
  for i in range(0,len(frames),9):sheet(frames[i:i+9],folder/f'{clip}_contact_{i+1:02d}_{min(i+9,len(frames)):02d}.jpg',512,512,3)
  probe=subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries','stream=nb_read_frames,width,height,r_frame_rate,duration','-of','json',str(folder/(clip+'.mp4'))],text=True);(folder/(clip+'_ffprobe.json')).write_text(probe);print(clip,probe)
