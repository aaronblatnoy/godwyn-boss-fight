# Godwyn likeness iteration verdicts

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
