"""Record measured results, visual limitations and preservation checks."""
from pathlib import Path
from PIL import Image
import json,numpy as np,hashlib,struct
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'renders/astra/character'
d=json.loads((P/'round2_bake_diagnostic.json').read_text());q=d['round2_quantitative_verification'];g=q['gold'];r=q['robe'];views=['front','side','three_quarter','chest','face','shoulder','sword','arms_raised']
checks={}
for v,box in [('face',(280,330,680,740)),('sword',(0,0,960,960))]:
 a=np.asarray(Image.open(P/f'after_{v}.png').crop(box)).astype(float);b=np.asarray(Image.open(P/f'round2_{v}.png').crop(box)).astype(float);delta=np.abs(a-b)
 checks[v]={'pixel_box_xyxy':list(box),'mean_absolute_8bit_difference':float(delta.mean()),'max_absolute_8bit_difference':float(delta.max()),'pixels_different_fraction':float(np.any(delta>0,axis=-1).mean())};assert delta.max()==0
for v in views:assert Image.open(P/f'round2_{v}.png').size==(960,960)
d['final_visual_review']={'reviewed_views':views,'reviewed_glb_imports':['three_quarter','arms_raised'],'face_and_sword_pixel_comparison':checks,'robe_spec_conflict':'The stated linear RGB target is honored. Under the unchanged lighting it renders pale/cornflower, not the desired deep reference blue. A separately labeled deeper-blue render-only option is supplied; no alternate RGB has been substituted into the delivered asset.','deepblue_option':{'file':'round2_deepblue_option_three_quarter.png','approximate_linear_base':[.002,.024,.217],'included_in_delivered_models':False},'remaining_gaps':['Blue shapes at inherited fractured seams/holes and intentional cloth boundaries remain; zero gold-atlas contamination is not a claim that every visible blue triangle has vanished.','Source scrollwork is retained in a repaired class mask, but fractured triangle edges still interrupt its appearance; fully smooth continuous trim is not achieved everywhere.','Robe numerical color and requested deep visual appearance conflict in the fixed evaluation rig.','Face remains waxy and hair remains a fused mass; central face render pixels match round 1 exactly.','Concurrent animation stress poses remain owed because none of the requested files existed at the single initial check.']}
d['root_cause']['certainty']='Blue contamination is measured in the old texture and UV samples. The shared margin and classification thresholds are contributing-cause inferences from the old pipeline; no controlled margin-12 versus margin-0 ablation was run. Cage projection is ruled out by saved bake settings. The replacement isolates material targets and verifies the final filtering footprints directly.'
d['final_files']={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [ROOT/'models/astra_character_v2.blend',ROOT/'models/astra_character_v2.glb']}
d['stage']='round2_final_with_round1_baseline_preserved'
(P/'round2_bake_diagnostic.json').write_text(json.dumps(d,indent=2))
def vec(a):return '('+', '.join(f'{x:.5f}' for x in a)+')'
old=d['regions']['robe_source_inset_3px']['round1_rgb_linear']['median'];new=r['core_linear_base']['median'];delta=r['core_median_delta_from_spec'];oldgold=d['uv_samples']['chest_gold'];delivery=d['delivery']
text=f'''

## Round 2 — material isolation, metallic response and literal robe RGB

The isolated armor bake now passes the numeric contamination and metallic checks, and the original geometry/weight repair and sword are preserved. **The visual brief is not fully met:** the explicitly requested linear robe RGB renders pale under the locked evaluation lighting, and inherited broken surfaces still interrupt the trim. I retained the explicit RGB requirement and supplied `round2_deepblue_option_three_quarter.png` as a clearly labeled, render-only alternative closer to the original blue. It is not silently applied to the delivered models.

### Diagnostic before edits

`round2_bake_diagnostic.json` was first written before changing materials. It retains round-1 base-color, ORM and normal measurements, source-mask interiors at 0/3/8 source pixels, and explicit UV/position samples from the chest, shoulder, lower robe and face. Both encoded PNG RGB and explicitly decoded linear RGB are recorded. Round-1 models, nine maps and NumPy audit arrays are retained in `round1_backup/`.

Blue contamination affected **{100*d['regions']['gold_source_inset_3px']['blue_in_gold_fraction']:.4f}%** of texels at least three source pixels inside the source gold mask, and **{100*oldgold['blue_fraction']:.4f}%** of gold-class chest face-centroid samples. The chest's median metallic value was **{oldgold['orm']['median'][2]:.5f}**, with roughness p05–p95 **{oldgold['orm']['p05'][1]:.3f}–{oldgold['orm']['p95'][1]:.3f}**. Its median linear base color was **{vec(oldgold['base_linear']['median'])}**.

The old bake used **12 pixels of ADJACENT_FACES margin** on a fragmented shared atlas. No cage or selected-to-active projection was enabled, so a cage pulling robe color onto armor is ruled out. Shared dilation, filtering footprints, hard texture-threshold masks in the bump field, and neutral transition colors assigned to skin are contributing-cause inferences from the pipeline; I did not run a controlled 12px-versus-0px margin ablation. Some blue triangles already exist in `before_chest.png`, so the original visual problem is not exclusively a new bake defect.

### Material and bake changes

Gold and robe now have **separate 4096² base-color/ORM/normal atlases**, using the unchanged UV coordinates. Each target is baked independently in Cycles with **4px EXTEND**, no cage and no projection from other objects. The gold graph has no blue or cloth branch. Empty atlas space is then filled from valid texels in the same material target, and gold metallic padding is exactly 1.0. This last step was added after the first verification caught 822 of 633,325 armor samples losing full metallic response at empty borders.

Gold uses three deliberate linear color zones: aged limb gold `(0.48, 0.30, 0.08)`, warmer champagne cuirass `(0.62, 0.42, 0.125)`, and paler shoulder gold `(0.68, 0.49, 0.19)`, with subtle modulation. Metallic is **1.0**. Pointiness and the smoothed existing cavity/AO signal drive a much wider roughness range. Fine brushing/engraving is substantially shallower than round 1, avoiding the large repetitive relief that softened the metallic read. The first preview looked too silver; the second bake warmed these zones and raised the roughness floor by 0.05.

The source scrollwork mask receives small-hole closure and isolated-speck removal. **30,296 border faces** use the robe/trim material so the blue cutouts defining the ornament survive; **13,239 neutral transition faces** below the protected head/neck are classified as gold or cloth instead of skin. This restores gold material response to pale transition flecks, but it does not repair broken triangle outlines. All 14,779 protected head/neck/hair faces retain their original shaders/maps. New sleeve maps remain **2048²**. The approved sword's three **2048² maps were deliberately retained byte-for-byte**, rather than resampling an already approved material; its geometry and shader are unchanged. Editable procedural sources are retained in the blend.

The GLB embeds **{len(delivery['embedded_images'])} PNGs**: nine character maps (isolated gold, robe, preserved head), three sleeve maps and three unchanged sword maps. Every material has normal and metallic/roughness textures. Isolation increases the map count from the original nine, while retaining the requested resolutions.

### Quantitative result and robe-spec comparison

Seven barycentric bilinear samples per armor triangle give **{g['core_orm']['count']:,} samples across {g['surface_faces']:,} faces**. **Zero** contain blue contamination; **100%** are fully metallic. Blue contamination also remains zero after 2×, 4× and 8× box-filter mip tests. Actual gold roughness p05–p95 is **{g['core_orm']['p05'][1]:.3f}–{g['core_orm']['p95'][1]:.3f}**. These checks cover the isolated armor material, not every blue shape visible between different surfaces in the beauty render.

- Requested robe linear RGB: **(0.08000, 0.12000, 0.35000)**.
- Round-1 median in inset source robe regions: **{vec(old)}**.
- Round-2 median across **{r['core_linear_base']['count']:,}** nonmetal lower-robe surface samples: **{vec(new)}**.
- Round-2 median minus spec: **{vec(delta)}**, at most **{100*max(r['core_median_relative_error']):.3f}%** relative error. The remaining difference is mostly 8-bit quantization and subtle fabric variation.

This numeric correction actually raises the robe's diffuse reflectance. The original reference's encoded robe median was `(0.0, 0.20392, 0.51765)`, which decodes to a much more saturated blue than the supplied linear target. The delivered RGB therefore **does not achieve the requested deep-blue appearance** under the unchanged lighting. The separate deeper-blue preview uses approximately `(0.002, 0.024, 0.217)` linear on cloth while retaining gold trim. A preference question was raised during the work; without a reply I honored the explicit numeric specification. No lighting, exposure or camera adjustment disguises this discrepancy.

### Visual review, preservation and outstanding work

I viewed all eight final **960×960 BLENDER_EEVEE** renders after the last padding correction, plus both fresh-GLB renders. They use the unchanged `astra_character_common.py` `VIEWS` values: front, side, three_quarter, chest, face, shoulder, sword and arms_raised. The original before/after PNG hashes are unchanged.

- Front, side and three-quarter: metallic highlights and dark recesses have stronger separation, and armor pieces have distinct tones. Robe remains too pale for the visual brief when the literal RGB is used.
- Chest and shoulder: shared-atlas color bleed is removed from the gold target. Blue shapes at fractured seams, holes and intentional garment boundaries remain. Coarse triangles still break the scrollwork silhouette; perfectly continuous fine trim is not achieved everywhere.
- Face: still waxy, with fused helmet-like hair. The central face box `(280, 330)–(680, 740)` is **pixel-identical** to round 1 (maximum 8-bit difference 0), confirming no regression there. Some lower hair/armor transitions remain conspicuous.
- Sword: the **entire 960px render is pixel-identical** to round 1, and all three texture hashes match the backup.
- Raised arms and GLB: the existing repaired deformation is retained. Vertex positions, polygon topology, vertex weights/group names, UV buffers, object transforms and modifier lists match the round-1 signatures exactly. The raised test still has **{delivery['raised_pose_spike_edges']} spike edges**, maximum edge **{delivery['raised_pose_longest_edge_m']:.6f} m**, and p99 stretch ratio **{delivery['raised_pose_stretch_p99']:.4f}**. Small seam openings remain; no new weighting changes were made.

**Motion stress checks remain owed.** At the single initial check, `scripts/astra_xslash_v2_poses.py` and all three `renders/astra/pose_stress_{{windup,cross,follow}}.png` files were absent. Per instruction I did not wait or check again, and therefore did not generate the six pose shoulder/cape-root close-ups. No `scripts/astra_xslash_*` files were edited. `models/godwyn_game.glb` retains its original SHA-256.
'''
f=P/'self_critique.md';oldtext=f.read_text();marker='\n## Round 2 —';oldtext=oldtext.split(marker)[0];f.write_text(oldtext.rstrip()+text)
print(json.dumps({'files':d['final_files'],'pixel_checks':checks,'quantitative_checks':'passed','visual_brief':'remaining robe/trim gaps documented'},indent=2))
