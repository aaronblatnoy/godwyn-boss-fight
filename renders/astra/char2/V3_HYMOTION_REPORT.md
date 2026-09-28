# V3 HY-Motion moveset — final review

Executed September 28, 2026 on black-sky. Default Codex performed the visual review directly; no delegated or external-model judging.

**Outcome: sword_slash_r published from Round 2. All 27 new HY-Motion candidates rejected after visual inspection; no complete Phase-1 moveset was produced.**

## Step 0

Completed within the brief's initial 20-minute window. The relaxed p99 ceiling
is 2.2. I inspected all decoded frames of the three existing Round-2 films,
then rendered exact (non-interpolated) worst-p99 and absolute-worst frames in
Cycles/OptiX at 1024 square on black-sky.

| Source | Requested clip | Worst p99 | Decision |
|---|---|---:|---|
| Right_Hand_Sword_Slash | sword_slash_r | 1.7530 | ACCEPT: readable cut; no visible tearing at F26 or F16 |
| Sword_Parry | parry_stance | 1.8546 | REJECT: exact F15 exposes jagged open torso and skirt surfaces |
| Hit_Reaction | stagger | 1.9240 | REJECT: exact F21 exposes open breastplate, hip and robe fragmentation |

All three pass the inherited visible-collar, sword/body, sword/head, and floor
numbers. Numeric passage does not override the visible defects. Some gaps are
pre-existing source topology; the parry and recoil poses make them conspicuous.
The accepted slash retains the known minor source-surface limitations.

Published `models/astra_character_v3.blend` and `.glb` on black-sky with
`Combat_Stance` (51 frames) and `sword_slash_r` (46 frames), both at 30 fps.
The preceding canonical pair is preserved as `_prev`. Native/GLB action names,
frame counts, all 24 bones, hierarchy and weight normalization passed the
round-trip check. Maximum rest-joint error: 0.0326 mm.

Publication receipts: `renders/hymotion/v3/step0_publish.json` and
`step0_roundtrip.json`. Visual evidence and exact crops: `renders/hymotion/v3/step0/`.

## Generation and retarget contract

Nine roles, seeds 42 / 137 / 271. The brief's durations take precedence for
these authored clips, including its two-second `the_pause` excerpt; SPEC's
gameplay pause lasts 3–5 seconds. The brief also explicitly requests the first
X diagonal down-right then down-left, reversing SPEC's listed starting side.
Prompts preserve the grounded low-hang, heavy weight-shift vocabulary.

The V3 import has bone display tails approximately 100 times longer than its
actual joint spacing. Retarget scale therefore uses hip-to-knee-to-ankle joint
positions, not bone tail lengths. HY-Motion aiming follows the existing
`hymotion_retarget.py` method with a proper right-handed root, inherited foot
orientation relative to the shin, and a rigid RightHand-bound sword. Grounding
uses one constant vertical shift per clip, never per-frame floor clamping.

New candidate films use native 30 fps frames at 768×768, no optical-flow
interpolation. Every candidate receives all-frame body-stretch, sole, sword,
floor and visible-collar checks. The inherited allowed interior jaw/gorget
attachment volume remains excluded from exterior collision checks.

## Execution constraints

All ComfyUI, Blender, ffmpeg and ffprobe execution is on black-sky. No git.
Ollama and vLLM remain untouched. An initial GPU out-of-memory failure occurred
when another Ollama workload occupied both GPUs; only this run's ComfyUI
instance was restarted for CPU generation. Blender rendering uses OptiX only.
The main transcript log is `renders/astra/char2/codex_hym.log`.

## Corrected retarget pass

An initial retarget pass omitted world travel. The node returns joint positions with a constant pelvis offset while storing actual motion in `transl`; `hymotion/pipeline/body_model.py` lines 302–309 add translation to vertices but return untranslated `posed_joints`. The inherited retarget assumed moving pelvis keypoints. The corrected implementation subtracts the constant pelvis offset, adds NPZ `transl`, then applies the same smoothing, aiming, scale and constant grounding. Every candidate film, audit, crop and verdict was regenerated. Invalid preliminary outputs are preserved under `first_pass_missing_root_translation/` and excluded from final results. This correction matters particularly for walk travel, hop height, landing and collapse.


## Generation settings and prompts

HY-Motion-1.0-Lite; Qwen3-8B-bnb-4bit text encoder, CPU offload; node-default motion guidance. Seeds **42, 137, 271** for every role. Native 30 fps. Full request graphs, output hashes and ComfyUI histories are preserved in each `_generation.json`.

### idle_low_hang — 3 seconds

