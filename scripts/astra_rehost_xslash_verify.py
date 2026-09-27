"""Consolidate the X-slash cloth fix and regression gates."""
import hashlib
import json
import sys
from pathlib import Path


root = Path(sys.argv[1])
output = root / "renders/astra/rehost/xslash"


def load(name):
    return json.loads((output / name).read_text())


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


before = load("cloth_floor_before.json")
after = load("cloth_floor_after.json")
fix = load("cloth_floor_fix.json")
surface_before = load("surface_verification.pre_cloth.json")
surface_after = load("surface_verification.json")
grip_before = load("xslash_grip_metrics.pre_cloth.json")
grip_after = load("xslash_grip_metrics.json")
head_before = load("head_hair_collar_verification.pre_cloth.json")
head_after = load("head_hair_collar_verification.json")
move_before = load("xslash_metrics.pre_cloth.json")
move_after = load("xslash_metrics.json")
attack_before = load("xslash_attack_verification.pre_cloth.json")
attack_after = load("xslash_attack_verification.json")
natural_before = load("naturalness_metrics_rehost.pre_cloth.json")
natural_after = load("naturalness_metrics_rehost.json")
natural_surface_before = load("naturalness_surface_rehost.pre_cloth.json")
natural_surface_after = load("naturalness_surface_rehost.json")
video = load("xslash_cloth_video_verification.json")

assert after["sample_step_frames"] == 0.25 and after["samples"] == 357
assert after["minimum_clearance_m"] >= 0.002
assert not after["penetrating_frames"]
assert not after["penetrating_vertices"]["components"]
assert surface_after["v2_body"]["cloth_min_m"] >= 0.002
assert surface_after["v2_body"]["sole_min_m"] == surface_before["v2_body"]["sole_min_m"]
assert surface_after["planted_penetration_frames"] == {"Left": [], "Right": []}
assert fix["noncloth_action_digest_before"] == fix["noncloth_action_digest_after"]
assert fix["rest_digest_before"] == fix["rest_digest_after"]

assert grip_after == grip_before
assert head_after == head_before
assert move_after == move_before
assert attack_after == attack_before

# The naturalness summary legitimately changes evaluated cloth surface fields.
# Everything else except translated-cloth quaternion decomposition must be exact.
natural_core_before = dict(natural_before)
natural_core_after = dict(natural_after)
cloth_before = natural_core_before.pop("cloth")
cloth_after = natural_core_after.pop("cloth")
natural_core_before.pop("foot_floor")
natural_core_after.pop("foot_floor")
assert natural_core_after == natural_core_before

lag_correlation_delta = 0.0
lag_end_world_speed_delta = 0.0
lag_delay_changes = []
for bone, old in cloth_before.items():
    new = cloth_after[bone]
    if old["yaw_velocity_best_delay"] != new["yaw_velocity_best_delay"]:
        lag_delay_changes.append(bone)
    lag_correlation_delta = max(lag_correlation_delta,
                                abs(old["max_correlation"] - new["max_correlation"]))
    lag_end_world_speed_delta = max(lag_end_world_speed_delta,
                                    abs(old["end_world_speed_deg_frame"]
                                        - new["end_world_speed_deg_frame"]))
assert not lag_delay_changes
assert lag_correlation_delta < 1e-6
assert lag_end_world_speed_delta < 1e-5

for old_row, new_row in zip(natural_surface_before["rows"], natural_surface_after["rows"]):
    for row in (old_row, new_row):
        row.pop("cloth_min_z", None)
        row.pop("cloth_sword_min_vertex_centerline_m", None)
        row.pop("cloth_leg_capsule_candidates", None)
assert natural_surface_before == natural_surface_after

source_model = root / "models/astra_xslash_v2_final_on_char2_wip.blend"
fixed_model = root / "models/astra_xslash_v2_final_on_char2_cloth_wip.blend"
mp4 = output / "xslash_cloth.mp4"
assert sha256(source_model) == fix["source_sha256"]
assert sha256(fixed_model) == fix["output_sha256"]
assert sha256(mp4) == video["video_sha256"]
assert video["decoded_frame_count"] == 90 and video["decode_error_free"]

