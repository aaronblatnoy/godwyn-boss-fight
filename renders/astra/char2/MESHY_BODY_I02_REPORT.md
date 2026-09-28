# Meshy God A body graft — iteration 02 report

## Decision

**NOT PUBLISHED.** Iteration 02 fixes the rest-pose source defects that blocked iteration 01: the tied-back-hair source has complete shoulders and arms, the segmented candidate has no floating hair debris or arm hole, its trim is continuous, and its sash does not cut through the plates. It is clearly closer to `body-concepts/god_A.png` than the published procedural body and cleaner at rest than `meshy_body_i01_comparison.png`.

Publication still fails two mandatory gates:

1. The exact 24-bone midpoint coverage audit is false for `RightForeArm`, `RightHand`, `Head`, and `head_end` (details below).
2. All five extended-pose renders show severe strip-like deformation through the fused robe/armor surface. I02 p99 edge stretch is 48.382×–73.787× versus I01's 21.093×–27.080×, and I02 maximum stretch is worse than I01 in three of five moves. This fails the “no tearing worse than i01” visual gate.

`models/astra_character_v2.blend/.glb` remain unchanged at SHA-256 `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255` / `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5`. Because publication did not occur, no `astra_character_v2_pre_body.blend/.glb` backups were created.

All Blender, rendering, animation, and ffmpeg work ran on **black-sky**. The Mac received only PNG, JSON, MD, log, and MP4 evidence; no `.blend` or `.glb` was copied to it. No git commit or push was made.

## Import findings

`models/meshy_body_godA_hairback.glb` imports as one mesh object with one PBR material:

- 278,318 vertices, 310,938 triangles
- bounds: 1.277033 × 0.793332 × 1.899059 m
- four packed 2048² maps: base color, ORM, emission, and normal
- 20,574 apparent topological components before coincident-seam welding
- open hands, no sword geometry

The raw EEVEE front/side/three-quarter views read strongly as the God A concept: gold plate, blue velvet, laurel trim, asymmetric sash, gauntlets, greaves, boots, and long decorated robe are all present. Unlike I01, the tied-back source hair does not cross either shoulder or arm, and both upper limbs are visibly complete.

The 20,574 apparent islands are duplicate-seam topology rather than 20,574 isolated visible shards. A 0.00005 m source-space weld merged 122,834 coincident vertices (278,318 → 155,484) and produced one connected visible source surface before head segmentation. This weld was necessary before applying the brief's mandatory component cleanup; applying the 200-vertex rule to the duplicated import directly would have deleted nearly the entire costume.

## Segmentation and cleanup

Segmentation used fitted world geometry plus sampled base-color/ORM texels:

- head/neck: remove every non-plate face crossing world z = 2.605 m
- gorget exception: retain metallic plate through z = 2.77 m inside |x| ≤ 0.40 m
- plate: metallic ≥ 0.65, constrained to torso/arm, leg, boot, and gauntlet envelopes
- blue velvet: B > 1.20R, B > 1.20G, metallic < 0.35
- hair-colored component mean: z ≥ 1.55 m, metallic < 0.65, R ≥ 0.34, G ≥ 0.22, R−B ≥ 0.20, G−B ≥ 0.08
- sword: no source sword-shaped component was present; zero sword faces were removed

Results:

| Item | Result |
|---|---:|
| Source faces | 310,938 |
| Head/neck faces removed | 12,691 |
| Components after head cut | 17 |
| Components under 200 vertices removed | 16 |
| Vertices / faces in those small components | 52 / 18 |
| Hair-colored components removed | 0 |
| Retained components | 1 |
| Final body vertices / faces | 149,413 / 298,229 |
| Plate faces / vertices | 102,573 / 55,838 |
| Blue-cloth faces / vertices | 143,022 / 79,915 |

The tied-back source hair was removed with the head above the seam; no separate surviving below-seam component met the mean hair-color rule. The retained body is one connected component.

