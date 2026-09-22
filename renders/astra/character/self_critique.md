# Godwyn character v2 — self critique

The catastrophic cape spikes are removed in the raised-arm test, and the character now has real baked surface detail that survives GLB export. This is still an imperfect intermediate asset, visibly below Elden Ring production quality. The inherited fragmented geometry is the main remaining limitation.

## Source inspection

I inspected the supplied rest/front, rest/side and final animation references before editing, then extracted and inspected both source images. `char1` and `Godwyn_Sword` share one material and the same two **2048 × 2048** textures:

- `godwyn_albedo`: mostly flat gold/blue regions, coarse skin paint and color boundaries describing existing trim. It contains little fine surface shading, no convincing fabric weave, and no authored blade abrasion.
- `godwyn_metallic-godwyn_roughness`: metallic and roughness packed into blue/green channels; red is constant. Most variation distinguishes material classes rather than wear within a material. There is **no source normal texture**.

Measurements excluding three pixels around material boundaries support that assessment: robe roughness standard deviation was only **0.00191** around a mean of **0.698**. Gold roughness standard deviation was **0.01414** around **0.381**. Source robe color-channel deviations were approximately **0.0072 / 0.0024 / 0.0021**. The original 2K resolution therefore overstated the amount of actual surface information. See `source_inspection.json`, `source_1.png`, `source_2.png`, and `texture_detail_audit.json`.

## Changes and verification

**Weights and shoulder/cape separation.** I welded near-coincident seam vertices, examined the original influences and limb positions, fitted limb regions, removed arm influences from the assigned body/cape region, normalized the limb weights, and retained a maximum of four bone influences. Pure weight smoothing did not solve the connected cape/arm surfaces: it traded spikes for broad stretched sheets. The final copy also separates **2,622 connecting triangles, about 1.63% of source surface area**, along those fitted boundaries. Added skinned inner sleeves cover the resulting openings; they were reduced and recessed after visual inspection so they sit under the armor. I removed 777 small, unbound fragment vertices near the seams.

The same ±105° upper-arm test originally produced **7,778 edges longer than 20 cm whose rest length was under 12 cm**, with a worst edge of **1.506 m**. The repaired test produces **zero** such edges. The pre-final cleanup 99th-percentile edge-length ratio fell from **25.33× to 1.36×**. `weights_delivered.json` records the final saved-copy measurement after cleanup, and the fresh GLB import is shown in `glb_check_arms_raised.png`. This verifies this pose, not every possible combat animation. Small seam gaps, coarse trim and some detached-looking forms remain visible in the raised shoulder close-up.

**New texture information, not just shader settings.** Blender procedural noise, projected curved ornament, crossed thread fields, elongated scratch fields, geometric pointiness and local ambient occlusion were baked to image textures. Cycles was used only for baking; all evaluation stills use **BLENDER_EEVEE**. The final shading materials use image textures for base color, tangent-space normal and packed occlusion/roughness/metallic (ORM):

- Character: **three 4096 × 4096 maps**. The albedo is newly baked with color/patina variation; it is not just an enlargement of the original. Curved engraving surrounds the retained chest emblem and decorates plates/gauntlets. The robe has baked crossed-thread normal and roughness detail. The source atlas remains fragmented, limiting effective texel density on small islands.
- Sword: **three 2048 × 2048 maps**, using a dedicated UV layout. The blade has a cool steel finish, longitudinal abrasion and pitting; the gold hilt has worn, engraved relief. Detached hand-like source fragments above the grip were removed and the pommel was finished. A rigid one-bone skin replaces the broken imported bone-tail offset.
- Inner sleeves: **three 2048 × 2048 maps** with baked fabric weave, color and roughness.

On the source-region comparison masks, roughly **30% of gold texels** and **82% of robe texels** now have normal XY displacement greater than 0.012 from neutral. Final gold/robe roughness deviations are about **0.098 / 0.188**. These are broad texture-content measurements, affected by AO, boundaries and changed masks; they are not isolated measurements of weave or wear strength. The final bake audit finds **99.99% valid tangent-normal coverage** and **99.94% roughness coverage** on painted character texels.

**Materials and presentation.** The gold has variable polish and darker cavities; the blue cloth has a rougher response and a small sheen contribution. Skin is pale with slight subsurface scattering in Blender and a faint warm emission. The skin mask and eye contrast were corrected after an unsuccessful gold-contaminated first bake. Hair has reduced metallic response and fine striations. The evaluation rig uses the requested **(1.0, 0.92, 0.6)** warm key, cool fill, warm rim, and charcoal ground. Before/after comparison cameras, lights and exposure match; the sword's corrected evaluation placement is used for both.

