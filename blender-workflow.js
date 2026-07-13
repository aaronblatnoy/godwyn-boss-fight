// Godwyn Phase-1 headless-Blender buildout, compiled from blender-build-plan.txt.
//
// Real DAG (from plan Section 12.1 / 11):
//   P0 -> P1 -> P2 -> P3 -> P4 -+-> P5 -+-> P7
//                               +-> P6 -+
// P0..P4 edit the SAME .blend statefully => STRICTLY SEQUENTIAL (awaited chain).
// P5 and P6 depend ONLY on P4 and write DISJOINT dirs (renders/character vs
//   renders/moveset) + DISJOINT scripts (05 vs 06) => genuine parallel() fork.
// P7 joins on P5 AND P6.
//
// Isolation: NONE. The build happens on mossad over SSH (agents author scripts
//   locally, scp, run headless). Parallel safety for P5/P6 comes from disjoint
//   scripts + disjoint output dirs, not git worktrees. (Worktree isolation is
//   irrelevant to SSH-side work and would only fragment the local clone.)
//
// Model policy (from the caller's KEY CONTEXT, which OVERRIDES the plan's
//   sonnet-mostly Section 12.3): claude-fable-5 for ALL Blender-Python
//   script-writing phases (P0..P6); default model for the mechanical
//   setup/commit phase (P7). No specialized subagents (refractor/audit/ozempic)
//   are used — the plan (Section 12.1 DAG note) explicitly forbids them:
//   this is asset generation, not a cross-referenced refactor or a
//   correctness-critical proof.

export const meta = {
  name: 'godwyn-blender-phase1',
  description:
    'Headless-Blender (Cycles/GPU on mossad) buildout of Godwyn Phase-1: env+GPU proof, base mesh, details, materials, rig/lights/cams/.blend, then a parallel character-sheet || moveset render fork, then commit+README.',
  phases: [
    { title: 'P0 Env setup + GPU proof', detail: 'Install Blender 4.x headless on mossad; prove Cycles renders on the RTX 3060 Ti GPU (OptiX/CUDA); scaffold dirs + lib_godwyn GPU helper + .gitattributes.' },
    { title: 'P1 Base mesh', detail: 'Author 01_base_mesh.py -> a 3.2m barefoot humanoid Godwyn_Body at 1.4x human proportions, neutral stance, self-contained (no addons).' },
    { title: 'P2 Details', detail: 'Author 02_details.py adding partial gold armor (exposed chest), blue flowing robe, long partial-braid golden hair (mesh), slim gold-hilt/blue-blade longsword (origin at grip).' },
    { title: 'P3 Materials', detail: 'Author 03_materials.py: pale luminous SSS+emission skin, worn gold armor, deep-blue robe (no emission), subtle blue blade, golden hair, void world with a faint vertical golden crack.' },
    { title: 'P4 Rig + lights + cams + .blend', detail: 'Author 04_rig_lights_cams.py: simple posable armature (sword parented to hand bone), dark-fantasy "Godwyn-is-the-light" rig, 8 named cameras, Cycles GPU/OptiX+denoise config, SAVE models/godwyn_phase1.blend.' },
    { title: 'P5 Character sheet renders', detail: 'Author 05_render_sheet.py: open the .blend, loop sheet cams (front, 3q-L, 3q-R, back, side, face, sword), render >=6 2K GPU PNGs to renders/character/. Base pose = low hang guard.' },
    { title: 'P6 Moveset renders', detail: 'Author 06_render_moveset.py: open the .blend, pose + render EXACTLY 7 moveset poses to renders/moveset/, reset to rest between poses.' },
    { title: 'P7 Commit + README previews', detail: 'Write build_all.sh (runs 00..06), update README with preview thumbnails + regenerate note + fan-art credit, prune wip, git add -A + commit on mossad. NEVER auto-push.' },
  ],
};

const SSH = 'All remote ops are non-interactive one-shots: ssh mossad "cmd" (multi-line: ssh mossad "cmd1 && cmd2"). Claude Code CANNOT open an interactive SSH session (INV-1). mossad = Arch Linux, 2x RTX 3060 Ti (8GB each), NVIDIA driver 610.43.02. Repo already cloned at ~/godwyn-boss-fight (git@github.com:aaronblatnoy/godwyn-boss-fight.git). git pull before working on mossad; git add -A + commit on mossad after each phase (do NOT push).';

