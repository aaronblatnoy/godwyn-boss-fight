# Sword-arm naturalness audit — partial, with explicit blockers

**The requested fresh Blender audit is not complete.** Blender 5.2.1 LTS (`9e2066aef7ef`) at `/opt/homebrew/bin/blender` crashes with exit 139 during Metal capability detection, before Python or scene loading. Consequently this report contains independent reanalysis of existing evaluated samples and actual visual inspection of extracted existing footage. It does **not** claim fresh depsgraph evaluation, new EEVEE stills, a second camera angle, or measured mesh penetration.

All four requested targets existed at the first file listing; none was skipped and no model stub was created. All four model hashes remain unchanged. The pinned Codex session ID is **01a074ee-75d1-74e2-ac80-8378dbd1609c**. No resume command was used.

`models/astra_xslash_v2_final_wip.blend` was found **FROZEN/read-only per coordinator ruling** and was audited but not edited, regardless of findings. Defects are filed in `defects_xslash.md` for the motion track. The three moveset blends were also strictly read-only.

## Evidence and measurement validity

The entire `renders/astra/naturalness_audit.md` was read first. This pass starts from the post-fix state; the corrected 176° teleport, 134.87° backward wrist, elbow over-fold, and missing counter-lean are not presented as new defects.

The X-slash file hash matches the prior verification's fixed-blend hash: `a029446fa54910887382f52f2479d9d3e95cf765f32ff1de6cb5f47f289e653c`. Its existing MP4 also matches the prior verified video hash. This supports use of the existing post-fix evidence, although this pass did not regenerate it. Moveset sample and video timestamps postdate their target saves, but their manifests hash the source character rather than the audited move blend. Current-moveset attribution therefore remains provisional.

The existing rig samples confirm the exact chain `RightShoulder → RightArm → RightForeArm → RightHand`; X-slash rest metadata confirms that hierarchy. There are no finger bones in the 121-bone rig. Fresh armature inspection was attempted but never reached Python. Joint angles use bone heads, not the imported display tails, which are approximately 100× too long.

Reanalyzed **1,284 quarter-frame samples**: X-slash F1–90 (357); idle F1–97 (385, duplicate loop endpoint after displayed F96); lunge F1–64 (253); walk F1–73 (289, duplicate loop endpoint after displayed F72). These are the complete cached ranges, not freshly queried action ranges. All four `data_<name>.json` files retain per-sample arm local/world quaternions, joint angles, and complete integer/quarter angular-velocity and acceleration arrays. Each explicitly labels its inherited-sample provenance.

Rotation differences use normalized shortest quaternion logs and ignore antipodal signs. Speed intervals are labeled by their ending frame; acceleration differences are centered at the intervening sample. Units are °/frame and °/frame²; at 30 fps multiply by 30 and 900 for °/s and °/s². A spike requires speed >4°/frame and ≥10× the median of up to three neighbors on each side, excluding itself. No such event was found. Large acceleration is reported separately and is not automatically called a teleport.

Elbow flexion is zero at straight and screened against 0–150°. The unsigned angle cannot alone certify the anatomical hyperextension sign. Shoulder elevation and torso-relative sagittal/frontal projections are screened against a broad 180° elevation / 60° extension envelope; signed negative abduction can represent crossing the chest, not necessarily impossible ROM. Axial humeral limits require calibration not present here.

Wrist components are **axis proxies**: express elbow→wrist direction in the hand's normalized world basis; flexion = −atan2(z,y), deviation = atan2(x,sqrt(y²+z²)). This separates lateral bend from palm-plane bend while holding axes to the hand. Hand local X/Z are not mesh-calibrated palm axes. The ±70°/±30° screens identify candidates, not certified clinical ROM. Total wrist bend is also retained independently. Grip drift is measured in a unit-scale hand frame from existing hilt/tip landmarks; two landmarks do not establish axial roll.

## Verdicts

The requested binary labels below refer to **audit acceptance**. A missing required check fails acceptance; it does not prove bad animation. No full PASS can be issued while geometry and required camera evidence are missing.

### xslash — FAIL-with-defect-report

Remaining wrist-deviation candidate and simultaneous first-cut arm peaks; geometry/render coverage incomplete. See [defects_xslash.md](defects_xslash.md).

