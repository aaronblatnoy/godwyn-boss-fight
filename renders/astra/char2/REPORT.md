# Godwyn character round 1 — face and skin

**Visual gate: NOT MET.** The saved model is more defined than the supplied blank-mask baseline, but it is not a photorealistic likeness of the approved man. The skin still reads waxy/synthetic; the orbital transitions, nose/alar forms, philtrum and lips need further anatomical refinement. This is an incomplete visual result, not an approved photoreal character.

## Review images

- [Before / after face, left / right](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/before_after_face.png)
- [Approved portrait](/Users/aaron_7nh0yzm/godwyn-boss-fight/face-concepts/godwyn_face_APPROVED.png)
- [Before face](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/before_face.png)
- [After face](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/after_face.png)
- [Before front](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/before_front.png)
- [After front](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/after_front.png)
- [After three-quarter face](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/after_face_three_quarter.png)
- [Fresh GLB import](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/glb_check_face.png)

All character renders use local Cycles METAL on the Apple M1 Pro, 32 samples, 960×960, AgX, exposure −0.35. Before/after cameras, lights and world match. Existing evaluation fixtures and camera definitions come from `astra_character_common.py`. The extra three-quarter face camera uses location (2.9, −5, 3.15), target (0, −0.25, 2.99), orthographic scale 0.59.

## Recon and geometry

The source `char1` has 181,435 vertices. The head above 2.78 m contains 6,464 vertices and 12,430 complete polygons, including hair. Only approximately 1,600 head polygons were assigned to the original skin slot; some skin-colored forehead polygons were assigned to gold. Median edge length in the original skin-face region is approximately 9.8 mm, with a 26.9 mm 95th percentile. This is insufficient for anatomical eyelid, lip and nostril detail.

The face needed local subdivision first. A whole-character voxel remesh would have endangered the existing UVs and skinning. The procedural pass adds local density, smooths inherited triangular planes, reshapes the forehead, cheek/chin planes, sockets, nose, lips and philtrum, and introduces faint asymmetry. Final `char1` has 253,776 vertices and 435,498 polygons. Approximately 64,642 local skin vertices were available for the sculpt before the nasal-opening cleanup. Existing body vertex positions are preserved to approximately 0.000000039 m floating-point error.

Eighteen added mesh objects provide two eyeballs, two iris surfaces, two pupils, corneas, wet lines, tear corners, eyebrows, lashes and recessed nostril liners. All are weighted to the existing Head bone. Eye optics remain spherical while the surrounding facial proportions change. Nostril openings are physical holes, although their shape remains too simplified for the reference.

The source has one UV layer, `UVMap`, sharing a full-character 4K atlas. Existing UVs are retained/interpolated during subdivision. A second layer, `AstraChar2FaceUV`, provides a dedicated planar face atlas. Its front projection is suitable for this evaluation but is not a production facial retopology/UV overhaul. Full object, topology, material-node/link, image, UV and bone inventories are in `recon.json` and `recon.log`, including an additional head UV connectivity/area assessment.

## Skin and eyes

The existing skin material name and slot are retained. The new Principled shader uses subsurface weight 0.20, RGB radius (1, 0.36, 0.17), scale 0.0012 m, IOR 1.44, and spatial roughness/specular breakup. Four packed 1536×1536 maps carry skin albedo, tangent normal, ORM and emission. An embedded 768×128 radial texture supplies hazel-green iris detail.

The canonical base (0.95, 0.90, 0.82) remains the Principled default/reference. The connected epidermal albedo map supplies warmer, darker reflectance; the visible surface is therefore not uniform canonical ivory. Canonical emission color (1, 0.88, 0.45) is filtered through a nonzero spatial map, while strength remains exactly 2.5 in both Blender and GLB. Approximate emission coverage is 0.6–8.4%, preserving gold radiance while allowing shadows to read.

Skin microdetail combines deterministic procedural fields with high-frequency skin detail extracted locally from the approved portrait. Broad illumination is removed, and eyes, brows, nostrils, lips and hair are masked out of this transfer. It does not paste a photograph of the face over the mesh. Earlier attempts with forehead hair contamination were rejected.

## What improved and what remains

Brows, hooded eyes, irises/pupils and corneal reflections are now visible. Lips and mouth separation read, the nostrils open, cheek/chin shapes are more distinct, the excessive forehead-to-lower-face ratio is reduced, and the complexion has warmer color and surface variation.

The final front and three-quarter views still look synthetic. Eyelids are too simplified, the nasal and philtrum transitions are not convincing enough, and skin response remains too smooth/waxy compared with the approved portrait. The unchanged hair shell and pre-existing hair/skin boundary defects also hurt overall realism. Hair strands/braids, armor color, robe color, shoulder seams and pose stress testing remain outside this round.

Eight procedural previews were inspected. The first two had clear protruding-eye/faceting failures; later passes corrected these, but none reached the requested photographic likeness. Final images and the saved Blender scene explicitly retain the NOT MET assessment.

## Validation and delivery

The original object names, five `char1` material slots, 121 original vertex-group names, and all 121 bone names/rest positions are preserved. The pose is neutral and the Blender file has zero actions. A repeat build reproduced the same named objects, counts, transforms and spatial vertex/face-center geometry exactly. Native Blender spheres can reorder vertex/face indices; the bidirectional geometry comparison confirms identical surfaces.

The final GLB is 124,216,260 bytes, with one skin, zero animations and 20 embedded images. All five `char1` primitives include tangents. Export-only triangulation handles subdivision boundary ngons without changing the editable saved mesh. A fresh GLB import was rendered and inspected. Cycles subsurface scattering has no exact core glTF representation; the GLB carries the portable albedo, normal, roughness, emission and eye transmission instead.

There were no environment blockers. All work stayed local; no SSH, network access, package installation or git commands were used. No writes targeted other agents' owned paths. Technical implementation and packaging were completed, but the visual target remains unfinished.

## Files and reproduction

Primary saved files:

- `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2.blend`
- `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2.glb`
- `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2_prechar2.blend` — untouched input backup
- `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2_prechar2.glb` — previous export backup
- `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2_char2_work.blend` — procedural working output

Main authoring scripts are `scripts/astra_char2_face.py` and `scripts/astra_char2_skin.py`. Run `blender --background --python scripts/astra_char2_build.py` to rebuild the working model from the backup, then `astra_char2_deliver.py` to validate, render and export. `astra_char2_glb_check.py` verifies a fresh import; `astra_char2_finalize.py` records the candid quality assessment. Use the local Blender executable `/opt/homebrew/bin/blender` and set `PYTHONDONTWRITEBYTECODE=1`.

[Exact written paths](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/written_paths.txt) lists every retained output, script and explicitly written temporary file. [Delivery manifest](/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/char2/delivery_manifest.json) records sizes and primary model hashes. Drafts and earlier diagnostic failure logs are retained for review; `validation.json` and `idempotence.json` contain the final technical results.
