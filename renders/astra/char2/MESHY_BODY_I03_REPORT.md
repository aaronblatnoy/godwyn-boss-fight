# Meshy God A body graft — iteration 03 report

## Decision

**NOT PUBLISHED.** I03 materially improves the accepted I02 deformation failure, but it does not pass the mandatory pre-render stretch gate. No I03 still, Cycles render, comparison, or film was rendered, because the brief explicitly forbids rendering until all five moves pass that gate. The full contact/collision audit and GLB round-trip were likewise not started after the blocking gate failed.

The canonical assets remain unchanged:

- `models/astra_character_v2.blend`: `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255`
- `models/astra_character_v2.glb`: `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5`

No `astra_character_v2_pre_body.blend/.glb` backups were created because publication was never authorized. No `.blend` or `.glb` was copied to the Mac. No git commit or push was made.

## Execution boundary

All Blender work ran on black-sky using the required form:

```text
ssh black-sky 'cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/<script>.py -- <args>'
```

The Mac received only scripts, JSON, Markdown, PNG inspection input, and logs. The supervisor log is `renders/astra/char2/codex_meshy_body_i03.log`.

## Source and preserved assets

I03 opened `models/astra_character_v2_body_i02.blend` as the saved I02 cleaned/welded/segmented/fitted intermediate. The replacement body remained 149,413 vertices / 298,229 faces with the existing PBR material and `astra_body_plate` classification.

Geometry digests before and after the build prove that these objects were unchanged:

- `AstraChar2_Meshy_HeadHair`
- `AstraChar2_Meshy_NeckBlend`
- `Godwyn_Sword`

The sword retains its `RightHand`-only binding.

## Rigid pre-pose

The fitted source joint chains were aligned sequentially to the production rest rig with nearest inferred bone-segment membership and a 40 mm smooth joint band. Child transforms used the already-corrected parent target.

| Segment | Before | After | Assigned vertices |
|---|---:|---:|---:|
| LeftArm | 0.621° | 0.000° | 6,624 |
| LeftForeArm | 0.000° | 0.000° | 6,026 |
| LeftHand | 0.000° | 0.000° | 4,698 |
| RightArm | 4.692° | 0.000° | 4,606 |
| RightForeArm | 47.008° | 0.000° | 7,407 |
| RightHand | 40.699° | 0.000° | 4,094 |
| LeftUpLeg | 0.212° | 0.000° | 10,798 |
| LeftLeg | 0.877° | 0.000° | 18,094 |
| LeftFoot | 0.000° | 0.000° | 6,978 |
| RightUpLeg | 1.019° | 0.000° | 9,158 |
| RightLeg | 0.874° | 0.000° | 16,774 |
| RightFoot | 0.000° | 0.000° | 6,999 |

The mandatory right forearm and hand angle gate therefore passes (both are within 5° after correction). RightForeArm midpoint coverage improved from I02's 186.865 mm vertex distance to an enclosed midpoint with 45.061 mm nearest-triangle distance. RightHand improved from 199.544 mm to 13.074 mm.

### 24-bone coverage

Twenty-three of 24 rows pass. `head_end` remains the sole failure at 65.937 mm versus the 60 mm gate. A separate all-visible-mesh probe confirmed the preserved head/hair is the nearest final surface; every other visible object is farther away. Altering that result would require moving the protected published head/hair or changing the rig rest, both forbidden.

## Heat binding

The exact automatic-weight operator was:

```python
bpy.ops.object.parent_set(type="ARMATURE_AUTO", keep_transform=True)
```

It returned `{'FINISHED'}`. The operator ran against a temporary duplicate of `Armature` so the production rest rig could remain byte-for-byte unchanged. On the duplicate only, heat-deform bones were restricted to the body chain, all `phys_*`, `head_end`, and `headfront` deformation was disabled, and the rig's unusually long display/control tails were temporarily represented as anatomical head-to-child-head segments. The heat weights were then extracted, the duplicate was deleted, and the body was parented to the untouched production `Armature`.

Heat weighting produced zero unweighted vertices, so the specified nearest-weighted-vertex fallback count is zero. The binding then used six graph-smoothing passes, a 40 mm metallic transition band, and 30 harmonic transition passes around fixed plate cores. Non-core vertices were limited to their top four normalized body-bone weights. All `phys_*` weights are zero.