const FABLE_FLOW =
  'AUTHORING FLOW (plan A5): author the .py LOCALLY, scp it to mossad:~/godwyn-boss-fight/scripts/, run headless via ssh mossad "blender --background --python ~/godwyn-boss-fight/scripts/<name>.py 2>&1", capture stdout/stderr to renders/wip/logs/. The committed .py IS the reproducible source of truth (INV-5).';

const INVARIANTS = [
  'INV-1 headless-only: every Blender call is `blender --background --python <script>`; all remote calls via ssh mossad "..." one-shots.',
  'INV-2 GPU-real: renders MUST use Cycles on GPU (OptiX preferred, CUDA fallback). CPU-only render is a FAILURE, not a degraded pass. Each render script preamble sets cycles.device=GPU AND asserts >=1 GPU device enabled; fail LOUD on silent CPU fallback.',
  'INV-3 spec-fidelity: colors/proportions/silhouette come from SPEC.txt lines 293-341, not imagination. Phase-1 rules: NO crown, NO dark markings, barefoot, partial gold armor over EXPOSED chest, blue robes, long partial-braid hair, luminous pale skin, low-hang-guard neutral. Any deviation is a bug.',
  'INV-4 export-friendly: single "Godwyn" collection, apply-scale-friendly transforms, clean armature with sane bone names, meaningful object names (Godwyn_*).',
  'INV-5 reproducibility: the .blend is regenerable from scripts; seed any randomness.',
  'INV-6 idempotent scripts: each script clears/rebuilds its own objects by name (delete existing "Godwyn_Body" before recreating) so re-running never duplicates geometry; reset pose to rest between moveset poses.',
  'INV-7 light-source-is-Godwyn: his emission (SPEC 337, radius ~12m, key color 1.0,0.92,0.6) lights the void plus the golden crack — NOT a neutral studio rig.',
].join('\n  - ');

const SPEC =
  'GODWYN SPEC (SPEC.txt 293-341 appearance/materials, 400-517 moveset): 3.2m demigod at 1.4x human proportions (reads as a noble person, not a giant); golden-blonde hair, partially braided + loose flow; partial gold chest/shoulder/arm armor over EXPOSED chest; deep-blue flowing robe as primary garment; barefoot; NO crown; NO dark markings; pale luminous near-translucent skin with faint emission glow. Longsword: gold hilt + gold-filigree crossguard + subtle blue-tinged blade (subtle, not glowing heavily), origin at grip. ' +
  'MATERIALS (author Cycles nodes to MATCH these LINEAR RGB values per assumption A7): skin base 0.95,0.90,0.82 + SSS + emission 1.0,0.88,0.45 @ ~2.5 (subtle, must not blow out); gold armor/hilt/crossguard 0.82,0.65,0.15 metallic=1 slight-sheen faintly-worn; blue robe 0.08,0.12,0.35 NO emission; blade steel+subtle-blue-tint faint-emission << skin; hair golden-blonde lighter than armor; cast-light key 1.0,0.92,0.6; void world near-black + faint vertical golden crack ~1.0,0.85,0.4. ' +
  'RENDER SPEC: 2K portrait (plan default 2048x2560; caller target 1440x2560) for character sheet, 1920x1080 for moveset action; Cycles GPU (OptiX/CUDA), samples ~128-256 + OptiX denoise, film transparent OFF (keep the void), Filmic/AgX color mgmt; PNG output.';

const phaseResult = {
  type: 'object',
  properties: {
    ok: { type: 'boolean', description: 'true only if the phase met its plan-Section-3 validation gate' },
    summary: { type: 'string' },
    evidence: { type: 'string', description: 'device table / object list / camera+bone list / render filenames / the "Using OptiX"/"Using CUDA" GPU log line — whatever this phase\'s plan validation demands' },
    gpuUsed: { type: 'boolean', description: 'true if a "Using OptiX" or "Using CUDA" line was observed for any render this phase produced (INV-2); N/A phases may set true' },
    outputs: { type: 'array', items: { type: 'string' }, description: 'relative repo paths this phase produced (scripts + renders + .blend)' },
    needsUserJudgment: { type: 'boolean', description: 'true if a preview "runs but looks wrong" and needs human visual sign-off (plan 12.5)' },
    blockers: { type: 'array', items: { type: 'string' } },
  },
  required: ['ok', 'summary', 'evidence', 'gpuUsed', 'outputs'],
};