### Required 24-bone midpoint coverage

The final audit uses the new body for replacement-region bones and the preserved published head/hair/NeckBlend for `Head`, `head_end`, and `headfront`. Twenty of 24 rows are within 60 mm. Four fail the literal threshold:

| Bone | Nearest final-surface vertex |
|---|---:|
| RightForeArm | 186.865 mm |
| RightHand | 199.544 mm |
| Head | 110.505 mm |
| head_end | 65.937 mm |

The right-side failures expose the source's symmetric open-hand forearm pose versus the rig's much more vertical sword-hand rest. A diagnostic right-lower-arm difference of 51.087° was measured. Rigid nearest-segment correction trials were rejected because cross-boundary triangles in the fused drape/arm sheet tore into long strips. The actual shoulder-to-elbow A-pose differences are only 3.065° left and 5.375° right, below the brief's 8° trigger, so the final clean rest candidate retains no limb correction. The head midpoint failures reflect the distance from internal head-bone centers to the preserved outer head/hair surface, but they are reported as failures under the requested literal 60 mm rule.

## Fit and seam

- uniform scale: 1.6639820058
- translation: (0.004500, −0.164000, 1.582013) m
- target height: 3.16 m
- maximum pelvis/shoulder/knee/ankle/crown landmark error: 0.012625 m (0.400% of height)
- 2% gate: 0.0632 m — pass
- upper-arm A-pose differences: 3.065° left, 5.375° right — below the 8° correction trigger

The published `AstraChar2_Meshy_HeadHair` and `AstraChar2_Meshy_NeckBlend` remain in place. Non-plate body geometry stops at z=2.605 m; the retained source gorget overlaps the 2.605–2.735 m NeckBlend band and hides the body seam in the required views. `Godwyn_Sword` is preserved with its original RightHand-only binding. A pale lower-head/bust shelf remains visible behind the neck in the strict side view; it belongs to the preserved published head assembly, not the new body segmentation.

## Binding and replacement candidate

Weights were transferred by nearest proximity from `astra_character_v2_meshy_i03_defrag.blend`: donor `char1` supplied body/cloth weights, while the R5 armor surfaces supplied plate proximity. Metallic plate vertices were collapsed to one nearest body-bone weight; no plate vertex retains a `phys_*` weight. `phys_robe_*` / `phys_cape_*` weights were restricted to blue/velvet texels only.

- donor body vertices: 322,354
- donor R5 armor vertices: 113,760
- phys donor vertices: 91,314
- target vertices using phys weights: 62,158
- phys robe/cape groups used: 62
- plate vertices assigned by R5 proximity / nearest-bone fallback: 25,946 / 29,892
- blue-cloth phys requeries: 17,473
- empty-weight nearest-bone fallbacks: 5,459

The candidate removes donor `char1`, all `AstraChar2_R5_*` armor, `Astra_Undersleeves`, `AstraChar2_R5_ClothFitEnvelope`, and `AstraChar2_R6_NeckGraft`. It preserves the published head/hair, NeckBlend, and sword. The source PBR material is unchanged; no additional gold tint was needed.

## Native and GLB gates

| Gate | Result |
|---|---:|
| Armature bones | 121 |
| Candidate actions | 0 |
| Rest-matrix error | 0.0 |
| Body unweighted vertices | 0 |
| Bad body weight sums | 0 |
| Maximum body weight-sum error | 5.2154e−8 |
| Non-rigid/phys plate vertices | 0 / 55,838 |
| Sword binding | RightHand only |
| GLB round-trip bones | 121 |
| GLB world-joint maximum error | 1.4305e−5 m (gate 5e−5 m) |
| GLB skin joint counts | [121] |
| GLB animations | 0 |
| GLB unweighted/bad vertices | 0 |

These build and round-trip gates pass. The separate 24-bone midpoint coverage gate does not.

## Five-move audit

