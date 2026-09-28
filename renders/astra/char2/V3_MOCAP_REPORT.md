# Godwyn V3 Meshy Mocap and Head-Attachment Report

## Result

The head attachment is materially improved and the canonical V3 has been republished with a rigid `Head`-driven head/hair object, a rigid `neck`-driven collar-interior NeckBlend, the sword still rigidly bound to `RightHand`, and one accepted Meshy action: `Combat_Stance` (51 frames at 30 fps).

The motion-library result is intentionally conservative. All 15 supplied GLBs were independently imported, retargeted, mechanically audited, rendered, and visually reviewed, but 14 were rejected. Nine fail at least one hard geometry gate. Five more pass the stated four hard gates but look visibly unsuitable on this character (airborne/gliding, nearly horizontal, out of frame, or lacking boss-scale weight). The canonical GLB therefore does not pretend to contain a complete SPEC moveset.

Published files on black-sky:

- `models/astra_character_v3.blend` — SHA-256 `49ff778d2279723230a6c9bdc1ebd2d423d67d7db58f746aa19544e3669b5a72`
- `models/astra_character_v3.glb` — SHA-256 `2aeb5782c4736660a58bd867737e0c5c9f3c7f4fb50e2b728f1ae753d94443e7`
- `models/astra_character_v3_prev.blend` — preserved original SHA-256 `e254ac97530c265ee1ac36b659f4d5ae752e8d27ec6842254e8b79277ca2abc9`
- `models/astra_character_v3_prev.glb` — preserved original SHA-256 `e2577625e35af133ef3fe0e240016e59108a10e9453430c4a58d4ca95e6b9fe9`

No Git commit or push was made.

## Source-clip integrity and timing

All 15 input GLBs have different complete SHA-256 hashes. Each imports as one animation on the same 24-name bone set used by V3. File order differs from the target bone order, but the set is exact. The largest source-to-V3 rest-joint position difference is 23.158 mm; every transfer therefore used each skeleton's own rest pose, copied per-bone pose rotation deltas by name, preserved `Hips` translation, and suppressed non-root translation channels that would otherwise pull the slightly different rests apart.

| Clip | SHA-256 prefix | Frames @ 30 fps | Max rest difference | Root travel | Source mode |
|---|---:|---:|---:|---:|---|
| Combat_Stance | `65a24d28d1c` | 51 | 23.060 mm | 0.067 mm | in-place |
| Walk_Fight_Forward | `5573af77debfd` | 53 | 23.158 mm | 0.002 mm | in-place |
| Attack | `0c20f5fcb357` | 85 | 18.263 mm | 1.515 mm | in-place |
| Left_Slash | `93313666c011` | 96 | 18.917 mm | 1.810 mm | in-place |
| Right_Hand_Sword_Slash | `976ffc04777c` | 46 | 18.803 mm | 3.086 mm | in-place |
| Double_Combo_Attack | `05bb3c8889d8` | 86 | 12.087 mm | 2.780 m | root motion |
| Triple_Combo_Attack | `6c3422cef209` | 131 | 16.272 mm | 3.449 m | root motion |
| Sword_Judgment | `57877f8221e0` | 132 | 20.493 mm | 2.243 m | root motion |
| Reaping_Swing | `27644b14a0f2` | 179 | 21.443 mm | 1.280 m | root motion |
| Rightward_Spin | `2c3182a711a3` | 241 | 19.035 mm | 2.165 mm | in-place |
| Basic_Jump | `ce89e1431686` | 178 | 10.418 mm | 2.621 m | root motion |
| Roll_Dodge | `c81eed21c305` | 56 | 16.887 mm | 7.145 m | root motion |
| Sword_Parry | `bead370e92b4` | 57 | 16.753 mm | 0.574 mm | in-place |
| Hit_Reaction | `3b62b63f82ee` | 50 | 21.865 mm | 2.178 m | root motion |
| Dead | `1b4a541be742` | 90 | 7.393 mm | 1.751 m | root motion |

The source files are distinct, not duplicate containers with renamed actions. The full hashes and GLB animation accessor timing are in `astra_v3m_probe.json`.

## Head diagnosis and correction

