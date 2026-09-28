"""Compare i01 and i02 body edge stretch at each move's extended frame."""
import bpy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from astra_body_move_verify import edge_stretch

OUT = ROOT / "renders/astra/rehost_body_i02/meshy_body_i02_stretch_comparison.json"
FRAMES = {"idle_guard": 48, "walk_stalk": 36, "lunge_thrust": 40,
          "rising_spin": 40, "xslash": 55}


def path_for(iteration, move):
    stem = "astra_xslash" if move == "xslash" else f"astra_move_{move}"
    return ROOT / f"models/{stem}_body_{iteration}.blend"


def main():
    report = {}
    for move, frame in FRAMES.items():
        report[move] = {}
        for iteration in ("i01", "i02"):
            model = path_for(iteration, move)
            bpy.ops.wm.open_mainfile(filepath=str(model))
            row = edge_stretch(bpy.context.scene, bpy.data.objects["char1"], frame)
            row["model"] = str(model.relative_to(ROOT))
            report[move][iteration] = row
        report[move]["i02_vs_i01_max_ratio"] = (
            report[move]["i02"]["maximum_ratio"] / report[move]["i01"]["maximum_ratio"]
        )
        print("BODY_STRETCH_COMPARE", move, json.dumps(report[move]), flush=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
