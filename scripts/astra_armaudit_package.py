"""FFmpeg-only evidence extraction from existing renders. NOT fresh Blender renders."""
import sys, json, subprocess, hashlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/armaudit'
FRAMES={'xslash':[1,27,38,39,47,48,54,61,90],'idle_guard':[1,9,25,34,49,65,78,82,96],'lunge_thrust':[1,17,25,29,32,37,40,43,64],'walk_stalk':[1,9,23,36,42,49,59,68,72]}
CROPS={'xslash':'crop=560:490:40:35','idle_guard':'crop=480:570:140:110','lunge_thrust':'crop=700:420:20:130','walk_stalk':'crop=480:570:140:110'}

def run(args):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr)
    return result.stdout

def main():
    manifest={'mode':'inherited_render_extractions_NOT_new_camera_renders','stills':{},'clips':{},'inspected':False}
    for name,frames in FRAMES.items():
        folder=ROOT/('renders/astra/v2_final_on_char/video_frames' if name=='xslash' else f'renders/astra/moves/{name}/frames')
        dest=OUT/f'stills_{name}';dest.mkdir(exist_ok=True)
        entries=[]
        for f in frames:
            source=folder/f'{f:03d}.png';target=dest/f'{f:03d}_inherited.png'
            run(['ffmpeg','-v','error','-y','-i',str(source),'-vf',CROPS[name],'-frames:v','1',str(target)])
            entries.append({'frame':f,'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output':str(target.relative_to(ROOT)),'crop':CROPS[name]})
        listing=OUT/f'sheet_{name}_inputs.txt';listing.write_text(''.join(f"file '{ROOT/e['output']}'\n" for e in entries))
        sheet=OUT/f'sheet_{name}_inherited.png'
        run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-vf','scale=400:400:force_original_aspect_ratio=decrease,pad=400:400:(ow-iw)/2:(oh-ih)/2:color=0x151515,tile=3x3:nb_frames=9:padding=4:margin=4','-frames:v','1',str(sheet)])
        manifest['stills'][name]={'entries':entries,'sheet':str(sheet.relative_to(ROOT)),'order':frames,'camera_angles':1,'missing':'second angle and fresh EEVEE no-motion-blur closeups'}
    for name,windows in {'xslash':[(30,44),(47,64)],'lunge_thrust':[(21,44)]}.items():
        video=ROOT/('renders/astra/godwyn_xslash_v2_final.mp4' if name=='xslash' else f'renders/astra/moves/{name}.mp4')
        for i,(a,b) in enumerate(windows,1):
            target=OUT/f'clips_{name}_strike{i}_slowmo.mp4';count=(b-a+1)*2
            vf=f'trim=start_frame={a-1}:end_frame={b},setpts=2*(PTS-STARTPTS),tpad=stop_mode=clone:stop_duration=0.033333333,fps=30,trim=end_frame={count},'+CROPS[name]
            run(['ffmpeg','-v','error','-y','-i',str(video),'-vf',vf,'-an','-c:v','libx264','-crf','16','-preset','fast','-pix_fmt','yuv420p',str(target)])
            probe=json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames,r_frame_rate,width,height,duration','-of','json',str(target)]))['streams'][0]
            assert int(probe['nb_frames'])==count,(target,probe,count)
            run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'])
            # Inspect every source frame by extracting every other half-speed frame into sequential sheets.
            decoded=OUT/f'decoded_{name}_strike{i}';decoded.mkdir(exist_ok=True)
            run(['ffmpeg','-v','error','-y','-i',str(target),'-vf',r'select=not(mod(n\,2)),scale=400:400:force_original_aspect_ratio=decrease,pad=400:400:(ow-iw)/2:(oh-ih)/2:color=0x151515,tile=4x2:nb_frames=8:padding=4:margin=4','-fps_mode','vfr',str(decoded/'sheet_%02d.png')])
            manifest['clips'][target.name]={'source':str(video.relative_to(ROOT)),'source_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'source_frames':[a,b],'speed':.5,'duplicate_factor':2,'probe':probe,'decode_passed':True,'decoded_sheets':[str(p.relative_to(ROOT)) for p in sorted(decoded.glob('*.png'))],'frame_order':'Every second output frame = consecutive original frames, row-major, eight per sheet; last sheet may contain black padding.'}
    (OUT/'evidence_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Packaged inherited evidence; no new Blender render or second angle is claimed.')

if __name__=='__main__':main()
