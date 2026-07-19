"""
anim_flipbook.py — Phase 0 / P2.B contact-sheet renderer.

CLI:
  blender --background --python anim_flipbook.py -- \
      --glb /path/to/animated.glb \
      [--action ActionName] \
      [--frames N]          (default 16, must be a perfect square) \
      [--out-prefix /tmp/godwyn_flipbook] \
      [--width 256] [--height 256]  (per-panel resolution)

Renders N evenly-spaced EEVEE frames from 2 cameras (front + 3/4 side),
then ffmpeg-tiles each into ONE labeled contact sheet.

Output:
  /tmp/godwyn_flipbook_front.jpg
  /tmp/godwyn_flipbook_34.jpg

Idempotent (delete-before-recreate on all temp objects / cameras).
NEVER writes to ~/Desktop.
Engine: BLENDER_EEVEE (fast; no OptiX assert needed for previews).
"""

import bpy
import sys
import os
import math
import argparse
import subprocess
import shutil


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Godwyn animation flipbook / contact sheet")
    parser.add_argument("--glb", required=False)
    parser.add_argument("--blend", required=False)
    parser.add_argument("--action", required=False, default=None)
    parser.add_argument("--frames", type=int, default=16)
    parser.add_argument("--out-prefix", default="/tmp/godwyn_flipbook")
    parser.add_argument("--width",  type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    return parser.parse_args(argv)


def load_file(glb=None, blend=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if glb:
        bpy.ops.import_scene.gltf(filepath=glb)
    elif blend:
        bpy.ops.wm.open_mainfile(filepath=blend)


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def find_action(name=None):
    if not bpy.data.actions:
        return None
    if name:
        return bpy.data.actions.get(name)
    return bpy.data.actions[0]


def assign_action(arm_obj, action):
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    arm_obj.animation_data.action = action


def get_char_center(arm_obj):
    """Get world center of the character (armature bbox center)."""
    xs, ys, zs = [], [], []
    for pb in arm_obj.pose.bones:
        hw = arm_obj.matrix_world @ pb.matrix.translation
        xs.append(hw.x); ys.append(hw.y); zs.append(hw.z)
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    cz = (max(zs) + min(zs)) / 2 + 0.2  # slight up
    height = max(zs) - min(zs)
    return (cx, cy, cz), height


def delete_by_name(names):
    for name in names:
        if name in bpy.data.objects:
            obj = bpy.data.objects[name]
            bpy.data.objects.remove(obj, do_unlink=True)


def setup_cameras(center, height):
    """Create / recreate front and 3/4 cameras looking at center."""
    dist = height * 1.8
    cx, cy, cz = center

    # Front camera
    delete_by_name(["FlipbookCamFront", "FlipbookCam34"])

    # Front: look from +Y toward -Y (Blender convention: camera looks -Z in local)
    import mathutils
    for name, azimuth_deg in [("FlipbookCamFront", 0), ("FlipbookCam34", 45)]:
        az = math.radians(azimuth_deg)
        cam_x = cx + dist * math.sin(az)
        cam_y = cy - dist * math.cos(az)
        cam_z = cz + height * 0.3

        cam_data = bpy.data.cameras.new(name=name)
        cam_data.lens = 50.0
        cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
        cam_obj.location = (cam_x, cam_y, cam_z)

        # Point camera at center
        target = mathutils.Vector((cx, cy, cz))
        direction = target - cam_obj.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()


def setup_light():
    """Add a simple key light if none exists."""
    existing_lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
    if not existing_lights:
        light_data = bpy.data.lights.new(name="FlipbookKey", type='SUN')
        light_data.energy = 3.0
        light_obj = bpy.data.objects.new(name="FlipbookKey", object_data=light_data)
        bpy.context.scene.collection.objects.link(light_obj)
        light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))


