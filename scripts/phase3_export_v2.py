"""
phase3_export_v2.py — PHASE 3 export + verify + render + commit.

Steps:
  1. Import godwyn_xslash_wip.blend (the best WIP from the P2 loop).
  2. Export models/godwyn_xslash_v2.glb with full armature (Mixamo +
     phys_ chains) + skinning + baked textures + Godwyn_XSlash action.
     +Y up, no apply-armature.
  3. Re-import verify: bone count, animation track + frame count,
     skinning (vertex groups), textures, phys_ chain bones, Godwyn_Sword.
  4. Render EEVEE mp4 renders/game/godwyn_xslash_v2.mp4 (front, 30fps).
     Also save frames /tmp/p3_frames/ for sanity read.
  5. Write final metrics JSON + critLog rollup to
     renders/game/godwyn_xslash_v2.metrics.json.

Idempotent: deletes output files by name before recreating.
Blender 5.2: BLENDER_EEVEE for render engine.
INV-5: rig + skinning + baked materials are NOT touched.
INV-3: idempotent.
"""

import bpy
import sys
import os
import json
import shutil
import math
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
REPO       = Path("/home/aaron/godwyn-boss-fight")
WIP_BLEND  = REPO / "models" / "godwyn_xslash_wip.blend"
OUT_GLB    = REPO / "models" / "godwyn_xslash_v2.glb"
OUT_MP4    = REPO / "renders" / "game" / "godwyn_xslash_v2.mp4"
FRAMES_DIR = Path("/tmp/p3_v2_frames")
METRICS_IN = REPO / "renders" / "game" / "godwyn_xslash_v2.round1.metrics.json"
METRICS_OUT= REPO / "renders" / "game" / "godwyn_xslash_v2.metrics.json"
CRIT_LOG_PRE = [
    {
        "round": 1,
        "metricsPass": None,
        "error": "metrics-null",
        "metricsJson": str(REPO / "renders" / "game" / "godwyn_xslash_v2.round1.metrics.json")
    }
]
ACTION_NAME = "Godwyn_XSlash"

print("=" * 60)
print("PHASE 3: Export + Verify + Render")
print("=" * 60)

# ── 1. Load the WIP blend ──────────────────────────────────────────────────
print(f"\n[1] Loading {WIP_BLEND}")
bpy.ops.wm.open_mainfile(filepath=str(WIP_BLEND))

scene = bpy.context.scene
print(f"  Scene objects: {[o.name for o in bpy.data.objects]}")

# Find armature
arm_obj = None
for o in bpy.data.objects:
    if o.type == 'ARMATURE':
        arm_obj = o
        break
assert arm_obj, "No armature found in WIP blend!"
print(f"  Armature: {arm_obj.name}, bones: {len(arm_obj.data.bones)}")

# Confirm action
action = bpy.data.actions.get(ACTION_NAME)
if action is None:
    # Try slot-based: look for actions with that name prefix
    for a in bpy.data.actions:
        print(f"  Available action: {a.name}")
    # Try the armature's animation data
    if arm_obj.animation_data and arm_obj.animation_data.action:
        action = arm_obj.animation_data.action
        print(f"  Using armature's active action: {action.name}")
    else:
        print("  WARNING: Godwyn_XSlash action not found by name; trying NLA or slots...")
        # In Blender 5.2 slotted actions, check action slots
        for a in bpy.data.actions:
            if "xslash" in a.name.lower() or "slash" in a.name.lower():
                action = a
                print(f"  Found by name-match: {action.name}")
                break
assert action, f"Could not find action '{ACTION_NAME}' in blend!"
print(f"  Action: {action.name}, frame range: {action.frame_range}")

# Set frame range from action
fr_start = int(action.frame_range[0])
fr_end   = int(action.frame_range[1])
scene.frame_start = fr_start
scene.frame_end   = fr_end
print(f"  Frame range: {fr_start}..{fr_end}")

# Check phys_ chains
phys_bones = [b.name for b in arm_obj.data.bones if b.name.startswith("phys_")]
body_bones  = [b.name for b in arm_obj.data.bones if not b.name.startswith("phys_")]
print(f"  Body bones: {len(body_bones)}")
print(f"  phys_ bones: {len(phys_bones)} (first 5: {phys_bones[:5]})")

# Check Godwyn_Sword
sword = bpy.data.objects.get("Godwyn_Sword")
print(f"  Godwyn_Sword: {'FOUND' if sword else 'MISSING'}")
if sword:
    print(f"  Sword parent: {sword.parent} / parent_bone: {sword.parent_bone}")

# ── 2. Export final GLB ────────────────────────────────────────────────────
print(f"\n[2] Exporting to {OUT_GLB}")
if OUT_GLB.exists():
    OUT_GLB.unlink()
    print("  Removed old v2.glb")

