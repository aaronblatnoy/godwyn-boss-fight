"""Black-sky-only evidence layouts; no source images overwritten."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps
import sys,subprocess,json
R=Path(__file__).resolve().parents[1];assert str(R)=='/home/aaron/godwyn-boss-fight';O=R/'renders/astra/v4';mode=sys.argv[1]
def sheet(paths,out,tw,th,cols):
 rows=(len(paths)+cols-1)//cols;canvas=Image.new('RGB',(tw*cols,(th+32)*rows),(18,18,22));draw=ImageDraw.Draw(canvas)
 for i,p in enumerate(paths):
  im=ImageOps.contain(Image.open(p).convert('RGB'),(tw,th));x=(i%cols)*tw+(tw-im.width)//2;y=(i//cols)*(th+32);canvas.paste(im,(x,y));draw.text(((i%cols)*tw+10,y+th+8),p.stem,fill='white')
 canvas.save(out,quality=94)
if mode=='initial':sheet(sorted((O/'initial_material').glob('*.png')),O/'initial_material_contact.jpg',400,600,4)
if mode=='final':
 sheet(sorted((O/'final').glob('*.png')),O/'stills_contact.jpg',400,600,4)
 sheet([O/'references/godwyn_full_composite.png',O/'final/rest_front.png'],O/'body_comparison.jpg',750,1200,2)
 sheet([O/'references/godwyn_face_APPROVED.png',O/'v3face/rest_face.png',O/'final/rest_face.png'],O/'face_comparison.jpg',600,900,3)
 cropdir=O/'crops';cropdir.mkdir(exist_ok=True)
 for label,path,box in [('approved',O/'references/godwyn_face_APPROVED.png',(170,300,670,860)),('v3',O/'v3face/rest_face.png',(300,730,900,1260)),('v4',O/'final/rest_face.png',(260,760,970,1430))]:
  Image.open(path).crop(box).save(cropdir/(label+'_eyes_nose_mouth.png'))
 sheet(sorted(cropdir.glob('*eyes_nose_mouth.png')),O/'face_crops_comparison.jpg',600,600,3)
if mode=='film':
 folder=O/'film';frames=sorted((folder/'Combat_Stance_frames').glob('*.png'));assert len(frames)==51
 subprocess.run(['ffmpeg','-y','-framerate','30','-i',str(folder/'Combat_Stance_frames/%04d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(folder/'Combat_Stance.mp4')],check=True)
 for i in range(0,len(frames),9):sheet(frames[i:i+9],folder/f'contact_{i+1:02d}_{min(i+9,len(frames)):02d}.jpg',512,512,3)
 probe=subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries','stream=nb_read_frames,width,height,r_frame_rate,duration','-of','json',str(folder/'Combat_Stance.mp4')],text=True);(folder/'ffprobe.json').write_text(probe);print(probe)
