#!/bin/bash
################################################################################
# build_all.sh — Reproducible Blender asset build orchestrator for Godwyn
#
# Runs scripts 00 through 06 sequentially on mossad (headless Blender).
# Each stage builds on the prior stage, culminating in a complete character
# model, materials, lighting rig, and render suite.
#
# Usage:
#   ssh mossad "cd ~/godwyn-boss-fight && bash scripts/build_all.sh"
#
# For individual stages:
#   ssh mossad "blender --background --python ~/godwyn-boss-fight/scripts/00_env_check.py 2>&1"
#   ssh mossad "blender --background --python ~/godwyn-boss-fight/scripts/01_base_mesh.py 2>&1"
#   ... etc
#
# All output goes to stdout/stderr; capture to a log if needed:
#   ssh mossad "cd ~/godwyn-boss-fight && bash scripts/build_all.sh 2>&1 | tee build.log"
#
# Invariants (see blender-build-plan.txt):
#   - INV-1 headless-only: --background mode, no GUI
#   - INV-2 GPU-real: each render script asserts >=1 GPU device enabled
#   - INV-5 reproducibility: scripts are idempotent and seed-deterministic
#   - INV-6 idempotent: each script clears prior objects by name before rebuild
################################################################################

set -e  # exit on first error

REPO_ROOT="$HOME/godwyn-boss-fight"
SCRIPTS_DIR="$REPO_ROOT/scripts"
BLENDER_BIN="blender"

# Color output for readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_phase() {
    echo -e "${GREEN}=== PHASE $1 ===${NC}"
}

log_error() {
    echo -e "${RED}ERROR: $1${NC}"
    exit 1
}

# Ensure we're in the repo root
if [ ! -d "$SCRIPTS_DIR" ]; then
    log_error "scripts/ directory not found at $SCRIPTS_DIR"
fi

# Verify Blender is available
if ! command -v "$BLENDER_BIN" &> /dev/null; then
    log_error "Blender ($BLENDER_BIN) not found on PATH"
fi

echo "Godwyn Phase 1 Asset Build — All Stages"
echo "Starting at $(date)"
echo "Repo: $REPO_ROOT"
echo ""
echo "BASE MESH: MPFB2 v2.0.16 (MakeHuman Plugin For Blender 2)"
echo "  Installed at: /home/aaron/.config/blender/5.1/extensions/user_default/mpfb"
echo "  Enable headlessly: bpy.ops.preferences.addon_enable(module='bl_ext.user_default.mpfb')"
echo "  HumanService.create_human() -> 19158-vert anatomical human with real face/hands/feet"
echo "  Probe script: scripts/p0_probe_blender_paths.py"
echo "  Test script:  scripts/p0_test_mpfb2.py"
echo "  Render test:  scripts/p0_render_base_human.py"
echo ""

# PHASE 0: Environment check + MPFB2 gate
log_phase "0 — Environment & GPU Setup (OptiX) + MPFB2 base mesh gate"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/00_env_check.py" 2>&1 || log_error "Phase 0 GPU check failed"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/p0_test_mpfb2.py" 2>&1 || log_error "Phase 0 MPFB2 gate failed"

# PHASE 1: Base human (MPFB2 anatomical human — NOT primitive+Skin modifier)
# Produces Godwyn_Body in the "Godwyn" collection, saves models/godwyn_phase1.blend,
# renders clay previews to renders/wip/phase1/.
log_phase "1 — Base Human (REAL anatomical human via MPFB2)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/01_base_human.py" 2>&1 || log_error "Phase 1 failed"