A tall knight holds a heavy greatsword in his right hand. He stands in a loaded low hang guard, sword hanging low at his right side with the point toward the ground. Subtle breathing and restrained weight shifts, feet planted, upright and threatening. Seamless looping stance. No jumps or spins.

### stalk_walk — 2 seconds

A tall knight holds a heavy greatsword in his right hand. He advances slowly with deliberate heavy alternating steps, sword held low at his right side in low hang guard. Grounded stalking walk, weight shifts from heel to toe, toes forward. Upright shoulders, no jumps, no running. Repeating walking cycle.

### x_combo — 2 seconds

A tall knight holds a heavy greatsword in his right hand. From low hang guard he drives two powerful crossing diagonal sword cuts in front of his body: first down-right, then down-left, tracing a visible X. Spine, hips and shoulders drive the heavy blade, with grounded weight shifts between planted feet. Continuous flowing assault, no jumps, no flips, no reset between cuts.

### horizontal_sweep — 1.5 seconds

A tall knight holds a heavy greatsword in his right hand. From low hang guard he sweeps the greatsword widely from right to left at chest height. His hips and shoulders drive the cut, planted feet pivot, follow-through turns his back toward the opponent. One grounded heavy sword cut. No jumps, no flips.

### jump_lunge — 2 seconds

A tall knight holds a heavy greatsword in his right hand. From low guard he makes a short low hop forward into a straight right-handed greatsword thrust. The thrust is the landing: he lands firmly on his leading foot and takes one overshooting forward step, turning his back toward the passed opponent. Heavy compact gap closer, no flips or high leaps.

### rising_spin — 2 seconds

A tall knight holds a heavy greatsword in his right hand. From low hang guard he makes exactly one full controlled clockwise turn over two seconds while swinging the greatsword from low to high. Feet step and pivot on the ground, heavy readable circular rising cut. At most one rotation per second. No jumps, flips or repeated whirling.

### the_pause — 2 seconds

A tall knight holds a heavy greatsword in his right hand. He freezes completely in low hang guard, sword low at his right side, staring forward. After a long still hold he suddenly takes one short step sideways offline, keeping the sword ready. Grounded and minimal. No jumps or spins.

### stagger — 1 seconds

A tall knight holds a heavy greatsword in his right hand. He takes a compact heavy hit to the chest, recoils through his shoulders and spine, shifts his weight backward onto one foot and recovers his balance. Right hand keeps the greatsword beside the body. Grounded brief stagger, no leap, no fall, no spin.

### death — 2.5 seconds

A tall knight holds a heavy greatsword in his right hand. He collapses forward under his weight, first sinking onto both knees, then falling forward until his torso lies down on the ground. His right arm carries the greatsword away to his side. Heavy irreversible collapse and still finish. No jump, no flip, no recovery.

## Per-candidate audit and visual verdicts

Each 768×768 film was examined through chronological pages containing **every native frame**, followed by exact 1024×1024 crops at both the worst-p99 frame and the absolute maximum-stretch frame. These are direct visual inspections, not a real-time video-playback claim. Contact sheets and MP4s accompany every candidate.

Collar pairs are summed exterior head/hair triangle intersections across all frames. Sword/body reports affected frames. Blade penetration is depth below z=0. Sole contact reports frames with the lowest sole within 5 mm; a globally grounded clip can still float during its motion, which the visual review rejects.

