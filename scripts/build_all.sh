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

# PHASE 2: Dress + hair + sword on the MPFB2 body (REBUILT for the new base)
# Adds Godwyn_Armor / Godwyn_Robe / Godwyn_Hair / Godwyn_Sword to the "Godwyn"
# collection in models/godwyn_phase1.blend, renders GPU previews to
# renders/wip/phase2/.
log_phase "2 — Armor, Robe, Hair, Sword (on Godwyn_Body)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/02_details.py" 2>&1 || log_error "Phase 2 failed"

# PHASE 3: Materials — SPEC colors, skin SSS + inner glow, void world + crack.
# Loads models/godwyn_phase1.blend, assigns all materials, saves back.
log_phase "3 — Materials (skin SSS, gold, robe, blade, hair, void world)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/03_materials.py" 2>&1 || log_error "Phase 3 failed"

# PHASE 4: Rig + Lights + Cameras — humanoid armature on MPFB2 body, dark-fantasy
# lighting rig (warm top-down key / cool fill / warm rim), 8 named cameras,
# Cycles GPU/OptiX config. Saves models/godwyn_phase1.blend + renders 04_lit.png.
log_phase "4 — Armature, Lighting rig, 8 Cameras (Cycles GPU/OptiX)"
"$BLENDER_BIN" --background --python "$SCRIPTS_DIR/04_rig_lights_cams.py" 2>&1 || log_error "Phase 4 failed"

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

echo ""
echo -e "${GREEN}=== ALL PHASES COMPLETE ===${NC}"
echo "Finished at $(date)"
echo ""
echo "Output locations:"
echo "  .blend model: $REPO_ROOT/models/godwyn_phase1.blend"
echo "  Character sheet: $REPO_ROOT/renders/character/*.png (7 views)"
echo "  Moveset poses: $REPO_ROOT/renders/moveset/*.png (7 poses)"
echo ""
echo -e "${YELLOW}Next step: git add -A && git commit  (NEVER push without explicit user instruction)${NC}"