**Portable export confirmed.** `models/astra_character_v2.glb` is **86,107,384 bytes** and contains **nine PNG images embedded in binary bufferViews**, each verified by its PNG header: three at 4096² and six at 2048². Every exported material references both its normal map and metallic/roughness map. ORM occlusion is connected and fabric sheen is exported through `KHR_materials_sheen`. `export_verification.json` lists every image, resolution, byte count, hash and material; `exported_gltf.json` contains the complete exported JSON. A fresh import was rendered and visually checked. Blender subsurface scattering does not have an equivalent in this GLB; its subtle skin appearance will vary by viewer. The core baked color, roughness, metallic, normal and occlusion information is portable.

## Visual review of the final stills

- **Front / side / three-quarter:** recognizable regal silhouette and preserved armor layering; the sword reads as steel. Highlights are still too broad in some gold regions, and the pooled robe hem remains lumpy.
- **Chest:** the new curved relief is plainly visible around the original emblem and on surrounding plates. It is repetitive procedural ornament, not bespoke FromSoftware heraldic carving. The source's broken plate edges and triangular blemishes remain conspicuous at this magnification.
- **Face:** skin contamination is reduced and eye contrast restored, but the face remains waxy and under-sculpted. Painted eye shapes, weak lips, rough hairline and absent lashes prevent a convincing hero close-up.
- **Shoulder / raised shoulder:** fabric weave is visible and the long stretched spikes are gone. The seam is still visibly reconstructed; inherited ragged triangles, some clipping and exposed lining remain. Proper separate garment topology and authored shoulder correctives would improve this substantially.
- **Sword / hilt:** abrasive marks, pitting and engraved gold are visible. The inherited blade is still uneven rather than cleanly forged, and scratch distribution is more procedural than art-directed.
- **Raised arms / GLB re-import:** cape no longer stretches into long sheets. Hands, sword, cloth and armor follow the rig consistently in the tested pose. Fine attachment and collision work remains.

All eight requested before/after pairs are **960 × 960 PNGs** named `before_<view>.png` and `after_<view>.png`: front, side, three_quarter, chest, face, shoulder, sword and arms_raised. Additional hilt, raised-shoulder and GLB re-import stills are included. Every generated evaluation render was viewed before further visual changes; superseded diagnostic renders remain in this folder.

## Why this still falls short

True Elden Ring quality would require clean, separately modeled armor and cloth, deliberate topology and joint correctives, a higher-quality facial sculpt with separate eyes, layered hair cards or groomed strands, authored fabric folds and trim, and plate-specific ornament/wear painting. Baking more pixels cannot repair the source's missing surfaces or turn its solid hair into strands. The delivered improvement is strongest in deformation stability, portable surface information and material separation, not in underlying anatomical or garment craftsmanship.

The original `models/godwyn_game.glb` SHA-256 is unchanged, as recorded in `export_verification.json`. Work products are confined to the new character files/scripts and this directory; the animation session's `astra_xslash_*` files were not modified.

## Round 2 — material isolation, metallic response and literal robe RGB

The isolated armor bake now passes the numeric contamination and metallic checks, and the original geometry/weight repair and sword are preserved. **The visual brief is not fully met:** the explicitly requested linear robe RGB renders pale under the locked evaluation lighting, and inherited broken surfaces still interrupt the trim. I retained the explicit RGB requirement and supplied `round2_deepblue_option_three_quarter.png` as a clearly labeled, render-only alternative closer to the original blue. It is not silently applied to the delivered models.

### Diagnostic before edits

`round2_bake_diagnostic.json` was first written before changing materials. It retains round-1 base-color, ORM and normal measurements, source-mask interiors at 0/3/8 source pixels, and explicit UV/position samples from the chest, shoulder, lower robe and face. Both encoded PNG RGB and explicitly decoded linear RGB are recorded. Round-1 models, nine maps and NumPy audit arrays are retained in `round1_backup/`.

Blue contamination affected **0.3361%** of texels at least three source pixels inside the source gold mask, and **0.3712%** of gold-class chest face-centroid samples. The chest's median metallic value was **0.96078**, with roughness p05–p95 **0.263–0.490**. Its median linear base color was **(0.65837, 0.39676, 0.03190)**.

The old bake used **12 pixels of ADJACENT_FACES margin** on a fragmented shared atlas. No cage or selected-to-active projection was enabled, so a cage pulling robe color onto armor is ruled out. Shared dilation, filtering footprints, hard texture-threshold masks in the bump field, and neutral transition colors assigned to skin are contributing-cause inferences from the pipeline; I did not run a controlled 12px-versus-0px margin ablation. Some blue triangles already exist in `before_chest.png`, so the original visual problem is not exclusively a new bake defect.

### Material and bake changes

Gold and robe now have **separate 4096² base-color/ORM/normal atlases**, using the unchanged UV coordinates. Each target is baked independently in Cycles with **4px EXTEND**, no cage and no projection from other objects. The gold graph has no blue or cloth branch. Empty atlas space is then filled from valid texels in the same material target, and gold metallic padding is exactly 1.0. This last step was added after the first verification caught 822 of 633,325 armor samples losing full metallic response at empty borders.

