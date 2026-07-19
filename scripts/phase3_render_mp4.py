"""
phase3_render_mp4.py — Render EEVEE frame sequence then encode mp4.

Blender 5.2: use render.image_settings.file_format='PNG' + animation=True
to produce a frame sequence, then ffmpeg to encode mp4.
"""

import bpy
import sys
import os
import math
import subprocess
from pathlib import Path

REPO       = Path("/home/aaron/godwyn-boss-fight")
WIP_BLEND  = REPO / "models" / "godwyn_xslash_wip.blend"
OUT_MP4    = REPO / "renders" / "game" / "godwyn_xslash_v2.mp4"
FRAMES_DIR = Path("/tmp/p3_v2_frames")
ACTION_NAME = "Godwyn_XSlash"

print("=" * 60)
print("PHASE 3 RENDER: EEVEE frame sequence -> mp4")
print("=" * 60)

# Load blend
print(f"\nLoading {WIP_BLEND}")
bpy.ops.wm.open_mainfile(filepath=str(WIP_BLEND))
scene = bpy.context.scene

# Confirm action
action = bpy.data.actions.get(ACTION_NAME)
if action is None:
    for a in bpy.data.actions:
        print(f"  Available action: {a.name}")
    raise RuntimeError(f"Action '{ACTION_NAME}' not found")
fr_start = int(action.frame_range[0])
fr_end   = int(action.frame_range[1])
scene.frame_start = fr_start
scene.frame_end   = fr_end
print(f"Frame range: {fr_start}..{fr_end}")

# Find front camera (XS_Cam is front camera from the build script)
cam_obj = scene.camera
if cam_obj is None:
    for o in bpy.data.objects:
        if o.type == 'CAMERA' and 'Cam' in o.name and 'Back' not in o.name:
            scene.camera = o
            cam_obj = o
            break
    if cam_obj is None:
        for o in bpy.data.objects:
            if o.type == 'CAMERA':
                scene.camera = o
                cam_obj = o
                break
print(f"Camera: {cam_obj.name if cam_obj else 'NONE'}")

# Prefer XS_Cam (front camera from the build script)
xs_cam = bpy.data.objects.get("XS_Cam")
if xs_cam:
    scene.camera = xs_cam
    cam_obj = xs_cam
    print(f"Using XS_Cam (front)")

# EEVEE render settings
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.fps = 30
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'

# Render to frame sequence
FRAMES_DIR.mkdir(parents=True, exist_ok=True)
# Clear old frames
for f in FRAMES_DIR.glob("p3v2_*.png"):
    f.unlink()

frame_pattern = str(FRAMES_DIR / "p3v2_####.png")
scene.render.filepath = str(FRAMES_DIR / "p3v2_")
print(f"Rendering {fr_end - fr_start + 1} frames to {FRAMES_DIR}/p3v2_*.png ...")
bpy.ops.render.render(animation=True)
print("Render done.")

# Check frames
frames = sorted(FRAMES_DIR.glob("p3v2_*.png"))
print(f"Rendered {len(frames)} frames")
assert len(frames) > 0, "No frames rendered!"

# ffmpeg encode
if OUT_MP4.exists():
    OUT_MP4.unlink()
OUT_MP4.parent.mkdir(parents=True, exist_ok=True)
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-framerate", "30",
    "-pattern_type", "glob",
    "-i", str(FRAMES_DIR / "p3v2_*.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "20",
    str(OUT_MP4)
]
print(f"ffmpeg: {' '.join(ffmpeg_cmd)}")
result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
print(result.stdout[-500:] if result.stdout else "")
print(result.stderr[-500:] if result.stderr else "")
assert result.returncode == 0, f"ffmpeg failed: {result.stderr}"
assert OUT_MP4.exists(), f"mp4 not created at {OUT_MP4}"
mp4_size = OUT_MP4.stat().st_size / (1024*1024)
print(f"\n✓ mp4 OK: {mp4_size:.1f} MB -> {OUT_MP4}")

# Sanity frames - copy a couple to readable paths for scp
sanity_paths = [frames[0], frames[len(frames)//2], frames[-1]]
for sp in sanity_paths:
    dest = FRAMES_DIR / ("sanity_" + sp.name)
    import shutil
    shutil.copy(sp, dest)
    print(f"  Sanity frame: {dest}")

print("\n" + "=" * 60)
print("RENDER COMPLETE")
print(f"  mp4: {OUT_MP4}  ({mp4_size:.1f} MB)")
print(f"  frames: {len(frames)}")
print("=" * 60)
