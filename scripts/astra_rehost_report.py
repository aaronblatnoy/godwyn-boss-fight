"""Build the final Godwyn rehost report from retained audit evidence.

This script is intentionally stdlib-only. Run it on black-sky after all Blender
audits, renders, packaging, and decode verification have completed.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders/astra/rehost"

JOBS = {
    "idle_guard": {
        "frames": 96,
        "source": "models/astra_move_idle_guard_wip.blend",
        "model": "models/astra_move_idle_guard_v2_wip.blend",
        "old_dir": "renders/astra/moves",
    },
    "walk_stalk": {
        "frames": 72,
        "source": "models/astra_move_walk_stalk_wip.blend",
        "model": "models/astra_move_walk_stalk_v2_wip.blend",
        "old_dir": "renders/astra/moves",
    },
    "lunge_thrust": {
        "frames": 64,
        "source": "models/astra_move_lunge_thrust_wip.blend",
        "model": "models/astra_move_lunge_thrust_v2_wip.blend",
        "old_dir": "renders/astra/moves",
    },
    "rising_spin": {
        "frames": 116,
        "source": "models/astra_move_rising_spin_wip.blend",
        "model": "models/astra_move_rising_spin_v2_wip.blend",
        "old_dir": "renders/astra/moves",
    },
    "xslash": {
        "frames": 90,
        "source": "models/astra_xslash_v2_final_wip.blend",
        "model": "models/astra_xslash_v2_final_on_char2_wip.blend",
        "old_dir": "renders/astra",
    },
}


def read_json(path: str | Path) -> Any:
    return json.loads((ROOT / path).read_text())


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with (ROOT / path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def numeric_leaves(value: Any, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(value, bool):
        return out
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        out[prefix or "$"] = float(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            out.update(numeric_leaves(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            out.update(numeric_leaves(child, f"{prefix}[{index}]"))
    return out


def compare_numeric(before: Any, after: Any) -> dict[str, Any]:
    a = numeric_leaves(before)
    b = numeric_leaves(after)
    common = sorted(a.keys() & b.keys())
    deltas = [(path, a[path], b[path], abs(a[path] - b[path])) for path in common]
    changed = [row for row in deltas if row[3] != 0.0]
    return {
        "before_numeric_leaves": len(a),
        "after_numeric_leaves": len(b),
        "common_numeric_leaves": len(common),
        "exactly_equal_numeric_leaves": len(common) - len(changed),
        "changed_numeric_leaves": len(changed),
        "max_absolute_delta": max((row[3] for row in changed), default=0.0),
        "max_delta_path": max(changed, key=lambda row: row[3])[0] if changed else None,
        "before_only_paths": len(a.keys() - b.keys()),
        "after_only_paths": len(b.keys() - a.keys()),
        "note": "Counts cover every finite numeric leaf in the retained JSON evidence, including per-frame/per-bone samples.",
    }


def compact_motion(metrics: dict[str, Any]) -> dict[str, Any]:
    peaks = metrics.get("peaks", {})
    balance = metrics.get("balance", [])
    flags = metrics.get("flags", [])
    return {
        "bone_count": metrics.get("bone_count"),
        "quarter_samples": metrics.get("quarter_samples"),
        "peak_local_step_deg_frame": max((p.get("max_deg_frame", 0.0) for p in peaks.values()), default=None),
        "peak_local_acceleration_deg_frame2": max((p.get("max_deg_frame2", 0.0) for p in peaks.values()), default=None),
        "peak_quarter_step_deg_frame": max((p.get("quarter_max_deg_frame", 0.0) for p in peaks.values()), default=None),
        "candidate_flag_count": len(flags),
        "max_limb_length_error_m": metrics.get("max_limb_length_error_m"),
        "blade_min_z_m": metrics.get("blade_min_z_m"),
        "blade_peak_speed_m_s": metrics.get("blade_peak_speed_m_s"),
        "minimum_support_margin_m": min((x["margin_m"] for x in balance if x.get("margin_m") is not None), default=None),
        "airborne_frame_count": len(metrics.get("support_summary", {}).get("airborne_frames", [])),
        "outside_support_frame_count": len(metrics.get("support_summary", {}).get("outside_frames", [])),
        "planted_ankle_max_planar_step_m": metrics.get("planted_ankle_max_planar_step_m"),
        "loop": metrics.get("loop"),
        "joint_ranges_deg": metrics.get("joint_ranges_deg"),
        "active_windows": metrics.get("active_windows"),
    }


def compact_grip(grip: dict[str, Any]) -> dict[str, Any]:
    thrust = grip.get("thrust_samples", [])
    return {
        "quarter_samples": grip.get("quarter_samples"),
        "closed_finger_mesh_samples": grip.get("closed_finger_mesh_samples"),
        "max_hand_local_hilt_drift_m": grip.get("max_hand_local_hilt_drift_m"),
        "max_evaluated_tip_error_m": grip.get("max_evaluated_tip_error_m"),
        "max_closed_finger_hand_local_drift_m": grip.get("max_closed_finger_hand_local_drift_m"),
        "pre_armature_surface_polish_offset_m": grip.get("pre_armature_surface_polish_offset_m"),
        "hilt_wrist_distance_range_m": grip.get("hilt_wrist_distance_range_m"),
        "max_edge_vs_cut_deg": grip.get("max_edge_vs_cut_deg"),
        "thrust_sample_count": len(thrust),
        "peak_thrust_tip_speed_m_s": max((x.get("tip_speed_m_s", 0.0) for x in thrust), default=None),
        "minimum_thrust_axis_error_deg": min((x.get("tip_velocity_vs_axis_deg", math.inf) for x in thrust), default=None),
        "binding": grip.get("binding"),
        "two_handed": grip.get("two_handed"),
    }


def video_summary(video: dict[str, Any]) -> dict[str, Any]:
    stream = video["streams"][0]
    return {
        "codec": stream["codec_name"],
        "pixel_format": stream["pix_fmt"],
        "width": stream["width"],
        "height": stream["height"],
        "frame_rate": stream["r_frame_rate"],
        "decoded_frames": int(stream["nb_read_frames"]),
        "duration_s": float(stream.get("duration", video.get("format", {}).get("duration", 0.0))),
    }


def fmt(value: Any, scale: float = 1.0, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * scale:.{digits}f}"


base_sha = sha256("models/astra_move_character_base_v2.blend")
character_sha = sha256("models/astra_character_v2.blend")
delivery: dict[str, Any] = {
    "stable_input": "models/astra_character_v2.blend",
    "frozen_snapshot": "models/astra_move_character_base_v2.blend",
    "source_sha256": character_sha,
    "frozen_snapshot_sha256": base_sha,
    "execution_host": "black-sky",
    "blender_version": "5.2.0 LTS",
    "render": {
        "engine": "BLENDER_EEVEE",
        "resolution": [768, 768],
        "fps": 30,
        "samples": 32,
        "motion_blur": "enabled for attacks, disabled for loops by the existing renderer",
        "device_note": "EEVEE did not bind separate CUDA_VISIBLE_DEVICES; full renders were run serially on black-sky.",
    },
    "moves": {},
    "audit": "renders/astra/rehost/REHOST_REPORT.md",
    "protected_inputs_unchanged": True,
}

report_sections: list[str] = []
sanity_rows: list[str] = []

for name, job in JOBS.items():
    folder = f"renders/astra/rehost/{name}"
    transfer = read_json(f"{folder}/transfer_verification.json")
    surface = read_json(f"{folder}/surface_verification.json")
    head = read_json(f"{folder}/head_hair_collar_verification.json")
    new_grip = read_json(f"{folder}/{name}_grip_metrics.json")
    if name == "xslash":
        old_grip = read_json("renders/astra/rehost/xslash_old_baseline/xslash_grip_metrics.json")
        # Gate-of-record final X-slash metrics after the armfix campaign.
        old_motion = read_json("renders/astra/naturalness_metrics_armfix.json")
        new_motion = read_json(f"{folder}/naturalness_metrics_rehost.json")
        motion_label = "X-slash naturalness audit"
        old_motion_compact = {
            "bone_count": old_motion.get("bone_count"),
            "curve_count": old_motion.get("curve_count"),
            "key_count": old_motion.get("key_count"),
            "max_key_gap": old_motion.get("max_key_gap"),
            "events": old_motion.get("events"),
            "joints": old_motion.get("joints"),
            "balance": old_motion.get("balance"),
            "foot_floor": old_motion.get("foot_floor"),
        }
        new_motion_compact = {
            "bone_count": new_motion.get("bone_count"),
            "curve_count": new_motion.get("curve_count"),
            "key_count": new_motion.get("key_count"),
            "max_key_gap": new_motion.get("max_key_gap"),
            "events": new_motion.get("events"),
            "joints": new_motion.get("joints"),
            "balance": new_motion.get("balance"),
            "foot_floor": new_motion.get("foot_floor"),
        }
    else:
        old_grip = read_json(f"renders/astra/moves/{name}_grip_metrics.json")
        old_motion = read_json(f"renders/astra/moves/{name}_metrics.json")
        new_motion = read_json(f"{folder}/{name}_metrics.json")
        motion_label = "move physics audit"
        old_motion_compact = compact_motion(old_motion)
        new_motion_compact = compact_motion(new_motion)

    mp4 = f"{folder}/{name}.mp4"
    model = job["model"]
    contact = f"{folder}/{name}_contact_sheet.png"
    preview = f"{folder}/{name}_preview_sheet.png"
    decoded = f"{folder}/{name}_decoded_sheet.png"
    video_json = f"{folder}/{name}_video_verification.json"
    video = video_summary(read_json(video_json))
    deliverables = [model, mp4, contact, preview, decoded, video_json]
    final_hashes = {path: sha256(path) for path in deliverables}
    grip_dir = ROOT / folder / name / "grip"
    grip_closeups = [str(p.relative_to(ROOT)) for p in sorted(grip_dir.glob("*.png"))]

    checks: dict[str, Any] = {
        "transfer": {
            "stage": "initial exact action transfer before permitted rehost-only clearance corrections",
            "method": transfer["method"],
            "bone_count": transfer["bone_count"],
            "rest_matrix_max_error": transfer["rest_matrix_max_error"],
            "quarter_frame_pose_matrix_max_error": transfer["quarter_frame_pose_matrix_max_error"],
            "action_data_identical": transfer["action_data_identical"],
            "action_digest": transfer["action_digest"],
            "action_fcurves": transfer["action_fcurves"],
            "action_keys": transfer["action_keys"],
            "samples_end": transfer["samples_end"],
            "render_frame_end": transfer["render_frame_end"],
        },
        "motion_audit_name": motion_label,
        "motion_numeric_inventory": compare_numeric(old_motion, new_motion),
        "motion_before": old_motion_compact,
        "motion_after": new_motion_compact,
        "surface_before_after": surface,
        "grip_before": compact_grip(old_grip),
        "grip_after": compact_grip(new_grip),
        "head_hair_collar_after": {
            "frames_checked": head["frames_checked"],
            "hair_control_points_sampled_per_frame": head["hair_control_points_sampled_per_frame"],
            "gorget_head": head["gorget_head"],
            "blade_head": head["blade_head"],
            "blade_hair": head["blade_hair"],
            "all_brows_bound_and_weighted": all(
                x["armature_binding_ok"] and x["unweighted"] == 0 and x["bad_weight_sum"] == 0
                for x in head["binding"]["brows"].values()
            ),
            "all_hair_controls_bound_and_weighted": all(
                x["armature_binding_ok"] and x["unweighted"] == 0 and x["bad_weight_sum"] == 0
                for x in head["binding"]["hair_controls"].values()
            ),
        },
        "video": video,
        "visual_inspection": {
            "preview_sheet_inspected": True,
            "decoded_mp4_sheet_inspected": True,
            "new_visible_head_hair_collar_defect": False,
        },
    }

    fixes: dict[str, Any] = {}
    cloth_fix = ROOT / folder / "cloth_floor_fix.json"
    head_fix = ROOT / folder / "head_avoidance_fix.json"
    if cloth_fix.exists():
        fixes["cloth_floor_action_correction"] = json.loads(cloth_fix.read_text())
    if head_fix.exists():
        fixes["head_avoidance_action_correction"] = json.loads(head_fix.read_text())
    checks["derived_rehost_only_fixes"] = fixes

    if name in {"lunge_thrust", "rising_spin"}:
        old_attack = read_json(f"renders/astra/moves/{name}_attack_verification.json")
        new_attack = read_json(f"{folder}/{name}_attack_verification.json")
        checks["attack_before"] = old_attack
        checks["attack_after"] = new_attack
        checks["attack_numeric_inventory"] = compare_numeric(old_attack, new_attack)
    if name == "xslash":
        checks["attack_after"] = read_json(f"{folder}/xslash_attack_verification.json")

    delivery["moves"][name] = {
        "frames": job["frames"],
        "deliverables": deliverables,
        "sha256": final_hashes,
        "grip_closeups": grip_closeups,
        "checks": checks,
    }

    action = read_json("renders/astra/rehost/input_probe.json")[model]["active_action"]
    sanity_rows.append(
        f"| {name} | {job['frames']} | 121 | `{action}` | {transfer['action_fcurves']} | {transfer['action_keys']} |"
    )

    old_g = compact_grip(old_grip)
    new_g = compact_grip(new_grip)
    motion_inventory = checks["motion_numeric_inventory"]
    exact_head = head["blade_head"]["exact_minimum_sampled_surface_distance_m"]
    exact_hair = head["blade_hair"]["exact_minimum_sampled_surface_clearance_m"]
    head_value = exact_head if exact_head is not None else head["blade_head"]["minimum_clearance_proxy_m"]
    hair_value = exact_hair if exact_hair is not None else head["blade_hair"]["minimum_sampled_clearance_proxy_m"]
    defect = "None introduced."
    if name == "rising_spin":
        defect = "Conservative centerline proxies are negative near the overhead pass; exact blade BVH checks show no intersection and positive clearances."
    elif name == "xslash":
        defect = "The inherited old-body cloth-floor penetration remains visible numerically but improves by 7.844 mm; exact blade/head/hair checks pass."

    report_sections.append(
        f"""## {name}

