# Meshy head-and-hair graft report

## Outcome

**Published.** `models/astra_character_v2_meshy_i01.blend/.glb` passed the native, hero-assembly, synthetic stress-pose, GLB round-trip, and Rising Spin F40 gates. The candidate is clearly closer to `face-concepts/godwyn_face_APPROVED.png` than likeness i06: it preserves the reference's long masculine face, straight narrow nose, eye spacing and lid shape, restrained mouth, center-parted layered hair, and visible braids. The current canonical pair was backed up to `models/astra_character_v2_pre_meshy.blend/.glb` before publication.

## Import findings

- Source: `models/meshy_head_approved.glb`, SHA-256 `c013834d7626564551e0777802152a4f16fbebc6bdb314739b78bf61fffab24b`.
- One imported object, `Mesh_0`: 151,654 vertices, 155,683 triangle faces, one material.
- Raw bounds: min `(-0.923820, -0.630568, -0.950737)` m; max `(0.921072, 0.635681, 0.947833)` m; size `(1.844892, 1.266249, 1.898570)` m.
- Material inventory: one Principled PBR material with packed 2048×2048 base-color (`Image_0`), ORM (`Image_1`), emission (`Image_3`), and normal (`normal`) images. These maps were preserved; the source was not repainted.
- The nominally single mesh contains 13,852 disconnected topology components. It cannot be cleanly separated into skin, eyes, hair, braids, neck and shoulders without reconstructing or repainting it.
- The imported front reads as the approved man much more convincingly than likeness i06. Profile depth and braid placement are credible. The reconstruction remains AI-smoothed, the skin lacks the reference's pore-level realism, and the rear/side hair resolves into coarse sculpted sheets with blunt tapered ends rather than individual fibers. Those limits remain in the published asset.

The pre-existing textured import renders are `meshy_import_front.png`, `meshy_import_side.png`, and `meshy_import_tq.png`. Numeric import inventory is in `meshy_import.json`, `meshy_probe.json`, `meshy_components.json`, and `meshy_colorprobe.json`.

## Fit and graft method

The untouched body source was `models/astra_character_v2_pre_likeness.blend`, SHA-256 `c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386`.

- Orientation: the GLB was already upright and facing −Y; no rotation was applied.
- Base scale: `0.31`; translation `(0.00043, -0.25190, 2.85520)` m.
- Final horizontal/depth fit: `1.05×` about the fixed MPFB eye line. Z landmarks were not changed by this clearance fit.
- MPFB reference landmarks: eye centers `(-0.052836, -0.379566, 2.976550)` and `(0.052836, -0.379566, 2.976550)` m; proxy chin `z=2.780000`; crown `z=3.158399`; ear-width proxy `0.274012` m; prior neck cut `z=2.745`; hidden collar base `z=2.605`.
- Meshy fitted proxies: eye line `z=2.976410`; chin `z=2.804670`; crown `z=3.149028`; seam `z=2.605030`. Final trimmed bounds are min `(-0.295266, -0.438172, 2.560732)` and max `(0.298592, -0.026008, 3.149028)` m.
- A conservative texture-and-position mask removed 8,451 bright lower-bust/shoulder faces while retaining the darker long hair and braids.
- The MPFB head, eye/cornea/iris/pupil/brow/lash/wetline/tear inserts, scalp, all procedural/native hair curves, controls, and portable hair meshes were removed. The twelve historical hair bones remain so the rig remains exactly 121 bones; they have no Meshy users.
- Because hair and skin are inseparable, all 144,995 retained Meshy vertices are rigidly bound to `Head`, as allowed for an unsplit head+hair mesh. A separate 9-row × 64-side neck blend band uses the proven `Spine`/`neck`/`Head` weights from `z=2.605` to `2.735` and stays inside the gorget.
- An initial inferred per-vertex neck mask was rejected after stress testing produced 47.46×/86.23× edge stretch. The rigid fused-mesh binding reduces final native Meshy edge stretch to 1.000693× arms-raised and 1.000107× combat; neck-band maxima are 1.059408× and 1.158956×.
- No subsurface change was applied: the sole imported material fuses skin, eyes, hair, ties and residual garment texels, so a skin-only SSS/emission mask could not be made reliably without repainting. Base color, roughness/metallic, normal and emission maps remain intact.

Complete numbers and the rejected-weighting rationale are in `meshy_fit.json` and `codex_meshy_graft.log`.

## Validation

### Native candidate

- Bones: **121**; actions: **0**; rest-matrix error: **0.0**.
- Referenced skinned vertices: **411,626**; unweighted/bad-sum vertices: **0**; maximum weight-sum error: `4.887580871582031e-06`.
- Legacy MPFB head absent and Meshy head present.
- Arms-raised and combat-stress renders completed in Cycles on both RTX 3060 Ti OptiX devices; neutral pose restored.
- Head/hair maximum edge stretch: `1.0006933212×` arms-raised, `1.0001069307×` combat.
- Neck-band maximum edge stretch: `1.0594083071×` arms-raised, `1.1589558125×` combat.

### Hero assembly

- Actual `astra_cine_hero_render.assemble_inputs` loader exercised with a synthetic two-key Head action.
- Bones: **121**; rest-transform maximum error: **0.0**; all armature modifier targets valid; Meshy head present.

