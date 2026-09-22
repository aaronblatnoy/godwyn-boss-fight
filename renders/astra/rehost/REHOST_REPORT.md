# Godwyn final-character move rehost report

## Result

PASS with disclosed residuals. All five finished actions are hosted on the published v2 character, preserve the 121-bone rest rig, pass the exact-transfer gate before any permitted rehost-only clearance correction, pass the regenerated grip and head/hair/collar acceptance checks, render at their original frame counts, and package as fully decoded H.264/yuv420p MP4s.

All rendering and auditing ran on black-sky. The final evidence was generated with Blender 5.2.0 LTS and `/usr/bin/ffmpeg`; the Mac only orchestrated SSH jobs and received the small allowed evidence files.

The full-render attempt first tested `CUDA_VISIBLE_DEVICES=0/1`. Headless EEVEE loaded GPU 0 for both processes and left GPU 1 idle, so the second process was stopped and every full move was rendered serially, as required. No frame count or sample count was reduced.

## Input integrity and method

- Published character: `models/astra_character_v2.blend`, SHA-256 `c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386`.
- Frozen v2 base: `models/astra_move_character_base_v2.blend`, SHA-256 `c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386`.
- Preferred transfer method used for every move: retain the complete source staging scene, replace the old character with the full published v2 assembly, and copy the baked action exactly at the Blender action-data level without retargeting. The transfer verification is a transfer-time gate.
- Derived v2-only grip repairs and permitted cloth-floor/head-avoidance action corrections are retained in the new files only. Walk Stalk and Rising Spin received distal cloth-chain corrections; Rising Spin also received a four-channel neck envelope over F30–54 to clear the new head. Therefore the final corrected actions are not claimed byte-identical to their old-body sources. Protected published/base/old-body inputs were hash-checked unchanged after all work.
- The non-fatal Blender package add-on warning about optional `cattrs` appeared at startup on black-sky; every invoked audit/render script nevertheless completed with its asserted exit status and Blender quit normally.

## Structural sanity

| Move | Render frames | Bones | Assigned action | F-curves | Keys |
|---|---:|---:|---|---:|---:|
| idle_guard | 96 | 121 | `Astra_Move_idle_guard.002_OnChar2` | 847 | 326095 |
| walk_stalk | 72 | 121 | `Astra_Move_walk_stalk.002_OnChar2` | 847 | 244783 |
| lunge_thrust | 64 | 121 | `Astra_Move_lunge_thrust.002_OnChar2` | 847 | 214291 |
| rising_spin | 116 | 121 | `Astra_Move_rising_spin.002_OnChar2` | 847 | 390467 |
| xslash | 90 | 121 | `Astra_Godwyn_XSlash_V2_Final_Naturalness_OnChar2` | 847 | 307643 |

The final assembly contains both eyebrow meshes, nine skinned hair-control meshes, nine native curve objects, and nine portable strand meshes in every move. Binding assertions passed for every audited frame.

## Numeric evidence policy

Each per-move section gives the delivery-critical before/after values. `delivery_verification.json` additionally inventories **every finite numeric leaf** in the retained before/after motion JSONs (including per-frame and per-bone samples), reports equality/change counts and the largest delta, and embeds the compact motion, grip, surface, attack, head/hair/collar, and video checks. The original and regenerated full JSON evidence remains beside each move.

## idle_guard

Method: complete source staging scene retained; old character replaced by full published char2 assembly; action copied without retargeting. At the exact-transfer gate, the action digest was `b94e5fe764a84cd7d9a7f18f6ac22e3cbc8fbe9a0066a98e3b445c7bc273c877`; all 847 F-curves and 326095 keys transferred without retargeting, with rest-matrix and quarter-frame pose-matrix error both 0.0. No post-transfer action correction was required.

