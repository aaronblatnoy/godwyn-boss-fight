"""
probe_rig.py — Phase 0 rig enumeration.
Enumerates armature bones, classifies phys_ chains, confirms Godwyn_Sword parent.
Writes a rigMap JSON to /tmp/godwyn_rigmap.json and prints it.
Blender 5.2 safe (no action.fcurves).
"""
import bpy
import json
import sys
import os

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
OUT = "/tmp/godwyn_rigmap.json"

# --- Load the glb ---
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

# --- Find armature ---
arm_obj = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        arm_obj = obj
        break

if arm_obj is None:
    print("ERROR: no armature found")
    sys.exit(1)

arm = arm_obj.data
all_bones = [b.name for b in arm.bones]

# Classify
phys_bones = [b for b in all_bones if b.startswith("phys_")]
body_bones = [b for b in all_bones if not b.startswith("phys_")]

# phys_ sub-classification by prefix
phys_cape = [b for b in phys_bones if "cape" in b.lower()]
phys_robe = [b for b in phys_bones if "robe" in b.lower()]
phys_hair = [b for b in phys_bones if "hair" in b.lower()]
phys_other = [b for b in phys_bones if b not in phys_cape and b not in phys_robe and b not in phys_hair]

# Extract actual prefixes from phys_other
other_prefixes = {}
for b in phys_other:
    parts = b.split("_")
    if len(parts) >= 2:
        prefix = "_".join(parts[:2])  # e.g. phys_wing
        other_prefixes.setdefault(prefix, []).append(b)

# Sword parent check
sword_obj = bpy.data.objects.get("Godwyn_Sword")
sword_parent_bone = None
sword_parent_obj = None
if sword_obj:
    sword_parent_obj = sword_obj.parent.name if sword_obj.parent else None
    sword_parent_bone = sword_obj.parent_bone if sword_obj.parent_bone else None

# Build rigMap
rig_map = {
    "armature_name": arm_obj.name,
    "total_bone_count": len(all_bones),
    "body_bone_count": len(body_bones),
    "body_bones": sorted(body_bones),
    "phys_total": len(phys_bones),
    "phys_cape_prefix": "phys_cape",
    "phys_cape_count": len(phys_cape),
    "phys_cape_bones": sorted(phys_cape),
    "phys_robe_prefix": "phys_robe",
    "phys_robe_count": len(phys_robe),
    "phys_robe_bones": sorted(phys_robe),
    "phys_hair_prefix": "phys_hair",
    "phys_hair_count": len(phys_hair),
    "phys_hair_bones": sorted(phys_hair),
    "phys_other": phys_other,
    "phys_other_prefixes": other_prefixes,
    "sword_object": "Godwyn_Sword" if sword_obj else "NOT_FOUND",
    "sword_parent_object": sword_parent_obj,
    "sword_parent_bone": sword_parent_bone,
    "sword_parented_to_righthand": sword_parent_bone == "RightHand",
    "all_phys_bones": sorted(phys_bones),
}

with open(OUT, "w") as f:
    json.dump(rig_map, f, indent=2)

print(f"RIGMAP written to {OUT}")
print(json.dumps(rig_map, indent=2))
