"""Publish X-slash cloth-fix report and delivery metadata."""
import hashlib
import json
import sys
from pathlib import Path


root = Path(sys.argv[1])
report_path = root / "renders/astra/rehost/REHOST_REPORT.md"
delivery_path = root / "renders/astra/rehost/delivery_verification.json"
output = root / "renders/astra/rehost/xslash"
verification = json.loads((output / "xslash_cloth_audit_verification.json").read_text())
surface = json.loads((output / "surface_verification.json").read_text())
fix = json.loads((output / "cloth_floor_fix.json").read_text())
video = json.loads((output / "xslash_cloth_video_verification.json").read_text())


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


section = f"""## X-slash cloth-floor fix

All Blender, audit, render, ffmpeg, and packaging compute for this follow-up ran on **black-sky**. The immutable input remained `models/astra_xslash_v2_final_on_char2_wip.blend` (SHA-256 `{verification['input_sha256']}`); the fixed scene is `models/astra_xslash_v2_final_on_char2_cloth_wip.blend`.

The new deformed-geometry probe checked all **357 quarter-frame samples**. The true before minimum was **{verification['cloth_floor']['before_minimum_m'] * 1000:.3f} mm at F{verification['cloth_floor']['before_worst_frame']:.2f}**, slightly below the earlier integer-only −4.122 mm record. Exactly four robe-hem vertices penetrated: **49060, 49875, 50781, 50786**, owned by `phys_robe_side_L` / `phys_robe_side_R`; cape and arm-bound undersleeves had no penetrating vertices. Complete vertex/frame/coordinate evidence is in `renders/astra/rehost/xslash/cloth_floor_before.json`.

Method: measured quarter-frame deficits were given a short conservative envelope, then distributed progressively in world Z over existing distal secondary links 03 through each affected chain tip. Only location curves on `phys_cape_R_03..06`, `phys_robe_side_L_03..07`, and `phys_robe_side_R_03..07` changed. The 90-frame action range, every body/arm/sword/head/foot channel, the rest rig, mesh, weights, and limb lengths were untouched; the non-cloth action and rest-rig digests are exact matches. This is distal cloth gathering, not limb scaling or a body translation.

After save/reload, the minimum across all 357 samples is **+{verification['cloth_floor']['after_minimum_m'] * 1000:.3f} mm** (gate +2.000 mm), with zero penetrating cloth vertices or frames. The independent integer-frame surface audit is **+{verification['cloth_floor']['integer_frame_minimum_m'] * 1000:.3f} mm**. Sole clearance remains exactly **{verification['key_metrics']['sole_minimum_m'] * 1000:.3f} mm**. Grip remains {verification['key_metrics']['grip_hand_local_hilt_drift_m'] * 1e6:.3f} µm hand-local / {verification['key_metrics']['grip_evaluated_tip_error_m'] * 1e6:.3f} µm evaluated tip; exact blade-to-head and blade-to-hair clearances remain **{verification['key_metrics']['blade_head_exact_minimum_m'] * 1000:.3f} mm / {verification['key_metrics']['blade_hair_exact_minimum_m'] * 1000:.3f} mm**. Robe/cape lag stays **+{verification['key_metrics']['robe_lag_frames']} / +{verification['key_metrics']['cape_lag_frames']} frames**. Move, grip, attack, and head/hair/collar JSON are byte-equivalent to their pre-fix baselines; all non-cloth naturalness and surface fields are exact.

The complete 90-frame clip was rendered at 768×768, 32 samples, 30 fps with the existing attack render settings and decoded without error. All six consecutive decoded sheets (F1–90), the contact sheet, and the three full-resolution worst-sample pairs (left before / right after: F57.50, F56.50, F57.25) were inspected; no new pop, discontinuity, exposed breakthrough, or head/hair/collar defect was found.

Final SHA-256: `{verification['fixed_blend_sha256']}` (`models/astra_xslash_v2_final_on_char2_cloth_wip.blend`); `{verification['mp4_sha256']}` (`renders/astra/rehost/xslash/xslash_cloth.mp4`).

Retained limitation: clearance is certified at quarter-frame samples, not continuously between samples. Cloth remains deterministic kinematic secondary motion rather than fabric simulation, and the front view still reads as lightly ground-pooled because the certified gap is only 2.269 mm with contact shadows.

"""

text = report_path.read_text()
start = text.find("## X-slash cloth-floor fix")
if start >= 0:
    end = text.find("\n## ", start + 3)
    text = text[:start] + (text[end + 1:] if end >= 0 else "")
anchor = "## New head/hair/collar defects and dispositions"
assert anchor in text
text = text.replace(anchor, section + anchor, 1)
text = text.replace(
    "Head/hair/collar disposition: The inherited old-body cloth-floor penetration remains visible numerically but improves by 7.844 mm; exact blade/head/hair checks pass. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.",
    "Head/hair/collar disposition: The dedicated cloth-floor follow-up below supersedes the residual penetration recorded here; exact blade/head/hair checks continue to pass. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.")
