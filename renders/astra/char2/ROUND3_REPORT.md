Round 3 delivery — visual quality gate NOT MET. Updated assets are inspectable and loadable; they are not approved for the hero render.

Hero render input: `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2.blend`.
Portable asset: `/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2.glb`.
Round-start backups: `models/astra_character_v2_preround3.blend` and `.glb`. A pre-weight-repair checkpoint is `models/astra_character_v2_r3_preweights.blend`.

**Visible changes and their limits**

- Geometry: removed 5,581 detached sliver faces; welded 721 seam vertices; filled 1,037 small boundary holes. Local cloth fairing preserved substantial panels and their overall silhouette. Large connected collar, shoulder, elbow and skirt fractures remain plainly visible. This is a partial repair, not a topology pass approval.
- Cloth: changed glaring blue toward deep indigo/violet. Sheen weight is 0.65 on cloth, suppressed by the existing metallic trim mask; sheen tint is linear (0.035, 0.020, 0.090), roughness 0.75. Cloth roughness is 0.78. Final cloth-only albedo multipliers versus its existing atlas are approximately (0.042, 0.018, 0.046); trim uses a separate brass multiplier. The result is darker and less plastic, but still lacks the reference’s convincing velvet nap and clean tailoring.
- Gold: retained metallic=1, original 4096 atlas layout and three tonal zones. Applied linear RGB multipliers (0.63, 0.62, 0.72), additional AO-based recess darkening (0.65 + 0.35*AO), and +0.10 roughness. The upper armor still reads too bright and lumpy compared with the approved antique brass.
- Relief: recovered fine height from existing normal-map slopes and physically displaced the existing tessellation: nominal ±0.35 mm gold and up to +0.6 mm metallic cloth trim before the retained Smooth modifier. This geometry survives GLB export. Linked height/displacement nodes are retained for inspection with shader scale zero to prevent applying the already-baked geometry displacement twice. Added 26 surface-conforming chased-laurel paths, radius 0.65 mm, with underlying plate weights. Their sparse wire-like appearance is not adequate ornate engraving. Existing cloth topology is too irregular for crisp embroidered leaf relief at this tessellation.
- Hair: portable Principled anisotropy 0.72; 1,351 new fine fiber segments, including two three-bundle plaits, weighted to the eight existing front hair bones. Reassigned 140 hair-weighted faces from metallic armor to the existing hair material slot. The original solid hair masses and rope-like sections remain dominant, particularly in side/back views. This is not a full strand-groom rebuild or a full fiber-scattering shader.
- Face: retained the approved-reference framing and established proportions, increased normal-map strength from 0.85 to 1.35, reduced uniform specular response, softened lip relief by less than 1 mm and moved/darkened the nostril liners. Visible pores are improved, but they can read as fine grit. The face remains synthetic: blocky sockets, glassy staring eyes, molded lips, simplified nostrils and insufficient anatomical transitions. The side-by-side does not pass photorealism.

**Emission reconciliation**

The audit value of approximately 0.014 is compatible with the actual material. The Principled emission strength is 2.5, but its color is driven by an intentionally attenuated emission texture, not the unmasked canonical (1.0, 0.88, 0.45). The measured 8-bit texture red channel has min/median/max 0.0033465 / 0.0103298 / 0.0331048 in linear space. Multiplication by 2.5 yields effective red emission 0.0083663 / 0.0258246 / 0.0827619. These are whole-atlas statistics, not an area-weighted face average. The audit’s 0.014 corresponds to a 0.0056 multiplier, or 0.56% of unmasked canonical red emission. This is intentional textured attenuation, NOT compliance with a uniform effective emission of 2.5. It was retained this round to avoid washing out structure.

Skin SSS is 0.18, reddish radius (1.0, 0.36, 0.17), scale 0.0013 m; specular IOR level 0.27. Ear/nostril rim translucency still does not visibly match the reference. Core glTF does not reproduce Cycles SSS exactly.

**Shipped stress poses**

Applied the motion agent’s read-only pose definitions at frames 30, 41 and 60. Final repair smoothed 21,903 local vertex weights over existing surface connections, with four influences maximum in the repaired region and a 6 cm transition. It does not change vertex positions, rest bones or cloth-panel structure. Rebound the added chased relief to the repaired plate weights.

