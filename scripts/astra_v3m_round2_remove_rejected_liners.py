"""Remove liner experiments rejected by direct render review."""

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_round2_wip.blend"
REPORT = ROOT / "renders/astra/char2/astra_v3m_round2_build.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    removed = []
    for name in (
        "AstraChar2_R2_TorsoOccluder",
        "AstraChar2_R2_HemLiner",
        "AstraChar2_R2_LargeTorsoPatches",
    ):
        old = bpy.data.objects.get(name)
        if old:
            removed.append(name)
            bpy.data.objects.remove(old, do_unlink=True)
    report = json.loads(REPORT.read_text())
    report["gap_and_hem_fix"]["liner_experiments"] = {
        "status": "rejected and removed",
        "removed_objects": removed,
        "reason": "own-eye hero review found visible primitive panels worse than the source discontinuities",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("V3M_R2_REJECTED_LINERS_REMOVED", json.dumps(removed), flush=True)


if __name__ == "__main__":
    main()
