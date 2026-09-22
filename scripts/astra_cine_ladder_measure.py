"""Fixed robe patches plus fixed cloth-boundary contrast samples, via ffmpeg."""
import sys
sys.dont_write_bytecode=True
import array,json,subprocess,statistics
from pathlib import Path
import astra_cine_sample_robe as patch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/cine/indigo_ladder'

def image(path):
    raw=subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-i',str(path),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb48le','pipe:1'],check=True,stdout=subprocess.PIPE).stdout
    a=array.array('H');a.frombytes(raw)
    if sys.byteorder!='little':a.byteswap()
    assert len(a)==1920*1080*3
    return a

def rgb(a,x,y):return [a[(y*1920+x)*3+c]/257 for c in range(3)]
def luma(p):return .2126*p[0]+.7152*p[1]+.0722*p[2]
def mean(a,pts):return statistics.mean(luma(rgb(a,x,y)) for x,y in pts)

def main():
    paths={k:OUT/f'indigo_{k}_f041.png' for k in 'ABC'}
    paths['previous']=ROOT/'renders/astra/cine/blue_corrected/blue_verify_f041.png'
    images={k:image(p) for k,p in paths.items()}
    # Define boundaries on brightest rung C only, then reuse exactly for A/B.
    # Lower robe excludes weapon/arms/head. Color test avoids gold trim samples.
    ref=images['C'];sites=[]
    def blue(x,y):
        r,g,b=rgb(ref,x,y);return b>r+10 and b>g+10
    for y in range(700,901,10):
        for side,lo,hi in [('left',650,920),('right',1100,1320)]:
            xs=[x for x in range(lo,hi) if all(blue(x+d,y) for d in [-1,0,1])]
            if not xs:continue
            edge=min(xs) if side=='left' else max(xs)
            inward=1 if side=='left' else -1
            inside=[(edge+inward*d,y+dy) for d in range(3,8) for dy in [-1,0,1]]
            outside=[(edge-inward*d,y+dy) for d in range(8,13) for dy in [-1,0,1]]
            # Skip boundaries adjacent to geometry, not actual void.
            if mean(ref,outside)>2:continue
            sites.append({'side':side,'edge_xy':[edge,y],'inside':inside,'outside':outside})
    assert len(sites)>=20,'Too few valid cloth-to-void boundary samples'
    result={'patch_method':'Identical 16x16 rectangles, mean displayed RGB 0–255 after AgX, decoded RGB48 with ffmpeg.',
        'edge_method':'Fixed sites from blue-dominant lower-robe edges in C; y700..900 every10px, 15 pixels inside/outside each site. Encoded Rec.709 luma Yprime, not physical luminance. Outside must be <=2/255 in C. Delta<=5 flags weak separation; this is a local diagnostic, not a universal perceptual threshold.',
        'edge_sites':sites,'rungs':{}}
    for name,path in paths.items():
        a=images[name];measure=[]
        for site in sites:
            inside=mean(a,site['inside']);outside=mean(a,site['outside'])
            measure.append({'side':site['side'],'edge_xy':site['edge_xy'],'inside_yprime':inside,'outside_yprime':outside,'delta':inside-outside})
        summary={}
        for side in ['left','right']:
            group=[s for s in measure if s['side']==side];d=[s['delta'] for s in group]
            summary[side]={'sites':len(d),'min_delta':round(min(d),3),'median_delta':round(statistics.median(d),3),'weak_sites_delta_le_5':sum(x<=5 for x in d)}
        result['rungs'][name]={'path':str(path),'patches':patch.sample(path),'edge_summary':summary,'edge_samples':measure}
    (OUT/'ladder_measurements.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,r in result['rungs'].items():print(name,json.dumps({'patches':r['patches'],'edges':r['edge_summary']}))
if __name__=='__main__':main()