The following ratios compare deformed edge length to neutral length, excluding edges shorter than 0.5 mm. Shoulder and cape-root spatial regions include adjacent armor/hair; cloth-only submetrics are recorded separately in r3_stress.json. A normalized weight sum is a technical check, not a visual deformation pass.

- windup: shoulder p95 stretch 1.23×; cape-root p95 1.92× (before local weight repair 12.56×). Cape-root maximum 8.21×. Visual verdict: FAIL — attachments remain, but residual pinching, interpenetration and fractured surfaces remain.
- cross: shoulder p95 stretch 1.61×; cape-root p95 1.90× (before local weight repair 11.35×). Cape-root maximum 7.91×. Visual verdict: FAIL — attachments remain, but residual pinching, interpenetration and fractured surfaces remain.
- follow: shoulder p95 stretch 1.49×; cape-root p95 2.01× (before local weight repair 12.95×). Cape-root maximum 8.92×. Visual verdict: FAIL — attachments remain, but residual pinching, interpenetration and fractured surfaces remain.

Weight sums on referenced char1 vertices: zero-weight 0; nonunit sums 0. The final file is neutral and animation-clean. All six final shoulder/cape-root images are under renders/astra/char2/stress_*.png.

**Rig, export and physics status**

Fresh GLB re-import succeeded: 187,126,684 bytes, 1 skin, 121 joints, 0 animations. Original object names, material-slot lists, vertex-group names and bone rest transforms were preserved. Native actions: 0; nonidentity pose bones: 0. Export includes KHR_materials_sheen, KHR_materials_anisotropy and KHR_materials_emissive_strength. Dedicated embedded sheen-mask textures preserve the native cloth/metallic-trim separation; the exporter otherwise omitted this linked arithmetic.

Twelve inherited hair bones survive export; eight front bones now also drive the added fibers. Full hair physics is OUTSTANDING. The frontal cap fibers remain head-weighted, the old solid groom remains, and no spring/jiggle simulation was installed or validated. The inherited hair bone world lengths are anomalous for this character (see r3_preservation.json); rest transforms were intentionally preserved. The presence of exported bone chains is not a physics-ready sign-off.

**Garment structure and document contradictions**

The model has a waist sash/front tabard, floor-reaching side/back panels, and an asymmetric shoulder drape/underlayer integrated with the armor. It is not simply a standalone robe or only a back cape. The central front panel ends above the floor, so the specified floor-length primary front tabard is not fully met. Panels were not restructured.

- SPEC covered breastplate/greaves/sabatons conflicts with CLAUDE invariant 4’s exposed chest/bare feet. Kept covered chest and boots as explicitly instructed; did not edit either document.
- CLAUDE’s gold (0.82, 0.65, 0.15) is brighter/more saturated than the approved aged-brass reference. Used the concept-directed atlas rebalance described above, retaining the three existing zones.
- SPEC’s exposed-arms wording elsewhere conflicts with its near-full armor coverage/face-only exposure description. No new exposure was invented.
- The approved face image exposes the upper chest; its face remains binding while the separately instructed armor coverage remains intact.
- Older boss-fight.txt spear choreography and Miquella-on-back wording differ from the sword/roots sequence in SPEC. No animation or cinematic files were changed.

**Evidence and exact written files**

- renders/astra/char2/sidebyside_face.png — approved reference left, final native render right, matched 1610-pixel height.
- renders/astra/char2/sidebyside_hair.png — matching wider hair views, before left/after right.
- renders/astra/char2/sidebyside_gold.png and sidebyside_cloth.png — matching 1080-square views, before left/after right.
- renders/astra/char2/after_face.png, after_face_three_quarter.png, after_front.png, after_hair.png, after_gold.png, after_cloth.png.
- renders/astra/char2/r3_written_files.json enumerates every delivered/modified path, including scripts, textures, logs, checkpoints and all six stress images.

Reproduce the asset from the immutable round-start input with PYTHONDONTWRITEBYTECODE=1 python3 scripts/astra_char2_r3_pipeline.py. It runs individual local Blender stills, preserves the allowed path boundaries, and exports without animation. No git, network, installs, Pillow or remote rendering was used.

The unresolved production blockers are the large connected topology fractures, residual deformation errors, solid underlying hair, unvalidated hair physics, incomplete ornate relief, and the synthetic face. The main improvements are a substantially better cloth color/material response, small defect cleanup, and reduced pose-induced weight spikes. Those improvements do not amount to the approved photoreal character.