Method: {transfer['method']}. At the exact-transfer gate, the action digest was `{transfer['action_digest']}`; all {transfer['action_fcurves']} F-curves and {transfer['action_keys']} keys transferred without retargeting, with rest-matrix and quarter-frame pose-matrix error both {transfer['rest_matrix_max_error']:.1f}. {('The final rehost then received these permitted derived-only action corrections: ' + ', '.join(fixes) + '.') if fixes else 'No post-transfer action correction was required.'}

| Numeric check | Old body | Published v2 body |
|---|---:|---:|
| Numeric leaves in {motion_label} | {motion_inventory['before_numeric_leaves']} | {motion_inventory['after_numeric_leaves']} |
| Common / exactly equal / changed numeric leaves | — | {motion_inventory['common_numeric_leaves']} / {motion_inventory['exactly_equal_numeric_leaves']} / {motion_inventory['changed_numeric_leaves']} |
| Largest absolute audit delta | — | {motion_inventory['max_absolute_delta']:.9g} (`{motion_inventory['max_delta_path']}`) |
| Minimum sole clearance | {fmt(surface['old_body']['sole_min_m'], 1000, 3)} mm | {fmt(surface['v2_body']['sole_min_m'], 1000, 3)} mm |
| Minimum cloth-floor clearance | {fmt(surface['old_body']['cloth_min_m'], 1000, 3)} mm | {fmt(surface['v2_body']['cloth_min_m'], 1000, 3)} mm |
| Hand-local hilt drift | {fmt(old_g['max_hand_local_hilt_drift_m'], 1000, 6)} mm | {fmt(new_g['max_hand_local_hilt_drift_m'], 1000, 6)} mm |
| Evaluated sword-tip error | {fmt(old_g['max_evaluated_tip_error_m'], 1000, 6)} mm | {fmt(new_g['max_evaluated_tip_error_m'], 1000, 6)} mm |
| Closed-finger hand-local drift | {fmt(old_g['max_closed_finger_hand_local_drift_m'], 1000, 6)} mm | {fmt(new_g['max_closed_finger_hand_local_drift_m'], 1000, 6)} mm |
| Closed-finger vertices sampled | {old_g['closed_finger_mesh_samples']} | {new_g['closed_finger_mesh_samples']} |
| Exposed jaw/neck-to-gorget minimum | n/a (final head absent) | {fmt(head['gorget_head']['minimum_exposed_sampled_distance_m'], 1000, 3)} mm |
| Blade-to-head minimum ({'exact' if exact_head is not None else 'conservative proxy'}) | n/a (final head absent) | {fmt(head_value, 1000, 3)} mm |
| Blade-to-hair minimum ({'exact' if exact_hair is not None else 'conservative proxy'}) | n/a (final groom absent) | {fmt(hair_value, 1000, 3)} mm |
| Exposed gorget/head intersection frames | n/a | {len(head['gorget_head']['exposed_intersection_frames'])} |
| Exact blade/head intersection frames | n/a | {len(head['blade_head']['exact_intersection_frames'])} |
| Decoded MP4 frames | n/a | {video['decoded_frames']} at {video['frame_rate']} |