Gold uses three deliberate linear color zones: aged limb gold `(0.48, 0.30, 0.08)`, warmer champagne cuirass `(0.62, 0.42, 0.125)`, and paler shoulder gold `(0.68, 0.49, 0.19)`, with subtle modulation. Metallic is **1.0**. Pointiness and the smoothed existing cavity/AO signal drive a much wider roughness range. Fine brushing/engraving is substantially shallower than round 1, avoiding the large repetitive relief that softened the metallic read. The first preview looked too silver; the second bake warmed these zones and raised the roughness floor by 0.05.

The source scrollwork mask receives small-hole closure and isolated-speck removal. **30,296 border faces** use the robe/trim material so the blue cutouts defining the ornament survive; **13,239 neutral transition faces** below the protected head/neck are classified as gold or cloth instead of skin. This restores gold material response to pale transition flecks, but it does not repair broken triangle outlines. All 14,779 protected head/neck/hair faces retain their original shaders/maps. New sleeve maps remain **2048²**. The approved sword's three **2048² maps were deliberately retained byte-for-byte**, rather than resampling an already approved material; its geometry and shader are unchanged. Editable procedural sources are retained in the blend.

The GLB embeds **15 PNGs**: nine character maps (isolated gold, robe, preserved head), three sleeve maps and three unchanged sword maps. Every material has normal and metallic/roughness textures. Isolation increases the map count from the original nine, while retaining the requested resolutions.

### Quantitative result and robe-spec comparison

Seven barycentric bilinear samples per armor triangle give **633,325 samples across 90,475 faces**. **Zero** contain blue contamination; **100%** are fully metallic. Blue contamination also remains zero after 2×, 4× and 8× box-filter mip tests. Actual gold roughness p05–p95 is **0.216–0.687**. These checks cover the isolated armor material, not every blue shape visible between different surfaces in the beauty render.

- Requested robe linear RGB: **(0.08000, 0.12000, 0.35000)**.
- Round-1 median in inset source robe regions: **(0.01033, 0.01764, 0.09531)**.
- Round-2 median across **804,961** nonmetal lower-robe surface samples: **(0.08022, 0.11954, 0.35153)**.
- Round-2 median minus spec: **(0.00022, -0.00046, 0.00153)**, at most **0.438%** relative error. The remaining difference is mostly 8-bit quantization and subtle fabric variation.

This numeric correction actually raises the robe's diffuse reflectance. The original reference's encoded robe median was `(0.0, 0.20392, 0.51765)`, which decodes to a much more saturated blue than the supplied linear target. The delivered RGB therefore **does not achieve the requested deep-blue appearance** under the unchanged lighting. The separate deeper-blue preview uses approximately `(0.002, 0.024, 0.217)` linear on cloth while retaining gold trim. A preference question was raised during the work; without a reply I honored the explicit numeric specification. No lighting, exposure or camera adjustment disguises this discrepancy.

### Visual review, preservation and outstanding work

I viewed all eight final **960×960 BLENDER_EEVEE** renders after the last padding correction, plus both fresh-GLB renders. They use the unchanged `astra_character_common.py` `VIEWS` values: front, side, three_quarter, chest, face, shoulder, sword and arms_raised. The original before/after PNG hashes are unchanged.

- Front, side and three-quarter: metallic highlights and dark recesses have stronger separation, and armor pieces have distinct tones. Robe remains too pale for the visual brief when the literal RGB is used.
- Chest and shoulder: shared-atlas color bleed is removed from the gold target. Blue shapes at fractured seams, holes and intentional garment boundaries remain. Coarse triangles still break the scrollwork silhouette; perfectly continuous fine trim is not achieved everywhere.
- Face: still waxy, with fused helmet-like hair. The central face box `(280, 330)–(680, 740)` is **pixel-identical** to round 1 (maximum 8-bit difference 0), confirming no regression there. Some lower hair/armor transitions remain conspicuous.
- Sword: the **entire 960px render is pixel-identical** to round 1, and all three texture hashes match the backup.
- Raised arms and GLB: the existing repaired deformation is retained. Vertex positions, polygon topology, vertex weights/group names, UV buffers, object transforms and modifier lists match the round-1 signatures exactly. The raised test still has **0 spike edges**, maximum edge **0.117782 m**, and p99 stretch ratio **1.3571**. Small seam openings remain; no new weighting changes were made.

**Motion stress checks remain owed.** At the single initial check, `scripts/astra_xslash_v2_poses.py` and all three `renders/astra/pose_stress_{windup,cross,follow}.png` files were absent. Per instruction I did not wait or check again, and therefore did not generate the six pose shoulder/cape-root close-ups. No `scripts/astra_xslash_*` files were edited. `models/godwyn_game.glb` retains its original SHA-256.