| Numeric check | Old body | Published v2 body |
|---|---:|---:|
| Numeric leaves in move physics audit | 3005 | 3220 |
| Common / exactly equal / changed numeric leaves | — | 3005 / 2863 / 142 |
| Largest absolute audit delta | — | 1.98499072e-05 (`anatomy[19].Left_wrist`) |
| Minimum sole clearance | 1.543 mm | 2.145 mm |
| Minimum cloth-floor clearance | 0.031 mm | 0.698 mm |
| Hand-local hilt drift | 0.000474 mm | 0.000474 mm |
| Evaluated sword-tip error | 0.000572 mm | 0.000572 mm |
| Closed-finger hand-local drift | 0.000905 mm | 0.000884 mm |
| Closed-finger vertices sampled | 2256 | 2263 |
| Exposed jaw/neck-to-gorget minimum | n/a (final head absent) | 13.396 mm |
| Blade-to-head minimum (conservative proxy) | n/a (final head absent) | 974.610 mm |
| Blade-to-hair minimum (conservative proxy) | n/a (final groom absent) | 481.644 mm |
| Exposed gorget/head intersection frames | n/a | 0 |
| Exact blade/head intersection frames | n/a | 0 |
| Decoded MP4 frames | n/a | 96 at 30/1 |

Head/hair/collar disposition: None introduced. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.

Final SHA-256: `fc24935c6e0b74722e73fc8a779487b12ae7aaf26bb3ee1d03d9cebad73919ce` (`models/astra_move_idle_guard_v2_wip.blend`); `0aa72b762c0846eaf527da5fb8806523b0454c450f5bc6b2c80cb494670481bf` (`renders/astra/rehost/idle_guard/idle_guard.mp4`).

## walk_stalk

Method: complete source staging scene retained; old character replaced by full published char2 assembly; action copied without retargeting. At the exact-transfer gate, the action digest was `15cd351ad4d01fc69371992078062e9eb59fd268e9a07c3e7e58b1b9f726108a`; all 847 F-curves and 244783 keys transferred without retargeting, with rest-matrix and quarter-frame pose-matrix error both 0.0. The final rehost then received these permitted derived-only action corrections: cloth_floor_action_correction.

| Numeric check | Old body | Published v2 body |
|---|---:|---:|
| Numeric leaves in move physics audit | 2676 | 2676 |
| Common / exactly equal / changed numeric leaves | — | 2676 / 2558 / 118 |
| Largest absolute audit delta | — | 1.11893233e-05 (`anatomy[18].Right_wrist`) |
| Minimum sole clearance | 1.672 mm | 1.883 mm |
| Minimum cloth-floor clearance | 0.946 mm | 1.033 mm |
| Hand-local hilt drift | 0.000461 mm | 0.000461 mm |
| Evaluated sword-tip error | 0.000571 mm | 0.000571 mm |
| Closed-finger hand-local drift | 0.000848 mm | 0.000840 mm |
| Closed-finger vertices sampled | 2256 | 2263 |
| Exposed jaw/neck-to-gorget minimum | n/a (final head absent) | 16.567 mm |
| Blade-to-head minimum (conservative proxy) | n/a (final head absent) | 936.457 mm |
| Blade-to-hair minimum (conservative proxy) | n/a (final groom absent) | 443.071 mm |
| Exposed gorget/head intersection frames | n/a | 0 |
| Exact blade/head intersection frames | n/a | 0 |
| Decoded MP4 frames | n/a | 72 at 30/1 |

Head/hair/collar disposition: None introduced. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.

Final SHA-256: `164ef0e4705d43c7b1230b51ede372d1549024f4b42be933ac39ac751db89e92` (`models/astra_move_walk_stalk_v2_wip.blend`); `5d8fcd002cb9f771017db9e8e9ffe1281bc46419807dd6005dd10fc6f72203a4` (`renders/astra/rehost/walk_stalk/walk_stalk.mp4`).

## lunge_thrust

Method: complete source staging scene retained; old character replaced by full published char2 assembly; action copied without retargeting. At the exact-transfer gate, the action digest was `06e6ed299462d7204ccdc39d0bd316bb5dca62832c0725f8bde71ca40150ccc8`; all 847 F-curves and 214291 keys transferred without retargeting, with rest-matrix and quarter-frame pose-matrix error both 0.0. No post-transfer action correction was required.