- Shoulder elevation: 10.08° (F43.25) to 75.24° (F27).
- Shoulder flexion projection: -19.30° (F38.25) to 74.59° (F26.75).
- Shoulder abduction projection: -61.16° (F52.25) to 58.39° (F35.75).
- Elbow flexion: 14.98° (F61.25) to 148.22° (F38.75).
- Total wrist bend: 5.92° (F66) to 70.71° (F48.25).
- Wrist flexion proxy: -62.58° (F48.5) to 53.22° (F1).
- Wrist deviation proxy: -46.77° (F47.25) to 14.62° (F77).
- RightShoulder: integer peak 2.704°/frame ending F39, acceleration 1.172°/frame² centered F36; quarter peak 2.769°/frame ending F38.25, acceleration 1.579°/frame² centered F35.25.
- RightArm: integer peak 44.126°/frame ending F39, acceleration 31.142°/frame² centered F37; quarter peak 49.967°/frame ending F39, acceleration 38.294°/frame² centered F36.75.
- RightForeArm: integer peak 24.094°/frame ending F59, acceleration 19.117°/frame² centered F39; quarter peak 26.325°/frame ending F59.25, acceleration 30.328°/frame² centered F38.75.
- RightHand: integer peak 21.896°/frame ending F54, acceleration 25.775°/frame² centered F55; quarter peak 25.885°/frame ending F54, acceleration 40.180°/frame² centered F39.25.
- Isolated speed spikes ≥10× neighboring median: 0. Hilt translation drift: 0.000303 mm; blade longitudinal-axis drift: 0.0000247°.
- Upper-arm/torso mesh penetration ranges: **not measured**, not zero. Full axial grip orientation: not independently certified.

### idle_guard — FAIL-with-defect-report

No demonstrated arm-motion breach; required current-file, geometry and camera checks incomplete. See [defects_idle_guard.md](defects_idle_guard.md).

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

### lunge_thrust — FAIL-with-defect-report

Fast compact recovery and lateral motion at the last active thrust frame are candidate refinements; current-file and geometry coverage incomplete. See [defects_lunge_thrust.md](defects_lunge_thrust.md).

- Shoulder elevation: 39.54° (F27.5) to 78.30° (F43).
- Shoulder flexion projection: -19.41° (F39.25) to 63.21° (F44).
- Shoulder abduction projection: 39.39° (F28) to 77.53° (F42.75).
- Elbow flexion: 49.34° (F1) to 105.51° (F25.5).
- Total wrist bend: 4.88° (F32) to 26.36° (F64).
- Wrist flexion proxy: -24.04° (F16.5) to 13.57° (F55.25).
- Wrist deviation proxy: -24.02° (F64) to 8.16° (F27.25).
- RightShoulder: integer peak 1.675°/frame ending F29, acceleration 0.279°/frame² centered F23; quarter peak 1.677°/frame ending F28.5, acceleration 0.282°/frame² centered F22.75.
- RightArm: integer peak 15.875°/frame ending F40, acceleration 4.962°/frame² centered F39; quarter peak 16.055°/frame ending F39.5, acceleration 5.336°/frame² centered F38.75.
- RightForeArm: integer peak 8.228°/frame ending F30, acceleration 3.788°/frame² centered F31; quarter peak 8.381°/frame ending F29.5, acceleration 4.194°/frame² centered F31.25.
- RightHand: integer peak 16.072°/frame ending F40, acceleration 5.353°/frame² centered F43; quarter peak 16.240°/frame ending F39.75, acceleration 5.441°/frame² centered F42.75.
- Isolated speed spikes ≥10× neighboring median: 0. Hilt translation drift: 0.000374 mm; blade longitudinal-axis drift: 0.0000334°.
- Upper-arm/torso mesh penetration ranges: **not measured**, not zero. Full axial grip orientation: not independently certified.

### walk_stalk — FAIL-with-defect-report

No demonstrated arm-motion breach; required current-file, geometry and camera checks incomplete. See [defects_walk_stalk.md](defects_walk_stalk.md).

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

## Remaining findings and sequencing

**X-slash:** deviation proxy reaches −46.77° at F47.25 and exceeds ±30° over F44.75–51.75. Even ±15° axis-roll sensitivity leaves 33.76°–58.41° absolute deviation. This is a credible new candidate beyond the previous broad total-bend screen, but needs palm calibration. Quarter-frame elbow maximum is 148.22° at F38.75; the integer maximum still reproduces 147.92° at F39. The wrist total peak is 70.71° at F48.25 rather than the integer 70.54° at F48; it must not be confused with a >70° flexion violation.

