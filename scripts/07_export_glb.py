"""
07_export_glb.py — Phase 7: Final animatable GLB export + verification gate.

Opens models/godwyn_phase1.blend (which carries the full rigged character with
procedural beauty materials), loads the pre-baked PNGs from models/textures/
(produced by 03b_bake_maps.py), builds minimal glTF-compatible export
materials from those on-disk textures, resets to rest pose, and exports
models/godwyn_phase1.glb with:
  - Skinning (armature deform) INCLUDED
  - Shape keys / blendshapes INCLUDED
  - Normal maps + tangents INCLUDED
  - +Y up (glTF convention), rest-pose bind
  - Export materials from baked PNGs (procedural nodes are NOT exported
    by glTF — baked maps are required for a non-flat-clay GLB)

Then re-imports the GLB headlessly and reports:
  bone count, mesh count, blendshape count, material + texture count
to confirm the file is a valid animatable game asset (Godot-ready).

PREREQUISITE: 03b_bake_maps.py must have run and produced models/textures/.
GATE (exits 1 on any failure):
  - GLB exists and is > 500 KB
  - >= 1 armature with all core bones
  - >= 1 skinned mesh
  - >= 7 Expr_* blendshapes on body mesh
  - >= 6 materials with baseColorTexture
  - >= 6 materials with normalTexture

Usage (run AFTER 03b_bake_maps.py):
  blender --background --python ~/godwyn-boss-fight/scripts/07_export_glb.py
"""
import json
import os
import struct
import sys

import bpy

REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
BLEND     = os.path.join(REPO_ROOT, "models", "godwyn_phase1.blend")
TEX_DIR   = os.path.join(REPO_ROOT, "models", "textures")
GLB_OUT   = os.path.join(REPO_ROOT, "models", "godwyn_phase1.glb")

CORE_BONES = ("root", "spine.01", "chest", "head",
              "hand.R", "hand.L", "upper_arm.R", "upper_arm.L",
              "thigh.R", "thigh.L")

# Objects to receive baked export materials (must match 03b_bake_maps.py)
BAKE_OBJECTS = {
    "Godwyn_Body":  0.0,   # metallic constant
    "Godwyn_Armor": 1.0,
    "Godwyn_Tabard":  0.0,
    "Godwyn_Hair":  0.0,
    "Godwyn_Sword": 1.0,
    "Godwyn_Eyes":  0.0,
}


def _load_image(name: str, path: str, colorspace: str = "sRGB") -> bpy.types.Image:
    """Load or re-use a bpy image from disk."""
    existing = bpy.data.images.get(name)
    if existing:
        bpy.data.images.remove(existing)
    img = bpy.data.images.load(path)
    img.name = name
    img.colorspace_settings.name = colorspace
    return img


