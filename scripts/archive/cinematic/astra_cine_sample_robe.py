"""Sample displayed RGB from final PNGs using ffmpeg; no Pillow or color edits."""
import argparse, array, json, subprocess, sys
from pathlib import Path
REGIONS = {'front_tabard': (985, 570, 16, 16),
           'frame_right_skirt': (1145, 800, 16, 16),
           'frame_left_skirt': (827, 810, 16, 16)}

def sample(path):
    data=subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(path),
        '-frames:v','1','-f','rawvideo','-pix_fmt','rgb48le','pipe:1'],check=True,stdout=subprocess.PIPE).stdout
    values=array.array('H');values.frombytes(data)
    if sys.byteorder!='little':values.byteswap()
    assert len(values)==1920*1080*3,'Expected full-resolution RGB48 frame'
    result={}
    for name,(x,y,w,h) in REGIONS.items():
        pixels=[values[(yy*1920+xx)*3:(yy*1920+xx)*3+3] for yy in range(y,y+h) for xx in range(x,x+w)]
        result[name]={'rectangle_xywh':[x,y,w,h],
            'mean_rgb_0_255':[round(sum(p[c] for p in pixels)/len(pixels)/257,3) for c in range(3)]}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    dest=a.output.resolve();assert dest.is_relative_to(root/'renders/astra/cine') or dest.is_relative_to(Path('/tmp').resolve())
    report={'measurement':'Mean displayed RGB after AgX from 16-bit PNG, scaled to 0–255; not scene-linear. Identical fixed 16x16 patches, top-left origin.',
        'before_path':str(a.before.resolve()),'after_path':str(a.after.resolve()),'before':sample(a.before),'after':sample(a.after)}
    dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