First-cut world peaks: RightShoulder F35.50 → RightArm F39.00 = RightForeArm F39.00 → RightHand F39.50. Upper-arm and forearm peaks are 57.77°/frame and 57.74°/frame. The simultaneous peak is a strict whip-test flag. Second cut improves to RightArm F54.50 → RightForeArm F54.75 → RightHand F56.25. Local peaks are non-monotonic because they include elbow flexion and wrist compensation; this is not direct torque measurement. Existing fast acceleration is disclosed above without rebranding it as the already-fixed flip.

**Lunge:** in active F25–35, local peaks are RightShoulder F28.50 → RightArm F28.75 → RightForeArm F29.50, while RightHand peaks early at F27.50. A relatively fixed wrist can be appropriate for a thrust, so a wrist flick is not automatically recommended. Recovery world peaks bunch at F39.50 across upper arm/forearm/hand, 15.50/15.40/17.48°/frame. Upper-arm local recovery peak 16.06°/frame is 1.99× the active-thrust peak. At the final active frame F35, tip velocity is 50.65° off the blade axis, with 1.144 m/s transverse versus 0.938 m/s axial motion. Frame-specific F-curve trials are in the defect report.

**Idle and walk:** elbow excursions are 11.08° and 12.85°; neither is a locked straight arm. The largest sword-arm endpoint rotation mismatches are 0° and 0.0000661°. The largest finite-step seam velocity differences are 0.0829°/s and 0.4445°/s, both on RightForeArm. These small finite-difference values do not establish a visible snap. No strike exists in either action, so strike-sequence and strike-clip requirements are not applicable.

Constant-angular-velocity and wrist-only delivery claims were checked rather than assumed. X-slash first-cut local speed CVs are 0.580/0.432/0.396 for upper arm/forearm/hand; second-cut CVs are 0.346/0.691/0.374. Those speeds vary appreciably. The elbow is not straight throughout either cut, and both proximal joints move. No such puppet tell was confirmed by these tests.

## Single-support COM re-examination, F30–39

**Re-examined.** Reused the prior segment mass weights and boot hull (20 cm width, 12 cm heel extension, 9 cm beyond toe base), with right support alone from F30 until F40. F39 static margin is **−30.76 cm**, or −32.76 cm after a separate 2 cm inset. At quarter samples it reaches −31.39 cm at F39.75. This reproduces the prior retained warning.

Added a velocity-sensitive screen: capture point `COM_xy + velocity_xy / sqrt(9.81 / COM_height_above_floor)`, using central quarter-frame differences. It is outside right-foot support by 43.40 cm at F39; the worst pre-contact value is −73.12 cm at F37. After the left foot joins at F40 it is **18.68 cm inside** the enlarged hull; static margin is then +20.98 cm. The F40 support change can catch the proxy. This does not certify balance: vertical acceleration, sword mass/inertia, and angular momentum are omitted. The prior 2–6% sword-mass sensitivity was read but not independently rerun. Retain the warning; do not assert an inevitable fall from static COM alone.

## Visual assessment and evidence actually inspected

All four newly assembled nine-pose sheets were viewed directly. The 36 individual PNGs are FFmpeg crops of existing renders, with the original source paths and SHA-256 values recorded in `evidence_manifest.json`. They are not new EEVEE renders and provide only one angle per target. Source motion blur remains; cropping cannot undo it.

- **X-slash:** inspected `sheet_xslash_inherited.png`, F1, 27, 38, 39, 47, 48, 54, 61, 90. The rise into the load and both cuts are continuous. The first cut bunches the shoulder/elbow action; the second load keeps the wrist visibly cocked. The final extension softens into recovery. No return of the prior arm flip is visible. Blur and front occlusion prevent certifying elbow/armor clearance or the anatomical direction of wrist bend.
- **Idle guard:** inspected `sheet_idle_guard_inherited.png`, F1, 9, 25, 34, 49, 65, 78, 82, 96. The low point-down guard remains supported, with modest changes at the elbow and weight shift. No sword slippage or snap is visible. The tiny breathing motion is better established by the samples than by sparse stills.
- **Lunge thrust:** inspected `sheet_lunge_thrust_inherited.png`, F1, 17, 25, 29, 32, 37, 40, 43, 64. The thrust loads and extends with a firm wrist. The elbow rises toward the head and the blade drops conspicuously in F37–44, supporting the fast-recovery candidate. The initial thrust is not an elbow-locked straight push.
- **Walk stalk:** inspected `sheet_walk_stalk_inherited.png`, F1, 9, 23, 36, 42, 49, 59, 68, 72. The sword stays deliberately guarded while the body moves beneath it. No visible arm pop or slipping hilt is established. Torso-facing and underside contacts remain hidden.

