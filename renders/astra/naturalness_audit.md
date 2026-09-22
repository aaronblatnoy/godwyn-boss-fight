# Godwyn X-slash naturalness audit — 90-frame final revision

Audited the approved final scene, corrected its existing animation, and re-rendered F1–90. This is **an improvement with documented residual issues**, not a claim of a physically simulated or collision-free character. The major arm flips, backward wrist bend, elbow over-fold and severe hem sinking were real. The anticipation already had acceleration shaping; the low F46–57 poses already had good support margins.

## Deliverables and scope

- Fixed scene: `models/astra_xslash_v2_final_wip.blend`; original scene retained at `models/astra_xslash_v2_final_prefix.blend`.
- Shippable clip: `renders/astra/godwyn_xslash_v2_final.mp4`; original retained at `renders/astra/godwyn_xslash_v2_final_prefix.mp4`.
- [Before metrics](naturalness_metrics_before.json), [after metrics](naturalness_metrics_after.json), [invariant verification](naturalness_verification.json).
- [Before evaluation sheet](v2_final_on_char/naturalness_before_evaluation_sheet.png), [after evaluation sheet](v2_final_on_char/naturalness_after_evaluation_sheet.png). Frame order: 1, 13, 27, 31, 34, 36, 38, 39, 40, 43, 46, 53, 54, 57, 61, 79, 80, 84, 86, 90.

All authoring changes are existing pose-bone rotation/location keys, plus location keys on the existing blur ribbons to follow the small corrected first-cut grip displacement. Mesh vertices, topology, skin weights, bone rest hierarchy, used material shaders, lighting, camera, world, EEVEE settings, exposure and image settings compare unchanged. Blender discarded two unused material IDs during normal save/reload (`Astra charcoal`, `GodwynGameMat`); no used shader or material assignment was authored. No cinematography paths, character sources, SPEC.txt or CLAUDE.md were written. No network, installs or git commands were used.

**Framing constraint:** the saved final blend uses the front orthographic camera (scale 5.4). The prior MP4 used a temporary three-quarter override. The user reiterated no camera changes, so the new clip and all before/after evaluation images use the unchanged saved front camera. This accounts for the framing difference from the backed-up MP4.

## Measurement method and limits

- Sampled **121 bones, 847 F-curves and 302,379 existing keys** at all 90 integer frames and all 357 quarter frames. Maximum source key spacing is 0.25 frame; interpolation is Bézier with clamped automatic handles. Quaternion components, scalar derivatives and world/parent-space transforms are retained in the raw JSON.
- Rotation velocity uses the shortest quaternion logarithm of `q_next * inverse(q_previous)`, expressed in degrees/frame. This avoids mistaking antipodal quaternion signs for flips. At 30 fps, multiply speed by 30 and acceleration by 900 for per-second units. We also retain scalar component sign reversals; these alone are not anatomical defects.
- Automated candidate thresholds: direction dot below −0.5 with both adjacent angular steps above 0.5°; speed above both 4°/frame and 2.8× its local seven-sample median; angular acceleration above 12°/frame². These are audit flags, not hard human limits. All flagged bones/frames have a disposition below.
- Major-bone head velocities/accelerations and quarter-frame angular peaks cover every non-cloth bone. Imported display tails are approximately 100× too long, so limb lengths and COM use joint heads; wrist longitudinal direction uses the normalized hand orientation.
- Elbow flexion is 0° at straight, not the interior elbow angle. Wrist bend is the forearm/hand-long-axis angle; the rest wrist itself is angled. A broad 80° warning and 150° elbow-flexion warning are screening thresholds, not a calibrated anatomical constraint rig. Separate radial/ulnar deviation and forearm pronation cannot be fully certified from these imported axes.
- COM proxy: torso 49.7%, head 8.1%; each thigh 10%, shank 4.65%, foot 1.45%, upper arm 2.8%, forearm 1.6%, hand 0.6%. Segment centers use interpolated joint heads. Support hull uses a 20 cm boot width, 12 cm heel extension and 9 cm beyond the toe joint; a 2 cm inset is the conservative margin. Left support is F1–29 and F40–90, right support F1–90. Actual sword landmarks supply 2%, 4%, 6% body-mass sensitivity checks.
- Foot/cloth surface tests evaluate the real skinned mesh at every integer frame against the actual stage plane, Z = −0.015 m. Sole selection uses low vertices predominantly weighted to foot/toe bones. Cloth-leg capsule proximity is only a candidate test: shared skinning regions and covered legs prevent treating every close vertex as an intersection.
- Timing and lean measurements are kinematic evidence. They do not measure torque, ground reaction forces, inertial tensors or fabric physics.

