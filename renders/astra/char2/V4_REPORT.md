# Godwyn V4 — publication withheld

**V4 is a rejected working candidate.** The single-pass head/neck/collar is a substantial assembly improvement over the v3 graft, but the face is visibly less resolved than the v3 head, the generated hands are open, and Combat_Stance produces a severe serrated fold across the rear robe. Passing the requested p99 stretch threshold does not make that deformation acceptable. No `models/astra_character_v4.blend/.glb` is promoted by this run.

All Blender, Cycles/OptiX, EEVEE, and ffmpeg execution is on black-sky. No Git commands were used. New scripts are prefixed `astra_v4_`. Candidate assets and evidence are confined to `renders/astra/v4/`; the report and tee log are in `renders/astra/char2/`. The v3 model family and v3hym render paths were not written by these scripts.

## Input and preservation

Input: `models/meshy_godwyn_full_rigged.glb`, 3.160001 m tall, 279,316 vertices, 308,821 triangles. There are 24 bones and zero unweighted or invalid-weight-sum vertices. The maximum body weight-sum error is 1.43e-7.

Bone names: Hips; Spine02, Spine01, Spine; neck, Head, head_end, headfront; LeftShoulder, LeftArm, LeftForeArm, LeftHand; RightShoulder, RightArm, RightForeArm, RightHand; LeftUpLeg, LeftLeg, LeftFoot, LeftToeBase; RightUpLeg, RightLeg, RightFoot, RightToeBase.

No body/head vertices were removed, moved, grafted, subdivided, or smoothed. No skin weights were edited. The SHA-256 fingerprint of positions, ordered face-corner indices, UV coordinates, and vertex-group assignments before and after both builds is identical: `fcf51bdc626fd3440c11efc249ddf965fdd68623682bdc665803cc13968b9d63`. The complete mesh, including its existing defects, is preserved.

Evidence: [input inspection](../v4/raw_probe.json), [build and preservation](../v4/build.json).

## Raw visual inspection and face resolution

I opened all four raw EEVEE renders individually. The front has a recognizable approximation of the composite's broad character design, but the hands are open rather than clenched. The side shows a continuous neck entering the collar. The back has a continuous robe and a broad, blunt hair mass. The face close-up has conspicuously blurred eyes and eyebrows, angular nose/jaw planes, and limited lip detail. It does not convincingly reproduce the approved portrait's face at close range.

- Head/hair region above world Z 2.75 m: **11,435 triangles**. This is a reproducible geometric region count, not a separately segmented head object.
- Front facial ROI: **1,738 triangles**, **3.9325 texels/cm**.
- Chest ROI: **7,106 triangles**, **3.6416 texels/cm**.
- Face/chest linear density ratio: **1.080**. The head receives very little preferential texture allocation.
- The v3 separate head's skin-mask region measures **14.7237 texels/cm** and 15,956 triangles. That region includes the neck and is not an identical crop, but the roughly 3.74× density difference agrees with the visible loss of eye/lip detail.

Density is `sqrt(sum(UV triangle area) × texture width × texture height / sum(world triangle area in cm²))`, using the 2048×2048 base atlas. The facial ROI is Z 2.77–3.04 m, |X| < 0.14 m, Y < −0.48 m; chest is Z 2.1–2.5 m, |X| < 0.3 m, Y < −0.4 m. Region boundaries and raw values are retained in [resolution.json](../v4/resolution.json) and [uv_proof.json](../v4/uv_proof.json).

**The v4 face is clearly worse than the v3 donor head in close-up resolution and likeness.** The v3 reference render itself has a broken collar and overbright studio highlights; those defects do not erase its better eye, lip, and facial-surface definition. Compare [approved/v3/v4](../v4/face_comparison.jpg), [feature crops](../v4/face_crops_comparison.jpg), and [body concept/model](../v4/body_comparison.jpg).

## Materials and mask correction

The rigged GLB retained base color and an emission connection to that same image, but no ORM/normal map connections. The unrigged full-character GLB supplies base, ORM, normal, and emission maps. The source material graph was copied by UV, retaining these connections; all images are packed.

The rigged and unrigged base images are not byte-identical: RGB mean absolute difference 0.02168, sampled correlation 0.99460. The rigged mesh has fewer distinct UVs, but **every retained rigged UV matches a source UV exactly** (nearest-source distance maximum 0 pixels at 2048). This supports the atlas transfer without claiming identical topology or guaranteed tangent-normal behavior after rigging. See [UV distance proof](../v4/uv_distance.json).

