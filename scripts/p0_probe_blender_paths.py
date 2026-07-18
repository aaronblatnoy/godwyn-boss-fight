"""
p0_probe_blender_paths.py — Probe Blender 5.1.2 addon/extension install paths.
Used during Phase 0 setup to determine where to install MPFB2.
"""
import bpy
import sys
import os
import addon_utils

print("=" * 60)
print("[probe] Blender path probe")
print("=" * 60)

# User resource paths
scripts_path = bpy.utils.user_resource("SCRIPTS")
addons_path  = bpy.utils.user_resource("SCRIPTS", path="addons")
ext_path     = bpy.utils.user_resource("EXTENSIONS")

print(f"  SCRIPTS:    {scripts_path}")
print(f"  ADDONS:     {addons_path}")
print(f"  EXTENSIONS: {ext_path}")
print()

# All addon search paths
print("  addon_utils.paths():")
for p in addon_utils.paths():
    print(f"    {p}")
print()

# Check if MPFB2 is already installed
print("  Checking for mpfb in modules...")
for amod in sys.modules:
    if "mpfb" in amod.lower():
        print(f"    FOUND: {amod}")

# Check extensions repo
ext_base = bpy.utils.user_resource("EXTENSIONS")
if ext_base and os.path.isdir(ext_base):
    print(f"  Extensions dir contents: {os.listdir(ext_base)}")

# Blender version
print(f"\n  Blender version: {bpy.app.version_string}")
print("=" * 60)
print("[probe] DONE")