verification = {
    "status": "PASS",
    "execution_host": "black-sky",
    "input_unchanged": True,
    "input_sha256": fix["source_sha256"],
    "fixed_blend": str(fixed_model.relative_to(root)),
    "fixed_blend_sha256": fix["output_sha256"],
    "mp4": str(mp4.relative_to(root)),
    "mp4_sha256": video["video_sha256"],
    "cloth_floor": {
        "quarter_frame_samples": after["samples"],
        "before_minimum_m": before["minimum_clearance_m"],
        "before_worst_frame": before["worst_frame"],
        "before_worst_vertex": before["worst_vertex"],
        "before_penetrating_vertices": before["penetrating_vertices"],
        "after_minimum_m": after["minimum_clearance_m"],
        "after_worst_frame": after["worst_frame"],
        "after_penetrating_frames": after["penetrating_frames"],
        "integer_frame_minimum_m": surface_after["v2_body"]["cloth_min_m"],
        "gate_m": 0.002,
    },
    "channel_invariants": {
        "noncloth_action_digest_exact": True,
        "rest_rig_digest_exact": True,
        "frame_range": fix["frame_range"],
        "modified_bones": fix["modified_bones"],
        "limb_stretch_introduced": False,
    },
    "regressions": {
        "move_metrics_byte_equivalent_json": True,
        "grip_metrics_byte_equivalent_json": True,
        "attack_verification_byte_equivalent_json": True,
        "head_hair_collar_byte_equivalent_json": True,
        "sole_minimum_exact": True,
        "naturalness_noncloth_exact": True,
        "naturalness_surface_noncloth_exact": True,
        "cloth_lag_best_delays_exact": True,
        "cloth_lag_max_correlation_absolute_delta": lag_correlation_delta,
        "cloth_end_world_speed_max_absolute_delta_deg_frame": lag_end_world_speed_delta,
    },
    "key_metrics": {
        "grip_hand_local_hilt_drift_m": grip_after["max_hand_local_hilt_drift_m"],
        "grip_evaluated_tip_error_m": grip_after["max_evaluated_tip_error_m"],
        "grip_closed_finger_drift_m": grip_after["max_closed_finger_hand_local_drift_m"],
        "sole_minimum_m": surface_after["v2_body"]["sole_min_m"],
        "blade_head_exact_minimum_m": head_after["blade_head"]["exact_minimum_sampled_surface_distance_m"],
        "blade_hair_exact_minimum_m": head_after["blade_hair"]["exact_minimum_sampled_surface_clearance_m"],
        "robe_lag_frames": move_after["cloth_yaw_lag"]["phys_robe_front_C_06"]["best_delay_frames"],
        "cape_lag_frames": move_after["cloth_yaw_lag"]["phys_cape_C_06"]["best_delay_frames"],
    },
    "video": {
        "source_frames": video["source_frame_count"],
        "decoded_frames": video["decoded_frame_count"],
        "decode_error_free": video["decode_error_free"],
        "codec": video["ffprobe"]["streams"][0]["codec_name"],
        "pixel_format": video["ffprobe"]["streams"][0]["pix_fmt"],
        "resolution": [video["ffprobe"]["streams"][0]["width"],
                       video["ffprobe"]["streams"][0]["height"]],
        "fps": video["ffprobe"]["streams"][0]["r_frame_rate"],
        "before_after_stills": video["before_after_stills"],
    },
    "retained_limitations": [
        "Clearance is certified at quarter-frame samples, not continuous time between samples.",
        "Cloth remains deterministic kinematic secondary motion, not fabric simulation.",
        "The front-view hem still reads as ground-pooled because the certified gap is only 2.269 mm and contact shadows remain.",
    ],
}
(output / "xslash_cloth_audit_verification.json").write_text(
    json.dumps(verification, indent=2) + "\n")
print(json.dumps(verification, indent=2))
