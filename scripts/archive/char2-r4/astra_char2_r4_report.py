"""Write the final evidence-backed handoff and exact file manifest; no dependencies."""
import json,hashlib,struct
from pathlib import Path
R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');O=R/'renders/astra/char2'
def read(name):return json.loads((O/name).read_text())
g=read('r4_groom.json');v=read('r4_preservation_validation.json');p=read('r4_hair_physics.json');e=read('r4_export_validation.json');h=read('r4_hero_assembly.json')
assert v['max_rest_matrix_difference']==0 and v['bones']==121 and v['actions']==0 and v['neutral']
assert not v['changed_nonhair_geometry'] and not v['changed_original_types_or_slots'] and not v['missing_original_objects']
assert e['joints']==[121] and e['animations']==0 and e['reimport_actions']==0 and len(e['hair_skinned_mesh_nodes'])==14
assert h['rest_transform_max_error']==0 and h['visible_native_curve_objects']==14 and h['visible_portable_strand_objects']==0
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
models={}
for name in ['astra_character_v2.blend','astra_character_v2.glb']:
 path=R/'models'/name;models[name]={'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
assert models['astra_character_v2.blend']['sha256']==h['character_sha256'],'Hero assembly must be checked against final file'
images={}
for name in ['after_face.png','after_hair.png','after_front.png','after_face_three_quarter.png','sidebyside_face.png','sidebyside_hair.png','r4_before_hair.png','r4_hair_spring_peak.png','r4_hair_spring_settled.png']:
 path=O/name
 with path.open('rb') as f:data=f.read(24)
 assert data[:8]==b'\x89PNG\r\n\x1a\n';w,hh=struct.unpack('>II',data[16:24]);assert w>=1080 and hh>=1080
 images[name]={'path':str(path),'width':w,'height':hh}
peak=p['states']['peak'];travel=max(x['max_displacement_m'] for x in peak['groups'].values());error=max(x['portable_center_error_m'] for x in peak['groups'].values())
hand={'models':models,'images':images,'native_curves':g['total_native_curves'],'native_control_points':g['native_points'],'portable_hair_vertices':g['portable_vertices'],'removed_shell_faces':g['removed_shell_faces'],'removed_crown_fragments':g['removed_misclassified_crown_fragments'],'bones':121,'animations':0,'hair_bone_chain_status':'OUTSTANDING_FULL_PHYSICS_READINESS','working_asset_rig':'Three existing four-bone chains drive 14 native curve groups and 14 matching skinned GLB meshes.','outstanding':['Native Blender oversized display tails retained for exact animation rest compatibility; corrected physical endpoints/lengths are explicit spring metadata.','Engine spring/collision solver integration and collision/multi-axis validation.','Photoreal concept-art gate; groom is still too regular at the crown and roots.','Runtime LOD/performance work for the large individual-strand GLB.'],'hero_assembly_pass':True,'hero_rest_error':h['rest_transform_max_error'],'spring_peak_displacement_m':travel,'spring_native_control_error_m':max(x['curve_control_error_m'] for x in peak['groups'].values()),'spring_portable_center_error_m':error,'spring_body_displacement_m':peak['nonhair_body_max_displacement_m'],'visual_gate':'NOT_MET'}
(O/'r4_handoff.json').write_text(json.dumps(hand,indent=2))
text=f'''Round 4: native hair-curves groom — visual gate NOT MET

Hero renderer target: `{R}/models/astra_character_v2.blend`.
Portable export: `{R}/models/astra_character_v2.glb`.
Both canonical paths are updated. The final hero-loader check uses the current character file and the shipped `models/astra_xslash_v2_final_wip.blend`, without saving either input or changing the cinematography code.

**What changed.** Replaced {g['removed_shell_faces']:,} faces of the inherited solid hair shell and retired the old cap/flow/plait geometry. Removed {g['removed_misclassified_crown_fragments']} misclassified blue fragments entirely above z=2.90 m; these were crown remnants, not garment panels. Original object names and material slot lists remain intact, including the now-empty retired hair objects. New hair is {g['total_native_curves']:,} native Blender hair curves with {g['native_points']:,} control points. There are 12,800 loose fibers and 864 braid fibers: six plaits, each woven from three bundles of 48 fibers. Roots, scalp underlay, fine flyaways, tapered ends, depth variation and loose waves replace the old long shell. The small scalp surfaces are anatomical root support; they do not form the long hair silhouette.

Native rendering uses Principled Hair / Chiang, melanin variation and lengthwise strand scattering. The GLB contains matching individually skinned strand meshes with anisotropy 0.72 and `KHR_materials_anisotropy`; native Blender Curves are not a portable glTF geometry primitive. Export meshes are hidden in the Blender render so the groom is not doubled. The export adds {g['portable_vertices']:,} hair vertices and is {models['astra_character_v2.glb']['bytes']/1e6:.1f} MB. It is loadable, but runtime LOD and performance work remain. Identical engine shading has not been visually verified.

**Preservation and handoff.** Final validation confirms 121 bones, zero actions/animations, neutral pose, original object names and slot lists, and exactly unchanged rest matrices. All remaining non-hair vertex coordinates, topology/material assignments and UVs match the pre-round-4 asset. The only non-hair rig correction removes inherited hair-bone influences from {g['orphan_hair_influences_cleaned']:,} referenced character vertices and normalizes their remaining body-bone weights, preventing hair motion from dragging body surfaces. Face, armor and cloth shaders are unchanged. The blue garment geometry, boots and covered chest are retained.

The actual hero assembly passed with rest-transform error **0.0**, 14 visible native curve objects and zero visible portable strand objects. The GLB passed fresh Blender import with one 121-joint skeleton, no animations, all 14 hair meshes skinned, all 12 hair joints present, and anisotropy retained in the exported materials.

**Hair bone chains: OUTSTANDING for full physics readiness.** The working deformation/export path is complete: three four-bone chains drive the groom through skinned point controls, and the same weights drive the GLB strand meshes. A local single-axis damped angular impulse test uses stiffness 32 s^-2, damping 7 s^-1, unit inertia and a 1/120 s integration step. Peak hair displacement was {travel:.6f} m; visible body displacement was {peak['nonhair_body_max_displacement_m']:.1f} m. Native curve/control error was zero; exported-mesh centerline error was at most {error*1e6:.3f} micrometres. The groom returned to neutral after six simulated seconds, with no actions or keyframes created. Peak and settled stills are included.

The native bone display tails are still oversized (roughly 16–22 m). Direct length edits made Blender recompute inherited rest matrices, breaking the existing hero script's 1e-6 tolerance. A trial could not preserve that tolerance, so those edits were discarded. The final model retains the exact original cached rest transforms. Correct physical segment lengths (roughly 0.162–0.224 m, with 0.4 m front and 0.6 m back terminal segments) and endpoints are stored as per-bone spring properties. GLB extras convert endpoints to **glTF Y-up metres**. glTF represents joint transforms, not Blender display-tail lengths. The runtime spring/collision solver, collision response, multi-axis validation and native display-tail cleanup compatible with the shared rig are still outstanding. The local test is not proof of collision-safe engine behavior. The hero loader reuses the animation rig verbatim and does not copy these new spring properties from the character rig; dynamic spring hookup in that path also remains an integration task.

**Visual assessment against the binding concept.** The opaque face veil and the old faceted long-hair termination are gone. The forehead and cheeks are exposed, strands extend past the shoulders, individual tapered fibers appear at the silhouette, and the loose hair has more depth and waves. However, the crown still has overly orderly rows; the center part and temple transition remain too constructed; some clumps still combine into broad bands; the three-quarter view exposes excessive rear volume and gaps behind the ears; and the braid pattern is more repetitive and less individually legible than the reference. This is a real groom and a useful structural improvement, but it does not yet match the approved image photorealistically. The unchanged synthetic face, artificial eyes, and inherited face/neck/armor fragments remain visible in close-up. No face-design variants were made or consulted.

**Comparisons.** `sidebyside_face.png` places the approved reference on the left and the final front portrait on the right at matched height. `sidebyside_hair.png` places the immutable pre-round-4 model on the left and the final groom on the right under the same framing and lights. Portraits are 1080×1610; hair and full-body stills are 1080×1080. Gate stills use local Metal Cycles, 128 samples, no denoising, and the house AgX/exposure convention. Raw sampling leaves some visible grain; it avoids smoothing away fine fibers. Spring-test stills use the existing 24-sample denoised house helper. No animation sequence was rendered.

**Specification conflicts retained/reported.** The known CLAUDE.md exposed-chest/barefoot instruction contradicts SPEC's covered breastplate and armored feet; the user's resolution was followed. The approved face image is a facial reference, not an instruction to uncover the chest. The remote/OptiX instruction was overridden for this local session. No new appearance contradiction was resolved by inventing a design, and no protected specification or other agent's files were edited.

**Reproduction.** Run `scripts/astra_char2_r4_groom.py` headlessly with `PYTHONDONTWRITEBYTECODE=1`; it always rebuilds from `models/astra_character_v2_preround4.blend`. Then run `astra_char2_r4_physics.py`, `astra_char2_r4_export.py`, `astra_char2_r4_validate.py`, `astra_char2_r4_hero_check.py`, and the render script (`-- before` for the immutable baseline; `-- after` for final views). `astra_char2_r4_physics.py -- --render` produces only peak/settled stills. The separate crown cleanup is an idempotent finishing utility; that removal is also integrated into the main groom script. `r4_rest_compatibility.json` is the discarded length-edit experiment, not the final compatibility verdict. Final evidence is in `r4_preservation_validation.json`, `r4_hero_assembly.json`, `r4_export_validation.json`, `r4_hair_physics.json`, and `r4_handoff.json`.

Exact absolute paths for every retained round-4 script, model, render, comparison and diagnostic are listed in `r4_written_files.json`. Immutable pre-round-4 .blend and .glb backups are retained. No git commands, network, installations, Pillow or remote execution were used.
'''
(O/'ROUND4_REPORT.md').write_text(text)
files=set((R/'scripts').glob('astra_char2_r4_*.py'))|set(O.glob('r4_*'))|{O/'ROUND4_REPORT.md',O/'r4_written_files.json'}|{Path(x['path']) for x in images.values()}
files|={R/'models'/n for n in ['astra_character_v2.blend','astra_character_v2.glb','astra_character_v2_preround4.blend','astra_character_v2_preround4.glb']}
(O/'r4_written_files.json').write_text(json.dumps({'files':[str(f) for f in sorted(files) if f.is_file() or f.name=='r4_written_files.json'],'transient_export_path_replaced_by_canonical_glb':str(R/'models/astra_character_v2_round4_export.glb')},indent=2))
print(json.dumps(hand,indent=2))
