# Walk Stalk sword-arm defect disposition — moveset track

**FAIL-with-defect-report for incomplete required audit coverage. No confirmed sword-arm motion defect in the available samples.** This is not a claim that a failing animation was found. The blend was never edited.

## Findings from the measured cached samples

- Shoulder elevation: 43.54° (F58.75) to 48.30° (F38.5).
- Shoulder flexion projection: 35.99° (F58.75) to 42.15° (F37.5).
- Shoulder abduction projection: 31.32° (F22.5) to 33.72° (F41).
- Elbow flexion: 43.94° (F59) to 56.79° (F36).
- Total wrist bend: 31.20° (F23.25) to 32.99° (F42.25).
- Wrist flexion proxy: -29.58° (F8.5) to -25.25° (F59.25).
- Wrist deviation proxy: -19.15° (F58) to -13.75° (F14.75).
- RightShoulder: integer peak 0.113°/frame ending F48, acceleration 0.010°/frame² centered F29; quarter peak 0.113°/frame ending F47.5, acceleration 0.010°/frame² centered F66.
- RightArm: integer peak 0.415°/frame ending F50, acceleration 0.073°/frame² centered F59; quarter peak 0.416°/frame ending F49.75, acceleration 0.078°/frame² centered F59.75.
- RightForeArm: integer peak 0.908°/frame ending F50, acceleration 0.149°/frame² centered F59; quarter peak 0.911°/frame ending F49.25, acceleration 0.157°/frame² centered F59.75.
- RightHand: integer peak 0.440°/frame ending F70, acceleration 0.071°/frame² centered F59; quarter peak 0.441°/frame ending F69.25, acceleration 0.076°/frame² centered F59.75.
- Isolated speed spikes ≥10× neighboring median: 0. Hilt translation drift: 0.000303 mm; blade longitudinal-axis drift: 0.0000254°.
- Upper-arm/torso mesh penetration ranges: **not measured**, not zero. Full axial grip orientation: not independently certified.

The elbow changes by 12.85° over the cycle, so it is not locked. The chain has nonzero, varying local velocities; the wrist is neither frozen nor the only moving joint. The guarded arm position fits the intended watchful low guard. A stationary-looking sword in a guard is not sufficient evidence of a puppet swing.

The duplicated loop endpoint has at most 0.0000661° sword-arm rotation mismatch. The largest one-sided quarter-frame velocity difference is 0.4445°/s on RightForeArm. Such a finite-step difference includes normal curvature; it is not proof of a derivative discontinuity. No visible pose snap was identified in the inspected beginning/end stills.

## Open audit defect: current-file and geometry certification

Required coverage is incomplete for F1–73: Blender crashed before running the collector. The inherited samples postdate the target's save, but do not carry that target blend's SHA-256. Fresh depsgraph evaluation, palm-axis calibration, upper-arm/torso overlap, full grip roll and two-angle renders are still required. Their absence prevents PASS.

**F-curve disposition:** no quantitative breach justifies changing a key here. Do not add arbitrary sway, retime the loop, or modify the wrist to manufacture a defect. Run the prepared read-only collector and review any actual collision candidate before choosing an F-curve correction.

Evidence actually inspected: `sheet_walk_stalk_inherited.png`, with frame order [1, 9, 23, 36, 42, 49, 59, 68, 72]; nine individual crop files are retained in `stills_walk_stalk/`. They are inherited single-camera renders, not newly rendered two-angle evidence. There is no strike in this action, so no strike slow-motion clip is required.
