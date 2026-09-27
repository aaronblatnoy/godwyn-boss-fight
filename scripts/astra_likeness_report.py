"""Write the likeness verdict history, final report, and before/after plate."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
published = json.loads((OUT / 'likeness_published.json').read_text())
native = json.loads((OUT / 'likeness_final_validation.json').read_text())
roundtrip = json.loads((OUT / 'likeness_roundtrip_validation.json').read_text())
rising = json.loads((OUT / 'likeness_rising_spin_clearance.json').read_text())

before = Image.open(OUT / 'mpfb_final_textured_front.png').convert('RGB')
after = Image.open(OUT / 'likeness_i06_front.png').convert('RGB')
if before.size != after.size:
    before = before.resize(after.size, Image.Resampling.LANCZOS)
plate = Image.new('RGB', (before.width + after.width, max(before.height, after.height)), (20, 20, 20))
plate.paste(before, (0, 0))
plate.paste(after, (before.width, 0))
plate.save(OUT / 'likeness_before_after.png', optimize=True)

verdicts = """# Godwyn likeness iteration verdicts

All portrait gates were rendered at the established MPFB framing with Cycles on the two asserted OptiX devices. The approved face reference is the left panel of each `likeness_iNN_approved_comparison.png`.

## Iteration 01 — FAIL

- **Skin:** procedural SSS/pore structure was present, but linear-space values plus warm lighting overexposed the face; it read white and waxy rather than living.
- **Hair:** guide displacement introduced volume, but the direct hair color was saturated orange and the original parallel sheets remained dominant.
- **Eyes:** new lid/lash/tear geometry followed the face, but the aperture remained too open and the gaze still read as staring.
- **Brows/lips:** brow fill and lip shell were improvements, but the exposure erased most lip definition.

## Iteration 02 — FAIL

- **Skin:** exposure was corrected and warmth/pore variation became visible, but pore relief was too coarse and mottled.
- **Hair:** large coherent waves made the groom fuller, but separated into ribbon-like copper clumps with black gaps.
- **Eyes:** darker natural sclera and muted iris helped; lid thickness was still insufficient.
- **Brows/lips:** both were clearer than the published face, but not enough to offset the hair/eye failures.

## Iteration 03 — CLOSER, NOT FINAL

- **Skin:** finer pore response and warmer color were materially closer; broad coat highlights still looked plastic.
- **Hair:** the reddish-gold palette and tighter clumps were closer, though the rear flow still winged backward.
- **Eyes:** iris color improved, but the MPFB opening continued to expose too much sclera.
- **Brows/lips:** fuller tapered brows and a closed neutral mouth passed their local visual goals.

## Iteration 04 — CLOSER, EYE GATE FAIL

- Reduced coat response and a gravity-biased rear groom improved skin and shoulder fall.
- The added upper-lid overlay was occluded by the existing opening and did not materially change the expression.
- No publish.

## Iteration 05 — VISUAL PASS; MECHANICAL FAIL

- Direct soft-tissue adjustment of the existing lid boundary produced a heavier upper lid and neutral-sorrowful gaze without changing topology or the rest rig.
- Skin, warm wavy groom, hazel-green eyes, fuller brows, and closed fuller lips were all clearly closer to the approved reference than the published input.
- Native stress validation rejected the rerouted short temple braids: old hanging-chain weights produced 13.544× left / 12.594× right maximum segment stretch. No publish.

## Iteration 06 — PASS / FINAL

- Neutral appearance is visually the same as i05; only the short temple-sweep braids were rebound rigidly to `Head`, which is appropriate for their new short route. The long loose groom retains all twelve hair bones.
- Braid stress fell to 1.00064× left / 1.00048× right; the long-groom worst case is 1.57106×.
- Native, hero-assembly, GLB export, two-pose round-trip, publish, and Rising Spin F40 clearance gates all passed.
- Further procedural edits would mainly reshuffle the same guide architecture or alter the approved MPFB phenotype, so iteration stopped at six of the allowed eight.
"""
(OUT / 'LIKENESS_VERDICTS.md').write_text(verdicts)

report = f"""# Godwyn likeness closeout

## Result

The published Godwyn character was replaced only after iteration 06 passed the visual and mechanical gates. The accepted MPFB head was not regenerated. Armor, cloth, body, and the 121-bone rest rig were not redesigned or edited.

![Published before on the left; likeness i06 after on the right](likeness_before_after.png)

![Approved reference on the left; likeness i06 on the right](likeness_i06_approved_comparison.png)

