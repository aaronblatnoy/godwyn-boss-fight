"""
Boss Fight Phase 0 — Sword Parenting + Swing Bone Map + Test Render
- Import godwyn_game.glb
- Report Godwyn_Sword object: parent, parent_bone, constraints
- Report all bone names relevant to sword swing (shoulder/arm/forearm/hand,
  spine chain, leg step bones)
- Report phys_ chain counts (cape/robe/hair)
- Pose RightHand bone and render 1 frame (EEVEE) to confirm sword follows hand
"""
import bpy, os, math
from mathutils import Matrix, Euler

GLB = os.path.expanduser("~/godwyn-boss-fight/models/godwyn_game.glb")
OUT = os.path.expanduser("~/godwyn-boss-fight/renders/bf_phase0_sword_test.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ── Clear scene ──────────────────────────────────────────────────────────────
bpy.ops.wm.read_factory_settings(use_empty=True)

# ── Import ───────────────────────────────────────────────────────────────────
bpy.ops.import_scene.gltf(filepath=GLB)

print("=" * 70)
print("BF PHASE 0 — SWORD PROBE")
print("=" * 70)

# ── All objects ──────────────────────────────────────────────────────────────
print("\n[ALL OBJECTS]")
for obj in bpy.data.objects:
    parent_name = obj.parent.name if obj.parent else "None"
    pb = obj.parent_bone if obj.parent_bone else ""
    print(f"  {obj.name:35s}  type={obj.type:10s}  parent={parent_name:20s}  parent_bone={pb!r}")

# ── Sword object details ─────────────────────────────────────────────────────
print("\n[SWORD OBJECT DETAIL]")
sword = bpy.data.objects.get("Godwyn_Sword")
if sword is None:
    # Try case-insensitive
    for obj in bpy.data.objects:
        if "sword" in obj.name.lower():
            sword = obj
            break

if sword:
    print(f"  Name:        {sword.name}")
    print(f"  Type:        {sword.type}")
    print(f"  Parent:      {sword.parent.name if sword.parent else 'None'}")
    print(f"  Parent bone: {sword.parent_bone!r}")
    print(f"  Parent type: {sword.parent_type}")
    print(f"  World loc:   {tuple(round(x,4) for x in sword.matrix_world.translation)}")
    print(f"  Constraints: {[c.type for c in sword.constraints]}")
    # Modifiers
    print(f"  Modifiers:   {[m.type for m in sword.modifiers]}")
    # Vertex groups
    print(f"  VGroups:     {[vg.name for vg in sword.vertex_groups]}")
else:
    print("  ERROR: No sword object found!")
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            print(f"  MESH: {obj.name}")

# ── Armature bone map ─────────────────────────────────────────────────────────
print("\n[ARMATURE BONE MAP]")
arm_obj = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm_obj:
    bones = arm_obj.data.bones
    bone_names = [b.name for b in bones]
    print(f"  Armature: {arm_obj.name}  total bones: {len(bone_names)}")

    # Categorize by function
    swing_categories = {
        "SWORD ARM (right side)": ["RightShoulder", "RightArm", "RightForeArm", "RightHand"],
        "SPINE CHAIN":            ["Spine", "Spine01", "Spine02"],
        "HIP/ROOT":               ["Hips", "Root", "Pelvis"],
        "LEFT LEG (step)":        ["LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"],
        "RIGHT LEG (plant)":      ["RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"],
        "HEAD/NECK":              ["neck", "Head", "head_end", "headfront"],
        "LEFT ARM":               ["LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"],
    }

    for category, targets in swing_categories.items():
        found = [n for n in targets if n in bone_names]
        missing = [n for n in targets if n not in bone_names]
        print(f"\n  {category}:")
        for name in found:
            b = bones[name]
            parent_name = b.parent.name if b.parent else "ROOT"
            print(f"    FOUND  {name:20s} parent={parent_name}")
        for name in missing:
            print(f"    MISS   {name}")

    # Phys chains
    print("\n[PHYS CHAIN BONES]")
    phys_bones = [b.name for b in bones if b.name.startswith("phys_")]
    cape_bones  = [n for n in phys_bones if "cape"  in n]
    robe_back_c = [n for n in phys_bones if "robe_back_C"  in n]
    robe_back_l = [n for n in phys_bones if "robe_back_L"  in n]
    robe_back_r = [n for n in phys_bones if "robe_back_R"  in n]
    robe_front_c= [n for n in phys_bones if "robe_front_C" in n]
    robe_front_l= [n for n in phys_bones if "robe_front_L" in n]
    robe_front_r= [n for n in phys_bones if "robe_front_R" in n]
    robe_side_l = [n for n in phys_bones if "robe_side_L"  in n]
    robe_side_r = [n for n in phys_bones if "robe_side_R"  in n]
    hair_back   = [n for n in phys_bones if "hair_back"    in n]
    hair_front_l= [n for n in phys_bones if "hair_front_L" in n]
    hair_front_r= [n for n in phys_bones if "hair_front_R" in n]

    print(f"  Total phys_ bones: {len(phys_bones)}")
    print(f"  Cape chain (phys_cape_C/L/R):")
    print(f"    phys_cape_C: {len([n for n in cape_bones if '_C_' in n])} bones")
    print(f"    phys_cape_L: {len([n for n in cape_bones if '_L_' in n])} bones")
    print(f"    phys_cape_R: {len([n for n in cape_bones if '_R_' in n])} bones")
    print(f"  Robe back chain:")
    print(f"    _C: {len(robe_back_c)}  _L: {len(robe_back_l)}  _R: {len(robe_back_r)}")
    print(f"  Robe front chain:")
    print(f"    _C: {len(robe_front_c)}  _L: {len(robe_front_l)}  _R: {len(robe_front_r)}")
    print(f"  Robe side chain:")
    print(f"    _L: {len(robe_side_l)}  _R: {len(robe_side_r)}")
    print(f"  Hair back chain: {len(hair_back)} bones")
    print(f"  Hair front chain: _L={len(hair_front_l)}  _R={len(hair_front_r)}")
    print(f"  First cape bone: {cape_bones[0] if cape_bones else 'N/A'}")
    print(f"  Last  cape bone: {cape_bones[-1] if cape_bones else 'N/A'}")
    print(f"  First robe_back_C bone: {robe_back_c[0] if robe_back_c else 'N/A'}")
    print(f"  Last  robe_back_C bone: {robe_back_c[-1] if robe_back_c else 'N/A'}")

# ── Test render: pose RightHand and render 1 EEVEE frame ─────────────────────
print("\n[TEST RENDER — EEVEE SWORD SWING POSE]")
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT
scene.frame_set(1)

# Set up basic lighting
bpy.ops.object.light_add(type='SUN', location=(3, -5, 8))
sun = bpy.context.active_object
sun.data.energy = 5.0

# Camera — side view to see the sword
bpy.ops.object.camera_add(location=(5, -6, 2.5))
cam = bpy.context.active_object
cam.rotation_euler = Euler((math.radians(80), 0, math.radians(45)), 'XYZ')
scene.camera = cam

# Pose the RightHand bone (and RightForeArm) to swing the sword up/forward
if arm_obj:
    # Must be in POSE mode
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    def pose_bone(arm, bone_name, rot_xyz_deg):
        pb = arm.pose.bones.get(bone_name)
        if pb:
            pb.rotation_mode = 'XYZ'
            pb.rotation_euler = Euler([math.radians(a) for a in rot_xyz_deg], 'XYZ')
            pb.keyframe_insert(data_path='rotation_euler', frame=1)
            return True
        return False

    # Swing pose: raise right arm, rotate forearm for sword lift
    r = pose_bone(arm_obj, "RightArm",    (-60,   0, -30))   # raise upper arm
    r = pose_bone(arm_obj, "RightForeArm", (-20,  30,   0))  # extend forearm
    r = pose_bone(arm_obj, "RightHand",   (-15,   0,  15))   # wrist angle
    # Lean spine forward slightly
    r = pose_bone(arm_obj, "Spine02",     (  5,   0,   0))

    bpy.ops.object.mode_set(mode='OBJECT')
    print("  Pose applied to RightArm / RightForeArm / RightHand / Spine02")

# Update scene
bpy.context.view_layer.update()

# Render
print(f"  Rendering to: {OUT}")
bpy.ops.render.render(write_still=True)
print("  Render DONE")

print("\n" + "=" * 70)
print("BF PHASE 0 COMPLETE")
print("=" * 70)
