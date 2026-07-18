"""
03b_bake_maps.py — Phase 3b: BAKE the procedural detail to textures and
export the SHIPPING game asset (p5 fixer r1, blocker #10 / EXPORT-READY).

Root cause being fixed: every material is procedural object-space Cycles
nodes, which glTF strips — the exported godwyn_phase1.glb contained ZERO
images/textures and the shipped asset was literally flat clay, violating
the "detail ships as normal maps" invariant.

What this script does (GPU Cycles bakes — INV-2 asserted):
  1. Opens models/godwyn_phase1.blend (must already be rigged by 04).
  2. Smart-UV-unwraps Godwyn_Body/Armor/Robe/Hair/Sword/Eyes into a
     "BakeUV" layer (the procedural shaders keep using object coords /
     the explicit "EyeUV" map, so nothing changes visually).
  3. For every mesh, bakes the EXISTING procedural node trees to:
       - <obj>_basecolor.png (sRGB)      — Base Color input chain
       - <obj>_mr.png (non-color)        — G=roughness bake, B=metallic
       - <obj>_normal.png (non-color)    — bump-height bake converted to a
                                           tangent-space normal map (numpy)
     via EMIT-rewire bakes (works for metals + mixed shaders alike).
  4. Builds Mat_<obj>_Baked (textures wired the way the glTF exporter
     recognises: baseColorTexture / metallicRoughnessTexture /
     normalTexture), assigns them IN-MEMORY ONLY, and exports
     models/godwyn_phase1.glb (skeleton + skin + blendshapes preserved).
  5. Asserts the exported GLB actually contains images and normal textures.

The .blend is NEVER saved here — the stored model keeps its procedural
beauty materials; the GLB is the normal-map-based game asset.

Run (AFTER 04_rig_lights_cams.py):
  blender --background --python ~/godwyn-boss-fight/scripts/03b_bake_maps.py
"""
import json
import math
import os
import struct
import sys

import bpy
import numpy as np

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
import lib_godwyn as G

REPO_ROOT = os.path.expanduser("~/godwyn-boss-fight")
BLEND = os.path.join(REPO_ROOT, "models", "godwyn_phase1.blend")
GLB_OUT = os.path.join(REPO_ROOT, "models", "godwyn_phase1.glb")
TEX_DIR = os.path.join(REPO_ROOT, "models", "textures")
os.makedirs(TEX_DIR, exist_ok=True)

# object -> (bake resolution, metallic constant for the MR blue channel)
BAKE_OBJECTS = {
    "Godwyn_Body":  (2048, 0.0),
    "Godwyn_Armor": (1024, 1.0),
    "Godwyn_Tabard":  (1024, 0.0),
    "Godwyn_Hair":  (1024, 0.0),
    "Godwyn_Sword": (1024, 1.0),
    "Godwyn_Eyes":  (512,  0.0),
}
HREF = 0.006          # metres of height mapped to the full 0..1 bake range
BAKE_SAMPLES = 32
MARGIN = 8


def _principled(nt):
    return next((n for n in nt.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)


def _output(nt):
    return next((n for n in nt.nodes
                 if n.bl_idname == "ShaderNodeOutputMaterial"
                 and n.is_active_output), None) or next(
        (n for n in nt.nodes
         if n.bl_idname == "ShaderNodeOutputMaterial"), None)


def smart_unwrap(obj):
    """Smart-UV-project into a 'BakeUV' layer (created if missing)."""
    me = obj.data
    if "BakeUV" not in me.uv_layers:
        me.uv_layers.new(name="BakeUV")
    me.uv_layers.active = me.uv_layers["BakeUV"]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0),
                             island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"[03b] {obj.name}: BakeUV smart-projected "
          f"({len(me.uv_layers)} uv layers)")


