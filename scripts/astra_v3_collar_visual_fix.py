"""Remove the rejected rigid neck cylinder while retaining the hidden collar cap."""

import argparse
import json
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]


def cli():
    raw = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", default="models/astra_character_v3fists_wip.blend")
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_collar_visual_fix.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main():
    args = cli()
    blend = root_path(args.blend)
    output = root_path(args.out)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    bridge = bpy.data.objects.get("Astra_V3_Rigid_Neck_Bridge")
    assert bridge is not None
    removed = bridge.name
    bpy.data.objects.remove(bridge, do_unlink=True)
    cap = bpy.data.objects.get("Astra_V3_Collar_Occluder")
    assert cap is not None and cap.parent_bone == "Head"
    report = {
        "schema": "astra-v3fists-collar-visual-fix",
        "removed_object": removed,
        "reason": "fresh preview showed the rigid skin cylinder outside the high collar as a rectangular block",
        "retained_occluder": cap.name,
        "retained_occluder_parent_bone": cap.parent_bone,
        "visible_gold_rim_source": "preserved plate-classified char1 gorget geometry",
    }
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_COLLAR_VISUAL_FIX_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