| Candidate | Frames | p99 / worst frame | Absolute max / frame | Collar pairs | Sword/body frames | Blade penetration mm | Sole contact frames | Numeric gate | Verdict |
|---|---:|---|---|---:|---:|---:|---:|---|---|
| idle_low_hang_s42 | 90 | 1.4087 / F54 | 7.291 / F90 | 0 | 0 | 0.00 | 9/90 | PASS | REJECT |
| idle_low_hang_s137 | 90 | 1.3742 / F50 | 7.935 / F43 | 0 | 0 | 0.00 | 7/90 | PASS | REJECT |
| idle_low_hang_s271 | 90 | 1.4637 / F26 | 7.164 / F57 | 0 | 0 | 0.00 | 4/90 | PASS | REJECT |
| stalk_walk_s42 | 60 | 1.3641 / F50 | 3.943 / F35 | 0 | 0 | 0.00 | 5/60 | PASS | REJECT |
| stalk_walk_s137 | 60 | 1.4416 / F19 | 4.560 / F18 | 0 | 0 | 0.00 | 6/60 | PASS | REJECT |
| stalk_walk_s271 | 60 | 1.3984 / F47 | 4.025 / F31 | 0 | 0 | 0.00 | 4/60 | PASS | REJECT |
| x_combo_s42 | 60 | 1.6836 / F17 | 10.219 / F5 | 1466 | 0 | 0.00 | 3/60 | FAIL | REJECT |
| x_combo_s137 | 60 | 1.7391 / F9 | 10.760 / F10 | 0 | 1 | 0.00 | 3/60 | FAIL | REJECT |
| x_combo_s271 | 60 | 1.6598 / F26 | 9.004 / F9 | 3 | 1 | 0.00 | 9/60 | FAIL | REJECT |
| horizontal_sweep_s42 | 45 | 1.9836 / F14 | 7.408 / F15 | 0 | 2 | 0.00 | 1/45 | FAIL | REJECT |
| horizontal_sweep_s137 | 45 | 1.9345 / F9 | 8.418 / F10 | 0 | 7 | 0.00 | 1/45 | FAIL | REJECT |
| horizontal_sweep_s271 | 45 | 1.7688 / F29 | 8.473 / F34 | 0 | 0 | 0.00 | 1/45 | PASS | REJECT |
| jump_lunge_s42 | 60 | 1.9505 / F13 | 8.284 / F16 | 0 | 12 | 662.73 | 2/60 | FAIL | REJECT |
| jump_lunge_s137 | 60 | 2.1200 / F10 | 7.562 / F20 | 0 | 5 | 421.98 | 2/60 | FAIL | REJECT |
| jump_lunge_s271 | 60 | 2.0631 / F16 | 8.959 / F15 | 0 | 0 | 0.00 | 2/60 | PASS | REJECT |
| rising_spin_s42 | 60 | 1.7574 / F27 | 9.012 / F5 | 0 | 6 | 0.00 | 2/60 | FAIL | REJECT |
| rising_spin_s137 | 60 | 1.7063 / F35 | 9.565 / F23 | 0 | 5 | 161.35 | 1/60 | FAIL | REJECT |
| rising_spin_s271 | 60 | 1.8866 / F22 | 8.864 / F17 | 0 | 2 | 0.00 | 1/60 | FAIL | REJECT |
| the_pause_s42 | 60 | 1.4530 / F4 | 6.504 / F24 | 0 | 0 | 0.00 | 4/60 | PASS | REJECT |
| the_pause_s137 | 60 | 1.4548 / F40 | 6.985 / F9 | 0 | 0 | 0.00 | 7/60 | PASS | REJECT |
| the_pause_s271 | 60 | 1.4155 / F40 | 6.181 / F60 | 0 | 0 | 0.00 | 4/60 | PASS | REJECT |
| stagger_s42 | 30 | 1.6433 / F5 | 9.198 / F15 | 349 | 0 | 77.57 | 1/30 | FAIL | REJECT |
| stagger_s137 | 30 | 1.7222 / F24 | 8.403 / F8 | 0 | 19 | 254.21 | 1/30 | FAIL | REJECT |
| stagger_s271 | 30 | 1.7591 / F30 | 9.044 / F1 | 0 | 2 | 0.00 | 3/30 | FAIL | REJECT |
| death_s42 | 75 | 1.4973 / F7 | 6.888 / F5 | 0 | 3 | 323.82 | 18/75 | FAIL | REJECT |
| death_s137 | 75 | 1.7166 / F6 | 8.121 / F37 | 0 | 8 | 1301.57 | 5/75 | FAIL | REJECT |
| death_s271 | 75 | 1.6325 / F41 | 7.756 / F8 | 348 | 6 | 1071.41 | 13/75 | FAIL | REJECT |

**idle_low_hang_s42: REJECT.** Corrected root-motion film: all 90 frames and both exact crops reviewed. Restrained movement and low blade, but an oblique bowed posture, empty off-hand near the hilt, conspicuously exposed neck insert, and pointed-toe support. The loaded upright low-hang silhouette is absent. Evidence: [film](../../hymotion/v3/idle_low_hang_s42.mp4), [contact sheet](../../hymotion/v3/idle_low_hang_s42_sheet.jpg), [audit](../../hymotion/v3/idle_low_hang_s42_audit.json), [F54 crop](../../hymotion/v3/idle_low_hang_s42_crop_F54.png), [F90 crop](../../hymotion/v3/idle_low_hang_s42_crop_F90.png).

**idle_low_hang_s137: REJECT.** Corrected root-motion film: all 90 frames and both exact crops reviewed. Almost static bowed stance with open off-hand reaching forward and exposed neck mass above the gorget. Boots remain perched on pointed toes; the sword reaches forward rather than resting low at the side. Evidence: [film](../../hymotion/v3/idle_low_hang_s137.mp4), [contact sheet](../../hymotion/v3/idle_low_hang_s137_sheet.jpg), [audit](../../hymotion/v3/idle_low_hang_s137_audit.json), [F43 crop](../../hymotion/v3/idle_low_hang_s137_crop_F43.png), [F50 crop](../../hymotion/v3/idle_low_hang_s137_crop_F50.png).