def render_frames(scene, cam_obj, frames_to_render, tmp_dir, prefix, width, height):
    """Render specified frames using cam_obj, save to tmp_dir/prefix_XXXX.png."""
    scene.camera = cam_obj
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100

    paths = []
    for f in frames_to_render:
        scene.frame_set(f)
        out_path = os.path.join(tmp_dir, f"{prefix}_{f:04d}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        paths.append(out_path)
    return paths


def make_contact_sheet_ffmpeg(frame_paths, out_path, n_cols, n_rows, label=""):
    """Use ffmpeg to tile frame_paths into a labeled contact sheet."""
    if not frame_paths:
        return False

    # ffmpeg filter: scale + tile + drawtext label
    # Build input args
    inputs = []
    for p in frame_paths:
        inputs += ["-i", p]

    n = len(frame_paths)
    tile_spec = f"{n_cols}x{n_rows}"

    filter_parts = []
    for i in range(n):
        filter_parts.append(f"[{i}:v]copy[f{i}]")

    concat_inputs = "".join(f"[f{i}]" for i in range(n))
    filter_parts.append(f"{concat_inputs}xstack=inputs={n}:layout=" + ":".join([
        f"{(i % n_cols) * 256}_{(i // n_cols) * 256}" for i in range(n)
    ]) + "[base]")

    # fallback: use tile filter instead of xstack for simpler tiling
    ffmpeg_cmd = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex",
        f"{''.join(f'[{i}:v]' for i in range(n))}xstack=inputs={n}:fill=black:layout="
        + "|".join([f"{(i % n_cols) * 256}_{(i // n_cols) * 256}" for i in range(n)])
        + "[out]",
        "-map", "[out]",
        "-frames:v", "1",
        out_path
    ]

    # Simpler approach: use ffmpeg tile via concat + vstack/hstack is complex
    # Use the simple tile approach: scale all to same size, then tile
    simple_cmd = ["ffmpeg", "-y"]
    for p in frame_paths:
        simple_cmd += ["-i", p]

    # Build a proper tile layout
    tile_filter = ""
    for i in range(n):
        tile_filter += f"[{i}:v]scale=256:256[v{i}];"

    # Arrange into rows
    row_filters = []
    for row in range(n_rows):
        row_inputs = "".join(f"[v{row * n_cols + col}]" for col in range(n_cols))
        tile_filter += f"{row_inputs}hstack=inputs={n_cols}[row{row}];"
        row_filters.append(f"[row{row}]")

    all_rows = "".join(row_filters)
    tile_filter += f"{all_rows}vstack=inputs={n_rows}[out]"

    simple_cmd += ["-filter_complex", tile_filter, "-map", "[out]", "-frames:v", "1", out_path]

    result = subprocess.run(simple_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg tile failed: {result.stderr[:500]}")
        # fallback: just copy first frame
        shutil.copy(frame_paths[0], out_path)
        return False
    return True


def main():
    args = parse_args()

    n_frames = args.frames
    n_cols = int(math.sqrt(n_frames))
    n_rows = math.ceil(n_frames / n_cols)
    # Adjust to fill grid
    while n_cols * n_rows < n_frames:
        n_rows += 1

    load_file(glb=args.glb, blend=args.blend)

    scene = bpy.context.scene
    arm_obj = find_armature()
    if arm_obj is None:
        print("ERROR: no armature found")
        sys.exit(1)

    action = find_action(args.action)
    if action is None:
        print("ERROR: no action found")
        sys.exit(1)

    assign_action(arm_obj, action)
    frame_start = int(action.frame_range[0])
    frame_end   = int(action.frame_range[1])
    total_frames = frame_end - frame_start + 1

    # Pick evenly spaced frames
    if n_frames >= total_frames:
        frames_to_render = list(range(frame_start, frame_end + 1))
    else:
        step = total_frames / n_frames
        frames_to_render = [int(frame_start + i * step) for i in range(n_frames)]

    scene.frame_set(frame_start)
    bpy.context.view_layer.update()
    center, height = get_char_center(arm_obj)

    setup_cameras(center, height)
    setup_light()

    out_prefix = args.out_prefix
    tmp_dir = os.path.dirname(out_prefix) or "/tmp"
    os.makedirs(tmp_dir, exist_ok=True)

    cam_configs = [
        ("FlipbookCamFront", "front"),
        ("FlipbookCam34",    "34"),
    ]

    contact_sheets = []
    for cam_name, suffix in cam_configs:
        cam_obj = bpy.data.objects.get(cam_name)
        if cam_obj is None:
            print(f"WARNING: camera {cam_name} not found, skipping")
            continue

        frame_paths = render_frames(
            scene, cam_obj, frames_to_render,
            tmp_dir, f"flipbook_{suffix}",
            args.width, args.height
        )

        sheet_path = f"{out_prefix}_{suffix}.jpg"
        ok = make_contact_sheet_ffmpeg(frame_paths, sheet_path, n_cols, n_rows, label=suffix)
        if ok:
            contact_sheets.append(sheet_path)
            print(f"CONTACT_SHEET:{sheet_path}")
        else:
            print(f"WARNING: contact sheet generation failed for {suffix}")

    # Cleanup per-frame PNGs
    for _, suffix in cam_configs:
        for f in frames_to_render:
            p = os.path.join(tmp_dir, f"flipbook_{suffix}_{f:04d}.png")
            if os.path.exists(p):
                os.remove(p)

    print(f"FLIPBOOK_DONE: {len(contact_sheets)} contact sheets written")
    for cs in contact_sheets:
        print(f"  {cs}")


if __name__ == "__main__":
    main()
