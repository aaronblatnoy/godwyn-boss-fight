from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json
R=Path(__file__).resolve().parents[1];O=R/'renders/astra/v3b';font=ImageFont.truetype('/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf',17)
views=['front','side','three_quarter','back','collar','collar_top45','face'];sheet=Image.new('RGB',(7*300,2*480),(17,19,24));d=ImageDraw.Draw(sheet)
for row,pose in enumerate(['rest','stance']):
 for col,view in enumerate(views):
  p=O/'final'/f'{pose}_{view}.png';im=Image.open(p).convert('RGB');im.thumbnail((300,450));sheet.paste(im,(col*300,row*480+30));d.text((col*300+8,row*480+5),pose+' / '+view,font=font,fill='white')
sheet.save(O/'stills_contact_sheet.jpg',quality=94)
paths=sorted((O/'film/Combat_Stance_frames').glob('*.png'));assert len(paths)==51,len(paths)
for start in range(0,len(paths),9):
 page=Image.new('RGB',(1536,3*540),(17,19,24));d=ImageDraw.Draw(page)
 for j,p in enumerate(paths[start:start+9]):
  im=Image.open(p).convert('RGB');im.thumbnail((512,512));x=j%3*512;y=j//3*540;page.paste(im,(x,y+28));d.text((x+10,y+5),'Combat_Stance frame '+str(int(p.stem)),font=font,fill='white')
 page.save(O/'film'/f'contact_{start+1:02d}_{min(start+9,51):02d}.jpg',quality=95)
print(json.dumps({'still_images':14,'film_frames':51,'film_contact_sheets':6}))