**idle_low_hang_s271: REJECT.** Corrected root-motion film: all 90 frames and F26/F57 reviewed. Sword remains forward near waist height rather than hanging at the right side. One boot hangs above the floor, with pointed-toe support and a bowed neck. Both crops show the exposed neck insert and dark shoulder seam. Evidence: [film](../../hymotion/v3/idle_low_hang_s271.mp4), [contact sheet](../../hymotion/v3/idle_low_hang_s271_sheet.jpg), [audit](../../hymotion/v3/idle_low_hang_s271_audit.json), [F26 crop](../../hymotion/v3/idle_low_hang_s271_crop_F26.png), [F57 crop](../../hymotion/v3/idle_low_hang_s271_crop_F57.png).

**stalk_walk_s42: REJECT.** Corrected root-motion film: all 60 frames and F50/F35 reviewed. Alternating forward gait now includes source travel, but the boots still dangle with pointed toes and lack convincing heel-to-toe loading. Sword stays high and horizontal in front rather than low. Both exact crops expose a long neck column and gaps inside the skirt. Evidence: [film](../../hymotion/v3/stalk_walk_s42.mp4), [contact sheet](../../hymotion/v3/stalk_walk_s42_sheet.jpg), [audit](../../hymotion/v3/stalk_walk_s42_audit.json), [F35 crop](../../hymotion/v3/stalk_walk_s42_crop_F35.png), [F50 crop](../../hymotion/v3/stalk_walk_s42_crop_F50.png).

**stalk_walk_s137: REJECT.** Corrected root-motion film: all 60 frames and F19/F18 reviewed. Forward alternating gait is present, but boots remain pointed and hovering without convincing heel-to-toe loading. The sword is carried forward at waist height; the open off-hand and very long exposed neck insert undermine the heavy low guard. Evidence: [film](../../hymotion/v3/stalk_walk_s137.mp4), [contact sheet](../../hymotion/v3/stalk_walk_s137_sheet.jpg), [audit](../../hymotion/v3/stalk_walk_s137_audit.json), [F18 crop](../../hymotion/v3/stalk_walk_s137_crop_F18.png), [F19 crop](../../hymotion/v3/stalk_walk_s137_crop_F19.png).

**stalk_walk_s271: REJECT.** Corrected film: all 60 frames and F47/F31 reviewed. Small alternating gait with pointed boots and visibly floating support; blade remains forward rather than low at the right side. Worst crops show an exposed tall neck insert and small dark torso/shoulder openings. The stance never reads as a heavy stalking walk. Evidence: [film](../../hymotion/v3/stalk_walk_s271.mp4), [contact sheet](../../hymotion/v3/stalk_walk_s271_sheet.jpg), [audit](../../hymotion/v3/stalk_walk_s271_audit.json), [F31 crop](../../hymotion/v3/stalk_walk_s271_crop_F31.png), [F47 crop](../../hymotion/v3/stalk_walk_s271_crop_F47.png).

**x_combo_s42: REJECT.** Corrected film: all 60 frames and both exact crops reviewed. One broad rising cross-body arc, a hold, then one lowering cut and long recovery; no distinct down-right/down-left pair. Both crops show neck separation and armor openings, including the shoulder/side. Feet remain lightly floating. Evidence: [film](../../hymotion/v3/x_combo_s42.mp4), [contact sheet](../../hymotion/v3/x_combo_s42_sheet.jpg), [audit](../../hymotion/v3/x_combo_s42_audit.json), [F5 crop](../../hymotion/v3/x_combo_s42_crop_F5.png), [F17 crop](../../hymotion/v3/x_combo_s42_crop_F17.png).

**x_combo_s137: REJECT.** Corrected film: all 60 frames and both exact crops reviewed. One raised windup and cross-body cut followed by a low recovery; no readable pair of opposing downward cuts. Both worst frames expose large jagged holes in shoulder/side armor and the neck insert. The off-hand never grips the weapon. Evidence: [film](../../hymotion/v3/x_combo_s137.mp4), [contact sheet](../../hymotion/v3/x_combo_s137_sheet.jpg), [audit](../../hymotion/v3/x_combo_s137_audit.json), [F9 crop](../../hymotion/v3/x_combo_s137_crop_F9.png), [F10 crop](../../hymotion/v3/x_combo_s137_crop_F10.png).

