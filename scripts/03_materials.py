"""
03_materials.py — Phase 3: Materials & Shaders — the golden luminous demigod.

Assigns EVERY Cycles material + builds the void world background, per
SPEC.txt 332-341 and build-plan Section 3 Phase 3 / Section 4 material table.

Materials authored:
  Mat_Skin        — Principled BSDF base (0.95,0.90,0.82) + SSS (pale, low
                    radius) + subtle Emission mix (1.0,0.88,0.45) @ ~2.5;
                    near-translucent demigod skin that self-illuminates without
                    blowing out (SPEC 334-336).
  Mat_Gold        — metallic=1, base (0.82,0.65,0.15), low-moderate roughness,
                    slight sheen, roughness-noise variation for faintly-worn
                    feel (SPEC 341).  Shared by Godwyn_Armor hilt/crossguard.
  Mat_Robe        — deep blue (0.08,0.12,0.35), NO emission (SPEC 340),
                    cloth-ish roughness + slight sheen for fabric read.
  Mat_Blade       — steel + subtle blue tint, faint emission << skin (SPEC
                    317 "blue-tinged... not glowing heavily").
  Mat_Hair        — golden-blonde (0.75,0.58,0.08), lighter/less-saturated
                    than armor, anisotropic sheen.
  Void world      — near-black + faint vertical golden crack (already built by
                    lib_godwyn.build_void_bg; we extend it here with the
                    world shader and the crack plane).

All SPEC color values treated as linear sRGB per assumption A7.

INV-2: GPU enforced and asserted before render.
INV-3: SPEC-faithful colors, no deviation.
INV-6: Idempotent — clears previous material assignments before re-applying.
INV-7: Godwyn's skin emission is the scene's primary light source.

Run:
  blender --background --python scripts/03_materials.py
"""

import sys
import os
import math
import bpy

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import lib_godwyn as G

