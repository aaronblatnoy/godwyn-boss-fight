# Meshy graft iteration 02 — geometry/material notes

## Outcome

Iteration 02 was built as new, unpublished candidate files. The published `models/astra_character_v2.blend/.glb`, iteration-01 files, and `models/astra_character_v2_pre_likeness.blend` were treated as read-only. No render engine was invoked; every check in this pass is numeric.

- Blend: `models/astra_character_v2_meshy_i02.blend` — 187,108,213 bytes, SHA-256 `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255`.
- GLB: `models/astra_character_v2_meshy_i02.glb` — 146,416,944 bytes, SHA-256 `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5`.
- Publication status: **NOT PUBLISHED**.

## Geometry changes

- Rebuilt from the untouched Meshy GLB and the protected pre-likeness body instead of editing the defective i01 result.
- Measured the visible gorget upper rim from `AstraChar2_R5_GorgetRim` at z=2.748500109 m.
- Applied one planar non-hair bisect at z=2.605000000 m, 143.500 mm below the rim (minimum required: 25 mm).
- The source's disconnected cut segments yielded 0 direct `holes_fill` faces across 299 cut-plane vertices. The overlapping 9×64 Spine/neck/Head blend band starts on the same plane and supplies a closed 64-triangle planar bottom cap, satisfying the cap/bridge gate.
- Classified 115,340 hair faces and did not pass them through the bust bisect. Hair z-min changed by 0.0 m and z-max by 0.0 m; any nonzero lower-bound change is limited to the 232 disconnected components removed under the explicit rule: entire bounding box below the cut plane and maximum dimension <15 mm.
- Hair classification thresholds: luma ≤0.665 (strong capture ≤0.595), R−B ≥0.175, G−B ≥0.085, plus the documented outside-head-core geometry envelope in `meshy_i02_cut_audit.json`.
- Angular cut audit: 24 sectors; cut-boundary vertices above rim−25 mm: 0.

## Material change

Hair uses the original base color unchanged. The skin-classification mask `meshy_skin_mask` applies this exact node chain only to skin:

1. `Meshy i02 SPEC multiply`: MULTIPLY factor 1.0 by RGBA [0.95, 0.9, 0.82, 1.0].
2. `Meshy i02 warm HSV`: hue 0.485, saturation 1.15, value 0.92, factor 1.0.
3. `Meshy i02 skin mix`: MIX factor from `meshy_skin_mask`, original base color on input 1 and corrected skin on input 2.

The imported normal, ORM/roughness/metallic, and emission maps remain connected and packed.

For glTF portability, export converts the same mask to two standard PBR face-material slots in memory: `AstraChar2 Meshy i02 original hair and non-skin PBR` retains `Image_0`, while `AstraChar2 Meshy i02 corrected skin PBR` uses `Image_0_Meshy_i02_skin_corrected` with the identical multiply/HSV math above. The native `.blend` is not modified by this export-only conversion. Round-trip inspection confirms both materials and both images are present, and both materials retain base-color, metallic/roughness, normal, and emission texture slots.

## Gorget shards (reported, not rebuilt)

Using the audit definition “current disconnected component with ≤12 triangles and maximum bounding-box dimension <30 mm,” the existing gorget/gorget-rim contains **0** detached shard components. Each current object is one connected component; exact object bounds, centroids, boundary/nonmanifold edge counts, and any qualifying shard locations are in `meshy_i02_cut_audit.json`. The banked repair record reports 6,675 fractured neck/collar faces removed in total, including 103 final strays. Those historical removals are not counted as present i02 shard locations. No armor geometry was rebuilt or repaired.

## Numeric validation

- Native: 121 bones; 0 actions; rest-matrix error 0.0; 0 unweighted/bad-sum vertices; maximum weight-sum error 4.887580871582031e-06.
- Native arms-raised stretch: head/hair 1.000674843788147×; neck band 1.1442304849624634×.
- Native combat-stress stretch: head/hair 1.000112533569336×; neck band 1.3955484628677368×.
- GLB round trip: 121 bones; 0 actions; maximum joint-position error 1.430511474609375e-05 m (gate 5e-05 m); joint counts [121]; animations 0; 0 unweighted/bad-sum vertices.
- Round-trip arms-raised stretch: head/hair 1.0010534524917603×; neck band 1.288557767868042×.
- Round-trip combat-stress stretch: head/hair 1.0010522603988647×; neck band 1.3956036567687988×.
- Rising Spin F40 exact overlaps: head 0; hair 0.
- Rising Spin F40 sampled surface distance: head 7.494 mm; hair 6.556 mm. Assembly rest error 0.0.

## Pending GPU render, comparison, and publication

PID 3937364 / `train_marika_v2.py` was active at task start, was never signaled or otherwise touched, and ended naturally before final handoff. No render was started because this task explicitly prohibits rendering. Before running these later commands, independently confirm both approved GPUs remain available. The render script asserts OptiX and never permits CPU fallback.

```bash
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=front"
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=side"
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=three_quarter"
ssh black-sky "cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/astra_meshy_render.py -- candidate=models/astra_character_v2_meshy_i02.blend prefix=meshy_i02 only=collar"
ssh black-sky "cd ~/godwyn-boss-fight && python scripts/astra_meshy_comparison.py -- final=renders/astra/char2/meshy_i02_front.png output=renders/astra/char2/meshy_i02_approved_comparison.png"
```

Review all four i02 views and `meshy_i02_approved_comparison.png` against the approved face reference and the i01 defect renders. Only after explicit owner approval, publish without changing the banked i01 files:

```bash
ssh black-sky "cd ~/godwyn-boss-fight && cp -p models/astra_character_v2_meshy_i02.blend models/astra_character_v2.blend && cp -p models/astra_character_v2_meshy_i02.glb models/astra_character_v2.glb"
```

No git commit or push was made.