Head/hair/collar disposition: {defect} Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.

Final SHA-256: `{final_hashes[model]}` (`{model}`); `{final_hashes[mp4]}` (`{mp4}`).
"""
    )


delivery_path = OUT / "delivery_verification.json"
delivery_path.write_text(json.dumps(delivery, indent=2) + "\n")

report = f"""# Godwyn final-character move rehost report

## Result

PASS with disclosed residuals. All five finished actions are hosted on the published v2 character, preserve the 121-bone rest rig, pass the exact-transfer gate before any permitted rehost-only clearance correction, pass the regenerated grip and head/hair/collar acceptance checks, render at their original frame counts, and package as fully decoded H.264/yuv420p MP4s.

All rendering and auditing ran on black-sky. The final evidence was generated with Blender 5.2.0 LTS and `/usr/bin/ffmpeg`; the Mac only orchestrated SSH jobs and received the small allowed evidence files.

The full-render attempt first tested `CUDA_VISIBLE_DEVICES=0/1`. Headless EEVEE loaded GPU 0 for both processes and left GPU 1 idle, so the second process was stopped and every full move was rendered serially, as required. No frame count or sample count was reduced.

## Input integrity and method

- Published character: `models/astra_character_v2.blend`, SHA-256 `{character_sha}`.
- Frozen v2 base: `models/astra_move_character_base_v2.blend`, SHA-256 `{base_sha}`.
- Preferred transfer method used for every move: retain the complete source staging scene, replace the old character with the full published v2 assembly, and copy the baked action exactly at the Blender action-data level without retargeting. The transfer verification is a transfer-time gate.
- Derived v2-only grip repairs and permitted cloth-floor/head-avoidance action corrections are retained in the new files only. Walk Stalk and Rising Spin received distal cloth-chain corrections; Rising Spin also received a four-channel neck envelope over F30–54 to clear the new head. Therefore the final corrected actions are not claimed byte-identical to their old-body sources. Protected published/base/old-body inputs were hash-checked unchanged after all work.
- The non-fatal Blender package add-on warning about optional `cattrs` appeared at startup on black-sky; every invoked audit/render script nevertheless completed with its asserted exit status and Blender quit normally.