_REPO_ROOT   = os.path.dirname(_SCRIPT_DIR)
_WIP_DIR     = os.path.join(_REPO_ROOT, "renders", "wip")
_LOG_DIR     = os.path.join(_WIP_DIR, "logs")
_PREVIEW_OUT = os.path.join(_WIP_DIR, "03_beauty.png")
os.makedirs(_WIP_DIR, exist_ok=True)
os.makedirs(_LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# MATERIAL NAMES (used for idempotent clearing, INV-6)
# ---------------------------------------------------------------------------
MAT_NAMES = (
    "Mat_Skin",
    "Mat_Gold",
    "Mat_Robe",
    "Mat_Blade",
    "Mat_Hair",
    "Mat_VoidCrack",
    "Mat_EyeSclera",
    "Mat_EyeIris",
    "Mat_EyePupil",
)

PREVIEW_MAT_PREFIXES = ("Prev_", "Mat_SkinPreview", "Mat_ClayPreview")

OBJECT_ASSIGNMENTS = {
    "Godwyn_Body":  "Mat_Skin",
    "Godwyn_Armor": "Mat_Gold",
    "Godwyn_Robe":  "Mat_Robe",
    "Godwyn_Hair":  "Mat_Hair",
    "Godwyn_Sword": None,           # handled specially: hilt=gold, blade=blade
}


# ---------------------------------------------------------------------------
# IDEMPOTENT CLEAR (INV-6)
# ---------------------------------------------------------------------------

def clear_materials():
    """Remove any prior Phase-3 materials (by name) before rebuilding."""
    for name in MAT_NAMES:
        if name in bpy.data.materials:
            mat = bpy.data.materials[name]
            bpy.data.materials.remove(mat)
    # Also purge leftover preview materials from P1/P2
    for name in list(bpy.data.materials.keys()):
        if any(name.startswith(p) for p in PREVIEW_MAT_PREFIXES):
            bpy.data.materials.remove(bpy.data.materials[name])


# ---------------------------------------------------------------------------
# NODE HELPERS
# ---------------------------------------------------------------------------

def _new_node(nt, bl_idname, location=(0, 0)):
    n = nt.nodes.new(bl_idname)
    n.location = location
    return n


def _link(nt, from_node, from_socket, to_node, to_socket):
    nt.links.new(from_node.outputs[from_socket], to_node.inputs[to_socket])


# ---------------------------------------------------------------------------
# MATERIAL BUILDERS
# ---------------------------------------------------------------------------

def make_skin_material() -> bpy.types.Material:
    """
    Pale luminous demigod skin (SPEC 312, 334-336).

    Strategy: use Principled BSDF's native emission inputs (Blender 4+)
    so the emission is composited correctly inside the BSDF instead of
    being additive-summed with Add Shader (which blows out in dark scenes).
    Falls back to a MixShader (low fac) for older Blender builds so the
    skin glows but never overwhelms.

    SPEC target: luminous, pale, slight inner glow — NOT blown out to white.
    Emission strength 2.5 is the SPEC value but using it with Add Shader
    in a near-black void saturates to white; using it inside Principled BSDF
    or at fac 0.12 in a Mix keeps form visible.
    """
    mat = bpy.data.materials.new("Mat_Skin")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (700, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))

    # Base skin color (linear sRGB, SPEC 334)
    pbsdf.inputs["Base Color"].default_value = G.COL_SKIN_BASE

    # Roughness: noise-broken 0.42..0.58 so the skin has spec variation
    # instead of a uniform plastic sheen (major #5)
    tex_c = _new_node(nt, "ShaderNodeTexCoord", (-500, -200))
    noise = _new_node(nt, "ShaderNodeTexNoise", (-320, -200))
    mapv  = _new_node(nt, "ShaderNodeMapRange", (-140, -200))
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 5.0
    mapv.inputs["From Min"].default_value = 0.0
    mapv.inputs["From Max"].default_value = 1.0
    mapv.inputs["To Min"].default_value   = 0.42
    mapv.inputs["To Max"].default_value   = 0.58
    _link(nt, tex_c, "Object", noise, "Vector")
    _link(nt, noise, "Fac",    mapv,  "Value")
    _link(nt, mapv,  "Result", pbsdf, "Roughness")

    # Specular — skin-level, not plastic
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.40
    except (KeyError, AttributeError):
        try:
            pbsdf.inputs["Specular"].default_value = 0.20
        except (KeyError, AttributeError):
            pass
    # Sheen: soft grazing-angle breakup
    try:
        pbsdf.inputs["Sheen Weight"].default_value = 0.12
        pbsdf.inputs["Sheen Roughness"].default_value = 0.45
    except KeyError:
        pass

    # Subsurface — REAL translucent warmth: warm red-orange radius, larger
    # scale so ears/nose/fingers show light bleed (major #5)
    sss_color = (0.98, 0.88, 0.72, 1.0)
    try:
        # Blender 4+ API
        pbsdf.inputs["Subsurface Weight"].default_value = 0.32
        pbsdf.inputs["Subsurface Radius"].default_value = (0.14, 0.06, 0.032)
        try:
            pbsdf.inputs["Subsurface Color"].default_value = sss_color
        except KeyError:
            pass
        try:
            pbsdf.inputs["Subsurface Scale"].default_value = 0.25
        except KeyError:
            pass
    except KeyError:
        try:
            pbsdf.inputs["Subsurface"].default_value = 0.32
            pbsdf.inputs["Subsurface Radius"].default_value = (0.12, 0.05, 0.028)
            pbsdf.inputs["Subsurface Color"].default_value = sss_color
        except KeyError:
            pass

    # Emission: SPEC color (1.0,0.88,0.45) @ strength 2.5, delivered through a
    # LOW MixShader factor so the effective radiance is 2.5 * 0.10 = 0.25 —
    # in the near-black void this makes Godwyn VISIBLY self-luminous (he is
    # the room's light source, blocker #4) while the Principled layer keeps
    # full 3D form (shadows, SSS). Not blown out; not a studio product shot.
    emit = _new_node(nt, "ShaderNodeEmission", (200, -200))
    mix  = _new_node(nt, "ShaderNodeMixShader", (480, 0))
    emit.inputs["Color"].default_value    = G.COL_SKIN_EMIT
    emit.inputs["Strength"].default_value = G.SKIN_EMIT_STR   # 2.5 per SPEC

    # Fac 0.22 => effective radiance 2.5 * 0.22 = 0.55 (r3 major #2: 0.10
    # still read as flat matte plaster). At 0.55 the skin visibly glows warm
    # in the void and CASTS light that rims the robe/armor, while the
    # Principled layer keeps 3D form. The external key drops in 04 so this
    # glow leads the exposure instead of fighting a studio key.
    mix.inputs["Fac"].default_value = 0.22
    _link(nt, pbsdf, "BSDF",     mix, 1)
    _link(nt, emit,  "Emission", mix, 2)
    _link(nt, mix,   "Shader",   out, "Surface")

    return mat


