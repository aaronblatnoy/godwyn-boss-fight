# MPFB anatomical head graft — delivery report

## Delivered files and source correction

- `models/astra_character_v2.blend` — final textured character, neutral pose, original 121-bone rig, zero actions.
- `models/astra_character_v2.glb` — freshly exported character and portable skinned individual hair fibers; re-imported and rendered in both test poses.
- Final validated working source: `models/astra_character_v2_mpfb_surface_finish_i03.blend`.
- Final renders: `mpfb_final_textured_front.png`, `mpfb_final_textured_side.png`, `mpfb_final_textured_three_quarter.png`, `mpfb_final_textured_body.png`.
- Native pose evidence: `mpfb_final_arms_raised.png`, `mpfb_final_combat_stress.png`.
- GLB pose evidence: `mpfb_roundtrip_arms_raised.png`, `mpfb_roundtrip_combat_stress.png`.
- Reference comparison: `mpfb_approved_comparison.png` (approved reference left, delivered front right).
- Banked-body stress comparison: `mpfb_banked_final_stress_comparison.png` (approved banked body left, final graft right).

The coordinator's correction was followed. Early grafts i01–i03 used the pristine pre-MPFB body and an independent collar rebuild; those are superseded historical trials. Corrected graft i04 instead opened the then-canonical approved collar-banked body, SHA256 `68cf6f8cacd807822238f66bbed73faa98afa0308f8c516c7292b1a65085b56e`. It did not run the independent armor/cloth rebuild or its ornament script. Every later groom, fit and surface candidate descends from that corrected graft.

`astra_character_v2_collar_banked.blend/.glb` and the pristine `astra_character_v2_premfpb.blend` were not overwritten. Canonical files were replaced only after final native/hero/export/round-trip checks and image review. Final SHA256 values:

- Blend: `c5a691c624a67ff299f2bb2822fd04346e4bb6184e0273a2fa8dba9869a86386`
- GLB: `74674393fbc8447b084d62f4ed89f6c44b6b145a720f840926e10ac225fe8775`

## MPFB source and phenotype

The infrastructure issue was resolved: Blender 5.2.1 successfully rendered `/tmp/astra_char2_mpfb_smoke.png`, and the explicitly authorized MPFB2 v2.0.17 service `bl_ext.user_default.mpfb.services.humanservice.HumanService.create_human()` produced 19,158 vertices. No installation, network access or git operation was used. MPFB runtime scratch data was redirected to `/tmp`.

The accepted isolated head is iteration 4. Its phenotype targets were not regenerated or retuned after the coordinator instructed that it be kept. The complete editable MPFB source is retained in `models/astra_character_mpfb_head_i04.blend`; numeric recipe and helper measurements are in `mpfb_head_i04_parameters.json`. The source human is not included in the final character.

Tuning progressed from an overly young, tightly spaced first face to an adult male: age moved to 0.5; eye spacing/aperture and mouth width increased; nasal depth was reduced; brow projection, chin bone definition and cheek structure were retained. Uniform scale is 1.6, aligned to the existing approximately 3.16 m character crown and neck/rig placement, checked against the supplied body references. The isolated head contains 4,633 vertices and 4,603 faces before subdivision and the neck bridge.

Exact macro values:

```json
{
  "gender": 1.0,
  "age": 0.5,
  "muscle": 0.58,
  "weight": 0.34,
  "proportions": 0.65,
  "height": 0.5,
  "cupsize": 0.5,
  "firmness": 0.5,
  "race": {
    "caucasian": 1.0,
    "asian": 0.0,
    "african": 0.0
  }
}
```

Exact detail targets:

```json
{
  "head/head-rectangular": 0.12,
  "head/head-oval": 0.2,
  "head/head-scale-vert-incr": 0.24,
  "chin/chin-width-incr": 0.06,
  "chin/chin-bones-incr": 0.3,
  "chin/chin-prominent-incr": 0.1,
  "eyebrows/eyebrows-trans-forward": 0.38,
  "eyebrows/eyebrows-trans-down": 0.12,
  "nose/nose-greek-incr": 0.28,
  "nose/nose-width3-decr": 0.16,
  "mouth/mouth-scale-horiz-incr": 0.6,
  "mouth/mouth-lowerlip-volume-decr": 0.08,
  "eyes/l-eye-push2-in": 0.26,
  "cheek/l-cheek-bones-incr": 0.28,
  "ears/l-ear-scale-decr": 0.08,
  "eyes/r-eye-push2-in": 0.26,
  "cheek/r-cheek-bones-incr": 0.28,
  "ears/r-ear-scale-decr": 0.08,
  "nose/nose-scale-vert-incr": 0.15,
  "mouth/mouth-upperlip-volume-incr": 0.1,
  "eyes/l-eye-trans-out": 0.8,
  "eyes/r-eye-trans-out": 0.8,
  "nose/nose-scale-depth-decr": 0.28,
  "nose/nose-point-up": 0.08,
  "head/head-fat-decr": 0.16,
  "chin/chin-height-incr": 0.08,
  "eyes/l-eye-scale-incr": 0.12,
  "cheek/l-cheek-inner-decr": 0.14,
  "eyes/r-eye-scale-incr": 0.12,
  "cheek/r-cheek-inner-decr": 0.14,
  "head/head-back-scale-depth-decr": 0.15,
  "eyes/l-eye-height2-incr": 0.5,
  "eyes/l-eye-height1-incr": 0.12,
  "eyes/l-eye-height3-incr": 0.12,
  "eyes/r-eye-height2-incr": 0.5,
  "eyes/r-eye-height1-incr": 0.12,
  "eyes/r-eye-height3-incr": 0.12
}
```

## Graft and approved collar preservation

The R5 graft/binding pattern was reused. The accepted MPFB head is appended, the lower neck is conditioned beneath z=2.815, cut at z=2.745, and extended through a matching 56-vertex ring with 12 bridge rows to a collar-contained base at z=2.605. Subdivision produces the final continuous head/neck surface. Existing obsolete head-skin polygons are removed from `char1`; its rest vertices, weights, and all non-head polygons are preserved. This is a closed replacement head/neck overlapping the concealed body junction, **not a claim that the entire historical body has become one welded manifold**. The temporary banked neck object's name/data remain retained hidden.

The proven R5 `bind`/`head_weights` machinery assigns the replacement to the original Head, neck and Spine hierarchy. No bone is renamed, moved, added, deleted or reparented. Existing character object names and material-slot names are retained, including retired groom objects. Final head topology: 79,522 vertices, 79,520 faces, 0 boundary edges, 0 edges shared by more than two faces.

The approved collar repair is the coordinator's banked repair: its report records removal of 29,267 inherited armor faces and 6,675 fractured neck/collar faces, welding of 32 vertices, retention of R5 cuirass/gorget/mantle/pauldrons and the inward upper-cloth fit. Those operations were **not applied again**. Final protected armor geometry, world matrices and weights match the corrected-graft banked hashes exactly: `True`. See `ROUND6_COLLAR_BANKED.md` and `mpfb_graft_i04.json`.

## Hair, eyes and skin

The initial R4 salvage attempt geometrically re-rooted existing native curves, skin controls and portable strands. It failed the profile/three-quarter gate because of an occipital gap. Final long guides were regenerated on the MPFB scalp using the existing R5 native-curve → skinned-control → portable-fiber machinery. Eleven grooming trials are documented below; failed trials were not silently promoted.

Final groom has 18,000 long loose strands, 900 braid constituent strands, and 14,000 short scalp strands: **32,900 individual curves**. Four braids each use three interwoven bundles of 75 fine strands; they are not two-rope twists. Long loose groups use 64 samples per curve, braids 160, short scalp layers 18. Portable GLB fibers use microscopic triangular tubes sampled at every other control point plus the tip.

All twelve original hair bones are used. Short scalp strands are Head-bound. Long strands pin their first 25 mm to Head and smoothly transition over the next 100 mm into the R5 chain weights. This corrects isolated abrupt root attachments found by stress testing: the worst segment stretch dropped from about 40× to 1.5045× in the same combat test. Native curves and evaluated controls agree exactly in that test; portable tube centers agree within 0.000001192 m.