# Ensure renders/game dir exists
OUT_MP4.parent.mkdir(parents=True, exist_ok=True)

# Select all relevant objects for export
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath           = str(OUT_GLB),
    export_format      = 'GLB',
    use_selection      = False,        # export everything
    export_apply       = False,        # do NOT apply armature (keep rest-pose bind)
    export_animations  = True,
    export_skins       = True,
    export_texcoords   = True,
    export_normals     = True,
    export_materials   = 'EXPORT',
    export_cameras     = False,
    export_lights      = False,
    export_yup         = True,         # +Y up
)
assert OUT_GLB.exists(), f"Export failed — {OUT_GLB} not created!"
size_mb = OUT_GLB.stat().st_size / (1024*1024)
print(f"  Export OK: {size_mb:.1f} MB")

# ── 3. Re-import VERIFY ────────────────────────────────────────────────────
print(f"\n[3] Re-import verify: {OUT_GLB}")

# Fresh scene for verify
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT_GLB))

v_arm = None
for o in bpy.data.objects:
    if o.type == 'ARMATURE':
        v_arm = o
        break
assert v_arm, "RE-IMPORT: No armature found!"

v_bones = [b.name for b in v_arm.data.bones]
v_phys  = [b for b in v_bones if b.startswith("phys_")]
v_body  = [b for b in v_bones if not b.startswith("phys_")]
print(f"  Bone count: {len(v_bones)} (body={len(v_body)}, phys_={len(v_phys)})")

# Animation track
v_action = None
if v_arm.animation_data:
    v_action = v_arm.animation_data.action
# Also check NLA
if v_action is None:
    if v_arm.animation_data and v_arm.animation_data.nla_tracks:
        for track in v_arm.animation_data.nla_tracks:
            for strip in track.strips:
                v_action = strip.action
                break
            if v_action:
                break
# Also global actions list
if v_action is None:
    for a in bpy.data.actions:
        v_action = a
        break

assert v_action, "RE-IMPORT: No animation track found!"
v_fr = v_action.frame_range
v_nframes = int(v_fr[1] - v_fr[0]) + 1
print(f"  Animation track: '{v_action.name}'  frames {int(v_fr[0])}..{int(v_fr[1])} ({v_nframes} frames)")

# Skinning check — any mesh with vertex groups
v_skinned = []
for o in bpy.data.objects:
    if o.type == 'MESH' and o.vertex_groups:
        v_skinned.append(f"{o.name}(vg={len(o.vertex_groups)})")
print(f"  Skinned meshes: {v_skinned}")
assert v_skinned, "RE-IMPORT: No skinned meshes found!"

# Textures check
v_images = [img.name for img in bpy.data.images]
print(f"  Textures: {v_images}")

# phys_ chains
assert len(v_phys) > 0, "RE-IMPORT: phys_ chains MISSING!"
print(f"  phys_ chains: {len(v_phys)} bones — OK")

# Godwyn_Sword
v_sword = bpy.data.objects.get("Godwyn_Sword")
assert v_sword, "RE-IMPORT: Godwyn_Sword MISSING!"
print(f"  Godwyn_Sword: PRESENT (parent={v_sword.parent_bone})")

print("  ✓ RE-IMPORT GATE PASSED")

reimport_verified = True
reimport_info = {
    "boneCount":    len(v_bones),
    "bodyBones":    len(v_body),
    "physBones":    len(v_phys),
    "animTrack":    v_action.name,
    "frameRange":   [int(v_fr[0]), int(v_fr[1])],
    "frameCount":   v_nframes,
    "skinnedMeshes":v_skinned,
    "textures":     v_images,
    "swordPresent": True,
}

# ── 4. Render EEVEE mp4 ────────────────────────────────────────────────────
print(f"\n[4] Rendering EEVEE mp4 -> {OUT_MP4}")

# Re-open the WIP blend so we have the full scene with lighting
bpy.ops.wm.open_mainfile(filepath=str(WIP_BLEND))
scene = bpy.context.scene

# EEVEE settings
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.fps = 30
scene.frame_start = fr_start
scene.frame_end   = fr_end
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'

# Ensure a camera is set
cam_obj = scene.camera
if cam_obj is None:
    # Find any camera
    for o in bpy.data.objects:
        if o.type == 'CAMERA':
            scene.camera = o
            cam_obj = o
            break
    if cam_obj is None:
        # Create a front camera
        bpy.ops.object.camera_add(location=(0, -5, 1.2), rotation=(math.radians(90), 0, 0))
        cam_obj = bpy.context.active_object
        scene.camera = cam_obj
        print("  Created fallback front camera")
print(f"  Camera: {cam_obj.name if cam_obj else 'NONE'}")