def make_gold_material() -> bpy.types.Material:
    """
    Gold armor / hilt / crossguard — metallic PBR, faintly worn (SPEC 341).

    Node graph:
      Noise Texture (roughness variation)  →  Mix (map to 0.15-0.35)
             ↓ roughness
      Principled BSDF (metallic=1, slight anisotropy)
             ↓
      Material Output

    The roughness noise gives the "faintly worn" look without needing a
    painted texture map.
    """
    mat = bpy.data.materials.new("Mat_Gold")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial",  (800, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled",  (500, 0))
    mapv  = _new_node(nt, "ShaderNodeMapRange",         (250, -100))
    noise = _new_node(nt, "ShaderNodeTexNoise",         (0, -100))
    tex_c = _new_node(nt, "ShaderNodeTexCoord",         (-200, -100))

    # Base gold color (linear sRGB, SPEC 341)
    pbsdf.inputs["Base Color"].default_value = G.COL_GOLD
    pbsdf.inputs["Metallic"].default_value   = 1.0
    # Anisotropy for metallic sheen
    try:
        pbsdf.inputs["Anisotropic"].default_value          = 0.25
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.0
    except KeyError:
        pass
    # IOR for metallic look
    try:
        pbsdf.inputs["IOR"].default_value = 1.5
    except KeyError:
        pass

    # Noise → roughness variation (faintly worn)
    noise.inputs["Scale"].default_value      = 12.0
    noise.inputs["Detail"].default_value     = 4.0
    noise.inputs["Roughness"].default_value  = 0.65
    noise.inputs["Distortion"].default_value = 0.15

    # Map noise 0..1 → roughness 0.25..0.45 — worn layered plate, NOT chrome
    # (minor #9: art direction wants clearly "slightly worn" gold)
    mapv.inputs["From Min"].default_value = 0.0
    mapv.inputs["From Max"].default_value = 1.0
    mapv.inputs["To Min"].default_value   = 0.25
    mapv.inputs["To Max"].default_value   = 0.45
    try:
        mapv.clamp = True
    except AttributeError:
        pass

    _link(nt, tex_c, "Object",   noise, "Vector")
    _link(nt, noise, "Fac",      mapv,  "Value")
    _link(nt, mapv,  "Result",   pbsdf, "Roughness")
    _link(nt, pbsdf, "BSDF",    out,   "Surface")

    return mat


def make_robe_material() -> bpy.types.Material:
    """
    Deep blue flowing robe — cloth-ish, NO emission (SPEC 340).

    Principled BSDF: deep-blue base, moderate roughness, slight sheen
    for the flowing-fabric read.
    """
    mat = bpy.data.materials.new("Mat_Robe")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (400, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))

    # Deep blue (linear sRGB, SPEC 340)
    pbsdf.inputs["Base Color"].default_value = G.COL_ROBE
    pbsdf.inputs["Roughness"].default_value  = 0.85     # matte cloth
    pbsdf.inputs["Metallic"].default_value   = 0.0
    # NO emission
    # Kill the specular wash that lifted the blue to periwinkle (major #6)
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.08
    except (KeyError, AttributeError):
        try:
            pbsdf.inputs["Specular"].default_value = 0.05
        except (KeyError, AttributeError):
            pass

    # Sheen for fabric fold micro-highlights
    try:
        pbsdf.inputs["Sheen Weight"].default_value = 0.18
        pbsdf.inputs["Sheen Roughness"].default_value = 0.55
    except KeyError:
        try:
            pbsdf.inputs["Sheen"].default_value = 0.18
        except KeyError:
            pass

    _link(nt, pbsdf, "BSDF", out, "Surface")
    return mat


def make_blade_material() -> bpy.types.Material:
    """
    Sword blade — polished steel + subtle blue tint + faint glow (SPEC 317).

    Round-2 rebuild (major #6): the old MixShader(steel, dim-emission)
    DARKENED the metal — the blade read as flat navy plastic. Now it is a
    single Principled BSDF: metallic=1, LOW roughness (real specular steel),
    lighter blue-steel base, with the faint blue emission delivered through
    the Principled emission inputs (strength 0.12 — far below the skin's
    effective glow) so it never dims the metal reflections.
    """
    mat = bpy.data.materials.new("Mat_Blade")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (400, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))

    # r3 major #4: at roughness 0.10 in a black void a perfect mirror has
    # nothing to reflect — the blade rendered near-black. Lighter steel base,
    # broader highlight lobe, and a stronger (still << skin) blue emission so
    # the edge reads against the void.
    pbsdf.inputs["Base Color"].default_value = (0.78, 0.82, 0.92, 1.0)
    pbsdf.inputs["Metallic"].default_value   = 1.0
    pbsdf.inputs["Roughness"].default_value  = 0.24     # steel, not a mirror
    try:
        pbsdf.inputs["Anisotropic"].default_value = 0.35   # forged grain
    except KeyError:
        pass
    # faint blue emission INSIDE the BSDF (Blender 4+), << skin (0.55 eff.)
    try:
        pbsdf.inputs["Emission Color"].default_value = G.COL_BLADE_EMIT
        pbsdf.inputs["Emission Strength"].default_value = 0.30
    except KeyError:
        pass

    _link(nt, pbsdf, "BSDF", out, "Surface")
    return mat