**x_combo_s271: REJECT.** Corrected film: all 60 frames and F26/F9 reviewed. A level cross-body sweep and gradual lowering replace the two diagonal downward cuts. The shoulder and flank armor split into large jagged openings in both crops; exposed neck insert and floating pointed boots persist. Evidence: [film](../../hymotion/v3/x_combo_s271.mp4), [contact sheet](../../hymotion/v3/x_combo_s271_sheet.jpg), [audit](../../hymotion/v3/x_combo_s271_audit.json), [F9 crop](../../hymotion/v3/x_combo_s271_crop_F9.png), [F26 crop](../../hymotion/v3/x_combo_s271_crop_F26.png).

**horizontal_sweep_s42: REJECT.** Corrected film: all 45 frames and F14/F15 reviewed. A broad initial sweep is readable, but the body then folds and sinks into a suspended kneeling turn rather than a grounded sweeping recovery. Both crops expose torn shoulder armor and a large side/waist opening. Evidence: [film](../../hymotion/v3/horizontal_sweep_s42.mp4), [contact sheet](../../hymotion/v3/horizontal_sweep_s42_sheet.jpg), [audit](../../hymotion/v3/horizontal_sweep_s42_audit.json), [F14 crop](../../hymotion/v3/horizontal_sweep_s42_crop_F14.png), [F15 crop](../../hymotion/v3/horizontal_sweep_s42_crop_F15.png).

**horizontal_sweep_s137: REJECT.** Corrected film: all 45 frames and F9/F10 reviewed. The blade rises into a windup and drops across the body, followed by a hopping recovery; the requested grounded horizontal sweep is absent. Both exact crops show large broken strips of shoulder, flank and inner-skirt geometry. Evidence: [film](../../hymotion/v3/horizontal_sweep_s137.mp4), [contact sheet](../../hymotion/v3/horizontal_sweep_s137_sheet.jpg), [audit](../../hymotion/v3/horizontal_sweep_s137_audit.json), [F9 crop](../../hymotion/v3/horizontal_sweep_s137_crop_F9.png), [F10 crop](../../hymotion/v3/horizontal_sweep_s137_crop_F10.png).

**horizontal_sweep_s271: REJECT.** Corrected film: all 45 frames and F29/F34 reviewed. Upward windup crosses high in front, then the character bows and lowers the blade. No sustained wide horizontal sweep or loaded back-foot pivot; much of the recovery visibly hovers. Crops show a dark open shoulder seam and floating off-hand rather than a stable grip. Evidence: [film](../../hymotion/v3/horizontal_sweep_s271.mp4), [contact sheet](../../hymotion/v3/horizontal_sweep_s271_sheet.jpg), [audit](../../hymotion/v3/horizontal_sweep_s271_audit.json), [F29 crop](../../hymotion/v3/horizontal_sweep_s271_crop_F29.png), [F34 crop](../../hymotion/v3/horizontal_sweep_s271_crop_F34.png).

**jump_lunge_s42: REJECT.** Corrected film: all 60 frames and F13/F16 reviewed. A short raised-blade chop drops into a deep crouch and long hold, then rises; no forward thrust or readable landing overshoot. Pointed feet float through portions of the move. Both crops show an open shoulder seam and badly folded/open inner-skirt geometry. Evidence: [film](../../hymotion/v3/jump_lunge_s42.mp4), [contact sheet](../../hymotion/v3/jump_lunge_s42_sheet.jpg), [audit](../../hymotion/v3/jump_lunge_s42_audit.json), [F13 crop](../../hymotion/v3/jump_lunge_s42_crop_F13.png), [F16 crop](../../hymotion/v3/jump_lunge_s42_crop_F16.png).

**jump_lunge_s137: REJECT.** Corrected film: all 60 frames and F10/F20 reviewed. The weapon makes an overhead chop into a very wide low stance, followed by a low turning recovery to face away. It does not thrust through a short forward hop and overshooting landing. Worst crops expose flank strips, an open shoulder seam and fragmented inner cloth. Evidence: [film](../../hymotion/v3/jump_lunge_s137.mp4), [contact sheet](../../hymotion/v3/jump_lunge_s137_sheet.jpg), [audit](../../hymotion/v3/jump_lunge_s137_audit.json), [F10 crop](../../hymotion/v3/jump_lunge_s137_crop_F10.png), [F20 crop](../../hymotion/v3/jump_lunge_s137_crop_F20.png).

**jump_lunge_s271: REJECT.** Corrected film: all 60 frames and F16/F15 reviewed. A sideways extended reach sinks into a split stance, then pivots away and holds. It lacks the short forward hop, forward thrust and overshooting landing. The torso is more intact than the other lunges, but the neck insert remains exposed and the recovery floats above pointed boots. Evidence: [film](../../hymotion/v3/jump_lunge_s271.mp4), [contact sheet](../../hymotion/v3/jump_lunge_s271_sheet.jpg), [audit](../../hymotion/v3/jump_lunge_s271_audit.json), [F15 crop](../../hymotion/v3/jump_lunge_s271_crop_F15.png), [F16 crop](../../hymotion/v3/jump_lunge_s271_crop_F16.png).

