"""
p0_rig_probe.py — Phase 0 rig verification.
Imports godwyn_game.glb, enumerates ALL bones, classifies:
  - phys_ chains (cape/robe/hair) with ACTUAL prefixes and counts
  - body bones (non-phys_)
  - confirms Godwyn_Sword parented to RightHand bone

Emits a rigMap JSON to /tmp/p0_rigmap.json and prints it.
DOES NOT trust A-1 blindly -- reports actual names.
"""
import bpy
import sys
import json
import os

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

# Find armature
arm_obj = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        arm_obj = obj
        break

if arm_obj is None:
    print("RIG_PROBE: ERROR no armature found")
    sys.exit(1)

all_bones = [b.name for b in arm_obj.data.bones]
print(f"RIG_PROBE: Total bones = {len(all_bones)}")

# Classify bones
phys_bones = [n for n in all_bones if n.startswith("phys_")]
body_bones = [n for n in all_bones if not n.startswith("phys_")]

# Break phys_ into sub-chains by second segment
from collections import defaultdict
phys_by_prefix = defaultdict(list)
for bn in phys_bones:
    parts = bn.split("_")
    if len(parts) >= 2:
        # e.g. phys_cape_C_00 -> prefix = phys_cape
        # e.g. phys_robe_L_00 -> prefix = phys_robe
        # e.g. phys_hair_00 -> prefix = phys_hair
        prefix = "_".join(parts[:2])  # phys_cape, phys_robe, phys_hair
        phys_by_prefix[prefix].append(bn)
    else:
        phys_by_prefix["phys_other"].append(bn)

phys_summary = {k: {"count": len(v), "bones": sorted(v)} for k, v in phys_by_prefix.items()}

# Check Godwyn_Sword parenting
sword_obj = bpy.data.objects.get("Godwyn_Sword")
sword_info = {}
if sword_obj is None:
    # Try variants
    sword_candidates = [o.name for o in bpy.data.objects if "sword" in o.name.lower() or "Sword" in o.name]
    sword_info = {"found": False, "candidates": sword_candidates, "parent_bone": None}
    print(f"RIG_PROBE: Godwyn_Sword NOT found. Candidates: {sword_candidates}")
else:
    parent_bone = sword_obj.parent_bone if sword_obj.parent_type == 'BONE' else None
    sword_info = {
        "found": True,
        "name": sword_obj.name,
        "parent_type": sword_obj.parent_type,
        "parent_obj": sword_obj.parent.name if sword_obj.parent else None,
        "parent_bone": parent_bone,
        "parented_to_RightHand": parent_bone == "RightHand",
    }
    print(f"RIG_PROBE: Godwyn_Sword parent_bone={parent_bone} (expected RightHand: {parent_bone == 'RightHand'})")

# Mixamo body bone check (look for common Mixamo names)
MIXAMO_EXPECTED = [
    "Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]
# Also check Spine01/Spine02 variants
MIXAMO_ALT = ["Spine01", "Spine02", "Neck1"]
mixamo_found = [n for n in MIXAMO_EXPECTED if n in body_bones]
mixamo_alt_found = [n for n in MIXAMO_ALT if n in body_bones]
mixamo_missing = [n for n in MIXAMO_EXPECTED if n not in body_bones]

print(f"RIG_PROBE: body bones count = {len(body_bones)}")
print(f"RIG_PROBE: phys_ bones count = {len(phys_bones)}")
print(f"RIG_PROBE: phys_ chain breakdown: {list(phys_summary.keys())}")
print(f"RIG_PROBE: Mixamo expected found: {len(mixamo_found)}/{len(MIXAMO_EXPECTED)}")
print(f"RIG_PROBE: Mixamo missing: {mixamo_missing}")
print(f"RIG_PROBE: Alt names found: {mixamo_alt_found}")
print(f"RIG_PROBE: All body bones: {sorted(body_bones)}")

rig_pass = (
    sword_info.get("parented_to_RightHand", False) and
    len(phys_bones) > 0
)

rigmap = {
    "rig_gate_pass": rig_pass,
    "armature_name": arm_obj.name,
    "total_bones": len(all_bones),
    "body_bones_count": len(body_bones),
    "body_bones": sorted(body_bones),
    "phys_bones_count": len(phys_bones),
    "phys_chains": phys_summary,
    "phys_chain_prefixes": sorted(phys_summary.keys()),
    "mixamo_matched": mixamo_found,
    "mixamo_alt_found": mixamo_alt_found,
    "mixamo_missing": mixamo_missing,
    "sword": sword_info,
    "rig_gate_pass": rig_pass,
}

out = "/tmp/p0_rigmap.json"
with open(out, "w") as f:
    json.dump(rigmap, f, indent=2)

print(f"RIGMAP_JSON:{out}")
print(json.dumps(rigmap, indent=2))
print(f"RIG_GATE: {'PASS' if rig_pass else 'FAIL'}")