Three half-speed crop clips were produced with **2× frame duplication at 30 fps** and decoded without errors. `clips_xslash_strike1_slowmo.mp4` covers F30–44 (30 output frames, 1.0 s); strike2 covers F47–64 (36 output frames, 1.2 s); `clips_lunge_thrust_strike1_slowmo.mp4` covers F21–44 (48 output frames, 1.6 s). Every original frame was visually inspected via the clips' eight decoded sheets: two for first X-slash, three for second X-slash, three for lunge. This was sequential decoded-frame inspection, not real-time playback. Row-major order and padding are documented in the manifest.

The original post-fix evaluation sheet, all three moveset contact sheets, and original full-resolution X-slash F48, lunge F40, and idle F33 were also viewed. Their absence from the deliverable list means they were read-only inputs, not newly produced files.

## Blocker, remaining work, and reproduction

Metal/default/factory startup all fail before executing scripts. OpenGL is not a supported backend in this build; its help lists only Metal. Command-mode startup also crashes. The backtrace reaches `supports_barycentric_whitelist` through `MTLBackend::metal_is_supported`. The exact GPU-device cause is not established. No sandbox bypass, permission escalation, external session, or server was used.

`scripts/astra_armaudit_capture.py` prepares fresh per-frame depsgraph sampling, evaluated torso/armor OBB versus upper-arm capsule overlap, evaluated full grip orientation, and transient front/side arm cameras using BLENDER_EEVEE. It never saves a blend, and caps each invocation at 20 rendered frames. It is **syntax-checked only**; do not describe it as runtime-validated. Coarse overlap is a candidate, not proof of mesh intersection. Palm-axis and hinge-sign calibration still require inspection even after it runs.