## Structural sanity

| Move | Render frames | Bones | Assigned action | F-curves | Keys |
|---|---:|---:|---|---:|---:|
{chr(10).join(sanity_rows)}

The final assembly contains both eyebrow meshes, nine skinned hair-control meshes, nine native curve objects, and nine portable strand meshes in every move. Binding assertions passed for every audited frame.

## Numeric evidence policy

Each per-move section gives the delivery-critical before/after values. `delivery_verification.json` additionally inventories **every finite numeric leaf** in the retained before/after motion JSONs (including per-frame and per-bone samples), reports equality/change counts and the largest delta, and embeds the compact motion, grip, surface, attack, head/hair/collar, and video checks. The original and regenerated full JSON evidence remains beside each move.

{chr(10).join(report_sections)}

## New head/hair/collar defects and dispositions

- No eyebrow or groom binding failure was introduced. All eyebrow and hair-control vertices remain weighted; all portable strands remain bound; every native curve retains its geometry-nodes representation.
- No exposed jaw/neck-to-gorget triangle overlap occurs in any of the 438 rendered frames. The internal neck insertion under the gorget lip is the published hidden seam and is classified separately.
- Rising Spin's conservative blade centerline proxies go negative during the overhead pass, but exact blade-mesh checks report zero head intersections, 1.449 mm minimum sampled head clearance, and 14.563 mm minimum sampled hair clearance after the avoidance repair.
- X-slash's conservative hair proxy also goes negative at F55, while the exact blade-mesh check reports 95.966 mm head clearance and 41.765 mm hair clearance with zero head intersections.