def _build_export_mat(obj_name: str, metallic: float) -> bpy.types.Material:
    """
    Build a minimal PBR material from the on-disk baked PNGs so the glTF
    exporter sees recognised node trees and includes the textures.
    Returns the new material.
    """
    mat_name = f"Mat_{obj_name}_Export"
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])

    bc_path = os.path.join(TEX_DIR, f"{obj_name}_basecolor.png")
    mr_path = os.path.join(TEX_DIR, f"{obj_name}_mr.png")
    nm_path = os.path.join(TEX_DIR, f"{obj_name}_normal.png")

    assert os.path.isfile(bc_path), f"FATAL: missing baked texture {bc_path}"
    assert os.path.isfile(mr_path), f"FATAL: missing baked texture {mr_path}"
    assert os.path.isfile(nm_path), f"FATAL: missing baked texture {nm_path}"

    bc_img = _load_image(f"{obj_name}_bc",  bc_path, "sRGB")
    mr_img = _load_image(f"{obj_name}_mr",  mr_path, "Non-Color")
    nm_img = _load_image(f"{obj_name}_nm",  nm_path, "Non-Color")

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    # Output
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)

    # Principled BSDF
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    bsdf.inputs["Metallic"].default_value = metallic
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Base Color texture
    bc_tex = nt.nodes.new("ShaderNodeTexImage")
    bc_tex.location = (-200, 300)
    bc_tex.image = bc_img
    bc_tex.image.colorspace_settings.name = "sRGB"
    nt.links.new(bc_tex.outputs["Color"], bsdf.inputs["Base Color"])

    # MetallicRoughness texture (G=roughness, B=metallic — glTF convention)
    mr_tex = nt.nodes.new("ShaderNodeTexImage")
    mr_tex.location = (-200, 0)
    mr_tex.image = mr_img
    mr_tex.image.colorspace_settings.name = "Non-Color"
    # Blender 5.x: ShaderNodeSeparateColor replaced ShaderNodeSeparateRGB
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (0, 0)
    nt.links.new(mr_tex.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    if metallic == 0.0:          # metallic channel from texture only if not constant
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    # Normal map texture
    nm_tex = nt.nodes.new("ShaderNodeTexImage")
    nm_tex.location = (-200, -300)
    nm_tex.image = nm_img
    nm_tex.image.colorspace_settings.name = "Non-Color"
    nm_node = nt.nodes.new("ShaderNodeNormalMap")
    nm_node.location = (0, -300)
    nt.links.new(nm_tex.outputs["Color"], nm_node.inputs["Color"])
    nt.links.new(nm_node.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


# ---------------------------------------------------------------------------
# 1. Load the blend file
# ---------------------------------------------------------------------------
print(f"[07] Loading {BLEND}")
assert os.path.isfile(BLEND), f"FATAL: {BLEND} not found — run 04_rig_lights_cams.py first"
assert os.path.isdir(TEX_DIR),  f"FATAL: {TEX_DIR} not found — run 03b_bake_maps.py first"
bpy.ops.wm.open_mainfile(filepath=BLEND)

# ---------------------------------------------------------------------------
# 2. Verify armature + body in .blend
# ---------------------------------------------------------------------------
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
assert len(arms) >= 1, "FATAL: no armature in .blend"
arm = arms[0]
print(f"[07] Armature: '{arm.name}' ({len(arm.pose.bones)} bones)")

body = bpy.data.objects.get("Godwyn_Body")
assert body is not None, "FATAL: Godwyn_Body not found in .blend"
sk = body.data.shape_keys
n_expr_blend = 0 if sk is None else sum(
    1 for k in sk.key_blocks if k.name.startswith("Expr_"))
assert n_expr_blend >= 7, \
    f"FATAL: only {n_expr_blend} Expr_ shape keys in .blend (need >= 7)"
assert body.find_armature() is not None, \
    "FATAL: Godwyn_Body is not skinned to an armature"
print(f"[07] .blend OK: {n_expr_blend} Expr_ shape keys, body skinned")

# ---------------------------------------------------------------------------
# 3. Reset armature to rest pose (bind pose for the exported skeleton)
# ---------------------------------------------------------------------------
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.select_all(action="SELECT")
bpy.ops.pose.rot_clear()
bpy.ops.pose.loc_clear()
bpy.ops.pose.scale_clear()
bpy.ops.object.mode_set(mode="OBJECT")
print(f"[07] Armature reset to rest/bind pose")

# ---------------------------------------------------------------------------
# 4. Build and assign glTF-compatible export materials from baked textures
#    (In-memory only — the .blend is NOT saved; procedural materials stay)
# ---------------------------------------------------------------------------
print(f"[07] Building export materials from {TEX_DIR}")
for obj_name, metallic in BAKE_OBJECTS.items():
    obj = bpy.data.objects.get(obj_name)
    if obj is None:
        print(f"[07] WARNING: {obj_name} not in scene — skipping")
        continue
    export_mat = _build_export_mat(obj_name, metallic)
    # Replace all material slots with the export material
    obj.data.materials.clear()
    obj.data.materials.append(export_mat)
    print(f"[07]   {obj_name}: assigned {export_mat.name}")

# ---------------------------------------------------------------------------
# 4b. DECIMATE heavy meshes for a game-plausible GLB (fixer r1 minor #7):
#     Godwyn_Armor / Godwyn_Hair carry ~500k verts each of render-grade
#     geometry; surface detail ships in the baked normal maps, so the GLB
#     export gets a Decimate(COLLAPSE) modifier which export_apply=True
#     applies AT EXPORT ONLY (in-memory; the .blend keeps full geometry).
#     Meshes with shape keys (the body) are never decimated.
# ---------------------------------------------------------------------------
# fixer r5: strip the preview-only floor disc — scene-level export must
# ship ONLY the character asset
_ground = bpy.data.objects.get("Preview_Ground")
if _ground is not None:
    bpy.data.objects.remove(_ground, do_unlink=True)
    print("[07]   Preview_Ground removed before export")

DECIMATE_RATIO = float(os.environ.get("GODWYN_GLB_DECIMATE", "0.30"))
for heavy_name in ("Godwyn_Armor", "Godwyn_Hair"):
    heavy = bpy.data.objects.get(heavy_name)
    if heavy is None or heavy.data.shape_keys:
        continue
    if len(heavy.data.vertices) < 100_000 or DECIMATE_RATIO >= 0.999:
        continue
    dec = heavy.modifiers.new("ExportDecimate", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = DECIMATE_RATIO
    # keep the armature modifier LAST so skinning still applies
    while heavy.modifiers.find(dec.name) < len(heavy.modifiers) - 1:
        mods = [m.type for m in heavy.modifiers]
        if mods[-1] == "ARMATURE":
            break
        bpy.context.view_layer.objects.active = heavy
        bpy.ops.object.modifier_move_down(modifier=dec.name)
    # ensure decimate sits BEFORE the armature modifier
    names = [m.name for m in heavy.modifiers]
    arm_idx = next((i for i, m in enumerate(heavy.modifiers)
                    if m.type == "ARMATURE"), None)
    if arm_idx is not None and names.index(dec.name) > arm_idx:
        bpy.context.view_layer.objects.active = heavy
        for _ in range(names.index(dec.name) - arm_idx):
            bpy.ops.object.modifier_move_up(modifier=dec.name)
    print(f"[07] {heavy_name}: export Decimate ratio={DECIMATE_RATIO} "
          f"({len(heavy.data.vertices):,} verts pre-collapse)")

# ---------------------------------------------------------------------------
# 5. Export GLB
# ---------------------------------------------------------------------------
print(f"[07] Exporting GLB -> {GLB_OUT}")
bpy.ops.export_scene.gltf(
    filepath=GLB_OUT,
    export_format="GLB",
    export_yup=True,                    # +Y up (glTF convention)
    use_selection=False,                # export entire scene
    export_apply=True,                  # apply non-armature modifiers
    export_skins=True,                  # include skinning / vertex weights
    export_morph=True,                  # include shape keys / blendshapes
    export_morph_normal=True,           # normals per blendshape
    export_morph_tangent=True,          # tangents per blendshape
    export_normals=True,                # mesh normals
    export_tangents=True,               # tangents for normal maps
    export_materials="EXPORT",          # ship materials + textures
    export_vertex_color="NONE",         # skip vertex colors
    export_cameras=False,               # no cameras in game asset
    export_lights=False,                # no lights in game asset
    export_animations=False,            # no timeline animations yet
    export_nla_strips=False,
    export_def_bones=False,             # export all bones (not just deform)
    export_rest_position_armature=True, # bind/rest pose
)
print(f"[07] Export done")

# ---------------------------------------------------------------------------
# 6. Parse GLB JSON chunk to audit texture coverage
# ---------------------------------------------------------------------------
assert os.path.isfile(GLB_OUT), "FATAL: GLB was not created"
size = os.path.getsize(GLB_OUT)
assert size > 500_000, f"FATAL: GLB suspiciously small ({size} bytes)"

with open(GLB_OUT, "rb") as fh:
    magic, _ver, _length = struct.unpack("<III", fh.read(12))
    assert magic == 0x46546C67, "FATAL: output is not a valid GLB"
    clen, ctype = struct.unpack("<II", fh.read(8))
    assert ctype == 0x4E4F534A, "FATAL: first GLB chunk is not JSON"
    gltf = json.loads(fh.read(clen))

n_imgs  = len(gltf.get("images",    []))
n_texs  = len(gltf.get("textures",  []))
n_mats  = len(gltf.get("materials", []))
mats    = gltf.get("materials", [])
n_base  = sum(1 for m in mats
              if m.get("pbrMetallicRoughness", {}).get("baseColorTexture"))
n_norm  = sum(1 for m in mats if m.get("normalTexture"))

print(f"[07] GLB JSON: materials={n_mats} images={n_imgs} textures={n_texs} "
      f"baseColorTex={n_base} normalTex={n_norm}")

assert n_imgs  > 0, "FATAL: GLB has zero images (flat-clay export)"
assert n_texs  > 0, "FATAL: GLB has zero textures"
assert n_base >= 6, f"FATAL: only {n_base} materials have baseColorTexture (need 6)"
assert n_norm >= 6, f"FATAL: only {n_norm} materials have normalTexture (need 6)"

# ---------------------------------------------------------------------------
# 7. Round-trip re-import — verify animatability
# ---------------------------------------------------------------------------
print(f"[07] Round-trip re-importing {GLB_OUT} ...")
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB_OUT)

imp_arms   = [o for o in bpy.data.objects if o.type == "ARMATURE"]
imp_meshes = [o for o in bpy.data.objects if o.type == "MESH"]

assert len(imp_arms) == 1, \
    f"FATAL: {len(imp_arms)} armatures in re-imported GLB (want 1)"
imp_arm    = imp_arms[0]
bones      = {b.name for b in imp_arm.data.bones}
bone_count = len(bones)

missing = [b for b in CORE_BONES if b not in bones]
assert not missing, f"FATAL: core bones missing after re-import: {missing}"

# Find body mesh (the one with Expr_* shape keys)
imp_body = None
for o in imp_meshes:
    if o.data.shape_keys and any(
            k.name.startswith("Expr_") for k in o.data.shape_keys.key_blocks):
        imp_body = o
        break
assert imp_body is not None, \
    "FATAL: no mesh with Expr_* blendshapes in re-imported GLB"
n_bs = sum(1 for k in imp_body.data.shape_keys.key_blocks
           if k.name.startswith("Expr_"))
assert n_bs >= 7, \
    f"FATAL: only {n_bs} Expr_* blendshapes survived re-import (need 7)"
assert imp_body.find_armature() is not None, \
    "FATAL: body mesh is not skinned after re-import"

mesh_count = len(imp_meshes)
mat_count  = len(bpy.data.materials)
tex_count  = len(bpy.data.images)

# ---------------------------------------------------------------------------
# 8. Final gate report
# ---------------------------------------------------------------------------
print()
print("=" * 68)
print("[07] GATE PASSED — godwyn_phase1.glb is a valid animatable asset")
print(f"  File:        {GLB_OUT}")
print(f"  Size:        {size / 1_048_576:.1f} MB")
print(f"  Armatures:   1 ('{imp_arm.name}', {bone_count} bones)")
print(f"  Meshes:      {mesh_count}")
print(f"  Blendshapes: {n_bs} Expr_* shape keys on body (Godot-ready)")
print(f"  Materials:   {mat_count} ({n_base} baseColorTex, {n_norm} normalTex)")
print(f"  Images:      {tex_count} textures re-imported")
print("  Skeleton:    skinned + animatable (Godot 4 / glTF 2.0 compatible)")
print("=" * 68)