The skin mask is generated from warm base-color chroma, excludes metallic gold and blue, and is limited to face/ear/neck UV regions. It gates the skin_i01 recipe: SPEC multiply 0.35, HSV hue 0.492/saturation 1.28/value 1, rosy soft-light 0.10, SSS weight 0.32, radius (1, 0.35, 0.2), scale 0.008 m. Plates receive roughness 0.35 and 25% (0.82, 0.65, 0.15) gold tint. Blue cloth receives the 30% (0, 0.03, 0.23) anchor. Hair is excluded from the plate tint.

The first mask was rejected: it caught blond hair and left bright triangle-edge lines. I inspected all fourteen initial views, retained them under `initial_material/`, tightened the chroma and exposed-surface selection, padded the allowed UV region by six pixels, and softened the mask over two short filtering passes. The revised diagnostic estimates mask coverage at 79.23% of the facial ROI, 0.43% of the broad back-hair ROI, and 0.0093% of the top-hair ROI. These are approximate geometric regions, not a perfect semantic hair segmentation; exact zero hair spill is not certified. The final renders remove most of the first pass's white lines, but retain faceting and small eye/hairline creases. Skin reads warm, with overly bright studio highlights.

## Grip, motion, and full-clip audit

The source `Godwyn_Sword` RightHand-local rest transform was reapplied to v4 and rigidly weighted to RightHand. It is armature-parented with a RightHand deform binding. Translation adjustment is **0 mm**: the source grip already intersects the hand. The fitted handle-center marker lies **7.102 mm inward** from the nearest right-hand surface along its normal. This signed local surface measurement is not proof of a closed fist. The generated fingers remain open, and moving the sword by up to 30 mm cannot close them without violating the body-preservation rule.

Combat_Stance has **51 frames at 30 fps**. Parent-first, rest-independent world-space orientation baking reports a maximum quaternion orientation error of **0.000° at Blender's float precision**, not a claim of mathematical exactness. Source root motion is retained apart from per-frame Z grounding corrections of −8.579 to +2.711 mm.

All 51 integer frames were audited:

- Worst body edge-stretch p99: **1.50997**, passes ≤2.2. Edges shorter than 2 mm are excluded from this percentile.
- Lowest foot sole: **+0.999885 to +1.000151 mm**, passes the 5 mm planted-sole gate. The other foot is elevated by roughly 6 cm in the stance; this is not a both-feet-grounded claim.
- Blade/body intersecting triangle pairs: **0**.
- Sword/body pairs outside the RightHand grip region: **0**.
- Whole sword/body pairs including the intentional hand contact: up to **469**. Thus a literal whole-sword zero-overlap claim would be false.
- Lowest blade point: **+957.498 mm**; **0 mm floor penetration**, passes a ≤20 mm penetration allowance.
- Unweighted or bad-weight-sum vertices: **0** on body and sword.

The audit's `mechanical_pass` covers those numeric gates only. Maximum individual edge stretch exceeds 40×; the full side/back renders reveal a severe rear-robe deformation band. The p99 measure hides a small population of extreme failures. This is why the candidate is rejected despite that flag. The cloth weights were not smoothed because the brief permits only materials, sword placement, and motion transfer on the preserved character.

Evidence: [all-frame audit and grip measurement](../v4/audit.json).

## Per-view verdicts

All final stills are 1200×1800 Cycles OptiX, 48 samples, on the two available RTX 3060 Ti devices. The cameras use fixed world-axis front/side/back positions; the stance turns the character relative to those axes. The floor is dark, so the numeric foot measurements carry the precise clearance result.

Rest views:

- **Front:** continuous body/collar and recognizable gold/blue design; open sword hand and coarse face. FAIL overall quality.
- **Side:** neck/collar joins without the v3 graft gap; continuous robe in rest. Face remains angular and hair blocky. Assembly improvement, not a likeness pass.
- **Three-quarter:** intact torso, drape, and collar; visibly open hand around the handle. FAIL grip.
- **Back:** continuous back plate, robe, and hem in rest; blunt hair terminus. No large missing rear surface observed.
- **Face:** warm but overbright, blurry eyes, coarse lips, faceted nose/jaw, small sharp creases. FAIL face fidelity.
- **Collar:** continuous skin into the raised collar; no exposed liner tube or floating graft pieces. Rough surface detail remains. PASS the gross attachment check.
- **Top-down at 45°:** the collar surrounds the neck without the previous empty funnel; folded metallic surface and blocky hair remain. Gross collar closure improved.

Combat_Stance frame 1:

