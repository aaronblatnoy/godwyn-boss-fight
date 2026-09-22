"""Create isolated rehost manifests from immutable delivered evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "renders/astra/rehost"
MODELS = {
    "idle_guard": "models/astra_move_idle_guard_v2_wip.blend",
    "walk_stalk": "models/astra_move_walk_stalk_v2_wip.blend",
    "lunge_thrust": "models/astra_move_lunge_thrust_v2_wip.blend",
    "rising_spin": "models/astra_move_rising_spin_v2_wip.blend",
    "xslash": "models/astra_xslash_v2_final_on_char2_wip.blend",
}

for name in ["idle_guard", "walk_stalk", "lunge_thrust", "rising_spin"]:
    manifest = json.loads((ROOT / f"renders/astra/moves/{name}_manifest.json").read_text())
    manifest.update({
        "source": "models/astra_move_character_base_v2.blend",
        "model": MODELS[name],
        "rehosted_from": f"models/astra_move_{name}_wip.blend",
        "source_sha256": "c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386",
    })
    folder = DEST / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

xslash = {
    "name": "xslash",
    "description": "Naturalness-approved two-cut X-slash rehosted onto final char2.",
    "cut_type": "slash",
    "contact_frames": [1, 13, 27, 31, 34, 36, 38, 40, 43, 46, 53, 54, 57, 61, 70, 80, 90],
    "grip_frames": [1, 31, 38, 40, 46, 54, 57, 61, 90],
    "active": [[37, 42], [54, 59]],
    "edge_check_windows": [[37, 42], [54, 59]],
    "cascade_window": [30, 61],
    "planted": {
        "Left": [f <= 29 or f >= 40 for f in range(1, 91)],
        "Right": [True] * 90,
    },
    "frames": 90,
    "samples_end": 90,
    "loop": False,
    "travel": [0.0, 0.0, 0.0],
    "source": "models/astra_move_character_base_v2.blend",
    "model": MODELS["xslash"],
    "rehosted_from": "models/astra_xslash_v2_final_wip.blend",
    "source_sha256": "c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386",
}
folder = DEST / "xslash"
folder.mkdir(parents=True, exist_ok=True)
(folder / "xslash_manifest.json").write_text(json.dumps(xslash, indent=2) + "\n")
print("REHOST MANIFESTS READY")