### GLB round trip

- Exported GLB: 134,171,896 bytes; no animations.
- Imported bones: **121**; exact hierarchy retained; skin joint count `[121]`.
- Maximum round-trip world joint-position error: `1.430511474609375e-05` m (14.306 µm), below the 50 µm gate.
- Referenced skinned vertices: **517,555**; unweighted/bad-sum vertices: **0**; maximum weight-sum error: `1.3969838619232178e-07`.
- Round-trip arms-raised and combat-stress renders completed on OptiX; neutral pose restored.

### Rising Spin F40

- Rehosted `models/astra_move_rising_spin_v2_wip.blend` in memory onto the final candidate; assembly rest error **0.0**.
- Exact blade/head triangle overlaps: **0**.
- Exact blade/hair triangle overlaps: **0**.
- Sampled blade-to-head surface distance: **6.523 mm**.
- Sampled blade-to-hair surface distance: **6.523 mm**.
- No fiber-radius allowance was used. Because the GLB is fused, triangles were partitioned geometrically into central anterior head/neck-band versus remaining hair. This is an explicit classification limitation, not a claim that Meshy supplied semantic parts.

The initial 1.00× horizontal fit had 46 exact hair overlaps and only 0.457 mm head clearance; it was rejected. A 0.94× trial was worse. The final 1.05× eye-line-centered horizontal/depth fit is the first tested fit with zero overlaps for both partitions.

## Publish decision

**PUBLISH.** All required mechanical gates pass, and the final approved-reference comparison is visibly closer than `likeness_i06_approved_comparison.png`. Meshy supplies the reference's identity and hairstyle directly, while i06 remains a pale, generic MPFB phenotype with an organized procedural groom and visibly mismatched eyes, nose, mouth and jaw.

Backups made before publication:

- `models/astra_character_v2_pre_meshy.blend` — SHA-256 `955d11c06ae9d43a236d46cb038a214f87bfdfc9a554e792f83e8272b3969c63`
- `models/astra_character_v2_pre_meshy.glb` — SHA-256 `bdb404abe7f6f6e8bcfc04eb8b8bafce344a1f24f2f5e18948b06c981ba54ee6`

Published/candidate files:

- `models/astra_character_v2_meshy_i01.blend` and `models/astra_character_v2.blend` — 186,733,525 bytes; SHA-256 `5aa0abc9557c4163acd2cf4afbb2286aa36d4362df613385d37282c0920ea6e6`
- `models/astra_character_v2_meshy_i01.glb` and `models/astra_character_v2.glb` — 134,171,896 bytes; SHA-256 `5aaf8b0c76be6d526e795b531cce7d61ad773ae87bb71c8634ef222d053de5cd`

Key render SHA-256 values:

- `meshy_graft_front.png`: `89c093d1aef05c3f31258cbe5aff7e0a45848bf1ada27b5b78411b397316449b`
- `meshy_graft_side.png`: `c39ae87b7c81793bae0fc0bd968fa5c6741b181eca0c4f20bb2a9a4179953743`
- `meshy_graft_three_quarter.png`: `149708ad8201416e7f214cb7c8c574a296f84566f0ecfba8f3273315ca3896b7`
- `meshy_graft_approved_comparison.png`: `75032ac94448a682f0a9eb15ecb3d73acc93bd34615a881f1ef2e61906005f2a`
- `meshy_native_arms_raised.png`: `d4fc78542195561c02c04196ffa6b4c74cdfa7ee348402ba65aa649acc57928f`
- `meshy_native_combat_stress.png`: `3d42b2831f7e0d968218b47e7267a3b564d7f2422123f4216ce8c90f3f6f731a`
- `meshy_roundtrip_arms_raised.png`: `07fd0bd3c950547576efdfc0494d3bf63de3ead3d3efa43ab2343348eedbd4a0`
- `meshy_roundtrip_combat_stress.png`: `db965396038375dace828643d9e1b2a940d5078c1006a12cc40a515c0711e41d`
- `meshy_rising_spin_f040.png`: `bf37651cc3a65b34325c2ec4dda069f404fe4b3079a79fc8d8ed2c3add116ad1`

## Honest shortfalls

- This is a high-density, fused Meshy asset, not production facial topology. It has no facial deformation loops, separate eyeballs, strand hair, semantic skin mask, or clean welded neck ring.
- Head and hair move rigidly together on `Head`; the hidden neck band provides the only bend. This is appropriate for the supplied inseparable mesh but less anatomical than a clean skinned head/neck/hair asset.
- The back and ends of the hair are coarse sheet-like reconstructions. Braids read correctly at portrait distance but do not have procedural-fiber fidelity.
- Skin and eyes are smoother and less photoreal than the approved 2D reference. No repaint or skin-only SSS was attempted because that would violate the texture-preservation/masking constraint.
- Lower-bust removal is conservative. It is visually hidden by the gorget and armor, but the underlying Meshy topology remains thousands of disconnected patches rather than a welded manifold.
- Rising Spin clearance is an exact triangle-overlap test on a disclosed geometric head/hair partition at F40, plus sampled nearest-surface distances. It is not continuous-time collision certification.

No Blender, ffmpeg or heavy compute ran on the Mac. No `.blend` or `.glb` was copied to the Mac. No git commit or push was made.