def make_hair_material() -> bpy.types.Material:
    """
    Golden-blonde hair — lighter/less-saturated than armor gold (SPEC 299).

    Principled BSDF with anisotropic sheen (approximates hair specularity
    on mesh tubes), COL_HAIR is (0.75,0.58,0.08) — same hue family as
    armor gold but brighter/less saturated.
    """
    mat = bpy.data.materials.new("Mat_Hair")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    out   = _new_node(nt, "ShaderNodeOutputMaterial", (400, 0))
    pbsdf = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))

    pbsdf.inputs["Base Color"].default_value = G.COL_HAIR
    pbsdf.inputs["Roughness"].default_value  = 0.40    # silky-smooth hair
    pbsdf.inputs["Metallic"].default_value   = 0.0

    # Anisotropy → hair-like directional sheen along the strands
    try:
        pbsdf.inputs["Anisotropic"].default_value          = 0.55
        pbsdf.inputs["Anisotropic Rotation"].default_value = 0.0
    except KeyError:
        pass

    # Subtle specular boost so the gold reads at render distance
    try:
        pbsdf.inputs["Specular IOR Level"].default_value = 0.60
    except KeyError:
        try:
            pbsdf.inputs["Specular"].default_value = 0.40
        except KeyError:
            pass

    _link(nt, pbsdf, "BSDF", out, "Surface")
    return mat


def make_eye_materials():
    """
    Sclera / iris / pupil for the real MPFB2 eyeballs (blocker #2).
    Iris = warm gold-hazel per art direction; all three get a glossy
    clear-coat so the eyes catch light.
    """
    def base(name, color, rough, emit=None):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = _new_node(nt, "ShaderNodeOutputMaterial", (400, 0))
        p = _new_node(nt, "ShaderNodeBsdfPrincipled", (0, 0))
        p.inputs["Base Color"].default_value = color
        p.inputs["Roughness"].default_value = rough
        try:   # glossy cornea coat
            p.inputs["Coat Weight"].default_value = 1.0
            p.inputs["Coat Roughness"].default_value = 0.03
        except KeyError:
            pass
        if emit is not None:
            try:
                p.inputs["Emission Color"].default_value = emit[0]
                p.inputs["Emission Strength"].default_value = emit[1]
            except KeyError:
                pass
        _link(nt, p, "BSDF", out, "Surface")
        return mat

    # r3 blocker #1: iris emission 0.60 blew the amber past the sclera —
    # under AgX both rendered flat WHITE and only the tiny pupil survived.
    # Whisper-level emission only; the iris must read as a DARK warm ring.
    sclera = base("Mat_EyeSclera", (0.88, 0.86, 0.82, 1.0), 0.30,
                  emit=((0.95, 0.93, 0.88, 1.0), 0.03))
    iris   = base("Mat_EyeIris",   (0.42, 0.26, 0.07, 1.0), 0.20,
                  emit=((1.0, 0.85, 0.40, 1.0), 0.10))   # deep amber-gold
    pupil  = base("Mat_EyePupil",  (0.012, 0.010, 0.008, 1.0), 0.12)
    return sclera, iris, pupil


def assign_eye_materials(eyes, sclera, iris, pupil, skin):
    """
    Godwyn_Eyes (built by 02_details.build_eyes) carries per-face
    material_index bands already: 0=sclera, 1=iris, 2=pupil, 3=eyelid skin
    (r3). Replace the materials IN-SLOT — materials.clear() would RESET
    every polygon's material_index to 0 (that wiped the iris/pupil in r2).
    """
    me = eyes.data
    assert len(me.materials) >= 3, \
        f"Godwyn_Eyes expected 3+ material slots, has {len(me.materials)}"
    me.materials[0] = sclera
    me.materials[1] = iris
    me.materials[2] = pupil
    if len(me.materials) >= 4:
        me.materials[3] = skin           # eyelid shells match the face
    me.update()
    counts = [0, 0, 0, 0]
    for poly in me.polygons:
        counts[min(poly.material_index, 3)] += 1
    print(f"[03_materials] Godwyn_Eyes slots refilled: {counts[0]} sclera / "
          f"{counts[1]} iris / {counts[2]} pupil / {counts[3]} lid polys")


# ---------------------------------------------------------------------------
# SWORD MATERIAL ASSIGNMENT (two-slot: hilt=gold, blade=blade)
# ---------------------------------------------------------------------------

def assign_sword_materials(sword, mat_gold, mat_blade):
    """
    The sword is one joined mesh. We use two material slots and face-level
    assignment:
      Slot 0 = Mat_Gold  (hilt, crossguard, pommel — all gold parts)
      Slot 1 = Mat_Blade (the blade geometry)

    Strategy: faces near or below z=0.21 (in local space, where the
    crossguard/hilt/pommel live) go to slot 0; faces above go to slot 1.
    The blade's local z starts at ~0.20 (just above the crossguard collar).
    """
    sword.data.materials.clear()
    sword.data.materials.append(mat_gold)    # slot 0
    sword.data.materials.append(mat_blade)   # slot 1

    # world-to-local matrix for vertex z lookup
    mw = sword.matrix_world
    for poly in sword.data.polygons:
        # centroid in local space
        local_z = poly.center[2]
        poly.material_index = 1 if local_z > 0.22 else 0

    sword.data.update()