**rising_spin_s42: REJECT.** Corrected film: all 60 frames and F27/F5 reviewed. The character rotates away while lifting the blade, then unwinds toward the initial facing instead of completing one continuous full turn. Much of the move levitates above its shadow. F27 exposes severe shredded back armor; F5 shows the tall neck insert and shoulder opening. Source hip-yaw proxy: 221.1-degree range, only 5.9-degree net turn, peak 1.983 turns/s. Evidence: [film](../../hymotion/v3/rising_spin_s42.mp4), [contact sheet](../../hymotion/v3/rising_spin_s42_sheet.jpg), [audit](../../hymotion/v3/rising_spin_s42_audit.json), [F5 crop](../../hymotion/v3/rising_spin_s42_crop_F5.png), [F27 crop](../../hymotion/v3/rising_spin_s42_crop_F27.png).

**rising_spin_s137: REJECT.** Corrected film: all 60 frames and both exact crops reviewed. Two rapid rotations with prolonged airborne-looking travel; not one controlled grounded turn. F35 exposes broad back and shoulder holes plus cloth splitting; F23 exposes the neck column. Source hip yaw measures -711.1 degrees net and a 3.523 turns/s peak. Evidence: [film](../../hymotion/v3/rising_spin_s137.mp4), [contact sheet](../../hymotion/v3/rising_spin_s137_sheet.jpg), [audit](../../hymotion/v3/rising_spin_s137_audit.json), [F23 crop](../../hymotion/v3/rising_spin_s137_crop_F23.png), [F35 crop](../../hymotion/v3/rising_spin_s137_crop_F35.png).

**rising_spin_s271: REJECT.** Corrected film: all 60 frames and both exact crops reviewed. Rapid winding and unwinding with a raised-blade hold, floating feet and a long recovery; not one continuous controlled turn. Both exact crops reveal major holes in the back/side armor and underarm. Source hip-yaw range is 334.3 degrees but only 7.8 degrees net, with a 3.294 turns/s peak. Evidence: [film](../../hymotion/v3/rising_spin_s271.mp4), [contact sheet](../../hymotion/v3/rising_spin_s271_sheet.jpg), [audit](../../hymotion/v3/rising_spin_s271_audit.json), [F17 crop](../../hymotion/v3/rising_spin_s271_crop_F17.png), [F22 crop](../../hymotion/v3/rising_spin_s271_crop_F22.png).

**the_pause_s42: REJECT.** Corrected film: all 60 frames and both exact crops reviewed. An almost static angled guard persists for the whole clip; the sudden step never arrives. Boots begin suspended and only drift toward the floor. Both crops show the exposed neck insert and open blue shoulder seam. Evidence: [film](../../hymotion/v3/the_pause_s42.mp4), [contact sheet](../../hymotion/v3/the_pause_s42_sheet.jpg), [audit](../../hymotion/v3/the_pause_s42_audit.json), [F4 crop](../../hymotion/v3/the_pause_s42_crop_F4.png), [F24 crop](../../hymotion/v3/the_pause_s42_crop_F24.png).

**the_pause_s137: REJECT.** Corrected film: all 60 frames and both exact crops reviewed. A slight weight shift and bob occurs in an otherwise static low-blade stance, with no distinct freeze-to-sudden-step event. Pointed boots briefly hover. Both crops expose the long neck insert and open inner-skirt surfaces. Evidence: [film](../../hymotion/v3/the_pause_s137.mp4), [contact sheet](../../hymotion/v3/the_pause_s137_sheet.jpg), [audit](../../hymotion/v3/the_pause_s137_audit.json), [F9 crop](../../hymotion/v3/the_pause_s137_crop_F9.png), [F40 crop](../../hymotion/v3/the_pause_s137_crop_F40.png).

**the_pause_s271: REJECT.** Corrected film: All 60 frames and both crops reviewed. Tiny weight and arm changes never become the sudden advancing step. Low blade is closer to the target, but the stance remains bowed and the neck insert and inner-skirt opening are conspicuous. Evidence: [film](../../hymotion/v3/the_pause_s271.mp4), [contact sheet](../../hymotion/v3/the_pause_s271_sheet.jpg), [audit](../../hymotion/v3/the_pause_s271_audit.json), [F40 crop](../../hymotion/v3/the_pause_s271_crop_F40.png), [F60 crop](../../hymotion/v3/the_pause_s271_crop_F60.png).

