# Godwyn v3 — Meshy Auto-Rig Build Report

Date: 2026-09-28  
Execution host: `black-sky`  
Blender: 5.2.0 LTS  
Status: **PUBLISHED — ALL REQUIRED AUDIT GATES PASS**

## Publish state

The new lineage is published on `black-sky`:

- `models/astra_character_v3.blend` — 67,589,746 bytes — SHA-256 `43b3a6643e6c6ddb8cc317ee0bed3381d3c654832028a5f5f2b7e7a8d405359c`
- `models/astra_character_v3.glb` — 75,960,192 bytes — SHA-256 `c98c7b6df2406c91b72298d8c3d6ee2c10fd768f24cce68ac29c481f19f2cb91`

The GLB was imported into a fresh Blender scene and passed round-trip validation: one 24-bone armature, the exact expected bone-name set, five named animation clips with exact frame counts at 30 fps, and zero unweighted or non-normalized vertices on the largest imported skinned mesh.

The protected v2 files were not modified. Their hashes before and after publication were identical:

- `models/astra_character_v2.blend`: `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255`
- `models/astra_character_v2.glb`: `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5`

No commit or push was made.

## 1. Meshy rig inspection

`models/meshy_body_godA_hairback_rigged.glb` contains one bound body mesh and one 24-bone armature. `Hips` is the only root, all expected body bone names are present, and there are no finger bones. The body has 276,903 vertices, 309,328 triangles, 24 vertex groups, zero unweighted vertices, normalized weights, and one to four influences per vertex.

The unrigged source has 310,938 triangles, versus 309,328 in the Meshy-rigged service output: a pre-existing 0.492% reduction (`0.995079` ratio). No decimation, merge-by-distance, or topology reduction was performed in this v3 build. “Full resolution” therefore means the complete Meshy auto-rig service output, minus the explicitly replaced head/hair region.

The rigged GLB retained only one 2048×2048 base-color image. The unrigged source retained four 2048×2048 images. The build restored the source ORM, normal, and emission maps through the shared UV layout while retaining the auto-rig base color.

Evidence: `meshy_rig_inspect.json`.

## 2. Head, seam, and neckline

The original Meshy head/hair/neck region was removed above the gorget boundary. The retained body changed from 309,328 to 295,426 faces; 12,579 non-plate head/neck faces and 1,323 hair-colored component faces were removed. The approved i02 head was fitted with a uniform scale of `1.020167`; crown error was `0.0 m`, the fitted eye line was `2.984043 m`, and the measured seam-anchor error was `1.91e-8 m`.

The first texture pass selected an emission image instead of the actual base-color branch and was rejected. The final pass resolved `Image Texture.001` / `Image_0.001`, created the packed image `Astra_V3_Head_BaseColor_NecklineFixed.001`, replaced 72,456 core texels and 269,015 texels including feathering, and used the adjacent-neck median linear RGB `[0.788235, 0.639216, 0.415686]`. The final before/after crops are `meshy_v3_neckline_before.png` and `meshy_v3_neckline_after.png`.

Close-up semantic QA found that the initially skinned procedural sleeve and the appended `AstraChar2_Meshy_NeckBlend` displaced outside the neck silhouette. Both were rejected rather than hidden in the final file. The final seam uses the approved head's central neck, a closed rigid neck bridge parented to `Head`, and a small gold gorget trim. Two targeted donor cleanup passes removed 14,072 low shoulder/chest faces while preserving the face and upper hair. The collar close-up shows the neck join contained by the armor; the remaining dark triangular recess is the gorget's own V-shaped cavity, not an open mesh seam.

Evidence: `meshy_v3_seam_fix.json`, `meshy_v3_sleeve_rejection.json`, `meshy_v3_head_trim.json`, `meshy_v3_neck_cleanup.json`, `meshy_v3_neck_bridge.json`, and `hero_collar_closeup.png`.

## 3. Sword grip

`Godwyn_Sword` (4,235 vertices) uses the old rig's `RightHand`-local transform reapplied to the new `RightHand` rest transform. It is bone-parented to `Astra_V3_Rig/RightHand`. There are no finger bones, so the intended presentation is the supplied open-palm grip.

Maximum measured hand-local hilt drift was between `0.000474 mm` and `0.001046 mm` across the five moves, below the `0.01 mm` gate.

## 4. Retargeted actions

The mapping is identity for all 24 target bones. Each source pose was root-frame aligned and height-scaled (`0.988276`), then solved with direction aiming and position correction against old-rig posed joint heads. The target rest joint layout differs materially from the old rig despite matching names—up to about 384 mm at `RightHand`—so non-root position channels are intentionally baked in addition to rotation channels. This is what makes the measured target joints match rather than merely copying rotations between unlike rest layouts.

Published actions:

| Clip | Frames | FPS | Loop metadata |
|---|---:|---:|---|
| `Godwyn_V3_idle_guard` | 96 | 30 | yes |
| `Godwyn_V3_walk_stalk` | 72 | 30 | yes |
| `Godwyn_V3_lunge_thrust` | 64 | 30 | no |
| `Godwyn_V3_rising_spin` | 116 | 30 | no |
| `Godwyn_V3_xslash` | 90 | 30 | no |