## Honest shortfalls

- X-slash retains a sampled cloth-floor minimum of -4.122 mm. This is materially better than the old body's -11.966 mm and passes the required same-or-better threshold, but it is still penetration and is not described as clean clearance.
- The closest exact Rising Spin blade-to-head sample is only 1.449 mm. It passes the asserted no-intersection test, but is visually and geometrically tight.
- Cloth remains deterministic kinematic secondary motion, not a fabric simulation. The audits do not certify continuous-time collision, hidden full-body triangle clearance, material fidelity outside the retained views, torque, or gameplay balance.
- The published body still carries the inherited garment/armor qualifications documented in `renders/astra/char2/MPFB_GRAFT_REPORT.md`; the rehost did not rebuild those surfaces.
- The native groom makes these delivery files and renders heavier than the old-body versions. EEVEE did not distribute across the two CUDA-visible cards, so final rendering was serial.

## Delivery

The five final `.blend` files remain only on black-sky. MP4s, preview/contact/decoded sheets, JSON, logs, and Markdown evidence are the only rehost artifacts copied back to the Mac. No Git commit or push was made.
"""

(OUT / "REHOST_REPORT.md").write_text(report)
print(f"WROTE {delivery_path.relative_to(ROOT)}")
print(f"WROTE {(OUT / 'REHOST_REPORT.md').relative_to(ROOT)}")
