# X-slash sword-arm defects — motion track

**FAIL-with-defect-report. Partial audit; fresh geometry and second-angle checks are blocked.**

`models/astra_xslash_v2_final_wip.blend` is **FROZEN/read-only per coordinator ruling**. It was audited through the existing post-fix evidence and its file hash, never edited or saved. These are queued suggestions for the owning track after its freeze is explicitly lifted, not instructions to change the staged hero-render input now.

## X01 — Moderate candidate: excessive lateral wrist loading, F44.75–51.75

Bone: `RightHand` relative to `RightForeArm`. The hand-axis decomposition measures deviation **−46.77° at F47.25**, exceeding the requested ±30° screen by **16.77°**. Integer poses F46/F47/F48 measure −43.11°/−46.76°/−45.19°. The maximum total wrist bend is **70.71° at F48.25**; total bend is not the same as flexion. Flexion proxy remains within −62.58° to +53.22°.

This is a remaining lateral-loading question, not a rediscovery of the corrected 134.87° backward wrist. The previous audit explicitly did not certify deviation. Hand local X is the transverse-axis proxy and Z the palm-normal proxy; the rig has no finger bones to validate those axes. Rotating this axis assignment ±15° about hand Y still gives 33.76°–58.41° absolute deviation at F47.25. This strengthens the candidate but does not replace palm-mesh calibration. The blurred front images cannot confirm an anatomical breach on their own.

Suggested F-curve correction **if mesh-axis calibration confirms the candidate**: reduce the derived deviation extremum at F47.25 from −46.77° to approximately −25°, smoothly over F44–53. Redistribute the saved blade orientation through forearm roll and elbow-pole position; bake the resulting `RightArm`, `RightForeArm`, and `RightHand.rotation_quaternion[0:4]` keys with aligned quaternion signs. Preserve F44/F53 endpoints and grip binding, and recheck elbow ≤150°. The angles above are measured joint targets, not existing Euler-channel values.

Evidence actually inspected: `stills_xslash/047_inherited.png`, `048_inherited.png`, `sheet_xslash_inherited.png`, and `decoded_xslash_strike2/sheet_01.png`. Render fresh no-blur front/side F46–49 before accepting a correction.

## X02 — Minor timing finding under the requested whip criterion, first cut F30–44

`RightArm` and `RightForeArm` world angular-speed peaks occur simultaneously at **F39.00**, **57.77°/frame** and **57.74°/frame**. `RightHand` follows at F39.50, 45.63°/frame. The clavicle already leads at F35.50. Thus the chain starts proximally, but the upper-arm-to-forearm peak has **zero delay**. The first cut remains somewhat bunched at the elbow in the inspected front sequence.

Local peaks are also non-monotonic: RightArm F39.00 → RightForeArm F41.75, while RightHand peaks at F38.75. The second cut has better world ordering: F54.50 → F54.75 → F56.25. This is a residual strict-timing flag, not evidence of an impossible stroke; elbow flexion and compensatory wrist rotation need not share the same speed maximum.

Suggested timing trial for the owning track: redistribute F37–41 quaternion keys so upper-arm world speed peaks near F38.75, forearm near F39.25, and hand near F39.75. Preserve F30/F44 endpoints and the impact window, and re-solve the coupled arm rather than shifting independent quaternion components. Compare the trial against the existing continuous cut before adopting it.

Evidence actually inspected: `clips_xslash_strike1_slowmo.mp4` through both decoded sheets, covering every original F30–44. Existing motion blur limits examination of the hinge plane.

## X03 — Retained balance warning, re-examined rather than declared fixed

The prior F30–39 right-foot-only support assumption reproduces the **−30.76 cm static margin at F39** (−32.76 cm with the separate 2 cm inset). Quarter samples approach **−31.39 cm at F39.75**. A linear-inverted-pendulum capture-point screen gives **−43.40 cm at F39**, then **+18.68 cm at F40** when the left foot enters the support hull. The worst pre-contact capture margin is −73.12 cm at F37; F38 is −64.86 cm. Static margin at F40 is +20.98 cm.

Conclusion: the warning remains. The enlarged support at F40 can catch the proxy; these numbers do not prove a fall or certify dynamic balance. The capture-point model assumes constant COM height and negligible angular momentum, both imperfect during this accelerating slash. Sword-mass sensitivity was not independently repeated in this pass.

No isolated wrist or shoulder key edit will resolve this support geometry. If the owner chooses to reblock: trial earlier left-foot contact at F39, distribute the accompanying pelvis/spine translation over F35–40, and re-solve both arms to maintain grip. Re-evaluate actual sole clearance and the full support transition; do not shift the torso 31 cm in one frame or apply this to the frozen input.

## Known retained acceleration and limits

There are **no ≥10× isolated local-speed spikes** at integer or quarter sampling. Peak local quarter-frame acceleration is RightArm 38.29°/frame² at F36.75, RightForeArm 30.33°/frame² at F38.75, and RightHand 40.18°/frame² at F39.25. These refine the previous report's retained fast-motion warning; they do not reinstate the corrected 176° teleport. Elbow flexion is 14.98°–148.22°, including subframes; no over-150° result. The F57→61 extension is 91.97°→15.26°, softening to 18.65° at F62 and 33.17° at F64, so the elbow is not locked straight for the cut.

Hand-local hilt translation drift is 0.000303 mm and blade-axis drift 0.0000247°, both numerical noise. Full axial grip rotation and upper-arm/torso mesh penetration were **not freshly measured**. Front-image overlap at F38–40/F51–56 is occlusion, not a confirmed penetrating frame range. Close the geometry gap with `astra_armaudit_capture.py`; no collision correction is justified yet.