# PHASE 2: RE-OUTFIT — ornate near-full GOLD PLATE + hair + sword on the
# MPFB2 body. Godwyn_Armor is the full plate kit (cuirass + plackarts,
# gorget, pauldrons + armroot collars, rerebraces/couters/vambraces +
# forearm shells + gauntlets, belt + 4 faulds + 7 tassets + underskirt +
# pelvis plate, cuisses, poleyns, greaves, SABATONS). Godwyn_Cape is now
# ONLY the deep-blue cape (the old cloth skirt is gone). Set GODWYN_FAST=1
# for quick 4-shot previews while iterating.
# (fixer r5: 02 ends with a HEROIC PROPORTION pass — arms +16%, legs +9%,
# head -5% x, renormalized to 3.2m — applied to body+armor+cape+hair+eyes
# together; 04 carries the same remap in its bone table and adds a
# Preview_Ground contact floor, stripped again by 07 before GLB export.)
# (phase4 fixer r5: eye aperture OPENED (visible sclera, 36-deg iris,
# pupil 14) + deeper supratarsal lid crease; brows rebuilt as a dense fan
# of FINE 1.3mm tapered hairs hugging the ridge; lips get a deeper seam +
# vermilion + philtrum; hair width classes merged down (2.2/3.8/5.6mm,
# 380 locks, deeper waves, fine ragged fringe); emblem gets a crisp
# rimmed medallion boss + bigger prouder wreath leaves + bolder rays;
# rerebrace rebuilt as 3 overlapping articulated lames + couter fan x2;
# fauld/tasset lame overlap deepened (no gap slits).)
# (phase4 fixer r4: deeper orbital sockets + stronger brow shadow line +
# midface narrowing + philtrum/lip definition; hair rebuilt with 320 locks
# in wide width classes (2.6/5.0/8.5mm) + two-frequency wave/curl so locks
# undulate; fringe/temple-fall density up (no scalp shell); temple braids
# fall FORWARD framing the face; brow tufts bow proud of the skin.)
# (phase4 fixer r3: hairline advanced ~28mm w/ temple recession; brow/
# zygomatic/jaw planes strengthened; lower-lid shelf + tear trough; iris
# +10% w/ stronger corneal bulge; layered lock lengths + swept-back temple
# braids both sides + sparse flyaways; faulds rebuilt as articulated
# V-point lames (ring fluting gone); greaves get a forged entasis + single
# chased band; poleyns get 3-plate fan flanges; chest emblem redesigned as
# laurel wreath + 12 radiating Order rays (no wagon wheel); the r2 chest
# garland leaf cords (shard read) are deleted — plate-face laurel ornament
# lives in Mat_Gold's structured scroll bands now.)
log_phase "2 — GOLD PLATE armor kit, Cape, Hair, Sword (on Godwyn_Body)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/02_details.py" 2>&1 || log_error "Phase 2 failed"

# PHASE 3: Materials — SPEC colors, skin SSS + inner glow, void world + crack,
# (phase4 fixer r5: skin micro-detail REGION-VARIED (zone noise gates the
# pore fields) at ~half amplitude (speckle cut); gold gets real worn-metal
# character — burnished LOW-ROUGHNESS bright convex-bevel wear, fuller
# crevice/overlap grime, ±0.15 low-freq roughness breakup — and the
# filigree/laurel scroll bands scale to ~10cm motifs w/ stronger relief;
# tabard embroidery band widened ~2x (16 leaf-pairs ~55mm + 18-leaf
# continuous hem garland, thicker stem, brighter two-tone thread); hair
# warmed to true golden-blonde w/ stronger root-to-tip gradient + coat.)
# (phase4 fixer r2: gold engraving is border-masked over a mostly-clean
# polished field — the structured laurel ornament is 02's garland geometry;
# tabard laurel EMBROIDERY is drawn in the panels' TabardUV space as a
# stitched texture band, not physical piping cords; skin gets lid-darkening
# masks + reduced SSS so the face reads sculpted, not waxen.)
# (phase4 fixer r4: gold wear clamps to convex EDGES only (field speckle /
# torn-foil flecks gone — mid-plate is clean polished gold); engraving gets
# near-black cavity fill + brighter gated ridges + roughness contrast +
# 1.5x scroll scale so it reads at Cam_Full; tabard embroidery is a REAL
# alternating laurel leaf-pair garland (elongated lens leaves + stem,
# two-tone gold), band narrowed ~30%; skin gets a 680-scale pore field +
# 0.0062 micro-normal + stronger lip/lid/jaw zoning; eyes get a wet cornea
# (coat rough 0.05, IOR 1.75) + wide dark limbal ring; hair goes
# aniso-sheen (0.92 + coat band) over silkier roughness.)
# (phase4 fixer r3: gold gets deep-cut STRUCTURED LAUREL SCROLL BANDS at
# plate heights + cavity grime (dark cuts / bright ridges) + crevice-
# weighted wear (no uniform speckle); tabard embroidery widened to a real
# 40-55mm alternating-leaf laurel garland band + stitch-direction bump;
# skin pore bump/micro-roughness up + deeper socket AO; hair gets
# per-strand hue+roughness jitter; eyes get lid-contact occlusion.)
# plus PROCEDURAL MICRO DETAIL (object-space coords, no UVs): skin pores +
# mottling, robe thread-weave + nap, gold edge-wear (pointiness) + scratches +
# grime, brushed blade grain, hair strand streaks. All detail ships as BUMP
# (Displacement socket, method=BUMP — game-safe/animatable). Also renders a
# close-up WITH adaptive micro-displacement for beauty comparison ONLY,
# strictly after the .blend save (set GODWYN_SKIP_DISP=1 to skip).
# Loads models/godwyn_phase1.blend, assigns all materials, saves back.
log_phase "3 — Materials (skin SSS, gold, robe, blade, hair, void, micro detail)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/03_materials.py" 2>&1 || log_error "Phase 3 failed"

