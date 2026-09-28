# Godwyn v3 — Meshy Auto-Rig Build Report

Date: 2026-09-28  
Execution host: `black-sky`  
Blender: 5.2.0 LTS  
Status: **FIST VARIANT PUBLISHED — ALL REQUIRED AUDIT GATES PASS**

## Publish state

The closed-fist Meshy body is the published Godwyn v3 on `black-sky`:

- `models/astra_character_v3.blend` — 63,126,814 bytes — SHA-256 `e254ac97530c265ee1ac36b659f4d5ae752e8d27ec6842254e8b79277ca2abc9`
- `models/astra_character_v3.glb` — 70,657,336 bytes — SHA-256 `e2577625e35af133ef3fe0e240016e59108a10e9453430c4a58d4ca95e6b9fe9`

The previous open-hand v3 was preserved byte-for-byte as the reference variant before canonical publication:

- `models/astra_character_v3_openhand.blend` — SHA-256 `43b3a6643e6c6ddb8cc317ee0bed3381d3c654832028a5f5f2b7e7a8d405359c`
- `models/astra_character_v3_openhand.glb` — SHA-256 `c98c7b6df2406c91b72298d8c3d6ee2c10fd768f24cce68ac29c481f19f2cb91`

The protected v2 files also remained byte-identical:

- `models/astra_character_v2.blend` — SHA-256 `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255`
- `models/astra_character_v2.glb` — SHA-256 `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5`

No model file was copied back to the Mac. No git commit or push was made.

## 1. Fist-body rig inspection

Primary input: `models/meshy_body_godA_fists_rigged.glb`, SHA-256 `ad427e85feec6797be20d2646e08d5ee7c3dc21fb49c9b42cf9923007df8bf6d`.

- One bound `char1` mesh: 261,942 vertices and 309,212 triangles.
- One armature with the exact expected 24-bone set; `Hips` is the sole root.
- No finger bones.
- Zero unweighted vertices, zero bad normalized-weight sums, and one to four influences per vertex.
- A packed 2048×2048 base-color texture survived the rig service.

The unrigged fist source has 310,910 triangles. The rigged service output has 309,292 total triangles including its 80-triangle helper object, a `0.994796` ratio. This small topology reduction came from the rigging service; the v3 build did not decimate or merge the retained body.

Evidence: `meshy_v3fists_rig_inspect.json`.

## 2. Fix 1 — gorget integrity and collar closure

The fist build was rebuilt from the source so no plate-classified face could be deleted by head/neck removal. Initial body segmentation removed:

| Class | Faces removed |
|---|---:|
| skin | 2,745 |
| hair | 8,935 |
| lining | 67 |
| plate | **0** |

The collar selection contained 13,545 plate-classified faces, and the measured lowest selected collar vertex was `z=2.464160442 m`. The visible gold rim is entirely the preserved source gorget. A small dark disc, `Astra_V3_Collar_Occluder`, is parented to the neck/head chain and closes only the hidden collar interior. An experimental rigid skin bridge and a thicker occluder were rejected after previews because they protruded beyond the collar; neither is in the published model.

Additional residual-shell cleanup removed 1,142 non-plate/non-cloth faces from the original body head/neck volume, again removing zero plate and zero cloth faces. Donor cleanup removed 2,447 skin faces in the first trim, 129 additional skin faces outside the fitted neck ellipse, and 11,208 disconnected low non-hair donor-fragment faces across 1,604 small components. The main connected face/neck component and every hair-classified component were preserved. Final face counts are 296,323 on `char1` and 139,162 on the donor head/hair object.

Fresh 1200×1800 renders verify the gorget rim is continuous in the front, side, three-quarter, and collar-closeup views; no cut-through or open dark void remains. The last pale disconnected shoulder shell found in side/three-quarter QA was removed before the final renders and audit.

Evidence: `meshy_v3fists_build.json`, `meshy_v3fists_finalize.json`, `meshy_v3fists_body_head_cleanup.json`, `meshy_v3fists_donor_cleanup.json`, `meshy_v3fists_donor_component_cleanup.json`, and `renders/astra/v3fists/hero_collar_closeup.png`.

## 3. Fix 2 — neckline repaint reverted

The neckline repaint was removed completely. The approved skin material and its original base-color image were freshly appended from `models/astra_character_v2_skin_i01.blend`; no texel was repainted.