| Numeric check | Old body | Published v2 body |
|---|---:|---:|
| Numeric leaves in move physics audit | 2572 | 2572 |
| Common / exactly equal / changed numeric leaves | — | 2572 / 2422 / 150 |
| Largest absolute audit delta | — | 5.89456001e-05 (`anatomy[3].Right_wrist`) |
| Minimum sole clearance | 1.867 mm | 2.156 mm |
| Minimum cloth-floor clearance | 2.092 mm | 2.608 mm |
| Hand-local hilt drift | 0.000937 mm | 0.000937 mm |
| Evaluated sword-tip error | 0.000648 mm | 0.000648 mm |
| Closed-finger hand-local drift | 0.001203 mm | 0.001268 mm |
| Closed-finger vertices sampled | 2256 | 2263 |
| Exposed jaw/neck-to-gorget minimum | n/a (final head absent) | 12.387 mm |
| Blade-to-head minimum (conservative proxy) | n/a (final head absent) | 521.271 mm |
| Blade-to-hair minimum (conservative proxy) | n/a (final groom absent) | 157.317 mm |
| Exposed gorget/head intersection frames | n/a | 0 |
| Exact blade/head intersection frames | n/a | 0 |
| Decoded MP4 frames | n/a | 64 at 30/1 |

Head/hair/collar disposition: None introduced. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.

Final SHA-256: `b7a1d6a2fcb852f62217a313fb2f442c73e615660abbe143083ab7cf530ad352` (`models/astra_move_lunge_thrust_v2_wip.blend`); `ea1de282d635401bced923acbd1e8fb5b319e15eb9e078b8b25e5ef9a5a14c65` (`renders/astra/rehost/lunge_thrust/lunge_thrust.mp4`).

## rising_spin

Method: complete source staging scene retained; old character replaced by full published char2 assembly; action copied without retargeting. At the exact-transfer gate, the action digest was `084f7c7eda459c48e56a1a3b6912ac8cf4dbd85e60be47d34b6ae6c8dd51d6c0`; all 847 F-curves and 390467 keys transferred without retargeting, with rest-matrix and quarter-frame pose-matrix error both 0.0. The final rehost then received these permitted derived-only action corrections: cloth_floor_action_correction, head_avoidance_action_correction.

| Numeric check | Old body | Published v2 body |
|---|---:|---:|
| Numeric leaves in move physics audit | 3790 | 3789 |
| Common / exactly equal / changed numeric leaves | — | 3789 / 3076 / 713 |
| Largest absolute audit delta | — | 21 (`peaks.neck.peak_frame`) |
| Minimum sole clearance | 2.151 mm | 2.698 mm |
| Minimum cloth-floor clearance | 2.001 mm | 2.059 mm |
| Hand-local hilt drift | 0.000757 mm | 0.000757 mm |
| Evaluated sword-tip error | 0.000677 mm | 0.000677 mm |
| Closed-finger hand-local drift | 0.001049 mm | 0.001077 mm |
| Closed-finger vertices sampled | 2256 | 2263 |
| Exposed jaw/neck-to-gorget minimum | n/a (final head absent) | 5.602 mm |
| Blade-to-head minimum (exact) | n/a (final head absent) | 1.449 mm |
| Blade-to-hair minimum (exact) | n/a (final groom absent) | 14.563 mm |
| Exposed gorget/head intersection frames | n/a | 0 |
| Exact blade/head intersection frames | n/a | 0 |
| Decoded MP4 frames | n/a | 116 at 30/1 |

Head/hair/collar disposition: Conservative centerline proxies are negative near the overhead pass; exact blade BVH checks show no intersection and positive clearances. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.

Final SHA-256: `ee2c7694deee7d8082cc3ef447dc201a7fcfb334156a9e939a199336e4ce839d` (`models/astra_move_rising_spin_v2_wip.blend`); `7a5604a96bf5a8e082e35c3c7d2fb6abb6bd124fd9c1f7f729d828190bb9eb8b` (`renders/astra/rehost/rising_spin/rising_spin.mp4`).

## xslash