Eye inserts retain their existing object/material-slot names. Iris radius is 10.3 mm and pupil radius 3.5 mm. They are reprojected onto the MPFB eye sphere with 0.12/0.20 mm offsets and a 4 mm downward gaze adjustment within the unchanged lids. The inherited dark-green sclera was corrected. Misfitting legacy wetline/lash/tear-corner inserts are retained hidden so they do not cross the MPFB lid opening. Existing eyebrow fibers are widened and reprojected onto the brow surface, and a new packed hazel radial iris map supplies detail. The old cornea object is retained hidden; iris clearcoat supplies the wet surface reflection without the old offset glass cap.

Skin reuses `astra_char2_skin.py`'s packed maps, reference microstructure and layered shader machinery, with MPFB landmark-warped face UVs, pale restrained warm color, softened lip pigmentation, 20% SSS and 1.2 mm red-channel scale. The four 1536² maps are `mpfb_skin_basecolor_1536.png`, `mpfb_skin_normal_1536.png`, `mpfb_skin_orm_1536.png`, `mpfb_skin_emission_1536.png` and are packed. Existing aged-brass banked armor materials are retained. Neutral clay lighting is unchanged through the gates. Final textured portraits keep the same cameras but use a 75 W fill and 2 m key for more directional color review; pose comparisons use the shared neutral studio. Skin was reviewed only after the anatomical clay passes; insert/weight refinements each received another three-view clay review.

## Validation and its limits

Final native checks (`mpfb_final_validation.json`):

- Bones: 121; actions: 0; rest_matrix_error: **0.0**.
- Existing character names/material slots preserved: True.
- Protected banked armor hashes preserved: True.
- Referenced skinned vertices checked: 2,795,849; unweighted/bad-sum vertices: 0; maximum weight-sum error: 0.0009765625.
- All twelve original hair bones used; neutral pose restored; no actions baked.

The actual hero assembly loader was exercised against the final source using a synthetic two-key Head rotation on the same approved banked rig. Result: 121 bones, rest_transform_max_error **0.0**, valid modifier targets `True` and native-curve control references `True`. The real loader runs; no excluded animation file or moveset is loaded. This establishes compatible assembly, not a claim that forbidden production animations were inspected.

Synthetic arms-raised and combat poses include arm/elbow motion, head/torso rotation, leg motion and hair-chain deflection. Evaluated changed geometry is finite and bounded. Native head maximum edge stretch is 1.1425× in arms-raised and 1.2952× in combat; most head edges are much closer to rigid. Protected plates remain stable. Exact per-object maxima and 99th percentiles are recorded in the JSON.

**Inherited-body qualification:** the preserved banked body contains conspicuous old lower chest/sleeve fragments and robe deformation under the synthetic combat pose. A render of the unchanged banked baseline in the same pose confirms those pre-exist this graft (`mpfb_banked_combat_stress.png`). The comparison image shows this directly. The head/neck/hair checks do not justify claiming that every historical garment surface is clean or that arbitrary poses are collision-free. The coordinator expressly required preserving that banked body; it was not replaced with the superseded independent cleanup.

## GLB round trip

The exported asset excludes studio floor/cameras/lights, hidden retired surfaces, native curve controls and the native-curve representation. It includes the corresponding portable skinned fibers, character meshes and original rig. Export has no animations. Candidate GLB was re-imported into an empty Blender scene and rendered in the same arms-raised and combat poses before publication.

From `mpfb_roundtrip_validation.json`:

- Imported bones: 121; exact original bone-name set and parent hierarchy retained: True.
- Skin joint counts: [121]; animation count: 0.
- Maximum rest world-joint position error: 0.0000143051 m.
- Referenced skinned vertices: 2,902,726; unweighted/bad-sum vertices: 0; maximum weight-sum error: 1.3969838619232178e-07.
- All twelve hair bones present in actual vertex influences; both posed re-imports evaluated without new graft explosions; neutral pose restored.

An initial 10-micrometer round-trip joint-position tolerance flagged a 14.3-micrometer maximum on the imported cape chain. Independent evaluation of the serialized GLB joint transforms found a 12.4-micrometer maximum before Blender import. The final tolerance is 50 micrometers, with the actual measured error reported above; source rest matrices remain exactly unchanged.

GLB size: 284.4 MiB. This is a dense fidelity asset, not an optimized LOD. Standard glTF portable fibers and PBR approximate native hair shading; Cycles skin SSS is not reproduced exactly in glTF. These are format/shader limitations, not missing bone weights.