- Base-color image: `Image_3`, 2048×2048.
- Pixel SHA-256 before and after fit: `4a92f67641c34aa29441bf934a9955b6c495dd90a78050a577bd218194858b94`.
- `meshy_skin_mask` masked vertices before and after append/fit: 23,655.
- Edited texels: **0**.

The high collar hides the tunic neckline band, so a texture patch is unnecessary. The fresh face and collar close-ups show the original skin_i01 face/neck quality without the prior orange-yellow mottling.

Evidence: `meshy_v3fists_build.json`, `renders/astra/v3fists/hero_face_closeup.png`, and `renders/astra/v3fists/hero_collar_closeup.png`.

## 4. Head fit, sword seating, and retarget

The approved head/hair was uniformly fitted at scale `1.020168111` about the measured seam center. Crown error was `-0.000000238 m`; seam-anchor error was `0.000000019 m`.

`Godwyn_Sword` uses the old `RightHand`-local hilt transform reapplied to the fist rig's `RightHand` rest transform and is bone-parented to `Astra_V3_Rig/RightHand`. The hilt point was already inside the convex hull of 4,497 RightHand-weighted fist vertices:

- Hilt-to-fist intersection depth: `3.046042 mm`.
- Seating adjustment: `0 mm` of the permitted 30 mm.

The 24-name bone mapping is identity by name, but the actual retarget is position/direction based: root anatomical-frame alignment, parent-forward direction aiming on 17 non-leaf bones, non-root pose-location correction to the aligned source joints, and leaf-basis copying for both hands. All clips were baked at 30 fps:

| Clip | Frames | Loop |
|---|---:|---|
| `Godwyn_V3_idle_guard` | 96 | yes |
| `Godwyn_V3_walk_stalk` | 72 | yes |
| `Godwyn_V3_lunge_thrust` | 64 | no |
| `Godwyn_V3_rising_spin` | 116 | no |
| `Godwyn_V3_xslash` | 90 | no |

The centered head exposed a blade/head collision at x-slash frames 54–55. The smallest tested leaf-only correction that cleared both frames was a `-40°` local-Z rotation on `RightHand`, smoothly blended over frames 47–63. Because `RightHand` is a leaf bone, audited core-joint positions did not change, and the sword remained rigid to the hand.

Evidence: `meshy_v3fists_bone_mapping.json`, `meshy_v3fists_retarget_samples.json`, `meshy_v3fists_finalize.json`, and `meshy_v3fists_xslash_clearance_fix.json`.

## 5. Clarified gates and final canonical audit

These numbers come from a fresh audit of published `models/astra_character_v3.blend`, after all geometry cleanup and publication.

The 40 mm joint-position p99 gate applies only to these 18 core joints: `Hips`, `Spine02`, `Spine01`, `Spine`, left/right shoulder, arm, forearm, hand, up-leg, leg, and foot. `neck`, `Head`, `head_end`, `headfront`, `LeftToeBase`, and `RightToeBase` are still measured but are report-only.

The edge gate population is only edges with rest length at least 2 mm. Exactly 2,967 shorter degenerate seam edges were excluded from max and p99. The audit JSON lists every excluded edge index, endpoint pair, and rest length under `edge_stretch.excluded_degenerate_seam_edges`; 528,020 of 530,987 edges remained in the gated population.

| Move | Core-joint p50 / p99 (mm) | Edge stretch p99 / max | Grip drift max (mm) | Min sole (mm) | Blade/head-hair overlap frames |
|---|---:|---:|---:|---:|---:|
| idle_guard | 0.000238 / 0.000754 | 1.401979 / 2.973307 | 0.000483 | 0.499713 | 0 |
| walk_stalk | 0.000246 / 0.000759 | 1.436527 / 2.809981 | 0.000550 | 0.499830 | 0 |
| lunge_thrust | 0.000267 / 0.000963 | 1.470530 / 2.997650 | 0.000656 | 0.499794 | 0 |
| rising_spin | 0.000234 / 0.000740 | 1.417532 / 2.983191 | 0.000595 | 0.499837 | 0 |
| xslash | 0.000239 / 0.000783 | 1.522439 / 2.998830 | 0.000764 | 0.499846 | 0 |

Overall gated core-joint error across 7,884 samples was p50 `0.000240 mm`, p99 `0.000800 mm`, and max `0.001508 mm`. All edge-stretch p99 values are at or below 1.6 and all qualifying-edge maxima are at or below 3.0. Sword drift is below the 0.01 mm gate, sole clearance stays above the `-0.001 mm` penetration gate, and all five moves have zero blade/head and blade/hair triangle-pair overlaps.

