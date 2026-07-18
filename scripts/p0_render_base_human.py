"""
p0_render_base_human.py — Render the MPFB2 base human to /tmp for visual inspection.
Phase 0 gate: confirm real face + hands + feet are present.

Usage:
  blender --background --python ~/godwyn-boss-fight/scripts/p0_render_base_human.py 2>&1
"""
import bpy
import sys
import os
import math
import importlib
import mathutils

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

print("=" * 60)
print("[p0_render_base_human] Rendering MPFB2 base human")
print("=" * 60)

# ---------------------------------------------------------------------------
# 1. GPU assertion (INV-2)
# ---------------------------------------------------------------------------
active_gpu = G.enable_gpu()
print(f"[p0_render_base_human] GPU: {active_gpu}")

# ---------------------------------------------------------------------------
# 2. Reset scene
# ---------------------------------------------------------------------------
G.reset_scene()

# ---------------------------------------------------------------------------
# 3. Enable MPFB2 and create human
# ---------------------------------------------------------------------------
print("[p0_render_base_human] Loading MPFB2...")
bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")

def dynamic_import(pkg_suffix, key):
    for amod in sys.modules:
        if amod.endswith(pkg_suffix):
            m = importlib.import_module(amod)
            if hasattr(m, key):
                return getattr(m, key)
    raise ValueError(f"No module ending in '{pkg_suffix}' with attr '{key}'")

HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
print("[p0_render_base_human] Creating neutral base human...")
human = HumanService.create_human()
print(f"[p0_render_base_human] Human: '{human.name}' | verts={len(human.data.vertices)} | dims={tuple(round(d,3) for d in human.dimensions)}")

# ---------------------------------------------------------------------------
# 4. Scale to Godwyn's height (3.2m) and centre on floor
# ---------------------------------------------------------------------------
target_height = 3.2  # metres
current_height = human.dimensions.z
scale_factor = target_height / current_height
human.scale = (scale_factor, scale_factor, scale_factor)
bpy.ops.object.select_all(action='DESELECT')
human.select_set(True)
bpy.context.view_layer.objects.active = human
bpy.ops.object.transform_apply(scale=True)

# Move so feet are at z=0
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
human.location.z = target_height / 2.0
print(f"[p0_render_base_human] Scaled to {target_height}m. New dims: {tuple(round(d,3) for d in human.dimensions)}")

# ---------------------------------------------------------------------------
# 5. Clay material
# ---------------------------------------------------------------------------
mat = bpy.data.materials.new("ClayPreview")
mat.use_nodes = True
nt = mat.node_tree
pbsdf = nt.nodes.get("Principled BSDF")
if pbsdf:
    pbsdf.inputs["Base Color"].default_value = (0.80, 0.72, 0.65, 1.0)
    pbsdf.inputs["Roughness"].default_value = 0.85
human.data.materials.clear()
human.data.materials.append(mat)

# Also apply to any child objects (MPFB2 may create sub-objects)
for child in human.children_recursive:
    if child.type == 'MESH':
        child.data.materials.clear()
        child.data.materials.append(mat)

# ---------------------------------------------------------------------------
# 6. Lights
# ---------------------------------------------------------------------------
# Key light: 3/4 front
key = bpy.data.objects.new("KeyLight", bpy.data.lights.new("KeyLight", "AREA"))
key.data.energy = 1200
key.data.size = 2.0
key.data.color = (1.0, 0.95, 0.85)
key.location = (3.0, -4.0, 5.0)
key.rotation_euler = (math.radians(45), 0, math.radians(30))
bpy.context.scene.collection.objects.link(key)

# Fill light
fill = bpy.data.objects.new("FillLight", bpy.data.lights.new("FillLight", "AREA"))
fill.data.energy = 400
fill.data.size = 3.0
fill.data.color = (0.7, 0.85, 1.0)
fill.location = (-3.0, -2.0, 3.0)
bpy.context.scene.collection.objects.link(fill)

# Rim light (back)
rim = bpy.data.objects.new("RimLight", bpy.data.lights.new("RimLight", "AREA"))
rim.data.energy = 600
rim.data.size = 1.5
rim.data.color = (1.0, 0.92, 0.7)
rim.location = (0.0, 3.5, 4.0)
bpy.context.scene.collection.objects.link(rim)

# ---------------------------------------------------------------------------
# 7. Camera — full body 3/4 view
# ---------------------------------------------------------------------------
cam_data = bpy.data.cameras.new("PreviewCam")
cam_data.lens = 85
cam_data.clip_end = 50.0
cam_obj = bpy.data.objects.new("PreviewCam", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)

# Frame the 3.2m figure with 10% headroom
cam_obj.location = (2.5, -6.5, 1.8)
target = mathutils.Vector((0.0, 0.0, 1.6))
direction = target - mathutils.Vector(cam_obj.location)
rot_q = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_q.to_euler()
bpy.context.scene.camera = cam_obj

# ---------------------------------------------------------------------------
# 8. Cycles GPU render — 512px wide for quick inspection
# ---------------------------------------------------------------------------
scene = bpy.context.scene
G.configure_cycles(scene, samples=64, resolution_x=512, resolution_y=768, use_denoiser=True)

# Force GPU (double-check assertion)
scene.cycles.device = "GPU"
assert scene.cycles.device == "GPU", "GPU not set — INV-2 violated"

out_path = "/tmp/p0_base_human_preview.png"
print(f"[p0_render_base_human] Rendering to {out_path}...")
G.render_to_path(out_path, scene)

# ---------------------------------------------------------------------------
# 9. Validate output
# ---------------------------------------------------------------------------
if not os.path.exists(out_path):
    print(f"[p0_render_base_human] FATAL: no output at {out_path}", file=sys.stderr)
    sys.exit(1)
size = os.path.getsize(out_path)
if size < 4096:
    print(f"[p0_render_base_human] FATAL: suspiciously small output ({size}B)", file=sys.stderr)
    sys.exit(1)
print(f"[p0_render_base_human] Output OK: {out_path} ({size:,} bytes)")

print("=" * 60)
print("[p0_render_base_human] GATE: MPFB2 human rendered. Check image for real face+hands+feet.")
print("=" * 60)