## Honest visual assessment

The MPFB source supplies actual orbital cavities, brow/nasal planes, chin/jaw structure and ear cartilage that the old procedural Gaussian head lacked. The coordinator-accepted head iteration 4 has been retained through the corrected graft. Profile anatomy is now directly exposed and documented, not hidden by front-only approval.

This is **not a claim of photographic equality with the approved concept**. The delivered brows/lid detailing are softer and simpler, the upper face/hairline presentation differs, the skin finish is less photographic, and the groom is more symmetrical and parallel than the reference's fuller tousled layers. Some long-hair leading edges remain deliberately arranged. The approved image provides no side drawing; statements that the profile reads as the same man are visual interpretations, not a measured exact profile match. The supplied comparison is intended to make these limitations easy to judge.

The separate inherited cloth/armor defects remain visible, as explained above. No claim of a complete whole-body resurfacing or perfect game-pose collision coverage is made.

## Per-iteration clay judgments

The following is the retained contemporaneous gate history, including failed trials, the banked-body correction and the final eye/weight reviews.

# MPFB clay review log

All judgments are from actual rendered images. Gray diffuse material override, no skin maps, no emission. Source images and parameter JSONs are saved per iteration. The approved reference contains a frontal face; profile identity is assessed for consistency with those visible landmarks, not against an invented approved side image.

## Isolated head 01 — FAIL

Front: eye spacing is too narrow; the large forehead, short middle face, and broad lower face read too young. It is not the approved man. MPFB age .30 was an inappropriate child/young blend.

Profile: the orbital recess, separate brow ridge, nasal bridge and ear folds are anatomical, but the youthful face proportions and blunt lower-face silhouette do not read as the same man. The first profile camera also cropped the nose and must not be used as a passing depth review; a corrected profile is retained with the final consistent framing.

Three-quarter: continuous cheeks, sockets and ears are a substantial topology improvement, but the identity remains too youthful and the jaw too wide. No graft approved.

## Isolated head 02 — FAIL / closer

Front: adult phenotype, longer middle/lower face, narrower chin and stronger cheek planes improve the match. Eye spacing and eye aperture remain smaller than the reference; the nose still reads too dominant.

Profile: the eye is visibly recessed beneath the brow, the nose has a continuous bridge, the ear has helix/concha depth, and the chin/jaw have plausible adult form. The heavy brow-to-forehead transition and somewhat long projecting nose still do not read convincingly as the approved man. Further correction required, not approved from the front view alone.

Three-quarter: better masculine proportions and jaw shape, but central features remain too concentrated and the nose needs restraint. No graft approved.

## Isolated head 03 — FAIL / refinement required

Front: nose and cheek proportions are closer, but the eye openings still look narrow and the mouth is too small compared with the approved face. Eye spacing improved only slightly; the target's maximum translation is small in physical units.

Profile: reduced nasal projection is better, with an unbroken bridge and actual recession beneath the brow. The chin and ear placement are plausible for the reference. However, the overall impression remains a generic model rather than convincingly the same man, particularly because the eye/mouth balance is still wrong. No graft approved.

Three-quarter: facial planes are coherent and the protruding-nose defect is substantially reduced. A further aperture/spacing and mouth-width pass is required.

## Isolated head 04 — PASS for anatomical graft trial; likeness still scrutinized at the assembled gate

Front: the adult long face, stronger brow, opened and more widely spaced eyes, restrained straight nose, wider relaxed mouth and defined chin now have the reference's principal proportions. The lack of brows and hair makes the isolated gray face less individually recognizable; the assembled clay is still required.

Profile: this now reads to me as a credible side view of the same intended noble face. The brow projects over a recessed orbit rather than a flat eye socket. The bridge is continuous and relatively straight, the tip is restrained rather than the round-5 projection, the chin sits behind the nose with a defined lower jaw, and the MPFB ear has a helix, antihelix and concha in the correct eye-to-nose vertical region. This is an interpretation of depth from the frontal concept, not proof of an exact profile identity.

Three-quarter: the nose no longer overwhelms the face; brow, socket, cheek and jaw planes remain connected and readable. Approved to trial the graft. No skin material work is authorized by this gate alone: assembled front/profile/three-quarter are next.

## Graft 01 — FAIL at neck/collar