Method: complete source staging scene retained; old character replaced by full published char2 assembly; action copied without retargeting. At the exact-transfer gate, the action digest was `4e67baced997e08ce26c4b9f7ea6ae297c0ceb682a093f1e0f4604e36408d426`; all 847 F-curves and 307643 keys transferred without retargeting, with rest-matrix and quarter-frame pose-matrix error both 0.0. No post-transfer action correction was required.

| Numeric check | Old body | Published v2 body |
|---|---:|---:|
| Numeric leaves in X-slash naturalness audit | 10108 | 10071 |
| Common / exactly equal / changed numeric leaves | — | 10071 / 8187 / 1884 |
| Largest absolute audit delta | — | 55 (`foot_floor.foot_sole_vertex_counts.cloth`) |
| Minimum sole clearance | 1.009 mm | 1.342 mm |
| Minimum cloth-floor clearance | -11.966 mm | -4.122 mm |
| Hand-local hilt drift | 0.000676 mm | 0.000676 mm |
| Evaluated sword-tip error | 0.000603 mm | 0.000603 mm |
| Closed-finger hand-local drift | 0.000950 mm | 0.000967 mm |
| Closed-finger vertices sampled | 2396 | 2263 |
| Exposed jaw/neck-to-gorget minimum | n/a (final head absent) | 9.838 mm |
| Blade-to-head minimum (exact) | n/a (final head absent) | 95.966 mm |
| Blade-to-hair minimum (exact) | n/a (final groom absent) | 41.765 mm |
| Exposed gorget/head intersection frames | n/a | 0 |
| Exact blade/head intersection frames | n/a | 0 |
| Decoded MP4 frames | n/a | 90 at 30/1 |

Head/hair/collar disposition: The inherited old-body cloth-floor penetration remains visible numerically but improves by 7.844 mm; exact blade/head/hair checks pass. Brows and all nine hair-control families are armature-bound, fully weighted, and follow the 121-bone rig. Preview, final contact sheet, and frames decoded from the actual MP4 were inspected.

Final SHA-256: `23ac6ae2e6305c471847b432a16770340802e30c93a482ee27f0480154b75bbf` (`models/astra_xslash_v2_final_on_char2_wip.blend`); `23eebae113faa713614701e59127b44c397cb3ab8a458f5555a71b230b9fd0e7` (`renders/astra/rehost/xslash/xslash.mp4`).


## New head/hair/collar defects and dispositions

- No eyebrow or groom binding failure was introduced. All eyebrow and hair-control vertices remain weighted; all portable strands remain bound; every native curve retains its geometry-nodes representation.
- No exposed jaw/neck-to-gorget triangle overlap occurs in any of the 438 rendered frames. The internal neck insertion under the gorget lip is the published hidden seam and is classified separately.
- Rising Spin's conservative blade centerline proxies go negative during the overhead pass, but exact blade-mesh checks report zero head intersections, 1.449 mm minimum sampled head clearance, and 14.563 mm minimum sampled hair clearance after the avoidance repair.
- X-slash's conservative hair proxy also goes negative at F55, while the exact blade-mesh check reports 95.966 mm head clearance and 41.765 mm hair clearance with zero head intersections.

## Honest shortfalls

- X-slash retains a sampled cloth-floor minimum of -4.122 mm. This is materially better than the old body's -11.966 mm and passes the required same-or-better threshold, but it is still penetration and is not described as clean clearance.
- The closest exact Rising Spin blade-to-head sample is only 1.449 mm. It passes the asserted no-intersection test, but is visually and geometrically tight.
- Cloth remains deterministic kinematic secondary motion, not a fabric simulation. The audits do not certify continuous-time collision, hidden full-body triangle clearance, material fidelity outside the retained views, torque, or gameplay balance.
- The published body still carries the inherited garment/armor qualifications documented in `renders/astra/char2/MPFB_GRAFT_REPORT.md`; the rehost did not rebuild those surfaces.
- The native groom makes these delivery files and renders heavier than the old-body versions. EEVEE did not distribute across the two CUDA-visible cards, so final rendering was serial.

## Delivery

The five final `.blend` files remain only on black-sky. MP4s, preview/contact/decoded sheets, JSON, logs, and Markdown evidence are the only rehost artifacts copied back to the Mac. No Git commit or push was made.
