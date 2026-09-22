# Lunge thrust sword-arm defects — moveset track

**FAIL-with-defect-report. Candidate motion refinements plus blocked fresh geometry/second-angle verification.** Current blend was never edited. Cached samples were written after the blend, but no cached audit hash ties them conclusively to that exact file. All motion findings here require confirmation on the current blend.

## L01 — Moderate candidate: recovery rotation overwhelms the thrust, F37–44

At F39.50, `RightArm`, `RightForeArm`, and `RightHand` world angular speeds peak simultaneously at **15.50, 15.40, and 17.48°/frame**. The corresponding upper-arm local peak is **16.06°/frame**, almost twice the active thrust's **8.06°/frame at F28.75**. Local hand speed reaches **16.24°/frame at F39.75**. The elbow stays deeply folded: **98.81° at F38**, **102.14° at F40**, **99.997° at F42**. The arm therefore rotates as a compact assembly during the fast direction change rather than visibly releasing successive segments.

The inspected F37–44 sequence shows the shoulder/elbow rising beside the head while the sword drops through a large arc. It is continuous, not a single-frame teleport, but the recovery reads as a conspicuous joint-driven flourish after a comparatively controlled thrust. The intended BACK TO PLAYER ending is relevant; this is a stylistic naturalness candidate, not a human-ROM violation.

Suggested F-curve trial: stretch the F37–44 RightArm/RightForeArm/RightHand quaternion transition to F37–47, reducing the upper-arm local peak toward 11°–12°/frame. Offset forearm response about 0.5 frame and wrist response about 1 frame after the upper arm. Preserve the F64 ending. If that makes the ending late, take time from the later held recovery rather than compressing the initial recoil. Recheck blade clearance before accepting.

Evidence: `stills_lunge_thrust/037_inherited.png`, `040_inherited.png`, `043_inherited.png`, and `decoded_lunge_thrust_strike1/sheet_03.png` (every F37–44).

## L02 — Minor candidate: active thrust begins moving sideways at F35

The manifest labels F25–35 active. At F35, independently differentiated cached blade landmarks give **1.479 m/s** tip speed, **0.938 m/s axial**, **1.144 m/s transverse**, and **50.65°** between tip velocity and blade axis. At F34 the angle is only **5.54°**. Thus the final active frame already enters the lateral recovery. This is not wrist overextension: total wrist bend is only 6.12° at F35. It is a trajectory/timing issue, and its importance depends on whether F35 is intended to remain a straight thrust.

Suggested F-curve trial: keep the RightArm/RightForeArm hand-target trajectory tangent to the blade through F35, moving the first lateral recovery keys from F34.75–35 to F35.75–36. Retain the F28.25 peak axial delivery and start the wider recovery after the active interval. Recompute tip velocity, since simply rotating the sword would change point alignment.

## Requested whip-sequence flag, with thrust-specific disposition

Within F25–35 the local peaks are clavicle F28.50 → upper arm F28.75 → forearm F29.50, but the hand peaks at **F27.50, 3.38°/frame**, before the elbow. World forearm peak F27.25 also precedes upper arm F28.50. This fails a strict proximal-to-distal rotational-peak test. However a thrust should retain a relatively firm wrist; its axial tip speed peaks at **7.22 m/s at F28.25**. Do not add a decorative wrist flick solely to satisfy peak ordering. If a whip-like thrust is required, trial the small hand compensation peak at F30 instead of F27.50 and preserve blade-axis alignment. This timing flag alone is not a hard naturalness defect.

## Checks without a demonstrated defect

Elbow 49.34°–105.51°; wrist total bend 4.88°–26.36°; flexion proxy −24.04° to +13.57°; deviation proxy −24.02° to +8.16°; shoulder elevation 39.54°–78.30°. No ≥10× isolated local-speed spikes. Hand-local hilt drift 0.000374 mm; longitudinal-axis drift 0.0000334°. These support stable gripping and a flexing elbow. Motion-speed variation is substantial, so no constant-angular-velocity swing is alleged.

Upper-arm versus evaluated torso/armor overlap, calibrated anatomical wrist axes, full grip roll, fresh action sampling, and the second render angle remain unverified. Do not apply collision or ROM corrections without those measurements. `astra_armaudit_capture.py` contains the pending measurement/render work and is syntax-checked only.
