"""Write the final round-2 report and explicit absolute-path manifest."""
from pathlib import Path
import json,sys
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2'
m=json.loads((OUT/'round2_metrics.json').read_text());v=json.loads((OUT/'round2_validation.json').read_text());repeat=json.loads((OUT/'round2_idempotence.json').read_text());rt=json.loads((OUT/'round2_glb_roundtrip.json').read_text())
text=f'''Round 2 — saved revision, photorealism gate NOT MET

The binding visual test is sidebyside_face.png: the unaltered approved portrait on the LEFT and the native Blender render on the RIGHT, both 848 × 1264. No rejected face concepts were opened or used. Every visual iteration has its own preserved comparison. This is a model revision for review; it is not an approved likeness or a photoreal finished face.

The fixed front-on portrait camera uses location (0, -5, 2.900), target (0, -.30, 2.900), orthographic scale .650. Portrait lighting is held identical between r2_baseline_portrait_face.png and after_face.png. AgX exposure stays -.35. The full-body after_front.png uses the house camera and lighting from astra_character_common.py. Portrait lighting is deliberately documented separately from the brighter house full-body setup.

Visible changes:

- The straight horizontal forehead edge has been replaced by a curved, irregular hairline, lower at the temples, with a center part and fine overlapping strands. The retained large hair mass remains visibly molded and metallic. The new strands still do not reproduce the approved portrait's natural density, waves, and clump structure.
- Eye and mouth placement moved upward to shorten the mid/lower face. A continuous, dense facial patch inside the existing char1 mesh replaced the overlapping front surface. It supplies cheekbone prominence, submalar/temple hollows, a smoother jaw/chin transition, nasal wings, nostril openings, lip volumes, and a philtrum. The nose, lips and jaw still look procedurally constructed rather than like the approved man's anatomy. In particular the nostril liners read like small plugs and the lips have an overly molded border; these are unresolved defects, not successes.
- Hazel-green iris geometry is larger, eye openings are calmer and less slit-like, and sclera is tinted. Eyelid tissue, existing lashes, brows and wet lines remain actual geometry. The eyes still look artificial; tear-corner tissue is not as legible or convincing as in the reference.
- Four packed 2048-pixel skin maps supply color zoning, pores, fine detail, roughness breakup and spatial emission. Only high-frequency skin detail and bounded chromatic variation from the approved portrait are sampled; broad lighting and facial organs are excluded. This is not a photograph placed in front of the model. At portrait scale the pores remain too subdued, and the skin still lacks the reference's organic translucency and convincing photoreal response. The enlarged crop in round2_skin_detail_comparison.png makes this shortfall especially clear.

Measurement: mean image-plane error for four approximate landmarks changed from {m['before_mean_error_px']:.2f} px to {m['after_mean_error_px']:.2f} px. Iris centers come from geometry; mouth and nasal anchors are approximate anatomical correspondences. This measures alignment only, NOT realism or identity. See round2_metrics.json for the coordinates and methodology. The visual comparison remains the acceptance test, and it still fails photorealism.

Skin implementation: the canonical Base Color input remains (.95, .90, .82), while an epidermal albedo map controls the rendered local reflectance. Golden emission is retained at strength 2.5, with canonical color (1, .88, .45) spatially filtered through a nonzero map (approximately 0.4–3.3%). Principled subsurface weight .24, radius RGB (1, .36, .17), scale .0015 m. These settings are present; I do not claim that their mere presence proves realistic skin. The ears remain obscured by retained hair, so an ear-rim translucency match could not be verified. Core glTF does not preserve the exact Cycles subsurface model.

Preservation and validation:

- Original object names and existing material-slot lists preserved; char1 still has five material slots.
- Original armature bone names/rest positions and original vertex-group names preserved.
- Maximum blue garment vertex displacement: {v['cloth_vertex_max_change_m']:.10f} m. Garment weights exactly unchanged.
- Maximum body vertex displacement below 2.78 m: {v['body_below_2_78_max_change_m']:.10f} m.
- No actions or stray character animation. New facial surface and added hairline meshes are Head-weighted.
- Rebuilding from the immutable round-2 input produces identical geometry, topology and skin-map hashes: {repeat['exact_geometry_and_maps_repeat']}.
- Fresh exported-GLB import succeeded: {rt['fresh_import_loadable']}; {rt['armature_bones']} bones; no animations. Export includes skin normal/roughness/emission maps, tangents, and emissive strength 2.5. Native and imported-GLB portraits are both preserved for review.

Blue garment assessment — geometry unchanged:

Blue cloth exists inside char1 and Astra_Undersleeves, rather than as a separate robe/cape object. The front has a central hanging panel with gold edging, a waist sash, a diagonal torso/shoulder drape, and underlayer accents. The central panel stops above the floor around the lower legs; the side/rear train reaches the floor. In the house render the cloth reads pale/periwinkle rather than the specified deep blue. Neither geometry nor color was restructured in this round. Side and back views reveal a broad continuous skirt/train volume trailing to the floor. It is therefore a HYBRID integrated tabard/sash plus robe-like side/rear train, not a clean set of separate integrated panels. I cannot certify the current geometry as fully matching the SPEC's “not a standalone robe / never a cape” appearance. Upper rear attachment is partly hidden by hair. Bone names include phys_cape_* and phys_robe_front/side_*; those names support the rig inventory but do not by themselves establish the garment's visual classification. See r2_garment_back.png, r2_garment_side.png and round2_garment.json. No garment restructuring, cloth simulation, or cloth-weight edits were made.

Document discrepancies reported, not redesigned:

- CLAUDE.md:65 says barefoot/exposed chest/partial armor, contradicting SPEC.txt:326–347. The supervisor's explicit resolution was followed: covered breastplate, armored legs and boots preserved. CLAUDE.md was not edited.
- boss-fight.txt:244, 247 and 344 retain spear-attack language. SPEC.txt:1413–1415 explicitly supersedes those older attacks with the swordsman combo tree. No weapon or attack-system edits were made.
- boss-fight.txt:313 describes Miquella descending onto Godwyn's back, whereas SPEC.txt's transition section (~889–892) has him approach, kneel, and send gold from his hands into the deathroot veins. The transition was not changed.
- SPEC.txt:349 mentions visible skin on “face, arms” while 331 and 347 specify armored arms and essentially only the face exposed. This textual ambiguity was not used to expose more skin.
- The approved portrait shows exposed shoulders/chest; the supervisor explicitly resolved armor coverage using SPEC. The portrait was used for the face, while the model's chest armor remained covered.

Local execution only: Blender 5.2.1 LTS, Cycles METAL on the Apple M1 Pro. Portraits use 48 samples; full-body review uses 32. No git commands, network access, remote connections, package installation, or Pillow were used. No external service blocked delivery. The unresolved obstacle is visual quality: the model remains synthetic, and I would not call it a photoreal match or production-ready face.

Exact retained files written in this round are listed as absolute paths in round2_written_files.json. A syntax-check command briefly generated scripts/__pycache__/astra_char2_round2_deliver.{sys.implementation.cache_tag}.pyc outside the allowed prefix; that single generated file was removed immediately. No other agent files were edited. The manifest records this removed incidental artifact separately. The canonical model files were updated; round2_input.blend/.glb retain the pre-round-2 state. The scripts reconstruct the revision from that immutable input. Run astra_char2_round2_refine.py, then astra_char2_round2_deliver.py, locally headless with --python-exit-code 1. The repeat checker rebuilds without rendering and proves content repeatability.
'''
(OUT/'ROUND2_REPORT.md').write_text(text)
paths=[ROOT/'models'/n for n in ['astra_character_v2.blend','astra_character_v2.glb','astra_character_v2_round2_input.blend','astra_character_v2_round2_input.glb','astra_character_v2_round2_work.blend','astra_character_v2_round2_iteration9.blend']]
paths+=list((ROOT/'scripts').glob('astra_char2_round2_*.py'))
paths+=list(OUT.glob('r2_*'))+list(OUT.glob('round2_*'))
paths+=[OUT/n for n in ['after_face.png','after_front.png','after_face_three_quarter.png','after_sidebyside.png','sidebyside_face.png','ROUND2_REPORT.md','round2_written_files.json']]
manifest=sorted({str(p) for p in paths if p.is_file() or p.name=='round2_written_files.json'})
(OUT/'round2_written_files.json').write_text(json.dumps({'retained_files':manifest,'removed_incidental_file':str(ROOT/'scripts/__pycache__'/('astra_char2_round2_deliver.'+sys.implementation.cache_tag+'.pyc'))},indent=2))
print(text)
