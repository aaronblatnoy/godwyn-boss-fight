"""Give Round-2 boundary caps a visible fabric-underlayer material (black-sky)."""

import json
from collections import Counter, defaultdict
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / "models/astra_character_v3m_round2_wip.blend"
REPORT = ROOT / "renders/astra/char2/astra_v3m_round2_build.json"


def key(vector):
    return tuple(round(float(value), 4) for value in vector)


def main():
    bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
    body = bpy.data.objects["char1"]
    patch = bpy.data.objects["AstraChar2_R2_BoundaryPatches"]
    material = bpy.data.materials.get("V3M R2 visible blue underlayer")
    if material is None:
        material = bpy.data.materials.new("V3M R2 visible blue underlayer")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.012, 0.045, 0.20, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.18
    bsdf.inputs["Roughness"].default_value = 0.46
    patch.data.materials.clear()
    patch.data.materials.append(material)
    counts = Counter()
    for polygon in patch.data.polygons:
        polygon.material_index = 0
        counts[0] += 1
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    report = json.loads(REPORT.read_text())
    report["gap_and_hem_fix"]["cap_material_method"] = "single visible deep-blue fabric underlayer; no texture projection or black void"
    report["gap_and_hem_fix"]["cap_faces_by_material_slot"] = {str(index): count for index, count in sorted(counts.items())}
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3M_R2_PATCH_MATERIAL_PASS", json.dumps({"faces": len(patch.data.polygons), "by_slot": dict(counts)}), flush=True)


if __name__ == "__main__":
    main()