All five actions were copied exactly at initial rehost. The derived files then received only quarter-frame Hips floor correction and distal phys-bone gathering. All grip, sole, cloth-floor, and requested blade/head/hair gates pass after correction.

| Move | Sole min | Cloth min | Max hilt drift | Blade audit | Max edge stretch | P99 edge stretch |
|---|---:|---:|---:|---|---:|---:|
| idle_guard F48 | +0.685 mm | +2.450 mm | 0.000525 mm | n/a | 674.302× | 61.581× |
| walk_stalk F36 | +0.540 mm | +2.254 mm | 0.000472 mm | n/a | 787.082× | 65.884× |
| lunge_thrust F40 | +0.531 mm | +2.066 mm | 0.000965 mm | n/a | 1,141.381× | 73.787× |
| rising_spin F40 | +0.539 mm | +2.267 mm | 0.000597 mm | 0 head / 0 hair overlaps; 7.857 / 6.570 mm sampled clearance | 782.785× | 71.561× |
| xslash F55 | +0.680 mm | +2.040 mm | 0.000722 mm | 0 head / 0 hair overlaps; 88.323 / 87.158 mm sampled clearance | 573.075× | 48.382× |

### Stretch comparison with I01

| Move | I01 max | I02 max | I02 / I01 | I01 p99 | I02 p99 |
|---|---:|---:|---:|---:|---:|
| idle_guard | 385.968× | 674.302× | 1.747× | 21.093× | 61.581× |
| walk_stalk | 379.756× | 787.082× | 2.073× | 24.753× | 65.884× |
| lunge_thrust | 566.157× | 1,141.381× | 2.016× | 26.267× | 73.787× |
| rising_spin | 978.347× | 782.785× | 0.800× | 27.080× | 71.561× |
| xslash | 900.265× | 573.075× | 0.637× | 22.567× | 48.382× |

The maximum improves for Rising Spin and X-slash but worsens for the other three moves. More importantly, the p99 ratio is worse in all five, matching the visible widespread strip deformation. The visual motion gate therefore fails even though the delivery/contact mechanics pass.

## Render and video evidence

Rest views were rendered in Cycles on black-sky with OptiX, 96 samples, denoising, at 1200×1800. Move stills and films used EEVEE at 768×768, 32 samples, 30 fps.

Rest-pose comparison:

- against `god_A.png`: overall costume silhouette, blue/gold layout, armor, greaves, sash, and trim are substantially closer than the published procedural body
- against `meshy_body_i01_comparison.png`: I02 removes the floating shoulder debris, restores both arm surfaces, and keeps the trim continuous
- sash/plate relationship: pass at rest
- shredded rest hems: pass; the long robe/cape edges are continuous
- extended-pose integrity: fail; every move still contains severe strips, spikes, or collapsed fused-sheet regions

The required films decode cleanly:

| Film | Frames | Codec | Pixel format | Resolution / fps |
|---|---:|---|---|---|
| rising_spin.mp4 | 116 | H.264 | yuv420p | 768×768 / 30 fps |
| xslash.mp4 | 90 | H.264 | yuv420p | 768×768 / 30 fps |

## SHA-256

