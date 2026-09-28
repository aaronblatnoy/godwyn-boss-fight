# Astra V3B rebuild — REJECTED FOR PUBLICATION

The raw-body rebuild and review artifacts are under `renders/astra/v3b/` on black-sky. **This candidate is not clean and must not be merged or published.** The body-preservation proof passes, but the collar/neck attachment, remaining hair slivers, and grounding checks fail the requested release standard. No `models/astra_character_v3b.blend/.glb` has been promoted by this run.

All Blender, Cycles/OptiX, and ffmpeg work ran on black-sky. No Git was used. This run did not write `models/astra_character_v3.*` or `renders/astra/v3hym*`. Local work comprised scripts, image inspection, and evidence/report copies. Command output was appended with tee to `renders/astra/char2/codex_v3b.log`.

## Removal and preservation

The initial inset-cylinder experiment was rejected because it left the old head. The final candidate uses the owner's subsequent A/B volume, with protected-region masks overriding deletion:

- A: vertex Z > 2.749731178 m, horizontal radius from the measured neck axis < 0.28 m.
- B: face passes the i02 hair-color test, vertex radius < 0.20 m, vertex Z > 2.55 m.
- Every vertex of a removed face must satisfy A or B. No body deletion is based on component size, color alone, or Z alone.
- Neck axis: (0.024525675, -0.270875159) m, averaged from 2,041 raw vertices with neck weight > 0.5. Original measured rim reference: 2.754731178 m; measured floor: 2.480000257 m. The original reference is held fixed for the removal predicate.
- The original measured collar population is 10,027 faces. A further 1,190 taller gold collar faces were added to protection after visual inspection showed the first band missed the tall side/rear rim. These are never deleted.

| Region | Raw faces | Retained faces | Removed |
|---|---:|---:|---:|
| Cape | 14,177 | 14,177 | 0 |
| Upper back | 17,666 | 17,666 | 0 |
| Collar/gorget, combined measured population | 11,217 | 11,217 | 0 |
| Original measured collar | 10,027 | 10,027 | 0 |
| Taller collar guard | 1,190 | 1,190 | 0 |
| Pauldrons | 11,039 | 11,039 | 0 |
| Rear hem | 42,841 | 42,841 | 0 |
| All plate-classified faces, including old head/crown | 99,247 | 99,063 | 184 |
| Entire raw body | 309,212 | 299,063 | 10,149 |
| Entire body outside the A/B volume | 295,186 | 295,186 | 0 |

Regions overlap; rows must not be summed. Their exact masks, angular measurements, and outside-volume counts are in `../v3b/build_r5.json` and `scripts/astra_v3b_rebuild.py`. The 184 removed plate-classified faces are outside the protected collar/pauldron populations and inside the allowed head volume.

An independent fresh raw import verifies that **every retained ordered triangle has exactly identical rest coordinates and face-corner UVs**, with unique surviving raw face IDs. See `../v3b/preservation_final.json`. This proves preservation of the selected geometry; it does not pretend that color/position masks are a perfect semantic segmentation of every collar fragment.

## Liner and materials

The final liner has 72 angular sectors and seven rings, 504 vertices, smooth shading, a skin funnel, a wall skirt, and a closed dark bottom polygon. The inner ring is at Z 2.73 m, the wall contact at 2.70 m, and the bottom at 2.56 m. Horizontal BVH rays fit the retained wall. The contact seam uses barycentrically interpolated weights from the hit body triangle, blending to rigid neck weights at the inner edge. This changes the original neck-only liner binding to follow the collar's deformation; the copied NeckBlend remains rigid to `neck`.

The liner and NeckBlend share a flat material with **zero image-texture nodes**. Median head neck-texture RGB from 7,182 sampled skin texels is (0.8431373, 0.6941177, 0.4980392), decoded from sRGB to linear (0.6795426, 0.4396572, 0.2122308). The native skin_i01 subsurface settings are copied: weight 0.32, radius (1, 0.35, 0.2), scale 0.008 m, anisotropy 0. Roughness is 0.55. See `build_r5.json` and `scripts/astra_v3b_materials.py`.

**Visual failure:** the orange texture-mapping artifact is gone, but the loft does not meet the jagged collar opening cleanly. Skin patches cross the front edge, dark triangular gaps remain, and the copied NeckBlend is visibly offset from the head in rest pose. A closed bottom polygon is not proof of a visually closed collar. The resulting funnel is too broad and visibly artificial. The exact-contact revision did not resolve these defects.

The head keeps its native skin_i01 material. Body plates use roughness 0.35 and 25% warm gold tint (0.82, 0.65, 0.15); cloth uses the 30% deep-blue anchor (0, 0.03, 0.23), with the source normal/ORM/emission maps retained.

## Hair, binding, and animation