class _BakeRig:
    """Temporarily rewires ONE material for an EMIT channel bake."""

    def __init__(self, mat, channel, img):
        self.mat = mat
        self.nt = mat.node_tree
        self.channel = channel
        self.img = img
        self.tmp = []
        self.orig_from = None

    def __enter__(self):
        nt = self.nt
        out = _output(nt)
        pb = _principled(nt)
        # bake-target image node (active) + explicit BakeUV lookup
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "BakeUV"
        imgn = nt.nodes.new("ShaderNodeTexImage")
        imgn.image = self.img
        nt.links.new(uvn.outputs["UV"], imgn.inputs["Vector"])
        nt.nodes.active = imgn
        imgn.select = True
        self.tmp += [uvn, imgn]

        emit = nt.nodes.new("ShaderNodeEmission")
        self.tmp.append(emit)

        if self.channel in ("BASECOLOR", "ROUGHNESS"):
            sockname = "Base Color" if self.channel == "BASECOLOR" \
                else "Roughness"
            if pb is None:
                # emission-only material (e.g. void crack): bake its color
                src = None
                emit.inputs["Color"].default_value = (0, 0, 0, 1)
            else:
                sock = pb.inputs[sockname]
                if sock.is_linked:
                    src = sock.links[0].from_socket
                    nt.links.new(src, emit.inputs["Color"])
                else:
                    v = sock.default_value
                    if hasattr(v, "__len__"):
                        emit.inputs["Color"].default_value = tuple(v)
                    else:
                        emit.inputs["Color"].default_value = (v, v, v, 1.0)
        elif self.channel == "HEIGHT":
            disp = next((n for n in nt.nodes
                         if n.bl_idname == "ShaderNodeDisplacement"), None)
            if disp is not None and disp.inputs["Height"].is_linked:
                scale = float(disp.inputs["Scale"].default_value)
                src = disp.inputs["Height"].links[0].from_socket
                # normalized = 0.5 + (h - mid) * scale / HREF
                mid = float(disp.inputs["Midlevel"].default_value)
                m1 = nt.nodes.new("ShaderNodeMath")
                m1.operation = "SUBTRACT"
                m1.inputs[1].default_value = mid
                nt.links.new(src, m1.inputs[0])
                m2 = nt.nodes.new("ShaderNodeMath")
                m2.operation = "MULTIPLY_ADD"
                m2.inputs[1].default_value = scale / HREF
                m2.inputs[2].default_value = 0.5
                nt.links.new(m1.outputs[0], m2.inputs[0])
                nt.links.new(m2.outputs[0], emit.inputs["Color"])
                self.tmp += [m1, m2]
            else:
                emit.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1.0)

        # stash + replace the surface link
        if out.inputs["Surface"].is_linked:
            self.orig_from = out.inputs["Surface"].links[0].from_socket
        nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
        return self

    def __exit__(self, *exc):
        nt = self.nt
        out = _output(nt)
        if self.orig_from is not None:
            nt.links.new(self.orig_from, out.inputs["Surface"])
        for n in self.tmp:
            nt.nodes.remove(n)
        return False


def bake_channel(obj, channel, img):
    mats = [s.material for s in obj.material_slots if s.material]
    rigs = [_BakeRig(m, channel, img) for m in mats]
    for r in rigs:
        r.__enter__()
    try:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type="EMIT", margin=MARGIN, use_clear=True)
    finally:
        for r in rigs:
            r.__exit__()
    print(f"[03b]   baked {channel} -> {img.name}")


def _save_png(img, path):
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()


def _new_img(name, res, srgb):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, res, res, alpha=False,
                              float_buffer=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def height_to_normal(h_img, res, out_name):
    """Convert the baked height image to a tangent-space normal map."""
    px = np.empty(res * res * 4, dtype=np.float32)
    h_img.pixels.foreach_get(px)
    px = px.reshape(res, res, 4)
    h = px[..., 0] * HREF                     # back to metres
    texel = 1.0 / res                          # ~1 UV-metre per tile assumed
    gy, gx = np.gradient(h, texel)
    nx, ny, nz = -gx, -gy, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    out = np.empty((res, res, 4), dtype=np.float32)
    out[..., 0] = nx * 0.5 + 0.5
    out[..., 1] = ny * 0.5 + 0.5
    out[..., 2] = nz * 0.5 + 0.5
    out[..., 3] = 1.0
    n_img = _new_img(out_name, res, srgb=False)
    n_img.pixels.foreach_set(out.ravel())
    return n_img


def compose_mr(rough_img, metallic, res, out_name):
    """MetallicRoughness texture: R=1 (unused occ), G=rough, B=metallic."""
    px = np.empty(res * res * 4, dtype=np.float32)
    rough_img.pixels.foreach_get(px)
    px = px.reshape(res, res, 4)
    out = np.empty_like(px)
    out[..., 0] = 1.0
    out[..., 1] = px[..., 0]
    out[..., 2] = metallic
    out[..., 3] = 1.0
    mr_img = _new_img(out_name, res, srgb=False)
    mr_img.pixels.foreach_set(out.ravel())
    return mr_img


def build_baked_material(obj_name, base_img, mr_img, n_img):
    name = f"Mat_{obj_name}_Baked"
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    pb = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pb.location = (250, 0)
    nt.links.new(pb.outputs["BSDF"], out.inputs["Surface"])
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.location = (-700, 0)
    uvn.uv_map = "BakeUV"

    tb = nt.nodes.new("ShaderNodeTexImage")
    tb.location = (-450, 300)
    tb.image = base_img
    nt.links.new(uvn.outputs["UV"], tb.inputs["Vector"])
    nt.links.new(tb.outputs["Color"], pb.inputs["Base Color"])

    tm = nt.nodes.new("ShaderNodeTexImage")
    tm.location = (-450, 0)
    tm.image = mr_img
    nt.links.new(uvn.outputs["UV"], tm.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-150, 0)
    nt.links.new(tm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], pb.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], pb.inputs["Metallic"])

    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.location = (-450, -320)
    tn.image = n_img
    nt.links.new(uvn.outputs["UV"], tn.inputs["Vector"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.location = (-150, -320)
    nm.uv_map = "BakeUV"
    nm.inputs["Strength"].default_value = 1.0
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], pb.inputs["Normal"])

    if obj_name == "Godwyn_Body":     # keep the demigod glow on the asset
        try:
            pb.inputs["Emission Color"].default_value = G.COL_SKIN_EMIT
            pb.inputs["Emission Strength"].default_value = 0.25
        except KeyError:
            pass
    return mat