The original problem was not a missing parent. The donor head/hair was already rigidly weighted to `Head`; it read as detached because it sat high and slightly large, retained a long faceted donor neck/hair underside inside the open gorget, and had no separate neck-driven bridge. The original measured full-head bounds were Z 2.5599–3.1600 m. The jaw-underside estimate was Z 2.70218 m, while the stored low inner-collar reference was Z 2.46416 m: a raw 238.0 mm vertical interval. That low rim reference is intentionally conservative and is not the nearest visible collar point, but it correctly exposed the missing interior bridge. The original head-above-jaw/body-height ratio was 0.14488, or about 1:6.90, versus the concept target of about 1:7.5.

The correction:

- uniformly scaled the head/hair to 0.94 about the `Head` rest anchor;
- lowered it 20 mm;
- kept the entire surviving head/hair rigidly weighted only to `Head`;
- created a tapered five-ring NeckBlend from Z 2.485 to 2.690 m and rigidly weighted it only to `neck`;
- removed 17 residual source-head shell faces from `char1`;
- removed 49,247 hidden donor neck/hair faces below the gorget in two measured passes.

The corrected jaw estimate is Z 2.69154 m. The NeckBlend reaches Z 2.690 m, leaving a 1.54 mm jaw-to-filled-interior vertical clearance and no visible exposed neck column in the approved stance. The transformed full-head crown is approximately Z 3.12189 m; head-above-jaw/body height is approximately 0.13785, or 1:7.25. This is much closer to the 1:7.5 concept, although still about 3.4% larger by this metric.

The accepted stance has zero head/hair-versus-collar/pauldron triangle pairs at frame 1 and its most extended frame, F33. The audit also confirms the final bindings: head=`Head`, NeckBlend=`neck`, sword=`RightHand`.

Visual caveat: the seated jaw and filled collar are clearly better than the before render, but this remains a rough donor graft. The back hair ends abruptly and has a few jagged/floating nape fragments in close profile. The source body's rear torso and robe also contain large pre-existing open/fragmented regions, especially visible in the side hero. These are not hidden in the evidence renders.

## Mechanical audit

Body stretch and soles were sampled on every integer frame. Sword/head, sword/body, and blade/floor were also evaluated on every integer frame. Head/hair versus collar/pauldrons follows the brief's attachment check at frame 1 and the automatically selected most-extended frame. `Head pairs` below is the sum at those two sampled attachment poses. A negative blade Z is penetration below the Z=0 floor. Sword/floor was reported but was not one of the four enumerated hard gates; it was still used in the visual acceptance decision.

| Clip | Stretch p99 | Lowest sole | Head pairs | Sword/head frames | Sword/body frames | Lowest blade | Hard gates |
|---|---:|---:|---:|---:|---:|---:|---|
| Combat_Stance | 1.5091 | +49.1 mm | 0 | 0 | 0 | +970.6 mm | PASS |
| Walk_Fight_Forward | 1.4463 | -4.0 mm | 0 | 0 | 0 | +2416.3 mm | PASS |
| Attack | 1.5655 | -4.0 mm | 2 | 0 | 0 | -76.3 mm | FAIL |
| Left_Slash | 1.5819 | +0.3 mm | 3 | 0 | 0 | +606.2 mm | FAIL |
| Right_Hand_Sword_Slash | 1.5741 | -4.0 mm | 2 | 0 | 0 | +965.3 mm | FAIL |
| Double_Combo_Attack | 1.5641 | -4.0 mm | 9 | 0 | 0 | -100.8 mm | FAIL |
| Triple_Combo_Attack | 1.5750 | -4.0 mm | 0 | 0 | 0 | +68.7 mm | PASS |
| Sword_Judgment | 1.5786 | -4.0 mm | 0 | 0 | 0 | +835.2 mm | PASS |
| Reaping_Swing | 1.5721 | -1.2 mm | 101 | 0 | 0 | +305.6 mm | FAIL |
| Rightward_Spin | 1.5695 | -4.0 mm | 5 | 0 | 0 | -102.9 mm | FAIL |
| Basic_Jump | 1.5705 | -4.0 mm | 530 | 0 | 0 | +412.7 mm | FAIL |
| Roll_Dodge | 1.5850 | -4.0 mm | 0 | 0 | 0 | -442.3 mm | PASS* |
| Sword_Parry | 1.5702 | -4.0 mm | 0 | 0 | 0 | +1774.7 mm | PASS |
| Hit_Reaction | 1.5580 | -4.0 mm | 100 | 0 | 0 | +3014.0 mm | FAIL |
| Dead | 1.5645 | -4.0 mm | 5 | 0 | 0 | -501.7 mm | FAIL |

