"""
Phase 0 probe: verify Blender + GPU, import godwyn_game.glb + mocap_combo.glb,
confirm shared Mixamo skeleton, report mocap action name / frame range / fps.
Blender 5.2 compatible (slotted actions API).
"""

import bpy
import sys
import os

print("=" * 60)
print("PHASE 0 PROBE - Godwyn Boss Fight")
print("=" * 60)

# ── 1. Blender version ───────────────────────────────────────────
v = bpy.app.version_string
print(f"Blender version : {v}")

# ── 2. GPU / Cycles check ────────────────────────────────────────
prefs = bpy.context.preferences
cycles_prefs = prefs.addons.get("cycles")
if cycles_prefs:
    cp = prefs.addons["cycles"].preferences
    cp.refresh_devices()
    gpu_devices = [d for d in cp.devices if d.type in ("CUDA", "OPTIX", "HIP", "METAL")]
    print(f"Cycles GPU devices found: {len(gpu_devices)}")
    for d in gpu_devices:
        print(f"  [{d.type}] {d.name}  use={d.use}")
else:
    print("WARNING: Cycles addon not found")

# ── 3. Clear scene ───────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)

# ── 4. Mixamo reference bone set (24 bones) ──────────────────────
MIXAMO_BONES = {
    "Hips", "Spine", "Spine1", "Spine2",
    "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
    "LeftHandIndex1", "RightHandIndex1",
}
# Also accept Spine01 variant
MIXAMO_BONES_ALT = set(b.replace("Spine1", "Spine01") for b in MIXAMO_BONES)

