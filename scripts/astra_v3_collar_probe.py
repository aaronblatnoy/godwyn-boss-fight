"""Measure fist-source collar z distributions without modifying any asset."""

import json
import sys
from collections import Counter
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astra_v3_build as build


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/char2/meshy_v3fists_collar_probe.json"


def histogram(values, step=0.01):
    return dict(sorted(Counter(round(float(value) / step) * step for value in values).items()))


def main():
    _rig, body = build.import_rigged(ROOT / "models/meshy_body_godA_fists_rigged.glb")
    images = build.import_source_pbr(body.data.materials[0], ROOT / "models/meshy_body_godA_fists.glb")
    rows = build.face_samples(body, build.image_array(images["base"]), build.image_array(images["orm"]))
    region = [row for row in rows if abs(row["center"].x) <= 0.48 and -0.58 <= row["center"].y <= 0.22 and 2.35 <= row["center"].z <= 2.90]
    plate = [row for row in region if row["plate"]]
    nonplate = [row for row in region if not row["plate"]]
    report = {
        "region_faces": len(region),
        "plate_faces": len(plate),
        "nonplate_faces": len(nonplate),
        "plate_center_z_histogram_10mm": histogram([row["center"].z for row in plate]),
        "plate_vertex_z_percentiles_m": {str(p): float(np.percentile([point.z for row in plate for point in row["coords"]], p)) for p in (0, 1, 2, 5, 10, 25, 50, 75, 90, 95, 99, 100)},
        "plate_center_z_percentiles_m": {str(p): float(np.percentile([row["center"].z for row in plate], p)) for p in (0, 1, 2, 5, 10, 25, 50, 75, 90, 95, 99, 100)},
        "nonplate_center_z_histogram_10mm": histogram([row["center"].z for row in nonplate]),
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print("V3FISTS_COLLAR_PROBE_PASS", json.dumps({"plate_faces": len(plate), "plate_percentiles": report["plate_center_z_percentiles_m"]}), flush=True)


if __name__ == "__main__":
    main()
