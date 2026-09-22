"""Tile evaluation frames, encode libx264/yuv420p, decode and verify all frames."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'renders/astra/v2_final_on_char'
FINAL = ROOT / 'renders/astra/godwyn_xslash_v2_final.mp4'


def ffmpeg(args):
    subprocess.run([(__import__('shutil').which('ffmpeg') or '/opt/homebrew/bin/ffmpeg'), '-hide_banner', '-loglevel', 'error', '-y'] + args, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sheets-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((OUT / 'manifest.json').read_text())
    for angle in ['front', 'three_quarter']:
        for kind, frames in [('cuts', manifest['cut_frames']), ('flow', manifest['flow_frames']), ('poses', manifest['poses'])]:
            temp = Path('/tmp') / f'astra_xslash_v2_final_{angle}_{kind}'
            temp.mkdir(exist_ok=True)
            for index, frame in enumerate(frames):
                source = OUT / f'{angle}_pose_f{frame:02d}.png' if kind == 'poses' else OUT / f'contact_{angle}/{frame:03d}.png'
                shutil.copy2(source, temp / f'{index:03d}.png')
            cols = 4 if kind == 'poses' else 7
            ffmpeg(['-framerate', '1', '-i', str(temp / '%03d.png'), '-vf',
                    f'tile={cols}x2:nb_frames={len(frames)}:padding=4:margin=8:color=0x171b22',
                    '-frames:v', '1', str(OUT / f'{kind}_sheet_{angle}.png')])
    if args.sheets_only:
        return
    frames = sorted((OUT / 'video_frames').glob('*.png'))
    assert [p.name for p in frames] == [f'{i:03d}.png' for i in range(1, 91)]
    ffmpeg(['-framerate', '30', '-start_number', '1', '-i', str(OUT / 'video_frames/%03d.png'),
            '-frames:v', '90', '-c:v', 'libx264', '-crf', '17', '-preset', 'slow',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(FINAL)])
    # Decode the actual deliverable into six consecutive sheets, all 90 frames.
    ffmpeg(['-i', str(FINAL), '-vf',
            'scale=320:320,tile=5x3:nb_frames=15:padding=4:margin=8:color=0x171b22',
            '-fps_mode', 'vfr', str(OUT / 'decoded_sheet_%02d.png')])
    ffmpeg(['-v', 'error', '-xerror', '-i', str(FINAL), '-f', 'null', '-'])
    probe = json.loads(subprocess.check_output([
        (__import__('shutil').which('ffprobe') or '/opt/homebrew/bin/ffprobe'), '-v', 'error', '-count_frames', '-show_streams',
        '-show_format', '-of', 'json', str(FINAL)], text=True))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    assert video['codec_name'] == 'h264' and video['pix_fmt'] == 'yuv420p'
    assert int(video['nb_read_frames']) == 90 and video['r_frame_rate'] == '30/1'
    assert (video['width'], video['height']) == (640, 640)
    assert abs(float(probe['format']['duration']) - 3.0) < 1e-6
    (OUT / 'video_verification.json').write_text(json.dumps(probe, indent=2) + '\n')
    print('ASTRA FINAL PACKAGE COMPLETE', FINAL, flush=True)


if __name__ == '__main__':
    main()