Front: the original eye components and brow fibers were brought onto the MPFB anatomy. The face maintains the isolated proportions, but the lower neck has a conspicuous lateral flare. The patch collar does not adequately cover the fragmented upper torso.

Profile: the face still reads as the same intended anatomical interpretation as isolated 04; brow/orbit/nose/chin/ear depth was not flattened by skinning. The throat-to-collar connection and exposed broken body transitions fail the assembled gate.

Three-quarter and collar: residual shards and openings below the mantle/shoulder caps are clearly visible. The limited replacement is rejected. Proceed to a narrower neck bridge and the full round-5 upper-armor replacement/cloth containment pattern. No material pass.

## Graft 02 — head/neck pass; shoulder-junction FAIL

Front: narrowing the lower neck removes the flange and seats the head naturally in the gorget. The facial proportions remain those of isolated 04.

Profile: the brow/orbit depth, restrained nose, chin, jaw angle and ear survive the graft. I still read the face as the same intended man, with the previously stated limitation of having only a frontal approved reference. The neck now has a continuous throat line into the collar.

Three-quarter/collar: the full cuirass removes the broken chest field, but retained upper-cloth and old arm fragments remain visible in the shoulder articulation gaps. This is a real failure, not something to hide with hair. Replace only those damaged upper fragments with continuous skinned undersleeves; preserve the lower original garment. No material pass.

## Graft 03 — PASS head/neck/collar geometry; groom gate next

Front: continuous neck, no lateral flange, fitted gorget, intact facial shape. Existing eyebrow and eye component names are preserved. The collar shard field is removed without hiding it under a groom.

Profile: true orbital recession and brow overhang remain visible, with the same refined bridge/tip, chin projection, lower-jaw line and anatomical ear as isolated 04. I read it as the same intended face, now seated naturally on the existing body. There is no profile flattening or nose projection regression from the graft.

Three-quarter/collar: the throat/neck/collar and shoulder articulation surfaces are continuous. Smooth skinned undersleeves replace the broken upper cloth fragments. Original lower garment geometry remains rough and some inherited forearm-transition strips are still visible farther below; those are separate from the repaired neck/shoulder field and will be recorded rather than described as a fully rebuilt body.

Proceed to a groom clay gate, retaining these bald views as the unobstructed depth evidence. No skin material changes yet.

## Coordinator correction — grafts 01–03 superseded as body sources

The coordinator approved and banked another session's collar repair into the canonical body while this campaign was active. Grafts 01–03 sourced the older pristine backup and therefore contain an independent, non-authoritative armor repair. They are retained as iteration history only. The validated isolated MPFB head 04 is kept unchanged. Recombination 04 uses the approved canonical SHA-256 `68cf6f8cacd807822238f66bbed73faa98afa0308f8c516c7292b1a65085b56e` and does not execute this campaign's armor rebuild, cloth cleanup, undersleeve replacement or plate ornament code.

## Groom 01 salvage trial — FAIL, obsolete body source

Front: many fine strands and actual three-bundle braids remain, but the frontal groom reads too much like continuous curtains and has a hard lifted hairline edge.

Profile: a large occipital gap exposes the scalp and some back guides leave the head in separated fans. This unequivocally fails even though the frontal silhouette is plausible. The facial profile underneath is unchanged, but the groom is not acceptable as the same overall character.

Three-quarter: confirms that simple geometric re-rooting does not repair the inherited guide layout. Regenerate the guides on the MPFB scalp while retaining the proven curve/control/portable-strand and 12-bone binding machinery. This trial also used superseded graft 03; none of its independent armor/ornament work will enter the corrected banked-body result.

## Corrected graft i04 — approved collar-bank recombination

Source body is canonical SHA256 68cf6f8cacd807822238f66bbed73faa98afa0308f8c516c7292b1a65085b56e. Isolated head i04 was reused unchanged above the neck transition; no phenotype regeneration. The redundant armor rebuild from grafts i01–i03 was not run. Every protected banked armor mesh/world transform/weight hash matches. Every char1 rest vertex/weight and every non-head polygon is retained. The temporary banked neck object is retained hidden and replaced visibly by the MPFB neck.

