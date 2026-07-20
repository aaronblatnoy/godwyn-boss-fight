"""
p0_rig_enum.py -- Phase 0 rig enumeration probe.
Imports godwyn_game.glb, enumerates:
  - all armature bones (body + phys_ chains)
  - Godwyn_Sword object and its parent bone
  - phys_ prefix/count breakdown
Prints a JSON rigMap to stdout.
"""
import bpy
import sys
import json

def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    glb = "/home/aaron/godwyn-boss-fight/models/godwyn_game.glb"
    bpy.ops.import_scene.gltf(filepath=glb)

    arm_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            arm_obj = obj
            break

    if arm_obj is None:
        print("ERROR: no armature")
        sys.exit(1)

    all_bones = [b.name for b in arm_obj.data.bones]
    body_bones = [n for n in all_bones if not n.startswith("phys_")]
    phys_bones = [n for n in all_bones if n.startswith("phys_")]

    # Break down phys_ prefixes
    from collections import defaultdict
    phys_groups = defaultdict(list)
    for b in phys_bones:
        parts = b.split("_")
        if len(parts) >= 3:
            prefix = "_".join(parts[:2])  # e.g. phys_cape, phys_robe, phys_hair
        else:
            prefix = b
        phys_groups[prefix].append(b)

    # Sword object
    sword_obj = bpy.data.objects.get("Godwyn_Sword")
    sword_parent_bone = None
    sword_parent_obj = None
    if sword_obj:
        sword_parent_obj = sword_obj.parent.name if sword_obj.parent else None
        sword_parent_bone = sword_obj.parent_bone if sword_obj.parent_bone else None

    # Check for RightHand bone
    rh_bone = arm_obj.pose.bones.get("RightHand")

    rig_map = {
        "armature_name": arm_obj.name,
        "total_bones": len(all_bones),
        "body_bone_count": len(body_bones),
        "body_bones": sorted(body_bones),
        "phys_bone_count": len(phys_bones),
        "phys_groups": {k: {"count": len(v), "bones": sorted(v)} for k, v in sorted(phys_groups.items())},
        "Godwyn_Sword_found": sword_obj is not None,
        "Godwyn_Sword_parent_object": sword_parent_obj,
        "Godwyn_Sword_parent_bone": sword_parent_bone,
        "RightHand_bone_found": rh_bone is not None,
        "gate_sword_parented_to_RightHand": (
            sword_obj is not None and
            sword_parent_bone == "RightHand"
        ),
        "gate_phys_chains_found": len(phys_bones) > 0,
    }

    print("RIGMAP_JSON_BEGIN")
    print(json.dumps(rig_map, indent=2))
    print("RIGMAP_JSON_END")

main()
