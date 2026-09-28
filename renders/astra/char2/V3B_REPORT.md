# V3B rebuild — rejected strict-volume candidate, clarification pending

Status: **INCOMPLETE / VISUAL FAIL.** No accepted `models/astra_character_v3b.blend` or `.glb` has been published. The strict candidate is saved on black-sky at `renders/astra/v3b/strict_candidate.blend`. This is a diagnostic checkpoint, not a finished rebuild.

## Blocking conflict in the brief

Step 1 says the only removal volume is an inset vertical neck cylinder plus skin/hair geometry above the top of the Meshy head. The measured raw head top is Z=3.160000324 m, the maximum of the entire raw body. Therefore the second volume contains zero faces. The inset cylinder misses the forward face and substantial head shell. Actual Cycles renders show two heads: the retained old face in front of the approved donor. Deleting those remaining old-head faces would exceed the explicitly specified removal volume.

An asynchronous clarification was sent: allow a head-shaped extension above the collar while preserving collar/cape/back/pauldrons, or retain the exact written volume. No answer has been received at this checkpoint. The broader cut has not been executed.

## Build and preservation evidence

Fresh input: `models/meshy_body_godA_fists_rigged.glb` on black-sky. Raw SHA-256: `ad427e85feec6797be20d2646e08d5ee7c3dc21fb49c9b42cf9923007df8bf6d`.

The concurrent v3 job was isolated by a read-only-source snapshot under `renders/astra/v3b/source_snapshot.blend`, SHA-256 `57595cbed5d7b24b8838c8c1d3438262422737c71fdd5ea73e78684ead3306ad`. The source currently contained Combat_Stance and sword_slash_r; this candidate retains only Combat_Stance. No writes targeted `models/astra_character_v3.*` or `renders/astra/v3hym*`. No Git command was run. Blender and all rendering ran only on black-sky; no ffmpeg operation has been needed yet.

The neck axis is the mean XY of 2,041 raw vertices with neck weight >0.5: X=24.5257 mm, Y=−270.8752 mm. The working high-torso collar population is source plate-classified faces centered in Z=2.48–2.73 m, |X|<0.30 m, with sampled vertices within 0.36 m of the neck axis. Its measured vertex top is 2.754731 m; its lower sample is 2.480000 m. These are conservative geometric working measurements, not a manually certified semantic collar segmentation. Seventy-two angular sectors use their minimum radial distance, inset by 8 mm. Resulting removal radii range from 77.852 to 188.962 mm. The head reaches approximately 270 mm from the same axis.

309,212 raw faces → 303,001 retained faces: 6,211 removed. Every removed face has all three vertices within the allowed volume. The above-head clause removed zero faces. Every retained triangle's ordered world coordinates is exactly equal to its original triangle, verified through persistent raw face IDs.

Per-region before → after counts (geometric/texture masks, definitions in astra_v3b_build.py):

- cape: 14177 → 14177 (0 removed).
- upper_back: 17666 → 17666 (0 removed).
- collar: 10027 → 10027 (0 removed).
- pauldrons: 11039 → 11039 (0 removed).
- rear_hem: 42841 → 42841 (0 removed).

The broad legacy plate classifier labels 99,247 faces as plate; 862 of these lie inside the removal cylinder and are removed. It also classifies some old head-shell faces as plate, so this is not a certified armor-material count. The explicitly measured collar and pauldrons retain all their faces. All region counts outside the allowed volume are identical before and after. See `build.json` for exact masks/counts and all 72 radii.

The preliminary `probe.json` used an invalid four-vertex neck selection and is superseded by `neck_measure.json`, `weights.npz`, and `build.json`; its preliminary neck-axis number must not be used.

## Parts, liner, look, and animation

Appended donor head/hair, NeckBlend and Godwyn_Sword from the snapshot. Each object matrix differs from its source by exactly zero; bindings remain Head, neck, and RightHand respectively. The source head material is retained. Six weld-aware hair-bearing components remain; zero meet the <40 vertex or >30 mm isolation criteria. The five smaller components are 92–456 vertices and 13.90–16.61 mm from the main hair geometry. No head geometry was removed in this cleanup.

The new collar liner has five 72-vertex rings, lofted from the existing neck ring at Z=2.806856 m to the measured inner wall at Z=2.729731 m, a skirt down to the floor, and a dark disk at Z=2.490000 m. It is rigidly neck-skinned using the same material as the existing NeckBlend. **Visual failure:** the mapped skin material reads conspicuously orange/gold and the irregular outer edge looks like an added primitive. It requires proper skin UV sampling and smoother wall matching. The remaining old head also obstructs a meaningful final collar-closure inspection. No all-angle no-void claim is made.

