# Round 6 collar repair — promoted before head work

Canonical files: models/astra_character_v2.blend and models/astra_character_v2.glb. Recoverable copies: models/astra_character_v2_collar_banked.blend and .glb.

Replaced 29,267 inherited armor faces and removed 6,675 fractured neck/collar faces. Welded 32 coincident vertices. Zero zero-area faces were found among the removed armor; zero flipped faces required correction on the new plates; zero pre-existing boundary loops required closing. New plates have zero boundary and zero non-manifold edges. The neck graft was constructed closed.

Retained the R5 cuirass, gorget, clavicle mantle, pauldrons and upper-arm plates. Original object names/material slot lists are preserved. Original blue panel topology, rest vertices and weights are unchanged. Only the collar contact band receives an evaluated inward fit (3,915 vertices, z > 2.48m). Lower drape remains untouched. The new plates use a clean aged-brass material; original 4K atlases are untouched.

Verified 1080×1080 front and three-quarter views in both clay and textured shading, with hair held out consistently in both before and after. Comparisons: r6_collar_comparison_clay_front.png, r6_collar_comparison_clay_three_quarter.png, r6_collar_comparison_textured_front.png, r6_collar_comparison_textured_three_quarter.png.

The gorget and shoulder-top shard field is removed. This is not a whole-character visual pass: old head/ear defects and lower chest/sleeve fragments remain visible in the diagnostic stills. New plate ornament is simplified versus the concept. The garment redesign is out of scope per user ruling.

Rig: 121 bones, rest_matrix_error 0.0, zero actions. Actual hero assembly passed with zero rest-transform error. GLB reimport: 70 meshes, one 121-bone armature, zero animations. All 12 hair bones survive; spring/collision integration remains UNVALIDATED / OUTSTANDING.

Shipped-pose geometry check: rigid gorget/pauldrons retain edge lengths within 0.04%; cuirass maximum edge stretch 1.10×; temporary neck graft maximum 1.36×. Neutral restored and zero actions after test. See r6_collar_stress.json. This is a deformation measurement, not a full collision certification.