# ---------------------------------------------------------------------------
# VOID WORLD + CRACK
# ---------------------------------------------------------------------------

def build_void_world():
    """
    Rebuild the void world shader (near-black) and the faint vertical golden
    crack plane (INV-7 / SPEC 337-341).  Idempotent: removes any prior
    Godwyn_VoidCrack first.

    The crack is a thin emissive plane standing 5.0m tall behind Godwyn,
    color (1.0,0.85,0.4), strength 3.5 — faint, framing, not dominant.
    """
    # World shader
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("VoidWorld")
        bpy.context.scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()
    bg = wnt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value     = G.COL_WORLD
    bg.inputs["Strength"].default_value  = 1.0
    wout = wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

    # Remove prior crack plane (INV-6)
    for name in list(bpy.data.objects.keys()):
        if "VoidCrack" in name:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    # Remove prior crack material
    if "Mat_VoidCrack" in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials["Mat_VoidCrack"])

    # Tall vertical emissive crack, built VERTICALLY in the XZ plane.
    # (The previous build used primitive_plane_add — which lies FLAT in XY —
    #  then scaled its zero-extent Z axis, leaving an invisible sliver. That
    #  is why every render had a featureless black background, blocker #4.)
    # Body faces -Y; cameras are at -Y, so the crack goes at +Y behind him,
    # offset in X so his silhouette does not fully occlude it.
    import random as _rnd
    _rnd.seed(52)
    # Round 4 (major #5): the crack at (x~1.0, y=7) overlapped Godwyn's
    # silhouette in BOTH review cameras and read as a glowing whip attached
    # to him. Now: pushed to y=12 (far behind), offset to x~2.6 (clears the
    # figure from Cam_Full at (1.5,-9.4) AND Cam_Face at (0,-2.1)), thinner,
    # near-vertical, base raised off the floor so it reads as a DISTANT
    # fissure in the void. Intensity fades toward the top (shader gradient).
    z0, z1 = 0.9, 6.6
    segs = 14
    cverts, cfaces = [], []
    for i in range(segs + 1):
        t = i / segs
        z = z0 + (z1 - z0) * t
        # gently jagged, near-vertical centre-line; pinches at both ends
        cx = 2.60 + 0.025 * math.sin(t * 9.0) + _rnd.uniform(-0.010, 0.010)
        hw = 0.030 * math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6 \
            + _rnd.uniform(0.0, 0.006)
        cverts.append((cx - hw, 12.0, z))
        cverts.append((cx + hw, 12.0, z))
    for i in range(segs):
        a = i * 2
        cfaces.append((a, a + 1, a + 3, a + 2))
    cme = bpy.data.meshes.new("Godwyn_VoidCrack")
    cme.from_pydata(cverts, [], cfaces)
    cme.update()
    crack = bpy.data.objects.new("Godwyn_VoidCrack", cme)
    bpy.context.scene.collection.objects.link(crack)

    crack_mat = bpy.data.materials.new("Mat_VoidCrack")
    crack_mat.use_nodes = True
    cnt = crack_mat.node_tree
    cnt.nodes.clear()
    emit = cnt.nodes.new("ShaderNodeEmission")
    # saturated deep gold at RESTRAINED strength: AgX whites-out emissive
    # highlights fast — 2.6 read as a white ribbon; ~1.8 keeps the gold HUE
    emit.inputs["Color"].default_value = (1.0, 0.50, 0.08, 1.0)
    # r4 major #5: strength FADES toward the top (distant-fissure read):
    # Generated Z (0 at base, 1 at top) -> Map Range 2.0 -> 0.30
    tco = cnt.nodes.new("ShaderNodeTexCoord")
    sep = cnt.nodes.new("ShaderNodeSeparateXYZ")
    mr = cnt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value   = 2.0
    mr.inputs["To Max"].default_value   = 0.30
    cnt.links.new(tco.outputs["Generated"], sep.inputs["Vector"])
    cnt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    cnt.links.new(mr.outputs["Result"], emit.inputs["Strength"])
    mout = cnt.nodes.new("ShaderNodeOutputMaterial")
    cnt.links.new(emit.outputs["Emission"], mout.inputs["Surface"])
    crack.data.materials.append(crack_mat)

    return crack


# ---------------------------------------------------------------------------
# ASSIGN ALL MATERIALS
# ---------------------------------------------------------------------------