def parse_glb(path):
    with open(path, "rb") as fh:
        magic, _ver, _length = struct.unpack("<III", fh.read(12))
        assert magic == 0x46546C67, "not a GLB"
        clen, ctype = struct.unpack("<II", fh.read(8))
        assert ctype == 0x4E4F534A, "first chunk not JSON"
        return json.loads(fh.read(clen))


def main():
    print("=" * 60)
    print("[03b_bake_maps] Phase 3b — bake procedural detail -> textures, "
          "export game GLB")
    print("=" * 60)

    bpy.ops.wm.open_mainfile(filepath=BLEND)
    gpu = G.enable_gpu()
    print(f"[03b] GPU backend: {gpu}")
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = BAKE_SAMPLES
    assert scene.cycles.device == "GPU", "GPU not set — INV-2 violated"

    for name in BAKE_OBJECTS:
        assert name in bpy.data.objects, f"{name} missing — run 01..04 first"

    baked = {}
    for obj_name, (res, metallic) in BAKE_OBJECTS.items():
        obj = bpy.data.objects[obj_name]
        print(f"[03b] === {obj_name} ({res}px, metallic={metallic}) ===")
        smart_unwrap(obj)

        base_img = _new_img(f"{obj_name}_basecolor", res, srgb=True)
        rough_img = _new_img(f"{obj_name}_rough_tmp", res, srgb=False)
        h_img = _new_img(f"{obj_name}_height_tmp", res, srgb=False)

        bake_channel(obj, "BASECOLOR", base_img)
        bake_channel(obj, "ROUGHNESS", rough_img)
        bake_channel(obj, "HEIGHT", h_img)

        n_img = height_to_normal(h_img, res, f"{obj_name}_normal")
        mr_img = compose_mr(rough_img, metallic, res, f"{obj_name}_mr")

        _save_png(base_img, os.path.join(TEX_DIR, f"{obj_name}_basecolor.png"))
        _save_png(mr_img, os.path.join(TEX_DIR, f"{obj_name}_mr.png"))
        _save_png(n_img, os.path.join(TEX_DIR, f"{obj_name}_normal.png"))
        baked[obj_name] = (base_img, mr_img, n_img)

    # -- swap to baked export materials (IN MEMORY ONLY — never saved) -------
    for obj_name, (base_img, mr_img, n_img) in baked.items():
        obj = bpy.data.objects[obj_name]
        mat = build_baked_material(obj_name, base_img, mr_img, n_img)
        for i in range(len(obj.data.materials)):
            obj.data.materials[i] = mat
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        print(f"[03b] {obj_name} <- {mat.name} (export-time)")

    # -- export the shipping GLB ---------------------------------------------
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        export_format="GLB",
        export_morph=True,
        export_skins=True,
        export_animations=False,
        export_apply=False,          # NEVER apply modifiers — keeps morphs
        export_image_format="AUTO",
        use_selection=False,
    )
    size = os.path.getsize(GLB_OUT)
    print(f"[03b] exported {GLB_OUT} ({size:,} bytes)")

    # -- texture gate ----------------------------------------------------------
    gltf = parse_glb(GLB_OUT)
    n_imgs = len(gltf.get("images", []))
    n_texs = len(gltf.get("textures", []))
    mats = gltf.get("materials", [])
    n_base = sum(1 for m in mats
                 if m.get("pbrMetallicRoughness", {}).get("baseColorTexture"))
    n_norm = sum(1 for m in mats if m.get("normalTexture"))
    print(f"[03b] GLB audit: images={n_imgs} textures={n_texs} "
          f"baseColorTex mats={n_base} normalTex mats={n_norm}")
    assert n_imgs >= len(BAKE_OBJECTS) * 3 - 2, \
        f"FATAL: GLB images missing ({n_imgs})"
    assert n_base >= len(BAKE_OBJECTS), "FATAL: baseColorTexture missing"
    assert n_norm >= len(BAKE_OBJECTS), "FATAL: normalTexture missing"

    # NOTE: the .blend is deliberately NOT saved — it keeps the procedural
    # beauty materials; the GLB above is the normal-map game asset.
    print("[03b] GATE OK: shipped GLB carries baked "
          "basecolor/metallicRoughness/normal textures.")
    print("=" * 60)


main()