- **Front:** stance transfers, blade clears body, neck stays attached; open grip, raised opposite foot, distorted inner robe. FAIL visual release.
- **Side:** large jagged horizontal rear-robe fold and dark wedge-like breaks. FAIL cloth deformation.
- **Three-quarter:** torso and collar remain together, but the lower robe has sharp creases/tearing-looking folds. FAIL cloth.
- **Back:** prominent serrated deformation band across the cape/robe, plus an open hand around the sword. FAIL.
- **Face:** warm skin, but blurry eyes and polygonal cheek/jaw planes remain obvious. No separate floating graft pieces observed. FAIL likeness/detail.
- **Collar:** neck remains connected to the collar during the forward lean. A dark recessed area remains beside/under the jaw, with rough interior shading; no detached head or broad empty liner funnel. Not a flawless close-up.
- **Top-down at 45°:** no large hollow collar; blocky hair, small sharp surface creases, and rough gold interior remain. Gross assembly improvement, not a full visual-quality pass.

I inspected all fourteen final images individually, along with all fourteen first-pass images, all four raw EEVEE views, the v3 face render, both target images, and the comparison layouts. The final side/back views are decisive: the candidate is not clean.

## Film and candidate GLB round-trip

The [root-tracking Combat_Stance film](../v4/film/Combat_Stance.mp4) contains all **51 frames**, **30 fps**, **1.700 seconds**, **768×768**, rendered with **20 Cycles OptiX samples**. Camera tracking follows Hips XY while leaving vertical motion visible. ffprobe independently confirms the decoded frame count and duration. I inspected every frame on six 512-pixel-tile contact sheets, plus the native first frame. The figure stays framed, the head stays attached, and the jagged robe defect persists throughout the subtle stance motion. This wider view does not excuse the close-up face failure.

Contact sheets: [1–9](../v4/film/contact_01_09.jpg), [10–18](../v4/film/contact_10_18.jpg), [19–27](../v4/film/contact_19_27.jpg), [28–36](../v4/film/contact_28_36.jpg), [37–45](../v4/film/contact_37_45.jpg), [46–51](../v4/film/contact_46_51.jpg).

A **candidate-only** GLB was exported and imported into a fresh Blender scene. Native base color and roughness were baked at 2048×2048 for the export graph. The native shader candidate is retained separately. I inspected both bake atlases, all three masks, and the imported [front](../v4/roundtrip/stance_front.png) and [top-down collar](../v4/roundtrip/stance_collar_top45.png) renders. The imported model retains the appearance and the same disqualifying defects. Native masked SSS has no exact core glTF equivalent; the GLB skin is an approximation.

Round-trip results:

- **24 bones**, exact bone-name set and parent hierarchy.
- One **Combat_Stance** clip, **51 frames at 30 fps**.
- Maximum rest-joint component error: **0.018746 mm**.
- Zero unweighted or invalid-weight-sum vertices after import.
- Rest sample matching error: **0.004929 mm**.
- Across 160 sampled vertices per mesh and all 51 frames, maximum body deformation difference: **0.027953 mm**; sword: **0.009387 mm**.
- Requested all-influence export; sampled deformation passes the 0.1 mm comparison threshold. This is a sampled comparison, not proof of every exported vertex.

See [roundtrip.json](../v4/roundtrip.json). Mechanical round-trip passes. **Visual release still fails.**

## Delivery and final verification

Working assets remain on black-sky under `/home/aaron/godwyn-boss-fight/renders/astra/v4/`: `raw.blend`, `candidate.blend`, `candidate_export.blend`, `candidate.glb`, and `roundtrip.blend`. They are evidence/working candidates, not approved model releases. Lightweight evidence, including all stills, all film frames, comparisons, contact sheets, the MP4, audits, and hashes, was copied to the Mac. Blender and ffmpeg were never run on the Mac.

- [Final still overview](../v4/stills_contact.jpg)
- [Face-detail comparison](../v4/face_crops_comparison.jpg)
- [Decisive posed robe failure](../v4/final/stance_side.png)
- [Final preservation/publication verification](../v4/final_verification.json)
- [Artifact SHA-256 manifest](../v4/artifact_hashes.txt)
- [Command log](codex_v4.log)

Final verification confirms the v3 source blend and both Meshy inputs have unchanged SHA-256 hashes; all recorded `models/astra_character_v3*` sizes and modification times are unchanged. Both v4 release paths are absent. No script wrote to `renders/astra/v3hym*`.

The run recovered from an SSH stall before Blender launch, a NumPy 2D cross-product compatibility error in the measurement script, and a missing remote copy of the comparison concept. The source concepts were copied into the V4 evidence directory. Blender emitted nonfatal extension-startup and unavailable MeshOptimizer messages; the final uncompressed export, fresh import, and validation completed successfully. The log retains those failures and warnings.

**Disposition: do not publish.** This input solves the gross graft junction, but preserving it unchanged cannot also provide closed fists, a clean animated robe, and the approved head's close-up fidelity. A replacement source with those properties, or an explicitly expanded geometry/weight-edit scope, is needed for a clean release.
