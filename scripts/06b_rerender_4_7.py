"""
06b_rerender_4_7.py — Re-render only poses 4 (overhead_slam) and 7 (double_spin).

Imports pose functions from 06_render_moveset.py to stay DRY.
Overwrites the existing PNGs in renders/moveset/.

Run: blender --background --python scripts/06b_rerender_4_7.py
"""

import sys
import os

import bpy
from mathutils import Vector

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

# Import the exact pose functions + helpers from 06_render_moveset
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "moveset", os.path.join(_SCRIPT_DIR, "06_render_moveset.py"))
_m = importlib.util.module_from_spec(_spec)
# Patch: the module calls main() at import time via the else branch.
# Temporarily stub it out.
import unittest.mock as _mock
with _mock.patch.object(_m, "__name__", "not_main_import"):
    # Actually we just need to exec selectively — load then patch main
    pass

# Simpler approach: exec the file content but replace the bottom guard
_src = open(os.path.join(_SCRIPT_DIR, "06_render_moveset.py")).read()
# Remove the bottom "else: main()" so import doesn't auto-run
_src = _src.replace("\nelse:\n    main()\n", "\n")
exec(compile(_src, "06_render_moveset.py", "exec"), globals())

# Now all functions from 06_render_moveset are in global scope.

_REPO_ROOT   = os.path.dirname(_SCRIPT_DIR)
_BLEND_PATH  = os.path.join(_REPO_ROOT, "models", "godwyn_phase1.blend")
_MOVESET_DIR = os.path.join(_REPO_ROOT, "renders", "moveset")
os.makedirs(_MOVESET_DIR, exist_ok=True)

RENDER_W = 1920
RENDER_H = 1080
RENDER_SAMPLES = 256

TARGETS = [
    ("4_overhead_slam",  pose_4_overhead_slam),
    ("7_double_spin",    pose_7_double_spin),
]


def main():
    print("=" * 60)
    print("[06b] Re-rendering poses 4 + 7 only")
    print("=" * 60)

    active_gpu = G.enable_gpu()
    print(f"[06b] GPU: {active_gpu}")

    if not os.path.isfile(_BLEND_PATH):
        print(f"[06b] FATAL: .blend not found: {_BLEND_PATH}", file=sys.stderr)
        sys.exit(1)

    bpy.ops.wm.open_mainfile(filepath=_BLEND_PATH)
    active_gpu = G.enable_gpu()
    print(f"[06b] GPU re-enabled: {active_gpu}")

    scene = bpy.context.scene
    configure_scene(scene)

    arm = _get_arm()
    print(f"[06b] Armature: '{arm.name}', {len(arm.pose.bones)} bones")

    sword = bpy.data.objects.get("Godwyn_Sword")
    if sword is None:
        print("[06b] FATAL: Godwyn_Sword missing", file=sys.stderr)
        sys.exit(1)

    failed = []

    for pose_name, pose_fn in TARGETS:
        out_path = os.path.join(_MOVESET_DIR, f"{pose_name}.png")
        print(f"\n[06b] --- Pose: {pose_name} ---")
        try:
            pose_fn(arm, scene)
            bpy.context.view_layer.update()
            render_pose(out_path, scene)
        except Exception as exc:
            import traceback
            msg = f"Pose {pose_name}: {exc}"
            print(f"[06b] FAIL: {msg}", file=sys.stderr)
            traceback.print_exc()
            failed.append(msg)
        finally:
            reset_pose(arm)
            restore_lights()
            bpy.context.view_layer.update()

    print("\n[06b] --- Results ---")
    for pose_name, _ in TARGETS:
        fpath = os.path.join(_MOVESET_DIR, f"{pose_name}.png")
        if os.path.isfile(fpath) and os.path.getsize(fpath) >= 1024:
            print(f"  OK   {pose_name}.png ({os.path.getsize(fpath)//1024} KB)")
        else:
            print(f"  MISS {pose_name}.png", file=sys.stderr)

    if failed:
        print(f"[06b] FAIL: {len(failed)} poses failed", file=sys.stderr)
        sys.exit(1)

    print("[06b] Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
