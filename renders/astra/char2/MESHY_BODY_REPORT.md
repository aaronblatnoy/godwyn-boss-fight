# Meshy God A body graft — i01 report

## Decision

**NOT PUBLISHED.** The candidate passes every requested numeric build, round-trip, grip, floor-clearance, and blade/head gate, and its rest-pose costume is substantially closer to `body-concepts/god_A.png` than the published procedural body. It does not pass the visual publication gate: the fused Meshy source is extremely fragmented, and the attempted head/hair removal leaves shredded shoulder/cape boundaries and floating fragments. The move renders also expose severe strip-like deformation on parts of the robe and armor. Therefore `models/astra_character_v2.blend` and `.glb` were not replaced, and no `pre_body` backups were created.

All Blender, rendering, animation, and ffmpeg work ran on **black-sky**. The Mac received only PNG, JSON, MD, log, and MP4 evidence. Blender was 5.2.0 LTS. The Cycles views were configured for GPU OptiX, 96 samples, and denoising. Move evidence used EEVEE at 768×768, 32 samples, 30 fps.

## Import findings

`models/meshy_body_godA.glb` imports as one object (`Mesh_0`) with one PBR material:

- 302,821 vertices, 311,024 triangles
- bounds: 1.259401 × 0.799948 × 1.899005 m
- four packed 2048² maps (base-color/emissive-type images plus ORM and normal inputs)
- 26,417 disconnected components
- open hands and no sword geometry in the actual file; this agrees with the supplied GLB summary but conflicts with the later prose description of a sword in the right hand

The unmodified import reads strongly as the God A concept: the blue-and-gold palette, asymmetric drape, sun chest motif, large pauldron, gauntlets, boots, and long trimmed robe are all substantially closer than the procedural published body.

## Segmentation

The source's disconnected, confetti-like topology made clean semantic separation impossible from topology alone. Segmentation therefore combined fitted world-space position with texture-sampled color/metallicity:

- head: remove non-plate faces crossing world Z = 2.605 m
- gorget exception: retain metallic plate faces through Z = 2.77 m inside |X| ≤ 0.40 m
- blond source head/hair below the seam: remove faces above Z = 1.55 m when sampled color satisfies R ≥ 0.34, G ≥ 0.22, R−B ≥ 0.20, G−B ≥ 0.08, with rear-Y threshold −0.30 m
- plate mask: metallic ≥ 0.65 plus torso/arm, front-leg, front-boot, and outer-gauntlet spatial envelopes
- sword: zero faces removed because the actual GLB contains no sword-shaped geometry

Result: 201,502 body faces / 194,455 body vertices, with 71,688 blond nonmetal head/hair faces and 37,834 upper head/neck faces removed. The mask retains 50,611 plate faces (47,856 plate vertices) and identifies 102,193 blue-cloth faces.

This was the best tested threshold balance, but it is not production-clean: blond hair and shoulder trim occupy the same fragmented color/space band, so more aggressive removal cuts the cape/pauldron while less aggressive removal leaves source-hair confetti.

## Fit and seam

- uniform scale: 1.6640292720
- translation: (0.004500, −0.164000, 1.581597) m
- target height: 3.16 m
- maximum landmark error: 0.012003 m (0.380% of height), versus the 0.0632 m / 2% gate
- source-vs-rig arm-angle differences: left 3.065°, right 5.375°; no rigid limb correction was needed because both are below 8°

The published `AstraChar2_Meshy_HeadHair` and `AstraChar2_Meshy_NeckBlend` are preserved. Non-plate body geometry stops at the 2.605 m seam; the retained source gorget overlaps the NeckBlend band (2.605–2.735 m). The existing `Godwyn_Sword` is preserved with its original RightHand-only binding.

## Binding and replacement candidate

Weights were transferred by nearest-donor proximity from `astra_character_v2_meshy_i03_defrag.blend`: `char1` supplied skin/cloth and phys weights; the R5 armor objects supplied plate proximity before plates were collapsed to one rigid nearest body-bone weight. Blue low-body cloth received a second phys-donor query. The candidate uses 63 `phys_robe_*` / `phys_cape_*` groups.

The candidate contains the retained Meshy i02 head/hair and NeckBlend, original sword, 121-bone armature, and the segmented source-PBR body. It removes the donor `char1`, all `AstraChar2_R5_*` armor objects, `Astra_Undersleeves`, `AstraChar2_R5_ClothFitEnvelope`, and `AstraChar2_R6_NeckGraft`. The Meshy material is unchanged; no additional gold tint was applied.

Build gates:

| Gate | Result |
|---|---:|
| Armature bones | 121 |
| Actions in character candidate | 0 |
| Rest-matrix error | 0.0 |
| Unweighted body vertices | 0 |
| Bad body weight sums | 0 |
| Maximum body weight-sum error | 5.22e−8 |
| Plate vertices with non-rigid or phys weights | 0 / 47,856 |
| GLB round-trip bones | 121 |
| GLB world-joint maximum error | 1.4305e−5 m (gate 5e−5 m) |
| GLB animations | 0 |
| GLB unweighted/bad vertices | 0 |