| Artifact | SHA-256 |
|---|---|
| source `meshy_body_godA_hairback.glb` | `44e0a064d8a955529d98b9d40323407be07270a2146e47791a2a2a66b9ca23aa` |
| donor `astra_character_v2_meshy_i03_defrag.blend` | `582d8c2fd417a702ac864c1919b3cf6428e6b1be9f2881cce593b29d9ad64254` |
| candidate `astra_character_v2_body_i02.blend` | `72d3c3fcc339ff4538cceedc3077640e1e6ba99872759963e76a9bf6582a1179` |
| candidate `astra_character_v2_body_i02.glb` | `8900cc9b38d6181b15f2436a590119ee04fcc6573ceffaa2e1861a0b7dc8509a` |
| idle_guard move | `de87bd208b18f9c203361335330352530d1c24daf82369fc1b5ff5b0d5ab988c` |
| walk_stalk move | `71e92343f46063810ef1a0fba304cdbd8ac4cbb2bd84f00d2a20a164ca804c4d` |
| lunge_thrust move | `f26d3cbf24e83c2fbaaa822557e1381094d6f504d1c629ede2edddafd06ad7a7` |
| rising_spin move | `da77b65274fa62237469389907c79ceadaccac4ddc3ad92b632d08fa062eb7c9` |
| xslash move | `047603dbef3c984f2a179f70acdecbd70847c9f3529ab1a85ea4f1d6e452174b` |
| rising_spin MP4 | `81528d74186723087fd335bce670840e5d8a39f295f7f9b7cff3936cb50a8ed0` |
| xslash MP4 | `8db2e4bc75e221ce0c0420181df2d3694b3a6d5f25118ee8695969b94dea2505` |
| Cycles front | `35b3ebbcab8124eb963cfaf0f114d5326e1bcf36418937aad98c673bc38f75ad` |
| Cycles side | `ade08eef767808e571f6f15941d2a80f123aa2523401004cbfba041566042084` |
| Cycles three-quarter | `013ac76506f1178830933c9bb4f49795ffac2cefb185ead46f1a274785510a50` |
| God A comparison | `c5932109968647c847e64e5427298f09c830462854c9f6157e475ca7d98b3917` |
| I01/I02 comparison | `c00e2202306b39d693e3f7aadff39f88e32e3826cf30b979041dfa9ae22c26e3` |
| unchanged published `.blend` | `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255` |
| unchanged published `.glb` | `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5` |

Candidate sizes on black-sky are 190,317,182 bytes (`.blend`) and 62,342,312 bytes (`.glb`).

## Evidence inventory

- `renders/astra/char2/meshy_body_i02_import.json`
- `renders/astra/char2/meshy_body_i02_cleanup.json`
- `renders/astra/char2/meshy_body_i02_fit.json`
- `renders/astra/char2/meshy_body_i02_build.json`
- `renders/astra/char2/meshy_body_i02_validation.json`
- `renders/astra/char2/meshy_body_i02_roundtrip.json`
- `renders/astra/char2/meshy_body2_import_{front,side,tq}.png`
- `renders/astra/char2/meshy_body_i02_{front,side,three_quarter}.png`
- `renders/astra/char2/meshy_body_i02_comparison.png`
- `renders/astra/char2/meshy_body_i02_vs_i01_comparison.png`
- `renders/astra/rehost_body_i02/meshy_body_moves_audit.json`
- `renders/astra/rehost_body_i02/meshy_body_i02_stretch_comparison.json`
- `renders/astra/rehost_body_i02/*_extended.png`
- `renders/astra/rehost_body_i02/{rising_spin,xslash}.mp4`

The candidate and five move `.blend` files plus candidate `.glb` remain on black-sky only.

## Honest remaining shortfalls

The new source solves I01's hair/shoulder reconstruction problem, but not the production-topology problem. Armor plates, velvet, trim, skin, and long robe are still one welded surface with triangles spanning semantic boundaries. Proximity weights cannot make that fused sheet behave simultaneously like rigid plate, articulated limbs, and secondary cloth during large poses. Restricting phys weights to blue texels protects metallic plates from cloth bones, but it leaves adjacent fused regions driven by sharply different bone sets; the result is widespread strip stretch rather than a local isolated defect.

The next viable iteration needs semantic geometry before binding: separate/remesh rigid armor, articulated skin/gauntlets/boots, and each cloth panel while preserving or rebaking the PBR maps. A separately generated headless body with separated garments, or a manual retopology/partition pass, is more promising than another proximity-weight threshold pass on this fused mesh. The asymmetric right forearm also needs a source pose aligned to the sword-hand rest or a topology-safe articulated correction before weight transfer.