# PHASE 4: Rig + Lights + Cameras — humanoid armature on MPFB2 body, dark-fantasy
# lighting rig (warm top-down key / cool fill / warm rim), 8 named cameras,
# Cycles GPU/OptiX config. Saves models/godwyn_phase1.blend + renders 04_lit.png.
log_phase "4 — Armature, Lighting rig, 8 Cameras (Cycles GPU/OptiX)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/04_rig_lights_cams.py" 2>&1 || log_error "Phase 4 failed"

# PHASE 4b: Macro-definition form check
# p1_macro_check renders clay form-check views (raking light) to renders/wip/
# (READ them: still a pill? soft face? -> adjust GODWYN_DETAIL_TARGETS in 01).
log_phase "4b — Macro form check"
"$BLENDER_BIN" --background "$REPO_ROOT/models/godwyn_phase1.blend" --python "$SCRIPTS_DIR/p1_macro_check.py" 2>&1 || log_error "Phase 4b macro form check failed"

# PHASE 4c: BAKE procedural detail -> textures + export the SHIPPING GLB
# (p5 fixer r1 blocker #10). 03b smart-UV-unwraps every Godwyn mesh into a
# BakeUV layer, GPU-bakes the procedural node trees to basecolor /
# metallicRoughness / normal PNGs (models/textures/), swaps in baked export
# materials IN MEMORY ONLY (the .blend keeps its procedural beauty mats) and
# exports models/godwyn_phase1.glb WITH textures. p1_glb_export_check then
# validates that GLB: images>0, baseColor+normal textures on every material,
# one armature + skinned body + 7 Expr_* blendshapes across a round trip.
log_phase "4c — Bake maps + textured animatable GLB export gate"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/03b_bake_maps.py" 2>&1 || log_error "Phase 4c bake/export failed"
"$BLENDER_BIN" --background "$REPO_ROOT/models/godwyn_phase1.blend" --python "$SCRIPTS_DIR/p1_glb_export_check.py" 2>&1 || log_error "Phase 4c GLB texture+animatability gate failed"

# PHASE 5: Character sheet renders (7 views, 2K portrait orientation)
# Loads models/godwyn_phase1.blend, sets low hang guard base pose, loops through
# 7 cameras (Front, 3Q Left/Right, Back, Side, Face, Sword detail) and renders
# high-quality PNGs to renders/character/.
log_phase "5 — Character Sheet Renders (7 views, 2K portrait)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/05_render_sheet.py" 2>&1 || log_error "Phase 5 character sheet renders failed"

# PHASE 6: Moveset pose renders (7 action poses, 2K cinematic)
# Loads models/godwyn_phase1.blend, sets each of 7 combat poses via bone
# rotation (low hang guard, X combo 1-2, overhead slam, backhand rotation,
# jump lunge, double spin) and renders high-quality stills to renders/moveset/.
log_phase "6 — Moveset Pose Renders (7 action stills, 2K cinematic)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/06_render_moveset.py" 2>&1 || log_error "Phase 6 moveset pose renders failed"

# PHASE 7: Final GLB export + animatability verification gate
# Opens models/godwyn_phase1.blend, loads pre-baked PNGs from models/textures/
# (produced by Phase 4c / 03b_bake_maps.py), builds glTF-compatible export
# materials, resets armature to rest/bind pose, exports models/godwyn_phase1.glb
# with: skinning INCLUDED, shape keys/blendshapes INCLUDED, normal maps +
# tangents INCLUDED, +Y up, rest-pose bind. Then re-imports headlessly and
# verifies: 1 armature (30 bones), 8 meshes, 7 Expr_* blendshapes, 18 textures.
# Godot-4-ready / glTF 2.0 animatable game asset.
log_phase "7 — Final GLB export + animatability gate (Godot-ready)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/07_export_glb.py" 2>&1 || log_error "Phase 7 GLB export + animatability gate failed"

echo ""
echo -e "${GREEN}=== ALL PHASES COMPLETE ===${NC}"
echo "Finished at $(date)"
echo ""
echo "Output locations:"
echo "  .blend model:    $REPO_ROOT/models/godwyn_phase1.blend"
echo "  Animatable GLB:  $REPO_ROOT/models/godwyn_phase1.glb  (Godot-4-ready)"
echo "  Character sheet: $REPO_ROOT/renders/character/*.png (7 views)"
echo "  Moveset poses:   $REPO_ROOT/renders/moveset/*.png (7 poses)"
echo ""
echo -e "${YELLOW}Next step: git add -A && git commit  (NEVER push without explicit user instruction)${NC}"
