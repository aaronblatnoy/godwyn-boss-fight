"""Package measured findings and explicit audit gaps; never certify unrun checks."""
import sys, json, ast, hashlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'renders/astra/armaudit'

XDEF='''# X-slash sword-arm defects — motion track

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
'''

LDEF='''# Lunge thrust sword-arm defects — moveset track

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
'''

def stats(name,d):
    r=d['ranges'];lines=[]
    labels={'shoulder_elevation_deg':'Shoulder elevation','shoulder_flexion_projection_deg':'Shoulder flexion projection','shoulder_abduction_projection_deg':'Shoulder abduction projection','elbow_flexion_deg':'Elbow flexion','wrist_total_bend_deg':'Total wrist bend','wrist_flexion_proxy_deg':'Wrist flexion proxy','wrist_deviation_proxy_deg':'Wrist deviation proxy'}
    for key,label in labels.items():
        v=r[key];lines.append(f"- {label}: {v['min']:.2f}° (F{v['min_frame']:g}) to {v['max']:.2f}° (F{v['max_frame']:g}).")
    for bone in ['RightShoulder','RightArm','RightForeArm','RightHand']:
        a=d['peaks'][bone]['integer_local'];b=d['peaks'][bone]['quarter_local']
        lines.append(f"- {bone}: integer peak {a['max_speed']:.3f}°/frame ending F{a['max_speed_frame']:g}, acceleration {a['max_acceleration']:.3f}°/frame² centered F{a['max_acceleration_center_frame']:g}; quarter peak {b['max_speed']:.3f}°/frame ending F{b['max_speed_frame']:g}, acceleration {b['max_acceleration']:.3f}°/frame² centered F{b['max_acceleration_center_frame']:g}.")
    lines.append(f"- Isolated speed spikes ≥10× neighboring median: {len(d['spikes'])}. Hilt translation drift: {d['grip']['max_translation_drift_m']*1000:.6f} mm; blade longitudinal-axis drift: {d['grip']['max_axis_drift_deg']:.7f}°.")
    lines.append('- Upper-arm/torso mesh penetration ranges: **not measured**, not zero. Full axial grip orientation: not independently certified.')
    return '\n'.join(lines)

def main():
    summary=json.loads((OUT/'summary.json').read_text());inv=json.loads((OUT/'source_inventory.json').read_text());e=json.loads((OUT/'evidence_manifest.json').read_text());v=json.loads((OUT/'verification.json').read_text())
    (OUT/'defects_xslash.md').write_text(XDEF)
    (OUT/'defects_lunge_thrust.md').write_text(LDEF)
    for name in ['idle_guard','walk_stalk']:
        d=summary[name];seam=max(d['loop'].items(),key=lambda kv:kv[1]['velocity_mismatch_deg_s']);error=max(x['endpoint_rotation_error_deg'] for x in d['loop'].values());span=d['ranges']['elbow_flexion_deg']['max']-d['ranges']['elbow_flexion_deg']['min']
        text=f'''# {name.replace('_',' ').title()} sword-arm defect disposition — moveset track

**FAIL-with-defect-report for incomplete required audit coverage. No confirmed sword-arm motion defect in the available samples.** This is not a claim that a failing animation was found. The blend was never edited.

## Findings from the measured cached samples

{stats(name,d)}

The elbow changes by {span:.2f}° over the cycle, so it is not locked. The chain has nonzero, varying local velocities; the wrist is neither frozen nor the only moving joint. The guarded arm position fits the intended watchful low guard. A stationary-looking sword in a guard is not sufficient evidence of a puppet swing.

The duplicated loop endpoint has at most {error:.7f}° sword-arm rotation mismatch. The largest one-sided quarter-frame velocity difference is {seam[1]['velocity_mismatch_deg_s']:.4f}°/s on {seam[0]}. Such a finite-step difference includes normal curvature; it is not proof of a derivative discontinuity. No visible pose snap was identified in the inspected beginning/end stills.

## Open audit defect: current-file and geometry certification

Required coverage is incomplete for F{d['frame_range'][0]:g}–{d['frame_range'][1]:g}: Blender crashed before running the collector. The inherited samples postdate the target's save, but do not carry that target blend's SHA-256. Fresh depsgraph evaluation, palm-axis calibration, upper-arm/torso overlap, full grip roll and two-angle renders are still required. Their absence prevents PASS.

**F-curve disposition:** no quantitative breach justifies changing a key here. Do not add arbitrary sway, retime the loop, or modify the wrist to manufacture a defect. Run the prepared read-only collector and review any actual collision candidate before choosing an F-curve correction.

Evidence actually inspected: `sheet_{name}_inherited.png`, with frame order {e['stills'][name]['order']}; nine individual crop files are retained in `stills_{name}/`. They are inherited single-camera renders, not newly rendered two-angle evidence. There is no strike in this action, so no strike slow-motion clip is required.
'''
        (OUT/f'defects_{name}.md').write_text(text)
    report='''# Sword-arm naturalness audit — partial, with explicit blockers

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
'''
    for name,d in summary.items():
        reason={'xslash':'Remaining wrist-deviation candidate and simultaneous first-cut arm peaks; geometry/render coverage incomplete.','lunge_thrust':'Fast compact recovery and lateral motion at the last active thrust frame are candidate refinements; current-file and geometry coverage incomplete.','idle_guard':'No demonstrated arm-motion breach; required current-file, geometry and camera checks incomplete.','walk_stalk':'No demonstrated arm-motion breach; required current-file, geometry and camera checks incomplete.'}[name]
        report+=f"\n### {name} — FAIL-with-defect-report\n\n{reason} See [defects_{name}.md](defects_{name}.md).\n\n{stats(name,d)}\n"
    report+='''
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

'''
    # Finalize checks and enumerate every produced file; no recursive external scan.
    v['syntax_checked']=[]
    for p in sorted((ROOT/'scripts').glob('astra_armaudit_*.py')):
        ast.parse(p.read_text());v['syntax_checked'].append(str(p.relative_to(ROOT)))
    for name,record in inv['targets'].items():
        digest=hashlib.sha256(Path(record['path']).read_bytes()).hexdigest();v['source_hashes'][name]['after']=digest;v['source_hashes'][name]['unchanged']=digest==record['sha256'];assert v['source_hashes'][name]['unchanged']
    (OUT/'verification.json').write_text(json.dumps(v,indent=2))
    (OUT/'report.md').write_text(report)
    (OUT/'deliverables.txt').write_text('')
    files=sorted([p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file()]+[p.relative_to(ROOT).as_posix() for p in (ROOT/'scripts').glob('astra_armaudit_*.py')])
    (OUT/'deliverables.txt').write_text('\n'.join(files)+'\n')
    (OUT/'report.md').write_text(report+'\n'.join('- `'+f+'`' for f in files)+'\n')
    print('Wrote four defect dispositions, report, verification, and complete file list:',len(files),'files. Full fresh audit remains blocked.')

if __name__=='__main__':main()
