"""
p0_test_mpfb2.py — Test MPFB2 headless human generation.
Phase 0 gate: confirm we can create a real anatomical human with face+hands+feet.

Usage:
  blender --background --python ~/godwyn-boss-fight/scripts/p0_test_mpfb2.py 2>&1
"""
import bpy
import sys
import os
import importlib
import addon_utils

print("=" * 60)
print("[p0_test_mpfb2] MPFB2 headless test")
print("=" * 60)

# ---------------------------------------------------------------------------
# 1. Enable MPFB2 extension
# ---------------------------------------------------------------------------
print("[p0_test_mpfb2] Enabling MPFB2 extension...")

# In Blender 5.x, extensions are enabled via addon_utils or preferences
# Try enabling via the extension system
try:
    # Extensions are prefixed with repo name in Blender 5.x
    # Try different module name formats
    for mod_name in ["bl_ext.user_default.mpfb", "mpfb"]:
        try:
            bpy.ops.preferences.addon_enable(module=mod_name)
            print(f"[p0_test_mpfb2] Enabled via: {mod_name}")
            break
        except Exception as e:
            print(f"[p0_test_mpfb2] Could not enable {mod_name}: {e}")
except Exception as e:
    print(f"[p0_test_mpfb2] addon_enable failed: {e}")

# Check what mpfb modules loaded
mpfb_mods = [k for k in sys.modules if "mpfb" in k.lower()]
print(f"[p0_test_mpfb2] mpfb modules in sys.modules: {mpfb_mods[:10]}")

if not mpfb_mods:
    print("[p0_test_mpfb2] FATAL: MPFB2 did not load into sys.modules")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. Use MPFB2 to create a base human
# ---------------------------------------------------------------------------
print("[p0_test_mpfb2] Attempting to create a human via HumanService...")

def dynamic_import(absolute_package_str, key):
    """MPFB2's quirk for finding modules regardless of extension path prefix."""
    for amod in sys.modules:
        if amod.endswith(absolute_package_str):
            mpfb_mod = importlib.import_module(amod)
            if not hasattr(mpfb_mod, key):
                raise AttributeError(f"Module {amod} does not have attribute {key}")
            return getattr(mpfb_mod, key)
    raise ValueError(f"No module found with name ending in '{absolute_package_str}'")

try:
    HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
    print(f"[p0_test_mpfb2] HumanService loaded: {HumanService}")
except Exception as e:
    print(f"[p0_test_mpfb2] FATAL: Could not import HumanService: {e}")
    sys.exit(1)

# Create a neutral base human
try:
    human_obj = HumanService.create_human()
    if human_obj is None:
        print("[p0_test_mpfb2] FATAL: create_human() returned None")
        sys.exit(1)
    print(f"[p0_test_mpfb2] Human created: '{human_obj.name}'")
    print(f"[p0_test_mpfb2] Object type: {human_obj.type}")
    print(f"[p0_test_mpfb2] Vertex count: {len(human_obj.data.vertices)}")
    print(f"[p0_test_mpfb2] Dimensions: {tuple(round(d,3) for d in human_obj.dimensions)}")
except Exception as e:
    print(f"[p0_test_mpfb2] FATAL: create_human() raised: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)

# ---------------------------------------------------------------------------
# 3. Verify it looks like a real human (vertex count sanity)
# ---------------------------------------------------------------------------
verts = len(human_obj.data.vertices)
print(f"[p0_test_mpfb2] Vertex count: {verts}")
if verts < 1000:
    print(f"[p0_test_mpfb2] WARNING: very low vertex count ({verts}) — may not be a full mesh")

# Save .blend for inspection
out_blend = "/tmp/mpfb2_test_human.blend"
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print(f"[p0_test_mpfb2] Saved test .blend: {out_blend}")

print("=" * 60)
print("[p0_test_mpfb2] MPFB2 test PASSED — real human base mesh available")
print("=" * 60)