## Defects corrected

### 01 — Major: sword-arm flips and teleports, F37–40 and F53–55

Before: RightForeArm rotated **176.49° in F38→39**, with 205.06°/frame² peak acceleration. RightArm jumped 148.96° at F54. The right elbow moved **84.04 cm in one frame**, F53→54; subframe upper-arm speed peaked at 320.36°/frame. Visuals show the forearm/gauntlet whipping around the arm rather than following one hinge plane.

Fix: replaced singular independent pole/aim orientations with continuous elbow-circle selection, smoothed pole travel and a consistent anatomical bend-plane frame; baked onto the existing quarter-frame channels. After: right forearm peak 24.09°/frame, acceleration 19.12°/frame²; elbow head step 16.42 cm; upper-arm subframe peak 49.97°/frame. The large one-frame flips are gone. Fast continuous slash acceleration remains and is disclosed below.
Evidence, left-to-right F36, F38, F39, F53, F54: [before](v2_final_on_char/naturalness_01_arm_pops_before.png), [after](v2_final_on_char/naturalness_01_arm_pops_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 02 — Major: backward sword wrist, F1–16, F39 and F74–90

Before: forearm/hand bend peaked at **134.87° at F86**, with 127.61° already at F1. This is not merely forearm roll. Fix: the continuous elbow solve favors a supported palm and penalizes excessive hand bend while retaining the world blade orientation. After: maximum 70.54° at F48; no frame exceeds the broad 80° screening threshold. Some 65–71° loaded poses remain stylized, not an anatomically certified grip.
Evidence, left-to-right F1, F13, F80, F90: [before](v2_final_on_char/naturalness_02_sword_wrist_before.png), [after](v2_final_on_char/naturalness_02_sword_wrist_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 03 — Major: sword elbow over-fold, F38–40, worst F39

Before: **166.53°** flexion at F39 folds the armored forearm almost back into the upper arm. Fix: smoothly extend the grip forward by up to 18 cm, F36.5–42, and re-solve the arm. After: maximum **147.92°** at F39. Limb lengths remain fixed; no bone rest edit or scaling was used. Existing first-cut ribbon objects receive the matching shutter-midpoint translation keys. Their baked shape is retained; a small subframe ribbon/path mismatch is acknowledged below.
Evidence, left-to-right F38, F39, F40: [before](v2_final_on_char/naturalness_03_elbow_fold_before.png), [after](v2_final_on_char/naturalness_03_elbow_fold_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 04 — Moderate: off-arm hinge kink, F40–44 and F52

Before: LeftForeArm peak 29.91°/frame; acceleration 17.52°/frame² at F43; reversal F43 flips from 3.06° to 14.63° per frame. Fix: smooth the elbow pole and use a consistent hinge plane while preserving the off-hand position track. After: peak 14.65°/frame and acceleration 11.31°/frame². Direction reversals at recoil extrema still occur, but the sharp twist is reduced. The specifically requested F36/F46 checks do **not** show elbow hyperextension; source flexion was 115.08°/72.63°.
Evidence, left-to-right F36, F40, F43, F46: [before](v2_final_on_char/naturalness_04_off_arm_kink_before.png), [after](v2_final_on_char/naturalness_04_off_arm_kink_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 05 — Minor: shoulders in identical timing, F1–90, most visible F34–40/F51–57

Before: left/right clavicle speed correlation at zero lag 1.000000, with both local peaks at F38.25 and F55.25. Fix: delay the off shoulder by two frames. After: zero-lag correlation 0.642579, best match at +2 frames; off-shoulder peaks F40.25/F57.25. The original arm/hand target paths were already asymmetric, so no wholesale mirrored-limb problem is claimed.
Evidence, left-to-right F34, F36, F38, F40: [before](v2_final_on_char/naturalness_05_shoulder_timing_before.png), [after](v2_final_on_char/naturalness_05_shoulder_timing_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 06 — Minor: off-hand wrist rigidly locked, F1–90

Before: all left-hand local rotation keys were constant; rest-relative wrist swing was zero throughout. Fix: a small delayed wrist response, −2° to +2.5°, following the arm phases. After: maximum 2.50° rest-relative swing while anatomical forearm/hand bend remains approximately 18.82–19.35°. This removes the absolute wrist lock without adding a conspicuous gesture.
Evidence, left-to-right F27, F43, F57, F90: [before](v2_final_on_char/naturalness_06_off_hand_rigidity_before.png), [after](v2_final_on_char/naturalness_06_off_hand_rigidity_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 07 — Moderate: missing wind-up sword-mass counter-lean, F13–30

Before: torso lean toward the horizontal blade direction was +0.81° at F13, +0.33° at F20 and +0.21° at F27: little opposing lean. Fix: distribute a gentle 3.5° world counter-lean across the three spine channels during anticipation, fading out by F37; hand targets stay in place. After: −0.21°, −1.40°, −1.66° respectively. Negative means away from the blade. Existing forward pull during cuts remains: +7.62° at F39 and +8.24° at F57. This adds visible weight response while retaining the authored attack timing.
Evidence, left-to-right F13, F27, F31: [before](v2_final_on_char/naturalness_07_counterlean_before.png), [after](v2_final_on_char/naturalness_07_counterlean_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 08 — Minor: repeated settling bob, F80–90, reversals around F82/F86

Before: the sword hand traversed 14.73 cm through multiple small stop/restart lobes. Fix: replace the late position lobes with one tangent-continuous arrival and a single return to the final guard. After: 11.21 cm, preserving the arrival velocity and F90 endpoint. This is a damped settling change, **not** a fix for linear interpolation: the original curves were already accelerated.
Evidence, left-to-right F80, F84, F86, F90: [before](v2_final_on_char/naturalness_08_settle_bob_before.png), [after](v2_final_on_char/naturalness_08_settle_bob_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 09 — Minor: planted boot hover/penetration, F1–29/F40–90 left; F1–90 right

Before evaluated sole clearance: left **-6.99 to 14.93 mm**, right **-2.58 to 15.38 mm**. Left sinking is worst at F58; floating is visible numerically around F40–49 and F76–90. Constant ankle height alone had hidden this skin-deformation error. Fix: offset the foot target by measured sole clearance and re-solve the leg with fixed segment lengths and foot orientation. After: left 1.01–3.62 mm; right 1.39–2.86 mm. Every sampled planted sole is above the plane and within the 5 mm visual contact tolerance.
Evidence, left-to-right F27, F46, F57, F90: [before](v2_final_on_char/naturalness_09_foot_contact_before.png), [after](v2_final_on_char/naturalness_09_foot_contact_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 10 — Minor: cloth co-rotation too immediate during the cuts, F31–60

The source was **not** devoid of lag: hem extrema already followed the hips, and no convincing hem-leading event was found. However, the strongest robe world-yaw velocity correlation was at zero delay, with the hem correlation about 0.98, so the fast motion was dominated by inherited pelvis rotation. The delayed local pulses largely cancelled in the accumulated chain. Fix: cumulative delayed, critically damped yaw compensation, small left/right panel offsets, and a smooth ending envelope; replace the explicit recovery sine response. After: robe velocity best delay is +1 frame, cape +2 (the search includes −10 to +20, so leading is not silently excluded). Central robe hem extrema are F49/F68 versus hips F44/F62, and the cape hem F49/F69. The source hem extrema were F48/F69 and F49/F67 respectively: improvement is in the fast response and damping, not a claim that all original follow-through was wrong.
Evidence, left-to-right F38, F43, F61, F90: [before](v2_final_on_char/naturalness_10_cloth_lag_before.png), [after](v2_final_on_char/naturalness_10_cloth_lag_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

### 11 — Major, now minor residual: cloth buried in the stage, especially F38–43/F53–61

Before: lowest sampled cloth point was **22.45 cm below the floor at F57**, caused by the lowered pelvis pulling the hanging hem into the stage. Fix: add measured, progressively distributed upward location corrections to existing distal cloth links; waist/spine roots and the first three links remain attached. Three measured correction passes let the lower fabric gather rather than disappear. After: deepest residual **1.20 cm at F56**, a 94.7% reduction. The rendered hem now pools visibly at the ground through the low poses.

Residual penetration above 3 mm occurs at F38–44, 48–72. **Not fully fixed:** the last small penetration comes from blended panel vertices; more shortening visibly compresses the hem, and correcting the binding/geometry is outside this animation-only pass. This is an explicit residual, not a collision-free claim.
Evidence, left-to-right F39, F46, F57, F90: [before](v2_final_on_char/naturalness_11_hem_floor_before.png), [after](v2_final_on_char/naturalness_11_hem_floor_after.png). Original-resolution matching frames are `v2_final_on_char/naturalness_before/NNN.png` and `v2_final_on_char/naturalness_after/NNN.png`.

## Defects and risks retained, with reasons

- **Moderate groundedness warning, F30–39:** static COM is outside the right-foot-only support hull. Worst source deficit 30.31 cm at F39; after 30.76 cm. The counter-lean/arm changes marginally worsen this proxy by about 0.45 cm; this is not hidden. The 2–6% sword-mass sensitivity does not eliminate the warning. **Not fixed:** this is a moving step caught by left-foot contact at F40, so static COM alone cannot establish an impossible fall. A guaranteed single-foot balance fix requires reblocking the approved step/whole-body translation, with significant knock-on effects on both cuts. No false claim of dynamically stable balance is made.

- **Minor residual knee settling reversals, F46/F79:** original right knee reversed at F46 and both knees at F79. Sole correction adds small corresponding thigh/knee responses. **Not fixed further:** these coincide with the intentional pelvis rise/rebound, have no positional teleport, and are small compared with the corrected arm defects. Flattening them would alter the approved weight-settle timing.

- **Moderate stylistic acceleration, F36–40/F53–55/F60–62:** some arm acceleration flags remain after the flips are removed. **Retained:** the blade still executes the approved fast cuts; high velocity alone is not a discontinuity. Every remaining flagged frame is listed below. A force/mass simulation would be needed to certify human-achievable torque.

- **Minor residual endpoint motion, F89–90:** local cloth channels approach rest, but inherited spine motion keeps the cape moving slightly at the clip end (central cape tip approximately 0.30°/frame; central robe tip 0.05°/frame). **Retained:** small continuous follow-through is preferable to forcibly locking the parent spine at the final frame. This clip is not asserted to be a seamless loop.

- **Minor approximation, blur ribbons F38–41:** the small first-cut grip extension is carried by existing ribbon translation keys at the shutter midpoint. **Not rebuilt:** an exact new curved ribbon would require vertex/geometry edits prohibited by this pass. The rendered result must be judged with this known approximation; the blade itself follows the corrected arm.

- **Unconfirmed cloth/leg clipping candidates, strongest around F57–58 and F69–73:** source cloth-weighted vertices approach leg capsule axes to sub-millimeter distances. These samples can include covered/shared skinning regions and do not prove an actual exposed-surface intersection. **No additional edit:** changing cloth to avoid every capsule would create hovering fabric and could move the front tabard away from the belt. The audit does not certify hidden cloth/leg collision clearance. The visible 640 px frames are the confirmation limit.

## Checks that were already good, and what the numbers do not imply

**Anticipation/settle interpolation:** there are no sparse linear limb curves to repair. F13–27 speed CVs were hips 0.443, sword hand 0.356, off-hand 0.277; the sword-hand step falls from 46.26 mm to 4.76 mm. F80–90 source sword-hand CV was 0.522. These are changing-speed paths, not constant-speed drifting. The only settle defect addressed is the repeated bob.

**Low-pose balance:** F46–57 source minimum static support margin is **17.72 cm**, after **18.34 cm**, comfortably inside the 2 cm inset. No unsupported-low-pose defect was invented.

**Momentum cascade:** the source already leads from hips through the three local spine channels: first cut peaks F34.25 → 35.25 → 36.25 → 37.25 → right clavicle 38.25; second cut 51.25 → 52.25 → 53.25 → 54.25 → 55.25. These local timings remain. In world space after correction, first cut hips 34.25 → upper spine 35.25 → right shoulder 35.5 → upper arm 39.0 → wrist 39.5; second cut 51.25 → 52.25 → 52.5 → upper arm 54.5 → forearm 54.75 → wrist 56.25. Thus the visible motion originates lower in the chain, rather than the torso and sword starting together. Local relative-joint speed peaks are not all monotonic—wrist compensation and elbow flexion can peak at different times—so an exact torque cascade is not claimed from F-curves. The corrected planted right sole provides a visible ground contact, with the single-support COM caveat above.

**Elbow/knee extension:** after correction, right elbow flexion remains 15.26–147.92°, left 37.04–137.28°. Neither passes through straight into a measured backward knee/elbow bend. A unsigned segment-angle test alone cannot prove the anatomical hinge sign; consistent bend-plane construction and visuals provide the additional check.

**Sword/cloth proximity:** source closest sampled cloth vertex to the grip–tip centerline was 30.31 cm; after 30.37 cm. No sword-through-hem event was confirmed. This is a vertex/centerline proximity test, not an exact triangle collision solver.

**Tabard/surcoat observation:** `phys_robe_front_*`, `phys_robe_side_*` and `phys_robe_back_*` roots are parented to Hips, consistent with belt anchoring. `phys_cape_*` roots are parented to Spine and represent a separate upper-body trailing system. The rig therefore supports more than one front panel; it does not imply that the blue front panel is shoulder-hung. The visible silhouette includes full side/back drapes as well as the front tabard. Per the scope restriction, no geometry, naming or hierarchy was restructured to reinterpret SPEC.txt.

## Full automated candidate disposition

The thresholds emitted 53 source angular events and 35 after events. Each bone below includes every flagged integer frame. Scalar component extrema (109 before / 103 after) are retained individually in the metrics JSON; they are not independently called defects when the quaternion motion remains continuous.

- **LeftArm:** source F43; after F43. Moderate source kink reduced as 04; remaining extrema are recoil/flexion changes, retained.
- **LeftForeArm:** source F31, 40–44, 52; after F43, 52, 58. Moderate source kink reduced as 04; remaining extrema are recoil/flexion changes, retained.
- **LeftLeg:** source F79; after F46, 79. Minor pelvis-driven settle/recoil response; retained to preserve weight timing and foot contact.
- **LeftUpLeg:** source Fnone; after F79. Minor pelvis-driven settle/recoil response; retained to preserve weight timing and foot contact.
- **RightArm:** source F38–40, 53–55; after F36–39, 53–55, 62. Major source defects corrected as 01–03; remaining flags are cut acceleration and continuous flexion/release extrema, retained for approved timing.
- **RightForeArm:** source F33–35, 37–40, 53–55, 60–61, 86; after F39, 45, 50–51, 53–55, 60–61. Major source defects corrected as 01–03; remaining flags are cut acceleration and continuous flexion/release extrema, retained for approved timing.
- **RightHand:** source F37–41, 53–56, 58, 61; after F37–40, 55, 62. Major source defects corrected as 01–03; remaining flags are cut acceleration and continuous flexion/release extrema, retained for approved timing.
- **RightLeg:** source F46, 79; after F46, 79. Minor pelvis-driven settle/recoil response; retained to preserve weight timing and foot contact.

All major-bone position and quarter-frame angular maxima are in `major_translation` in both metric files; all 121 bone angular maxima are in `peaks`. The right elbow was the unequivocal position discontinuity (84 cm/frame). Its correction does not make the hand slow: the largest remaining hand step occurs within the intentional fast cut, not an unkeyed teleport.

## Reproduction and review evidence

Use Blender 5.2.1 at `/opt/homebrew/bin/blender`, `--background --gpu-backend metal --python-exit-code 1`. The reproducible animation edit is `scripts/astra_xslash_naturalness_fix.py` reading the immutable prefix and the original sampled data; follow with `scripts/astra_xslash_naturalness_ground_cloth.py` three times. The surface/probe/analyze scripts produce the before/after JSON. `scripts/astra_xslash_naturalness_render.py -- after` renders the saved scene; `scripts/astra_xslash_naturalness_package.py` makes evidence sheets and overwrites the required MP4.

Evidence includes all 90 newly rendered PNGs, 20 matching before/after evaluation poses, 11 pairs of defect-specific sheets, and six consecutive sheets decoded from the actual final MP4. Within each defect sheet, frame order is printed in that defect’s entry. The decode is H.264/yuv420p, 640×640, 30 fps, exactly 90 frames / 3.0 s, and completes without errors.

Final visual review is complete: all six original decoded sheets and all six corrected MP4 decoded sheets (every frame F1–90), both matching 20-pose evaluation sheets, and enlarged critical poses were inspected. The corrected arm sweeps are continuous, the guard wrist is supported, and the low-pose hem remains visible instead of disappearing into the floor. No clear exposed leg breakthrough was seen from this front view; hidden collision clearance remains unverified. Limb-length validation at all 357 quarter frames passed within 0.1 mm. The material/camera/lighting/render/rest/mesh invariant checks and full MP4 decode passed. Detailed status is in `naturalness_verification.json`.

## Sword-arm follow-up — 2026-09-06

This section supersedes the earlier wrist/cascade conclusions for the current final. Trigger: the independently reported X-slash wrist-deviation and upper-arm/forearm timing findings in [the read-only arm audit](armaudit/defects_xslash.md). Both were independently reproduced from the actual approved scene using our existing probe/analyzer. No incomplete geometry or penetration claim from that audit is accepted as verified. Backup: `models/astra_xslash_v2_final_prefix2.blend` (SHA-256 `a029446fa54910887382f52f2479d9d3e95cf765f32ff1de6cb5f47f289e653c`); the older `_prefix.blend` remains untouched.

- **X01 — major, F45–51, maximum F47.25: excessive sword-wrist lateral deviation. Fixed.** The hand-frame lateral screen reproduced **−46.7653° at F47.25**. F46/F47/F48 were **−43.1115°/−46.7576°/−45.1908°**; all three and F47.25 are now **−25.0000°**. The full-clip quarter-frame range is **−29.3687° (F45) to +14.6236° (F77)**, inside ±30°. F44 **−22.5743°** and F53 **−19.8742°** retain their exact original pose values. The elbow travels around its fixed-length reach circle (maximum pole rotation **31.27°**) with smooth F44–46/F51–53 ramps; forearm and hand rotations compensate to retain the weapon binding. Total wrist-bend maximum improves **70.7106° → 59.7225°**. Evidence: [before F44–53](v2_final_on_char/armfix_wrist_before.png), [after F44–53](v2_final_on_char/armfix_wrist_after.png), [paired F46/F47/F48](v2_final_on_char/armfix_wrist_comparison.png), individual [before F47](v2_final_on_char/armfix_before/047.png) / [after F47](v2_final_on_char/armfix_after/047.png). The two ten-pose wrist sheets both use F44,45,46,47,48,49,50,51,52,53 in row order.

- **X02 — moderate, first-cut F39: simultaneous upper-arm/forearm speed peaks. Fixed.** RightArm remains **57.7710°/frame at F39.00**; RightForeArm changes **57.7418°/frame at F39.00 → 54.8305°/frame at F39.50**. The measured delay is **0 → 0.50 frame**. The clavicle still leads at F35.50. A bounded F34–44 forearm axial-roll retiming (maximum **23.11°** offset) produces the delay while a compensating hand rotation preserves the sword. RightHand world peak remains **45.6251°/frame at F39.50**. At the finer 1/64-frame sampling, the actual upper/fore peaks are F38.875/F39.28125: a **0.40625-frame** lead, showing the quarter-frame 0.50 value is a sampled estimate. Blade peak timing remains F39.484375; its measured finer-grid peak changes by only **0.00954°/frame**. Evidence: [before F36–41](v2_final_on_char/armfix_cascade_before.png), [after F36–41](v2_final_on_char/armfix_cascade_after.png), [paired F38/F39/F40](v2_final_on_char/armfix_cascade_comparison.png).

**Regression checks and retained findings.** All 90 integer frames and 357 quarter-frame poses were rechecked in [the gate-of-record metrics](naturalness_metrics_armfix.json), against [the freshly reproduced baseline](naturalness_metrics_armfix_before.json). Only RightArm/RightForeArm/RightHand quaternion curves changed; 5,264 extra keys give 1/32-frame sampling within the edit windows. All other animation channels and the mesh, weights, rest rig, materials, lights, camera, and EEVEE settings compare unchanged. Right-elbow quarter-frame maximum stays **148.2167°**, below 150°; finer sampling reaches **148.2183°**. Actual planted sole clearances remain exactly **1.009–3.621 mm left / 1.386–2.858 mm right**, with no sampled penetration. Every cloth lag metric and cloth-floor minimum is exactly unchanged.

- **Minor retained numerical balance change, F45–52:** the low-pose body-COM margin minimum is **183.3766 → 182.8766 mm at F47** (−0.5000 mm); the largest individual decrease is **0.8552 mm at F51**, whose remaining margin is 221.6962 mm. This is explicitly a small numerical decrease, not an exact balance improvement. It is retained because it is below a 1 mm comparison tolerance for the approximate segment-mass/support model and remains far inside the existing 20 mm inset; changing unrelated body keys to cancel it would overfit the proxy. The prior single-support warning remains **−307.6440 mm at F39**, unchanged, with no new outside-support frames.
- **Minor retained relative-rotation screening flags:** new >12°/frame² flags occur on RightArm F52 (**12.30**), RightForeArm F45/F46 (**14.22/19.56**), and RightHand F45/F53 (**12.74/12.14**); RightHand has a local counter-rotation reversal at F40 (**12.08 → 4.77°/frame**, direction dot **−0.974**). Forearm maximum local acceleration rises **19.12 → 26.80°/frame² at F39** as its timing separates from the upper arm. These are continuous elbow-pole/compensating-roll transitions, retained after subframe and visual review to preserve the weapon trajectory; they are not described as a perfectly clean set of curves. Upper-arm/hand maximum local angular acceleration and all three maximum integer head steps remain unchanged. The elbow-head acceleration maximum rises **85.85 → 98.59 mm/frame²**, moving from F36 to F45; this modest increase is another retained consequence of fitting the pole change between the locked endpoints. See the complete event arrays in the metrics.

World binding verification: maximum quarter-frame hand drift **0.000521 mm / 0.000028°**; actual integer sword tip/grip differences **0.000805/0.000563 mm**. The independent 1/64-frame check across F33–54 limits between-key hand drift to **0.0481 mm / 0.00287°**. These finite-precision tolerances are recorded, rather than claiming mathematically exact motion between every key. See [subframe results](naturalness_armfix_subframes.json) and [invariant/regression verification](naturalness_armfix_verification.json). Hidden armor/cloth triangle intersections remain unverified; the saved front-view evidence shows no new exposed breakthrough.

All 90 frames were re-rendered in **BLENDER_EEVEE**, using the existing saved scene settings, and encoded in place as [the final MP4](godwyn_xslash_v2_final.mp4): **640×640, 30 fps, 90 frames, 3.0 s, H.264/yuv420p**, full decode error-free. Focused poses and paired sheets were inspected, followed by all six consecutive sheets decoded from the actual new MP4 (`v2_final_on_char/armfix_decoded_01.png` through `06.png`, F1–90). [Video verification](v2_final_on_char/armfix_video_verification.json) records hashes and frame order. Final scene SHA-256: `0c6746a55fb56b2bb8ca1adecc4a8891f5790e18dd773a28d8b3b02fef7b7425`; MP4 SHA-256: `369f46d425c2715c84d8b043b2f5708a0c4993a3f07f7beffe33234661ab5629`.

Reproduction: `scripts/astra_xslash_armfix_apply.py` reads the immutable prefix2 and writes a candidate; the existing probe/surface/analyze scripts, then `astra_xslash_armfix_verify.py` and `astra_xslash_armfix_subframes.py`, supply numerical checks. The verified candidate was copied byte-for-byte to `models/astra_xslash_v2_final_wip.blend`. `astra_xslash_naturalness_render.py -- after` and `astra_xslash_armfix_package.py` render/package the deliverable. No cinematography, character, move-track, or arm-audit file was written.

