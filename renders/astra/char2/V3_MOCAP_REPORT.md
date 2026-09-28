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