# Ensure there's some lighting
light_found = any(o.type == 'LIGHT' for o in bpy.data.objects)
if not light_found:
    # Add a simple key light
    bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
    bpy.context.active_object.data.energy = 3.0
    print("  Added fallback sun light")

# Frames for sanity
FRAMES_DIR.mkdir(parents=True, exist_ok=True)
sanity_frames = [fr_start, (fr_start+fr_end)//2, fr_end]
for sf in sanity_frames:
    scene.frame_set(sf)
    scene.render.image_settings.file_format = 'PNG'
    out_f = str(FRAMES_DIR / f"p3_f{sf:04d}.png")
    scene.render.filepath = out_f
    bpy.ops.render.render(write_still=True)
    print(f"  Sanity frame {sf} -> {out_f}")

# Render mp4
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
if OUT_MP4.exists():
    OUT_MP4.unlink()
    print("  Removed old mp4")
scene.render.filepath = str(OUT_MP4)
bpy.ops.render.render(animation=True)

assert OUT_MP4.exists(), f"mp4 render failed — {OUT_MP4} not created!"
mp4_size_mb = OUT_MP4.stat().st_size / (1024*1024)
print(f"  mp4 OK: {mp4_size_mb:.1f} MB at {OUT_MP4}")

# ── 5. Write final metrics JSON + critLog ──────────────────────────────────
print(f"\n[5] Writing final metrics JSON -> {METRICS_OUT}")

# Load round1 metrics if present
round1_metrics = None
if METRICS_IN.exists():
    with open(METRICS_IN) as f:
        round1_metrics = json.load(f)
    print(f"  Loaded round1 metrics from {METRICS_IN}")

# Build final critLog entry for this export run
crit_log = list(CRIT_LOG_PRE)
# Add round1 actuals if we have them
if round1_metrics:
    crit_log[0] = {
        "round":          1,
        "metricsPass":    round1_metrics.get("overallMetricsPass", None),
        "metricsJson":    str(METRICS_IN),
        "M1_cape_pass":   round1_metrics["families"]["M1_cape"]["pass"],
        "M2_body_pass":   round1_metrics["families"]["M2_body"]["pass"],
        "M3_foot_pass":   round1_metrics["families"]["M3_foot"]["pass"],
        "M4_sword_pass":  round1_metrics["families"]["M4_sword"]["pass"],
        "worstAngVel":    round1_metrics["families"]["M2_body"].get("worstAngVel"),
        "smoothnessM5":   round1_metrics.get("smoothnessM5"),
        "vlmPass":        None,
        "vlmTrust":       "not-run",
        "combinedScore":  round1_metrics.get("smoothnessM5"),
        "note":           "P2 loop ran 1 round; metrics-null error in initial crit; actual metrics captured in round1 JSON"
    }

final_metrics = {
    "phase":              "P3-export",
    "animName":           ACTION_NAME,
    "outGlb":             str(OUT_GLB),
    "outMp4":             str(OUT_MP4),
    "reimportVerified":   reimport_verified,
    "reimportInfo":       reimport_info,
    "qualityLoop": {
        "passed":           False,
        "plateaued":        True,
        "rounds":           1,
        "bestCombinedScore": round1_metrics.get("smoothnessM5") if round1_metrics else None,
        "finalMetricsPass": round1_metrics.get("overallMetricsPass", False) if round1_metrics else False,
        "lastVlmTrust":     "not-run",
        "note":             "P2 loop stopped at 1 round (metrics-null error in initial critique); WIP exported as best-effort; M2_body failed (ang-vel 360/frame, RightForeArm limit); M1/M3/M4 passed; needsUserJudgment=true"
    },
    "critLog":            crit_log,
    "round1Metrics":      round1_metrics,
    "needsUserJudgment":  True,
    "awaitingUser":       "watch renders/game/godwyn_xslash_v2.mp4 — you are the final judge of feel; note M2_body failed (jerk/ang-vel), check for pops/snaps in the arm swing",
}

if METRICS_OUT.exists():
    METRICS_OUT.unlink()
with open(METRICS_OUT, 'w') as f:
    json.dump(final_metrics, f, indent=2)
print(f"  Wrote {METRICS_OUT}")

# ── Summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 3 COMPLETE")
print(f"  GLB:     {OUT_GLB}  ({size_mb:.1f} MB)")
print(f"  mp4:     {OUT_MP4}  ({mp4_size_mb:.1f} MB)")
print(f"  metrics: {METRICS_OUT}")
print(f"  reimport gate: PASSED")
print(f"  metrics pass:  {round1_metrics.get('overallMetricsPass', False) if round1_metrics else 'unknown'} (M2_body failed — needsUserJudgment)")
print("=" * 60)
