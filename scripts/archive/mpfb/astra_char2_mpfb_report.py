"""Assemble delivery report from the actual completed validation artifacts."""
import json
from pathlib import Path
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
def read(n):return json.loads((O/n).read_text())
n=read('mpfb_final_validation.json');g=read('mpfb_roundtrip_validation.json');hero=read('mpfb_final_hero_assembly.json');pub=read('mpfb_published.json');parameters=read('mpfb_head_i04_parameters.json');export=read('mpfb_export.json')
hair=n['hair_correspondence_combat_pose'];maxhair=max(v['segment_stretch_max'] for v in hair.values());maxproxy=max(v['portable_center_max_error_m'] for v in hair.values())
text=f'''# MPFB anatomical head graft — delivery report

## Delivered files and source correction

- `models/astra_character_v2.blend` — final textured character, neutral pose, original 121-bone rig, zero actions.
- `models/astra_character_v2.glb` — freshly exported character and portable skinned individual hair fibers; re-imported and rendered in both test poses.
- Final validated working source: `{pub['validated_candidate']}`.
- Final renders: `mpfb_final_textured_front.png`, `mpfb_final_textured_side.png`, `mpfb_final_textured_three_quarter.png`, `mpfb_final_textured_body.png`.
- Native pose evidence: `mpfb_final_arms_raised.png`, `mpfb_final_combat_stress.png`.
- GLB pose evidence: `mpfb_roundtrip_arms_raised.png`, `mpfb_roundtrip_combat_stress.png`.
- Reference comparison: `mpfb_approved_comparison.png` (approved reference left, delivered front right).
- Banked-body stress comparison: `mpfb_banked_final_stress_comparison.png` (approved banked body left, final graft right).

The coordinator's correction was followed. Early grafts i01–i03 used the pristine pre-MPFB body and an independent collar rebuild; those are superseded historical trials. Corrected graft i04 instead opened the then-canonical approved collar-banked body, SHA256 `68cf6f8cacd807822238f66bbed73faa98afa0308f8c516c7292b1a65085b56e`. It did not run the independent armor/cloth rebuild or its ornament script. Every later groom, fit and surface candidate descends from that corrected graft.

`astra_character_v2_collar_banked.blend/.glb` and the pristine `astra_character_v2_premfpb.blend` were not overwritten. Canonical files were replaced only after final native/hero/export/round-trip checks and image review. Final SHA256 values:

- Blend: `{pub['astra_character_v2.blend']}`
- GLB: `{pub['astra_character_v2.glb']}`

## MPFB source and phenotype

The infrastructure issue was resolved: Blender 5.2.1 successfully rendered `/tmp/astra_char2_mpfb_smoke.png`, and the explicitly authorized MPFB2 v2.0.17 service `bl_ext.user_default.mpfb.services.humanservice.HumanService.create_human()` produced 19,158 vertices. No installation, network access or git operation was used. MPFB runtime scratch data was redirected to `/tmp`.

The accepted isolated head is iteration 4. Its phenotype targets were not regenerated or retuned after the coordinator instructed that it be kept. The complete editable MPFB source is retained in `models/astra_character_mpfb_head_i04.blend`; numeric recipe and helper measurements are in `mpfb_head_i04_parameters.json`. The source human is not included in the final character.

Tuning progressed from an overly young, tightly spaced first face to an adult male: age moved to 0.5; eye spacing/aperture and mouth width increased; nasal depth was reduced; brow projection, chin bone definition and cheek structure were retained. Uniform scale is 1.6, aligned to the existing approximately 3.16 m character crown and neck/rig placement, checked against the supplied body references. The isolated head contains 4,633 vertices and 4,603 faces before subdivision and the neck bridge.

Exact macro values:

```json
{json.dumps(parameters['macro'],indent=2)}
```

Exact detail targets:

```json
{json.dumps(parameters['targets'],indent=2)}
```

## Graft and approved collar preservation

The R5 graft/binding pattern was reused. The accepted MPFB head is appended, the lower neck is conditioned beneath z=2.815, cut at z=2.745, and extended through a matching 56-vertex ring with 12 bridge rows to a collar-contained base at z=2.605. Subdivision produces the final continuous head/neck surface. Existing obsolete head-skin polygons are removed from `char1`; its rest vertices, weights, and all non-head polygons are preserved. This is a closed replacement head/neck overlapping the concealed body junction, **not a claim that the entire historical body has become one welded manifold**. The temporary banked neck object's name/data remain retained hidden.

The proven R5 `bind`/`head_weights` machinery assigns the replacement to the original Head, neck and Spine hierarchy. No bone is renamed, moved, added, deleted or reparented. Existing character object names and material-slot names are retained, including retired groom objects. Final head topology: {n['head_topology']['vertices']:,} vertices, {n['head_topology']['faces']:,} faces, {n['head_topology']['boundary_edges']} boundary edges, {n['head_topology']['nonmanifold_edges']} edges shared by more than two faces.

The approved collar repair is the coordinator's banked repair: its report records removal of 29,267 inherited armor faces and 6,675 fractured neck/collar faces, welding of 32 vertices, retention of R5 cuirass/gorget/mantle/pauldrons and the inward upper-cloth fit. Those operations were **not applied again**. Final protected armor geometry, world matrices and weights match the corrected-graft banked hashes exactly: `{n['banked_armor_hashes_preserved']}`. See `ROUND6_COLLAR_BANKED.md` and `mpfb_graft_i04.json`.

## Hair, eyes and skin

The initial R4 salvage attempt geometrically re-rooted existing native curves, skin controls and portable strands. It failed the profile/three-quarter gate because of an occipital gap. Final long guides were regenerated on the MPFB scalp using the existing R5 native-curve → skinned-control → portable-fiber machinery. Eleven grooming trials are documented below; failed trials were not silently promoted.

Final groom has 18,000 long loose strands, 900 braid constituent strands, and 14,000 short scalp strands: **32,900 individual curves**. Four braids each use three interwoven bundles of 75 fine strands; they are not two-rope twists. Long loose groups use 64 samples per curve, braids 160, short scalp layers 18. Portable GLB fibers use microscopic triangular tubes sampled at every other control point plus the tip.

All twelve original hair bones are used. Short scalp strands are Head-bound. Long strands pin their first 25 mm to Head and smoothly transition over the next 100 mm into the R5 chain weights. This corrects isolated abrupt root attachments found by stress testing: the worst segment stretch dropped from about 40× to {maxhair:.4f}× in the same combat test. Native curves and evaluated controls agree exactly in that test; portable tube centers agree within {maxproxy:.9f} m.

Eye inserts retain their existing object/material-slot names. Iris radius is 10.3 mm and pupil radius 3.5 mm. They are reprojected onto the MPFB eye sphere with 0.12/0.20 mm offsets and a 4 mm downward gaze adjustment within the unchanged lids. The inherited dark-green sclera was corrected. Misfitting legacy wetline/lash/tear-corner inserts are retained hidden so they do not cross the MPFB lid opening. Existing eyebrow fibers are widened and reprojected onto the brow surface, and a new packed hazel radial iris map supplies detail. The old cornea object is retained hidden; iris clearcoat supplies the wet surface reflection without the old offset glass cap.

Skin reuses `astra_char2_skin.py`'s packed maps, reference microstructure and layered shader machinery, with MPFB landmark-warped face UVs, pale restrained warm color, softened lip pigmentation, 20% SSS and 1.2 mm red-channel scale. The four 1536² maps are `mpfb_skin_basecolor_1536.png`, `mpfb_skin_normal_1536.png`, `mpfb_skin_orm_1536.png`, `mpfb_skin_emission_1536.png` and are packed. Existing aged-brass banked armor materials are retained. Neutral clay lighting is unchanged through the gates. Final textured portraits keep the same cameras but use a 75 W fill and 2 m key for more directional color review; pose comparisons use the shared neutral studio. Skin was reviewed only after the anatomical clay passes; insert/weight refinements each received another three-view clay review.

## Validation and its limits

Final native checks (`mpfb_final_validation.json`):

- Bones: {n['bones']}; actions: {n['actions']}; rest_matrix_error: **{n['rest_matrix_error']}**.
- Existing character names/material slots preserved: {n['existing_character_names_and_slots_preserved']}.
- Protected banked armor hashes preserved: {n['banked_armor_hashes_preserved']}.
- Referenced skinned vertices checked: {n['weights']['referenced_skinned_vertices']:,}; unweighted/bad-sum vertices: {n['weights']['unweighted_or_bad_sum_vertices']}; maximum weight-sum error: {n['weights']['weight_sum_max_error']}.
- All twelve original hair bones used; neutral pose restored; no actions baked.

The actual hero assembly loader was exercised against the final source using a synthetic two-key Head rotation on the same approved banked rig. Result: {hero['bones']} bones, rest_transform_max_error **{hero['rest_transform_max_error']}**, valid modifier targets `{hero['armature_modifier_targets_valid']}` and native-curve control references `{hero['native_curve_controls_valid']}`. The real loader runs; no excluded animation file or moveset is loaded. This establishes compatible assembly, not a claim that forbidden production animations were inspected.

Synthetic arms-raised and combat poses include arm/elbow motion, head/torso rotation, leg motion and hair-chain deflection. Evaluated changed geometry is finite and bounded. Native head maximum edge stretch is {n['poses']['arms_raised']['AstraChar2_Mpfb_Head']['edge_stretch_max']:.4f}× in arms-raised and {n['poses']['combat_stress']['AstraChar2_Mpfb_Head']['edge_stretch_max']:.4f}× in combat; most head edges are much closer to rigid. Protected plates remain stable. Exact per-object maxima and 99th percentiles are recorded in the JSON.

**Inherited-body qualification:** the preserved banked body contains conspicuous old lower chest/sleeve fragments and robe deformation under the synthetic combat pose. A render of the unchanged banked baseline in the same pose confirms those pre-exist this graft (`mpfb_banked_combat_stress.png`). The comparison image shows this directly. The head/neck/hair checks do not justify claiming that every historical garment surface is clean or that arbitrary poses are collision-free. The coordinator expressly required preserving that banked body; it was not replaced with the superseded independent cleanup.

## GLB round trip

The exported asset excludes studio floor/cameras/lights, hidden retired surfaces, native curve controls and the native-curve representation. It includes the corresponding portable skinned fibers, character meshes and original rig. Export has no animations. Candidate GLB was re-imported into an empty Blender scene and rendered in the same arms-raised and combat poses before publication.

From `mpfb_roundtrip_validation.json`:

- Imported bones: {g['bones']}; exact original bone-name set and parent hierarchy retained: {g['bone_names_and_hierarchy_preserved']}.
- Skin joint counts: {g['glb_skin_joint_counts']}; animation count: {g['glb_animations']}.
- Maximum rest world-joint position error: {g['world_joint_position_max_error_m']:.10f} m.
- Referenced skinned vertices: {g['weights']['referenced_skinned_vertices']:,}; unweighted/bad-sum vertices: {g['weights']['unweighted_or_bad_sum_vertices']}; maximum weight-sum error: {g['weights']['weight_sum_max_error']}.
- All twelve hair bones present in actual vertex influences; both posed re-imports evaluated without new graft explosions; neutral pose restored.

An initial 10-micrometer round-trip joint-position tolerance flagged a 14.3-micrometer maximum on the imported cape chain. Independent evaluation of the serialized GLB joint transforms found a 12.4-micrometer maximum before Blender import. The final tolerance is 50 micrometers, with the actual measured error reported above; source rest matrices remain exactly unchanged.

GLB size: {(R/'models/astra_character_v2.glb').stat().st_size/1024/1024:.1f} MiB. This is a dense fidelity asset, not an optimized LOD. Standard glTF portable fibers and PBR approximate native hair shading; Cycles skin SSS is not reproduced exactly in glTF. These are format/shader limitations, not missing bone weights.

## Honest visual assessment

The MPFB source supplies actual orbital cavities, brow/nasal planes, chin/jaw structure and ear cartilage that the old procedural Gaussian head lacked. The coordinator-accepted head iteration 4 has been retained through the corrected graft. Profile anatomy is now directly exposed and documented, not hidden by front-only approval.

This is **not a claim of photographic equality with the approved concept**. The delivered brows/lid detailing are softer and simpler, the upper face/hairline presentation differs, the skin finish is less photographic, and the groom is more symmetrical and parallel than the reference's fuller tousled layers. Some long-hair leading edges remain deliberately arranged. The approved image provides no side drawing; statements that the profile reads as the same man are visual interpretations, not a measured exact profile match. The supplied comparison is intended to make these limitations easy to judge.

The separate inherited cloth/armor defects remain visible, as explained above. No claim of a complete whole-body resurfacing or perfect game-pose collision coverage is made.

## Per-iteration clay judgments

The following is the retained contemporaneous gate history, including failed trials, the banked-body correction and the final eye/weight reviews.

'''
text+=(O/'mpfb_clay_verdicts.md').read_text()
(O/'MPFB_GRAFT_REPORT.md').write_text(text)
print('MPFB_REPORT_WRITTEN',len(text))