text = text.replace(
    "- X-slash retains a sampled cloth-floor minimum of -4.122 mm. This is materially better than the old body's -11.966 mm and passes the required same-or-better threshold, but it is still penetration and is not described as clean clearance.",
    "- X-slash's prior -4.122 mm integer-frame residual is superseded by the dedicated cloth-floor fix: +2.269 mm minimum at quarter frames and zero sampled penetration. Continuous-time collision between quarter samples remains uncertified.")
text = text.replace(
    "The five final `.blend` files remain only on black-sky. MP4s, preview/contact/decoded sheets, JSON, logs, and Markdown evidence are the only rehost artifacts copied back to the Mac.",
    "Final `.blend` deliverables remain only on black-sky; the original X-slash input is retained there read-only alongside the new cloth-fixed file. MP4s, preview/contact/decoded sheets, JSON, logs, and Markdown evidence are the only rehost artifacts copied back to the Mac.")
report_path.write_text(text)

manifest_path = output / "xslash_manifest.json"
manifest = json.loads(manifest_path.read_text())
manifest["model"] = "models/astra_xslash_v2_final_on_char2_cloth_wip.blend"
manifest["description"] = "Naturalness-approved two-cut X-slash rehosted onto final char2; quarter-frame cloth-floor clearance fixed."
manifest["cloth_floor_fix"] = {
    "source": "models/astra_xslash_v2_final_on_char2_wip.blend",
    "source_sha256": verification["input_sha256"],
    "model_sha256": verification["fixed_blend_sha256"],
    "minimum_quarter_frame_clearance_m": verification["cloth_floor"]["after_minimum_m"],
    "required_clearance_m": verification["cloth_floor"]["gate_m"],
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

delivery = json.loads(delivery_path.read_text())
move = delivery["moves"]["xslash"]
deliverables = [
    "models/astra_xslash_v2_final_on_char2_cloth_wip.blend",
    "renders/astra/rehost/xslash/xslash_cloth.mp4",
    "renders/astra/rehost/xslash/xslash_cloth_contact_sheet.png",
    "renders/astra/rehost/xslash/xslash_cloth_decoded_sheet.png",
    *[f"renders/astra/rehost/xslash/xslash_cloth_decoded_{index:02d}.png"
      for index in range(1, 7)],
    *[f"renders/astra/rehost/xslash/xslash_cloth_floor_before_after_{index:02d}.png"
      for index in range(1, 4)],
    "renders/astra/rehost/xslash/cloth_floor_before.json",
    "renders/astra/rehost/xslash/cloth_floor_after.json",
    "renders/astra/rehost/xslash/xslash_cloth_video_verification.json",
    "renders/astra/rehost/xslash/xslash_cloth_audit_verification.json",
]
move["deliverables"] = deliverables
move["sha256"] = {relative: sha256(root / relative) for relative in deliverables}
move["checks"]["surface_before_after"] = surface
move["checks"]["cloth_floor_fix"] = verification
move["checks"]["derived_rehost_only_fixes"] = {
    "cloth_floor": {
        "method": fix["method"],
        "modified_bones": fix["modified_bones"],
        "noncloth_action_digest_exact": True,
        "rest_rig_digest_exact": True,
    }
}
stream = video["ffprobe"]["streams"][0]
move["checks"]["video"] = {
    "codec": stream["codec_name"], "pixel_format": stream["pix_fmt"],
    "width": stream["width"], "height": stream["height"],
    "frame_rate": stream["r_frame_rate"],
    "decoded_frames": int(stream["nb_read_frames"]),
    "duration_s": float(video["ffprobe"]["format"]["duration"]),
}
move["checks"]["visual_inspection"] = {
    "all_six_consecutive_decoded_mp4_sheets_inspected": True,
    "three_full_resolution_before_after_pairs_inspected": True,
    "new_visible_animation_or_surface_defect": False,
    "inspection_location": "Mac, using only evidence rendered/decoded on black-sky",
}
delivery["execution_host"] = "black-sky"
delivery["render"]["device_note"] = (
    "All Blender, audit, render, ffmpeg, and packaging compute ran on black-sky; "
    "the cloth-fixed X-slash full render was serial.")
delivery_path.write_text(json.dumps(delivery, indent=2) + "\n")
print(json.dumps({
    "report": str(report_path.relative_to(root)),
    "delivery": str(delivery_path.relative_to(root)),
    "manifest": str(manifest_path.relative_to(root)),
    "blend_sha256": verification["fixed_blend_sha256"],
    "mp4_sha256": verification["mp4_sha256"],
}, indent=2))
