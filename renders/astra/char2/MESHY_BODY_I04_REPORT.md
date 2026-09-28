# Meshy God A body graft — iteration 04 report

## Decision

**NOT PUBLISHED.** I04 completed the required metal-boundary split and soft-only heat bind, but every move failed the mandatory pre-render stretch gate. Rendering was therefore forbidden and did not run. The downstream I02 grip, sole, cloth-floor, blade/head/hair, GLB round-trip, move-still, comparison, and film work was not started because the brief explicitly places all of it after a passing stretch gate.

The separated plate geometry is rigid as required (worst edge ratio 1.000371×), but the remaining soft sheet still contains welded blue-cloth-to-trim/skin edges. The blue skirt/cape override makes one endpoint Hips-only while an adjacent non-blue endpoint can retain heat weights from a limb or hand. The worst 0.878 mm rest edge reaches 759.642× in `idle_guard`, and the soft-body p99 is 71.872×–104.238× across the five moves. All five logical plate islands also open gaps over 15 mm; the worst is 616.999 mm in `xslash`.

The existing protected `head_end` midpoint remains 65.937 mm from the preserved head/hair surface versus the required 60 mm coverage gate. Thus stretch, seam-gap, and coverage publication gates all fail independently.

The canonical assets remain unchanged:

- `models/astra_character_v2.blend`: `a8748e58ddff750ddac98ae8afa5459a6104f015b8d6ef97e813c77815787255`
- `models/astra_character_v2.glb`: `17c96b5ebc52857aa0054b24d66c5bf54c2f5a5edeb2972faab899db57c257f5`

No `astra_character_v2_pre_body.blend/.glb` backups were created because publication was never authorized. No I04 GLB was exported. No `.blend` or `.glb` was copied to the Mac. No git commit or push was made.

## Execution boundary

All Blender work ran on black-sky with the required command form:

```text
ssh black-sky 'cd ~/godwyn-boss-fight && blender --background --python-exit-code 1 --python scripts/<script>.py --'
```

The Mac received only scripts, JSON, Markdown, and logs. No Blender, ffmpeg, rendering, or other heavy compute ran on the Mac.

## Source and candidate

- I03 source: `models/astra_character_v2_body_i03.blend`
  - 192,131,173 bytes
  - SHA-256 `04187a43d088c037cc4089f001e931ee67ec0b99cc6fa05710b162b09a4bb3aa`
- I04 candidate, retained on black-sky only: `models/astra_character_v2_body_i04.blend`
  - 190,201,398 bytes
  - SHA-256 `720a7abbdede3e92a69e9225a4be4f3367053163b6843f385742ac67865c7c64`

The published head/hair, NeckBlend, and sword geometry digests are unchanged. The sword remains bound only to `RightHand`.

## Metal-boundary split

The `astra_body_plate` face boundary was separated in face-select mode, which duplicated boundary vertices while preserving the original UV layer, material, and loop normals. The final objects are:

- soft body `char1`: 103,934 vertices / 195,656 faces
- rigid metal `AstraBody_I04_Plates`: 55,838 vertices / 102,573 faces

The separated metal contains 462 disconnected topological components. The required under-30-vertex merge rule assigned 457 small components to their nearest larger island, leaving five logical rigid islands. Every vertex in each island has exactly one bone at weight 1.0.

| Island | Vertices | Assigned bone | Small components merged |
|---:|---:|---|---:|
| 0 | 39,601 | LeftShoulder | 287 |
| 1 | 9,493 | LeftLeg | 120 |
| 2 | 6,289 | RightHand | 18 |
| 3 | 365 | Hips | 31 |
| 4 | 90 | RightForeArm | 1 |

Assignments are the highest I03 heat weight summed over each post-merge island. Full sums, bounds, component counts, and nearest-merge distances are in `meshy_body_i04_split.json`.

The large island 0 spans multiple anatomical regions (world z −1.268 mm to 2.791 m) but is one connected classified-metal region under the brief's literal topology and therefore receives one bone, `LeftShoulder`. That structural fact is the main cause of its large posed seam gaps.

## Soft-only heat binding and overrides

The soft object has 1,194 disconnected components. Blender's automatic heat operator could not solve the combined object, so the same `ARMATURE_AUTO` heat operation was run on temporary soft-only component meshes. All attempted components of 30 or more vertices bound successfully. The remaining 4,360 vertices were filled from the nearest heat-weighted soft vertex, following the I03 fallback convention. Six graph-smoothing passes were applied before the explicit overrides.

During heat binding, all `phys_*`, `head_end`, and `headfront` bones were non-deforming on the temporary heat proxy. The production armature was not changed.

Blue velvet was sampled from packed 2048² `Image_0.001` using the established threshold B > 1.20R, B > 1.20G, and face metallic < 0.35. It classified 72,998 soft vertices.

The belt was measured from 6,300 central pelvis-plate vertices. Their z range is 1.631177–2.050465 m; the median belt line used for I04 is **z = 1.874830 m**.

Override counts:

- 60,052 blue skirt/cape vertices: Hips-only
- 2,407 blue skirt/cape vertices: 100 mm belt blend, with leg influence removed
- 10,502 blue torso/sash vertices: restricted to Spine, Spine01, Spine02, LeftShoulder, RightShoulder
- 30,973 other soft vertices: heat weights, top four normalized
- below-belt blue vertices retaining leg influence: 0
- vertices with `phys_*` weights: 0

The optional front-slit leg influence was set to zero to prioritize the no-tearing gate.

### Structural gates

| Gate | Result |
|---|---:|
| Armature bones | 121 |
| Candidate actions | 0 |
| Rest-matrix error | 0.0 |
| Total weighted vertices | 159,772 |
| Unweighted vertices | 0 |
| Bad weight sums | 0 |
| Maximum weight-sum error | 1.41561e−7 |
| Vertices over four influences | 0 |
| Vertices with `phys_*` weights | 0 |
| Plate vertices with other than one 1.0 weight | 0 |

## Mandatory pre-render stretch gate

The exact most-extended I03/I02 frames were reused. Thresholds are soft p99 ≤ 1.6×, soft maximum ≤ 3.0×, and rigid plate maximum ≤ 1.01×.

| Move / frame | Soft p99 | Soft max | Plate max | Largest seam gap | Result |
|---|---:|---:|---:|---:|---|
| idle_guard F48 | 87.602× | 759.642× | 1.000280× | 259.907 mm | FAIL |
| walk_stalk F36 | 90.130× | 745.005× | 1.000263× | 259.908 mm | FAIL |
| lunge_thrust F40 | 91.349× | 691.033× | 1.000371× | 325.196 mm | FAIL |
| rising_spin F40 | 104.238× | 773.732× | 1.000276× | 208.988 mm | FAIL |
| xslash F55 | 71.872× | 669.457× | 1.000293× | 616.999 mm | FAIL |

Rigid-island construction succeeds: every plate maximum is far below 1.01×. The soft-body gate fails every move by a very large margin.

For the first four moves, the worst edge is the same 0.878 mm welded boundary edge. One endpoint is Hips-only and the other retains LeftUpLeg/Hips/RightUpLeg/LeftHand heat weights; its ratios are 691.033×–773.732×. In `xslash`, the worst 2.961 mm edge joins a RightHand/RightForeArm endpoint to a Hips-only endpoint and reaches 669.457×. This is the same fundamental mixed-surface problem localized one semantic boundary inward: metal is now separated, but blue cloth, gold trim, skin, and limb-adjacent non-metal geometry remain welded in the soft sheet.

### Plate-to-soft gaps

Every logical island exceeds 15 mm in every move. Maximum gaps by island and move are recorded in `meshy_body_i04_stretch.json`. The overall maxima are listed above. The least-bad island/frame result is still 19.571 mm (island 4, `idle_guard`), so no move passes the seam publication gate.

## 24-bone coverage

Twenty-three of 24 midpoint rows pass. `head_end` remains the sole failure:

- nearest surface: preserved `AstraChar2_Meshy_HeadHair`
- nearest-triangle distance: 65.937 mm
- gate: 60 mm

This is unchanged from I03 and cannot be corrected by the authorized body topology/weight changes.

## Work correctly blocked by the gate

Because `render_authorized` is false, I04 did not run:

- Cycles OptiX rest front/side/three-quarter renders
- concept comparison
- extended-pose stills or visual seam/tearing inspection
- Rising Spin or X-slash films
- grip, sole-clearance, cloth-floor, or blade/head/hair audits
- distal cloth gathering fixes
- GLB export or round-trip validation
- publication, canonical backups, or canonical replacement

This is deliberate compliance with “STRETCH GATE (must pass before any render)” and the step ordering in the I04 brief.

## Evidence copied to the Mac

- `renders/astra/char2/meshy_body_i04_probe.json`
- `renders/astra/char2/meshy_body_i04_split.json`
- `renders/astra/char2/meshy_body_i04_build.json`
- `renders/astra/rehost_body_i04/meshy_body_i04_stretch.json`
- `renders/astra/char2/codex_meshy_body_i04_probe.log`
- `renders/astra/char2/codex_meshy_body_i04_build.log`
- `renders/astra/char2/codex_meshy_body_i04_stretch.log`

The I04 candidate and five move `.blend` files remain on black-sky only.

## Known gaps

- No cloth secondary motion; all `phys_*` weights are zero.
- Skirt/leg clipping was allowed by the brief but never reached visual inspection because rendering was blocked.
- The source sword hand remains open.
- Soft cloth/trim/skin topology is still fused and tears at Hips-only/heat-weight boundaries.
- Classified metal contains anatomically broad connected islands, producing floating plates and seam gaps when assigned to one bone per island.
- The protected `head_end` coverage row remains 5.937 mm over its gate.

The next viable change would require another topology iteration that separates the remaining soft semantic boundaries and subdivides anatomically broad classified-metal connectivity. That work is outside I04's instruction to change only the stated metal split and soft-weight overrides.