`Roll_Dodge` passes the four enumerated gates but its blade penetrates the floor by 442.3 mm, so it is not accepted. No clip drives the blade through the body or head/hair. `Right_Hand_Sword_Slash` was the best-looking attack; two sequential clip-local head lifts totaling 20 mm still left the same two jaw/gorget triangle pairs at its extended frame, so it was rejected rather than weakening the attachment or falsifying the gate.

The initial retargets exceeded the 1.6 stretch gate on most actions. Rejected review actions were iteratively reduced toward their rest rotations and received constant root-height corrections where necessary; the accepted `Combat_Stance` required neither rotation reduction nor floor lift. The final audit values above are the post-correction measurements. This processing preserves frame timing and horizontal root paths, but the rejected films should be treated as compatibility studies, not pristine source-mocap previews.

## Visual review, clip by clip

- **Combat_Stance — ACCEPT as idle/low-hang placeholder.** Grounded and mechanically clean, with a stable silhouette and restrained motion. It is usable, but not a great final boss idle: the open off-hand and forward reach feel generic and slightly supplicant rather than regal or threatening.
- **Walk_Fight_Forward — DROP.** It passes the hard gates, but reads as a hovering side-lean/glide. Foot contact lacks weight and the body never develops a convincing stalking cadence.
- **Attack — DROP.** A flashy airborne cartwheel/dive rather than a readable grounded initiator. It also has two head/armor pairs and 76.3 mm of blade/floor penetration.
- **Left_Slash — DROP.** The body remains dramatically canted and airborne through much of the motion. The slash is not readable as a controlled horizontal boss sweep, and it has three head/armor pairs.
- **Right_Hand_Sword_Slash — DROP, despite being the best offensive candidate.** The wind-up, diagonal cut, and recovery are the clearest in the batch and mostly grounded. The unresolved two-pair jaw/gorget collision fails the hard gate; the attempted 20 mm clip-only head lift did not clear it.
- **Double_Combo_Attack — DROP.** Reads as repeated aerial tumbling, not an authored X-combo. Nine head/armor pairs and 100.8 mm blade/floor penetration reinforce the visual rejection.
- **Triple_Combo_Attack — DROP.** It technically passes the four gates and is the closest source for a longer sequence, but the framing exposes very large vertical/root excursions, including an out-of-frame airborne phase. It does not read as a deliberate three-beat sovereign combo on this body.
- **Sword_Judgment — DROP.** Mechanically passes, but the overhead/jump motion is overcranked, intermittently exits the useful camera volume, and lacks the planted mass expected of a sacred cleave.
- **Reaping_Swing — DROP.** An airborne pinwheel rather than a controlled wide reap; 101 head/armor pairs.
- **Rightward_Spin — DROP.** Long acrobatic roll/spin with repeated inverted poses, five head/armor pairs, and 102.9 mm blade/floor penetration. Not a grounded rising spin.
- **Basic_Jump — DROP.** Starts visibly suspended, leaves the frame at the apex, and has 530 head/armor triangle pairs at the attachment samples. It is not a safe jump-lunge base.
- **Roll_Dodge — DROP.** The tumble is legible, but too gymnastic for the silhouette and drives the sword 442.3 mm through the floor.
- **Sword_Parry — DROP.** Passes the automated gates, yet remains in a steep airborne lean for nearly the whole clip. There is no planted counterweight or readable parry beat.
- **Hit_Reaction — DROP.** Launches the character upward and out of frame instead of producing a compact stagger; 100 head/armor pairs.
- **Dead — DROP.** Begins like an upright sway and becomes a levitating horizontal dive, not a settled death. It also has five head/armor pairs and 501.7 mm blade/floor penetration.