Front: PASS head/neck; adult proportions and jaw width unchanged. Side: PASS relative to the accepted isolated head and graft i03: brow overhang, actual recessed orbit, straight bridge and restrained tip, projecting chin and mandibular angle, shaped ear all remain visible. In my assessment this is a plausible profile of the approved man, although the approved art supplies only a frontal view, so exact profile identity cannot be proved. Three-quarter: PASS; no forehead/temple collapse or neck seam flare. Collar: PASS preservation; the banked clean gorget/mantle/pauldron structure survives unchanged.

Body qualification: the approved banked body retains lower chest/sleeve fragments described in its own report. Those regions look rougher than the superseded independent rebuild in i03. This is not a whole-body cleanup pass or a claim that every visible polygon is improved; the required banked collar repair is preserved exactly. The new head/neck does not introduce those defects. Rig 121 bones, zero actions, rest_matrix_error 0.0. Actual hero assembly loader passed with rest_transform_max_error 0.0 using a permitted synthetic animation fixture.

## Regenerated groom i02 — FAIL
Front: temple guide ledges and an overly regular wide braid band distract from the accepted face. Side: crown loop and guide ledges are visible, despite improved occipital coverage. Three-quarter confirms squared guide transitions. Face depth itself is unchanged and remains acceptable; the combined groom does not pass.

## Regenerated groom i03 — FAIL
Front: top ledges corrected but a new visible transition at temple height remains. Side: no crown loop, continuous back coverage, but the transition reads as a horizontal shelf. Three-quarter confirms an overly tight cap feeding detached side curtains. Profile anatomy remains the accepted man; hairstyle prevents acceptance of the assembled result. Next iteration lifts guides naturally off the scalp and lowers their transition into hanging locks.

## Regenerated groom i04 — FAIL finishing gate
Front: smoother guide flow, but lifted leading edge and visible underlay line. Side: shelves/loop eliminated, scalp covered; face profile depth remains accepted. Three-quarter: no bald occipital patch but floating hairline edge needs root redistribution. Head/neck anatomy passes; combined grooming is not final.

## Regenerated groom i05 — FAIL reference hairline gate
Front: redistributed scalp roots and removal of opaque underlay eliminate the forehead seam; however the leading hairline remains too high versus the reference, enlarging the exposed forehead. Side: loose fine layered flow, no shelf or crown loop; profile reads as the accepted head. Three-quarter: coverage consistent, but frontal hairline position still needs correction. Next iteration moves only front guide roots toward the actual frontal hairline; head phenotype and all banked armor remain unchanged.

## Regenerated groom i06 — FAIL profile visibility gate
Front: improved lower frontal hairline, without changing the face. Side: a front lock curls too far forward and occludes the orbital/brow silhouette; therefore it cannot pass the required depth check. Three-quarter: frontal curl also reads too sculpted. The accepted head is unchanged, but I cannot approve the groomed profile as a clear presentation of that man. Sweep the guide arc backward at the temple in i07.

## Regenerated groom i07 — FAIL profile visibility gate
Front remains orderly, but the backward arc change did not resolve the forward orbital curl in side view; three-quarter also shows excessive forelock curvature. A gap appeared between side and rear guide fields. The accepted facial anatomy is still unchanged, but this assembled profile fails. The next correction restores the rear-side arc and applies explicit soft face-clearance constraints to front guides after scalp collision correction, which had pushed some guide samples toward the forehead rather than around the temple.

## Regenerated groom i08 — FAIL groom shape
Front/profile/three-quarter: facial depth is visible again, but the explicit clearance clamp creates planar hanging sheets and horizontal root transitions. This is not acceptable hair. Replacing the problematic front guides with a small sequence of deliberately exterior control points over the crown and around the temple; the good side/back coverage is retained. The forehead/eye/nose/chin/jaw geometry is unchanged.

## Regenerated groom i09 — FAIL crown transition
Front: exterior guide paths produce an excessive triangular widow's peak and lifted crown edge. Side: the eye/nose silhouette is visible again, and guide flow is smooth, but the crown lifts too abruptly from the root. Three-quarter confirms this artificial leading edge. Returning the center-part root to a more posterior scalp position and reducing the initial guide lift resolves the competing root/clearance constraints without changing the accepted head.