The head-only component cleanup was executed. Six hair-bearing welded components remain. The five secondary components contain 456, 368, 136, 111, and 92 source vertices, or 229, 199, 69, 61, and 53 unique geometric vertices after a 0.1 mm weld. Their nearest-main-hair distances are 13.9–16.6 mm. None satisfies the under-40-vertices or farther-than-30-mm rule, even when duplicate UV/normal vertices are excluded. **Zero components/vertices/faces were deleted.** Small floating-looking slivers and abrupt cut ends remain visible; the numeric rule did not deliver the requested clean appearance. See `hair_final.json` and the face renders.

Head, NeckBlend, and sword retain their source object transforms and Head/neck/RightHand bindings. The 24-bone rest matrices match exactly. The directly copied, sampled `Combat_Stance` action has 51 frames at 30 fps and is the only retained action. The maximum source-to-candidate world bone-matrix element difference is 7.8678131e-6 across the clip.

Independent source-snapshot versus candidate evaluation at rest and all 51 posed frames sampled 240 vertices per copied object: rest differences were zero; maximum posed differences were 1.491 micrometers for the head, 1.440 micrometers for NeckBlend, and 1.263 micrometers for the sword. Thus the rest-pose attachment problem is present with the copied source placements, rather than being hidden by a new head repositioning. See `bindings_final.json`.

The raw robe showed a severe serrated deformation fold even in a clay render. To reduce it, 100 iterations of adjacency-based weight smoothing were applied to the lower cloth with a tapered boundary. This changed 134,875 mesh vertices' weights and affects 168,677 retained faces. **Rest positions, faces, and UVs remain unchanged.** The posed hem is much improved, though a broad crease remains. This is a skin-weight correction, not a claim that all raw weights are byte-identical. Maximum body influence count is now nine; export must preserve all influences.

## Full-clip audits

| Check | Result | Verdict |
|---|---|---|
| Body stretch p99, worst of 51 frames | 1.6197168, limit 2.2 | PASS |
| Unweighted / bad-sum vertices | 0 across all asset meshes | PASS |
| Coincident-rest seam pairs | 103,921 pairs; maximum posed separation 0 m | PASS |
| Minimum sampled sole Z | +0.24988 mm | No penetration in sampled soles |
| Maximum clearance of lower foot | 10.6363 mm | FAIL strict grounding |
| Frames with lower foot within 5 mm | 30 of 51 | FAIL all-frame grounding |
| Broad head/collar triangle overlap count | Up to 404 pairs | Cannot certify zero visible overlap |
| Inherited restricted exterior overlap count | 0 | Insufficient; excludes central collar |
| Visual head/collar seam | Jagged gaps, exposed skin, rest-pose misjoin | FAIL |
| Hair silhouette | Residual slivers / chopped ends | FAIL |

Broad collision counts include intentional buried neck contact; they are **not** a count of visible defects. Conversely, the old exterior-only test's zero does not certify a clean collar. The requested zero-visible-overlap gate is not passed. Full per-frame measurements are in `audit_final.json`.

## My inspection of every required still

All fourteen native stills are Cycles OptiX, 64 samples, 1200×1800, rendered on black-sky and opened individually for my own inspection. The broad studio highlights make the face pale; the approved head look was retained. The rest three-quarter camera was additionally fitted to include the sword tip.

| View | My visual verdict |
|---|---|
| Rest front | Body, plates, and hem continuous; obvious head/NeckBlend misjoin and exposed skin column. FAIL assembly. |
| Rest side | Continuous robe silhouette and back; abrupt hair edge, stray fragment in front of collar, and attachment gap. FAIL assembly. |
| Rest three-quarter | Torso and drape intact; exposed cylindrical NeckBlend and disconnected-looking head. FAIL assembly. |
| Rest BACK | Back plate, cape anchor, and rear hem intact. Body preservation passes this view; hair ends remain ragged. |
| Rest collar | Large offset between copied head and NeckBlend; triangular gaps and floating-looking fragments. FAIL. |
| Rest top-down into collar | Skin-colored funnel present, but broad, artificial, offset, and not sealed visually at the front. FAIL. |
| Rest face | Face intact; small hair fragments, abrupt lower cut, and visible neck/collar misjoin. FAIL cleanup/attachment. |
| Stance front, frame 1 | Body and sword read well at full scale; no large missing hem. Exposed collar skin remains obvious. FAIL assembly. |
| Stance side, frame 1 | Back and robe remain continuous; broad deformation crease remains, without the earlier serrated break. Nape edge is rough. |
| Stance three-quarter, frame 1 | Continuous torso and robe silhouette; stray fragment visible in front of collar. FAIL cleanup. |
| Stance BACK, frame 1 | Back/cape/hem intact; broad cloth crease remains. Dark nape discontinuity visible beneath hair. FAIL attachment. |
| Stance collar, frame 1 | Head approaches collar, but jagged front seam and dark gaps remain; skin surface looks artificial. FAIL. |
| Stance top-down into collar, frame 1 | No large empty tube, but triangular front gaps and protruding skin survive. FAIL. |
| Stance face, frame 1 | Face intact; floating-looking hair slivers and rough cut ends are plainly visible. FAIL cleanup. |