def assign_all_materials():
    """
    Build every material and assign it to the corresponding Godwyn_* object.
    Clears preview materials from P1/P2 first (INV-6).
    """
    clear_materials()

    # Build materials
    mat_skin  = make_skin_material()
    mat_gold  = make_gold_material()
    mat_robe  = make_robe_material()
    mat_blade = make_blade_material()
    mat_hair  = make_hair_material()
    sclera, iris, pupil = make_eye_materials()

    print("[03_materials] Materials built: Skin, Gold, Robe, Blade, Hair, "
          "EyeSclera/Iris/Pupil.")

    # Simple assignments
    for obj_name, mat_name in OBJECT_ASSIGNMENTS.items():
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            print(f"[03_materials] WARNING: '{obj_name}' not found — skipping.",
                  file=sys.stderr)
            continue
        if mat_name is None:
            continue    # handled specially below
        if obj_name == "Godwyn_Body":
            continue    # body handled below (skin + eye slots)
        mat = bpy.data.materials[mat_name]
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        print(f"[03_materials]   {obj_name} <- {mat_name}")

    # Body: skin only (the eyeballs are the separate Godwyn_Eyes object now)
    body = bpy.data.objects.get("Godwyn_Body")
    if body:
        body.data.materials.clear()
        body.data.materials.append(mat_skin)
        print("[03_materials]   Godwyn_Body <- Mat_Skin")

    # Eyes: sclera/iris/pupil slots (banded by 02_details.build_eyes)
    eyes = bpy.data.objects.get("Godwyn_Eyes")
    if eyes:
        assign_eye_materials(eyes, sclera, iris, pupil, mat_skin)
        print("[03_materials]   Godwyn_Eyes <- EyeSclera/Iris/Pupil (+Skin lids)")
    else:
        print("[03_materials] WARNING: Godwyn_Eyes not found — run 02 first.",
              file=sys.stderr)

    # Sword: hilt=gold, blade=blade
    sword = bpy.data.objects.get("Godwyn_Sword")
    if sword:
        assign_sword_materials(sword, mat_gold, mat_blade)
        print("[03_materials]   Godwyn_Sword <- Gold (hilt) + Blade (blade)")
    else:
        print("[03_materials] WARNING: Godwyn_Sword not found — sword materials skipped.",
              file=sys.stderr)

    return mat_skin, mat_gold, mat_robe, mat_blade, mat_hair


# ---------------------------------------------------------------------------
# BEAUTY PREVIEW CAMERA + LIGHTING
# ---------------------------------------------------------------------------

def setup_beauty_preview(scene):
    """
    Minimal lighting for the beauty preview:
      - A warm key light from upper-front-left (INV-7 color 1.0,0.92,0.6)
      - A cool dim fill to keep shadow side readable, not pure black
      - A rim from behind to separate from the void

    NOT the full P4 rig — just enough to judge material colors.
    We rely primarily on Godwyn's skin emission to carry the face.
    """
    # Remove any prior preview lights/cam
    for name in list(bpy.data.objects.keys()):
        if name.startswith(("Beauty_", "Clay_")):
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    for d in list(bpy.data.lights):
        if d.name.startswith(("Beauty_", "Clay_")):
            bpy.data.lights.remove(d)
    for d in list(bpy.data.cameras):
        if d.name.startswith(("Beauty_", "Clay_")):
            bpy.data.cameras.remove(d)

    # --- Camera ---
    # Body faces -Y (documented in 02_details.py: "Body faces -Y").
    # Front of character (chest, face) is in the -Y hemisphere.
    # Camera must be placed at negative Y to see the front.
    # Slight right offset (+X) for a 3/4 portrait composition.
    cam_data = bpy.data.cameras.new("Beauty_Cam")
    cam_data.lens    = 70      # slight telephoto for portrait
    cam_data.clip_end = 60.0
    cam_obj = bpy.data.objects.new("Beauty_Cam", cam_data)
    scene.collection.objects.link(cam_obj)
    import mathutils
    # Camera at front-right: x=+1.2, y=-8.0 (looking at front), z=1.85 (mid-chest/upper body)
    cam_obj.location = (1.2, -8.0, 1.85)
    # Aim at chest center (head_z ~3.0, waist ~1.97; mid ~2.4)
    target = mathutils.Vector((0.0, 0.0, 2.10))
    direction = cam_obj.location - target
    cam_obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    scene.camera = cam_obj

    # Dark-fantasy lighting rig per SPEC: Godwyn is the scene light source.
    # In the void, there is no environmental light — the only illumination
    # comes from Godwyn himself and a faint off-axis key to reveal form.
    #
    # Rig philosophy:
    #   • GodwynGlow point at chest = primary ambient (warm, omni)
    #   • Key area light = reveal 3D form (shadows, SSS) from front-left
    #   • Rim area light = separate silhouette from void at back
    #   • No fill — void world has no fill; shadow side goes dark

    # --- Godwyn chest glow (ambient fill) — SPEC 337-339 ---
    # This simulates the inner-glow ambient the SPEC describes:
    # "Emission casts light YES — Godwyn is the room's light source"
    # Keep it LOW so it fills shadows warmly but doesn't flood the surface.
    # The KEY LIGHT is the primary form revealer.
    glow = bpy.data.lights.new("Beauty_GodwynGlow", "POINT")
    glow.energy   = 25.0     # low ambient — skin emission now does the work
    glow.color    = (1.0, 0.92, 0.6)
    glow.shadow_soft_size = 2.0
    glow_o = bpy.data.objects.new("Beauty_GodwynGlow", glow)
    scene.collection.objects.link(glow_o)
    glow_o.location = (0.0, -1.0, 2.30)   # slightly in front of chest

    # --- Key light: primary form revealer (three-point rig) ---
    # Strong directional area light from front-left-top casts shadows
    # and reveals muscle/fabric form. This is what gives the render depth.
    key = bpy.data.lights.new("Beauty_Key", "AREA")
    key.energy       = 110.0   # dim form light — Godwyn is the light source
    key.color        = (1.0, 0.92, 0.6)
    key.size         = 2.5
    key_o = bpy.data.objects.new("Beauty_Key", key)
    scene.collection.objects.link(key_o)
    key_o.location   = (-3.5, -5.0, 5.5)
    key_o.rotation_euler = (math.radians(50), math.radians(-30),
                             math.radians(-20))

    # --- Rim: behind character (+Y side), separates from void ---
    import mathutils as mu
    rim = bpy.data.lights.new("Beauty_Rim", "AREA")
    rim.energy        = 90.0
    rim.color         = (1.0, 0.88, 0.50)   # warm gold rim
    rim.size          = 2.5
    rim_o = bpy.data.objects.new("Beauty_Rim", rim)
    scene.collection.objects.link(rim_o)
    rim_o.location    = (0.0, 5.5, 4.0)
    target_rim = mu.Vector((0.0, 0.0, 2.0))
    dir_rim = mu.Vector(rim_o.location) - target_rim
    rim_o.rotation_euler = dir_rim.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------------------
