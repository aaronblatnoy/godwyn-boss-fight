"""
p0_phase0_rig_probe.py — Phase 0 rig verification probe.
Enumerates ACTUAL bone names and prefixes from godwyn_game.glb.
Emits a rigMap JSON to /tmp/rigmap.json.
"""
import bpy
import sys
import json
import os

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
OUT = "/tmp/rigmap.json"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arm_obj = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        arm_obj = obj
        break

if arm_obj is None:
    print("ERROR: no armature found")
    sys.exit(1)

all_bones = [b.name for b in arm_obj.data.bones]

# Classify by phys_ prefix
phys_bones = [n for n in all_bones if n.startswith("phys_")]
body_bones = [n for n in all_bones if not n.startswith("phys_")]

# Sub-classify phys_ chains
# Collect all unique second-segment prefixes: phys_X_* -> X
phys_prefixes = {}
for b in phys_bones:
    parts = b.split("_")
    if len(parts) >= 3:
        key = f"phys_{parts[1]}"
    elif len(parts) == 2:
        key = f"phys_{parts[1]}"
    else:
        key = "phys_other"
    phys_prefixes.setdefault(key, []).append(b)

# Specific chains
cape_bones = [n for n in phys_bones if "cape" in n.lower()]
robe_bones = [n for n in phys_bones if "robe" in n.lower()]
hair_bones = [n for n in phys_bones if "hair" in n.lower()]
other_phys = [n for n in phys_bones if n not in cape_bones + robe_bones + hair_bones]

# Confirm sword parenting
sword_obj = bpy.data.objects.get("Godwyn_Sword")
sword_parent_bone = None
sword_found = sword_obj is not None
if sword_obj:
    sword_parent_bone = sword_obj.parent_bone

# Check RightHand bone
righthand_bone = arm_obj.data.bones.get("RightHand")
righthand_found = righthand_bone is not None

rigmap = {
    "armature_name": arm_obj.name,
    "total_bone_count": len(all_bones),
    "body_bone_count": len(body_bones),
    "body_bones": body_bones,
    "phys_bone_count": len(phys_bones),
    "phys_chains_by_prefix": {k: {"count": len(v), "bones": v} for k, v in sorted(phys_prefixes.items())},
    "phys_cape_prefix": "phys_cape" if cape_bones else None,
    "phys_cape_bones": cape_bones,
    "phys_cape_count": len(cape_bones),
    "phys_robe_prefix": "phys_robe" if robe_bones else None,
    "phys_robe_bones": robe_bones,
    "phys_robe_count": len(robe_bones),
    "phys_hair_prefix": "phys_hair" if hair_bones else None,
    "phys_hair_bones": hair_bones,
    "phys_hair_count": len(hair_bones),
    "phys_other_bones": other_phys,
    "sword_object": "Godwyn_Sword",
    "sword_found": sword_found,
    "sword_parent_bone": sword_parent_bone,
    "righthand_bone_found": righthand_found,
    "sword_parented_to_righthand": (sword_parent_bone == "RightHand") if sword_parent_bone else False,
    "rig_gate_pass": (
        len(body_bones) >= 20 and
        (len(cape_bones) > 0 or len(robe_bones) > 0) and
        sword_found and
        sword_parent_bone == "RightHand"
    ),
    "all_bones": all_bones,
}

with open(OUT, "w") as f:
    json.dump(rigmap, f, indent=2)

print(f"RIGMAP_JSON:{OUT}")
print(json.dumps({
    "total_bones": rigmap["total_bone_count"],
    "body_bones": rigmap["body_bone_count"],
    "phys_cape": f"{rigmap['phys_cape_count']} bones ({rigmap['phys_cape_prefix']})",
    "phys_robe": f"{rigmap['phys_robe_count']} bones ({rigmap['phys_robe_prefix']})",
    "phys_hair": f"{rigmap['phys_hair_count']} bones ({rigmap['phys_hair_prefix']})",
    "phys_other": rigmap["phys_other_bones"],
    "sword_parent_bone": sword_parent_bone,
    "sword_parented_to_righthand": rigmap["sword_parented_to_righthand"],
    "rig_gate_pass": rigmap["rig_gate_pass"],
}, indent=2))