The diagnostic renders were also inspected, including the rejected cylinder result, successive liner revisions, body without its normal map, clay body, and color-coded collar assembly. They are retained under `../v3b/` for provenance.

## Deliverables and disposition

`candidate_final.blend` is a **rejected working candidate**, not a release. The full still set is in `../v3b/final/`. Completed film, contact sheets, export round-trip results, and final artifact hashes are documented below.

**Publication gate: FAIL.** Do not merge this candidate into the canonical model or the HY-Motion moveset. Remaining work is an actual clean neck-to-head/collar junction across rest and posed states, a hair cleanup policy that catches the visible slivers, and grounding correction with source-motion deviation measured. No claim is made that these problems are solved.

## Completed film, export, and evidence

The root-follow film contains all **51 frames at 30 fps**, 768×768, 24 Cycles OptiX samples, with XY camera tracking and no frame interpolation. ffprobe confirms 51 decoded frames and 1.700 seconds. I inspected frames 1–51 on six contact sheets, with 512-pixel tiles. The body and hem stay continuous through the small stance motion; the camera retains the figure without clipping. This wider view does not resolve the collar/hair failures shown in the close-ups. I did not use the small film tiles to overrule those failures.

The candidate GLB was exported and imported into a fresh Blender scene. Body base color and roughness, plus head base color, were baked at 2048×2048 on black-sky for the export material graph. The native shader version remains separately saved. I inspected the three baked atlases and the imported front/top-down renders. The export retains the gold/blue appearance and the same disqualifying collar defects. Native subsurface scattering has no exact core glTF equivalent.

Round-trip results (`roundtrip.json`, `export_weights.json`):

- 24 bones, exact bone-name set and parent hierarchy, one `Combat_Stance` action with 51 frames at 30 fps.
- Maximum rest-joint position error: 0.032611 mm.
- Zero unweighted or invalid-sum vertices after import.
- 160 sampled vertices per mesh, all 51 frames: maximum body deformation difference 0.104475 mm; head 0.002221 mm; NeckBlend 0.002080 mm; sword 0.009682 mm; liner 0.003806 mm.
- The body result narrowly exceeds the chosen 0.100 mm comparison gate, so the script's aggregate mechanical flag remains **false**. The threshold was not loosened after observing the result.
- `export_all_influences=True` was requested, avoiding the usual four-weight truncation. Direct binary inspection finds two joint/weight sets and a maximum of eight positive weights on the exported body. The native body has 3,331 vertices with nine positive weights, but the largest ninth weight is only 0.0000508408. Thus the exporter still drops tiny influences; this is **not a lossless skin-weight round-trip**. The liner retains its six influences. This limitation is recorded rather than hidden behind the export setting.

Evidence available locally and on black-sky:

- [All 14 stills overview](../v3b/stills_contact_sheet.jpg)
- [Rest BACK](../v3b/final/rest_back.png) and [stance BACK](../v3b/final/stance_back.png)
- [Rest collar failure](../v3b/final/rest_collar.png) and [stance top-down failure](../v3b/final/stance_collar_top45.png)
- [Combat_Stance MP4](../v3b/film/Combat_Stance.mp4)
- Film sheets: [1–9](../v3b/film/contact_01_09.jpg), [10–18](../v3b/film/contact_10_18.jpg), [19–27](../v3b/film/contact_19_27.jpg), [28–36](../v3b/film/contact_28_36.jpg), [37–45](../v3b/film/contact_37_45.jpg), [46–51](../v3b/film/contact_46_51.jpg)
- [Imported GLB front](../v3b/roundtrip/stance_front.png) and [imported GLB collar](../v3b/roundtrip/stance_collar_top45.png)
- [Removal counts](../v3b/build_r5.json), [independent preservation proof](../v3b/preservation_final.json), [full-clip audit](../v3b/audit_final.json), [copied-object proof](../v3b/bindings_final.json), [round-trip report](../v3b/roundtrip.json), [exported-weight inspection](../v3b/export_weights.json), [artifact hashes](../v3b/artifact_hashes.txt), [command log](codex_v3b.log).

Working Blender/GLB files remain on black-sky under `/home/aaron/godwyn-boss-fight/renders/astra/v3b/`: `candidate_final.blend`, `candidate_export.blend`, `candidate.glb`, and `roundtrip.blend`. They are rejected candidates, not model deliverables. Candidate-native SHA-256: `e139b185c8172c943dd59b07ed70322fe294fe0f329fea54600035b8a1231792`; candidate-GLB SHA-256: `654af1ec7fa1d9e3f291bc2c4cea47ec14f4fcfb6349ea3a1b3ed5367a74b029`.

Final checksum verification confirms the raw rigged GLB and private source snapshot are unchanged. Both proposed release paths, `models/astra_character_v3b.blend` and `.glb`, are absent. **The requested clean rebuild was not achieved; publication was correctly withheld.**
