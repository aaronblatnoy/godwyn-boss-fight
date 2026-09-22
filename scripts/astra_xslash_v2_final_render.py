"""Render preview stills, matching v2 evaluation frames, and the full 90 frames."""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'renders/astra/v2_final_on_char'
CUT = [33, 35, 37, 39, 41, 43, 45, 48, 50, 52, 54, 56, 58, 60]
FLOW = [1, 13, 25, 31, 36, 40, 46, 50, 54, 57, 64, 70, 80, 90]
POSES = [27, 36, 40, 46, 53, 57, 64, 90]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--video-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'models/astra_xslash_v2_final_wip.blend'))
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_percentage = 100
    scene.eevee.taa_render_samples = 24
    cam = scene.camera

    def view(angle):
        cam.location = {'front': (0, -11, 2.5), 'three_quarter': (4.8, -8.6, 3.3)}[angle]
        cam.rotation_euler = (Vector((0, -.2, 2.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.ortho_scale = 5.25
        cam.data.type = 'ORTHO'

    def phase(frame):
        if frame < 31: return 'ANTICIPATION'
        if frame < 37: return 'BODY LEADS'
        if frame <= 42: return 'CUT 1'
        if frame < 54: return 'FOLLOW / RECOIL'
        if frame <= 59: return 'CUT 2'
        if frame < 75: return 'RECOVERY'
        return 'SETTLE'

    def render(frame, path, size, stamp=True):
        scene.render.use_stamp = stamp
        for prop in ['date', 'time', 'render_time', 'frame', 'scene', 'camera', 'filename', 'memory', 'hostname']:
            setattr(scene.render, 'use_stamp_' + prop, False)
        scene.render.use_stamp_note = True
        scene.render.stamp_note_text = f'{phase(frame)}  |  F{frame:02d}'
        scene.render.stamp_font_size = 12 if size == 320 else 18
        scene.render.stamp_background = (.015, .02, .03, .85)
        scene.frame_set(frame)
        scene.render.resolution_x = size
        scene.render.resolution_y = size
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print('ASTRA FINAL FRAME', path.relative_to(OUT), flush=True)

    if args.preview:
        for angle, frame in [('front', 27), ('three_quarter', 64)]:
            view(angle)
            render(frame, OUT / f'blue_preview_{angle}_f{frame:02d}.png', 640)
        return
    if not args.video_only:
        for angle in ['front', 'three_quarter']:
            view(angle)
            for frame in POSES:
                render(frame, OUT / f'{angle}_pose_f{frame:02d}.png', 640)
            folder = OUT / f'contact_{angle}'
            folder.mkdir(exist_ok=True)
            for frame in sorted(set(CUT + FLOW)):
                render(frame, folder / f'{frame:03d}.png', 320)
    if args.full or args.video_only:
        view('three_quarter')
        folder = OUT / 'video_frames'
        folder.mkdir(exist_ok=True)
        scene.eevee.taa_render_samples = 48
        for frame in range(1, 91):
            render(frame, folder / f'{frame:03d}.png', 640, False)
    (OUT / 'manifest.json').write_text(json.dumps({
        'cut_frames': CUT, 'flow_frames': FLOW, 'poses': POSES,
        'video_frames': list(range(1, 91)) if args.full or args.video_only else [],
        'fps': 30, 'resolution': [640, 640],
        'robe_multiply_linear': list(scene['astra_final_robe_multiply_linear']),
    }, indent=2) + '\n')
    print('ASTRA FINAL RENDER COMPLETE', OUT, flush=True)


if __name__ == '__main__':
    main()