**stagger_s42: REJECT.** Corrected film: All 30 frames and both crops reviewed. The initial recoil is legible, but it arches the head far behind an exposed block-like neck insert, bobs into the air and sinks toward a kneel before recovering. F5 has flank slits and fragmented inner cloth; F15 adds a breastplate slit and open shoulder seam. Not a compact grounded stagger. Evidence: [film](../../hymotion/v3/stagger_s42.mp4), [contact sheet](../../hymotion/v3/stagger_s42_sheet.jpg), [audit](../../hymotion/v3/stagger_s42_audit.json), [F5 crop](../../hymotion/v3/stagger_s42_crop_F5.png), [F15 crop](../../hymotion/v3/stagger_s42_crop_F15.png).

**stagger_s137: REJECT.** Corrected film: all 30 frames and both exact crops reviewed. The recoil and return read clearly, but the initial back arch and vertical bob undermine grounded weight. F8 makes the head/neck attachment look separated and F24 exposes a wide jagged inner-cloth tear, plus a long neck insert and shoulder gap. Evidence: [film](../../hymotion/v3/stagger_s137.mp4), [contact sheet](../../hymotion/v3/stagger_s137_sheet.jpg), [audit](../../hymotion/v3/stagger_s137_audit.json), [F8 crop](../../hymotion/v3/stagger_s137_crop_F8.png), [F24 crop](../../hymotion/v3/stagger_s137_crop_F24.png).

**stagger_s271: REJECT.** Corrected film: all 30 frames and both exact crops reviewed. The most compact recoil of this set, but the wide stance bobs above the floor and returns to a deep crouch. Both exact endpoint crops show a large jagged split through the inner robe, an open blue shoulder seam and the awkward neck graft. Visual defects rule it out despite readable recoil. Evidence: [film](../../hymotion/v3/stagger_s271.mp4), [contact sheet](../../hymotion/v3/stagger_s271_sheet.jpg), [audit](../../hymotion/v3/stagger_s271_audit.json), [F1 crop](../../hymotion/v3/stagger_s271_crop_F1.png), [F30 crop](../../hymotion/v3/stagger_s271_crop_F30.png).

**death_s42: REJECT.** Corrected film: All 75 native frames and both exact crops reviewed. Knees-to-forward-collapse outline is present, but the opening floats, the recoil arches the head behind an exposed block-like neck insert, and the prone finish holds a raised tent of cloth/legs rather than settling convincingly. F7/F5 show open flank armor strips and fragmented inner cloth. Evidence: [film](../../hymotion/v3/death_s42.mp4), [contact sheet](../../hymotion/v3/death_s42_sheet.jpg), [audit](../../hymotion/v3/death_s42_audit.json), [F5 crop](../../hymotion/v3/death_s42_crop_F5.png), [F7 crop](../../hymotion/v3/death_s42_crop_F7.png).

**death_s137: REJECT.** Corrected film: All 75 native frames and both exact crops reviewed. A backward reach leads to kneeling and forward collapse, then a long static finish. The opening is airborne and the cape remains rigidly raised at the end. F6 exposes a neck stump with the head behind the torso and open flank armor; F37 has an open blue shoulder seam and separated-looking collar/neck. Evidence: [film](../../hymotion/v3/death_s137.mp4), [contact sheet](../../hymotion/v3/death_s137_sheet.jpg), [audit](../../hymotion/v3/death_s137_audit.json), [F6 crop](../../hymotion/v3/death_s137_crop_F6.png), [F37 crop](../../hymotion/v3/death_s137_crop_F37.png).

**death_s271: REJECT.** Corrected film: All 75 native frames and both exact crops reviewed. The knees and forward fall read, but an initial floating back arch hides the head behind an exposed neck insert. The last third freezes in a push-up-like collapsed pose with raised cloth. F8 has large black flank holes and F41 has an open back/shoulder armor gap and torn inner cape. These visible defects rule it out. Evidence: [film](../../hymotion/v3/death_s271.mp4), [contact sheet](../../hymotion/v3/death_s271_sheet.jpg), [audit](../../hymotion/v3/death_s271_audit.json), [F8 crop](../../hymotion/v3/death_s271_crop_F8.png), [F41 crop](../../hymotion/v3/death_s271_crop_F41.png).

## Final role table

| Role | Final status |
|---|---|
| sword_slash_r | Published from Round 2; accepted in Step 0 |
| parry_stance | Rejected in Step 0: visible torso/skirt defects |
| idle_low_hang | Rejected: no visually acceptable candidate; reasons above |
| stalk_walk | Rejected: no visually acceptable candidate; reasons above |
| x_combo | Rejected: no visually acceptable candidate; reasons above |
| horizontal_sweep | Rejected: no visually acceptable candidate; reasons above |
| jump_lunge | Rejected: no visually acceptable candidate; reasons above |
| rising_spin | Rejected: no visually acceptable candidate; reasons above |
| the_pause | Rejected: no visually acceptable candidate; reasons above |
| stagger | Rejected: no visually acceptable candidate; reasons above |
| death | Rejected: no visually acceptable candidate; reasons above |