## SPEC role recommendation

| SPEC role | Recommendation |
|---|---|
| Idle | `Combat_Stance` — accepted only as a placeholder |
| Walk / stalk | none; drop `Walk_Fight_Forward` |
| X-combo initiators | none; `Right_Hand_Sword_Slash` is the closest single cut but fails attachment clearance |
| Spin | none; drop `Rightward_Spin` |
| Jump lunge | none; drop `Basic_Jump` |
| Dodge | none; drop `Roll_Dodge` |
| Stagger | none; drop `Hit_Reaction` |
| Death | none; drop `Dead` |

A replacement capture/search should prioritize grounded root orientation, planted contacts, modest vertical travel, and sword-aware authored motion. The current batch is dominated by acrobatic whole-body rotations that conflict with this tall armored/robed silhouette.

## Render and film verification

Every clip has a `renders/astra/v3m/<clip>.mp4` and `<clip>_contact_sheet.png`. Remote `ffprobe` verified every film at 768×768, 30/1 fps, with an exact video-frame count matching the source count in the first table. The review films were rendered in Cycles on black-sky with OptiX at two samples on every other source frame, then motion-interpolated to 30 fps and padded by duplicating the final frame where necessary to preserve the exact inclusive source count. This is sufficient for motion review but not final cinematic-quality animation output.

Final heroes were rendered from the published canonical blend at frame 1 of `Combat_Stance`, 1200×1800, 128 Cycles samples, OptiX. `hero_comparison_sheet.png` places the model next to `body-concepts/god_A.png`. I inspected all 15 contact sheets and the six final hero/comparison images directly.

## GLB round-trip and deliverables

The published GLB round-trips with exactly one action, `Combat_Stance`, at 51 frames when imported into a 30 fps scene. It has the exact 24-bone names and hierarchy, one 24-joint skin, zero unweighted/bad-sum skinned vertices, and a maximum rest-joint position round-trip error of 0.0326 mm.

Primary evidence:

- `renders/astra/char2/astra_v3m_probe.json` — source hashes, clip timing, skeleton and rest-pose comparison
- `renders/astra/char2/astra_v3m_build.json` — head fix and per-clip retarget details
- `renders/astra/char2/meshy_v3m_audit.json` — full mechanical audit
- `renders/astra/char2/astra_v3m_publish.json` — promotion hashes, backup hashes, bindings, and export details
- `renders/astra/char2/astra_v3m_roundtrip.json` — independent GLB re-import checks
- `renders/astra/char2/codex_v3m.log` — command/run log
- `renders/astra/v3m/` — 15 films, 15 contact sheets, before images, final heroes, and concept comparison

The `.blend` and `.glb` deliverables remain on black-sky. Evidence images, films, JSON, report, and log were synchronized back to the Mac workspace.

---

## Round 2 — world-space retarget, September 28, 2026

This section supersedes the first-pass motion verdicts above. Round 2 rebuilt all 15 actions from the just-published fist-body source (`49ff778d…` blend), using exact source-bone world orientations—including roll—in parent-first order. `Hips` world position is the source position minus the source/target rest offset. No local-delta rotation transfer or per-frame floor clamping remains.

### Outcome

Only `Combat_Stance` passes every inherited hard gate and is published. `Right_Hand_Sword_Slash`, `Sword_Parry`, and `Hit_Reaction` look usable in the films and pass the floor and visible-collision checks, but their body edge-stretch p99 values are 1.7530, 1.8546, and 1.9240, respectively, above the hard 1.6 ceiling. They were therefore not retained in the final canonical asset. A temporary four-action promotion was replaced before delivery; it was not kept as `_prev`.

Final publication:

- `models/astra_character_v3.blend` — SHA-256 `32afac85f2676bfb4ab5db22156bfee14b9aae1844d0b3a12aa1977a117c1ba0`
- `models/astra_character_v3.glb` — SHA-256 `351a3ef83baee9ed4b315f1c042f76a72846af905680f17a51bf75b08b4b03ab`
- `models/astra_character_v3_prev.blend` — Round-1 canonical, SHA-256 `49ff778d2279723230a6c9bdc1ebd2d423d67d7db58f746aa19544e3669b5a72`
- `models/astra_character_v3_prev.glb` — Round-1 canonical, SHA-256 `2aeb5782c4736660a58bd867737e0c5c9f3c7f4fb50e2b728f1ae753d94443e7`
- `models/astra_character_v3_pre_mocap.*` — preserved original pair, SHA-256 prefixes `e254ac97…` / `e2577625…`