On a local execution context where this Blender can initialize, the first small batch is:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/tmp /opt/homebrew/bin/blender --background --gpu-backend metal --python-exit-code 1 --python scripts/astra_armaudit_capture.py -- xslash --stills 1,27,38,39,47,48,54,61,90
```

This renders 18 stills, not the held 90-frame hero job. Repeat with idle frames 1,9,25,34,49,65,78,82,96; lunge 1,17,25,29,32,37,40,43,64; walk 1,9,23,36,42,49,59,68,72. Separate clip batches can use `--clip 30:44` / `47:64` for X-slash, and `21:40` plus `41:44` for lunge. Fresh collector data is written with `_fresh.json`, so it does not overwrite or disguise inherited evidence. Reconcile source hashes and update the reports after those checks and camera reviews; the rendered clips would also need fresh encoding.

The completed cached work is reproducible without packages or bpy:

```sh
PYTHONDONTWRITEBYTECODE=1 /Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 scripts/astra_armaudit_analyze.py --cached
PYTHONDONTWRITEBYTECODE=1 python3 scripts/astra_armaudit_package.py
```

Analytic quaternion sign/known-angle tests passed, and integer elbow/wrist maxima reproduce the prior post-fix values within 0.01°. All three video decodes and expected frame counts passed. Source hashes before/after and numerical checks are in `verification.json`. No fresh geometry check is marked passed.

## Scope record

No blend, protected script, character/moveset/cinematography output, SPEC.txt, CLAUDE.md, or boss-fight.txt was edited. No git, ssh, network command or package install was run. Every Python/Blender invocation used PYTHONDONTWRITEBYTECODE=1; authored Python scripts additionally disable bytecode writes.

Two startup handling mistakes are disclosed: the first redirected log was initially created at `renders/astra/armaudit_inventory_start.log`, outside the allowed audit directory, then immediately moved into `renders/astra/armaudit/inventory_start.log`; no file remains at the mistaken path. The first Blender crash also wrote its default system-temp `blender.crash.txt`, outside the user-authorized /tmp path. Subsequent Blender invocations explicitly set TMPDIR=/tmp. These were scope deviations, not intentional changes to another track, and this report does not claim perfect write-scope compliance. No model was saved by any attempt.

## Complete deliverable file list

Paths below are relative to `/Users/aaron_7nh0yzm/godwyn-boss-fight`. The list includes scripts, raw data, reports, clips, stills, decoded sheets, manifests and diagnostics. Existing source files are excluded. `/tmp/blender.crash.txt` was also produced by failed startup attempts and copied into the audit directory; it is temporary, not a stable deliverable.

- `renders/astra/armaudit/analysis.log`
- `renders/astra/armaudit/blender_crash.txt`
- `renders/astra/armaudit/blender_help.txt`
- `renders/astra/armaudit/clips_lunge_thrust_strike1_slowmo.mp4`
- `renders/astra/armaudit/clips_xslash_strike1_slowmo.mp4`
- `renders/astra/armaudit/clips_xslash_strike2_slowmo.mp4`
- `renders/astra/armaudit/command_help.log`
- `renders/astra/armaudit/data_idle_guard.json`
- `renders/astra/armaudit/data_lunge_thrust.json`
- `renders/astra/armaudit/data_walk_stalk.json`
- `renders/astra/armaudit/data_xslash.json`
- `renders/astra/armaudit/decoded_lunge_thrust_strike1/sheet_01.png`
- `renders/astra/armaudit/decoded_lunge_thrust_strike1/sheet_02.png`
- `renders/astra/armaudit/decoded_lunge_thrust_strike1/sheet_03.png`
- `renders/astra/armaudit/decoded_xslash_strike1/sheet_01.png`
- `renders/astra/armaudit/decoded_xslash_strike1/sheet_02.png`
- `renders/astra/armaudit/decoded_xslash_strike2/sheet_01.png`
- `renders/astra/armaudit/decoded_xslash_strike2/sheet_02.png`
- `renders/astra/armaudit/decoded_xslash_strike2/sheet_03.png`
- `renders/astra/armaudit/defects_idle_guard.md`
- `renders/astra/armaudit/defects_lunge_thrust.md`
- `renders/astra/armaudit/defects_walk_stalk.md`
- `renders/astra/armaudit/defects_xslash.md`
- `renders/astra/armaudit/deliverables.txt`
- `renders/astra/armaudit/evidence_manifest.json`
- `renders/astra/armaudit/inventory.log`
- `renders/astra/armaudit/inventory_opengl.log`
- `renders/astra/armaudit/inventory_start.log`
- `renders/astra/armaudit/package.log`
- `renders/astra/armaudit/report.md`
- `renders/astra/armaudit/sheet_idle_guard_inherited.png`
- `renders/astra/armaudit/sheet_idle_guard_inputs.txt`
- `renders/astra/armaudit/sheet_lunge_thrust_inherited.png`
- `renders/astra/armaudit/sheet_lunge_thrust_inputs.txt`
- `renders/astra/armaudit/sheet_walk_stalk_inherited.png`
- `renders/astra/armaudit/sheet_walk_stalk_inputs.txt`
- `renders/astra/armaudit/sheet_xslash_inherited.png`
- `renders/astra/armaudit/sheet_xslash_inputs.txt`
- `renders/astra/armaudit/source_inventory.json`
- `renders/astra/armaudit/stills_idle_guard/001_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/009_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/025_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/034_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/049_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/065_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/078_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/082_inherited.png`
- `renders/astra/armaudit/stills_idle_guard/096_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/001_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/017_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/025_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/029_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/032_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/037_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/040_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/043_inherited.png`
- `renders/astra/armaudit/stills_lunge_thrust/064_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/001_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/009_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/023_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/036_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/042_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/049_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/059_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/068_inherited.png`
- `renders/astra/armaudit/stills_walk_stalk/072_inherited.png`
- `renders/astra/armaudit/stills_xslash/001_inherited.png`
- `renders/astra/armaudit/stills_xslash/027_inherited.png`
- `renders/astra/armaudit/stills_xslash/038_inherited.png`
- `renders/astra/armaudit/stills_xslash/039_inherited.png`
- `renders/astra/armaudit/stills_xslash/047_inherited.png`
- `renders/astra/armaudit/stills_xslash/048_inherited.png`
- `renders/astra/armaudit/stills_xslash/054_inherited.png`
- `renders/astra/armaudit/stills_xslash/061_inherited.png`
- `renders/astra/armaudit/stills_xslash/090_inherited.png`
- `renders/astra/armaudit/summary.json`
- `renders/astra/armaudit/verification.json`
- `scripts/astra_armaudit_analyze.py`
- `scripts/astra_armaudit_capture.py`
- `scripts/astra_armaudit_inspect.py`
- `scripts/astra_armaudit_package.py`
- `scripts/astra_armaudit_report.py`
