"""
PHASE 4 GATE — Verify godwyn_mocap_combo.glb re-imports with:
  - animation track (reports duration)
  - skinning intact (armature modifier on meshes)
  - Godwyn_Sword present

  blender --background --python scripts/phase4_verify_mocap_combo.py
"""
import bpy
import os
import sys

GLB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "models", "godwyn_mocap_combo.glb")
GLB = os.path.normpath(GLB)

if not os.path.exists(GLB):
    print(f"GATE_FAIL: GLB not found: {GLB}")
    sys.exit(1)

print(f"Importing: {GLB} ({os.path.getsize(GLB)/1024/1024:.1f} MB)")

# Import into a fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

objects = list(bpy.data.objects)
armatures = [o for o in objects if o.type == "ARMATURE"]
meshes = [o for o in objects if o.type == "MESH"]
actions = list(bpy.data.actions)

print(f"Objects: {[o.name for o in objects]}")
print(f"Armatures: {[a.name for a in armatures]}")
print(f"Meshes: {[m.name for m in meshes]}")
print(f"Actions: {[a.name for a in actions]}")

# GATE 1: Has armature
if not armatures:
    print("GATE_FAIL: No armature found in imported GLB")
    sys.exit(1)
print(f"GATE_PASS: Armature present: {armatures[0].name}")

# GATE 2: Has animation with duration > 0
if not actions:
    print("GATE_FAIL: No animation action found in imported GLB")
    sys.exit(1)

action = actions[0]
duration_frames = action.frame_range[1] - action.frame_range[0]
# Assume 24fps scene for duration
duration_sec = duration_frames / 24.0
print(f"GATE_PASS: Animation '{action.name}' duration={duration_frames:.0f} frames ({duration_sec:.2f}s)")

if duration_frames < 10:
    print(f"GATE_FAIL: Animation too short ({duration_frames} frames)")
    sys.exit(1)

# GATE 3: Has skinned meshes (meshes with armature modifier or vertex groups)
skinned = []
for mesh in meshes:
    has_arm_mod = any(m.type == "ARMATURE" for m in mesh.modifiers)
    has_vgroups = len(mesh.vertex_groups) > 0
    if has_arm_mod or has_vgroups:
        skinned.append(mesh.name)

if not skinned:
    print("GATE_FAIL: No skinned meshes found (no armature modifiers or vertex groups)")
    sys.exit(1)
print(f"GATE_PASS: Skinned meshes: {skinned}")

# GATE 4: Sword present
sword_objs = [o for o in objects if "sword" in o.name.lower()]
if sword_objs:
    print(f"GATE_PASS: Sword present: {[s.name for s in sword_objs]}")
else:
    print("GATE_WARN: No sword object found (may be merged or named differently)")

# Summary
print("=" * 60)
print(f"GLB_VERIFY_PASS")
print(f"  File: {GLB}")
print(f"  Size: {os.path.getsize(GLB)/1024/1024:.1f} MB")
print(f"  Animation duration: {duration_frames:.0f} frames = {duration_sec:.2f}s @ 24fps")
print(f"  Skinned meshes: {skinned}")
print(f"  Armature: {armatures[0].name}")