No Git commit or push was made.

### Input integrity and frame counts

The 15 source GLBs were re-hashed on black-sky. All 15 complete SHA-256 values are unique; there are no renamed duplicate containers. Their exact imported inclusive frame counts at 30 fps are:

| Clip | SHA-256 prefix | Frames |
|---|---:|---:|
| Combat_Stance | `65a24d28d1c` | 51 |
| Walk_Fight_Forward | `5573af77debfd` | 53 |
| Attack | `0c20f5fcb357` | 85 |
| Left_Slash | `93313666c011` | 96 |
| Right_Hand_Sword_Slash | `976ffc04777c` | 46 |
| Double_Combo_Attack | `05bb3c8889d8` | 86 |
| Triple_Combo_Attack | `6c3422cef209` | 131 |
| Sword_Judgment | `57877f8221e0` | 132 |
| Reaping_Swing | `27644b14a0f2` | 179 |
| Rightward_Spin | `2c3182a711a3` | 241 |
| Basic_Jump | `ce89e1431686` | 178 |
| Roll_Dodge | `c81eed21c305` | 56 |
| Sword_Parry | `bead370e92b4` | 57 |
| Hit_Reaction | `3b62b63f82ee` | 50 |
| Dead | `1b4a541be742` | 90 |

### Retarget and grounding measurements

Every reconstructed bone orientation matches the evaluated source world orientation to the audit's numeric precision: maximum reported error is `0.000000°` on every clip and every bone. Maximum `Hips` world-position error across the set is 0.000972 mm. One constant Z correction per clip brings the lowest sampled sole to Z=0; it does not manufacture per-frame contact. The last column exposes how few genuinely planted frames many acrobatic clips contain.

| Clip | Frames | Max orient error | Max root error | Constant Z shift | Sole before | Sole after | Frames within 5 mm |
|---|---:|---:|---:|---:|---:|---:|---:|
| Combat_Stance | 51 | 0.000000° | 0.000137 mm | -39.273 mm | +39.273 mm | -0.000008 mm | 30 |
| Walk_Fight_Forward | 53 | 0.000000° | 0.000120 mm | +31.355 mm | -31.355 mm | +0.000093 mm | 2 |
| Attack | 85 | 0.000000° | 0.000169 mm | +291.568 mm | -291.568 mm | 0.000000 mm | 3 |
| Left_Slash | 96 | 0.000000° | 0.000124 mm | -151.793 mm | +151.793 mm | -0.000042 mm | 12 |
| Right_Hand_Sword_Slash | 46 | 0.000000° | 0.000137 mm | +38.572 mm | -38.572 mm | -0.000044 mm | 5 |
| Double_Combo_Attack | 86 | 0.000000° | 0.000492 mm | -100.418 mm | +100.418 mm | -0.000053 mm | 2 |
| Triple_Combo_Attack | 131 | 0.000000° | 0.000716 mm | +175.538 mm | -175.538 mm | +0.000023 mm | 3 |
| Sword_Judgment | 132 | 0.000000° | 0.000478 mm | +182.944 mm | -182.944 mm | +0.000206 mm | 2 |
| Reaping_Swing | 179 | 0.000000° | 0.000206 mm | -14.513 mm | +14.513 mm | +0.000017 mm | 3 |
| Rightward_Spin | 241 | 0.000000° | 0.000481 mm | +599.299 mm | -599.299 mm | +0.000076 mm | 2 |
| Basic_Jump | 178 | 0.000000° | 0.000533 mm | +85.962 mm | -85.962 mm | -0.000107 mm | 11 |
| Roll_Dodge | 56 | 0.000000° | 0.000972 mm | +525.529 mm | -525.529 mm | -0.000026 mm | 1 |
| Sword_Parry | 57 | 0.000000° | 0.000123 mm | -166.613 mm | +166.613 mm | +0.000013 mm | 33 |
| Hit_Reaction | 50 | 0.000000° | 0.000477 mm | +6.090 mm | -6.090 mm | -0.000035 mm | 1 |
| Dead | 90 | 0.000000° | 0.000289 mm | +178.471 mm | -178.471 mm | -0.000162 mm | 3 |

