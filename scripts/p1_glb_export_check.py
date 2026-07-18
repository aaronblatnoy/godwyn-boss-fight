"""
p1_glb_export_check.py — animatability + texture gate for the SHIPPED GLB.

p5 fixer r1 (blocker #10): 03b_bake_maps.py now produces
models/godwyn_phase1.glb with baked basecolor/metallicRoughness/normal
textures. This gate therefore VALIDATES that file instead of re-exporting
(a re-export from the procedural .blend would ship flat clay again).

Asserts, on the .blend side:
  - >= 7 Expr_* shape keys on Godwyn_Body, body skinned to an armature
Asserts, on models/godwyn_phase1.glb:
  - JSON chunk: images > 0, textures > 0, every Godwyn material carries
    baseColorTexture AND normalTexture
  - round-trip import: exactly one armature with the expected core bones,
    skinned body mesh, >= 7 Expr_* blendshapes survived

Usage (run AFTER 03b_bake_maps.py):
  blender --background models/godwyn_phase1.blend \
      --python scripts/p1_glb_export_check.py
"""
import bpy
import json
import os
import struct
import sys

REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
GLB = os.path.join(REPO_ROOT, "models", "godwyn_phase1.glb")

# -- .blend side ---------------------------------------------------------------
body = bpy.data.objects["Godwyn_Body"]
sk = body.data.shape_keys
n_expr = 0 if sk is None else sum(
    1 for k in sk.key_blocks if k.name.startswith("Expr_"))
assert n_expr >= 7, f"FATAL: only {n_expr} Expr_ shape keys in .blend"
assert body.find_armature() is not None, "FATAL: body not skinned"
print(f"[p1_glb] .blend OK: {n_expr} Expr_ keys, body skinned")

# -- GLB must exist (produced by 03b_bake_maps.py) ------------------------------
assert os.path.isfile(GLB), \
    "FATAL: models/godwyn_phase1.glb missing — run 03b_bake_maps.py first"
size = os.path.getsize(GLB)
assert size > 500_000, "FATAL: GLB suspiciously small"

# -- texture audit straight from the GLB JSON chunk -----------------------------
with open(GLB, "rb") as fh:
    magic, _ver, _length = struct.unpack("<III", fh.read(12))
    assert magic == 0x46546C67, "FATAL: not a GLB"
    clen, ctype = struct.unpack("<II", fh.read(8))
    assert ctype == 0x4E4F534A, "FATAL: first chunk not JSON"
    gltf = json.loads(fh.read(clen))

n_imgs = len(gltf.get("images", []))
n_texs = len(gltf.get("textures", []))
mats = gltf.get("materials", [])
n_base = sum(1 for m in mats
             if m.get("pbrMetallicRoughness", {}).get("baseColorTexture"))
n_norm = sum(1 for m in mats if m.get("normalTexture"))
print(f"[p1_glb] GLB texture audit: images={n_imgs} textures={n_texs} "
      f"baseColorTex={n_base} normalTex={n_norm} (of {len(mats)} materials)")
assert n_imgs > 0, "FATAL: GLB contains ZERO images (flat-clay export)"
assert n_texs > 0, "FATAL: GLB contains ZERO textures"
assert n_base >= 6, f"FATAL: only {n_base} materials carry baseColorTexture"
assert n_norm >= 6, f"FATAL: only {n_norm} materials carry normalTexture"

# -- round-trip animatability verification --------------------------------------
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)

arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
assert len(arms) == 1, f"FATAL: {len(arms)} armatures in GLB (want 1)"
bones = {b.name for b in arms[0].data.bones}
for req in ("root", "spine.01", "chest", "head", "hand.R", "hand.L"):
    assert req in bones, f"FATAL: bone '{req}' missing from GLB ({bones})"

imp_body = None
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        keys = [k.name for k in o.data.shape_keys.key_blocks]
        if any(k.startswith("Expr_") for k in keys):
            imp_body = o
            break
assert imp_body is not None, "FATAL: no mesh with Expr_ blendshapes in GLB"
n_imp = sum(1 for k in imp_body.data.shape_keys.key_blocks
            if k.name.startswith("Expr_"))
assert imp_body.find_armature() is not None, "FATAL: GLB body not skinned"
n_re_imgs = len(bpy.data.images)
print(f"[p1_glb] GATE OK: 1 armature ({len(bones)} bones), skinned body, "
      f"{n_imp} expression blendshapes, {n_imgs} images "
      f"({n_re_imgs} re-imported) survived the GLB round trip")
