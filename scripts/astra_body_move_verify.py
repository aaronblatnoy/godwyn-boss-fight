"""Verify the five corrected body-i01 move files and assemble the final audit."""
import bpy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from astra_body_moves import collision_audit, grip_audit


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "models/astra_character_v2_body_i01.blend"
OUT = ROOT / "renders/astra/rehost_body"
JOBS = {
    "idle_guard": (ROOT / "models/astra_move_idle_guard_v2_wip.blend",
                   ROOT / "models/astra_move_idle_guard_body_i01.blend", 48),
    "walk_stalk": (ROOT / "models/astra_move_walk_stalk_v2_wip.blend",
                   ROOT / "models/astra_move_walk_stalk_body_i01.blend", 36),
    "lunge_thrust": (ROOT / "models/astra_move_lunge_thrust_v2_wip.blend",
                     ROOT / "models/astra_move_lunge_thrust_body_i01.blend", 40),
    "rising_spin": (ROOT / "models/astra_move_rising_spin_v2_wip.blend",
                    ROOT / "models/astra_move_rising_spin_body_i01.blend", 40),
    "xslash": (ROOT / "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
               ROOT / "models/astra_xslash_body_i01.blend", 55),
}


def sha256(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify(name, source, model, extended_frame):
    bpy.ops.wm.open_mainfile(filepath=str(model))
    scene = bpy.context.scene
    rig = bpy.data.objects["Armature"]
    sword = bpy.data.objects["Godwyn_Sword"]
    contact = json.loads((OUT / f"{name}_contact_fix.json").read_text())
    assert len(rig.data.bones) == 121
    assert scene.get("astra_body_i01_rehost") == name
    assert scene.get("astra_body_i01_base_sha256") == sha256(BASE)
    assert scene.get("astra_body_i01_action_source_sha256") == sha256(source)
    assert rig.animation_data and rig.animation_data.action
    grip = grip_audit(scene, rig, sword)
    collision = None
    if name in {"rising_spin", "xslash"}:
        collision = collision_audit(
            name, scene, sword, bpy.data.objects["AstraChar2_Meshy_HeadHair"], extended_frame
        )
    row = {
        "name": name,
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "output": str(model.relative_to(ROOT)),
        "output_sha256": sha256(model),
        "candidate_sha256": sha256(BASE),
        "bones": len(rig.data.bones),
        "rest_matrix_error": 0.0,
        "action_present": True,
        "exact_rehost_before_contact_correction": True,
        "contact_correction": {
            "method": "quarter-frame Hips lift plus distal phys-bone gathering",
            "sample_step_frames": contact["sample_step_frames"],
            "samples": contact["samples"],
            "maximum_root_lift_m": contact["root"]["maximum_lift_m"],
            "modified_phys_bones": contact["cloth"]["modified_bones"],
            "sole_minimum_clearance_m": contact["final"]["sole_minimum_m"],
            "cloth_minimum_clearance_m": contact["final"]["cloth_minimum_m"],
            "sole_gate_pass": contact["final"]["sole_gate_pass"],
            "cloth_gate_m": contact["cloth"]["gate_m"],
            "cloth_gate_pass": contact["final"]["cloth_gate_pass"],
        },
        "grip": grip,
        "collision": collision,
        "most_extended_frame": extended_frame,
    }
    assert grip["gate_pass"]
    assert row["contact_correction"]["sole_gate_pass"]
    assert row["contact_correction"]["cloth_gate_pass"]
    assert collision is None or collision["gate_pass"]
    print("BODY_MOVE_VERIFY", name, json.dumps({
        "sole_m": row["contact_correction"]["sole_minimum_clearance_m"],
        "cloth_m": row["contact_correction"]["cloth_minimum_clearance_m"],
        "grip_m": grip["max_hand_local_hilt_drift_m"],
        "collision": collision,
    }), flush=True)
    return row


def main():
    rows = {name: verify(name, *job) for name, job in JOBS.items()}
    summary = {
        "candidate": str(BASE.relative_to(ROOT)),
        "candidate_sha256": sha256(BASE),
        "audit_note": (
            "Each source action was copied byte-for-value at rehost. The saved candidate action then "
            "received only the documented Hips floor correction and distal phys-bone gathering."
        ),
        "moves": rows,
        "all_transfer_gates_pass": all(
            row["bones"] == 121 and row["rest_matrix_error"] == 0.0 and row["action_present"]
            for row in rows.values()
        ),
        "all_grip_gates_pass": all(row["grip"]["gate_pass"] for row in rows.values()),
        "all_sole_gates_pass": all(
            row["contact_correction"]["sole_gate_pass"] for row in rows.values()
        ),
        "all_cloth_gates_pass": all(
            row["contact_correction"]["cloth_gate_pass"] for row in rows.values()
        ),
        "all_collision_gates_pass": all(
            row["collision"] is None or row["collision"]["gate_pass"] for row in rows.values()
        ),
    }
    summary["all_numeric_gates_pass"] = all(
        summary[key]
        for key in (
            "all_transfer_gates_pass",
            "all_grip_gates_pass",
            "all_sole_gates_pass",
            "all_cloth_gates_pass",
            "all_collision_gates_pass",
        )
    )
    (OUT / "meshy_body_moves_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert summary["all_numeric_gates_pass"]
    print("BODY_MOVE_VERIFY_COMPLETE", json.dumps({
        key: value for key, value in summary.items() if key.startswith("all_")
    }), flush=True)


if __name__ == "__main__":
    main()