### Head, hair, collar, sash, and hem

- The previous head was 34.2031 mm below the measured front-rim reference. It was lifted 64.2031 mm, placing the chin 29.9999 mm above the rim—inside the requested 20–40 mm range—with the mouth and full jaw visible.
- Head scale remains 1.000; no scale adjustment was needed. NeckBlend ends 5.9999 mm below the chin, far below the 60 mm exposed-neck ceiling.
- Weld-aware topology found 41 hair-bearing components. Thirty-five components under 40 vertices were removed, totaling 184 vertices. No surviving component is farther than 30 mm from the main hair geometry.
- The body has hundreds of pre-existing Meshy boundary components. Round 2 added 324 small, exactly boundary-local weighted caps (1,247 vertices): 103 upper-torso, 217 belt, and 4 hem faces. Broad liner and large-cycle experiments were rendered, judged worse, and removed.
- Important visual limitation: the large side/rear torso and skirt discontinuities are still visible in profile. They are source-mesh fragmentation, not retarget stretch. The attempted liners read as obvious smooth primitives, so the final asset preserves the honest source defect instead of shipping a conspicuous fake panel. This model still needs a proper garment remodel for a clean side/back hero view.

### Full Round-2 mechanical audit

Every integer frame of all 15 actions was audited. Visible exterior head/hair-versus-collar/pauldron pairs are zero for every clip; central jaw/gorget interior overlap is intentionally allowed. Sword/head overlap is also zero throughout. Negative blade Z is floor penetration.

| Clip | Stretch p99 | Sole min | Visible head pairs | Sword/head frames | Sword/body frames | Blade min |
|---|---:|---:|---:|---:|---:|---:|
| Combat_Stance | 1.5119 | -0.000 mm | 0 | 0 | 0 | +930.4 mm |
| Walk_Fight_Forward | 1.8575 | +0.000 mm | 0 | 0 | 0 | +1831.6 mm |
| Attack | 2.2382 | +0.000 mm | 0 | 0 | 0 | -566.0 mm |
| Left_Slash | 2.1784 | -0.000 mm | 0 | 0 | 1 | +508.3 mm |
| Right_Hand_Sword_Slash | 1.7530 | -0.000 mm | 0 | 0 | 0 | +1037.7 mm |
| Double_Combo_Attack | 2.1803 | -0.000 mm | 0 | 0 | 1 | -648.6 mm |
| Triple_Combo_Attack | 2.0318 | +0.000 mm | 0 | 0 | 0 | -216.5 mm |
| Sword_Judgment | 1.7793 | +0.000 mm | 0 | 0 | 0 | +653.9 mm |
| Reaping_Swing | 2.1399 | +0.000 mm | 0 | 0 | 0 | +287.3 mm |
| Rightward_Spin | 1.9342 | +0.000 mm | 0 | 0 | 7 | -101.6 mm |
| Basic_Jump | 2.1744 | -0.000 mm | 0 | 0 | 0 | -1269.3 mm |
| Roll_Dodge | 1.8381 | -0.000 mm | 0 | 0 | 0 | -331.6 mm |
| Sword_Parry | 1.8546 | +0.000 mm | 0 | 0 | 0 | +1848.6 mm |
| Hit_Reaction | 1.9240 | -0.000 mm | 0 | 0 | 0 | +2084.9 mm |
| Dead | 1.9368 | -0.000 mm | 0 | 0 | 4 | -286.2 mm |

Root lifting cannot repair the seven negative-blade cases without floating their already-grounded soles. Attack, Double Combo, Triple Combo, Rightward Spin, Basic Jump, Roll Dodge, and Dead were dropped rather than receiving destructive wrist edits or dishonest root offsets. Left Slash, Double Combo, Rightward Spin, and Dead also have sword/body contacts.

### Direct film review and final verdicts

