"""Compose labelled contact sheets, libx264 MP4, and verify actual video decode."""
import sys,json,subprocess,shutil,math,struct,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/moves'
name=sys.argv[1];preview='preview' in sys.argv
m=json.loads((OUT/f'{name}_manifest.json').read_text());folder=OUT/name/('preview' if preview else 'frames')
def ff(args):subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-loglevel','error','-y']+args,check=True)
frames=m['contact_frames'];temp=Path('/tmp')/f'astra_move_{name}_sheet';temp.mkdir(exist_ok=True)
digits={'0':['111','101','101','101','111'],'1':['010','110','010','010','111'],'2':['111','001','111','100','111'],'3':['111','001','111','001','111'],'4':['101','101','111','001','001'],'5':['111','100','111','001','111'],'6':['111','100','111','101','111'],'7':['111','001','010','010','010'],'8':['111','101','111','101','111'],'9':['111','101','111','001','111'],'F':['111','100','110','100','100']}
def labelled(source,dest,f):
    raw=bytearray(subprocess.check_output(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(source),'-vf','scale=320:320','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-']))
    for y in range(6,30):
        for x in range(6,68):
            i=(y*320+x)*3;raw[i:i+3]=bytes((20,24,30))
    for k,ch in enumerate(f'F{f:03d}'):
        for y,row in enumerate(digits[ch]):
            for x,c in enumerate(row):
                if c=='1':
                    for yy in range(3):
                        for xx in range(3):
                            i=((10+y*3+yy)*320+10+k*13+x*3+xx)*3;raw[i:i+3]=bytes((245,230,195))
    def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
    scan=b''.join(b'\x00'+raw[y*960:(y+1)*960] for y in range(320))
    dest.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,320,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))
for i,f in enumerate(frames):
    source=folder/f'{f:03d}.png'
    if not source.exists() and m['loop'] and f==m['samples_end']:source=folder/'001.png'
    labelled(source,temp/f'{i:03d}.png',f)
cols=5;rows=math.ceil(len(frames)/cols)
ff(['-framerate','1','-i',str(temp/'%03d.png'),'-vf',f'tile={cols}x{rows}:nb_frames={len(frames)}:padding=4:margin=8:color=0x171b22','-frames:v','1',str(OUT/f'{name}_{"preview_sheet" if preview else "contact_sheet"}.png')])
if preview:sys.exit()
video=OUT/f'{name}.mp4'
ff(['-framerate','30','-start_number','1','-i',str(folder/'%03d.png'),'-frames:v',str(m['frames']),'-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',str(video)])
ff(['-xerror','-i',str(video),'-f','null','-'])
p=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)],text=True));v=p['streams'][0]
assert v['codec_name']=='h264' and v['pix_fmt']=='yuv420p' and int(v['nb_read_frames'])==m['frames'] and v['r_frame_rate']=='30/1'
(OUT/f'{name}_video_verification.json').write_text(json.dumps(p,indent=2))
ff(['-i',str(video),'-vf','fps=5,scale=256:256,tile=5x4:nb_frames=20:padding=4:margin=8:color=0x171b22','-fps_mode','vfr',str(OUT/name/'decoded_%02d.png')])
print('PACKAGED',video)
