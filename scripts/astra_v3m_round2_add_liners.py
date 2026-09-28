"""Add recessed fabric liners behind large Meshy torso/hem openings."""

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from astra_v3m_retarget_world import add_gap_occluders


BLEND = ROOT / "models/astra_character_v3m_round2_wip.blend"
REPORT = ROOT / "renders/astra/char2/astra_v3m_round2_build.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    for name in (
        "AstraChar2_R2_TorsoOccluder",
        "AstraChar2_R2_HemLiner",
        "AstraChar2_R2_LargeTorsoPatches",
    ):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    result = add_gap_occluders(bpy.data.objects["Astra_V3_Rig"])
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report = json.loads(REPORT.read_text())
    report["gap_and_hem_fix"]["large_boundary_patches"] = {
        "status": "rejected and removed",
        "reason": "touching upper boundary cycles include the intended neckline; direct closure produced a visible fan",
    }
    report["gap_and_hem_fix"]["large_open_shell_liners"] = result
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_R2_LINERS_PASS", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