| Gate | Result |
|---|---:|
| Armature bones | 121 |
| Candidate actions | 0 |
| Rest-matrix error | 0.0 |
| Unweighted body vertices | 0 |
| Bad weight sums | 0 |
| Maximum weight-sum error | 1.4674e-7 |
| Vertices over four influences | 0 |
| Vertices with `phys_*` weights | 0 |
| Classified plate vertices | 55,838 |
| Fixed rigid-core vertices | 14,330 |
| 40 mm heat-transition vertices | 41,508 |
| Rigid plate-core islands | 114 |

Known gap: the new robe/cape has no cloth secondary motion in I03. That is intentional for this iteration and remains future work.

## Mandatory pre-render stretch gate

The exact most-extended frames were loaded from `renders/astra/rehost_body_i02/meshy_body_move_stills.json`. Thresholds were p99 ≤ 1.6×, maximum ≤ 3.0×, and rigid plate-island maximum ≤ 1.01×.

| Move / frame | I02 p99 | I03 p99 | I02 max | I03 max | Plate max | Pass |
|---|---:|---:|---:|---:|---:|---|
| idle_guard F48 | 61.581× | 4.744× | 674.302× | 104.426× | 1.000280× | No |
| walk_stalk F36 | 65.884× | 4.886× | 787.082× | 107.576× | 1.000243× | No |
| lunge_thrust F40 | 73.787× | 5.632× | 1,141.381× | 104.760× | 1.000331× | No |
| rising_spin F40 | 71.561× | 6.354× | 782.785× | 106.334× | 1.000247× | No |
| xslash F55 | 48.382× | 5.726× | 573.075× | 100.454× | 1.000293× | No |

I03 improves p99 by roughly 8.4×–13.5× and maximum stretch by roughly 5.7×–10.9× over I02. Every rigid plate-core interior passes comfortably. The body-wide gate still fails every move.

The final category audit localizes the remaining problem:

- 38,303 same-island rigid plate edges: maximum 1.000331× or better in all moves.
- 0 direct cross-island rigid edges after the 40 mm erosion/transition repair.
- 8,551 rigid-core-to-transition boundary edges: p99 16.993×–22.788×.
- 400,959 non-core edges: p99 4.599×–6.181×.

Worst edges and both endpoint weight sets are recorded per move in `meshy_body_i03_stretch.json`. Representative failures remain tiny 2–6 mm welded edges at articulated transitions such as LeftArm/LeftShoulder, Hips/LeftUpLeg, and LeftLeg/LeftFoot.

## Structural conclusion

The required binding method is materially better than I02 proximity transfer, but weights alone cannot satisfy the combined topology and gate constraints on this source. The metallic, cloth, trim, skin, and limb surfaces are a single welded sheet. Keeping plate cores single-bone rigid while preserving those welded cross-material edges necessarily creates large edge extension during the production moves; smoothing enough to eliminate it would make the plate cores non-rigid and violate the other mandatory gate.

A viable next iteration must change topology before binding: separate plate islands and cloth panels along semantic boundaries (with UV-preserving vertex duplication or retopology), then heat-bind the articulated body/cloth and rigid-bind each disconnected plate. That is outside I03's hard rule to change only pre-pose and binding.

## Candidate artifacts (black-sky only)

- `models/astra_character_v2_body_i03.blend` — 192,131,173 bytes — `04187a43d088c037cc4089f001e931ee67ec0b99cc6fa05710b162b09a4bb3aa`
- `models/astra_character_v2_body_i03.glb` — 62,342,332 bytes — `2d29ebeda8b51356780ed51ce844a15c5dbd496c7727160f6633f0455587a91c`
- Five I03 move `.blend` files remain on black-sky only.

The GLB was exported but its round-trip audit was intentionally not run after the mandatory stretch gate failed.

## Evidence copied to the Mac

- `renders/astra/char2/meshy_body_i03_prepose.json`
- `renders/astra/char2/meshy_body_i03_build.json`
- `renders/astra/char2/meshy_body_i03_head_end_probe.json`
- `renders/astra/rehost_body_i03/meshy_body_i03_stretch.json`
- `renders/astra/rehost_body_i03/meshy_body_i03_stretch_regions.json`
- `renders/astra/char2/codex_meshy_body_i03.log`

No render or video evidence exists for I03 because `render_authorized` is false.
