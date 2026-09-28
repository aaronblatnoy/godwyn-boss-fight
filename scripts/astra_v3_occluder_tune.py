"""Replace the too-low collar cap with a rounded, thick interior lining disc."""

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
    parser.add_argument("--out", default="renders/astra/char2/meshy_v3fists_occluder_tune.json")
    return parser.parse_args(raw)


def root_path(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def main():
    args = cli()
    blend = root_path(args.blend)
    output = root_path(args.out)
    bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
    rig = bpy.data.objects["Astra_V3_Rig"]
    old = bpy.data.objects.get("Astra_V3_Collar_Occluder")
    assert old is not None
    mat = old.data.materials[0]
    bpy.data.objects.remove(old, do_unlink=True)
    center = (-0.205, -0.185, 2.640)
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=0.215, depth=0.180, end_fill_type="NGON", location=center)
    cap = bpy.context.object
    cap.name = "Astra_V3_Collar_Occluder"
    cap.scale.y = 0.76
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    cap.data.materials.append(mat)
    bevel = cap.modifiers.new("Astra V3 rounded lining edge", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 4
    bpy.context.view_layer.objects.active = cap
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    for poly in cap.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    world = cap.matrix_world.copy()
    cap.parent = rig
    cap.parent_type = "BONE"
    cap.parent_bone = "neck"
    cap.matrix_world = world
    report = {
        "schema": "astra-v3fists-occluder-tune",
        "object": cap.name,
        "shape": "rounded thick disc",
        "center_m": list(center),
        "radius_m": 0.215,
        "depth_m": 0.180,
        "y_scale": 0.76,
        "bevel_m": 0.035,
        "parent_bone": cap.parent_bone,
        "material": mat.name,
        "purpose": "fill the entire high-collar interior from frontal and three-quarter hero angles without reconstructing visible gold geometry",
    }
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_OCCLUDER_TUNE_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