Evidence: `meshy_v3_bone_mapping.json` and `meshy_v3_retarget_samples.json`.

## 5. Final audits

The following numbers are from the published `models/astra_character_v3.blend`, not the WIP.

| Move | Joint p50 / p99 (mm) | Edge stretch p99 / max | Grip max (mm) | Min sole (mm) | Blade/head-hair overlap frames |
|---|---:|---:|---:|---:|---:|
| idle_guard | 0.000223 / 0.000747 | 1.297256 / 2.700788 | 0.000474 | 0.499754 | 0 |
| walk_stalk | 0.000246 / 0.000960 | 1.329448 / 2.681325 | 0.000529 | 0.499828 | 0 |
| lunge_thrust | 0.000300 / 0.001068 | 1.377692 / 2.749999 | 0.001046 | 0.499854 | 0 |
| rising_spin | 0.000238 / 0.000776 | 1.318671 / 2.762361 | 0.000659 | 0.499742 | 0 |
| xslash | 0.000239 / 0.000964 | 1.398045 / 2.977356 | 0.000983 | 0.499827 | 0 |

Overall joint error across 10,512 joint samples was p50 `0.000240 mm`, p99 `0.000961 mm`, and max `0.001611 mm`, versus the 40 mm p99 gate. Every stretch p99 is at or below 1.6 and every maximum is at or below 3.0. Sword drift, sole clearance, and collision gates all pass.

Stretch repair was iterative. The final gate-closing equalization pass changed 15 vertices; earlier Laplacian passes touched broader neighborhoods, with the widest recorded pass touching 11,175 vertices (4.22% of the retained body). Per-pass command output is preserved in `codex_v3.log`.

Motion contact-sheet review found a failure that edge stretch alone did not expose: 40 disconnected lower-garment trim islands (1,210 vertices) were incorrectly dominated by `Head` weights and trailed behind during `rising_spin`. Those islands were reassigned rigidly to `Hips`; the final rising-spin contact sheet is clean and the complete audit still passes afterward.

Floor correction was applied as root lift to preserve the source motion while preventing penetration. Maximum lifts were 0.1899 m (idle), 0.2841 m (walk), 0.2725 m (lunge), 0.2257 m (rising spin), and 0.3514 m (xslash).

Evidence: `meshy_v3_audit.json`, `meshy_v3_weight_repair.json`, `meshy_v3_fragment_probe.json`, and `meshy_v3_fragment_repair.json`.

## 6. Look and renders

The body material uses plate roughness `0.35`; SPEC gold `(0.82, 0.65, 0.15)` mixed at 25%; and deep blue `(0.00, 0.03, 0.23)` mixed into the Meshy cloth at 30%. Skin comes from the approved i02/skin_i01 material path, with the corrected packed neckline base color.

All six hero images were rendered at 1200×1800, 128 samples, Cycles GPU, after positively asserting two `NVIDIA GeForce RTX 3060 Ti` OptiX devices. There was no CPU fallback.

Hero outputs:

- `hero_idle_front.png`
- `hero_idle_side.png`
- `hero_idle_three_quarter.png`
- `hero_collar_closeup.png`
- `hero_face_closeup.png`
- `hero_comparison_sheet.png` against `body-concepts/god_A.png`

All five films were rendered at 768×768 and encoded H.264 at 30 fps with matching contact sheets. The film camera follows root translation in X/Y while retaining vertical motion, so the lunging action remains in frame.

## 7. GLB round trip

The published GLB contains five meshes, one skin with 24 joints, 30 nodes, and exactly five animations. Each animation has 72 channels and the expected duration. Fresh-import action ranges were verified at 30 fps as 96, 72, 64, 116, and 90 frames. The imported skeleton has the exact expected 24 bone names. Round-trip status: **PASS**.

Evidence: `meshy_v3_publish.json` and `meshy_v3_roundtrip.json`.

## Honest shortfalls

- The rig has no finger bones. The sword is rigidly stable in the supplied open palm, but there is no articulated fist.
- The Meshy service output arrived with 1,610 fewer triangles than the unrigged source (0.492%). This build did not introduce that difference and did not decimate further.
- The old and new skeletons share names but not identical rest joint positions. The baked clips therefore depend on position channels as well as rotations; systems that discard joint translation will not reproduce the audited pose.
- The appended `NeckBlend` could not be retained honestly: semantic rendering showed it displaced outside the neckline. A rigid closed bridge and gorget trim replace it in the shipped model.
- The large root-height corrections reflect source/target rest-origin and sole differences. They pass the floor gate but are not subtle offsets.
- Hair and cloth have skinned motion only; no secondary physics simulation was added.
- The head/neck close-up is clean enough to publish, but the body gorget has a deep V-shaped recessed cavity that reads darker than the surrounding gold in frontal lighting.

## Artifact index

- Inspection: `renders/astra/char2/meshy_rig_inspect.json`
- Mapping: `renders/astra/char2/meshy_v3_bone_mapping.json`
- Audit: `renders/astra/char2/meshy_v3_audit.json`
- Publish: `renders/astra/char2/meshy_v3_publish.json`
- Round trip: `renders/astra/char2/meshy_v3_roundtrip.json`
- Heroes and films: `renders/astra/v3/`
- Complete execution log: `renders/astra/char2/codex_v3.log`