The approved body shader is installed: plate roughness 0.35, 25% warm-gold tint, and 30% deep-blue cloth anchor, preserving source base/ORM/normal textures.

Raw/v3 rest matrices are exactly identical. Combat_Stance copies directly, 51 frames at 30 fps. The maximum sampled world-matrix element difference over all bones/frames is 0.000007867813; the stored source and target object/bone transforms otherwise match to numerical precision. No floor clamp or new retarget was introduced.

## Mechanical audit of strict candidate

Every integer frame 1–51 was audited. Worst body edge-stretch p99: **1.542565**, passing the requested ≤2.2 limit. Edges shorter than 2 mm in rest are excluded, matching the prior audit definition. Lowest sole: **−0.002974 mm** (numerical floor contact). Thirty of 51 frames have a sole within 5 mm of the floor; the closest sole reaches **10.5249 mm** above the floor at the least-grounded frame. Thus continuous planted contact is not certified.

All skinned meshes have zero unweighted/bad-sum vertices. The inherited exterior head/armor gate reports zero pairs, but its exclusion removes central collar/neck geometry. A broader 24,056-face collar/shoulder population reports up to **35 triangle pairs**. Some may be buried intentional contact; they have not been classified as all visible or all invisible. The clearly visible surviving old head independently fails the head-removal requirement. Do not interpret the inherited zero as a visual pass.

There are 104,964 coincident-rest vertex pairs; they remain coincident throughout the clip. A conservative seam-weight experiment found **zero** disagreeing weight groups, modified zero vertices, and did not fix the rear garment defect. The experimental `stitched_candidate.blend` is geometrically identical to the strict candidate. The exact cause of the remaining posed tear needs boundary/overlap analysis; it is not explained by mismatched weights at exactly coincident vertices.

## Direct visual review — every generated image inspected

All nine generated PNGs were inspected directly by the Codex default model. All are 1200×1800 Cycles OptiX renders; raw diagnostics use 32 samples, candidate views use 64. The first candidate rendering process was killed; the successful rerun used CUDA_VISIBLE_DEVICES=1 and eight CPU threads. Both GPU assertions and all successful render writes are in codex_v3b.log. Blender emitted unrelated extension-registration warnings about missing cattrs; rendering and the final audit completed successfully despite those warnings.

- `diagnostic_raw_collar.png`: raw face and original collar intact; overbright diagnostic lighting, small source triangulation flecks visible.
- `diagnostic_raw_top.png`: confirms the old face occupies more than the safe neck-column footprint; collar is asymmetric/tapered.
- `strict/rest_front.png`: torso, legs and front robe continuous; unmistakable duplicate head. FAIL.
- `strict/rest_back.png`: the large upper-back holes are gone; cape and rear hem continuous in rest. Duplicate head and rough donor nape remain. Body restoration improves substantially; full character FAIL.
- `strict/rest_collar_top45.png`: old head shell obscures donor face; liner is conspicuous, orange/gold, and jagged. FAIL.
- `strict/stance_front.png`: stable recognizable stance and restored chest/side garment, but two faces plainly visible. FAIL.
- `strict/stance_back.png`: upper back/cape materially restored; broad horizontal rear-skirt discontinuities remain in pose despite complete original face counts. Duplicate head remains. FAIL.
- `strict/stance_collar_top45.png`: donor and source head both visible; liner looks like an artificial gold funnel, so it is not acceptable. FAIL.
- `stitch_back.png`: same duplicate head and rear-skirt discontinuity; coincident-weight experiment changed nothing. FAIL.

The two supplied comparison/reference images were also inspected. They support the restoration benefit to the back, but the unchanged raw topology still tears in Combat_Stance. The brief's deletion-only explanation does not account for the entire posed hem defect.

## Remaining work

After clarifying the removal-volume conflict: complete conservative head-only removal; refine the skin liner and verify 45-degree closure; diagnose/repair the posed skirt discontinuity without losing raw faces; rerun full collision/stretch/grounding checks; render all seven views in both poses and the root-tracking Combat_Stance film/contact sheet; inspect every resulting image/frame sheet; export and independently re-import the 24-bone/51-frame GLB; only then publish the v3b model pair and a final visual verdict.

The final 14-view set, film/contact sheet, GLB round-trip, and accepted model pair are **not complete**. No successful rebuild is claimed.
