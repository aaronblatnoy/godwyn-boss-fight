"""Inspect i02 body proximity around the 24 rest-rig body bones."""
import bpy
import json
from pathlib import Path
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models/astra_character_v2_body_i02.blend"
OUT = ROOT / "renders/astra/char2/meshy_body_i02_coverage_probe.json"

CHILD = {
    "Hips": "Spine02", "Spine02": "Spine01", "Spine01": "Spine", "Spine": "neck",
    "neck": "Head", "Head": "head_end",
    "LeftShoulder": "LeftArm", "LeftArm": "LeftForeArm", "LeftForeArm": "LeftHand",
    "RightShoulder": "RightArm", "RightArm": "RightForeArm", "RightForeArm": "RightHand",
    "LeftUpLeg": "LeftLeg", "LeftLeg": "LeftFoot", "LeftFoot": "LeftToeBase",
    "RightUpLeg": "RightLeg", "RightLeg": "RightFoot", "RightFoot": "RightToeBase",
}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(MODEL))
    rig = bpy.data.objects["Armature"]
    body = bpy.data.objects["char1"]
    tree = KDTree(len(body.data.vertices))
    for vertex in body.data.vertices:
        tree.insert(body.matrix_world @ vertex.co, vertex.index)
    tree.balance()
    rows = {}
    for name, child in CHILD.items():
        start = rig.matrix_world @ rig.data.bones[name].head_local
        end = rig.matrix_world @ rig.data.bones[child].head_local
        midpoint = (start + end) * 0.5
        nearest, index, distance = tree.find(midpoint)
        rows[name] = {"start": list(start), "end": list(end), "midpoint": list(midpoint),
                      "nearest": list(nearest), "vertex": index, "distance_m": distance}
    OUT.write_text(json.dumps(rows, indent=2) + "\n")
    print("BODY_COVERAGE_PROBE", json.dumps(rows), flush=True)


if __name__ == "__main__":
    main()