All five gates pass: joint position, edge stretch, sword grip, sole clearance, and blade/head/hair clearance.

Evidence: `meshy_v3fists_canonical_audit.json`.

## 6. Look and visual proof

The approved look is applied to the full-resolution Meshy material:

- Plate roughness `0.35`.
- Gold tint `(0.82, 0.65, 0.15)` at 25% mix.
- Deep-blue cloth tint `(0.00, 0.03, 0.23)` at 30% mix.
- Skin from the untouched approved skin_i01 source.

All final hero images were rendered at 1200×1800, 128 samples, in Cycles after positively asserting two `NVIDIA GeForce RTX 3060 Ti` OptiX devices. There was no CPU fallback.

Fresh hero outputs in `renders/astra/v3fists/`:

- `hero_idle_front.png`
- `hero_idle_side.png`
- `hero_idle_three_quarter.png`
- `hero_collar_closeup.png`
- `hero_face_closeup.png`
- `hero_comparison_model.png`
- `hero_comparison_sheet.png` against `body-concepts/god_A.png`

All five motion films were rendered remotely at 768×768, 30 fps, encoded to H.264 MP4 remotely with ffmpeg, and accompanied by 4×3 contact sheets:

- `idle_guard.mp4`
- `walk_stalk.mp4`
- `lunge_thrust.mp4`
- `rising_spin.mp4`
- `xslash.mp4`

## 7. GLB round trip

The canonical GLB was imported into a fresh Blender scene and passed round-trip validation:

- One armature with the exact 24 expected bone names.
- One skin with 24 joints.
- Three exported meshes and 29 nodes.
- Exactly five animations, each with 72 channels.
- Fresh-import frame ranges of 96, 72, 64, 116, and 90 frames at 30 fps.
- Largest imported skinned mesh: 261,440 vertices, 24 vertex groups, zero unweighted vertices, zero bad weight sums, one to four influences per vertex.

Round-trip status: **PASS**.

Evidence: `meshy_v3fists_publish.json` and `meshy_v3fists_roundtrip.json`.

## Open-hand reference variant

The prior open-hand build remains available unchanged as `models/astra_character_v3_openhand.blend/.glb`. It retains the same five retargeted actions and its previously passing mechanical audits, but it is reference-only: it uses the supplied open palm, and its earlier hero review was the source of the blocking gorget-tear and neckline-repaint findings. Those visual fixes were proved on the fist build and are why only the fist build replaced canonical v3.

## Honest shortfalls

- The 24-bone Meshy skeleton has no finger bones. The primary body has closed-fist geometry and the hilt is measurably seated inside it, but finger articulation is impossible on this rig.
- The rigging service output is 0.520% lower in triangle count than the unrigged fist source. This build did not create that reduction and did not decimate the retained body.
- The old and new skeletons share names but not identical rest positions. The baked actions therefore use joint translations as well as rotations; an importer that discards non-root joint translation will not reproduce the audited pose.
- The x-slash edge maximum is `2.998830`, which passes the `3.0` gate with little numerical margin.
- Root lifts used to keep the soles above the floor are substantial: maximum 0.2149 m (idle), 0.3015 m (walk), 0.2934 m (lunge), 0.2355 m (rising spin), and 0.3648 m (x-slash).
- Hair and cloth use skeletal deformation only; no secondary simulation was added.
- Blender emitted a non-fatal missing-`cattrs` extension warning at startup, and the exporter reported MeshOptimizer unavailable. Blender operations, GLB export, fresh import, and all validations still completed successfully.

## Artifact index

- Fist rig inspection: `renders/astra/char2/meshy_v3fists_rig_inspect.json`
- Build and visual-fix evidence: `renders/astra/char2/meshy_v3fists_build.json`, `meshy_v3fists_finalize.json`, and cleanup JSON files
- Bone mapping: `renders/astra/char2/meshy_v3fists_bone_mapping.json`
- Final canonical audit, including the full excluded-edge list: `renders/astra/char2/meshy_v3fists_canonical_audit.json`
- Publish and round trip: `renders/astra/char2/meshy_v3fists_publish.json`, `meshy_v3fists_roundtrip.json`
- Heroes, films, and contact sheets: `renders/astra/v3fists/`
- Complete command log: `renders/astra/char2/codex_v3.log`
