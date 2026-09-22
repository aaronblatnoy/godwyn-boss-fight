# Idle Guard sword-arm defect disposition — moveset track

**FAIL-with-defect-report for incomplete required audit coverage. No confirmed sword-arm motion defect in the available samples.** This is not a claim that a failing animation was found. The blend was never edited.

## Findings from the measured cached samples

- Shoulder elevation: 38.69° (F86) to 39.97° (F48.75).
- Shoulder flexion projection: 31.48° (F28.5) to 32.31° (F60.75).
- Shoulder abduction projection: 26.90° (F84.75) to 29.39° (F38.5).
- Elbow flexion: 35.01° (F81.75) to 46.09° (F33.75).
- Total wrist bend: 26.34° (F87.75) to 29.18° (F36.25).
- Wrist flexion proxy: -24.37° (F33.75) to -16.70° (F81.5).
- Wrist deviation proxy: -20.83° (F78.25) to -16.45° (F29.5).
- RightShoulder: integer peak 0.092°/frame ending F10, acceleration 0.006°/frame² centered F34; quarter peak 0.092°/frame ending F9.75, acceleration 0.007°/frame² centered F82.25.
- RightArm: integer peak 0.192°/frame ending F7, acceleration 0.013°/frame² centered F79; quarter peak 0.193°/frame ending F7, acceleration 0.017°/frame² centered F79.75.
- RightForeArm: integer peak 0.367°/frame ending F62, acceleration 0.030°/frame² centered F82; quarter peak 0.369°/frame ending F61.25, acceleration 0.045°/frame² centered F79.75.
- RightHand: integer peak 0.278°/frame ending F7, acceleration 0.021°/frame² centered F82; quarter peak 0.278°/frame ending F6.25, acceleration 0.028°/frame² centered F79.75.
- Isolated speed spikes ≥10× neighboring median: 0. Hilt translation drift: 0.000272 mm; blade longitudinal-axis drift: 0.0000162°.
- Upper-arm/torso mesh penetration ranges: **not measured**, not zero. Full axial grip orientation: not independently certified.

The elbow changes by 11.08° over the cycle, so it is not locked. The chain has nonzero, varying local velocities; the wrist is neither frozen nor the only moving joint. The guarded arm position fits the intended watchful low guard. A stationary-looking sword in a guard is not sufficient evidence of a puppet swing.

The duplicated loop endpoint has at most 0.0000000° sword-arm rotation mismatch. The largest one-sided quarter-frame velocity difference is 0.0829°/s on RightForeArm. Such a finite-step difference includes normal curvature; it is not proof of a derivative discontinuity. No visible pose snap was identified in the inspected beginning/end stills.

## Open audit defect: current-file and geometry certification

Required coverage is incomplete for F1–97: Blender crashed before running the collector. The inherited samples postdate the target's save, but do not carry that target blend's SHA-256. Fresh depsgraph evaluation, palm-axis calibration, upper-arm/torso overlap, full grip roll and two-angle renders are still required. Their absence prevents PASS.

**F-curve disposition:** no quantitative breach justifies changing a key here. Do not add arbitrary sway, retime the loop, or modify the wrist to manufacture a defect. Run the prepared read-only collector and review any actual collision candidate before choosing an F-curve correction.

Evidence actually inspected: `sheet_idle_guard_inherited.png`, with frame order [1, 9, 25, 34, 49, 65, 78, 82, 96]; nine individual crop files are retained in `stills_idle_guard/`. They are inherited single-camera renders, not newly rendered two-angle evidence. There is no strike in this action, so no strike slow-motion clip is required.