Final views: [front](likeness_i06_front.png), [side](likeness_i06_side.png), [three-quarter](likeness_i06_three_quarter.png).

## What changed

- **Skin:** procedural fine color variation, localized nose/cheek/lid/lip redness, 24% Principled subsurface at a 3.2 mm scale with `[1.0, 0.42, 0.18]` radius balance, fine roughness variation, restrained coat, and a very low albedo emission mask driven at the SPEC-required 2.5 strength. The SPEC pale base color remains the anchor rather than an unmodulated flat color.
- **Hair:** the retained 32,900-strand native/control/portable system now has warmer reddish-gold direct shading, darker roots, larger clumps, irregular wave, more crown/side volume, a more downward shoulder fall, and two short temple-origin three-bundle braids sweeping rearward. Loose hair still uses all twelve original hair bones; the short braids follow `Head` without simulation.
- **Eyes:** warm natural sclera, darker hazel-green radial iris with limbal ring, thicker upper/lower lid margins, a soft upper-lid closure, lash line/individual lashes, tear ducts, and a slightly lowered gaze.
- **Brows/lips:** two additional tapered brow-fill layers per side; a closed, volumetric upper/lower lip shell with a defined neutral seam.

## Validation and publication

- Native source: `{published['validated_candidate']}`.
- Native rig: **{native['bones']} bones**, **{native['actions']} actions**, rest-matrix error **{native['rest_matrix_error']}**, neutral restored **{native['neutral_restored']}**.
- Native referenced skinned vertices: **{native['weights']['referenced_skinned_vertices']:,}**; bad/unweighted: **{native['weights']['unweighted_or_bad_sum_vertices']}**; max weight-sum error **{native['weights']['weight_sum_max_error']:.10f}**.
- Head topology remains closed: **{native['head_topology']['vertices']:,} vertices**, **{native['head_topology']['faces']:,} faces**, zero boundary and non-manifold edges.
- Protected banked armor hashes preserved: **{native['banked_armor_hashes_preserved']}**.
- Actual hero assembly: 121 bones, valid modifier/control references, rest-transform max error **0.0**.
- GLB round trip: **{roundtrip['bones']} bones**, skin joint counts **{roundtrip['glb_skin_joint_counts']}**, animations **{roundtrip['glb_animations']}**, max world-joint position error **{roundtrip['world_joint_position_max_error_m']:.10f} m**, bad/unweighted referenced vertices **{roundtrip['weights']['unweighted_or_bad_sum_vertices']}**.
- Both native and GLB candidates rendered in arms-raised and combat-stress poses on asserted OptiX devices before publication.

Published SHA-256:

- `models/astra_character_v2.blend`: `{published['astra_character_v2.blend']}`
- `models/astra_character_v2.glb`: `{published['astra_character_v2.glb']}`

Preserved byte copies:

- `models/astra_character_v2_pre_likeness.blend`: `{published['pre_likeness_blend_sha256']}`
- `models/astra_character_v2_pre_likeness.glb`: `{published['pre_likeness_glb_sha256']}`

## Rising Spin proof

![Published likeness at Rising Spin F40](likeness_rising_spin_f040.png)

The corrected Rising Spin scene/action was rehosted in memory onto the new published character at the prior exact worst frame, F{rising['frame']}. The blade/head exact triangle-overlap count is **{rising['blade_head_exact_triangle_overlaps']}**. Sampled blade-to-head surface distance is **{rising['blade_head_exact_sampled_surface_distance_m'] * 1000:.3f} mm**. Sampled blade-to-hair clearance is **{rising['blade_hair_exact_sampled_surface_clearance_m'] * 1000:.3f} mm**, after the same **{rising['hair_fiber_radius_assumption_m'] * 1000:.1f} mm** fiber-radius allowance. This is a frame-40 sampled proof, not a claim of continuous-time collision clearance.

## Honest remaining gap

This is clearly closer than the prior publication, but it is not photographic equality with the concept. The fixed approved MPFB phenotype remains longer/narrower and more stylized than the reference. The procedural groom still shows a more organized center opening and broader guide families than the reference's dense, irregular photographic flyaways; the temple braids are subtler from the front. Lid, tear, lash, and lip inserts remain modeled details rather than scan-level anatomy. Skin pores and redness are procedural, and GLB PBR cannot reproduce the native Cycles SSS/hair response exactly. The original armor/body qualifications from the MPFB delivery remain unchanged.
"""
(OUT / 'LIKENESS_REPORT.md').write_text(report)
print('LIKENESS_REPORT_PASS')