## Five-move audit

All five source actions were copied exactly at initial rehost. The derived move files then received only documented quarter-frame Hips floor correction and distal phys-bone gathering. Grip, collision, and contact values below are from the final corrected files.

| Move | Sole min | Cloth min | Max hilt drift | Collision audit |
|---|---:|---:|---:|---|
| idle_guard | +0.573 mm | +2.618 mm | 0.000431 mm | n/a |
| walk_stalk | +0.542 mm | +2.412 mm | 0.000476 mm | n/a |
| lunge_thrust | +0.521 mm | +2.278 mm | 0.000936 mm | n/a |
| rising_spin | +0.529 mm | +2.313 mm | 0.000574 mm | F40: 0 head, 0 hair overlaps; 7.857 / 6.570 mm sampled clearance |
| xslash | +0.680 mm | +2.398 mm | 0.000598 mm | F55: 0 head, 0 hair overlaps; 88.323 / 87.158 mm sampled clearance |

All numeric move gates pass: 121 bones, zero rest error, RightHand-only sword, hilt drift below 0.01 mm, no sole penetration, cloth ≥ +2 mm, and zero requested blade/head/hair overlaps.

The films decode cleanly:

- rising_spin: 116 frames, H.264/yuv420p, 768×768, 30 fps
- xslash: 90 frames, H.264/yuv420p, 768×768, 30 fps

## Visual gate

| Required visual condition | Result |
|---|---|
| Clearly closer to God A than `fullbody_i03_front.png` | PASS in overall rest-pose costume design |
| No shredded hems / edges | **FAIL** — shoulder/cape edge and removed source-hair band are visibly shredded |
| Continuous trim | **FAIL** — shoulder-area trim breaks into floating fragments |
| Sash not cutting through plates | PASS in the rest-pose Cycles views |
| Move-result integrity | **FAIL** — extended-pose stills show severe strip/stretch artifacts in fused cloth/armor regions |

Because publication requires every numeric and visual condition, the visual failures are decisive. The candidate remains on black-sky as an investigation artifact only:

- `models/astra_character_v2_body_i01.blend`
- `models/astra_character_v2_body_i01.glb`
- five `*_body_i01.blend` move files

## SHA-256

| Artifact | SHA-256 |
|---|---|
| source `meshy_body_godA.glb` | `88de396e373c242d6e6130c53348b15a202ecddf8f4a1c4620d7ed966454ddac` |
| donor `astra_character_v2_meshy_i03_defrag.blend` | `582d8c2fd417a702ac864c1919b3cf6428e6b1be9f2881cce593b29d9ad64254` |
| candidate `.blend` | `108a2b30a3b3d641bb33c246abfd61630c99b752ad4ea75069fdc3c631b8b95a` |
| candidate `.glb` | `8973e9da4e49fcb93f98b445c0ed14a50537b9739d27af010308064f20804f14` |
| idle_guard move | `81582d402bab0078f0d9144a2bb7fa8f9662cb48c8400b5b8fb1071d372d6d5f` |
| walk_stalk move | `72d75f25c89e2b4ab081e8c5d2173ba35d19641a34146748a826e64c6ea457fb` |
| lunge_thrust move | `84c6db7e20305ec0517f2f67efb7a83f3d9e12964e8b1de21b26b0c98d8b5c7f` |
| rising_spin move | `f6610388290bbf750e48a977f518a9d992f04a9310815c24b6f180aa2d257324` |
| xslash move | `7afa7f5e3e7a7616cc31d7a57347eee6db2fdb89fd59699548897ffdf27179e1` |
| rising_spin MP4 | `d8283cc6590a71b6f214ce288254c2415c6625a8f0c62c378bff1ff85b884dee` |
| xslash MP4 | `4b0ff53558a43324514c4c96ee52b5622d27b78fbb0ef25fbb9d5b2b07059812` |
| unchanged published `.blend` | `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255` |
| unchanged published `.glb` | `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5` |

## Evidence

- `renders/astra/char2/meshy_body_import.json`
- `renders/astra/char2/meshy_body_fit.json`
- `renders/astra/char2/meshy_body_build.json`
- `renders/astra/char2/meshy_body_validation.json`
- `renders/astra/char2/meshy_body_roundtrip.json`
- `renders/astra/char2/meshy_body_i01_{front,side,three_quarter}.png`
- `renders/astra/char2/meshy_body_i01_comparison.png`
- `renders/astra/rehost_body/meshy_body_moves_audit.json`
- `renders/astra/rehost_body/*_extended.png`
- `renders/astra/rehost_body/{rising_spin,xslash}.mp4`

## Honest shortfall and recommended next step

The limiting issue is the source asset, not the rig count, fit, export, or floor/contact logic. With 26,417 tiny disconnected components and hair interleaved with cape/shoulder trim, texel/spatial masking cannot produce both a clean head removal and a continuous costume boundary. Proximity transfer also has no semantic topology on which to preserve the fused garment during large poses. A publishable next iteration needs a separately generated headless/no-hair body or a remeshed and manually partitioned body with distinct rigid armor and cloth islands before binding.