I directly inspected every Round-2 root-follow film plus both contact-sheet views. The labels below distinguish a bad retarget from a source clip that is simply wrong for this character. The world-space reconstruction fixed the old arbitrary cant/attachment collisions, but it did not turn acrobatic source motion into grounded boss choreography.

| Clip | Verdict | Own-eye assessment |
|---|---|---|
| Combat_Stance | **ACCEPT** | Grounded, stable, clean silhouette; usable low-hang idle placeholder, though the open off-hand is still generic rather than regal. |
| Walk_Fight_Forward | DROP | Still reads airborne/hovering for most of the cycle; only two frames reach the 5 mm contact band. Source-motion mismatch, not retarget cant. |
| Attack | DROP | Acrobatic leap with a suspended start and 566 mm blade/floor penetration; not a readable grounded initiator. |
| Left_Slash | DROP | Wild backbend/acrobatic sweep with visible garment stress and one sword/body overlap. |
| Right_Hand_Sword_Slash | DROP (best attack) | The clearest, most readable grounded cut and visually usable, but p99 1.7530 fails the inherited 1.6 hard gate. |
| Double_Combo_Attack | DROP | Floats/tumbles through the sequence; one sword/body frame and 648.6 mm blade penetration. |
| Triple_Combo_Attack | DROP | Most promising long combo by eye, but includes a pronounced leap, p99 2.0318, and 216.5 mm blade penetration. |
| Sword_Judgment | DROP | Oversized jump/sacred-slam motion repeatedly exceeds a useful boss silhouette; p99 1.7793. |
| Reaping_Swing | DROP | Broad floating pinwheel with visible cloth/body stress; not a controlled reap. |
| Rightward_Spin | DROP | Prolonged airborne tumble, seven sword/body frames, and 101.6 mm blade penetration. |
| Basic_Jump | DROP | Huge jump leaves the useful frame and drives the blade 1.269 m below the floor. |
| Roll_Dodge | DROP | A 7.15 m gymnastic airborne tumble rather than a compact dodge; 331.6 mm blade penetration. |
| Sword_Parry | DROP (visual reserve) | Grounded and readable as a held parry stance, but p99 1.8546 fails the hard stretch gate. |
| Hit_Reaction | DROP (visual reserve) | Readable knockback/stagger and clean collisions, but only one planted frame and p99 1.9240. |
| Dead | DROP | Clear falling/death intent, but four sword/body frames, 286.2 mm blade penetration, and p99 1.9368. |

### Films, cameras, and final renders

`renders/astra/v3m_round2/` contains 15 MP4s, 15 root-follow sheets, and 15 static-wide contact sheets. Every MP4 was independently checked with `ffprobe` on black-sky: 768×768, 30 fps, and exactly the source frame count in the input table. XY root-follow keeps traveling actions centered while preserving visible vertical motion; the static-wide sheet exposes total root travel.

Final 1200×1800 hero views and the collar/face close-ups are in `renders/astra/v3m_round2_final/`. They are rendered from the accepted Round-2 WIP state with inherited body-surface cap materials. The face framing is centered on the actual donor head. Direct inspection confirms the mouth/jaw clearance and removal of the small floating hair slivers; it also confirms the unresolved source garment fragmentation described above.

### Final GLB round-trip

The final GLB re-import contains exactly `Combat_Stance`, 51 frames at 30 fps. It preserves all 24 bone names and hierarchy, a 24-joint skin, and zero unweighted or bad-sum skinned vertices. Maximum rest-joint position error is 0.0326 mm.

Round-2 evidence:

- `renders/astra/char2/astra_v3m_round2_build.json` — world-space transfer, head/hair repair, per-clip root offsets and contact rows
- `renders/astra/char2/meshy_v3m_round2_audit.json` — all-frame, all-clip mechanical and collision audit
- `renders/astra/char2/astra_v3m_round2_publish.json` — final promotion hashes and backup lineage
- `renders/astra/char2/astra_v3m_round2_roundtrip.json` — independent GLB re-import result
- `renders/astra/char2/codex_v3m_round2.log` — complete run log
- `renders/astra/v3m_round2/` — all films and both sheet types
- `renders/astra/v3m_round2_final/` — accepted hero and close-up evidence