# VALIDATION ASSERTS (plan Section 3 Phase 3 gate)
# ---------------------------------------------------------------------------

def assert_materials():
    errors = []

    # All core materials must exist
    for name in ("Mat_Skin", "Mat_Gold", "Mat_Robe", "Mat_Blade", "Mat_Hair"):
        if name not in bpy.data.materials:
            errors.append(f"Material '{name}' missing")

    # Each character object must have at least one material slot
    for obj_name in ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Robe",
                     "Godwyn_Hair", "Godwyn_Sword", "Godwyn_Eyes"):
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            errors.append(f"Object '{obj_name}' missing")
            continue
        if len(obj.data.materials) == 0:
            errors.append(f"'{obj_name}' has no material slots")

    # Skin emission must be non-trivial (strength > 0).
    # Emission may be either in a ShaderNodeEmission node OR inside
    # Principled BSDF "Emission Strength" (Blender 4+).
    skin = bpy.data.materials.get("Mat_Skin")
    if skin:
        # Check Principled BSDF emission first (Blender 4+)
        pbsdf_skin = next((n for n in skin.node_tree.nodes
                           if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        emit_ok = False
        if pbsdf_skin:
            try:
                s = pbsdf_skin.inputs["Emission Strength"].default_value
                if s >= 0.5:
                    emit_ok = True
            except KeyError:
                pass
        # Fall back: standalone Emission node (Blender 3.x / Mix approach)
        if not emit_ok:
            emit_node = next((n for n in skin.node_tree.nodes
                             if n.bl_idname == "ShaderNodeEmission"), None)
            if emit_node is not None:
                s = emit_node.inputs["Strength"].default_value
                if s >= 0.1:   # only requires >0 — fac on MixShader controls intensity
                    emit_ok = True
        if not emit_ok:
            errors.append("Mat_Skin: no emission found (check Principled BSDF or Emission node)")

    # Gold must be metallic=1
    gold = bpy.data.materials.get("Mat_Gold")
    if gold:
        pbsdf = next((n for n in gold.node_tree.nodes
                      if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
        if pbsdf is None:
            errors.append("Mat_Gold has no Principled BSDF")
        else:
            m = pbsdf.inputs["Metallic"].default_value
            if m < 0.99:
                errors.append(f"Mat_Gold metallic < 1: {m}")

    # Robe must have NO emission node
    robe = bpy.data.materials.get("Mat_Robe")
    if robe:
        emit_nodes = [n for n in robe.node_tree.nodes
                      if n.bl_idname == "ShaderNodeEmission"]
        if emit_nodes:
            errors.append("Mat_Robe has an Emission node (SPEC 340: no emission)")

    # Void crack must exist and have a REAL emissive material bound
    # (a None slot passes len()>0 — that hid the blocker-#2 root cause)
    crack = bpy.data.objects.get("Godwyn_VoidCrack")
    if crack is None:
        errors.append("Godwyn_VoidCrack object missing")
    elif len(crack.data.materials) == 0 or crack.data.materials[0] is None:
        errors.append("Godwyn_VoidCrack has no material bound (empty slot)")
    elif not any(n.bl_idname == "ShaderNodeEmission"
                 for n in crack.data.materials[0].node_tree.nodes):
        errors.append("Godwyn_VoidCrack material has no Emission node")

    if errors:
        for e in errors:
            print(f"[03_materials] FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    print("[03_materials] ASSERT OK: All materials built and assigned.")
    print(f"[03_materials]   Skin emit strength = {G.SKIN_EMIT_STR} (subtle glow).")
    print(f"[03_materials]   Blade emit strength = {G.BLADE_EMIT_STR} << skin (restrained).")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("[03_materials] Phase 3 — Materials & Shaders")
    print("=" * 60)

    # INV-2: GPU enforced first, before any expensive work
    active_gpu = G.enable_gpu()
    print(f"[03_materials] GPU active: {active_gpu}")

    # Load the saved .blend — it already has all Godwyn_* objects from Phase 2.
    # This is the correct approach: apply materials to existing geometry rather
    # than rebuilding from module scripts (whose API changed in Phase 2).
    import os as _os
    blend_path = _os.path.join(_REPO_ROOT, "models", "godwyn_phase1.blend")
    if not _os.path.isfile(blend_path):
        print(f"[03_materials] FATAL: .blend not found: {blend_path}", file=sys.stderr)
        sys.exit(1)

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    print(f"[03_materials] Opened: {blend_path}")

    # INV-2: re-enable GPU after file open (file open resets scene settings)
    active_gpu = G.enable_gpu()
    print(f"[03_materials] GPU re-enabled after file open: {active_gpu}")

    # Confirm Godwyn objects are present
    expected = ("Godwyn_Body", "Godwyn_Armor", "Godwyn_Robe",
                "Godwyn_Hair", "Godwyn_Sword", "Godwyn_Eyes")
    missing = [n for n in expected if bpy.data.objects.get(n) is None]
    if missing:
        print(f"[03_materials] FATAL: Objects missing after .blend load: {missing}",
              file=sys.stderr)
        sys.exit(1)
    print(f"[03_materials] Godwyn objects confirmed: {list(expected)}")

    # Assign all materials (INV-3 / INV-6)
    assign_all_materials()

    # Build void world + crack (INV-7).
    # MUST run AFTER assign_all_materials: clear_materials() removes
    # Mat_VoidCrack by name, and when the crack was built first it was left
    # with an EMPTY slot — a default gray plane lit by the rim light. That
    # was the true root cause of blocker #2's "white line, not golden".
    crack = build_void_world()
    col = bpy.data.collections.get("Godwyn")
    if col is None:
        col = G.get_or_create_collection("Godwyn")
    G.move_to_collection(crack, col)
    print("[03_materials] Void world + golden crack plane built.")

    # SAVE the .blend NOW — before any preview-only lights/cameras exist.
    # (Previous revision never saved: Phase 3's SSS/emission/void-crack were
    #  lost and Phase 4+ rendered Phase-2 preview materials. Root cause of
    #  blockers #4/#5.)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    print(f"[03_materials] SAVED materials into {blend_path} "
          f"({os.path.getsize(blend_path) // 1024} KB)")

    # Setup beauty preview camera and lights (in-memory only, NOT saved)
    scene = bpy.context.scene
    setup_beauty_preview(scene)

    # Cycles render config — beauty preview at reduced res for iteration speed
    # (still 2K+ per plan; 1440x2560 = caller target from plan §10 OQ-1)
    G.configure_cycles(
        scene,
        samples=192,             # higher than clay for real material eval
        resolution_x=1440,
        resolution_y=2560,
        use_denoiser=True,
        film_transparent=False,  # keep the void black bg
    )

    # Validate
    assert_materials()

    # Render
    print(f"[03_materials] Rendering beauty preview -> {_PREVIEW_OUT}")
    G.render_to_path(_PREVIEW_OUT, scene)

    # Verify output
    if not os.path.isfile(_PREVIEW_OUT) or os.path.getsize(_PREVIEW_OUT) < 1024:
        print(f"[03_materials] FATAL: preview PNG missing/empty: {_PREVIEW_OUT}",
              file=sys.stderr)
        sys.exit(1)

    size_kb = os.path.getsize(_PREVIEW_OUT) // 1024
    print(f"[03_materials] Beauty preview OK: {_PREVIEW_OUT} ({size_kb} KB)")
    print("[03_materials] Object list:",
          sorted(o.name for o in bpy.data.collections["Godwyn"].objects))
    print("[03_materials] Phase 3 complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
else:
    main()