## Regenerated groom i10 — anatomical PASS, root finish incomplete
Front: smaller center-part transition but still a hard long-hair leading edge. Side: brow/orbit, straight nasal bridge and restrained tip, chin and jaw silhouette visible; no forward orbital curl or crown loop. Three-quarter: smooth guide flow but insufficient fine root coverage beneath the leading edge. Accepted head anatomy remains intact; add short scalp layers before surface work.

## Regenerated groom i11 — PASS face/graft clay gate; groom usable with stated style limitations
Front: the accepted adult MPFB face and jaw remain unchanged; fine scalp-rooted layers supply the hairline beneath the long strands. Side: the brow projects above a genuinely recessed orbit; bridge/tip are restrained, chin and mandibular angle are preserved. In my judgment this still reads as a plausible profile of the accepted man, not the shallow procedural head from prior rounds. The only approved image is frontal, so this is a reasoned identity interpretation rather than proof of an exact side-view likeness. Three-quarter: actual orbital, nasal, cheek and jaw planes remain continuous, without neck flare or a bald rear gap. Ear form/placement was verified unobstructed in graft i04; hair now partly covers it normally.

Groom limitation: the long center-part groups remain more parallel, symmetrical and deliberately arranged than the reference's fuller tousled hair; the leading edge is still somewhat orderly. This is not a claim of photographic hair fidelity. It now consists of fine flowing layers and four three-bundle interwoven braids, with a 14,000-strand short scalp layer. There are no guide shelves, forward eye-covering curls, crown loops or opaque forehead underlay seam. No head phenotype or approved armor geometry was changed during grooming. Proceed to skin/material review on this anatomy.

## Eye fit i01 and final fit i02 — PASS anatomical clay, three views each
The first textured trial revealed legacy dark-green sclera and iris caps partially buried in the eyeball surface. Replaced the existing iris/pupil/cornea object geometry with concentric caps at the MPFB helper centers; radius 10.3 mm iris and 3.5 mm pupil, with 0.12/0.20 mm surface offsets. The old cornea object is retained hidden, and clearcoat supplies the visible wet reflection. The accepted head vertices were not edited.

Front: larger correctly seated inserts stay inside the anatomical lids. Side: no protruding eye disc; brow overhang/orbital recession, nasal bridge/tip and chin/jaw silhouette remain unchanged and acceptable as the interpreted approved man. Three-quarter: no eye-surface bulge, no face/neck regression. Both eye-fit and final-fit views were inspected.

Final fit i02 changes only hair attachment weights: pin the first 25 mm of each long strand to Head, then blend over the following 100 mm into the established hair-chain weights. This removes isolated root-segment strain (previous worst about 40×; new worst 1.505× in the same synthetic combat pose). Native/control and portable correspondence remain within 1.2 micrometers. Neutral front/profile/three-quarter clay appearance is unchanged. Skin/material review can resume.

## Eye fit i02 — PASS final clay
A 4 mm downward gaze offset is projected back onto the actual eyeball sphere, so the iris caps remain seated rather than becoming offset intersecting discs. Front: neutral iris placement within unchanged MPFB lids. Side: no eye bulge or change to brow/orbit, nose tip/bridge, chin/jaw; this remains my accepted anatomical interpretation of the concept's man. Three-quarter: seated caps and unchanged cheek/neck planes. Hair geometry and smoothly blended root weights remain unchanged. All three clay renders inspected before final textured comparisons. Final actual hero loader also passes at rest error 0.0 with valid armature-modifier and native-curve-control references.

## Cosmetic finish i03 — PASS anatomical clay, three views
The accepted head/neck mesh is unchanged. Existing eyebrow hairs were widened 1.4× and thickened vertically 1.65×, then reprojected onto the anatomical brow surface. Legacy wetline/lash/tear-corner inserts that crossed the larger MPFB eye opening are retained hidden; the anatomical lid rim remains. Front: more appropriate brow span and clean eye opening. Side: no new shelf or bulging eye accessory, unchanged orbital/nasal/chin/jaw depth; still the accepted interpretation of the approved man. Three-quarter: brows sit on the surface and the eye opening is unobstructed. All three neutral-clay renders inspected. Fresh hazel iris detail and a less bright sclera are material-only refinements. Final portraits use the same framing with reduced fill (75 W versus neutral-clay 220 W) to inspect color under more directional portrait light; clay verdicts do not depend on that lighting change.
