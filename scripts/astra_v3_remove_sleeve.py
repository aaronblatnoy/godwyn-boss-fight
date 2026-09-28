"""Remove the rejected procedural seam sleeve after semantic render diagnosis."""

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3_wip.blend"
OUT = ROOT / "renders/astra/char2/meshy_v3_sleeve_rejection.json"


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    sleeve = bpy.data.objects.get("Astra_V3_SeamSleeve")
    assert sleeve is not None
    report = {
        "schema": "astra-v3-sleeve-rejection",
        "removed_object": sleeve.name,
        "reason": "semantic close-up proved armature deformation displaced the sleeve outside the neck silhouette",
        "replacement": "approved donor neck blend plus corrected head base-color neckline",
    }
    bpy.data.objects.remove(sleeve, do_unlink=True)
    bpy.context.scene["astra_v3_sleeve_rejection"] = json.dumps(report)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3_SLEEVE_REJECTION_PASS", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