Existing `Combat_Stance` is retained. Rejected candidates remain in separate work files under `models/hymotion_v3/`; they are not production clips.

## Publication, heroes, and limitations

**Published result: one additional clip, `sword_slash_r`, alongside the existing `Combat_Stance`. All 27 HY-Motion candidates were rejected; the nine requested new roles remain unavailable.** This is a completed generation/audit/rejection pass, not a production-ready Phase-1 moveset.

The final Blender and GLB remain the Step-0 publication on black-sky. All accepted clips passed its GLB round-trip: two names, 51/46 native frames at 30 fps, all 24 bones and their hierarchy, normalized skin weights, and maximum rest-joint error 0.0326 mm. Final SHA-256 checks confirm both published files and both original `_prev` backups are unchanged. No second promotion was needed because no HY candidate was accepted. See [publication receipt](../../hymotion/v3/step0_publish.json), [round-trip receipt](../../hymotion/v3/step0_roundtrip.json), and [final hash verification](../../hymotion/v3/final_publication_check.json).

All 27 corrected bakes passed an independent comparison of every world-space root sample against scaled, smoothed NPZ translation plus the one constant grounding shift: maximum error **0.00112 mm** over **1,620 frames**. This checks translation fidelity; it does not certify believable foot contact. See [root validation](../../hymotion/v3/root_validation.json).

All 27 candidates pass the relaxed p99 stretch ceiling, but only 11 pass every numeric collision/floor gate. None passes the visual and choreography review. The numeric p99 measures edge stretching, not pre-existing holes, exposed attachment geometry or cloth behaving like rigid panels. Several death/lunge/stagger clips also drive the rigidly held blade deeply below the floor; exact depths are in the table. The spin hip-yaw proxy supports the visible failures: s42 winds/unwinds (221 degree range), s137 makes about two fast turns (net -711 degrees; peak 3.52 turns/s), and s271 winds/unwinds (334 degree range). These are torso orientation diagnostics, not measurements of the blade path; [source-motion statistics](../../hymotion/v3/source_motion_stats.json) preserve the values.

Hero renders at 1200×1800, 48 samples, Cycles/OptiX were inspected directly in all six views. With no accepted `idle_low_hang`, its seed-42 frame-1 renders are explicitly marked **REJECTED diagnostics**: [front](../../hymotion/v3/hero_REJECTED_idle_low_hang_s42_front.png), [three-quarter](../../hymotion/v3/hero_REJECTED_idle_low_hang_s42_three_quarter.png), [side](../../hymotion/v3/hero_REJECTED_idle_low_hang_s42_side.png). They show a bowed head, oversized exposed neck insert, open back armor and pointed boots. They are not approved hero art.

The retained `Combat_Stance` frame-1 renders are supplied as a clearly named fallback: [front](../../hymotion/v3/hero_Combat_Stance_front.png), [three-quarter](../../hymotion/v3/hero_Combat_Stance_three_quarter.png), [side](../../hymotion/v3/hero_Combat_Stance_side.png). These also reveal existing large rear armor gaps, an inner-robe tear and the conspicuous neck graft. Retaining this existing clip does not certify the underlying V3 mesh as visually finished. View names denote fixed studio camera positions; character heading differs by action. [Hero receipt](../../hymotion/v3/heroes.json) records the fallback explicitly.

The next useful work is repair of V3 neck attachment, armor/robe surface continuity and foot-contact retargeting, followed by tightly directed choreography. Additional seeds alone will not repair those mesh and rig defects. Loop closure was not polished or certified for the rejected idle/walk clips, and no rejected action was promoted under a role name.

The ComfyUI process started by this run was stopped after generation; [shutdown receipt](../../hymotion/v3/comfy_shutdown.json). All ComfyUI, Blender, ffmpeg and ffprobe work ran on black-sky. No git commands were used; Ollama/vLLM were untouched.


## Evidence inventory

Completed 27 candidates / 1620 native frames: NPZ, per-seed Blender work file, all-frame audit, root-tracking MP4, contact sheet, complete chronological frame pages and both worst-stretch crops. Calibration files are excluded from these counts.

All new scripts are `scripts/astra_hym_*.py`. Main run log: `renders/astra/char2/codex_hym.log`. Machine-readable decisions: `renders/hymotion/v3/verdicts.json`. Canonical Blender/GLB and per-seed Blender files reside on black-sky; review evidence and this report are mirrored to the Mac.