function halt(phaseLabel, r) {
  log(`HALT at ${phaseLabel}: ${r && r.summary ? r.summary : 'phase did not pass its validation gate'}`);
  return {
    status: 'halted',
    haltedAt: phaseLabel,
    reason: (r && r.summary) || 'phase failed validation',
    blockers: (r && r.blockers) || [],
    needsUserJudgment: !!(r && r.needsUserJudgment),
    note: 'Plan left in lifecycle/pending (or repo root) — NOT archived. Fix + resume from this phase.',
  };
}

export default async function () {
  const PLAN = 'blender-build-plan.txt';
  const base =
    `Read ${PLAN} (repo root, ~/godwyn-boss-fight) in full first, plus the referenced SPEC.txt spans. This is a headless-Blender asset buildout on mossad.\n\n` +
    `ENVIRONMENT:\n  ${SSH}\n\n` +
    `INVARIANTS (all phases):\n  - ${INVARIANTS}\n\n` +
    `${SPEC}\n\n` +
    `Per-phase logs go to renders/wip/logs/phase-<id>.log and wip previews to renders/wip/<NN>_*.png (both gitignored per plan 12.6; add renders/wip/ to .gitignore in P0). ` +
    `RETURN the structured schema honestly: set ok=false and populate blockers if your plan-Section-3 validation gate is not met; set needsUserJudgment=true if the render "runs but looks wrong" (visual correctness is not machine-checkable — surface the preview, do not self-certify — plan 12.5).`;

  // ---- P0: environment + GPU proof (SINGLE, gates everything) ----
  phase('P0 Env setup + GPU proof');
  const p0 = await agent(
    `${base}\n\n${FABLE_FLOW}\n\n` +
      `PHASE 0 (plan Section 3 Phase 0). Slice: install Blender 4.x headless on mossad and PROVE Cycles renders on the 3060 Ti GPU. Touch ONLY: scripts/00_env_check.py, scripts/lib_godwyn.py (scene-reset + GPU-enable-and-assert helper + void-bg builder + render-to-path + proportion constants 3.2m/1.4x + material factory), the dir structure (scripts/ models/ renders/{character,moveset,wip/logs}), .gitattributes (mark *.png and *.blend binary), and .gitignore (renders/wip/).\n` +
      `Install branch (decide EMPIRICALLY): try \`ssh mossad "sudo pacman -Sy --noconfirm blender"\`; if sudo prompts non-interactively/hangs OR the build lists NO GPU devices in step below, FALL BACK to the official blender.org LTS tarball (curl + tar xf + symlink into ~/bin, no sudo). SUDO NOTE from caller: pacman may need a password non-interactively — if it fails, use the tarball route.\n` +
      `00_env_check.py: import bpy, engine=CYCLES, cycles prefs compute_device_type='OPTIX' (fallback 'CUDA'), enable EVERY GPU device, scene.cycles.device='GPU', PRINT the device table, render a 1-cube 1080p test frame to /tmp, and ASSERT the enabled-device list contains a GPU (fail loud otherwise).\n` +
      `VALIDATION GATE (must pass for ok=true): headless run exits 0; stdout device table lists >=1 GPU ENABLED with a "Using OptiX" or "Using CUDA" line (both 3060 Ti's ideally, but >=1 is acceptable — warn if <2); non-empty test PNG in /tmp; check free disk (df -h ~ && free -h). Commit scripts + lib on mossad (git add -A + commit; do NOT push).\n` +
      `If GPU refuses to come up after both install branches + 2 retries: this is an environment problem, not a code fix — set ok=false, needsUserJudgment=true, and report the driver/OptiX diagnosis in blockers (plan 12.5).`,
    { label: 'p0-env-gpu', phase: 'P0 Env setup + GPU proof', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
  );
  if (!p0.ok || !p0.gpuUsed) return halt('P0 Env setup + GPU proof', p0);

  // ---- P1: base mesh (SEQUENTIAL, depends on P0) ----
  phase('P1 Base mesh');
  const p1 = await agent(
    `${base}\n\n${FABLE_FLOW}\n\n` +
      `PHASE 1 (plan Section 3 Phase 1). Prereq DONE: Blender+GPU live, scripts/lib_godwyn.py exists. Slice: author scripts/01_base_mesh.py producing a self-contained procedural humanoid "Godwyn_Body" (NO external addons like MB-Lab/Human Generator unless P0 confirmed installed) — primitive+modifier assembly (e.g. Skin+Subsurf on a limb skeleton, subsurf modest: 2 viewport / 2-3 render for VRAM). Metric scale, total height 3.2m, 1.4x-human heroic-but-noble proportions (SPEC 313 — reads as a person, not a giant), barefoot feet modeled (no boots), NEUTRAL A/T-ish stance (posing is P6). Put in the "Godwyn" collection; clear any prior "Godwyn_Body" first (INV-6). Touch ONLY scripts/01_base_mesh.py and proportion constants in scripts/lib_godwyn.py.\n` +
      `VALIDATION GATE: headless exit 0; a clay preview (renders/wip/01_base.png, GPU) shows a 3.2m barefoot noble humanoid in neutral stance; assert bpy.data.objects["Godwyn_Body"] exists in the "Godwyn" collection. Commit the script (git add -A + commit; no push). Surface the clay preview for visual judgment.`,
    { label: 'p1-base-mesh', phase: 'P1 Base mesh', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
  );
  if (!p1.ok) return halt('P1 Base mesh', p1);

  // ---- P2: details (SEQUENTIAL, depends on P1) ----
  phase('P2 Details');
  const p2 = await agent(
    `${base}\n\n${FABLE_FLOW}\n\n` +
      `PHASE 2 (plan Section 3 Phase 2). Prereq DONE: Godwyn_Body exists. Slice: author scripts/02_details.py adding FOUR assets (serialize them in ONE script — do NOT fan out; they share the .blend + the file):\n` +
      `  1) Godwyn_Armor — PARTIAL gold plate over an EXPOSED chest (sternum-filigree suggestion, arm guards, shoulder pieces; NOT full plate). Shrinkwrap over Godwyn_Body with a small offset so it hugs without clipping (SPEC 305-306).\n` +
      `  2) Godwyn_Robe — long deep-blue flowing robe/cape as the PRIMARY garment, gentle static folds (no sim), hem ABOVE ankles so barefoot reads (SPEC 308).\n` +
      `  3) Godwyn_Hair — long golden-blonde, PARTIALLY braided + loose flowing locks, modeled as MESH cards/tubes (NOT particles — cheaper, GPU-friendly, deterministic); asymmetry sells "flowing", must not look like a helmet (SPEC 299-300).\n` +
      `  4) Godwyn_Sword — slim elegant one-handed longsword, blade + hilt + crossguard, its OWN origin AT THE GRIP so P4 can parent it to the hand bone; geometry only (glow is P3) (SPEC 316-318).\n` +
      `All objects in the "Godwyn" collection, prefixed Godwyn_, idempotent rebuild (INV-6), export-friendly names (INV-4). Touch ONLY scripts/02_details.py (+ helpers in lib_godwyn.py).\n` +
      `VALIDATION GATE: headless exit 0; clay preview (renders/wip/02_details.png) shows exposed-chest partial gold armor, blue flowing robe, long partial-braid hair, slim longsword; NO crown, NO boots (INV-3); sword origin at grip. Assert all four Godwyn_* objects exist. Commit script; surface preview for visual judgment.`,
    { label: 'p2-details', phase: 'P2 Details', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
  );
  if (!p2.ok) return halt('P2 Details', p2);

  // ---- P3: materials (SEQUENTIAL, depends on P2) ----
  phase('P3 Materials');
  const p3 = await agent(
    `${base}\n\n${FABLE_FLOW}\n\n` +
      `PHASE 3 (plan Section 3 Phase 3 + Section 4 material table). Prereq DONE: all geometry exists. Slice: author scripts/03_materials.py assigning every material + building the void world. Author Cycles nodes to MATCH the LINEAR RGB values in the SPEC block above (assumption A7 — treat SPEC values as linear sRGB; eyeball against intent):\n` +
      `  - SKIN: Principled base 0.95,0.90,0.82 + Subsurface (pale, low radius) + subtle Emission mix 1.0,0.88,0.45 @ ~2.5 so he self-illuminates WITHOUT blowing out to white (near-translucent demigod skin, SPEC 312/334-336).\n` +
      `  - GOLD ARMOR/HILT/CROSSGUARD: metallic=1, base 0.82,0.65,0.15, low-moderate roughness with slight sheen, faintly worn (roughness noise variation) (SPEC 341).\n` +
      `  - ROBE: deep blue 0.08,0.12,0.35, NO emission, cloth-ish roughness + slight sheen (SPEC 340).\n` +
      `  - SWORD BLADE: mostly non-emissive steel + SUBTLE blue tint + faint emission << skin (restrained; NOT glowing heavily — SPEC 317).\n` +
      `  - HAIR: golden-blonde, lighter/less-saturated than armor gold, sheen.\n` +
      `  - VOID WORLD: near-black world + a FAINT vertical golden light crack behind Godwyn (thin emissive vertical strip OR masked world gradient, ~1.0,0.85,0.4) — it frames, does not dominate (INV-7).\n` +
      `Touch ONLY scripts/03_materials.py (+ lib_godwyn material factory).\n` +
      `VALIDATION GATE: a GPU beauty preview (renders/wip/03_beauty.png) shows pale glowing skin, warm gold armor, deep-blue robe, subtle blue blade, void bg + faint golden vertical crack, colors matching SPEC intent, emission NOT blown out; log shows GPU used (INV-2 — include the "Using OptiX"/"Using CUDA" line in evidence, set gpuUsed). Commit script; surface preview for visual judgment.`,
    { label: 'p3-materials', phase: 'P3 Materials', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
  );
  if (!p3.ok || !p3.gpuUsed) return halt('P3 Materials', p3);

  // ---- P4: rig + lights + cams + SAVE .blend (SEQUENTIAL, opus-class integration) ----
  phase('P4 Rig + lights + cams + .blend');
  const p4 = await agent(
    `${base}\n\n${FABLE_FLOW}\n\n` +
      `PHASE 4 (plan Section 3 Phase 4) — the INTEGRATION point; rig topology + render config + color management here govern EVERY later render, so get it right. Prereq DONE: materials final. Slice: author scripts/04_rig_lights_cams.py and SAVE models/godwyn_phase1.blend. Touch ONLY scripts/04_rig_lights_cams.py (+ lib_godwyn if strictly needed).\n` +
      `  1) ARMATURE: a SIMPLE humanoid rig (spine, arms, legs, neck, a right-hand bone for the sword, optional hair bones). Sane bone names (INV-4). Parent Godwyn_Body with automatic weights; parent Godwyn_Sword to the right-hand bone; robe/armor parented or shrinkwrapped to follow. This is the rig P6 poses — posing 7 stills, NOT animating.\n` +
      `  2) LIGHTING RIG (INV-7 / SPEC 337-339): dramatic warm top-down KEY (gold ~1.0,0.92,0.6), a subtle cool FILL (shadow side not pure black), a RIM to separate him from the void. Godwyn reads as THE light source; dark-fantasy mood, NOT studio-neutral. The P3 golden crack is a background accent.\n` +
      `  3) CAMERAS (named): Cam_Front, Cam_ThreeQuarter_L, Cam_ThreeQuarter_R, Cam_Back, Cam_Side, Cam_Face (close-up), Cam_Sword (detail), Cam_Sheet (wide). Framed for a 3.2m subject.\n` +
      `  4) CYCLES CONFIG: engine=CYCLES, device='GPU', OptiX (CUDA fallback), samples ~128-256 with OptiX denoise ON (OpenImageDenoise fallback if OptiX denoiser unavailable), 2K portrait default (film transparent OFF — keep the void), Filmic or AgX (pick whichever preserves the luminous demigod glow — do NOT let it wash out the gold).\n` +
      `  5) SAVE models/godwyn_phase1.blend (P5/P6 OPEN this; they must NOT rebuild geometry).\n` +
      `VALIDATION GATE: headless exit 0; models/godwyn_phase1.blend saved; a lit GPU preview from Cam_ThreeQuarter (renders/wip/04_lit.png) shows dramatic warm key + rim separation against the void, denoised clean; ALL 8 named cameras present; armature present with Godwyn_Sword parented to the hand bone. Include the GPU log line in evidence (set gpuUsed). Commit script + .blend (git add -A + commit; no push). If rig/render-config/look decisions are genuinely ambiguous or the mesh breaks badly on auto-weights, set ok=false + needsUserJudgment=true and escalate (plan 12.5) rather than guessing.`,
    { label: 'p4-rig-lights-cams', phase: 'P4 Rig + lights + cams + .blend', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
  );
  if (!p4.ok || !p4.gpuUsed) return halt('P4 Rig + lights + cams + .blend', p4);

  // ---- P5 || P6: the ONE genuine parallel fork (both depend only on P4) ----
  // Safe to parallelize: both OPEN models/godwyn_phase1.blend read-only per
  // process, author DISJOINT scripts (05 vs 06), write DISJOINT dirs
  // (renders/character vs renders/moveset) + disjoint wip previews. No worktree
  // needed (SSH-side work; disjoint outputs give the safety). No shared Edit.
  phase('P5 Character sheet renders');
  phase('P6 Moveset renders');
  const [p5, p6] = await parallel([
    () =>
      agent(
        `${base}\n\n${FABLE_FLOW}\n\n` +
          `PHASE 5 (plan Section 3 Phase 5). Prereq DONE: models/godwyn_phase1.blend saved (cams+lights+materials+rig). Slice: author scripts/05_render_sheet.py. Touch ONLY scripts/05_render_sheet.py; write output ONLY to renders/character/. (Runs in parallel with Phase 6 — do NOT touch scripts/06_* or renders/moveset/.)\n` +
          `Open models/godwyn_phase1.blend ONCE (bpy.ops.wm.open_mainfile), set base pose = LOW HANG GUARD (sword hanging low at side, tip toward ground — SPEC 410), then LOOP the sheet cameras (Cam_Front, Cam_ThreeQuarter_L, Cam_ThreeQuarter_R, Cam_Back, Cam_Side, Cam_Face, Cam_Sword) setting scene.camera and rendering each to renders/character/<name>.png at 2K. Face close-up: noble, warm, neutral-sorrowful, NO dark markings (SPEC 301-303). Sword detail: gold hilt + filigree crossguard + subtle blue blade. Re-ASSERT GPU each render (INV-2); a bad single camera re-renders in isolation.\n` +
          `VALIDATION GATE: renders/character/ contains >=6 2K PNGs (front, 3q-L, 3q-R, back, side, face, sword), each non-empty, ALL GPU-rendered (INV-2 — include a "Using OptiX"/"Using CUDA" line per render in evidence, set gpuUsed), all spec-faithful (barefoot, no crown, blue robe, gold partial armor, luminous skin, low-hang sword, void bg + golden crack). Commit renders + script (git add -A + commit; no push). Surface previews for visual judgment.`,
        { label: 'p5-sheet-renders', phase: 'P5 Character sheet renders', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
      ),
    () =>
      agent(
        `${base}\n\n${FABLE_FLOW}\n\n` +
          `PHASE 6 (plan Section 3 Phase 6). Prereq DONE: models/godwyn_phase1.blend saved (rig + hand-bone-parented sword). Slice: author scripts/06_render_moveset.py. Touch ONLY scripts/06_render_moveset.py; write output ONLY to renders/moveset/. (Runs in parallel with Phase 5 — do NOT touch scripts/05_* or renders/character/.)\n` +
          `Open the .blend ONCE, then for EACH of the 7 poses: set armature bone rotations to match the description, use the hand-bone-parented sword (two-handed poses: rotate both arms to grip), choose an action-framing camera, render to the exact filename, then RESET pose to rest before the next (INV-6 — poses must not stack). Render EXACTLY these 7, 2K GPU:\n` +
          `  1) renders/moveset/1_low_hang_guard.png — neutral, sword low at side, tip toward ground (SPEC 410).\n` +
          `  2) renders/moveset/2_x_combo_hit1.png — diagonal cut top-right to bottom-left "\\\\" (SPEC 447).\n` +
          `  3) renders/moveset/3_x_combo_hit2.png — diagonal cut top-left to bottom-right "/".\n` +
          `  4) renders/moveset/4_overhead_slam.png — sword raised TWO-HANDED above head (SPEC 430/462-465).\n` +
          `  5) renders/moveset/5_backhand_rotation.png — mid CCW spin, BACK to camera (SPEC 500-501); ensure hair+robe back read well.\n` +
          `  6) renders/moveset/6_jump_lunge.png — AIRBORNE, sword extended downward (SPEC 416/480); ground-shadow off, add motion cues via pose + camera tilt.\n` +
          `  7) renders/moveset/7_double_spin.png — mid CW rotation, sword extended (SPEC 458-460).\n` +
          `Dramatic per-pose lighting is OK but stay within the dark-fantasy/void aesthetic. Verify the sword stays attached to the hand at extreme rotations. Re-assert GPU each render (INV-2).\n` +
          `VALIDATION GATE: EXACTLY 7 correctly-named 2K GPU PNGs in renders/moveset/, each visibly matching its SPEC pose (low-hang, "\\\\" cut, "/" cut, overhead two-handed, CCW back-to-cam, airborne-down, CW extended), void + golden crack present. Include the GPU log lines in evidence (set gpuUsed). If a single pose deforms ugly at an extreme angle, log it as a deferred item and continue with the others (plan 12.5) rather than halting the batch. Commit renders + script (git add -A + commit; no push). Surface previews for visual judgment.`,
        { label: 'p6-moveset-renders', phase: 'P6 Moveset renders', model: 'fable', agentType: 'general-purpose', schema: phaseResult },
      ),
  ]);
  if (!p5.ok || !p5.gpuUsed) return halt('P5 Character sheet renders', p5);
  if (!p6.ok || !p6.gpuUsed) return halt('P6 Moveset renders', p6);

  // ---- P7: commit + README previews (JOIN on P5 AND P6). NEVER auto-push. ----
  phase('P7 Commit + README previews');
  const p7 = await agent(
    `${base}\n\n` +
      `PHASE 7 (plan Section 3 Phase 7) — the JOIN gate (Phases 5 AND 6 done; all renders exist). Mechanical git + README embed + a small shell orchestrator. Touch ONLY scripts/build_all.sh, README.md, and git.\n` +
      `  1) Prune renders/wip/* (or ensure renders/wip/ stays gitignored — it was added in P0).\n` +
      `  2) Author scripts/build_all.sh: runs scripts 00..06 IN ORDER on mossad (the reproducible recipe, INV-5) and documents per-stage invocation (blender --background --python ...).\n` +
      `  3) Update README.md: add a "Renders" section embedding a few key previews (front, face, sword + a 2-3 pose montage from renders/moveset/), a short "How to regenerate: ssh mossad; bash build_all.sh" note, and a fan-art credit line (Enzo Spag / @DOUJ per SPEC 295).\n` +
      `  4) On mossad: git pull, git add -A, git status review, then COMMIT LOCALLY on mossad. Confirm total renders + .blend < ~100MB (else flag Git LFS as an open item — do NOT introduce LFS unilaterally).\n` +
      `  CRITICAL: DO NOT PUSH. Commit policy is opt-in; the user confirms the push. Set needsUserJudgment=true and state in the summary that the commit is staged locally on mossad awaiting the user's push confirmation.\n` +
      `VALIDATION GATE: working tree clean after the local commit; README shows the Renders section with valid thumbnail paths; build_all.sh present and references 00..06. Report git status + the README diff in evidence.`,
    { label: 'p7-commit-readme', phase: 'P7 Commit + README previews', model: 'default', agentType: 'general-purpose', schema: phaseResult },
  );
  if (!p7.ok) return halt('P7 Commit + README previews', p7);

  // Note: no lifecycle/ tree in this repo (plan lives at repo root as
  // blender-build-plan.txt), so there is nothing to archive. The Phase-7
  // local commit + README preview section IS the final audit artifact (plan
  // 12.6). Push is intentionally left to the user (commit policy is opt-in).
  return {
    status: 'complete',
    built: {
      p0: p0.summary, p1: p1.summary, p2: p2.summary, p3: p3.summary,
      p4: p4.summary, p5: p5.summary, p6: p6.summary, p7: p7.summary,
    },
    renders: {
      characterSheet: p5.outputs || [],
      moveset: p6.outputs || [],
    },
    gpuHonored: [p0, p3, p4, p5, p6].every((r) => r.gpuUsed),
    awaitingUser:
      'All phases passed and the tree is committed LOCALLY on mossad. NOT pushed — confirm the push (commit policy is opt-in). Review the surfaced previews: visual correctness is the real gate (plan Section 8 QA checklist).',
    visualJudgmentFlags: [p1, p2, p3, p4, p5, p6, p7]
      .filter((r) => r && r.needsUserJudgment)
      .map((r) => r.summary),
  };
}