def strip_mixamo_prefix(name):
    """Remove 'mixamorig:' or 'mixamorig9:' prefix if present."""
    for prefix in ("mixamorig9:", "mixamorig:"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name

def get_bone_names(armature_obj):
    return {strip_mixamo_prefix(b.name) for b in armature_obj.data.bones}

def check_mixamo_match(bone_names):
    core = MIXAMO_BONES | MIXAMO_BONES_ALT
    hits = bone_names & core
    # Check which of the 24 reference bones are present (accepting Spine01/Spine1 variants)
    matched = set()
    for ref in MIXAMO_BONES:
        alt = ref.replace("Spine1", "Spine01")
        if ref in bone_names or alt in bone_names:
            matched.add(ref)
    return matched

# ── 5. Import godwyn_game.glb ────────────────────────────────────
MODELS_DIR = os.path.expanduser("~/godwyn-boss-fight/models")
godwyn_glb = os.path.join(MODELS_DIR, "godwyn_game.glb")
mocap_glb  = os.path.join(MODELS_DIR, "mocap_combo.glb")

print(f"\nImporting: {godwyn_glb}")
bpy.ops.import_scene.gltf(filepath=godwyn_glb)

# Collect armatures after import
godwyn_armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
print(f"Armatures in scene after godwyn_game.glb import: {[a.name for a in godwyn_armatures]}")

godwyn_arm = godwyn_armatures[0] if godwyn_armatures else None
godwyn_bones = get_bone_names(godwyn_arm) if godwyn_arm else set()
godwyn_mixamo = check_mixamo_match(godwyn_bones)

print(f"\ngodwyn_game armature : {godwyn_arm.name if godwyn_arm else 'NONE'}")
print(f"Total bones          : {len(godwyn_bones)}")
phys_count = sum(1 for b in (godwyn_arm.data.bones if godwyn_arm else []) if b.name.startswith("phys_"))
sword_bones = [b.name for b in (godwyn_arm.data.bones if godwyn_arm else []) if "Sword" in b.name or "sword" in b.name]
print(f"phys_ chain bones    : {phys_count}")
print(f"Sword bones          : {sword_bones}")
print(f"Mixamo bones matched : {len(godwyn_mixamo)}/24  {sorted(godwyn_mixamo)}")
missing_from_godwyn = MIXAMO_BONES - godwyn_mixamo
if missing_from_godwyn:
    print(f"  MISSING from godwyn: {sorted(missing_from_godwyn)}")

# ── 6. Import mocap_combo.glb ────────────────────────────────────
print(f"\nImporting: {mocap_glb}")
bpy.ops.import_scene.gltf(filepath=mocap_glb)

all_arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
mocap_armatures = [a for a in all_arms if a not in godwyn_armatures]
print(f"Armatures after mocap_combo.glb import: {[a.name for a in all_arms]}")
mocap_arm = mocap_armatures[0] if mocap_armatures else None

mocap_bones = get_bone_names(mocap_arm) if mocap_arm else set()
mocap_mixamo = check_mixamo_match(mocap_bones)

print(f"\nmocap_combo armature : {mocap_arm.name if mocap_arm else 'NONE'}")
print(f"Total bones          : {len(mocap_bones)}")
print(f"Mixamo bones matched : {len(mocap_mixamo)}/24  {sorted(mocap_mixamo)}")
missing_from_mocap = MIXAMO_BONES - mocap_mixamo
if missing_from_mocap:
    print(f"  MISSING from mocap: {sorted(missing_from_mocap)}")

# ── 7. Mocap action info (Blender 5.2 slotted actions API) ───────
print("\n--- Mocap action / animation data ---")
scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
print(f"Scene FPS: {fps}")

# Enumerate all actions in the blend data
actions = list(bpy.data.actions)
print(f"Total actions in blend data: {len(actions)}")

for act in actions:
    print(f"\n  Action: '{act.name}'")
    frame_range = act.frame_range
    print(f"    frame_range : {frame_range[0]:.1f} – {frame_range[1]:.1f}")

    # Blender 5.2: slotted actions use act.layers
    if hasattr(act, "layers") and act.layers:
        for li, layer in enumerate(act.layers):
            print(f"    Layer[{li}]: '{layer.name}'  strips={len(layer.strips)}")
            for si, strip in enumerate(layer.strips):
                strip_name = getattr(strip, "name", "<unnamed>")
                print(f"      Strip[{si}]: '{strip_name}'  type={type(strip).__name__}")
                if hasattr(strip, "channelbag"):
                    # Slotted: enumerate slots
                    if hasattr(act, "slots"):
                        for si2, slot in enumerate(act.slots):
                            slot_id = getattr(slot, "name", None) or getattr(slot, "identifier", None) or f"slot[{si2}]"
                            try:
                                cb = strip.channelbag(slot)
                                if cb:
                                    fcurves = list(cb.fcurves)
                                    print(f"        Slot '{slot_id}': {len(fcurves)} fcurves")
                                    # Sample a few fcurve data paths
                                    for fc in fcurves[:5]:
                                        print(f"          {fc.data_path}[{fc.array_index}]  keys={len(fc.keyframe_points)}")
                            except Exception as e:
                                print(f"        Slot '{slot_id}': error – {e}")
                    else:
                        print(f"        (no slots attribute)")
    elif hasattr(act, "fcurves"):
        # Legacy (shouldn't happen in 5.2 but fallback)
        print(f"    fcurves (legacy): {len(list(act.fcurves))}")

# ── 8. Check if mocap arm has anim_data ──────────────────────────
if mocap_arm and mocap_arm.animation_data:
    ad = mocap_arm.animation_data
    print(f"\nMocap armature anim_data.action: {ad.action}")
    if ad.action:
        act = ad.action
        print(f"  Action name: '{act.name}'")
        print(f"  frame_range: {act.frame_range[0]:.1f} – {act.frame_range[1]:.1f}")

# ── 9. REST orientation comparison ───────────────────────────────
print("\n--- Rest pose orientation comparison (sample bones) ---")
SAMPLE = ["Hips", "Spine", "Spine1", "Spine01", "LeftArm", "RightArm",
          "LeftForeArm", "RightForeArm"]

def find_bone(arm, name):
    for b in arm.data.bones:
        if strip_mixamo_prefix(b.name) in (name, name.replace("Spine1", "Spine01"),
                                             name.replace("Spine01", "Spine1")):
            return b
    return None

if godwyn_arm and mocap_arm:
    for sname in SAMPLE:
        gb = find_bone(godwyn_arm, sname)
        mb = find_bone(mocap_arm, sname)
        if gb and mb:
            # head position in armature local space
            gh = tuple(round(x, 4) for x in gb.head_local)
            mh = tuple(round(x, 4) for x in mb.head_local)
            print(f"  {sname:20s}  godwyn={gh}  mocap={mh}")
        else:
            print(f"  {sname:20s}  godwyn={'OK' if gb else 'MISSING'}  mocap={'OK' if mb else 'MISSING'}")

# ── 10. GATE summary ─────────────────────────────────────────────
shared = godwyn_mixamo & mocap_mixamo
print("\n" + "=" * 60)
print("GATE SUMMARY")
print("=" * 60)
print(f"Shared Mixamo bones     : {len(shared)}/24")
print(f"godwyn_game total bones : {len(godwyn_bones)}  (phys_={phys_count}, sword={sword_bones})")
print(f"mocap_combo total bones : {len(mocap_bones)}")

# Determine pass/fail
gate_pass = len(shared) >= 20  # at least 20/24 shared
print(f"\nGATE PASS: {gate_pass}")
if not gate_pass:
    print("FAIL – insufficient shared skeleton coverage")
    sys.exit(1)

print("\nPhase 0 probe complete.")
